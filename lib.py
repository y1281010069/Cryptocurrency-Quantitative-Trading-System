import numpy as np
import logging
import requests
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

# 尝试导入配置文件，如果不存在则使用默认值
try:
    from config import TRADING_CONFIG
except ImportError:
    # 使用默认配置
    TRADING_CONFIG = {
        'ATR_PERIOD': 14
    }

def calculate_atr(df, period=None):
    # 如果没有提供period参数，使用配置中的值
    if period is None:
        period = TRADING_CONFIG['ATR_PERIOD']
    """计算ATR值（平均真实波动幅度）"""
    # 计算真实波动幅度
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    # 计算ATR (TR的N日移动平均线)
    df['atr'] = df['tr'].rolling(window=period).mean()
    return df['atr'].iloc[-1] if len(df) >= period else 0.0

def get_okx_positions(exchange, use_contract_utils=False):
    """获取OKX当前仓位列表
    
    Args:
        exchange: ccxt交易所实例
        use_contract_utils: 是否使用contract_utils计算成本（主要用于app.py）
    
    Returns:
        list: 格式化后的仓位列表
    """
    try:
        # 获取所有仓位
        positions = exchange.fetch_positions()
        
        # 过滤出非零仓位
        non_zero_positions = [pos for pos in positions if float(pos.get('contracts', 0)) != 0]
        
        # 格式化仓位数据
        formatted_positions = []
        for position in non_zero_positions:
            symbol = position.get('symbol', '')
            pos_side = position.get('side', '')  # 获取仓位方向
            
            # 计算当前价格（使用最新市场数据）
            current_price = 0
            if symbol in exchange.markets:
                try:
                    ticker = exchange.fetch_ticker(symbol)
                    current_price = ticker.get('last', 0)
                except Exception as e:
                    logger.warning(f"获取{symbol}当前价格失败: {e}")
                    current_price = 0
            
            # 计算盈亏百分比
            entry_price = float(position.get('entryPrice', 0))
            profit_percent = 0
            profit = float(position.get('unrealizedPnl', 0))
            
            # 根据参数决定是否使用contract_utils计算成本
            if use_contract_utils:
                try:
                    # 仅在需要时导入contract_utils
                    import contract_utils
                    amount = float(position.get('contracts', 0))
                    cost = contract_utils.calculate_cost(amount, entry_price, symbol)
                    profit_percent = (profit / cost * 100) if cost > 0 else 0
                    
                    # app.py格式的返回数据
                    formatted_position = {
                        'symbol': symbol,
                        'type': position.get('type', 'spot'),
                        'amount': amount,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'profit': profit,
                        'profit_percent': profit_percent,
                        'datetime': datetime.fromtimestamp(
                            position.get('timestamp', 0) / 1000
                        ).strftime('%Y-%m-%d %H:%M:%S') if position.get('timestamp') else '',
                        'cost': cost,
                        'posSide': pos_side
                    }
                except Exception as e:
                    logger.warning(f"使用contract_utils计算成本失败: {e}")
                    # 默认使用简单的盈亏百分比计算
                    if entry_price > 0 and current_price > 0:
                        profit_percent = ((current_price - entry_price) / entry_price) * 100
                    
                    formatted_position = {
                        'symbol': symbol,
                        'posSide': pos_side,
                        'amount': float(position.get('contracts', 0)),
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'profit_percent': round(profit_percent, 2)
                    }
            else:
                # 默认使用简单的盈亏百分比计算（multi_timeframe_system.py格式）
                if entry_price > 0 and current_price > 0:
                    profit_percent = ((current_price - entry_price) / entry_price) * 100
                
                formatted_position = {
                    'symbol': symbol,
                    'posSide': pos_side,
                    'amount': float(position.get('contracts', 0)),
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'profit_percent': round(profit_percent, 2)
                }
            
            formatted_positions.append(formatted_position)
        
        logger.info(f"成功获取到{len(formatted_positions)}个有效仓位")
        return formatted_positions
    except Exception as e:
        logger.error(f"获取仓位数据失败: {e}")
        return []

def send_trading_signal_to_api(signal, name, logger_param=None):
    """发送交易信号到API
    
    Args:
        signal: 交易信号对象，包含symbol、overall_action、target_short、stop_loss等属性
        name: 信号名称
        logger_param: 可选的日志记录器，如果不提供则使用默认logger
    
    Returns:
        bool: 是否成功发送信号
    """
    # 使用提供的logger或默认logger
    log = logger_param if logger_param is not None else logger
    
    try:
        # 设置ac_type参数：买入对应o_l，卖出对应o_s
        ac_type = 'o_l' if signal.overall_action == '买入' else 'o_s'
        
        # 构造请求参数
        payload = {
            'name': name,
            'mechanism_id': TRADING_CONFIG.get('MECHANISM_ID', ''),
            'stop_win_price': signal.target_short,
            'stop_loss_price': signal.stop_loss,
            'ac_type': ac_type,
            'loss': TRADING_CONFIG.get('LOSS', 1)
        }
        
        # 发送POST请求（表单形式）
        url = 'http://149.129.66.131:81/myOrder'
        response = requests.post(url, data=payload, timeout=10)
        
        # 记录请求结果
        if response.status_code == 200:
            log.info(f"成功发送交易信号到API: {signal.symbol} ({signal.overall_action})")
            return True
        else:
            log.warning(f"发送交易信号到API失败 (状态码: {response.status_code}): {signal.symbol}")
            log.debug(f"API响应: {response.text}")
            return False
    except Exception as e:
        log.error(f"发送交易信号到API时发生异常: {e}")
        return False

def send_position_info_to_api(position, name, logger_param=None):
    """发送持仓信息到API
    
    Args:
        position: 持仓信息字典，包含symbol、direction、amount等键
        name: 标的名称
        logger_param: 可选的日志记录器，如果不提供则使用默认logger
    
    Returns:
        bool: 是否成功发送持仓信息
    """
    # 使用提供的logger或默认logger
    log = logger_param if logger_param is not None else logger
    
    try:
        # 设置ac_type参数：多头对应c_l，空头对应c_s
        ac_type = 'c_l' if position['direction'] == 'long' else 'c_s'
        
        # 构造请求参数
        payload = {
            'name': name,
            'mechanism_id': TRADING_CONFIG.get('MECHANISM_ID', ''),
            'ac_type': ac_type,
            'volume_plan': position['amount']
        }
        
        # 发送POST请求（表单形式）
        url = 'http://149.129.66.131:81/myOrder'
        
        # 打印接口请求信息
        log.info(f"发送请求到接口: {url}")
        log.info(f"请求参数: {payload}")
        
        # 发送请求
        response = requests.post(url, data=payload, timeout=10)
        
        # 打印接口返回信息
        log.info(f"接口返回状态码: {response.status_code}")
        log.info(f"接口返回内容: {response.text}")
        
        # 记录请求结果
        if response.status_code == 200:
            log.info(f"成功发送持仓信息到API: {position['symbol']} ({position['direction']})")
            return True
        else:
            log.warning(f"发送持仓信息到API失败 (状态码: {response.status_code}): {position['symbol']}")
            log.debug(f"API响应: {response.text}")
            return False
    except Exception as e:
        log.error(f"发送持仓信息到API时发生异常: {e}")
        return False