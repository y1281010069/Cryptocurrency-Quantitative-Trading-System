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

def calculate_bollinger_band_signal_score(df: pd.DataFrame):
    """计算布林带信号评分
    
    根据布林带宽度走平或缩窄的前提条件，判断做多和做空信号
    正值表示看涨信号，负值表示看跌信号
    
    Args:
        df: 包含价格数据的DataFrame
        
    Returns:
        int: 布林带信号评分，正值表示看涨，负值表示看跌
    """
    # 确保数据足够
    if len(df) < 50:
        return 0
    
    # 计算布林带（使用20日移动平均和2倍标准差）
    window = 20
    df['sma'] = df['close'].rolling(window=window).mean()
    df['std'] = df['close'].rolling(window=window).std()
    df['upper_band'] = df['sma'] + 2 * df['std']
    df['lower_band'] = df['sma'] - 2 * df['std']
    df['band_width'] = df['upper_band'] - df['lower_band']
    df['band_width_pct'] = df['band_width'] / df['sma'] * 100
    
    # 判断布林带宽度是否走平或缩窄
    # 计算带宽变化趋势（最近10天的带宽均值与前10天的带宽均值比较）
    recent_band_width_avg = df['band_width_pct'].iloc[-10:].mean()
    previous_band_width_avg = df['band_width_pct'].iloc[-20:-10].mean()
    
    # 带宽走平或缩窄的条件
    is_band_width_flat_or_narrowing = recent_band_width_avg <= previous_band_width_avg * 1.05
    
    if not is_band_width_flat_or_narrowing:
        return 0
    
    # 获取最新价格和布林带值
    current_price = df['close'].iloc[-1]
    upper_band = df['upper_band'].iloc[-1]
    lower_band = df['lower_band'].iloc[-1]
    sma = df['sma'].iloc[-1]
    
    # 计算价格与布林带的距离百分比
    distance_to_upper = (current_price - upper_band) / sma * 100
    distance_to_lower = (lower_band - current_price) / sma * 100
    
    # 计算RSI用于指标配合判断
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi_series = 100 - (100 / (1 + rs))
    current_rsi = rsi_series.iloc[-1]
    prev_rsi = rsi_series.iloc[-2] if len(rsi_series) >= 2 else current_rsi
    
    # 计算KDJ指标（简化版，使用RSV和随机指标）
    n = 9
    df['low_n'] = df['low'].rolling(window=n).min()
    df['high_n'] = df['high'].rolling(window=n).max()
    df['rsv'] = (df['close'] - df['low_n']) / (df['high_n'] - df['low_n']) * 100
    df['k'] = df['rsv'].ewm(com=2, adjust=False).mean()
    df['d'] = df['k'].ewm(com=2, adjust=False).mean()
    
    current_k = df['k'].iloc[-1]
    current_d = df['d'].iloc[-1]
    prev_k = df['k'].iloc[-2] if len(df) >= 2 else current_k
    prev_d = df['d'].iloc[-2] if len(df) >= 2 else current_d
    
    # 判断KDJ金叉（K线上穿D线）和死叉（K线下穿D线）
    is_kdj_gold_cross = prev_k < prev_d and current_k > current_d
    is_kdj_death_cross = prev_k > prev_d and current_k < current_d
    
    # 检查看涨反转K线（锤子线、小阳线包孕阴线）
    def is_bullish_reversal_candle(i):
        if i < 1 or i >= len(df):
            return False
        
        current = df.iloc[i]
        previous = df.iloc[i-1]
        
        # 锤子线判断
        body = abs(current['close'] - current['open'])
        lower_shadow = min(current['close'], current['open']) - current['low']
        is_hammer = lower_shadow > body * 2 and body < current['high'] - max(current['close'], current['open'])
        
        # 小阳线包孕阴线
        is_bullish_engulfing = (previous['close'] < previous['open'] and  # 前一天阴线
                               current['close'] > current['open'] and    # 当天阳线
                               current['close'] > previous['open'] and    # 阳线收盘价高于前一天开盘价
                               current['open'] < previous['close'])        # 阳线开盘价低于前一天收盘价
        
        return is_hammer or is_bullish_engulfing
    
    # 检查看跌反转K线（流星线、小阴线包孕阳线）
    def is_bearish_reversal_candle(i):
        if i < 1 or i >= len(df):
            return False
        
        current = df.iloc[i]
        previous = df.iloc[i-1]
        
        # 流星线判断
        body = abs(current['close'] - current['open'])
        upper_shadow = current['high'] - max(current['close'], current['open'])
        is_shooting_star = upper_shadow > body * 2 and body < min(current['close'], current['open']) - current['low']
        
        # 小阴线包孕阳线
        is_bearish_engulfing = (previous['close'] > previous['open'] and  # 前一天阳线
                                current['close'] < current['open'] and    # 当天阴线
                                current['close'] < previous['open'] and    # 阴线收盘价低于前一天开盘价
                                current['open'] > previous['close'])        # 阴线开盘价高于前一天收盘价
        
        return is_shooting_star or is_bearish_engulfing
    
    # 1. 做多信号判断（价格靠近下轨时）
    if distance_to_lower >= -1 and distance_to_lower <= 1:  # 价格靠近下轨
        # 第一步：检查是否未有效跌破下轨
        # 检查最近3根K线收盘价是否都在轨道内，或跌破后快速收回
        valid_below_lower = True
        break_and_recover = False
        
        # 检查最近3根K线
        for i in range(1, min(4, len(df))):
            idx = -i
            if df['close'].iloc[idx] < df['lower_band'].iloc[idx]:
                # 如果有K线收盘价跌破下轨，检查之后是否快速收回
                if i > 1 and df['close'].iloc[idx+1] > df['lower_band'].iloc[idx+1]:
                    break_and_recover = True
                else:
                    valid_below_lower = False
        
        if not valid_below_lower and not break_and_recover:
            return 0
        
        # 第二步：看指标配合
        indicator_score = 0
        if current_rsi < 30:  # RSI超卖
            indicator_score += 3
        elif is_kdj_gold_cross:  # KDJ金叉
            indicator_score += 2
        elif current_rsi < 40 and current_rsi > prev_rsi:  # RSI开始回升
            indicator_score += 1
        
        if indicator_score == 0:
            return 0
        
        # 第三步：等K线确认
        pattern_score = 0
        if is_bullish_reversal_candle(-1):  # 最近一根K线是看涨反转
            pattern_score += 3
        elif is_bullish_reversal_candle(-2):  # 前一根K线是看涨反转
            pattern_score += 2
        
        # 综合评分
        total_score = indicator_score + pattern_score
        if total_score >= 3:  # 信号强度足够
            return total_score
    
    # 2. 做空信号判断（价格靠近上轨时）
    elif distance_to_upper <= 1 and distance_to_upper >= -1:  # 价格靠近上轨
        # 第一步：检查是否未有效突破上轨
        # 检查最近3根K线收盘价是否都在轨道内，或突破后快速回落
        valid_above_upper = True
        break_and_reverse = False
        
        # 检查最近3根K线
        for i in range(1, min(4, len(df))):
            idx = -i
            if df['close'].iloc[idx] > df['upper_band'].iloc[idx]:
                # 如果有K线收盘价突破上轨，检查之后是否快速回落
                if i > 1 and df['close'].iloc[idx+1] < df['upper_band'].iloc[idx+1]:
                    break_and_reverse = True
                else:
                    valid_above_upper = False
        
        if not valid_above_upper and not break_and_reverse:
            return 0
        
        # 第二步：看指标配合
        indicator_score = 0
        if current_rsi > 70:  # RSI超买
            indicator_score += 3
        elif is_kdj_death_cross:  # KDJ死叉
            indicator_score += 2
        elif current_rsi > 60 and current_rsi < prev_rsi:  # RSI开始回落
            indicator_score += 1
        
        if indicator_score == 0:
            return 0
        
        # 第三步：等K线确认
        pattern_score = 0
        if is_bearish_reversal_candle(-1):  # 最近一根K线是看跌反转
            pattern_score += 3
        elif is_bearish_reversal_candle(-2):  # 前一根K线是看跌反转
            pattern_score += 2
        
        # 综合评分（做空信号为负值）
        total_score = indicator_score + pattern_score
        if total_score >= 3:  # 信号强度足够
            return -total_score
    
    # 无明显信号
    return 0

