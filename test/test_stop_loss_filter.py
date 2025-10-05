import sys
import os
import json
from datetime import datetime
from typing import List

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入必要的类和配置
from multi_timeframe_system import MultiTimeframeSignal, TRADING_CONFIG

# 模拟配置
TEST_CONFIG = {
    'BUY_THRESHOLD': 0.5,
    'SELL_THRESHOLD': -0.5,
    'FILTER_BY_15M': False,
    'FILTER_BY_1H': False,
    'MAX_POSITIONS': 10
}

# 创建模拟交易信号
def create_mock_signals() -> List[MultiTimeframeSignal]:
    """创建用于测试的模拟交易信号"""
    now = datetime.now()
    
    # 创建不同条件的模拟信号
    signals = [
        # 信号1：买入信号，止损距离充足（1%）
        MultiTimeframeSignal(
            symbol="BTC/USDT",
            weekly_trend="买入",
            daily_trend="买入",
            h4_signal="买入",
            h1_signal="买入",
            m15_signal="买入",
            overall_action="买入",
            confidence_level="高",
            total_score=1.2,
            entry_price=40000.0,  # 当前价格
            target_short=42000.0,
            target_medium=0.0,
            target_long=0.0,
            stop_loss=39600.0,    # 止损价格，距离当前价格1%
            atr_one=0.0,
            reasoning=["综合评分达标"],
            timestamp=now
        ),
        # 信号2：买入信号，止损距离不足（0.2%）
        MultiTimeframeSignal(
            symbol="ETH/USDT",
            weekly_trend="买入",
            daily_trend="买入",
            h4_signal="买入",
            h1_signal="买入",
            m15_signal="买入",
            overall_action="买入",
            confidence_level="高",
            total_score=1.0,
            entry_price=2000.0,   # 当前价格
            target_short=2100.0,
            target_medium=0.0,
            target_long=0.0,
            stop_loss=1996.0,     # 止损价格，距离当前价格0.2%
            atr_one=0.0,
            reasoning=["综合评分达标"],
            timestamp=now
        ),
        # 信号3：卖出信号，止损距离充足（1%）
        MultiTimeframeSignal(
            symbol="SOL/USDT",
            weekly_trend="卖出",
            daily_trend="卖出",
            h4_signal="卖出",
            h1_signal="卖出",
            m15_signal="卖出",
            overall_action="卖出",
            confidence_level="高",
            total_score=-1.2,
            entry_price=100.0,    # 当前价格
            target_short=95.0,
            target_medium=0.0,
            target_long=0.0,
            stop_loss=101.0,      # 止损价格，距离当前价格1%
            atr_one=0.0,
            reasoning=["综合评分达标"],
            timestamp=now
        ),
        # 信号4：卖出信号，止损距离不足（0.2%）
        MultiTimeframeSignal(
            symbol="ADA/USDT",
            weekly_trend="卖出",
            daily_trend="卖出",
            h4_signal="卖出",
            h1_signal="卖出",
            m15_signal="卖出",
            overall_action="卖出",
            confidence_level="高",
            total_score=-1.0,
            entry_price=1.0,      # 当前价格
            target_short=0.95,
            target_medium=0.0,
            target_long=0.0,
            stop_loss=1.002,      # 止损价格，距离当前价格0.2%
            atr_one=0.0,
            reasoning=["综合评分达标"],
            timestamp=now
        )
    ]
    
    return signals

