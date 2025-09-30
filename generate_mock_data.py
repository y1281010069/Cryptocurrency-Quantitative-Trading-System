import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# 创建模拟数据函数
def generate_mock_data(symbol, current_price, days=5):
    # 计算数据点数
    total_points = days * 24 * 4  # 15分钟数据
    dates = [datetime.now() - timedelta(minutes=15*i) for i in range(total_points)]  # 15分钟数据
    dates.reverse()
    
    # 生成OHLCV数据，确保所有数组长度一致
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []
    volumes = []
    
    current_open = current_price
    for _ in range(total_points):
        change = random.uniform(-0.02, 0.02) * current_open
        close = current_open + change
        
        high = max(current_open, close) * (1 + random.uniform(0, 0.01))
        low = min(current_open, close) * (1 - random.uniform(0, 0.01))
        volume = random.uniform(100000, 5000000)
        
        open_prices.append(current_open)
        high_prices.append(high)
        low_prices.append(low)
        close_prices.append(close)
        volumes.append(volume)
        
        # 下一个开盘价等于当前收盘价
        current_open = close
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    })
    
    return df

# 创建一个模拟的multi_timeframe_analysis_new.txt文件
output_dir = 'multi_timeframe_reports'
os.makedirs(output_dir, exist_ok=True)
filename = os.path.join(output_dir, 'multi_timeframe_analysis_new.txt')

# 生成一些模拟交易对的数据
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT']
current_prices = [42000, 2200, 80, 0.5, 7]
actions = ['买入', '卖出', '买入', '观望', '买入']
confidences = ['高', '中', '高', '低', '中']
scores = [0.8, -0.6, 0.7, 0.05, 0.5]

with open(filename, 'w', encoding='utf-8') as f:
    f.write("=" * 100 + "\n")
    f.write("🎯 多时间框架专业投资分析报告\n")
    f.write("=" * 100 + "\n")
    f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"分析维度: 周线→日线→4小时→1小时→15分钟\n")
    f.write(f"发现机会: {len(symbols)} 个\n")
    f.write("=" * 100 + "\n\n")
    
    for i, (symbol, price, action, conf, score) in enumerate(zip(symbols, current_prices, actions, confidences, scores), 1):
        # 计算ATR值
        df = generate_mock_data(symbol, price)
        # 计算TR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        atr = df['tr'].rolling(window=14).mean().iloc[-1]
        
        # 计算一倍ATR值
        if action == "买入":
            # 一倍ATR = 当前价格 + ATR值
            art_one = price + atr
            # 1.5倍ATR作为短期目标
            target_short = price + 1.5 * atr
            # 使用1倍ATR的反向价格作为止损价格
            stop_loss = price - atr
        elif action == "卖出":
            # 一倍ATR = 当前价格 - ATR值
            art_one = price - atr
            # 1.5倍ATR作为短期目标
            target_short = price - 1.5 * atr
            # 使用1倍ATR的反向价格作为止损价格
            stop_loss = price + atr
        else:
            art_one = price
            target_short = price
            stop_loss = price * 0.98
        
        # 移除中期和长期目标
        target_medium = 0.0
        target_long = 0.0
        
        f.write(f"【机会 {i}】 {symbol}\n")
        f.write("-" * 80 + "\n")
        f.write(f"综合建议: {action}\n")
        f.write(f"信心等级: {conf}\n")
        f.write(f"总评分: {score:.3f}\n")
        f.write(f"当前价格: {price:.6f} USDT\n\n")
        
        f.write("多时间框架分析:\n")
        f.write(f"  周线趋势: {'买入' if random.random() > 0.5 else '观望'}\n")
        f.write(f"  日线趋势: {'买入' if random.random() > 0.5 else '观望'}\n")
        f.write(f"  4小时信号: {'买入' if random.random() > 0.5 else '观望'}\n")
        f.write(f"  1小时信号: {'买入' if random.random() > 0.5 else '观望'}\n")
        f.write(f"  15分钟信号: {'买入' if random.random() > 0.5 else '观望'}\n\n")
        
        f.write("目标价格:\n")
        f.write(f"  短期目标: {target_short:.6f} USDT\n")
        f.write(f"  止损价格: {stop_loss:.6f} USDT\n\n")
        
        f.write(f"分析依据: 周线:{'买入' if random.random() > 0.5 else '观望'}, 日线:{'买入' if random.random() > 0.5 else '观望'}, 4H:{'买入' if random.random() > 0.5 else '观望'}\n")
        f.write("\n" + "=" * 100 + "\n\n")
    
    f.write("⚠️ 投资建议:\n")
    f.write("• 多时间框架分析提供全面视角，建议结合基本面分析\n")
    f.write("• 长期投资关注周线和日线趋势\n")
    f.write("• 日内交易重点关注1小时和15分钟信号\n")
    f.write("• 严格执行止损，控制风险\n")

print(f"✅ 已生成模拟数据文件: {filename}")
print(f"文件包含 {len(symbols)} 个交易对的分析数据，其中包含正确计算的一倍ATR值。")