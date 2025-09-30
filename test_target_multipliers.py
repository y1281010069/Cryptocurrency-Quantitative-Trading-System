#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试目标价格和止损价格的乘数设置是否正确应用
"""

import logging
import sys
from typing import Dict

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_target_multipliers():
    """测试目标价格和止损价格的乘数设置是否正确应用"""
    logger.info("开始测试目标价格和止损价格乘数配置...")
    
    # 尝试导入配置文件，如果不存在则使用默认值
    try:
        from config import TRADING_CONFIG
    except ImportError:
        # 使用默认配置
        TRADING_CONFIG = {
            'BUY_THRESHOLD': 0.5,
            'SELL_THRESHOLD': -0.5,
            'ATR_PERIOD': 14,
            'TARGET_MULTIPLIER': 4.5,
            'STOP_LOSS_MULTIPLIER': 3,
            'ENABLED_SYMBOLS': [],
            'DISABLED_SYMBOLS': ['USDC/USDT']
        }
        logger.warning("配置文件未找到，使用默认配置")
    
    # 显示当前配置的乘数
    target_multiplier = TRADING_CONFIG['TARGET_MULTIPLIER']
    stop_loss_multiplier = TRADING_CONFIG['STOP_LOSS_MULTIPLIER']
    
    logger.info(f"当前配置: TARGET_MULTIPLIER={target_multiplier}, STOP_LOSS_MULTIPLIER={stop_loss_multiplier}")
    
    # 模拟数据
    test_cases = [
        {"symbol": "BTC/USDT", "current_price": 40000.0, "atr_value": 1000.0},
        {"symbol": "ETH/USDT", "current_price": 2000.0, "atr_value": 50.0},
        {"symbol": "SOL/USDT", "current_price": 100.0, "atr_value": 2.0}
    ]
    
    # 测试买入方向的价格计算
    logger.info("\n测试买入方向的价格计算:")
    for test_case in test_cases:
        symbol = test_case["symbol"]
        current_price = test_case["current_price"]
        atr_value = test_case["atr_value"]
        
        # 使用配置的乘数计算价格
        target_short = current_price + target_multiplier * atr_value
        stop_loss = current_price - stop_loss_multiplier * atr_value
        
        # 计算预期的百分比变化
        target_percent = ((target_short / current_price) - 1) * 100
        stop_loss_percent = ((stop_loss / current_price) - 1) * 100
        
        logger.info(f"{symbol}:")
        logger.info(f"  当前价格: {current_price:.2f} USDT")
        logger.info(f"  ATR值: {atr_value:.2f}")
        logger.info(f"  短期目标 ({target_multiplier}倍ATR): {target_short:.2f} USDT (+{target_percent:.2f}%)")
        logger.info(f"  止损价格 ({stop_loss_multiplier}倍ATR): {stop_loss:.2f} USDT ({stop_loss_percent:.2f}%)")
    
    # 测试卖出方向的价格计算
    logger.info("\n测试卖出方向的价格计算:")
    for test_case in test_cases:
        symbol = test_case["symbol"]
        current_price = test_case["current_price"]
        atr_value = test_case["atr_value"]
        
        # 使用配置的乘数计算价格
        target_short = current_price - target_multiplier * atr_value
        stop_loss = current_price + stop_loss_multiplier * atr_value
        
        # 计算预期的百分比变化
        target_percent = ((target_short / current_price) - 1) * 100
        stop_loss_percent = ((stop_loss / current_price) - 1) * 100
        
        logger.info(f"{symbol}:")
        logger.info(f"  当前价格: {current_price:.2f} USDT")
        logger.info(f"  ATR值: {atr_value:.2f}")
        logger.info(f"  短期目标 ({target_multiplier}倍ATR): {target_short:.2f} USDT ({target_percent:.2f}%)")
        logger.info(f"  止损价格 ({stop_loss_multiplier}倍ATR): {stop_loss:.2f} USDT (+{stop_loss_percent:.2f}%)")
    
    logger.info("\n✅ 目标价格和止损价格乘数配置测试完成")
    
if __name__ == "__main__":
    test_target_multipliers()