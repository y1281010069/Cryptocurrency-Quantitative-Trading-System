#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基础模型类，提供通用的数据库操作方法
"""
import os
import sys
import logging
from typing import Dict, Any, List, Tuple, Optional

# 添加当前目录到Python路径以便直接运行脚本
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 尝试相对导入，如果失败则使用绝对导入
try:
    from .db_connection import db, DatabaseConnection
except ImportError:
    from db_connection import db, DatabaseConnection

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)

class BaseModel:
    """基础模型类，所有数据表模型的父类"""
    
    # MySQL保留关键字列表
    MYSQL_RESERVED_WORDS = {
        'order', 'select', 'from', 'where', 'insert', 'update', 'delete',
        'create', 'drop', 'alter', 'table', 'database', 'index', 'view',
        'procedure', 'function', 'trigger', 'event', 'case', 'when', 'then',
        'else', 'end', 'join', 'inner', 'outer', 'left', 'right', 'full',
        'on', 'group', 'by', 'having', 'order', 'limit', 'offset', 'union',
        'all', 'distinct', 'as', 'like', 'in', 'between', 'and', 'or',
        'not', 'exists', 'is', 'null', 'true', 'false', 'default', 'auto_increment'
    }
    
    # 子类必须定义以下属性
    table_name: str = ""  # 表名
    primary_key: str = "id"  # 主键字段名
    
    def __init__(self, db_conn: Optional[DatabaseConnection] = None):
        """初始化模型
        
        Args:
            db_conn: 数据库连接对象，如果为None则使用全局的db实例
        """
        self.db = db_conn or db
        if not self.db:
            raise ValueError("数据库连接未初始化")
        
        # 缓存表结构
        self._table_columns = None
    
    @property
    def table_columns(self) -> List[str]:
        """获取表的所有字段名
        
        Returns:
            List[str]: 字段名列表
        """
        if self._table_columns is None:
            self._table_columns = self.db.get_table_columns(self.table_name)
        return self._table_columns
    
    def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证数据是否符合表结构
        
        Args:
            data: 要验证的数据字典
            
        Returns:
            Dict[str, Any]: 验证后的数据字典
        
        Raises:
            ValueError: 数据不符合表结构时抛出
        """
        valid_data = {}
        columns = self.table_columns
        
        for key, value in data.items():
            if key in columns:
                valid_data[key] = value
            else:
                logger.warning(f"字段 '{key}' 不在表 '{self.table_name}' 中，已忽略")
        
        return valid_data
    
    def _safe_table_name(self) -> str:
        """获取安全的表名，避免与MySQL保留关键字冲突
        
        Returns:
            str: 安全的表名（如果是保留关键字则用反引号包裹）
        """
        if self.table_name.lower() in self.MYSQL_RESERVED_WORDS:
            return f"`{self.table_name}`"
        return self.table_name
    
    def get(self, **kwargs) -> Optional[Dict[str, Any]]:
        """根据条件查询单条记录
        
        Args:
            **kwargs: 查询条件
            
        Returns:
            Optional[Dict[str, Any]]: 查询结果，如果没有找到则返回None
        """
        if not kwargs:
            return None
        
        # 构建WHERE子句
        where_clauses = []
        params = []
        for key, value in kwargs.items():
            where_clauses.append(f"{key} = %s")
            params.append(value)
        
        where_str = " AND ".join(where_clauses)
        query = f"SELECT * FROM {self._safe_table_name()} WHERE {where_str} LIMIT 1"
        
        result = self.db.execute_query(query, tuple(params))
        return result[0] if result else None
    
    def get_all(self, **kwargs) -> List[Dict[str, Any]]:
        """根据条件查询多条记录
        
        Args:
            **kwargs: 查询条件
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        query = f"SELECT * FROM {self._safe_table_name()}"
        params = []
        
        if kwargs:
            # 构建WHERE子句
            where_clauses = []
            for key, value in kwargs.items():
                where_clauses.append(f"{key} = %s")
                params.append(value)
            
            where_str = " AND ".join(where_clauses)
            query += f" WHERE {where_str}"
        
        return self.db.execute_query(query, tuple(params))
    
    def create(self, data: Dict[str, Any]) -> Optional[int]:
        """创建新记录
        
        Args:
            data: 要插入的数据字典
            
        Returns:
            Optional[int]: 新记录的主键ID，如果操作失败则返回None
        """
        # 验证数据
        valid_data = self.validate_data(data)
        if not valid_data:
            logger.warning("没有有效的数据可插入")
            return None
        
        # 构建INSERT语句
        columns = ", ".join(valid_data.keys())
        placeholders = ", ".join(["%s"] * len(valid_data))
        params = list(valid_data.values())
        
        query = f"INSERT INTO {self._safe_table_name()} ({columns}) VALUES ({placeholders})"
        
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(query, tuple(params))
                # 获取插入的ID
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"创建记录失败: {e}")
            return None
    
    def update(self, pk_value: Any, data: Dict[str, Any]) -> bool:
        """根据主键更新记录
        
        Args:
            pk_value: 主键值
            data: 要更新的数据字典
            
        Returns:
            bool: 更新是否成功
        """
        # 验证数据并排除主键
        valid_data = self.validate_data(data)
        if not valid_data or self.primary_key in valid_data:
            # 如果尝试更新主键，从数据中移除
            valid_data.pop(self.primary_key, None)
        
        if not valid_data:
            logger.warning("没有有效的数据可更新")
            return False
        
        # 构建UPDATE语句
        set_clauses = []
        params = []
        for key, value in valid_data.items():
            set_clauses.append(f"{key} = %s")
            params.append(value)
        
        # 添加主键到参数列表末尾
        params.append(pk_value)
        
        set_str = ", ".join(set_clauses)
        query = f"UPDATE {self._safe_table_name()} SET {set_str} WHERE {self.primary_key} = %s"
        
        try:
            affected_rows = self.db.execute_update(query, tuple(params))
            return affected_rows > 0
        except Exception as e:
            logger.error(f"更新记录失败: {e}")
            return False
    
    def delete(self, pk_value: Any) -> bool:
        """根据主键删除记录
        
        Args:
            pk_value: 主键值
            
        Returns:
            bool: 删除是否成功
        """
        query = f"DELETE FROM {self._safe_table_name()} WHERE {self.primary_key} = %s"
        
        try:
            affected_rows = self.db.execute_update(query, (pk_value,))
            return affected_rows > 0
        except Exception as e:
            logger.error(f"删除记录失败: {e}")
            return False
    
    def count(self, **kwargs) -> int:
        """统计符合条件的记录数量
        
        Args:
            **kwargs: 查询条件
            
        Returns:
            int: 记录数量
        """
        query = f"SELECT COUNT(*) as count FROM {self._safe_table_name()}"
        params = []
        
        if kwargs:
            # 构建WHERE子句
            where_clauses = []
            for key, value in kwargs.items():
                where_clauses.append(f"{key} = %s")
                params.append(value)
            
            where_str = " AND ".join(where_clauses)
            query += f" WHERE {where_str}"
        
        result = self.db.execute_query(query, tuple(params))
        return result[0]['count'] if result else 0
    
    def execute_query(self, query: str, params: Tuple = None) -> List[Dict[str, Any]]:
        """执行自定义SQL查询
        
        Args:
            query: SQL查询语句
            params: SQL参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        return self.db.execute_query(query, params)
    
    def execute_update(self, query: str, params: Tuple = None) -> int:
        """执行自定义SQL更新操作
        
        Args:
            query: SQL更新语句
            params: SQL参数
            
        Returns:
            int: 受影响的行数
        """
        return self.db.execute_update(query, params)