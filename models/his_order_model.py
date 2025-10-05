#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
his_order 表模型类
"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
his_order 表模型类
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


class HisOrder(BaseModel):
    """his_order 表模型"""
    
    table_name = "his_order"
    primary_key = "id"
    
    # 表字段信息
    # id: int (NOT NULL) (PRIMARY KEY)
    # variety_id: int (NOT NULL)
    # status: tinyint(1) (NOT NULL) DEFAULT 0
    # cost_open: decimal(20,10) (NOT NULL)
    # cost_close: decimal(20,10) (NOT NULL) DEFAULT 0.0000000000
    # max_price: decimal(20,10) (NOT NULL)
    # min_price: decimal(20,10) (NOT NULL)
    # volume: decimal(20,10) (NOT NULL)
    # open_order: varchar(100) (NOT NULL) DEFAULT 
    # colse_order: varchar(100) (NOT NULL) DEFAULT 
    # order_no: varchar(100) (NOT NULL)
    # stop_win_price: decimal(20,10) (NOT NULL) DEFAULT 0.0000000000
    # stop_loss_price: decimal(20,10) (NOT NULL) DEFAULT 0.0000000000
    # direction: varchar(10) (NOT NULL)
    # factor_name: varchar(20) (NOT NULL) DEFAULT 
    # creat_time: datetime (NOT NULL) DEFAULT CURRENT_TIMESTAMP
    # update_time: datetime (NOT NULL) DEFAULT CURRENT_TIMESTAMP
    # stopArr: text (NOT NULL)

    def __init__(self, db_conn=None):
        """初始化模型
        
        Args:
            db_conn: 数据库连接对象, 如果为None则使用全局的db实例
        """
        super().__init__(db_conn)


# 创建模型实例供全局使用
his_order_model = HisOrder()