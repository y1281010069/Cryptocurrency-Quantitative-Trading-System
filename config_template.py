# OKX API 配置文件模板
# 请复制此文件为 config.py 并填入您的实际API信息

import os

# 方式1: 直接在此文件中填写（不推荐，仅用于测试）
# API_KEY = "your_api_key_here"
# SECRET_KEY = "your_secret_key_here" 
# PASSPHRASE = "your_passphrase_here"

# 方式2: 从环境变量读取（推荐）
API_KEY = os.getenv('OKX_API_KEY', '')
SECRET_KEY = os.getenv('OKX_SECRET_KEY', '')
PASSPHRASE = os.getenv('OKX_PASSPHRASE', '')

# OKX 交易所配置
OKX_CONFIG = {
    'api_key': API_KEY,
    'secret': SECRET_KEY,
    'passphrase': PASSPHRASE,
    'sandbox': False,  # True=测试环境, False=正式环境
    'timeout': 30000,
}

# 验证配置
def validate_config():
    """验证API配置是否完整"""
    if not all([API_KEY, SECRET_KEY, PASSPHRASE]):
        raise ValueError(
            "API配置不完整! 请确保已设置以下环境变量:\n"
            "- OKX_API_KEY\n"
            "- OKX_SECRET_KEY\n" 
            "- OKX_PASSPHRASE\n"
            "或者直接在config.py文件中填写API信息"
        )
    return True

# 交易信号配置
TRADING_CONFIG = {
    # 交易信号评分阈值
    'BUY_THRESHOLD': 0.6,     # 买入信号评分阈值（大于等于）
    'SELL_THRESHOLD': -0.6,   # 卖出信号评分阈值（小于等于）
    
    # ATR配置
    'ATR_PERIOD': 14,         # ATR计算周期
    'TARGET_MULTIPLIER': 1.5, # 目标价格ATR倍数
    'STOP_LOSS_MULTIPLIER': 1.0, # 止损价格ATR倍数
    
    # 币种过滤配置
    'ENABLED_SYMBOLS': [],    # 启用的币种列表，为空时表示全部启用
    'DISABLED_SYMBOLS': [],    # 禁用的币种列表，优先级高于ENABLED_SYMBOLS
    
    # 时间框架过滤配置
    'FILTER_BY_15M': False,   # 是否根据15分钟时间框架过滤买入信号
    'FILTER_BY_1H': False,    # 是否根据1小时时间框架过滤买入信号
    
    # 持仓控制配置
    'MAX_POSITIONS': 10       # 最大持仓数量限制，超过此数量将放弃新的交易机会
}

if __name__ == "__main__":
    try:
        validate_config()
        print("✅ API配置验证成功!")
    except ValueError as e:
        print(f"❌ {e}")