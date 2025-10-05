#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
mechanism_copy1 表模型类
"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
mechanism_copy1 表模型类
"""
import os
import sys

# 添加当前目录到Python路径以便直接运行脚本
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 尝试相对导入，如果失败则使用绝对导入
try:
    from .base_model import BaseModel
except ImportError:
    from base_model import BaseModel


class MechanismCopy1(BaseModel):
    """mechanism_copy1 表模型"""
    
    table_name = "mechanism_copy1"
    primary_key = "id"
    
    # 表字段信息
    # id: int (NOT NULL) (PRIMARY KEY)
    # name: varchar(255) DEFAULT 
    # url: varchar(255) DEFAULT 
    # ws_url: varchar(255) DEFAULT 
    # access_Key: varchar(255) DEFAULT 
    # secret_Key: varchar(255) DEFAULT 
    # passphrase: varchar(255)
    # remark: varchar(255) DEFAULT for account
    # follow_multiple: decimal(10,2) DEFAULT 0.00
    # tx_money: decimal(10,2) DEFAULT 0.00

    def __init__(self, db_conn=None):
        """初始化模型
        
        Args:
            db_conn: 数据库连接对象, 如果为None则使用全局的db实例
        """
        super().__init__(db_conn)


# 创建模型实例供全局使用
mechanism_copy1_model = MechanismCopy1()