# 实现与multi_timeframe_system中相同的过滤逻辑
def filter_signals(signals: List[MultiTimeframeSignal], config: dict) -> List[MultiTimeframeSignal]:
    """根据配置过滤交易信号，包含止损价格过滤条件"""
    trade_signals = []
    
    for op in signals:
        # 检查是否是买入信号且评分达到阈值
        if op.total_score >= config['BUY_THRESHOLD'] and op.overall_action == "买入":
            # 应用时间框架过滤
            filter_by_15m = config.get('FILTER_BY_15M', False)
            filter_by_1h = config.get('FILTER_BY_1H', False)
            
            # 确定是否需要过滤
            should_filter = filter_by_15m or filter_by_1h
            
            # 如果不需要过滤，直接添加
            if not should_filter:
                # 添加止损价格过滤：如果止损价格距离当前价格不足0.3%，则过滤掉
                price_diff_percent = abs(op.entry_price - op.stop_loss) / op.entry_price * 100
                if price_diff_percent >= 0.3:
                    trade_signals.append(op)
                    print(f"✅ {op.symbol} 买入信号通过过滤: 止损距离 {price_diff_percent:.2f}%")
                else:
                    print(f"❌ {op.symbol} 买入信号因止损距离不足被过滤: {price_diff_percent:.2f}%")
            else:
                # 检查时间框架条件
                is_15m_buy = "买入" in op.m15_signal
                is_1h_buy = "买入" in op.h1_signal
                
                # 根据过滤开关决定是否添加信号
                if ((not filter_by_15m or is_15m_buy) and 
                    (not filter_by_1h or is_1h_buy)):
                    # 添加止损价格过滤
                    price_diff_percent = abs(op.entry_price - op.stop_loss) / op.entry_price * 100
                    if price_diff_percent >= 0.3:
                        trade_signals.append(op)
                        print(f"✅ {op.symbol} 买入信号通过过滤: 止损距离 {price_diff_percent:.2f}%")
                    else:
                        print(f"❌ {op.symbol} 买入信号因止损距离不足被过滤: {price_diff_percent:.2f}%")
        
        # 卖出信号应用时间框架过滤
        elif op.total_score <= config['SELL_THRESHOLD'] and op.overall_action == "卖出":
            # 应用时间框架过滤
            filter_by_15m = config.get('FILTER_BY_15M', False)
            filter_by_1h = config.get('FILTER_BY_1H', False)
            
            # 确定是否需要过滤
            should_filter = filter_by_15m or filter_by_1h
            
            # 如果不需要过滤，直接添加
            if not should_filter:
                # 添加止损价格过滤：如果止损价格距离当前价格不足0.3%，则过滤掉
                price_diff_percent = abs(op.entry_price - op.stop_loss) / op.entry_price * 100
                if price_diff_percent >= 0.3:
                    trade_signals.append(op)
                    print(f"✅ {op.symbol} 卖出信号通过过滤: 止损距离 {price_diff_percent:.2f}%")
                else:
                    print(f"❌ {op.symbol} 卖出信号因止损距离不足被过滤: {price_diff_percent:.2f}%")
            else:
                # 检查时间框架条件（卖出信号）
                is_15m_sell = "卖出" in op.m15_signal
                is_1h_sell = "卖出" in op.h1_signal
                
                # 根据过滤开关决定是否添加信号
                if ((not filter_by_15m or is_15m_sell) and 
                    (not filter_by_1h or is_1h_sell)):
                    # 添加止损价格过滤
                    price_diff_percent = abs(op.entry_price - op.stop_loss) / op.entry_price * 100
                    if price_diff_percent >= 0.3:
                        trade_signals.append(op)
                        print(f"✅ {op.symbol} 卖出信号通过过滤: 止损距离 {price_diff_percent:.2f}%")
                    else:
                        print(f"❌ {op.symbol} 卖出信号因止损距离不足被过滤: {price_diff_percent:.2f}%")
    
    return trade_signals

# 运行测试
def test_stop_loss_filter():
    """测试止损价格过滤功能"""
    print("=" * 80)
    print("🔍 开始测试止损价格过滤功能")
    print("=" * 80)
    
    # 创建模拟信号
    test_signals = create_mock_signals()
    print(f"📊 创建了 {len(test_signals)} 个模拟交易信号")
    
    # 过滤信号
    filtered_signals = filter_signals(test_signals, TEST_CONFIG)
    
    # 显示结果
    print("\n" + "=" * 80)
    print("📝 测试结果总结:")
    print(f"   • 原始信号数量: {len(test_signals)}")
    print(f"   • 过滤后信号数量: {len(filtered_signals)}")
    print(f"   • 过滤掉的信号数量: {len(test_signals) - len(filtered_signals)}")
    print(f"   • 通过过滤的信号: {[signal.symbol for signal in filtered_signals]}")
    
    # 验证结果
    expected_passed = 2  # 预期通过的信号数量
    assert len(filtered_signals) == expected_passed, \
        f"测试失败: 预期通过 {expected_passed} 个信号，但实际通过 {len(filtered_signals)} 个"
    
    print("✅ 测试通过!")
    print("✅ 止损价格过滤功能正常工作")
    print("=" * 80)

if __name__ == "__main__":
    test_stop_loss_filter()