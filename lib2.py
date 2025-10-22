import logging
import requests
import numpy as np
from datetime import datetime
import json
import redis

# 尝试导入配置文件，如果不存在则使用默认值
try:
    from config import TRADING_CONFIG, REDIS_CONFIG
except ImportError:
    # 使用默认配置
    TRADING_CONFIG = {'ATR_PERIOD': 14}
    REDIS_CONFIG = {'ADDR': '149.129.66.131:6379','PASSWORD': 'Bianhao8@'}

# 配置日志（只保留一套配置）
logger = logging.getLogger(__name__)
# 检查logger是否已有handler，如果没有则添加
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
def calculate_atr(df, period=None):
    # 如果没有提供period参数，使用配置中的值
    if period is None:
        period = TRADING_CONFIG['ATR_PERIOD']
    """计算ATR值（平均真实波动幅度）"""
    # 计算真实波动幅度
    df['tr'] = np.maximum(df['high'] - df['low'],np.maximum(abs(df['high'] - df['close'].shift(1)),abs(df['low'] - df['close'].shift(1))))
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
    # 尝试连接Redis
    redis_client = None
    cache_key = f"okx_positions_{'contract' if use_contract_utils else 'normal'}"
    
    try:
        # 从配置中解析Redis地址和端口
        addr = REDIS_CONFIG.get('ADDR', 'localhost:6379')
        host, port = addr.split(':')
        password = REDIS_CONFIG.get('PASSWORD', None)
        
        # 尝试连接Redis
        redis_client = redis.Redis(host=host,port=int(port),password=password,db=0,socket_connect_timeout=2,socket_timeout=2)
        redis_client.ping()
        
        # 尝试从缓存获取数据
        cached_data = redis_client.get(cache_key)
        if cached_data:
            logger.info(f"从Redis缓存获取仓位数据")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Redis连接或获取缓存失败: {e}")
    
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
            
            # 计算盈亏百分比
            entry_price = float(position.get('entryPrice', 0))
            profit_percent = 0
            profit = float(position.get('unrealizedPnl', 0))
            
            # 根据参数决定是否使用contract_utils计算成本
            if use_contract_utils:
                try:
                    # 仅在需要时导入contract_utils
                    from lib.tool import contract_utils
                    amount = float(position.get('contracts', 0))
                    cost = contract_utils.calculate_cost(amount, entry_price, symbol)
                    profit_percent = (profit / cost * 100) if cost > 0 else 0
                    
                    # app.py格式的返回数据
                    formatted_position = {'symbol': symbol, 'type': position.get('type', 'spot'), 'amount': amount, 'entry_price': entry_price, 'current_price': current_price, 'profit': profit, 'profit_percent': profit_percent, 'datetime': datetime.fromtimestamp(position.get('timestamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S') if position.get('timestamp') else '', 'cost': cost, 'posSide': pos_side}
                except Exception as e:
                    logger.warning(f"使用contract_utils计算成本失败: {e}")
                    # 默认使用简单的盈亏百分比计算
                    if entry_price > 0 and current_price > 0:
                        profit_percent = ((current_price - entry_price) / entry_price) * 100
                    
                    formatted_position = {'symbol': symbol, 'posSide': pos_side, 'amount': float(position.get('contracts', 0)), 'entry_price': entry_price, 'current_price': current_price, 'profit_percent': round(profit_percent, 2), 'direction': pos_side}
            else:
                # 默认使用简单的盈亏百分比计算（multi_timeframe_system.py格式）
                if entry_price > 0 and current_price > 0:
                    profit_percent = ((current_price - entry_price) / entry_price) * 100
                
                formatted_position = {'symbol': symbol, 'posSide': pos_side, 'amount': float(position.get('contracts', 0)), 'entry_price': entry_price, 'current_price': current_price, 'profit_percent': round(profit_percent, 2), 'datetime': datetime.fromtimestamp(position.get('timestamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S') if position.get('timestamp') else ''}
            formatted_positions.append(formatted_position)
        
        # 将结果存入Redis缓存，设置5秒过期
        if redis_client:
            try:
                redis_client.setex(
                    cache_key,
                    5,  # 5秒过期时间
                    json.dumps(formatted_positions)
                )
                logger.info(f"仓位数据已存入Redis缓存，5秒后过期")
            except Exception as e:
                logger.warning(f"Redis缓存写入失败: {e}")
        
        logger.info(f"成功获取到{len(formatted_positions)}个有效仓位")
        return formatted_positions
    except Exception as e:
        logger.error(f"获取仓位数据失败: {e}")
        return []

def send_trading_signal_to_api(signal, name, logger_param=None, LOSS=None, mechanism_id=None):
    """发送交易信号到API
    Args:
        signal: 交易信号对象，包含symbol、overall_action、target_short、stop_loss等属性
        name: 信号名称
        logger_param: 可选的日志记录器，如果不提供则使用默认logger
        LOSS: 可选的损失参数，如果不提供则使用配置中的默认值
        mechanism_id: 可选的交易机制ID，如果不提供则使用配置中的默认值
    Returns:
        bool: 是否成功发送信号
    """
    # 使用提供的logger或默认logger
    logger_used = logger_param if logger_param is not None else logger
    
    # 检查是否启用信号API
    if not TRADING_CONFIG.get('ENABLE_SIGNAL_API', False):
        logger_used.info(f"信号API未启用，跳过发送交易信号: {signal.symbol} ({signal.overall_action})")
        return False
    
    try:
        # 设置ac_type参数：买入对应o_l，卖出对应o_s
        ac_type = 'o_l' if signal.overall_action == '买入' else 'o_s'
        
        # 构造请求参数
        # 使用传入的LOSS值，如果未提供则使用配置中的默认值
        loss_value = LOSS if LOSS is not None else TRADING_CONFIG.get('LOSS', 1)
        
        # 使用传入的mechanism_id，如果未提供则使用配置中的默认值
        mechanism_id_value = mechanism_id if mechanism_id is not None else TRADING_CONFIG.get('MECHANISM_ID', '')
        payload = {'name': name, 'mechanism_id': mechanism_id_value, 'stop_win_price': signal.target_short, 'stop_loss_price': signal.stop_loss, 'ac_type': ac_type, 'loss': loss_value}
        
        # 发送POST请求（表单形式）
        url = 'http://149.129.66.131:81/myOrder'
        response = requests.post(url, data=payload, timeout=10)
        
        # 记录请求结果
        if response.status_code == 200:
            logger_used.info(f"成功发送交易信号到API: {signal.symbol} ({signal.overall_action})")
            return True
        else:
            logger_used.warning(f"发送交易信号到API失败 (状态码: {response.status_code}): {signal.symbol}")
            logger_used.info(f"API响应: {response.text}")  # 将debug改为info以确保日志可见
            return False
    except Exception as e:
        logger_used.error(f"发送交易信号到API时发生异常: {e}")
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
    logger_used = logger_param if logger_param is not None else logger
    
    try:
        # 检查position字典中必要的键是否存在
        if 'direction' not in position:
            # 尝试从posSide获取direction值
            if 'posSide' in position:
                logger_used.info("从posSide获取direction值")
                # 将posSide值映射到direction格式（假设posSide的值为'long'或'short'）
                position['direction'] = position['posSide']
            else:
                logger_used.error("position字典中缺少'direction'和'posSide'键")
                return False
        
        if 'symbol' not in position:
            logger_used.error("position字典中缺少'symbol'键")
            return False
            
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
        logger_used.info(f"发送请求到接口: {url}")
        logger_used.info(f"请求参数: {payload}")
        
        # 发送请求
        response = requests.post(url, data=payload, timeout=10)
        
        # 打印接口返回信息
        logger_used.info(f"接口返回状态码: {response.status_code}")
        logger_used.info(f"接口返回内容: {response.text}")
        
        # 记录请求结果
        if response.status_code == 200:
            logger_used.info(f"成功发送持仓信息到API: {position['symbol']} ({position['direction']})")
            return True
        else:
            logger_used.warning(f"发送持仓信息到API失败 (状态码: {response.status_code}): {position['symbol']}")
            logger_used.info(f"API响应: {response.text}")
            return False
    except Exception as e:
        logger_used.error(f"发送持仓信息到API时发生异常: {e}")
        return False