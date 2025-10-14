import unittest
import os
import sys
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入被测试的策略类
from strategies.multi_timeframe_strategy import MultiTimeframeStrategy, MultiTimeframeSignal
from strategies.base_strategy import BaseStrategy

class TestFileGeneration(unittest.TestCase):
    
    def setUp(self):
        """设置测试环境"""
        self.strategy = MultiTimeframeStrategy()
        self.test_dir = "test_output"
        os.makedirs(self.test_dir, exist_ok=True)
        
        # 创建测试用的交易信号数据
        self.mock_signals = [
            MultiTimeframeSignal(
                symbol="BTC/USDT",
                weekly_trend="看涨",
                daily_trend="看涨",
                h4_signal="买入",
                h1_signal="买入",
                m15_signal="买入",
                overall_action="买入",
                confidence_level="高",
                total_score=0.8,
                entry_price=60000.0,
                target_short=62000.0,
                target_medium=65000.0,
                target_long=70000.0,
                stop_loss=58000.0,
                atr_one=1000.0,
                reasoning=["RSI金叉", "MACD看涨背离"],
                timestamp=datetime.now()
            ),
            MultiTimeframeSignal(
                symbol="ETH/USDT",
                weekly_trend="看跌",
                daily_trend="看跌",
                h4_signal="卖出",
                h1_signal="卖出",
                m15_signal="卖出",
                overall_action="卖出",
                confidence_level="中",
                total_score=-0.6,
                entry_price=4000.0,
                target_short=3800.0,
                target_medium=3500.0,
                target_long=3000.0,
                stop_loss=4200.0,
                atr_one=100.0,
                reasoning=["MACD死叉", "布林带向下突破"],
                timestamp=datetime.now()
            )
        ]
        
        # 创建测试用的持仓数据
        self.mock_positions = [
            {
                'symbol': 'BTC/USDT',
                'posSide': 'long',
                'amount': '1.0',
                'entry_price': '58000.0',
                'current_price': '60000.0',
                'datetime': (datetime.now() - pd.Timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S'),
                'reason': '持仓时间超过5小时'
            },
            {
                'symbol': 'ETH/USDT',
                'posSide': 'short',
                'amount': '10.0',
                'entry_price': '4200.0',
                'current_price': '4000.0',
                'datetime': (datetime.now() - pd.Timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
                'reason': 'MultiTimeframeStrategy策略建议平仓'
            }
        ]
    
    def tearDown(self):
        """清理测试环境"""
        # 清理测试生成的文件
        if os.path.exists(self.test_dir):
            for file in os.listdir(self.test_dir):
                os.remove(os.path.join(self.test_dir, file))
            os.rmdir(self.test_dir)
    
    @patch('strategies.multi_timeframe_strategy.redis.Redis')
    @patch('strategies.multi_timeframe_strategy.send_trading_signal_to_api')
    def test_save_trade_signals(self, mock_send_api, mock_redis):
        """测试save_trade_signals方法是否正确生成交易信号文件"""
        # 模拟Redis返回空数据
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.get.return_value = None
        
        # 执行方法
        file_path = self.strategy.save_trade_signals(self.mock_signals)
        
        # 验证文件是否生成
        self.assertTrue(os.path.exists(file_path))
        
        # 验证文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("交易信号记录", content)
            self.assertIn("BTC/USDT", content)
            self.assertIn("ETH/USDT", content)
            self.assertIn("买入", content)
            self.assertIn("卖出", content)
    
    def test_save_positions_needing_attention(self):
        """测试save_positions_needing_attention方法是否正确生成持仓关注文件"""
        # 执行方法
        file_path = self.strategy.save_positions_needing_attention(self.mock_positions)
        
        # 验证文件是否生成
        self.assertTrue(os.path.exists(file_path))
        
        # 验证文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("需要关注的持仓记录", content)
            self.assertIn("BTC/USDT", content)
            self.assertIn("ETH/USDT", content)
            self.assertIn("持仓时间超过5小时", content)
            self.assertIn("MultiTimeframeStrategy策略建议平仓", content)
    
    def test_save_multi_timeframe_analysis(self):
        """测试save_multi_timeframe_analysis方法是否正确生成多时间框架分析报告"""
        # 执行方法
        file_path = self.strategy.save_multi_timeframe_analysis(self.mock_signals)
        
        # 验证文件是否生成
        self.assertTrue(os.path.exists(file_path))
        
        # 验证文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("多时间框架分析报告", content)
            self.assertIn("BTC/USDT", content)
            self.assertIn("ETH/USDT", content)
            self.assertIn("买入信号: 1 个", content)
            self.assertIn("卖出信号: 1 个", content)
            self.assertIn("综合建议: 观望", content)  # 因为买入和卖出信号数量相等

if __name__ == '__main__':
    unittest.main()