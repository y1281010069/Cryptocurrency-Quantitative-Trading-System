import numpy as np
import logging
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