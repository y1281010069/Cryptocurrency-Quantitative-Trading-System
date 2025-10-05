#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OKX API使用示例
展示如何使用python-okx库和封装的OKXAPI模块
"""
import sys
import os
from dotenv import load_dotenv  # 用于加载环境变量

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入封装的OKX API模块
from okx_api import OKXAPI, get_okx_api


def main():
    """主函数，展示OKX API的使用方法"""
    print("===== OKX API 使用示例 =====")
    
    try:
        # 加载环境变量（如果有）
        load_dotenv()
        
        # 从环境变量或直接设置API密钥
        api_key = os.getenv('OKX_API_KEY', 'your_api_key')
        secret_key = os.getenv('OKX_API_SECRET', 'your_secret_key')
        passphrase = os.getenv('OKX_API_PASSPHRASE', 'your_passphrase')
        
        # 创建OKX API实例（如果使用测试网络，将is_testnet设为True）
        # 注意：请确保在实际环境中正确设置API密钥
        okx = OKXAPI(api_key, secret_key, passphrase, is_testnet=False)
        
        # 或者使用单例模式获取API实例
        # okx = get_okx_api(api_key, secret_key, passphrase)
        
        # 检查连接状态
        if okx.connected:
            print("OKX API连接成功！")
            
            # 1. 获取账户余额
            print("\n1. 获取账户余额：")
            balance = okx.get_account_balance()
            print(f"账户余额数据：{balance}")
            
            # 2. 获取K线数据
            print("\n2. 获取BTC-USDT 15分钟K线数据：")
            klines = okx.get_klines("BTC-USDT", "15m", limit=5)
            print(f"最近5条K线数据：")
            for kline in klines:
                print(f"时间: {kline['datetime']}, 开盘: {kline['open']}, 最高: {kline['high']}, 最低: {kline['low']}, 收盘: {kline['close']}, 成交量: {kline['volume']}")
            
            # 3. 获取最新行情
            print("\n3. 获取BTC-USDT最新行情：")
            ticker = okx.get_ticker("BTC-USDT")
            print(f"最新价格: {ticker.get('last', 'N/A')}, 24h最高价: {ticker.get('high', 'N/A')}, 24h最低价: {ticker.get('low', 'N/A')}, 24h成交量: {ticker.get('volume', 'N/A')}")
            
            # 4. 获取订单簿
            print("\n4. 获取BTC-USDT订单簿（5档深度）：")
            order_book = okx.get_order_book("BTC-USDT", depth=5)
            print(f"卖单：")
            for ask in order_book.get('asks', [])[:5]:
                print(f"价格: {ask[0]}, 数量: {ask[1]}")
            print(f"买单：")
            for bid in order_book.get('bids', [])[:5]:
                print(f"价格: {bid[0]}, 数量: {bid[1]}")
            
            # 5. 获取所有交易对
            print("\n5. 获取OKX交易所支持的交易对（前10个）：")
            trading_pairs = okx.get_all_trading_pairs()
            print(f"前10个交易对: {trading_pairs[:10]}")
            print(f"总共有{len(trading_pairs)}个交易对")
            
            # 以下操作需要真实API密钥且有资金才能执行
            # 请谨慎使用，避免产生实际交易
            
            # # 6. 设置杠杆（合约交易）
            # print("\n6. 设置BTC-USDT杠杆（仅合约交易可用）：")
            # # 注意：此操作需要先开通合约交易权限
            # # leverage_set = okx.set_leverage("BTC-USDT", 10)
            # # print(f"杠杆设置结果: {'成功' if leverage_set else '失败'}")
            # 
            # # 7. 下单（请谨慎使用，会产生实际交易）
            # print("\n7. 下单示例（已注释，避免误操作）：")
            # # 以下代码会产生实际交易，请谨慎取消注释
            # # order_result = okx.place_order(
            # #     symbol="BTC-USDT",  # 交易对
            # #     side="buy",         # 买入方向（buy/sell）
            # #     order_type="limit", # 订单类型（limit/market）
            # #     quantity=0.0001,    # 数量
            # #     price=30000         # 价格（限价单）
            # # )
            # # print(f"下单结果: {order_result}")
            # 
            # # 8. 获取当前挂单
            # print("\n8. 获取当前挂单：")
            # # open_orders = okx.get_open_orders(symbol="BTC-USDT")
            # # print(f"当前挂单数量: {len(open_orders)}")
            # # for order in open_orders:
            # #     print(f"订单ID: {order['ordId']}, 状态: {order['state']}, 价格: {order.get('px', 'N/A')}, 数量: {order.get('sz', 'N/A')}")
            # 
            # # 9. 获取当前持仓
            # print("\n9. 获取当前持仓：")
            # # positions = okx.get_position()
            # # print(f"当前持仓数量: {len(positions)}")
            # # for position in positions:
            # #     print(f"交易对: {position['instId']}, 持仓数量: {position['pos']}, 平均价格: {position.get('avgPx', 'N/A')}")
            
        else:
            print("OKX API连接失败，请检查API密钥和网络连接。")
            print("注意：在实际使用时，请确保API密钥正确设置，并且已经添加IP白名单（如果有启用）。")
            
    except Exception as e:
        print(f"发生错误：{str(e)}")
        print("提示：")
        print("1. 请确保已安装必要的依赖：pip install python-okx python-dotenv")
        print("2. 请确保API密钥正确，并且已经在OKX网站上启用API")
        print("3. 如果使用模拟盘，请将is_testnet参数设置为True")
        print("4. 如需执行交易操作，请确保API有相应的权限")
    

if __name__ == "__main__":
    main()