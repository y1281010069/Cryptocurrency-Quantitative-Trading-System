import pandas as pd


def calculate_trend_indicators_and_score(df: pd.DataFrame, current_price, timeframe):
    """计算技术指标并计算趋势评分（SMA版本）
    
    Args:
        df: 包含价格数据的DataFrame
        current_price: 当前价格，用于处理数据不足的情况
        timeframe: 时间框架
        
    Returns:
        int: 趋势评分
    """
    # 计算技术指标
    sma_20 = df['close'].rolling(20).mean().iloc[-1]
    sma_50 = df['close'].rolling(50).mean() if len(df) >= 50 else pd.Series([current_price])
    sma_50 = sma_50.iloc[-1] if not sma_50.empty else current_price
    
    # 计算趋势评分
    score = 0
    if (timeframe != "15m"):
        if current_price > sma_20 > sma_50:
            score += 2
        elif current_price > sma_20:
            score += 1
        elif current_price < sma_20 < sma_50:
            score -= 2
        elif current_price < sma_20:
            score -= 1
    
    return score


def calculate_ema_trend_indicators_and_score(df: pd.DataFrame, current_price, timeframe):
    """计算技术指标并计算趋势评分（EMA版本）
    
    Args:
        df: 包含价格数据的DataFrame
        current_price: 当前价格，用于处理数据不足的情况
        timeframe: 时间框架
        
    Returns:
        int: 趋势评分
    """
    # 计算技术指标 - 使用EMA代替SMA
    ema_20 = df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema_50 = df['close'].ewm(span=50, adjust=False).mean() if len(df) >= 50 else pd.Series([current_price])
    ema_50 = ema_50.iloc[-1] if not ema_50.empty else current_price
    
    # 计算趋势评分
    score = 0
    if (timeframe != "15m"):
        if current_price > ema_20 > ema_50:
            score += 2
        elif current_price > ema_20:
            score += 1
        elif current_price < ema_20 < ema_50:
            score -= 2
        elif current_price < ema_20:
            score -= 1
    
    return score


def calculate_rsi_score(df: pd.DataFrame, timeframe):
    """计算RSI指标并返回RSI评分
    
    Args:
        df: 包含价格数据的DataFrame
        timeframe: 时间框架
        
    Returns:
        int: RSI评分
    """
    # 计算RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi_series = 100 - (100 / (1 + rs))
    rsi_value = rsi_series.iloc[-1]
    
    # 计算RSI评分
    score = 0
    # 其他时间框架保持原有逻辑
    if rsi_value < 30:
        score += 2  # 超卖
    elif rsi_value > 70:
        score -= 2  # 超买
    
    return score

def calculate_rsi_crossover_score(df: pd.DataFrame):
    """计算RSI交叉评分（专用于15m时间框架）
    
    Args:
        df: 包含价格数据的DataFrame
        
    Returns:
        int: RSI交叉评分
    """
    # 计算RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
    rs = gain / loss
    rsi_series = 100 - (100 / (1 + rs))
    
    # 15分钟时间框架特殊处理 - 交叉分析
    score = 0
    if len(rsi_series) >= 2:
        rsi_value = rsi_series.iloc[-1]
        prev_rsi = rsi_series.iloc[-2]
        if prev_rsi < 30 and rsi_value > 30:
            score += 2  # 前一根k小于30，当前k大于30 +2分
        elif prev_rsi > 70 and rsi_value < 70:
            score -= 2  # 前一根k大于70，当前k小于70 -2分
    
    return score


def calculate_volume_score(df: pd.DataFrame):
    """计算成交量评分
    
    Args:
        df: 包含价格数据的DataFrame
        
    Returns:
        int: 成交量评分
    """
    volume_avg = df['volume'].rolling(20).mean().iloc[-1]
    volume_current = df['volume'].iloc[-1]
    volume_ratio = volume_current / volume_avg if volume_avg > 0 else 1
    
    # 根据成交量比率计算评分
    score = 0
    if volume_ratio > 1.5:
        score += 1  # 成交量明显放大
    elif volume_ratio < 0.5:
        score -= 1  # 成交量明显萎缩
    
    return score