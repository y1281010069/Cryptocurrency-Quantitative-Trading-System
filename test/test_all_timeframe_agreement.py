import sys
import os
from datetime import datetime
from typing import Dict, List

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入必要的类和配置
from multi_timeframe_system import MultiTimeframeSignal, TRADING_CONFIG

# 模拟配置
TEST_CONFIG = {
    'BUY_THRESHOLD': 0.5,
    'SELL_THRESHOLD': -0.5,
    'TARGET_MULTIPLIER': 1.5,
    'STOP_LOSS_MULTIPLIER': 1.0
}

# 创建模拟的交易信号
def create_mock_signal(symbol: str, signals: Dict[str, str], overall_action: str, 
                      current_price: float, atr_value: float) -> MultiTimeframeSignal:
    """创建模拟的多时间框架交易信号"""
    
    # 检查是否所有时间框架都一致
    all_agreed = True
    first_signal = None
    for signal in signals.values():
        if not first_signal:
            first_signal = signal
        elif (("买入" in first_signal and "买入" not in signal) or 
              ("卖出" in first_signal and "卖出" not in signal)):
            all_agreed = False
            break
    
    # 根据是否所有时间框架一致决定使用的TARGET_MULTIPLIER
    target_multiplier = TEST_CONFIG['TARGET_MULTIPLIER']
    if all_agreed:
        target_multiplier *= 3
    
    # 计算目标价格和止损价格
    if overall_action == "买入":
        atr_one = current_price + atr_value
        target_short = current_price + target_multiplier * atr_value
        stop_loss = current_price - TEST_CONFIG['STOP_LOSS_MULTIPLIER'] * atr_value
    else:
        atr_one = current_price - atr_value
        target_short = current_price - target_multiplier * atr_value
        stop_loss = current_price + TEST_CONFIG['STOP_LOSS_MULTIPLIER'] * atr_value
    
    # 创建信号对象
    signal_obj = MultiTimeframeSignal(
        symbol=symbol,
        weekly_trend=signals.get('1w', '观望'),
        daily_trend=signals.get('1d', '观望'),
        h4_signal=signals.get('4h', '观望'),
        h1_signal=signals.get('1h', '观望'),
        m15_signal=signals.get('15m', '观望'),
        overall_action=overall_action,
        confidence_level="高" if (all_agreed or abs(0.8) >= TEST_CONFIG['BUY_THRESHOLD']) else "低",
        total_score=0.8 if overall_action == "买入" else -0.8,
        entry_price=current_price,
        target_short=target_short,
        target_medium=0.0,
        target_long=0.0,
        stop_loss=stop_loss,
        atr_one=atr_one,
        reasoning=[f"{tf}:{signal}" for tf, signal in signals.items()],
        timestamp=datetime.now()
    )
    
    return signal_obj, all_agreed, target_multiplier

