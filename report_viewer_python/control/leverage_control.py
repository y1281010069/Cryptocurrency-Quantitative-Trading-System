class LeverageControl:
    def __init__(self, okx_official_api=None):
        # 初始化OKX API客户端
        self.okx_official_api = okx_official_api  # 用于交易相关操作
        self.okx_public_api = None  # 用于公共数据查询
    
    def set_api_clients(self, okx_public_api=None, okx_account_api=None, okx_official_api=None):
        """设置API客户端实例"""
        if okx_official_api:
            self.okx_official_api = okx_official_api
        if okx_public_api:
            self.okx_public_api = okx_public_api
        # 兼容处理，保持向后兼容性
        if okx_account_api and not self.okx_official_api:
            self.okx_official_api = okx_account_api
    
    def get_perpetual_symbols(self):
        """获取所有永续合约交易对"""
        try:
            # 优先使用PublicAPI获取交易对信息
            if self.okx_public_api:
                # 使用OKX官方包的PublicAPI获取永续合约交易对
                result = self.okx_public_api.get_instruments({
                    'instType': 'SWAP'
                })
            elif self.okx_official_api:
                # 回退使用TradeAPI（如果PublicAPI不可用）
                result = self.okx_official_api.get_instruments({
                    'instType': 'SWAP'
                })
            else:
                raise ValueError("没有可用的OKX API客户端")
            
            # 提取交易对信息
            symbols = []
            for item in result.get('data', []):
                symbols.append({
                    'symbol': item.get('instId'),
                    'base': item.get('baseCcy'),
                    'quote': item.get('quoteCcy'),
                    'alias': item.get('alias')
                })
            
            # 按符号名称排序
            symbols.sort(key=lambda x: x['symbol'])
            return symbols
        except Exception as e:
            print(f"获取永续合约交易对时发生错误: {e}")
            return {'error': str(e), 'symbols': []}
    
    def set_max_leverage(self, symbol, leverage, mgn_mode='isolated'):
        """设置最大杠杆"""
        try:
            if not self.okx_official_api:
                raise ValueError("没有可用的OKX API客户端")
            
            # 验证杠杆值
            leverage = float(leverage)
            if leverage < 1 or leverage > 100:
                raise ValueError("杠杆值必须在1到100之间")
            
            # 构建请求参数
            params = {
                'instId': symbol,
                'lever': str(int(leverage)),  # OKX API通常需要整数字符串
                'mgnMode': mgn_mode
            }
            
            # 调用OKX API设置杠杆
            result = self.okx_official_api.set_leverage(params)
            
            # 检查响应
            if result.get('code') == '0':
                return {
                    'success': True,
                    'message': f"成功设置 {symbol} 的杠杆为 {leverage}x",
                    'symbol': symbol,
                    'leverage': leverage
                }
            else:
                return {
                    'success': False,
                    'message': result.get('msg', '设置杠杆失败')
                }
        except ValueError as e:
            print(f"参数验证错误: {e}")
            return {'success': False, 'message': str(e)}
        except Exception as e:
            print(f"设置杠杆时发生错误: {e}")
            return {'success': False, 'message': f"设置杠杆失败: {str(e)}"}
    
    def batch_set_leverage(self, symbols, leverage, mgn_mode='isolated'):
        """批量设置杠杆"""
        results = []
        success_count = 0
        fail_count = 0
        
        for symbol in symbols:
            result = self.set_max_leverage(symbol, leverage, mgn_mode)
            results.append({
                'symbol': symbol,
                'success': result['success'],
                'message': result['message']
            })
            
            if result['success']:
                success_count += 1
            else:
                fail_count += 1
        
        return {
            'total': len(symbols),
            'success_count': success_count,
            'fail_count': fail_count,
            'results': results
        }
    
    def get_current_leverage(self, symbol, mgn_mode='isolated'):
        """获取当前杠杆设置"""
        try:
            if not self.okx_official_api:
                raise ValueError("没有可用的OKX API客户端")
            
            # 使用OKX API获取当前杠杆设置
            # 可以通过获取持仓信息或专门的杠杆查询接口
            result = self.okx_official_api.get_positions({
                'instId': symbol,
                'mgnMode': mgn_mode
            })
            
            # 解析响应获取杠杆信息
            if result.get('code') == '0' and result.get('data'):
                for position in result['data']:
                    if position.get('instId') == symbol:
                        return {
                            'symbol': symbol,
                            'current_leverage': float(position.get('lever', 0)),
                            'mgn_mode': position.get('mgnMode')
                        }
            
            return {'symbol': symbol, 'current_leverage': 0, 'message': '未找到杠杆信息'}
        except Exception as e:
            print(f"获取当前杠杆时发生错误: {e}")
            return {'error': str(e)}