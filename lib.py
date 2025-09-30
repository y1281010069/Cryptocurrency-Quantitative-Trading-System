import numpy as np

def calculate_atr(df, period=14):
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