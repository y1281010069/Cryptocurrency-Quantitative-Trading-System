from datetime import datetime

class OKXControl:
    def __init__(self):
        # 初始化API客户端
        self.okx_exchange = None  # CCXT客户端
        self.okx_official_api = None  # OKX官方包API客户端
        self.okx_account_api = None  # 账户相关API
        self.okx_public_api = None  # 公共API
    
    def set_api_clients(self, okx_public_api=None, okx_account_api=None, okx_official_api=None, okx_exchange=None):
        """设置OKX API客户端实例"""
        self.okx_public_api = okx_public_api
        self.okx_account_api = okx_account_api
        self.okx_official_api = okx_official_api
        self.okx_exchange = okx_exchange
        # 兼容处理：如果没有设置okx_official_api但设置了okx_account_api，使用okx_account_api作为okx_official_api
        if not self.okx_official_api and okx_account_api:
            self.okx_official_api = okx_account_api
        print(f"OKXControl API客户端实例已设置 - Public API: {bool(okx_public_api)}, Account API: {bool(okx_account_api)}, Official API: {bool(okx_official_api)}, Exchange: {bool(okx_exchange)}")


    
    def get_balances(self, use_ccxt=False):
        """获取账户余额"""
        print("======= 开始执行get_balances方法 =======")
        print(f"参数: use_ccxt={use_ccxt}")
        print(f"可用API客户端 - OKX官方API: {bool(self.okx_official_api)}, CCXT: {bool(self.okx_exchange)}, Account API: {bool(self.okx_account_api)}")
        
        try:
            # 先尝试使用get_detailed_okx_balance方法
            if self.okx_account_api:
                print("尝试使用get_detailed_okx_balance方法获取余额...")
                detailed_result = self.get_detailed_okx_balance()
                print(f"get_detailed_okx_balance返回: {detailed_result.get('success')}, 错误: {detailed_result.get('error')}")
                
                if detailed_result.get('success'):
                    # 转换详细余额数据为前端需要的格式
                    all_balances = []
                    data = detailed_result.get('data', {})
                    
                    # 合并所有类型的余额
                    for balance_type in ['spot_balances', 'margin_balances', 'funding_balances']:
                        all_balances.extend(data.get(balance_type, []))
                    
                    # 转换为前端需要的格式
                    formatted_balances = []
                    for asset in all_balances:
                        formatted_balances.append({
                            'currency': asset.get('currency', ''),
                            'amount': asset.get('total_balance', 0),
                            'available': asset.get('available_balance', 0),
                            'frozen': asset.get('frozen_balance', 0)
                        })
                    
                    print(f"从detailed_okx_balance转换得到 {len(formatted_balances)} 条余额记录")
                    return formatted_balances
                else:
                    print("get_detailed_okx_balance执行失败，尝试其他方法")
            
            # 如果指定使用CCXT且有CCXT客户端
            if use_ccxt and self.okx_exchange:
                print("使用CCXT获取余额")
                balances = self.okx_exchange.fetch_balance()
                print(f"CCXT返回数据类型: {type(balances)}, 包含键: {balances.keys()}")
                # 转换为统一格式
                formatted = self._format_balances(balances)
                print(f"CCXT格式转换后得到 {len(formatted)} 条余额记录")
                return formatted
            # 如果有OKX官方API客户端
            elif self.okx_official_api:
                print("使用OKX官方包获取余额")
                result = self.okx_official_api.get_account_balance()
                print(f"OKX官方API返回数据: {result}")
                formatted = self._format_official_balances(result)
                print(f"官方API格式转换后得到 {len(formatted)} 条余额记录")
                return formatted
            else:
                raise ValueError("没有可用的API客户端")
        except Exception as e:
            print(f"获取余额时发生错误: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            return {'error': str(e), 'balances': []}
        finally:
            print("======= get_balances方法执行结束 =======")
    

    
    def get_orders(self, symbol=None, status=None):
        """获取订单列表"""
        try:
            if self.okx_official_api:
                # 使用OKX官方包获取订单
                params = {}
                if symbol:
                    params['instId'] = symbol
                if status:
                    params['state'] = status
                
                result = self.okx_official_api.get_orders(params)
                return self._format_orders(result)
            else:
                raise ValueError("没有可用的OKX API客户端")
        except Exception as e:
            print(f"获取订单时发生错误: {e}")
            return {'error': str(e), 'orders': []}
    
    def get_stop_orders(self):
        """获取止损止盈订单"""
        try:
            if self.okx_official_api:
                # 使用OKX官方包获取止损止盈订单
                result = self.okx_official_api.get_stop_orders()
                return self._format_stop_orders(result)
            else:
                raise ValueError("没有可用的OKX API客户端")
        except Exception as e:
            print(f"获取止损止盈订单时发生错误: {e}")
            return {'error': str(e), 'stop_orders': []}
    
    def get_history_positions(self, limit=100):
        """获取历史持仓"""
        try:
            if self.okx_official_api:
                # 使用OKX官方包获取历史持仓
                result = self.okx_official_api.get_history_positions({'limit': limit})
                return self._format_history_positions(result)
            else:
                raise ValueError("没有可用的OKX API客户端")
        except Exception as e:
            print(f"获取历史持仓时发生错误: {e}")
            return {'error': str(e), 'history_positions': []}
    
    # 格式化方法
    def _format_balances(self, ccxt_balances):
        """格式化CCXT返回的余额数据"""
        formatted = []
        # 提取非零余额
        if 'total' in ccxt_balances:
            for currency, amount in ccxt_balances['total'].items():
                if amount > 0:
                    formatted.append({
                        'currency': currency,
                        'amount': amount,
                        'available': ccxt_balances['free'].get(currency, 0),
                        'frozen': ccxt_balances['used'].get(currency, 0)
                    })
        return formatted
    
    def _format_official_balances(self, result):
        """格式化OKX官方API返回的余额数据"""
        formatted = []
        # 根据OKX官方API返回的数据格式处理
        if isinstance(result, dict) and result.get('code') == '0' and 'data' in result:
            for item in result['data']:
                # 处理不同格式的数据返回
                currency = item.get('ccy', item.get('currency', ''))
                available = float(item.get('cashBal', item.get('available', 0)))
                frozen = float(item.get('frozenBal', item.get('frozen', 0)))
                formatted.append({
                    'currency': currency,
                    'amount': available + frozen,
                    'available': available,
                    'frozen': frozen
                })
        return formatted
    
    def _format_positions(self, result):
        """格式化持仓数据"""
        formatted = []
        if isinstance(result, dict) and result.get('code') == '0' and 'data' in result:
            for item in result['data']:
                # 过滤掉没有持仓量的记录
                if float(item.get('pos', 0)) != 0:
                    formatted.append({
                        'symbol': item.get('instId'),
                        'side': item.get('side'),
                        'position': float(item.get('pos', 0)),
                        'avg_price': float(item.get('avgPx', 0)),
                        'unrealized_pnl': float(item.get('upl', 0)),
                        'liquidation_price': float(item.get('liqPx', 0)),
                        'leverage': float(item.get('lever', 0))
                    })
        return formatted
    
    def _format_orders(self, result):
        """格式化订单数据"""
        formatted = []
        if isinstance(result, dict) and result.get('code') == '0' and 'data' in result:
            for item in result['data']:
                formatted.append({
                    'order_id': item.get('ordId'),
                    'symbol': item.get('instId'),
                    'side': item.get('side'),
                    'price': float(item.get('px', 0)),
                    'quantity': float(item.get('sz', 0)),
                    'type': item.get('ordType'),
                    'status': item.get('state'),
                    'created_at': item.get('cTime')
                })
        return formatted
    
    def _format_stop_orders(self, result):
        """格式化止损止盈订单数据"""
        formatted = []
        if isinstance(result, dict) and result.get('code') == '0' and 'data' in result:
            for item in result['data']:
                formatted.append({
                    'order_id': item.get('ordId'),
                    'symbol': item.get('instId'),
                    'side': item.get('side'),
                    'trigger_price': float(item.get('triggerPx', 0)),
                    'order_price': float(item.get('px', 0)),
                    'quantity': float(item.get('sz', 0)),
                    'type': item.get('ordType'),
                    'status': item.get('state'),
                    'created_at': item.get('cTime')
                })
        return formatted
    
    def _format_history_positions(self, result):
        """格式化历史持仓数据"""
        formatted = []
        if isinstance(result, dict) and result.get('code') == '0' and 'data' in result:
            for item in result['data']:
                formatted.append({
                    'symbol': item.get('instId'),
                    'side': item.get('side'),
                    'quantity': float(item.get('pos', 0)),
                    'entry_price': float(item.get('avgPx', 0)),
                    'exit_price': float(item.get('closeAvgPx', 0)),
                    'pnl': float(item.get('upl', 0)),
                    'pnl_ratio': float(item.get('uplRatio', 0)) * 100 if item.get('uplRatio') else 0,
                    'open_time': item.get('openTime'),
                    'close_time': item.get('closeTime')
                })
        return formatted
    
    # 从okx_utils.py合并的方法
    def process_balance_asset(self, asset, prices_data=None):
        """处理单个资产余额数据"""
        # 初始化处理后的资产数据
        processed_asset = {
            'currency': asset.get('ccy', asset.get('currency', '')),
            'total_balance': float(asset.get('totalBal', asset.get('balance', 0))),
            'available_balance': float(asset.get('availBal', asset.get('available', 0))),
            'frozen_balance': float(asset.get('frozenBal', asset.get('frozen', 0))),
            'usdt_value': 0,
            'asset_name': self.get_asset_name(asset.get('ccy', asset.get('currency', '')))
        }
        
        # 计算USDT价值
        currency = processed_asset['currency']
        if currency == 'USDT':
            processed_asset['usdt_value'] = processed_asset['total_balance']
        elif prices_data and currency in prices_data:
            processed_asset['usdt_value'] = processed_asset['total_balance'] * prices_data[currency]
        
        return processed_asset
    
    def get_okx_balance(self):
        """获取OKX账户余额"""
        try:
            print("=== 开始获取OKX账户余额 ===")
            
            # 优先使用OKX官方API
            if self.okx_account_api:
                print("使用OKX官方AccountAPI获取余额数据...")
                result = self.okx_account_api.get_account_balance()
                # 确保返回数据是有效的
                if 'data' not in result:
                    print("警告: 官方API返回格式不正确")
                    return []
                
                formatted_balances = []
                for currency_data in result['data']:
                    # 遍历每种货币
                    for balance_item in currency_data.get('details', []):
                        total_balance = float(balance_item.get('eq', '0'))
                        if total_balance > 0:
                            currency = balance_item.get('ccy', '')
                            available = float(balance_item.get('availBal', '0'))
                            used = float(balance_item.get('frozenBal', '0'))
                            
                            formatted_balances.append({
                                'currency': currency,
                                'balance': total_balance,
                                'available': available,
                                'used': used,
                                'currency_name': self.get_asset_name(currency)
                            })
                
                # 按余额降序排序
                formatted_balances.sort(key=lambda x: x['balance'], reverse=True)
                
                print(f"=== OKX账户余额获取成功(官方API)，共 {len(formatted_balances)} 种资产 ===")
                return formatted_balances
            elif self.okx_exchange:
                # 备用：使用ccxt API获取余额
                print("使用CCXT API获取余额数据...")
                balance = self.okx_exchange.fetch_balance()
                
                formatted_balances = []
                
                # 检查余额数据结构
                if 'total' in balance:
                    total_balances = balance['total']
                    for currency, amount in total_balances.items():
                        if float(amount) > 0:
                            # 获取可用余额
                            free_amount = float(balance.get('free', {}).get(currency, '0'))
                            # 获取冻结余额
                            used_amount = float(balance.get('used', {}).get(currency, '0'))
                            
                            formatted_balances.append({
                                'currency': currency,
                                'balance': float(amount),
                                'available': free_amount,
                                'used': used_amount,
                                'currency_name': self.get_currency_name(currency)
                            })
                else:
                    # 处理其他可能的余额数据结构
                    for currency, info in balance.items():
                        if isinstance(info, dict) and 'total' in info:
                            amount = float(info['total'])
                            if amount > 0:
                                free_amount = float(info.get('free', '0'))
                                used_amount = float(info.get('used', '0'))
                                
                                formatted_balances.append({
                                    'currency': currency,
                                    'balance': amount,
                                    'available': free_amount,
                                    'used': used_amount,
                                    'currency_name': self.get_currency_name(currency)
                                })
                
                # 按余额降序排序
                formatted_balances.sort(key=lambda x: x['balance'], reverse=True)
                
                print(f"=== OKX账户余额获取成功(CCXT)，共 {len(formatted_balances)} 种资产 ===")
                return formatted_balances
            else:
                raise Exception("没有可用的API客户端")
            
        except Exception as e:
            print(f"=== 获取OKX账户余额时发生错误: {str(e)} ===")
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            return []
    
    def get_okx_open_orders(self, symbol=None):
        """获取OKX交易所的当前挂单数据，使用orders-pending接口"""
        try:
            print("=== 开始获取OKX挂单数据 ===")
            
            # 优先使用OKX官方API
            if self.okx_official_api:
                print("使用OKX官方API /api/v5/trade/orders-pending获取挂单数据...")
                # 构建参数 - 使用get_order_list方法调用orders-pending接口
                params = {
                    'instType': 'SWAP',  # 指定合约类型为永续合约
                    'limit': '100'  # 获取最多100条记录
                }
                if symbol:
                    params['instId'] = symbol
                
                # 使用get_order_list方法调用orders-pending接口
                result = self.okx_official_api.get_order_list(**params)
                
                # 确保返回数据是有效的
                if not isinstance(result, dict) or result.get('code') != '0' or 'data' not in result:
                    error_msg = result.get('msg', 'Unknown error') if isinstance(result, dict) else str(result)
                    print(f"警告: 官方API返回格式不正确或请求失败: {error_msg}")
                    return []
                
                formatted_orders = []
                for order in result['data']:
                    # orders-pending接口返回的就是未成交订单，无需额外过滤
                    # 格式化时间
                    c_time = order.get('cTime', '')
                    if c_time:
                        # OKX API 返回的时间戳是毫秒级
                        datetime_obj = datetime.fromtimestamp(int(c_time) / 1000)
                        datetime_str = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        datetime_str = ''
                    
                    # 格式化订单数据
                    formatted_order = {
                        'order_id': order.get('ordId', ''),
                        'symbol': order.get('instId', ''),
                        'type': order.get('ordType', ''),
                        'side': order.get('side', ''),
                        'price': float(order.get('px', '0')),
                        'amount': float(order.get('sz', '0')),
                        'remaining': float(order.get('sz', '0')) - float(order.get('accFillSz', '0')),
                        'filled': float(order.get('accFillSz', '0')),
                        'status': order.get('state', ''),
                        'created_at': datetime_str,
                        'base_asset': order.get('instId', '').split('-')[0] if '-' in order.get('instId', '') else '',
                        'quote_asset': order.get('instId', '').split('-')[1] if '-' in order.get('instId', '') else ''
                    }
                    formatted_orders.append(formatted_order)
                
                print(f"=== OKX挂单数据获取成功(官方API)，共 {len(formatted_orders)} 条订单 ===")
                return formatted_orders
            elif self.okx_exchange:
                # 备用：使用ccxt API获取挂单数据
                print("使用CCXT API获取挂单数据...")
                open_orders = self.okx_exchange.fetch_open_orders(symbol)
                
                formatted_orders = []
                for order in open_orders:
                    # 跳过模拟订单
                    if order.get('info', {}).get('tag') == '模拟订单':
                        continue
                    
                    # 格式化时间
                    timestamp = order.get('timestamp')
                    if timestamp:
                        datetime_obj = datetime.fromtimestamp(timestamp / 1000)
                        datetime_str = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        datetime_str = ''
                    
                    # 格式化订单数据
                    formatted_order = {
                        'order_id': order.get('id', ''),
                        'symbol': order.get('symbol', ''),
                        'type': order.get('type', ''),
                        'side': order.get('side', ''),
                        'price': float(order.get('price', '0')),
                        'amount': float(order.get('amount', '0')),
                        'remaining': float(order.get('remaining', '0')),
                        'filled': float(order.get('filled', '0')),
                        'status': order.get('status', ''),
                        'created_at': datetime_str,
                        'base_asset': order.get('symbol', '').split('/')[0] if '/' in order.get('symbol', '') else '',
                        'quote_asset': order.get('symbol', '').split('/')[1] if '/' in order.get('symbol', '') else ''
                    }
                    formatted_orders.append(formatted_order)
                
                print(f"=== OKX挂单数据获取成功(CCXT)，共 {len(formatted_orders)} 条订单 ===")
                return formatted_orders
            else:
                raise Exception("没有可用的API客户端")
            
        except Exception as e:
            print(f"=== 获取OKX挂单数据时发生错误: {str(e)} ====")
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            return []
    
    def cancel_okx_order(self, order_id, symbol):
        """取消OKX交易所的挂单"""
        try:
            print(f"=== 开始取消OKX挂单: {order_id} ===")
            
            # 优先使用OKX官方API
            if self.okx_official_api:
                print("使用OKX官方API取消订单...")
                result = self.okx_official_api.cancel_order(
                    instId=symbol,
                    ordId=order_id
                )
                
                # 检查取消结果
                if isinstance(result, dict) and result.get('code') == '0':
                    print(f"=== 取消OKX挂单成功(官方API): {order_id} ===")
                    return {
                        'success': True,
                        'message': '订单取消成功',
                        'data': result.get('data', {})
                    }
                else:
                    error_msg = result.get('msg', 'Unknown error') if isinstance(result, dict) else str(result)
                    print(f"=== 取消OKX挂单失败(官方API): {error_msg} ===")
                    return {
                        'success': False,
                        'message': f'取消订单失败: {error_msg}',
                        'data': {}
                    }
            elif self.okx_exchange:
                # 备用：使用ccxt API取消订单
                print("使用CCXT API取消订单...")
                result = self.okx_exchange.cancel_order(order_id, symbol)
                print(f"=== 取消OKX挂单成功(CCXT): {order_id} ===")
                return {
                    'success': True,
                    'message': '订单取消成功',
                    'data': result
                }
            else:
                raise Exception("没有可用的API客户端")
            
        except Exception as e:
            print(f"=== 取消OKX挂单时发生错误: {str(e)} ===")
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            return {
                'success': False,
                'message': f'取消订单时发生异常: {str(e)}',
                'data': {}
            }
    
    def modify_okx_order(self, order_id, symbol, new_price=None, new_quantity=None):
        """修改OKX交易所的挂单"""
        try:
            print(f"=== 开始修改OKX挂单: {order_id} ===")
            
            # 检查修改参数
            if new_price is None and new_quantity is None:
                print(f"=== 无需修改OKX挂单: {order_id} ===")
                return {
                    'success': True,
                    'message': '无需修改订单（无修改参数）',
                    'data': {}
                }
            
            # 优先使用OKX官方API
            if self.okx_official_api:
                print("使用OKX官方API修改订单...")
                
                # 构建修改参数
                params = {
                    'instId': symbol,
                    'ordId': order_id
                }
                
                if new_price is not None:
                    params['newPx'] = str(new_price)
                if new_quantity is not None:
                    params['newSz'] = str(new_quantity)
                
                # 发送修改订单请求
                result = self.okx_official_api.amend_order(**params)
                
                # 检查修改结果
                if isinstance(result, dict) and result.get('code') == '0':
                    print(f"=== 修改OKX挂单成功(官方API): {order_id} ===")
                    return {
                        'success': True,
                        'message': '订单修改成功',
                        'data': result.get('data', {})
                    }
                else:
                    error_msg = result.get('msg', 'Unknown error') if isinstance(result, dict) else str(result)
                    print(f"=== 修改OKX挂单失败(官方API): {error_msg} ===")
                    return {
                        'success': False,
                        'message': f'修改订单失败: {error_msg}',
                        'data': {}
                    }
            elif self.okx_exchange:
                # 备用：使用ccxt API修改订单
                print("使用CCXT API修改订单...")
                params = {}
                if new_price is not None:
                    params['price'] = new_price
                if new_quantity is not None:
                    params['amount'] = new_quantity
                
                result = self.okx_exchange.edit_order(order_id, symbol, **params)
                print(f"=== 修改OKX挂单成功(CCXT): {order_id} ===")
                return {
                    'success': True,
                    'message': '订单修改成功',
                    'data': result
                }
            else:
                raise Exception("没有可用的API客户端")
            
        except Exception as e:
            print(f"=== 修改OKX挂单时发生错误: {str(e)} ===")
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            return {
                'success': False,
                'message': f'修改订单时发生异常: {str(e)}',
                'data': {}
            }
    
    def get_asset_name(self, asset_code):
        """获取加密货币的完整名称"""
        asset_names = {
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'USDT': 'Tether',
            'USDC': 'USD Coin',
            'BNB': 'Binance Coin',
            'ADA': 'Cardano',
            'SOL': 'Solana',
            'XRP': 'Ripple',
            'DOT': 'Polkadot',
            'DOGE': 'Dogecoin',
            'AVAX': 'Avalanche',
            'LINK': 'Chainlink',
            'UNI': 'Uniswap',
            'LTC': 'Litecoin',
            'BCH': 'Bitcoin Cash',
            'ALGO': 'Algorand',
            'MATIC': 'Polygon',
            'TRX': 'Tron',
            'ETC': 'Ethereum Classic',
            'XLM': 'Stellar'
        }
        return asset_names.get(asset_code.upper(), asset_code)
    
    def get_detailed_okx_balance(self):
        """获取OKX详细账户余额数据"""
        print("======= 开始执行get_detailed_okx_balance方法 =======")
        try:
            print(f"OKX账户API初始化状态: {bool(self.okx_account_api)}")
            
            if not self.okx_account_api:
                raise ValueError("OKX账户API未初始化")
            
            # 获取OKX账户余额
            print("调用OKX账户API获取余额数据...")
            response = self.okx_account_api.get_account_balance()
            print(f"API响应类型: {type(response)}")
            print(f"API响应内容: {response}")
            
            # 检查响应格式
            if not isinstance(response, dict):
                raise ValueError(f"API返回格式错误，期望dict但得到: {type(response)}")
            
            print(f"API响应code: {response.get('code')}")
            print(f"API响应msg: {response.get('msg')}")
            
            if response.get('code') != '0':
                raise ValueError(f"API返回错误: {response.get('msg', 'Unknown error')}")
            
            # 处理余额数据
            balances_data = response.get('data', [])
            print(f"余额数据类型: {type(balances_data)}")
            print(f"余额数据长度: {len(balances_data) if isinstance(balances_data, list) else 'N/A'}")
            
            if isinstance(balances_data, list):
                print(f"前3条余额数据样本: {balances_data[:3]}")
            
            # 账户总资产结构
            account_balances = {
                'total_usdt_value': 0,
                'spot_balances': [],
                'margin_balances': [],
                'funding_balances': [],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 遍历处理各类资产
            asset_count = 0
            if isinstance(balances_data, list):
                for balance_item in balances_data:
                    print(f"处理余额项: {balance_item}")
                    # 检查是否有details字段（新版API格式）
                    if 'details' in balance_item:
                        print(f"处理包含details的账户数据，类型: {balance_item.get('type')}")
                        for detail in balance_item.get('details', []):
                            currency = detail.get('ccy', '')
                            total_balance = float(detail.get('totalEq', '0'))
                            
                            print(f"  处理资产: {currency}, 总余额: {total_balance}")
                            
                            if total_balance <= 0:
                                print(f"  跳过零余额资产: {currency}")
                                continue
                            
                            asset_record = {
                                'currency': currency,
                                'total_balance': total_balance,
                                'available_balance': float(detail.get('availEq', '0')),
                                'frozen_balance': float(detail.get('frozenBal', '0')),
                                'asset_name': self.get_asset_name(currency),
                                'usdt_value': float(detail.get('eqUsd', '0')),
                                'account_type': balance_item.get('type', 'spot')
                            }
                            
                            account_type = balance_item.get('type', 'spot')
                            if account_type == 'spot':
                                account_balances['spot_balances'].append(asset_record)
                            elif account_type == 'margin':
                                account_balances['margin_balances'].append(asset_record)
                            elif account_type == 'funding':
                                account_balances['funding_balances'].append(asset_record)
                            
                            account_balances['total_usdt_value'] += asset_record['usdt_value']
                            asset_count += 1
                    else:
                        # 旧版API格式直接处理
                        currency = balance_item.get('ccy', '')
                        total_balance = float(balance_item.get('totalBal', '0'))
                        
                        print(f"处理资产: {currency}, 总余额: {total_balance}")
                        
                        if total_balance <= 0:
                            print(f"跳过零余额资产: {currency}")
                            continue
                        
                        asset_record = {
                            'currency': currency,
                            'total_balance': total_balance,
                            'available_balance': float(balance_item.get('availBal', '0')),
                            'frozen_balance': float(balance_item.get('frozenBal', '0')),
                            'asset_name': self.get_asset_name(currency),
                            'usdt_value': 0,
                            'account_type': balance_item.get('type', 'spot')
                        }
                        
                        account_type = balance_item.get('type', 'spot')
                        if account_type == 'spot':
                            account_balances['spot_balances'].append(asset_record)
                        elif account_type == 'margin':
                            account_balances['margin_balances'].append(asset_record)
                        elif account_type == 'funding':
                            account_balances['funding_balances'].append(asset_record)
                        
                        if currency == 'USDT':
                            asset_record['usdt_value'] = total_balance
                            account_balances['total_usdt_value'] += total_balance
                        
                        asset_count += 1
            
            print(f"总共处理了 {asset_count} 个非零余额资产")
            print(f"现货账户资产数: {len(account_balances['spot_balances'])}")
            print(f"杠杆账户资产数: {len(account_balances['margin_balances'])}")
            print(f"资金账户资产数: {len(account_balances['funding_balances'])}")
            print(f"总USDT价值: {account_balances['total_usdt_value']}")
            
            # 按余额降序排序各类型资产
            for balance_type in ['spot_balances', 'margin_balances', 'funding_balances']:
                account_balances[balance_type].sort(key=lambda x: x['total_balance'], reverse=True)
            
            return {
                'success': True,
                'data': account_balances,
                'error': None
            }
        except Exception as e:
            error_message = f"获取OKX详细余额失败: {str(e)}"
            print(error_message)
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                'success': False,
                'data': None,
                'error': error_message
            }
        finally:
            print("======= get_detailed_okx_balance方法执行结束 =======")
    
    def get_okx_stop_orders(self):
        """获取OKX交易所的止盈止损订单数据，使用官方SDK的orders-algo-pending接口"""
        print("=== 开始获取OKX止盈止损订单数据 ===")
        # 如果没有成功连接到OKX官方API或API密钥未配置，返回空数据
        if not self.okx_official_api:
            print("OKX官方API实例未初始化 - 将返回空数据")
            return {'stop_orders': [], 'count': 0, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'error': 'OKX官方API实例未初始化'}
        
        try:
            print("正在调用OKX官方API /api/v5/trade/orders-algo-pending获取止盈止损订单...")
            
            # 使用OKX官方API调用orders-algo-pending接口，指定instType为SWAP
            # 止盈止损订单类型可以是：conditional, oco, trigger, iceberg, twap
            response = self.okx_official_api.order_algos_list(
                instType='SWAP',  # 指定合约类型为永续合约
                ordType='conditional,oco',  # 止盈止损相关的算法订单类型
                limit='100'  # 获取最多100条记录
            )
            
            # 检查响应是否成功
            if response and isinstance(response, dict) and 'code' in response and response['code'] == '0' and 'data' in response:
                stop_orders = response['data']
                print(f"成功获取到{len(stop_orders)}个止盈止损订单")
                # 打印前几个订单的详细信息，特别是trigger_price相关字段
                print(f"=== 订单数据详情示例 ===")
                for i, order in enumerate(stop_orders[:3]):  # 只打印前3个订单作为示例
                    print(f"订单{i+1}原始数据: {order}")
                    print(f"  - algoId: {order.get('algoId')}")
                    print(f"  - instId: {order.get('instId')}")
                    print(f"  - triggerPx: {order.get('triggerPx')}")
                    print(f"  - ordPx: {order.get('ordPx')}")
                    print(f"  - tpTriggerPx: {order.get('tpTriggerPx')}")
                    print(f"  - slTriggerPx: {order.get('slTriggerPx')}")
                    print(f"  - sz: {order.get('sz')}")
                    print(f"  - side: {order.get('side')}")
                    print(f"  - posSide: {order.get('posSide')}")
                    print(f"  - state: {order.get('state')}")
                
                # 安全地转换数值，处理空字符串
                def safe_float(value, default=0.0):
                    if value is None or value == '':
                        return default
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return default
                
                # 格式化订单数据
                formatted_orders = []
                for order in stop_orders:
                    # 优先从tpTriggerPx或slTriggerPx获取trigger_price值
                    # 对于OCO类型订单，使用止盈价格作为trigger_price
                    trigger_price_value = safe_float(order.get('triggerPx'))
                    if trigger_price_value == 0:
                        # 如果triggerPx为空，优先使用tpTriggerPx
                        if order.get('tpTriggerPx'):
                            trigger_price_value = safe_float(order.get('tpTriggerPx'))
                        # 如果没有tpTriggerPx，尝试使用slTriggerPx
                        elif order.get('slTriggerPx'):
                            trigger_price_value = safe_float(order.get('slTriggerPx'))
                    
                    # 构建符合我们格式的订单数据
                    formatted_order = {
                        'order_id': order.get('algoId', ''),
                        'symbol': order.get('instId', ''),
                        'side': order.get('side', ''),
                        'position_side': order.get('posSide', ''),
                        'type': order.get('ordType', ''),
                        'algo_type': order.get('algoType', ''),
                        # 优先使用tpTriggerPx作为trigger_price的值
                        'trigger_price': safe_float(order.get('tpTriggerPx'))  if order.get('tpTriggerPx') else None,
                        'order_price': safe_float(order.get('ordPx')),
                        'quantity': safe_float(order.get('sz')),
                        'status': order.get('state', ''),
                        'created_time': order.get('cTime', ''),
                        'tp_price': safe_float(order.get('tpOrdPx')),
                        'sl_price': safe_float(order.get('slTriggerPx')) if order.get('slTriggerPx') else None,
                        # 保存原始字段以便调试
                        'raw_tp_trigger_px': order.get('tpTriggerPx'),
                        'raw_sl_trigger_px': order.get('slTriggerPx'),
                        'raw_trigger_px': order.get('triggerPx')
                    }
                    formatted_orders.append(formatted_order)
                
                return {
                    'stop_orders': formatted_orders,
                    'count': len(formatted_orders),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': None
                }
            else:
                error_msg = response.get('msg', '未知错误') if response else '无响应'
                print(f"获取止盈止损订单失败: {error_msg}")
                return {
                    'stop_orders': [],
                    'count': 0,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': error_msg
                }
        except Exception as e:
            print(f"获取止盈止损订单时发生错误: {e}")
            # 打印更详细的错误信息
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            return {
                'stop_orders': [],
                'count': 0,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def cancel_okx_stop_order(self, order_id, symbol):
        """取消OKX交易所的止盈止损订单，使用官方SDK的cancel_algo_order接口"""
        print(f"=== 开始取消OKX止盈止损订单: {order_id}, {symbol} ===")
        # 如果没有成功连接到OKX官方API或API密钥未配置，返回失败
        if not self.okx_official_api:
            print("OKX官方API实例未初始化 - 无法取消订单")
            return {"success": False, "message": "OKX官方API实例未初始化"}
        
        try:
            print("正在调用OKX官方API /api/v5/trade/cancel-algos取消止盈止损订单...")
            # 使用OKX官方API调用cancel_algo_order接口取消算法订单
            response = self.okx_official_api.cancel_algo_order(
                algoId=order_id,
                instId=symbol
            )
            
            # 检查响应是否成功
            if response and isinstance(response, dict) and 'code' in response and response['code'] == '0':
                print(f"止盈止损订单取消成功: {order_id}")
                return {"success": True, "message": "止盈止损订单取消成功"}
            else:
                error_msg = response.get('msg', '未知错误') if response else '无响应'
                print(f"止盈止损订单取消失败: {error_msg}")
                return {"success": False, "message": f"止盈止损订单取消失败: {error_msg}"}
        except Exception as e:
            print(f"取消止盈止损订单时发生错误: {e}")
            # 打印更详细的错误信息
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            return {"success": False, "message": f"取消止盈止损订单时发生错误: {str(e)}"}
    
    def modify_okx_stop_order(self, order_id, symbol, new_tp_ord_price=None, new_tp_trigger_price=None, 
                             new_amount=None, new_sl_trigger_price=None):
        """修改OKX交易所的止盈止损订单，优先使用官方API，支持ccxt作为备用"""
        print(f"=== 开始修改OKX止盈止损订单: {order_id}, {symbol} ===")
        
        # 检查是否有参数需要修改
        has_modifications = any(x is not None for x in [new_tp_ord_price, new_tp_trigger_price, new_amount, new_sl_trigger_price])
        if not has_modifications:
            print(f"=== 无需修改OKX止盈止损订单: {order_id} ===")
            return {
                'success': True,
                'message': '无需修改订单（无修改参数）',
                'data': {}
            }
        
        try:
            # 优先使用OKX官方API
            if self.okx_official_api:
                print("使用OKX官方API修改止盈止损订单...")
                
                # 构建修改算法订单的参数
                amend_params = {
                    'algoId': order_id,
                    'instId': symbol
                }
                
                # 添加可以修改的参数
                if new_tp_ord_price is not None:
                    amend_params['newTpOrdPx'] = str(new_tp_ord_price)
                if new_tp_trigger_price is not None:
                    amend_params['newTpTriggerPx'] = str(new_tp_trigger_price)
                if new_sl_trigger_price is not None:
                    amend_params['newSlTriggerPx'] = str(new_sl_trigger_price)
                if new_amount is not None:
                    amend_params['newSz'] = str(new_amount)
                
                print(f"修改参数: {amend_params}")
                
                # 使用OKX官方API调用amend-algo-order接口修改算法订单
                response = self.okx_official_api.amend_algo_order(**amend_params)
                
                # 检查响应是否成功
                if response and isinstance(response, dict) and 'code' in response:
                    if response['code'] == '0':
                        print(f"止盈止损订单修改成功(官方API)")
                        return {
                            "success": True, 
                            "message": "止盈止损订单修改成功",
                            "data": response.get('data', {})
                        }
                    else:
                        error_msg = response.get('msg', '未知错误')
                        print(f"修改止盈止损订单失败(官方API): {error_msg}")
                        return {
                            "success": False, 
                            "message": f"修改订单失败: {error_msg}",
                            "data": {}
                        }
                else:
                    print(f"修改止盈止损订单失败，无有效响应")
                    return {
                        "success": False, 
                        "message": "修改止盈止损订单失败，无有效响应",
                        "data": {}
                    }
            elif self.okx_exchange:
                # 备用：使用ccxt API
                print("使用CCXT API修改止盈止损订单...")
                ccxt_params = {}
                if new_tp_ord_price is not None:
                    ccxt_params['price'] = new_tp_ord_price
                if new_amount is not None:
                    ccxt_params['amount'] = new_amount
                if new_tp_trigger_price is not None:
                    ccxt_params['triggerPrice'] = new_tp_trigger_price
                if new_sl_trigger_price is not None:
                    ccxt_params['stopPrice'] = new_sl_trigger_price
                
                result = self.okx_exchange.edit_order(order_id, symbol, **ccxt_params)
                print(f"=== 修改OKX止盈止损订单成功(CCXT): {order_id} ===")
                return {
                    'success': True,
                    'message': '止盈止损订单修改成功',
                    'data': result
                }
            else:
                raise Exception("没有可用的API客户端")
                
        except Exception as e:
            print(f"修改止盈止损订单时发生错误: {e}")
            # 打印更详细的错误信息
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            return {
                "success": False, 
                "message": f"修改订单时发生异常: {str(e)}",
                "data": {}
            }
    
    def get_okx_positions(self):
        """获取OKX交易所的当前仓位数据"""
        try:
            print("=== 开始获取OKX仓位数据 ===")
            print(f"API客户端状态 - AccountAPI: {bool(self.okx_account_api)}, Exchange: {bool(self.okx_exchange)}")
            
            # 优先使用OKX官方API
            if self.okx_account_api:  # 使用account_api而不是trade_api获取仓位
                print("使用OKX官方API(AccountAPI)获取仓位数据...")
                print("准备调用AccountAPI.get_positions()，参数: instType=\"\"")
                
                # 记录API调用开始时间
                import time
                start_time = time.time()
                
                # 根据API文档，获取所有仓位时不应该传递posSide参数
                result = self.okx_account_api.get_positions(instType="")
                
                # 记录API调用结束时间
                end_time = time.time()
                print(f"API调用耗时: {end_time - start_time:.4f} 秒")
                
                # 打印完整响应用于调试
                print(f"官方API返回类型: {type(result)}")
                print(f"官方API返回状态码: {result.get('code') if isinstance(result, dict) else '未知'}")
                print(f"官方API返回消息: {result.get('msg') if isinstance(result, dict) else '未知'}")
                print(f"官方API返回数据结构: {result}")
                
                # 确保返回数据是有效的
                if not result or not isinstance(result, dict):
                    print("警告: 官方API返回格式不正确或为空，不是有效的字典")
                    return []
                    
                if 'data' not in result:
                    print("警告: 官方API返回格式不正确，缺少'data'字段")
                    print(f"返回的所有字段: {list(result.keys())}")
                    return []
                
                # 检查data字段类型和内容
                data = result['data']
                print(f"data字段类型: {type(data)}")
                print(f"data字段长度: {len(data) if isinstance(data, list) else '非列表类型'}")
                
                if isinstance(data, list) and len(data) > 0:
                    print(f"前3条原始仓位数据样本:")
                    for i, pos in enumerate(data[:3]):
                        print(f"  仓位{i+1}: {pos}")
                
                formatted_positions = []
                skipped_positions = 0
                
                if isinstance(data, list):
                    print("开始处理仓位数据...")
                    for i, position in enumerate(data):
                        print(f"处理仓位{i+1}: {position.get('instId', '未知合约')}")
                        
                        # 过滤掉空仓位或未持仓的记录
                        pos_val_str = position.get('pos', '0')
                        print(f"  原始仓位值: {pos_val_str} (类型: {type(pos_val_str)})")
                        
                        try:
                            pos_val = float(pos_val_str)
                            print(f"  转换后的仓位值: {pos_val}")
                            
                            if abs(pos_val) < 0.000001:
                                print(f"  跳过空仓位: {position.get('instId', '未知合约')}")
                                skipped_positions += 1
                                continue
                            
                            # 获取资产信息
                            symbol = position.get('instId', '')
                            print(f"  合约符号: {symbol}")
                            
                            base_asset = symbol.split('-')[0] if '-' in symbol else ''
                            quote_asset = symbol.split('-')[1] if '-' in symbol else ''
                            print(f"  基础资产: {base_asset}, 报价资产: {quote_asset}")
                            
                            # 格式化数据
                            formatted_position = {
                                'instId': symbol,
                                'base_asset': base_asset,
                                'quote_asset': quote_asset,
                                'posSide': position.get('posSide', 'long'),
                                'pos': pos_val,
                                'avgPx': float(position.get('avgPx', '0')),
                                'upl': float(position.get('upl', '0')),
                                'uplRatio': float(position.get('uplRatio', '0')) * 100,
                                'markPx': float(position.get('markPx', '0')),
                                'liqPx': float(position.get('liqPx', '0')),
                                'lever': float(position.get('lever', '0')),
                                'notionalUsd': float(position.get('notionalUsd', '0')),
                                'baseAssetName': self.get_asset_name(base_asset),
                                'quoteAssetName': self.get_asset_name(quote_asset) if quote_asset else ''
                            }
                            
                            print(f"  格式化后的仓位数据: {formatted_position}")
                            formatted_positions.append(formatted_position)
                            
                        except Exception as field_error:
                            print(f"  处理字段时出错: {str(field_error)}")
                            continue
                
                print(f"=== OKX仓位数据获取成功(官方API) ===")
                print(f"  - 原始数据条数: {len(data) if isinstance(data, list) else '未知'}")
                print(f"  - 跳过的空仓位数: {skipped_positions}")
                print(f"  - 格式化后的有效仓位数: {len(formatted_positions)}")
                
                if formatted_positions:
                    print(f"  - 返回的前3条格式化仓位数据:")
                    for i, pos in enumerate(formatted_positions[:3]):
                        print(f"    仓位{i+1}: {pos}")
                
                return formatted_positions
            elif self.okx_exchange:
                # 备用：使用ccxt API获取仓位数据
                print("使用CCXT API获取仓位数据...")
                positions_data = self.okx_exchange.fetch_positions()
                
                print(f"CCXT API返回数据类型: {type(positions_data)}")
                print(f"CCXT API返回数据长度: {len(positions_data) if isinstance(positions_data, list) else '非列表类型'}")
                
                if isinstance(positions_data, list) and len(positions_data) > 0:
                    print(f"前3条CCXT仓位数据样本:")
                    for i, pos in enumerate(positions_data[:3]):
                        print(f"  仓位{i+1}: {pos}")
                
                formatted_positions = []
                for position in positions_data:
                    # 过滤掉空仓位
                    if abs(float(position.get('contracts', 0))) < 0.000001:
                        continue
                    
                    # 获取资产信息
                    symbol = position.get('symbol', '')
                    base_asset = symbol.split('/')[0]
                    quote_asset = symbol.split('/')[1] if '/' in symbol else ''
                    
                    # 格式化数据
                    formatted_position = {
                        'instId': symbol,
                        'base_asset': base_asset,
                        'quote_asset': quote_asset,
                        'posSide': position.get('side', 'long'),
                        'pos': float(position.get('contracts', '0')),
                        'avgPx': float(position.get('entryPrice', '0')),
                        'upl': float(position.get('unrealizedPnl', '0')),
                        'uplRatio': float(position.get('unrealizedPnlPcnt', '0')) * 100,
                        'markPx': float(position.get('markPrice', '0')),
                        'liqPx': float(position.get('liquidationPrice', '0')),
                        'lever': float(position.get('leverage', '0')),
                        'notionalUsd': float(position.get('notional', '0')),
                        'baseAssetName': self.get_asset_name(base_asset),
                        'quoteAssetName': self.get_asset_name(quote_asset) if quote_asset else ''
                    }
                    formatted_positions.append(formatted_position)
                
                print(f"=== OKX仓位数据获取成功(CCXT)，共 {len(formatted_positions)} 个仓位 ===")
                return formatted_positions
            else:
                print("错误: 没有可用的API客户端实例")
                raise Exception("没有可用的API客户端")
            
        except Exception as e:
            print(f"=== 获取OKX仓位数据时发生错误: {str(e)} ===")
            print(f"错误类型: {type(e).__name__}")
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            return []
    
    def handle_modify_stop_order_request(self, request_data):
        """处理修改止盈止损订单的请求"""
        try:
            print("=== 开始处理修改止盈止损订单请求 ===")
            
            # 验证必需参数
            required_fields = ['order_id', 'symbol', 'side', 'type']
            for field in required_fields:
                if field not in request_data:
                    print(f"缺少必需参数: {field}")
                    return {
                        'success': False,
                        'message': f'缺少必需参数: {field}',
                        'data': {}
                    }
            
            order_id = request_data['order_id']
            symbol = request_data['symbol']
            side = request_data['side']
            order_type = request_data['type']
            
            # 获取可选参数
            new_price = request_data.get('price')
            new_quantity = request_data.get('quantity')
            trigger_price = request_data.get('trigger_price')
            new_tp_trigger_price = request_data.get('new_tp_trigger_price')
            new_tp_ord_price = request_data.get('new_tp_ord_price')
            new_sl_trigger_price = request_data.get('new_sl_trigger_price')
            new_amount = request_data.get('new_amount', new_quantity)
            
            print(f"修改订单: ID={order_id}, Symbol={symbol}, Type={order_type}")
            
            # 参数类型转换
            if new_price is not None:
                new_price = float(new_price)
                print(f"新价格: {new_price}")
            if new_quantity is not None:
                new_quantity = float(new_quantity)
                print(f"新数量: {new_quantity}")
            if trigger_price is not None:
                trigger_price = float(trigger_price)
                print(f"新触发价格: {trigger_price}")
            
            # 转换止盈止损相关参数
            try:
                new_tp_trigger_price = float(new_tp_trigger_price) if new_tp_trigger_price is not None else None
                new_tp_ord_price = float(new_tp_ord_price) if new_tp_ord_price is not None else None
                new_sl_trigger_price = float(new_sl_trigger_price) if new_sl_trigger_price is not None else None
                if new_amount is not None:
                    new_amount = float(new_amount)
            except ValueError:
                print("价格和数量必须为数字")
                return {
                    'success': False,
                    'message': '价格和数量必须为数字',
                    'data': {}
                }
            
            # 检查是否有参数需要修改
            if new_price is None and new_quantity is None and trigger_price is None and \
               new_tp_trigger_price is None and new_tp_ord_price is None and \
               new_sl_trigger_price is None and new_amount is None:
                print("没有提供需要修改的参数")
                return {
                    'success': False,
                    'message': '没有提供需要修改的参数',
                    'data': {}
                }
            
            # 优先使用官方API - 直接调用modify_okx_stop_order方法
            if self.okx_official_api:
                print("使用OKX官方API修改止盈止损订单...")
                # 调用已经实现的modify_okx_stop_order方法
                result = self.modify_okx_stop_order(
                    order_id, symbol, new_tp_ord_price, new_tp_trigger_price, new_amount, new_sl_trigger_price
                )
                
                if result.get('success', False):
                    print(f"止盈止损订单修改成功: {order_id}")
                    return {
                        'success': True,
                        'message': '止盈止损订单修改成功',
                        'data': {}
                    }
                else:
                    error_msg = result.get('message', '修改失败')
                    print(f"修改失败: {error_msg}")
                    return {
                        'success': False,
                        'message': error_msg,
                        'data': {}
                    }
            elif self.okx_exchange:
                # 备用：使用CCXT API
                print("使用CCXT API修改止盈止损订单...")
                edit_params = {}
                if new_price is not None:
                    edit_params['price'] = new_price
                if new_quantity is not None:
                    edit_params['amount'] = new_quantity
                if trigger_price is not None:
                    edit_params['triggerPrice'] = trigger_price
                
                result = self.okx_exchange.edit_order(order_id, symbol, **edit_params)
                print(f"止盈止损订单修改成功(CCXT): {order_id}")
                return {
                    'success': True,
                    'message': '止盈止损订单修改成功',
                    'data': result
                }
            else:
                raise Exception("没有可用的API客户端")
            
        except Exception as e:
            print(f"处理修改止盈止损订单请求时出错: {str(e)}")
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            return {
                'success': False,
                'message': f'处理请求时发生异常: {str(e)}',
                'data': {}
            }
    
    def get_balances(self, use_ccxt=False):
        """获取OKX账户余额（供路由调用的主方法）"""
        try:
            print("=== 开始获取OKX账户余额(get_balances) ===")
            
            # 调用详细余额获取方法
            result = self.get_detailed_okx_balance()
            
            if result['success']:
                # 返回格式化后的余额数据
                return result['data']
            else:
                print(f"获取余额失败: {result['error']}")
                return {'error': result['error']}
            
        except Exception as e:
            error_message = f"获取OKX余额时发生错误: {str(e)}"
            print(error_message)
            return {'error': error_message}