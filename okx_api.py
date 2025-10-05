#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OKX交易所API封装模块
使用官方python-okx库提供的功能，为交易系统提供统一的接口
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
import time
from datetime import datetime, timedelta

# 导入官方python-okx库
from okx import Account, Market, Trade, PublicData

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OKXAPI:
    """OKX交易所API封装类"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str, is_testnet: bool = False):
        """初始化OKX API连接
        
        Args:
            api_key: OKX API密钥
            secret_key: OKX API私钥
            passphrase: OKX API密码
            is_testnet: 是否使用测试网络
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.is_testnet = is_testnet
        
        # API客户端实例
        self.account_api = None
        self.market_api = None
        self.trade_api = None
        self.public_api = None
        
        # 连接状态
        self.connected = False
        
        # 初始化连接
        self._init_apis()
    
    def _init_apis(self):
        """初始化各个API客户端"""
        try:
            # 创建API客户端实例
            flag = "1" if self.is_testnet else "0"  # 0: 实盘，1: 模拟盘
            
            self.account_api = Account(flag=flag, api_key=self.api_key, secret_key=self.secret_key, passphrase=self.passphrase)
            self.market_api = Market(flag=flag, api_key=self.api_key, secret_key=self.secret_key, passphrase=self.passphrase)
            self.trade_api = Trade(flag=flag, api_key=self.api_key, secret_key=self.secret_key, passphrase=self.passphrase)
            self.public_api = PublicData(flag=flag, api_key=self.api_key, secret_key=self.secret_key, passphrase=self.passphrase)
            
            # 验证连接
            self.get_account_balance()
            
            self.connected = True
            logger.info("OKX API连接成功")
            
        except Exception as e:
            self.connected = False
            logger.error(f"OKX API连接失败: {str(e)}")
            raise
    
    def get_account_balance(self) -> Dict:
        """获取账户余额
        
        Returns:
            Dict: 账户余额信息
        """
        try:
            result = self.account_api.get_account_balance()
            if result['code'] == '0':
                return result['data']
            else:
                logger.error(f"获取账户余额失败: {result['msg']}")
                return {}
        except Exception as e:
            logger.error(f"获取账户余额异常: {str(e)}")
            raise
    
    def get_klines(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """获取K线数据
        
        Args:
            symbol: 交易对，如 BTC-USDT
            timeframe: 时间周期，如 1m, 5m, 15m, 1h, 4h, 1d
            limit: 返回数据的数量
            
        Returns:
            List[Dict]: K线数据列表
        """
        try:
            # 将ccxt格式的时间周期转换为OKX格式
            timeframe_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1H', '2h': '2H', '4h': '4H', '6h': '6H', '12h': '12H',
                '1d': '1D', '1w': '1W', '1M': '1M'
            }
            
            okx_timeframe = timeframe_map.get(timeframe.lower(), timeframe)
            
            result = self.market_api.get_candlesticks(instId=symbol, bar=okx_timeframe, limit=limit)
            
            if result['code'] == '0':
                # 格式化K线数据，使其与ccxt返回格式兼容
                klines = []
                for kline in result['data']:
                    klines.append({
                        'timestamp': int(kline[0]),
                        'datetime': datetime.fromtimestamp(int(kline[0]) / 1000).strftime('%Y-%m-%dT%H:%M:%S'),
                        'open': float(kline[1]),
                        'high': float(kline[2]),
                        'low': float(kline[3]),
                        'close': float(kline[4]),
                        'volume': float(kline[5]),
                        'symbol': symbol
                    })
                return klines
            else:
                logger.error(f"获取K线数据失败: {result['msg']}")
                return []
        except Exception as e:
            logger.error(f"获取K线数据异常: {str(e)}")
            raise
    
    def get_ticker(self, symbol: str) -> Dict:
        """获取最新行情
        
        Args:
            symbol: 交易对，如 BTC-USDT
            
        Returns:
            Dict: 行情数据
        """
        try:
            result = self.market_api.get_ticker(instId=symbol)
            
            if result['code'] == '0':
                ticker_data = result['data'][0]
                return {
                    'symbol': symbol,
                    'last': float(ticker_data['last']),
                    'high': float(ticker_data['high24h']),
                    'low': float(ticker_data['low24h']),
                    'volume': float(ticker_data['vol24h']),
                    'timestamp': int(ticker_data['ts']),
                    'datetime': datetime.fromtimestamp(int(ticker_data['ts']) / 1000).strftime('%Y-%m-%dT%H:%M:%S')
                }
            else:
                logger.error(f"获取行情数据失败: {result['msg']}")
                return {}
        except Exception as e:
            logger.error(f"获取行情数据异常: {str(e)}")
            raise
    
    def get_order_book(self, symbol: str, depth: int = 10) -> Dict:
        """获取订单簿
        
        Args:
            symbol: 交易对，如 BTC-USDT
            depth: 订单簿深度
            
        Returns:
            Dict: 订单簿数据
        """
        try:
            result = self.market_api.get_orderbook(instId=symbol, sz=depth)
            
            if result['code'] == '0':
                order_book_data = result['data'][0]
                return {
                    'symbol': symbol,
                    'asks': [[float(ask[0]), float(ask[1])] for ask in order_book_data['asks']],
                    'bids': [[float(bid[0]), float(bid[1])] for bid in order_book_data['bids']],
                    'timestamp': int(order_book_data['ts']),
                    'datetime': datetime.fromtimestamp(int(order_book_data['ts']) / 1000).strftime('%Y-%m-%dT%H:%M:%S')
                }
            else:
                logger.error(f"获取订单簿失败: {result['msg']}")
                return {}
        except Exception as e:
            logger.error(f"获取订单簿异常: {str(e)}")
            raise
    
    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: Optional[float] = None, 
                    leverage: int = 1, reduce_only: bool = False) -> Dict:
        """下单
        
        Args:
            symbol: 交易对，如 BTC-USDT
            side: 交易方向，buy或sell
            order_type: 订单类型，market或limit
            quantity: 数量
            price: 价格（限价单）
            leverage: 杠杆倍数
            reduce_only: 是否仅减仓
            
        Returns:
            Dict: 下单结果
        """
        try:
            # 设置杠杆（如果需要）
            if leverage > 1:
                self.set_leverage(symbol, leverage)
            
            # 构建订单参数
            order_params = {
                'instId': symbol,
                'tdMode': 'cross' if leverage > 1 else 'cash',  # 保证金模式
                'side': side.upper(),
                'ordType': order_type.upper(),
                'sz': str(quantity),
                'reduceOnly': 'true' if reduce_only else 'false'
            }
            
            # 添加价格（如果是限价单）
            if order_type.lower() == 'limit' and price:
                order_params['px'] = str(price)
            
            # 下单
            result = self.trade_api.place_order(**order_params)
            
            if result['code'] == '0':
                logger.info(f"下单成功: {side} {symbol} {quantity} @ {price or 'market'}")
                return result['data'][0]
            else:
                logger.error(f"下单失败: {result['msg']}")
                return {}
        except Exception as e:
            logger.error(f"下单异常: {str(e)}")
            raise
    
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """设置杠杆倍数
        
        Args:
            symbol: 交易对，如 BTC-USDT
            leverage: 杠杆倍数
            
        Returns:
            bool: 是否设置成功
        """
        try:
            result = self.account_api.set_leverage(instId=symbol, lever=str(leverage), mgnMode='cross')
            
            if result['code'] == '0':
                logger.info(f"设置杠杆成功: {symbol} {leverage}x")
                return True
            else:
                logger.error(f"设置杠杆失败: {result['msg']}")
                return False
        except Exception as e:
            logger.error(f"设置杠杆异常: {str(e)}")
            raise
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """获取当前挂单
        
        Args:
            symbol: 交易对，如 BTC-USDT（可选）
            
        Returns:
            List[Dict]: 挂单列表
        """
        try:
            params = {}
            if symbol:
                params['instId'] = symbol
            
            result = self.trade_api.get_open_orders(**params)
            
            if result['code'] == '0':
                return result['data']
            else:
                logger.error(f"获取挂单失败: {result['msg']}")
                return []
        except Exception as e:
            logger.error(f"获取挂单异常: {str(e)}")
            raise
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """取消订单
        
        Args:
            order_id: 订单ID
            symbol: 交易对，如 BTC-USDT
            
        Returns:
            bool: 是否取消成功
        """
        try:
            result = self.trade_api.cancel_order(instId=symbol, ordId=order_id)
            
            if result['code'] == '0':
                logger.info(f"取消订单成功: {order_id}")
                return True
            else:
                logger.error(f"取消订单失败: {result['msg']}")
                return False
        except Exception as e:
            logger.error(f"取消订单异常: {str(e)}")
            raise
    
    def get_position(self, symbol: Optional[str] = None) -> List[Dict]:
        """获取当前持仓
        
        Args:
            symbol: 交易对，如 BTC-USDT（可选）
            
        Returns:
            List[Dict]: 持仓列表
        """
        try:
            params = {'mgnMode': 'cross'}
            if symbol:
                params['instId'] = symbol
            
            result = self.account_api.get_positions(**params)
            
            if result['code'] == '0':
                # 过滤掉空持仓
                return [pos for pos in result['data'] if float(pos['pos']) > 0]
            else:
                logger.error(f"获取持仓失败: {result['msg']}")
                return []
        except Exception as e:
            logger.error(f"获取持仓异常: {str(e)}")
            raise
    
    def get_all_trading_pairs(self) -> List[str]:
        """获取所有交易对
        
        Returns:
            List[str]: 交易对列表
        """
        try:
            # 获取现货交易对
            result = self.market_api.get_instruments(instType='SPOT')
            
            if result['code'] == '0':
                return [item['instId'] for item in result['data']]
            else:
                logger.error(f"获取交易对失败: {result['msg']}")
                return []
        except Exception as e:
            logger.error(f"获取交易对异常: {str(e)}")
            raise


