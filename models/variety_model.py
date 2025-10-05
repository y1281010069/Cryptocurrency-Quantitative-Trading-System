#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
variety 表模型类
"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
variety 表模型类
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


class Variety(BaseModel):
    """variety 表模型"""
    
    table_name = "variety"
    primary_key = "id"
    
    # 表字段信息
    # id: int (NOT NULL) (PRIMARY KEY)
    # name: varchar(255) (NOT NULL)
    # mechanism: int (NOT NULL) DEFAULT 0
    # pricePrecision: int (NOT NULL)
    # open: int (NOT NULL) DEFAULT 0
    # tradeOpen: tinyint(1) (NOT NULL) DEFAULT 0
    # statusJson: text (NOT NULL)
    # onboardDate: bigint (NOT NULL) DEFAULT 0
    # lastFundingRate: decimal(10,9) (NOT NULL) DEFAULT 0.000000000
    # nextFundingTime: bigint (NOT NULL)
    # quantityPrecision: decimal(10,6) (NOT NULL)
    # maxQty: decimal(20,6) (NOT NULL)
    # minQty: decimal(20,6) (NOT NULL)
    # stepSize: decimal(20,6) (NOT NULL)
    # minSz: decimal(40,20) (NOT NULL)

    def __init__(self, db_conn=None):
        """初始化模型
        
        Args:
            db_conn: 数据库连接对象, 如果为None则使用全局的db实例
        """
        super().__init__(db_conn)


# 创建模型实例供全局使用
variety_model = Variety()