def calculate_rsi_divergence_score(df: pd.DataFrame):
    """计算RSI背离评分
    
    根据价格与RSI指标的背离情况进行评分，包括顶背离（看跌）和底背离（看涨）
    正值表示看涨信号（底背离），负值表示看跌信号（顶背离）
    
    Args:
        df: 包含价格数据的DataFrame
        
    Returns:
        int: 背离信号评分，正值表示看涨，负值表示看跌
    """
    # 确保数据足够
    if len(df) < 50:
        return 0
    
    # 计算RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi_series = 100 - (100 / (1 + rs))
    
    # 获取最新价格和RSI
    current_price = df['close'].iloc[-1]
    current_rsi = rsi_series.iloc[-1]
    
    # 寻找最近的高点和低点
    # 价格高点和对应的RSI
    price_highs = []
    rsi_highs = []
    # 价格低点和对应的RSI
    price_lows = []
    rsi_lows = []
    
    # 分析最近50个交易日的数据
    lookback_period = min(50, len(df))
    
    # 寻找价格高点和低点
    for i in range(lookback_period - 1):
        idx = len(df) - lookback_period + i
        # 高点检测
        if (idx > 0 and idx < len(df) - 1 and 
            df['high'].iloc[idx] > df['high'].iloc[idx - 1] and 
            df['high'].iloc[idx] > df['high'].iloc[idx + 1]):
            price_highs.append((idx, df['high'].iloc[idx]))
            rsi_highs.append((idx, rsi_series.iloc[idx]))
        
        # 低点检测
        if (idx > 0 and idx < len(df) - 1 and 
            df['low'].iloc[idx] < df['low'].iloc[idx - 1] and 
            df['low'].iloc[idx] < df['low'].iloc[idx + 1]):
            price_lows.append((idx, df['low'].iloc[idx]))
            rsi_lows.append((idx, rsi_series.iloc[idx]))
    
    # 检查顶背离（看跌）
    if len(price_highs) >= 2 and len(rsi_highs) >= 2:
        # 按索引排序，取最近的两个高点
        price_highs.sort(key=lambda x: x[0], reverse=True)
        rsi_highs.sort(key=lambda x: x[0], reverse=True)
        
        # 确保高点匹配
        recent_price_high_idx, recent_price_high = price_highs[0]
        prev_price_high_idx, prev_price_high = price_highs[1]
        
        # 找到对应RSI高点
        recent_rsi_high = None
        prev_rsi_high = None
        
        for idx, rsi in rsi_highs:
            if not recent_rsi_high and idx <= recent_price_high_idx + 2 and idx >= recent_price_high_idx - 2:
                recent_rsi_high = rsi
            elif not prev_rsi_high and idx <= prev_price_high_idx + 2 and idx >= prev_price_high_idx - 2:
                prev_rsi_high = rsi
            if recent_rsi_high and prev_rsi_high:
                break
        
        # 顶背离条件：价格创新高，但RSI未创新高
        if recent_rsi_high and prev_rsi_high and recent_price_high > prev_price_high and recent_rsi_high < prev_rsi_high:
            score = 0
            
            # 辅助条件：RSI处于超买区
            if recent_rsi_high > 70:
                score += 2
            
            # 辅助条件：成交量萎缩
            recent_volume = df['volume'].iloc[recent_price_high_idx]
            volume_avg = df['volume'].rolling(20).mean().iloc[recent_price_high_idx]
            if volume_avg > 0 and recent_volume / volume_avg < 0.8:
                score += 1
            
            # 检查确认信号：看跌反转K线模式（简化版）
            if recent_price_high_idx < len(df) - 1:
                # 检查是否有流星线或类似看跌反转模式
                candle_body = abs(df['close'].iloc[recent_price_high_idx] - df['open'].iloc[recent_price_high_idx])
                upper_shadow = df['high'].iloc[recent_price_high_idx] - max(df['close'].iloc[recent_price_high_idx], df['open'].iloc[recent_price_high_idx])
                # 上影线较长的K线
                if upper_shadow > candle_body * 2:
                    score += 2
                
                # 后续K线收盘价低于反转K线最低价
                if df['close'].iloc[recent_price_high_idx + 1] < df['low'].iloc[recent_price_high_idx]:
                    score += 3
            
            if score >= 3:  # 至少有一定强度的信号
                return -score
    
    # 检查底背离（看涨）
    if len(price_lows) >= 2 and len(rsi_lows) >= 2:
        # 按索引排序，取最近的两个低点
        price_lows.sort(key=lambda x: x[0], reverse=True)
        rsi_lows.sort(key=lambda x: x[0], reverse=True)
        
        # 确保低点匹配
        recent_price_low_idx, recent_price_low = price_lows[0]
        prev_price_low_idx, prev_price_low = price_lows[1]
        
        # 找到对应RSI低点
        recent_rsi_low = None
        prev_rsi_low = None
        
        for idx, rsi in rsi_lows:
            if not recent_rsi_low and idx <= recent_price_low_idx + 2 and idx >= recent_price_low_idx - 2:
                recent_rsi_low = rsi
            elif not prev_rsi_low and idx <= prev_price_low_idx + 2 and idx >= prev_price_low_idx - 2:
                prev_rsi_low = rsi
            if recent_rsi_low and prev_rsi_low:
                break
        
        # 底背离条件：价格创新低，但RSI未创新低
        if recent_rsi_low and prev_rsi_low and recent_price_low < prev_price_low and recent_rsi_low > prev_rsi_low:
            score = 0
            
            # 辅助条件：RSI处于超卖区
            if recent_rsi_low < 30:
                score += 2
            
            # 辅助条件：成交量开始放大
            recent_volume = df['volume'].iloc[recent_price_low_idx]
            prev_volume = df['volume'].iloc[prev_price_low_idx]
            if prev_volume > 0 and recent_volume > prev_volume * 1.2:
                score += 1
            
            # 检查确认信号：看涨反转K线模式（简化版）
            if recent_price_low_idx < len(df) - 1:
                # 检查是否有锤子线或类似看涨反转模式
                candle_body = abs(df['close'].iloc[recent_price_low_idx] - df['open'].iloc[recent_price_low_idx])
                lower_shadow = min(df['close'].iloc[recent_price_low_idx], df['open'].iloc[recent_price_low_idx]) - df['low'].iloc[recent_price_low_idx]
                # 下影线较长的K线
                if lower_shadow > candle_body * 2:
                    score += 2
                
                # 后续K线收盘价高于反转K线最高价
                if df['close'].iloc[recent_price_low_idx + 1] > df['high'].iloc[recent_price_low_idx]:
                    score += 3
            
            if score >= 3:  # 至少有一定强度的信号
                return score
    
    # 无明显背离
    return 0