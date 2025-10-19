import unittest
import json
from unittest.mock import MagicMock, patch
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入要测试的模块
from report_viewer_python.control.okx_control import OKXControl

class TestLeverageControl(unittest.TestCase):
    
    def setUp(self):
        # 创建OKXControl实例用于测试
        self.okx_control = OKXControl()
        # 模拟API客户端
        self.mock_public_api = MagicMock()
        self.mock_official_api = MagicMock()
        self.mock_account_api = MagicMock()
        self.okx_control.set_api_clients(
            okx_public_api=self.mock_public_api,
            okx_official_api=self.mock_official_api,
            okx_account_api=self.mock_account_api
        )
    
    def test_get_perpetual_symbols_with_leverage(self):
        # 模拟API响应
        mock_response = {
            'code': '0',
            'data': [
                {'instId': 'BTC-USDT-SWAP', 'lever': '100', 'alias': 'BTC-USDT-SWAP', 'baseCcy': 'BTC', 'quoteCcy': 'USDT'},
                {'instId': 'ETH-USDT-SWAP', 'lever': '50', 'alias': 'ETH-USDT-SWAP', 'baseCcy': 'ETH', 'quoteCcy': 'USDT'}
            ]
        }
        self.mock_public_api.get_instruments.return_value = mock_response
        
        # 调用方法
        result = self.okx_control.get_perpetual_symbols_with_leverage()
        
        # 验证API调用 - 参数已更新为直接传递'SWAP'
        self.mock_public_api.get_instruments.assert_called_once_with('SWAP')
        
        # 验证结果
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['symbol'], 'BTC-USDT-SWAP')
        self.assertEqual(result[0]['max_leverage'], '100')  # 注意实际返回的是字符串
        self.assertEqual(result[1]['symbol'], 'ETH-USDT-SWAP')
        self.assertEqual(result[1]['max_leverage'], '50')
    
    def test_get_perpetual_symbols_with_leverage_api_error(self):
        # 模拟API错误响应
        mock_response = {
            'code': '500',
            'msg': 'Internal Server Error'
        }
        self.mock_public_api.get_instruments.return_value = mock_response
        
        # 调用方法
        result = self.okx_control.get_perpetual_symbols_with_leverage()
        
        # 验证结果
        self.assertIn('error', result)
        self.assertIn('symbols', result)
        self.assertEqual(result['symbols'], [])
    
    def test_set_max_leverage_success(self):
        # 模拟API响应
        mock_response = {
            'code': '0',
            'data': [{'instId': 'BTC-USDT-SWAP', 'lever': '20', 'mgnMode': 'isolated'}]
        }
        # 现在使用account_api而不是official_api
        self.mock_account_api.set_leverage.return_value = mock_response
        
        # 调用方法
        result = self.okx_control.set_max_leverage('BTC-USDT-SWAP', 20, 'isolated')
        
        # 验证API调用 - 参数顺序已更新
        self.mock_account_api.set_leverage.assert_called_once_with(
            lever='20',
            mgnMode='isolated',
            instId='BTC-USDT-SWAP'
        )
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertIn('成功设置', result['message'])
    
    def test_set_max_leverage_invalid_params(self):
        # 测试无效的杠杆值
        result = self.okx_control.set_max_leverage('BTC-USDT-SWAP', 0, 'isolated')
        
        # 验证结果
        self.assertFalse(result['success'])
        self.assertIn('杠杆值必须在', result['message'])
        self.mock_official_api.set_leverage.assert_not_called()
    
    @patch('time.sleep', return_value=None)  # 模拟time.sleep，避免测试等待
    def test_batch_set_leverage(self, mock_sleep):
        # 模拟set_max_leverage方法的返回值
        def mock_set_max_leverage(symbol, leverage, mgn_mode):
            if symbol == 'BTC-USDT-SWAP':
                return {'success': True, 'message': '成功设置 BTC-USDT-SWAP 的杠杆为 20x', 'symbol': symbol, 'leverage': leverage}
            elif symbol == 'ETH-USDT-SWAP':
                return {'success': False, 'message': '设置杠杆失败: API错误'}
            else:
                return {'success': True, 'message': '成功设置 SOL-USDT-SWAP 的杠杆为 20x', 'symbol': symbol, 'leverage': leverage}
        
        # 替换实例方法
        original_method = self.okx_control.set_max_leverage
        self.okx_control.set_max_leverage = MagicMock(side_effect=mock_set_max_leverage)
        
        try:
            # 调用方法
            symbols = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP']
            results = self.okx_control.batch_set_leverage(symbols, 20, 'isolated')
            
            # 验证结果
            self.assertEqual(results['total'], 3)
            self.assertEqual(results['success_count'], 2)
            self.assertEqual(results['fail_count'], 1)
            self.assertEqual(len(results['results']), 3)
        finally:
            # 恢复原始方法
            self.okx_control.set_max_leverage = original_method

if __name__ == '__main__':
    unittest.main()

if __name__ == '__main__':
    unittest.main()