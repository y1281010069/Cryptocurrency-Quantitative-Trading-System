#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试特定信号组合下的all_agreed状态判断和盈亏比应用"""

import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入配置
from config import TRADING_CONFIG

class SignalCombinationTester:
    """测试不同信号组合下的all_agreed状态判断"""
    
    def __init__(self):
        """初始化测试器"""
        self.target_multiplier = TRADING_CONFIG.get('TARGET_MULTIPLIER', 1.5)
        logger.info(f"当前配置的TARGET_MULTIPLIER值: {self.target_multiplier}")
    
    def test_agreement_logic(self, signals):
        """测试all_agreed判断逻辑（更新后的逻辑）
        
        Args:
            signals: 包含不同时间框架信号的字典
            例如: {"1w": "观望", "1d": "强烈买入", "4h": "买入", "1h": "买入", "15m": "观望"}
        
        Returns:
            dict: 包含判断结果的字典
        """
        logger.info(f"测试信号组合: {signals}")
        
        # 检查是否存在观望信号
        has_neutral = any("观望" in signal for signal in signals.values())
        
        # 过滤掉"观望"信号
        valid_signals = [signal for signal in signals.values() if "观望" not in signal]
        logger.info(f"过滤后有效信号: {valid_signals}")
        
        # 只有当没有观望信号且所有有效信号方向一致时，才算一致
        all_agreed = False
        if not has_neutral and valid_signals:
            # 检查所有有效信号是否方向一致
            first_direction = "买入" if "买入" in valid_signals[0] else "卖出"
            all_agreed = True
            for signal in valid_signals[1:]:
                if first_direction not in signal:
                    all_agreed = False
                    break
        
        logger.info(f"all_agreed状态: {all_agreed}, 有效信号数量: {len(valid_signals)}, 存在观望信号: {has_neutral}")
        
        # 计算应用的盈亏比乘数
        applied_multiplier = self.target_multiplier
        if all_agreed:
            applied_multiplier *= 3
            logger.info(f"所有时间框架信号一致且无观望信号，使用3倍盈亏比 (调整后乘数: {applied_multiplier})")
        else:
            logger.info(f"信号方向不一致或存在观望信号，使用标准盈亏比 (乘数: {applied_multiplier})")
        
        # 计算可能的盈亏比范围
        atr = 1.0  # 假设ATR值为1用于演示
        buy_target = atr * applied_multiplier
        stop_loss = atr * TRADING_CONFIG.get('STOP_LOSS_MULTIPLIER', 1.0)
        risk_reward_ratio = buy_target / stop_loss
        
        logger.info(f"计算的盈亏比: {risk_reward_ratio:.2f} (目标: {buy_target:.2f}x ATR, 止损: {stop_loss:.2f}x ATR)")
        
        return {
            "signals": signals,
            "valid_signals": valid_signals,
            "all_agreed": all_agreed,
            "applied_multiplier": applied_multiplier,
            "risk_reward_ratio": risk_reward_ratio
        }

if __name__ == "__main__":
    # 创建测试器实例
    tester = SignalCombinationTester()
    
    # 测试用户提到的信号组合：日线强烈买入、4小时买入、1小时买入、15分钟观望
    test_signals = {
        "1w": "观望",
        "1d": "强烈买入",
        "4h": "买入",
        "1h": "买入",
        "15m": "观望"
    }
    
    logger.info("===== 测试用户提到的信号组合 ====")
    result = tester.test_agreement_logic(test_signals)
    
    # 测试完全一致的信号组合（作为对比）
    logger.info("\n===== 测试完全一致的信号组合（对比） ====")
    consistent_signals = {
        "1w": "买入",
        "1d": "强烈买入",
        "4h": "买入",
        "1h": "买入",
        "15m": "买入"
    }
    tester.test_agreement_logic(consistent_signals)
    
    # 测试不一致的信号组合（作为对比）
    logger.info("\n===== 测试不一致的信号组合（对比） ====")
    inconsistent_signals = {
        "1w": "卖出",
        "1d": "强烈买入",
        "4h": "买入",
        "1h": "观望",
        "15m": "买入"
    }
    tester.test_agreement_logic(inconsistent_signals)
    
    logger.info("\n测试完成。请查看日志分析all_agreed状态判断逻辑。")