import pandas as pd
import numpy as np
import sys
import os

# 添加项目根目录到路径，以便导入策略模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.condition_analyzer import calculate_trend_indicators_and_score, calculate_ema_trend_indicators_and_score

def generate_test_data(trend='up', length=100):
    """生成测试数据
    
    Args:
        trend: 趋势方向 ('up', 'down', 'sideways')
        length: 数据长度
    
    Returns:
        DataFrame: 包含close和volume列的DataFrame
    """
    np.random.seed(42)  # 设置随机种子以获得可重复结果
    
    # 基础价格序列
    base_price = 50000.0
    
    if trend == 'up':
        # 上升趋势
        price_series = base_price + np.arange(length) * 100 + np.random.normal(0, 200, length)
    elif trend == 'down':
        # 下降趋势
        price_series = base_price - np.arange(length) * 100 + np.random.normal(0, 200, length)
    else:
        # 横盘趋势
        price_series = base_price + np.random.normal(0, 300, length)
    
    # 生成成交量数据
    volume_series = np.random.normal(1000000, 200000, length)
    volume_series = np.maximum(volume_series, 0)  # 确保成交量不为负
    
    # 创建DataFrame
    df = pd.DataFrame({
        'close': price_series,
        'volume': volume_series
    })
    
    return df

def test_indicators_comparison():
    """比较SMA和EMA版本的指标计算结果"""
    print("=== 测试SMA和EMA趋势指标计算函数 ===")
    
    # 测试不同趋势
    trends = ['up', 'down', 'sideways']
    timeframes = ['4h', '1h', '15m']
    
    for trend in trends:
        print(f"\n测试{trend}趋势数据:")
        df = generate_test_data(trend=trend)
        current_price = df['close'].iloc[-1]
        
        for timeframe in timeframes:
            # 计算SMA评分
            sma_score = calculate_trend_indicators_and_score(df, current_price, timeframe)
            
            # 计算EMA评分
            ema_score = calculate_ema_trend_indicators_and_score(df, current_price, timeframe)
            
            print(f"  时间框架: {timeframe}")
            print(f"    SMA评分: {sma_score}")
            print(f"    EMA评分: {ema_score}")
            
            # 对于15分钟时间框架，评分应为0
            if timeframe == "15m":
                assert sma_score == 0, f"15m时间框架SMA评分应为0，实际为{sma_score}"
                assert ema_score == 0, f"15m时间框架EMA评分应为0，实际为{ema_score}"
                print("    ✓ 15m时间框架评分正确为0")

if __name__ == "__main__":
    test_indicators_comparison()
    print("\n测试完成！")