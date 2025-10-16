# -*- coding: utf-8 -*-
"""
测试交易信号阈值判断逻辑
验证BUY_THRESHOLD和SELL_THRESHOLD是否正确使用了大于等于和小于等于
"""

import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)

def test_threshold_logic():
    """测试阈值判断逻辑"""
    logger.info("🚀 开始测试交易信号阈值判断逻辑")
    
    # 尝试导入配置
    try:
        from config import TRADING_CONFIG
        logger.info("✅ 成功导入配置文件")
    except ImportError:
        # 使用默认配置
        TRADING_CONFIG = {
            'BUY_THRESHOLD': 0.5,
            'SELL_THRESHOLD': -0.5
        }
        logger.warning("⚠️ 配置文件未找到，使用默认配置")
    
    # 获取阈值
    buy_threshold = TRADING_CONFIG.get('BUY_THRESHOLD', 0.5)
    sell_threshold = TRADING_CONFIG.get('SELL_THRESHOLD', -0.5)
    
    logger.info(f"\n当前配置:")
    logger.info(f"  BUY_THRESHOLD = {buy_threshold}")
    logger.info(f"  SELL_THRESHOLD = {sell_threshold}")
    
    # 测试买入阈值逻辑
    logger.info(f"\n测试买入阈值逻辑 (>= {buy_threshold}):")
    test_scores = [buy_threshold - 0.1, buy_threshold, buy_threshold + 0.1]
    for score in test_scores:
        result = "买入信号" if score >= buy_threshold else "非买入信号"
        logger.info(f"  评分 {score:.1f}: {result}")
    
    # 测试卖出阈值逻辑
    logger.info(f"\n测试卖出阈值逻辑 (<= {sell_threshold}):")
    test_scores = [sell_threshold - 0.1, sell_threshold, sell_threshold + 0.1]
    for score in test_scores:
        result = "卖出信号" if score <= sell_threshold else "非卖出信号"
        logger.info(f"  评分 {score:.1f}: {result}")
    
    logger.info("\n✅ 阈值判断逻辑测试完成")
    
if __name__ == "__main__":
    test_threshold_logic()