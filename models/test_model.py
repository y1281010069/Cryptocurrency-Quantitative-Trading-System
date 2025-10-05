#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试生成的模型是否正常工作"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import order_model
from models import db_connection
from loguru import logger


if __name__ == "__main__":
    try:
        # 初始化数据库连接
        db = db_connection.DBConnection()
        logger.info(f"数据库连接状态: {'已连接' if db.db else '未连接'}")
        
        if not db.db:
            logger.error("无法连接到数据库，测试失败")
            sys.exit(1)
        
        # 测试order模型是否可以正常使用（MySQL关键字表名）
        logger.info("测试order表模型...")
        order_count = order_model.count()
        logger.info(f"order表记录数: {order_count}")
        
        # 测试其他模型
        from models import factor_config_model
        factor_config_count = factor_config_model.count()
        logger.info(f"factor_config表记录数: {factor_config_count}")
        
        logger.info("所有模型测试成功！")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        sys.exit(1)
    finally:
        # 关闭数据库连接
        db_connection.close_db()
        logger.info("数据库连接已关闭")