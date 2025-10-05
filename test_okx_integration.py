#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OKX API集成测试脚本
用于验证python-okx库与现有系统的集成是否正常工作
"""
import sys
import os
import time
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入配置和必要的模块
try:
    from config import API_KEY, SECRET_KEY, PASSPHRASE
    CONFIG_AVAILABLE = True
    print("配置文件加载成功")
except ImportError:
    # 如果没有配置文件，使用模拟配置
    API_KEY = "your_api_key"
    SECRET_KEY = "your_secret_key"
    PASSPHRASE = "your_passphrase"
    CONFIG_AVAILABLE = False
    print("注意：配置文件未找到，使用示例配置")


class TestOKXIntegration:
    """OKX API集成测试类"""
    
    def __init__(self):
        """初始化测试类"""
        self.symbol = "BTC-USDT"  # 测试交易对
        self.timeframe = "15m"    # 测试时间框架
        self.limit = 5           # 返回数据条数
    
    def test_direct_api(self):
        """测试直接使用封装的OKXAPI类"""
        print("\n===== 测试直接使用OKXAPI类 ======")
        
        try:
            from okx_api import OKXAPI
            
            if not CONFIG_AVAILABLE:
                print("警告：由于没有有效的API配置，无法进行实际连接测试")
                print("请在config.py文件中设置有效的OKX API密钥以进行完整测试")
                return False
            
            # 创建OKX API实例
            okx = OKXAPI(API_KEY, SECRET_KEY, PASSPHRASE, is_testnet=False)
            
            # 测试获取K线数据
            print(f"\n1. 获取{self.symbol} {self.timeframe} K线数据：")
            klines = okx.get_klines(self.symbol, self.timeframe, self.limit)
            if klines:
                print(f"成功获取到{len(klines)}条K线数据")
                for kline in klines:
                    print(f"时间: {kline['datetime']}, 收盘价: {kline['close']}")
            else:
                print("获取K线数据失败")
                return False
            
            # 测试获取最新行情
            print(f"\n2. 获取{self.symbol}最新行情：")
            ticker = okx.get_ticker(self.symbol)
            if ticker:
                print(f"最新价格: {ticker.get('last', 'N/A')}")
                print(f"24h最高价: {ticker.get('high', 'N/A')}")
                print(f"24h最低价: {ticker.get('low', 'N/A')}")
            else:
                print("获取行情数据失败")
                return False
            
            # 测试获取订单簿
            print(f"\n3. 获取{self.symbol}订单簿（深度3）：")
            order_book = okx.get_order_book(self.symbol, depth=3)
            if order_book:
                print("卖单：")
                for ask in order_book.get('asks', [])[:3]:
                    print(f"价格: {ask[0]}, 数量: {ask[1]}")
                print("买单：")
                for bid in order_book.get('bids', [])[:3]:
                    print(f"价格: {bid[0]}, 数量: {bid[1]}")
            else:
                print("获取订单簿失败")
                return False
            
            print("\n直接API测试通过！")
            return True
            
        except Exception as e:
            print(f"直接API测试失败: {str(e)}")
            return False
    
    def test_adapter_with_ccxt_compatibility(self):
        """测试使用OKX适配器（ccxt兼容模式）"""
        print("\n===== 测试使用OKX适配器（ccxt兼容模式）======")
        
        try:
            from okx_adapter import get_ccxt_compatible_okx
            
            if not CONFIG_AVAILABLE:
                print("警告：由于没有有效的API配置，无法进行实际连接测试")
                print("请在config.py文件中设置有效的OKX API密钥以进行完整测试")
                return False
            
            # 创建ccxt兼容的OKX适配器
            exchange = get_ccxt_compatible_okx(
                api_key=API_KEY,
                secret_key=SECRET_KEY,
                password=PASSPHRASE,
                sandbox=False
            )
            
            # 测试获取K线数据（ccxt格式）
            print(f"\n1. 获取{self.symbol} {self.timeframe} K线数据（ccxt格式）：")
            ohlcv = exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=self.limit)
            if ohlcv:
                print(f"成功获取到{len(ohlcv)}条K线数据")
                for candle in ohlcv:
                    timestamp = datetime.fromtimestamp(candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"时间: {timestamp}, 收盘价: {candle[4]}")
            else:
                print("获取K线数据失败")
                return False
            
            # 测试获取行情（ccxt格式）
            print(f"\n2. 获取{self.symbol}行情数据（ccxt格式）：")
            ticker = exchange.fetch_ticker(self.symbol)
            if ticker:
                print(f"最新价格: {ticker.get('last', 'N/A')}")
                print(f"24h最高价: {ticker.get('high', 'N/A')}")
                print(f"24h最低价: {ticker.get('low', 'N/A')}")
            else:
                print("获取行情数据失败")
                return False
            
            print("\n适配器（ccxt兼容模式）测试通过！")
            return True
            
        except Exception as e:
            print(f"适配器测试失败: {str(e)}")
            return False
    
    def test_multi_timeframe_system_with_official_api(self):
        """测试在多时间框架系统中使用官方API"""
        print("\n===== 测试在多时间框架系统中使用官方API =====")
        
        try:
            from multi_timeframe_system import MultiTimeframeProfessionalSystem
            
            if not CONFIG_AVAILABLE:
                print("警告：由于没有有效的API配置，无法进行实际连接测试")
                print("请在config.py文件中设置有效的OKX API密钥以进行完整测试")
                return False
            
            # 创建系统实例，使用官方API
            system = MultiTimeframeProfessionalSystem(use_official_api=True)
            
            # 测试获取市场数据
            print(f"\n1. 获取{self.symbol} {self.timeframe} 市场数据：")
            df = system.get_timeframe_data(self.symbol, self.timeframe, self.limit)
            if not df.empty:
                print(f"成功获取到{len(df)}条市场数据")
                print(df.tail())
            else:
                print("获取市场数据失败")
                return False
            
            print("\n多时间框架系统使用官方API测试通过！")
            return True
            
        except Exception as e:
            print(f"多时间框架系统测试失败: {str(e)}")
            return False
    
    def test_config_based_api_selection(self):
        """测试从配置文件读取use_official_api设置"""
        print("\n===== 测试从配置文件读取use_official_api设置 =====")
        
        try:
            from multi_timeframe_system import MultiTimeframeProfessionalSystem
            
            if not CONFIG_AVAILABLE:
                print("警告：由于没有有效的API配置，无法进行实际连接测试")
                print("请在config.py文件中设置有效的OKX API密钥以进行完整测试")
                return False
            
            # 创建系统实例，不明确指定use_official_api参数，让系统从配置文件读取
            print("创建系统实例，让系统从配置文件读取API选择设置...")
            system = MultiTimeframeProfessionalSystem()
            
            # 测试获取市场数据
            print(f"\n1. 获取{self.symbol} {self.timeframe} 市场数据：")
            df = system.get_timeframe_data(self.symbol, self.timeframe, self.limit)
            if not df.empty:
                print(f"成功获取到{len(df)}条市场数据")
                print(df.tail())
            else:
                print("获取市场数据失败")
                return False
            
            print("\n从配置文件读取API设置测试通过！")
            return True
            
        except Exception as e:
            print(f"从配置文件读取API设置测试失败: {str(e)}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print(f"\n===== OKX API集成测试 - 开始于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")
        
        # 记录测试结果
        results = {
            "direct_api": self.test_direct_api(),
            "adapter": self.test_adapter_with_ccxt_compatibility(),
            "multi_timeframe_system": self.test_multi_timeframe_system_with_official_api(),
            "config_based_selection": self.test_config_based_api_selection()
        }
        
        # 打印测试总结
        print("\n===== 测试总结 =====")
        all_passed = True
        
        for test_name, passed in results.items():
            status = "通过" if passed else "失败"
            print(f"{test_name}: {status}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n所有测试通过！python-okx库已成功集成到系统中。")
            print("\n使用指南：")
            print("1. 通过配置文件设置（推荐）：")
            print("   在config.py文件中的OKX_CONFIG字典中设置'use_official_api': True")
            print("   这样系统会自动从配置文件读取设置，无需修改代码")
            print("2. 代码中直接设置：")
            print("   在创建系统实例时通过参数设置，例如: system = MultiTimeframeProfessionalSystem(use_official_api=True)")
            print("3. 直接使用我们封装的OKXAPI类进行更灵活的操作：")
            print("   例如: from okx_api import OKXAPI\n   okx = OKXAPI(api_key, secret_key, passphrase)")
            print("4. 示例文件位于examples/okx_api_example.py，包含更多使用案例")
        else:
            print("\n测试未全部通过，请检查错误信息并修复问题。")
        
        print(f"\n===== OKX API集成测试 - 结束于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")


if __name__ == "__main__":
    print("欢迎使用OKX API集成测试工具")
    print("此工具用于验证python-okx库与现有交易系统的集成是否正常工作")
    
    # 检查是否已安装必要的依赖
    try:
        import okx
        print("python-okx库已安装")
    except ImportError:
        print("警告：python-okx库未安装")
        print("请先运行: pip install python-okx")
        
    try:
        import ccxt
        print("ccxt库已安装")
    except ImportError:
        print("警告：ccxt库未安装")
        print("请先运行: pip install ccxt")
    
    # 运行测试
    test = TestOKXIntegration()
    test.run_all_tests()