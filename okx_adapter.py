#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OKX交易所适配器类
为使用ccxt库的现有系统提供python-okx库的兼容接口
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from datetime import datetime, timedelta
import time

# 导入我们之前创建的OKX API封装模块
from okx_api import OKXAPI, get_okx_api

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OKXAdapter:
    """OKX交易所适配器类，提供与ccxt.okx兼容的接口"""
    
    def __init__(self, api_key: str = '', secret_key: str = '', password: str = '', 
                 sandbox: bool = False, enableRateLimit: bool = True, timeout: int = 30000):
        """初始化OKX适配器
        
        Args:
            api_key: OKX API密钥
            secret_key: OKX API私钥
            password: OKX API密码（ccxt兼容参数名）
            sandbox: 是否使用测试网络（ccxt兼容参数名）
            enableRateLimit: 是否启用速率限制（ccxt兼容参数名）
            timeout: 请求超时时间（毫秒）
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = password  # ccxt使用password，我们使用passphrase
        self.is_testnet = sandbox
        self.enable_rate_limit = enableRateLimit
        self.timeout = timeout / 1000  # 转换为秒
        
        # 市场数据缓存
        self.markets = {}  # 存储市场数据，用于兼容ccxt的load_markets方法
        
        # 初始化OKX API实例
        self.okx_api = None
        self._init_api()
    
    def _init_api(self):
        """初始化OKX API"""
        try:
            # 使用单例模式获取API实例
            self.okx_api = get_okx_api(
                self.api_key, 
                self.secret_key, 
                self.passphrase, 
                self.is_testnet
            )
            
            # 模拟ccxt的load_markets行为
            self._load_markets()
            
            logger.info("OKX适配器初始化成功")
        except Exception as e:
            logger.error(f"OKX适配器初始化失败: {str(e)}")
            raise
    
    def _load_markets(self):
        """加载市场数据（模拟ccxt的load_markets方法）"""
        try:
            # 获取所有交易对
            trading_pairs = self.okx_api.get_all_trading_pairs()
            
            # 构建市场数据字典，兼容ccxt格式
            for pair in trading_pairs:
                self.markets[pair] = {
                    'id': pair,
                    'symbol': pair,
                    'base': pair.split('-')[0],
                    'quote': pair.split('-')[1] if '-' in pair else 'USDT',
                    'active': True,
                    'precision': {
                        'price': 2,
                        'amount': 6,
                        'cost': 2
                    }
                }
            
            logger.info(f"加载了{len(self.markets)}个交易对市场数据")
        except Exception as e:
            logger.error(f"加载市场数据失败: {str(e)}")
    
    def load_markets(self):
        """兼容ccxt的load_markets方法"""
        self._load_markets()
        return self.markets
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 100, 
                    since: Optional[int] = None, params: Dict = None) -> List:
        """获取OHLCV数据（K线图），兼容ccxt的fetch_ohlcv方法
        
        Args:
            symbol: 交易对
            timeframe: 时间周期
            limit: 返回的数据条数
            since: 开始时间戳（毫秒），暂不支持
            params: 额外参数，暂不支持
            
        Returns:
            List: OHLCV数据列表，格式为[[时间戳, 开盘价, 最高价, 最低价, 收盘价, 成交量], ...]
        """
        try:
            # 使用我们的OKX API获取K线数据
            klines = self.okx_api.get_klines(symbol, timeframe, limit)
            
            # 转换为ccxt格式：[[时间戳, 开盘价, 最高价, 最低价, 收盘价, 成交量], ...]
            ohlcv_data = []
            for kline in klines:
                ohlcv_data.append([
                    kline['timestamp'],  # 时间戳（毫秒）
                    kline['open'],       # 开盘价
                    kline['high'],       # 最高价
                    kline['low'],        # 最低价
                    kline['close'],      # 收盘价
                    kline['volume']      # 成交量
                ])
            
            return ohlcv_data
        except Exception as e:
            logger.error(f"获取{symbol} {timeframe} K线数据失败: {str(e)}")
            return []
    
    def fetch_ticker(self, symbol: str, params: Dict = None) -> Dict:
        """获取最新行情数据，兼容ccxt的fetch_ticker方法
        
        Args:
            symbol: 交易对
            params: 额外参数，暂不支持
            
        Returns:
            Dict: 行情数据字典
        """
        try:
            # 使用我们的OKX API获取行情数据
            ticker_data = self.okx_api.get_ticker(symbol)
            
            # 转换为ccxt格式
            if ticker_data:
                return {
                    'symbol': symbol,
                    'timestamp': ticker_data['timestamp'],
                    'datetime': ticker_data['datetime'],
                    'high': ticker_data['high'],
                    'low': ticker_data['low'],
                    'bid': None,  # python-okx提供的ticker不包含买卖盘
                    'bidVolume': None,
                    'ask': None,
                    'askVolume': None,
                    'vwap': None,
                    'open': None,
                    'close': ticker_data['last'],
                    'last': ticker_data['last'],
                    'previousClose': None,
                    'change': None,
                    'percentage': None,
                    'average': None,
                    'baseVolume': ticker_data['volume'],
                    'quoteVolume': None,
                    'info': ticker_data  # 原始数据
                }
            return {}
        except Exception as e:
            logger.error(f"获取{symbol}行情数据失败: {str(e)}")
            return {}
    
    def fetch_order_book(self, symbol: str, limit: int = 10, params: Dict = None) -> Dict:
        """获取订单簿数据，兼容ccxt的fetch_order_book方法
        
        Args:
            symbol: 交易对
            limit: 订单簿深度
            params: 额外参数，暂不支持
            
        Returns:
            Dict: 订单簿数据字典
        """
        try:
            # 使用我们的OKX API获取订单簿数据
            order_book_data = self.okx_api.get_order_book(symbol, limit)
            
            # 转换为ccxt格式
            if order_book_data:
                return {
                    'symbol': symbol,
                    'timestamp': order_book_data['timestamp'],
                    'datetime': order_book_data['datetime'],
                    'bids': order_book_data['bids'],
                    'asks': order_book_data['asks'],
                    'nonce': None,
                    'info': order_book_data  # 原始数据
                }
            return {}
        except Exception as e:
            logger.error(f"获取{symbol}订单簿数据失败: {str(e)}")
            return {}
    
    def create_order(self, symbol: str, type: str, side: str, amount: float, 
                    price: Optional[float] = None, params: Dict = None) -> Dict:
        """创建订单，兼容ccxt的create_order方法
        
        Args:
            symbol: 交易对
            type: 订单类型（'limit'或'market'）
            side: 交易方向（'buy'或'sell'）
            amount: 交易数量
            price: 交易价格（限价单）
            params: 额外参数，如'reduceOnly'，'leverage'等
            
        Returns:
            Dict: 订单创建结果
        """
        try:
            # 从params中提取额外参数
            reduce_only = params.get('reduceOnly', False) if params else False
            leverage = params.get('leverage', 1) if params else 1
            
            # 使用我们的OKX API下单
            order_result = self.okx_api.place_order(
                symbol=symbol,
                side=side,
                order_type=type,
                quantity=amount,
                price=price,
                leverage=leverage,
                reduce_only=reduce_only
            )
            
            # 转换为ccxt格式
            if order_result:
                return {
                    'id': order_result.get('ordId', ''),
                    'clientOrderId': order_result.get('clOrdId', ''),
                    'info': order_result,
                    'symbol': symbol,
                    'type': type,
                    'side': side,
                    'price': price,
                    'amount': amount,
                }
            return {}
        except Exception as e:
            logger.error(f"创建{side} {type} {symbol}订单失败: {str(e)}")
            raise
    
    def cancel_order(self, id: str, symbol: str = None, params: Dict = None) -> Dict:
        """取消订单，兼容ccxt的cancel_order方法
        
        Args:
            id: 订单ID
            symbol: 交易对
            params: 额外参数，暂不支持
            
        Returns:
            Dict: 订单取消结果
        """
        try:
            # 使用我们的OKX API取消订单
            success = self.okx_api.cancel_order(id, symbol)
            
            # 转换为ccxt格式
            return {
                'id': id,
                'symbol': symbol,
                'info': {'success': success}
            }
        except Exception as e:
            logger.error(f"取消订单{id}失败: {str(e)}")
            raise
    
    def fetch_open_orders(self, symbol: Optional[str] = None, since: Optional[int] = None, 
                          limit: Optional[int] = None, params: Dict = None) -> List:
        """获取当前挂单，兼容ccxt的fetch_open_orders方法
        
        Args:
            symbol: 交易对（可选）
            since: 开始时间戳（毫秒），暂不支持
            limit: 返回的数据条数，暂不支持
            params: 额外参数，暂不支持
            
        Returns:
            List: 挂单列表
        """
        try:
            # 使用我们的OKX API获取挂单
            open_orders = self.okx_api.get_open_orders(symbol)
            
            # 转换为ccxt格式
            ccxt_orders = []
            for order in open_orders:
                ccxt_orders.append({
                    'id': order.get('ordId', ''),
                    'clientOrderId': order.get('clOrdId', ''),
                    'datetime': datetime.fromtimestamp(int(order.get('ts', '0')) / 1000).strftime('%Y-%m-%dT%H:%M:%S'),
                    'timestamp': int(order.get('ts', '0')),
                    'lastTradeTimestamp': None,
                    'status': order.get('state', ''),
                    'symbol': order.get('instId', ''),
                    'type': order.get('ordType', ''),
                    'side': order.get('side', ''),
                    'price': float(order.get('px', '0')),
                    'amount': float(order.get('sz', '0')),
                    'filled': float(order.get('accFillSz', '0')),
                    'remaining': float(order.get('sz', '0')) - float(order.get('accFillSz', '0')),
                    'cost': None,
                    'trades': [],
                    'fee': None,
                    'info': order
                })
            
            return ccxt_orders
        except Exception as e:
            logger.error(f"获取挂单失败: {str(e)}")
            return []
    
    def fetch_balance(self, params: Dict = None) -> Dict:
        """获取账户余额，兼容ccxt的fetch_balance方法
        
        Args:
            params: 额外参数，暂不支持
            
        Returns:
            Dict: 账户余额数据
        """
        try:
            # 使用我们的OKX API获取账户余额
            balance_data = self.okx_api.get_account_balance()
            
            # 转换为ccxt格式
            if balance_data:
                balances = {'info': balance_data, 'free': {}, 'used': {}, 'total': {}}
                
                # 解析余额数据（根据OKX API返回的格式调整）
                for data in balance_data:
                    for coin in data.get('details', []):
                        currency = coin.get('ccy', '')
                        if currency:
                            balances['free'][currency] = float(coin.get('availBal', '0'))
                            balances['used'][currency] = float(coin.get('frozenBal', '0'))
                            balances['total'][currency] = float(coin.get('totalBal', '0'))
                
                return balances
            return {'info': {}, 'free': {}, 'used': {}, 'total': {}}
        except Exception as e:
            logger.error(f"获取账户余额失败: {str(e)}")
            return {'info': {}, 'free': {}, 'used': {}, 'total': {}}
    
    # 可以根据需要添加更多ccxt兼容的方法
    

# 提供一个与ccxt类似的接口，便于系统无缝切换
def get_ccxt_compatible_okx(api_key: str = '', secret_key: str = '', password: str = '', 
                           sandbox: bool = False, enableRateLimit: bool = True, timeout: int = 30000) -> OKXAdapter:
    """获取与ccxt兼容的OKX适配器实例
    
    Args:
        api_key: OKX API密钥
        secret_key: OKX API私钥
        password: OKX API密码
        sandbox: 是否使用测试网络
        enableRateLimit: 是否启用速率限制
        timeout: 请求超时时间（毫秒）
        
    Returns:
        OKXAdapter: OKX适配器实例
    """
    return OKXAdapter(api_key, secret_key, password, sandbox, enableRateLimit, timeout)