# 单例模式，方便全局使用
def get_okx_api(api_key: str = None, secret_key: str = None, passphrase: str = None, is_testnet: bool = False) -> OKXAPI:
    """获取OKX API实例（单例模式）
    
    Args:
        api_key: OKX API密钥
        secret_key: OKX API私钥
        passphrase: OKX API密码
        is_testnet: 是否使用测试网络
        
    Returns:
        OKXAPI: OKX API实例
    """
    global _okx_api_instance
    
    # 如果没有实例或参数发生变化，则创建新实例
    if not hasattr(get_okx_api, '_okx_api_instance') or \
       (api_key and api_key != getattr(get_okx_api, '_last_api_key', None)) or \
       (secret_key and secret_key != getattr(get_okx_api, '_last_secret_key', None)) or \
       (passphrase and passphrase != getattr(get_okx_api, '_last_passphrase', None)) or \
       is_testnet != getattr(get_okx_api, '_last_is_testnet', False):
        
        # 更新最后使用的参数
        setattr(get_okx_api, '_last_api_key', api_key)
        setattr(get_okx_api, '_last_secret_key', secret_key)
        setattr(get_okx_api, '_last_passphrase', passphrase)
        setattr(get_okx_api, '_last_is_testnet', is_testnet)
        
        # 创建新实例
        setattr(get_okx_api, '_okx_api_instance', OKXAPI(api_key, secret_key, passphrase, is_testnet))
    
    return getattr(get_okx_api, '_okx_api_instance', None)