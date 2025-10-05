#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试时间框架过滤功能
"""

import logging
from datetime import datetime
from typing import List
import sys

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 尝试导入配置和数据类
try:
    from multi_timeframe_system import MultiTimeframeSignal
    from config import TRADING_CONFIG
    logger.info("成功导入配置和数据类")
except ImportError:
    logger.warning("无法从multi_timeframe_system导入，使用本地模拟类")
    
    # 模拟MultiTimeframeSignal类用于测试
    class MultiTimeframeSignal:
        def __init__(self, symbol, weekly_trend, daily_trend, h4_signal, h1_signal, 
                     m15_signal, overall_action, confidence_level, total_score, 
                     entry_price, target_short, target_medium, target_long, 
                     stop_loss, atr_one, reasoning, timestamp):
            self.symbol = symbol
            self.weekly_trend = weekly_trend
            self.daily_trend = daily_trend
            self.h4_signal = h4_signal
            self.h1_signal = h1_signal
            self.m15_signal = m15_signal
            self.overall_action = overall_action
            self.confidence_level = confidence_level
            self.total_score = total_score
            self.entry_price = entry_price
            self.target_short = target_short
            self.target_medium = target_medium
            self.target_long = target_long
            self.stop_loss = stop_loss
            self.atr_one = atr_one
            self.reasoning = reasoning
            self.timestamp = timestamp
    
    # 模拟配置
    TRADING_CONFIG = {
        'BUY_THRESHOLD': 0.5,
        'SELL_THRESHOLD': -0.5,
        'FILTER_BY_15M': False,
        'FILTER_BY_1H': False
    }

# 模拟交易信号生成函数
def create_mock_signals() -> List[MultiTimeframeSignal]:
    """创建模拟的交易信号用于测试"""
    now = datetime.now()
    
    # 创建不同条件的模拟信号
    signals = [
        # 信号1：评分达标，15分钟和1小时都是买入
        MultiTimeframeSignal(
            symbol="BTC/USDT",
            weekly_trend="买入",
            daily_trend="买入",
            h4_signal="买入",
            h1_signal="买入",  # 1小时为买入
            m15_signal="买入", # 15分钟为买入
            overall_action="买入",
            confidence_level="高",
            total_score=1.2,
            entry_price=40000.0,
            target_short=42000.0,
            target_medium=0.0,
            target_long=0.0,
            stop_loss=38000.0,
            atr_one=0.0,
            reasoning=["综合评分达标"],
            timestamp=now
        ),
        # 信号2：评分达标，15分钟不是买入，1小时是买入
        MultiTimeframeSignal(
            symbol="ETH/USDT",
            weekly_trend="买入",
            daily_trend="买入",
            h4_signal="买入",
            h1_signal="买入",  # 1小时为买入
            m15_signal="观望", # 15分钟不是买入
            overall_action="买入",
            confidence_level="中",
            total_score=0.8,
            entry_price=2000.0,
            target_short=2100.0,
            target_medium=0.0,
            target_long=0.0,
            stop_loss=1900.0,
            atr_one=0.0,
            reasoning=["综合评分达标"],
            timestamp=now
        ),
        # 信号3：评分达标，15分钟是买入，1小时不是买入
        MultiTimeframeSignal(
            symbol="SOL/USDT",
            weekly_trend="买入",
            daily_trend="买入",
            h4_signal="买入",
            h1_signal="观望",  # 1小时不是买入
            m15_signal="买入", # 15分钟为买入
            overall_action="买入",
            confidence_level="中",
            total_score=0.7,
            entry_price=100.0,
            target_short=105.0,
            target_medium=0.0,
            target_long=0.0,
            stop_loss=95.0,
            atr_one=0.0,
            reasoning=["综合评分达标"],
            timestamp=now
        ),
        # 信号4：评分达标，15分钟和1小时都不是买入
        MultiTimeframeSignal(
            symbol="ADA/USDT",
            weekly_trend="买入",
            daily_trend="买入",
            h4_signal="买入",
            h1_signal="观望",  # 1小时不是买入
            m15_signal="观望", # 15分钟不是买入
            overall_action="买入",
            confidence_level="低",
            total_score=0.6,
            entry_price=1.0,
            target_short=1.05,
            target_medium=0.0,
            target_long=0.0,
            stop_loss=0.95,
            atr_one=0.0,
            reasoning=["综合评分达标"],
            timestamp=now
        ),
        # 信号5：卖出信号 - 15分钟和1小时都是卖出
        MultiTimeframeSignal(
            symbol="DOT/USDT",
            weekly_trend="卖出",
            daily_trend="卖出",
            h4_signal="卖出",
            h1_signal="卖出",  # 1小时为卖出
            m15_signal="卖出", # 15分钟为卖出
            overall_action="卖出",
            confidence_level="高",
            total_score=-1.0,
            entry_price=5.0,
            target_short=4.5,
            target_medium=0.0,
            target_long=0.0,
            stop_loss=5.5,
            atr_one=0.0,
            reasoning=["综合评分达标"],
            timestamp=now
        ),
        # 信号6：卖出信号 - 15分钟不是卖出，1小时是卖出
        MultiTimeframeSignal(
            symbol="LINK/USDT",
            weekly_trend="卖出",
            daily_trend="卖出",
            h4_signal="卖出",
            h1_signal="卖出",  # 1小时为卖出
            m15_signal="观望", # 15分钟不是卖出
            overall_action="卖出",
            confidence_level="中",
            total_score=-0.8,
            entry_price=20.0,
            target_short=18.0,
            target_medium=0.0,
            target_long=0.0,
            stop_loss=22.0,
            atr_one=0.0,
            reasoning=["综合评分达标"],
            timestamp=now
        ),
        # 信号7：卖出信号 - 15分钟是卖出，1小时不是卖出
        MultiTimeframeSignal(
            symbol="DOGE/USDT",
            weekly_trend="卖出",
            daily_trend="卖出",
            h4_signal="卖出",
            h1_signal="观望",  # 1小时不是卖出
            m15_signal="卖出", # 15分钟为卖出
            overall_action="卖出",
            confidence_level="中",
            total_score=-0.7,
            entry_price=0.1,
            target_short=0.09,
            target_medium=0.0,
            target_long=0.0,
            stop_loss=0.11,
            atr_one=0.0,
            reasoning=["综合评分达标"],
            timestamp=now
        )
    ]
    
    return signals

# 实现与multi_timeframe_system中相同的过滤逻辑
def filter_signals(signals: List[MultiTimeframeSignal], config: dict) -> List[MultiTimeframeSignal]:
    """根据配置过滤交易信号"""
    filtered = []
    
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
                filtered.append(op)
            else:
                # 检查时间框架条件
                is_15m_buy = "买入" in op.m15_signal
                is_1h_buy = "买入" in op.h1_signal
                
                # 根据过滤开关决定是否添加信号
                if ((not filter_by_15m or is_15m_buy) and 
                    (not filter_by_1h or is_1h_buy)):
                    filtered.append(op)
                    
        # 卖出信号应用时间框架过滤
        elif op.total_score <= config['SELL_THRESHOLD'] and op.overall_action == "卖出":
            # 应用时间框架过滤
            filter_by_15m = config.get('FILTER_BY_15M', False)
            filter_by_1h = config.get('FILTER_BY_1H', False)
            
            # 确定是否需要过滤
            should_filter = filter_by_15m or filter_by_1h
            
            # 如果不需要过滤，直接添加
            if not should_filter:
                filtered.append(op)
            else:
                # 检查时间框架条件（卖出信号）
                is_15m_sell = "卖出" in op.m15_signal
                is_1h_sell = "卖出" in op.h1_signal
                
                # 根据过滤开关决定是否添加信号
                # 逻辑：如果开启了对应过滤，则需要对应时间框架也为卖出；如果关闭了过滤，则不考虑该时间框架
                if ((not filter_by_15m or is_15m_sell) and 
                    (not filter_by_1h or is_1h_sell)):
                    filtered.append(op)
    
    return filtered

def test_timeframe_filter():
    """测试时间框架过滤功能"""
    logger.info("开始测试时间框架过滤功能...")
    
    # 创建模拟信号
    mock_signals = create_mock_signals()
    logger.info(f"创建了 {len(mock_signals)} 个模拟信号用于测试")
    
    # 打印模拟信号信息
    logger.info("\n模拟信号详情：")
    for i, signal in enumerate(mock_signals):
        logger.info(f"信号 {i+1}: {signal.symbol} - 操作: {signal.overall_action}, 评分: {signal.total_score:.2f}")
        logger.info(f"  1小时信号: {signal.h1_signal}, 15分钟信号: {signal.m15_signal}")
    
    # 测试不同的过滤配置组合
    test_cases = [
        {"name": "关闭所有过滤", "filter_by_15m": False, "filter_by_1h": False},
        {"name": "只开启15分钟过滤", "filter_by_15m": True, "filter_by_1h": False},
        {"name": "只开启1小时过滤", "filter_by_15m": False, "filter_by_1h": True},
        {"name": "同时开启15分钟和1小时过滤", "filter_by_15m": True, "filter_by_1h": True}
    ]
    
    # 运行每个测试用例
    for test_case in test_cases:
        # 创建测试配置
        test_config = TRADING_CONFIG.copy()
        test_config['FILTER_BY_15M'] = test_case['filter_by_15m']
        test_config['FILTER_BY_1H'] = test_case['filter_by_1h']
        
        # 应用过滤
        filtered_signals = filter_signals(mock_signals, test_config)
        
        # 分析结果
        buy_signals_before = len([s for s in mock_signals if s.overall_action == "买入"])  
        sell_signals_before = len([s for s in mock_signals if s.overall_action == "卖出"])
        
        buy_signals_after = len([s for s in filtered_signals if s.overall_action == "买入"])
        sell_signals_after = len([s for s in filtered_signals if s.overall_action == "卖出"])
        
        # 打印测试结果
        logger.info(f"\n【测试用例】: {test_case['name']}")
        logger.info(f"配置: FILTER_BY_15M={test_case['filter_by_15m']}, FILTER_BY_1H={test_case['filter_by_1h']}")
        logger.info(f"过滤前: 买入信号={buy_signals_before}, 卖出信号={sell_signals_before}")
        logger.info(f"过滤后: 买入信号={buy_signals_after}, 卖出信号={sell_signals_after}")
        
        # 打印通过过滤的信号
        logger.info("通过过滤的信号：")
        for signal in filtered_signals:
            logger.info(f"  {signal.symbol} - 操作: {signal.overall_action}")
    
    logger.info("\n✅ 时间框架过滤功能测试完成")
    
if __name__ == "__main__":
    test_timeframe_filter()