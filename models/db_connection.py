#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库连接模块
"""
import pymysql
import logging
from typing import Dict, Any, List, Tuple, Optional
from contextlib import contextmanager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseConnection:
    """数据库连接类，负责与MySQL数据库的连接和基本操作"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化数据库连接配置
        
        Args:
            config: 数据库配置字典，包含HOST, PORT, USER, PASSWORD, DB, CHARSET等
        """
        self.config = config
        self.connection = None
    
    def connect(self):
        """建立数据库连接
        
        Returns:
            pymysql.connections.Connection: 数据库连接对象
        
        Raises:
            pymysql.MySQLError: 数据库连接失败时抛出
        """
        try:
            self.connection = pymysql.connect(
                host=self.config.get('HOST'),
                port=self.config.get('PORT'),
                user=self.config.get('USER'),
                password=self.config.get('PASSWORD'),
                db=self.config.get('DB'),
                charset=self.config.get('CHARSET', 'utf8mb4'),
                cursorclass=pymysql.cursors.DictCursor  # 使用字典光标，结果以字典形式返回
            )
            logger.info(f"成功连接到数据库: {self.config.get('DB')}")
            return self.connection
        except pymysql.MySQLError as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.connection and not self.connection._closed:
            self.connection.close()
            logger.info("数据库连接已关闭")
    
    @contextmanager
    def get_cursor(self):
        """获取数据库游标，使用上下文管理器自动处理游标和连接
        
        Yields:
            pymysql.cursors.DictCursor: 数据库游标对象
        """
        if not self.connection or self.connection._closed:
            self.connect()
        
        try:
            with self.connection.cursor() as cursor:
                yield cursor
                self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
    
    def execute_query(self, query: str, params: Tuple = None) -> List[Dict[str, Any]]:
        """执行SQL查询并返回结果
        
        Args:
            query: SQL查询语句
            params: SQL参数，用于参数化查询
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"查询执行失败: {query}, 错误: {e}")
            raise
    
    def execute_update(self, query: str, params: Tuple = None) -> int:
        """执行SQL更新操作（INSERT, UPDATE, DELETE）
        
        Args:
            query: SQL更新语句
            params: SQL参数，用于参数化查询
            
        Returns:
            int: 受影响的行数
        """
        try:
            with self.get_cursor() as cursor:
                affected_rows = cursor.execute(query, params)
                return affected_rows
        except Exception as e:
            logger.error(f"更新操作失败: {query}, 错误: {e}")
            raise
    
    def get_all_tables(self) -> List[str]:
        """获取数据库中所有表的名称
        
        Returns:
            List[str]: 表名列表
        """
        query = "SHOW TABLES"
        result = self.execute_query(query)
        # 提取表名，适配不同的MySQL版本
        if result and isinstance(result[0], dict):
            # 对于MySQL 8.0+，键名格式为 'Tables_in_{dbname}'
            key = next(iter(result[0].keys()))
            return [row[key] for row in result]
        return []
    
    def get_table_structure(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的结构信息
        
        Args:
            table_name: 表名
            
        Returns:
            List[Dict[str, Any]]: 表结构信息列表，包含字段名、类型等
        """
        # 使用反引号包裹表名，避免与MySQL保留关键字冲突
        query = f"DESCRIBE `{table_name}`"
        return self.execute_query(query)
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """获取表的所有字段名
        
        Args:
            table_name: 表名
            
        Returns:
            List[str]: 字段名列表
        """
        structure = self.get_table_structure(table_name)
        return [col['Field'] for col in structure]

# 如果从配置文件导入失败，使用默认值
try:
    # 尝试直接导入配置
    try:
        from config import DATABASE_CONFIG
    except ImportError:
        # 如果直接导入失败，尝试添加父目录到路径
        import sys
        import os
        # 获取当前文件所在目录的父目录
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 将父目录添加到Python路径
        sys.path.append(parent_dir)
        from config import DATABASE_CONFIG
    
    # 创建一个全局的数据库连接实例
    db = DatabaseConnection(DATABASE_CONFIG)
except Exception as e:
    # 没有配置文件时，先创建一个默认的连接对象
    db = None
    logger.warning(f"配置文件未找到或导入失败: {e}")

if __name__ == "__main__":
    # 测试数据库连接
    if db:
        try:
            tables = db.get_all_tables()
            print(f"数据库中共有 {len(tables)} 个表:")
            for table in tables:
                print(f"- {table}")
                # 获取表结构
                structure = db.get_table_structure(table)
                print(f"  表结构: {len(structure)} 个字段")
        except Exception as e:
            print(f"测试连接失败: {e}")
        finally:
            db.close()