# 运行测试
def test_all_timeframe_agreement():
    """测试所有时间框架一致时使用3倍盈亏比的功能"""
    print("=" * 80)
    print("🔍 开始测试所有时间框架一致时使用3倍盈亏比的功能")
    print("=" * 80)
    
    # 测试场景1: 所有时间框架都为买入
    print("\n📊 测试场景1: 所有时间框架都为买入")
    signals1 = {
        '1w': '买入',
        '1d': '买入',
        '4h': '买入',
        '1h': '买入',
        '15m': '买入'
    }
    signal1, all_agreed1, multiplier1 = create_mock_signal(
        "BTC/USDT", signals1, "买入", 40000.0, 1000.0
    )
    expected_target1 = 40000.0 + (TEST_CONFIG['TARGET_MULTIPLIER'] * 3) * 1000.0
    expected_stop1 = 40000.0 - TEST_CONFIG['STOP_LOSS_MULTIPLIER'] * 1000.0
    
    print(f"   • 所有时间框架一致: {all_agreed1}")
    print(f"   • 使用的TARGET_MULTIPLIER: {multiplier1}")
    print(f"   • 目标价格: {signal1.target_short:.2f}")
    print(f"   • 预期目标价格: {expected_target1:.2f}")
    print(f"   • 止损价格: {signal1.stop_loss:.2f}")
    print(f"   • 盈亏比: {(signal1.target_short - signal1.entry_price)/abs(signal1.stop_loss - signal1.entry_price):.2f}:1")
    
    # 测试场景2: 所有时间框架都为卖出
    print("\n📊 测试场景2: 所有时间框架都为卖出")
    signals2 = {
        '1w': '卖出',
        '1d': '卖出',
        '4h': '卖出',
        '1h': '卖出',
        '15m': '卖出'
    }
    signal2, all_agreed2, multiplier2 = create_mock_signal(
        "ETH/USDT", signals2, "卖出", 2000.0, 50.0
    )
    expected_target2 = 2000.0 - (TEST_CONFIG['TARGET_MULTIPLIER'] * 3) * 50.0
    expected_stop2 = 2000.0 + TEST_CONFIG['STOP_LOSS_MULTIPLIER'] * 50.0
    
    print(f"   • 所有时间框架一致: {all_agreed2}")
    print(f"   • 使用的TARGET_MULTIPLIER: {multiplier2}")
    print(f"   • 目标价格: {signal2.target_short:.2f}")
    print(f"   • 预期目标价格: {expected_target2:.2f}")
    print(f"   • 止损价格: {signal2.stop_loss:.2f}")
    print(f"   • 盈亏比: {(signal2.entry_price - signal2.target_short)/abs(signal2.stop_loss - signal2.entry_price):.2f}:1")
    
    # 测试场景3: 时间框架不一致
    print("\n📊 测试场景3: 时间框架不一致")
    signals3 = {
        '1w': '买入',
        '1d': '买入',
        '4h': '观望',
        '1h': '卖出',
        '15m': '卖出'
    }
    signal3, all_agreed3, multiplier3 = create_mock_signal(
        "SOL/USDT", signals3, "买入", 100.0, 5.0
    )
    expected_target3 = 100.0 + TEST_CONFIG['TARGET_MULTIPLIER'] * 5.0
    expected_stop3 = 100.0 - TEST_CONFIG['STOP_LOSS_MULTIPLIER'] * 5.0
    
    print(f"   • 所有时间框架一致: {all_agreed3}")
    print(f"   • 使用的TARGET_MULTIPLIER: {multiplier3}")
    print(f"   • 目标价格: {signal3.target_short:.2f}")
    print(f"   • 预期目标价格: {expected_target3:.2f}")
    print(f"   • 止损价格: {signal3.stop_loss:.2f}")
    print(f"   • 盈亏比: {(signal3.target_short - signal3.entry_price)/abs(signal3.stop_loss - signal3.entry_price):.2f}:1")
    
    # 验证结果
    print("\n" + "=" * 80)
    print("✅ 测试验证结果:")
    
    # 验证场景1
    scenario1_passed = (all_agreed1 and 
                       multiplier1 == TEST_CONFIG['TARGET_MULTIPLIER'] * 3 and 
                       abs(signal1.target_short - expected_target1) < 0.01 and 
                       abs(signal1.stop_loss - expected_stop1) < 0.01)
    print(f"   • 场景1 (所有时间框架买入): {'通过' if scenario1_passed else '失败'}")
    
    # 验证场景2
    scenario2_passed = (all_agreed2 and 
                       multiplier2 == TEST_CONFIG['TARGET_MULTIPLIER'] * 3 and 
                       abs(signal2.target_short - expected_target2) < 0.01 and 
                       abs(signal2.stop_loss - expected_stop2) < 0.01)
    print(f"   • 场景2 (所有时间框架卖出): {'通过' if scenario2_passed else '失败'}")
    
    # 验证场景3
    scenario3_passed = (not all_agreed3 and 
                       multiplier3 == TEST_CONFIG['TARGET_MULTIPLIER'] and 
                       abs(signal3.target_short - expected_target3) < 0.01 and 
                       abs(signal3.stop_loss - expected_stop3) < 0.01)
    print(f"   • 场景3 (时间框架不一致): {'通过' if scenario3_passed else '失败'}")
    
    # 总体结果
    all_passed = scenario1_passed and scenario2_passed and scenario3_passed
    print(f"\n🎯 总体测试结果: {'全部通过' if all_passed else '部分失败'}")
    print("=" * 80)
    
    if all_passed:
        print("✅ 所有时间框架一致时使用3倍盈亏比的功能正常工作！")
    else:
        print("❌ 测试失败，请检查代码逻辑！")
    print("=" * 80)

if __name__ == "__main__":
    test_all_timeframe_agreement()