import numpy as np

# 尝试导入配置文件，如果不存在则使用默认值
try:
    from config import TRADING_CONFIG
except ImportError:
    # 使用默认配置
    TRADING_CONFIG = {
        'ATR_PERIOD': 14
    }

def calculate_atr(df, period=None):
    # 如果没有提供period参数，使用配置中的值
    if period is None:
        period = TRADING_CONFIG['ATR_PERIOD']
    """计算ATR值（平均真实波动幅度）"""
    # 计算真实波动幅度
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    # 计算ATR (TR的N日移动平均线)
    df['atr'] = df['tr'].rolling(window=period).mean()
    return df['atr'].iloc[-1] if len(df) >= period else 0.0