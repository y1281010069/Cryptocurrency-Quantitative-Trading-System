#!/usr/bin/env python3
"""
多时间框架策略实现
基于BaseStrategy实现的具体策略类
"""

import pandas as pd
import numpy as np
import json
import os
import redis
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, make_dataclass
import logging
import sys
import ccxt
from strategies.condition_analyzer import calculate_trend_indicators_and_score, calculate_rsi_score, calculate_volume_score, calculate_rsi_crossover_score

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 添加OKX库到路径
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib', 'python-okx-master'))

OKX_CONFIG = {
    'api_key': "e890514f-0371-48b2-90be-0a964e810020",
    'secret': "F201E388F664BC205FF1D6AC6B3F1C5E",
    'passphrase': "Bianhao8@",
    'sandbox': False,  # True=测试环境, False=正式环境
    'timeout': 30000,
}

# 策略配置 - 每个策略使用独立配置
TRADING_CONFIG = {
    "BUY_THRESHOLD": 0.3, 
    "SELL_THRESHOLD": -0.3,
    "ATR_PERIOD": 14,
    "TARGET_MULTIPLIER": 4.5,
    "STOP_LOSS_MULTIPLIER": 3,
    "ENABLED_SYMBOLS": None,
    "DISABLED_SYMBOLS": [
        "USDC/USDT"
    ],
    "VOLUME_THRESHOLD": 4000000,  # 交易量筛选阈值（USDT）
    "MAX_POSITIONS": 40,
    "MECHANISM_ID": 14,
    "LOSS": 1,  # 损失参数，传递给API
    "SIGNAL_TRIGGER_TIMEFRAME": "15m",  # 交易信号触发周期
    "TIMEFRAME_DATA_LENGTHS": {
        '4h': 168,   # 4小时
        '1h': 168,   # 1小时
        '15m': 168   # 15分钟
    }  # 不同时间框架所需的数据长度
}

# 配置日志记录器
logger = logging.getLogger(__name__)
# 使用从根记录器继承的配置，避免重复日志输出
# 如果需要特定配置，可以在这里单独设置，但不要使用logging.basicConfig()
logger.setLevel(logging.INFO)

# 导入项目模块
from strategies.base_strategy import BaseStrategy
import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 导入lib.py文件作为一个模块
import importlib.util
# 动态导入lib.py文件
spec = importlib.util.spec_from_file_location("lib_module", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib2.py"))
lib_module = importlib.util.module_from_spec(spec)
sys.modules["lib_module"] = lib_module
spec.loader.exec_module(lib_module)
# 从导入的模块中获取函数
calculate_atr = lib_module.calculate_atr
send_trading_signal_to_api = lib_module.send_trading_signal_to_api
get_okx_positions = lib_module.get_okx_positions
from okx.Account import AccountAPI
from config import REDIS_CONFIG


# 动态创建MultiTimeframeSignal类
def create_multi_timeframe_signal_class():
    # 先定义所有非默认参数
    non_default_fields = [
        ('symbol', str),
        ('weekly_trend', str),
        ('daily_trend', str),
        ('overall_action', str),
        ('confidence_level', str),
        ('total_score', float),
        ('entry_price', float),
        ('target_short', float),
        ('target_medium', float),
        ('target_long', float),
        ('stop_loss', float),
        ('atr_one', float),
        ('reasoning', List[str]),
        ('timestamp', datetime)
    ]
    
    # 从配置中获取所有时间框架作为默认参数字段
    default_fields = []
    timeframe_config = TRADING_CONFIG.get('TIMEFRAME_DATA_LENGTHS', {})
    for timeframe in timeframe_config.keys():
        # 将时间框架格式化为驼峰式命名（例如：4h -> h4_signal, 1h -> h1_signal, 15m -> m15_signal）
        if timeframe == '4h':
            field_name = 'h4_signal'
        elif timeframe == '1h':
            field_name = 'h1_signal'
        elif timeframe == '15m':
            field_name = 'm15_signal'
        else:
            # 对于其他时间框架，使用通用格式
            field_name = f'{timeframe}_signal'
        default_fields.append((field_name, str, "观望"))
    
    # 添加timeframe_signals字典作为默认参数
    default_fields.append(('timeframe_signals', dict, field(default_factory=dict)))
    
    # 组合所有字段，确保非默认参数在前，默认参数在后
    fields = non_default_fields + default_fields
    
    # 创建数据类
    return make_dataclass('MultiTimeframeSignal', fields)

# 创建MultiTimeframeSignal类
MultiTimeframeSignal = create_multi_timeframe_signal_class()


class MultiTimeframeStrategy(BaseStrategy):
    """多时间框架分析策略实现"""
    
    # 将OKX_CONFIG定义为类变量，以满足BaseStrategy的要求
    OKX_CONFIG = OKX_CONFIG
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化多时间框架策略
        
        Args:
            config: 策略配置参数，如果为None则使用默认的TRADING_CONFIG
        """
        # 如果没有提供配置，使用策略内置的TRADING_CONFIG
        if config is None:
            config = TRADING_CONFIG
        
        super().__init__("MultiTimeframeStrategy", config)
        self._init_exchange()



    def analyze(self, symbol: str, data: Dict[str, pd.DataFrame]) -> Optional[MultiTimeframeSignal]:
        """
        使用多时间框架策略分析交易对
        
        Args:
            symbol: 交易对符号
            data: 多时间框架数据，格式为 {timeframe: dataframe}
        
        Returns:
            MultiTimeframeSignal对象或None
        """
        try:
            signals = {} 
            strengths = {} 
            
            # 分析每个时间框架
            for tf, df in data.items():
                action, strength = self._analyze_timeframe(df, tf)
                signals[tf] = action
                strengths[tf] = strength
            
            if len(data) < 3:  # 至少需要3个时间框架
                return None
            
            # 获取当前价格
            current_price = data.get('1h', list(data.values())[0])['close'].iloc[-1]
            
            # 综合评分 - 更新权重，去掉1w和1d周期
            weights = {'4h': 0.4, '1h': 0.4, '15m': 0.2}
            total_score = 0
            reasoning = []
            
            for tf, signal in signals.items():
                weight = weights.get(tf, 0.1)
                strength = strengths[tf]
                
                if "买入" in signal:
                    total_score += strength * weight
                    reasoning.append(f"{tf}:{signal}")
                elif "卖出" in signal:
                    total_score -= strength * weight
                    reasoning.append(f"{tf}:{signal}")
            
            # 确定综合操作：根据配置的阈值判断买入、卖出或观望
            if total_score >= self.config['BUY_THRESHOLD']:
                overall_action = "买入"
                confidence = "高"
            elif total_score <= self.config['SELL_THRESHOLD']:
                overall_action = "卖出"
                confidence = "高"
            else:
                overall_action = "观望"
                confidence = "低"
            
            # 添加详细日志，记录每个交易对的分析结果
            logger.info(f"{symbol} 分析结果 - 总分: {total_score:.3f}, 操作: {overall_action}, 信号: {signals}")
            
            # 获取15分钟时间框架的数据来计算ATR
            df_15m = data.get('15m')
            if df_15m is None or df_15m.empty:
                # 如果没有15m数据，使用第一个可用时间框架的数据
                df_15m = list(data.values())[0]
            
            # 计算ATR值
            atr_value = calculate_atr(df_15m)
            
            # 检查是否存在观望信号
            has_neutral = any("观望" in signal for signal in signals.values())
            
            # 过滤掉"观望"信号
            valid_signals = [signal for signal in signals.values() if "观望" not in signal]
            
            # 只有当没有观望信号且所有有效信号方向一致时，才算一致
            all_agreed = False
            if not has_neutral and valid_signals:
                # 检查所有有效信号是否方向一致
                first_direction = "买入" if "买入" in valid_signals[0] else "卖出"
                all_agreed = all(first_direction in signal for signal in valid_signals)
            
            # 根据是否所有时间框架一致决定使用的TARGET_MULTIPLIER
            target_multiplier = self.config['TARGET_MULTIPLIER']
            if all_agreed:
                target_multiplier *= 3  # 所有时间框架一致时，使用3倍的TARGET_MULTIPLIER
            
            # 根据交易方向计算ATR相关价格（做多/做空）
            if overall_action == "买入":
                # 买入方向：
                # - target_multiplier倍ATR作为短期目标（当前价格 + target_multiplier*ATR）
                # - STOP_LOSS_MULTIPLIER倍ATR作为止损价格（当前价格 - STOP_LOSS_MULTIPLIER*ATR）
                atr_one = current_price + atr_value
                target_short = current_price + target_multiplier * atr_value
                stop_loss = current_price - self.config['STOP_LOSS_MULTIPLIER'] * atr_value
            else:
                # 卖出方向：
                # - target_multiplier倍ATR作为短期目标（当前价格 - target_multiplier*ATR）
                # - STOP_LOSS_MULTIPLIER倍ATR作为止损价格（当前价格 + STOP_LOSS_MULTIPLIER*ATR）
                atr_one = current_price - atr_value
                target_short = current_price - target_multiplier * atr_value
                stop_loss = current_price + self.config['STOP_LOSS_MULTIPLIER'] * atr_value
            
            # 移除中期和长期目标
            target_medium = 0.0
            target_long = 0.0
            
            # 创建动态时间框架信号字典，基于TIMEFRAME_DATA_LENGTHS配置
            timeframe_signals = {}
            for timeframe in TRADING_CONFIG.get('TIMEFRAME_DATA_LENGTHS', {}).keys():
                timeframe_signals[timeframe] = signals.get(timeframe, '观望')
            
            return MultiTimeframeSignal(
                symbol=symbol,
                weekly_trend="观望",  # 默认值，不再使用
                daily_trend="观望",   # 默认值，不再使用
                h4_signal=signals.get('4h', '观望'),
                h1_signal=signals.get('1h', '观望'),
                m15_signal=signals.get('15m', '观望'),
                timeframe_signals=timeframe_signals,
                overall_action=overall_action,
                confidence_level=confidence,
                total_score=total_score,
                entry_price=current_price,
                target_short=target_short,
                target_medium=target_medium,
                target_long=target_long,
                stop_loss=stop_loss,
                atr_one=atr_one,
                reasoning=reasoning,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            # 实际使用时应该记录日志
            print(f"多时间框架分析{symbol}失败: {e}")
            return None
            
    def _analyze_timeframe(self, df: pd.DataFrame, timeframe: str) -> tuple:
        """分析单个时间框架"""
        if df.empty or len(df) < 20:
            return "观望", 0.0
        
        current_price = df['close'].iloc[-1]
         
        # 评分系统
        score = 0
        
        # 使用配置的交易信号触发周期
        if timeframe == self.config["SIGNAL_TRIGGER_TIMEFRAME"]:
            # 交易信号触发周期只运行RSI交叉评分
            score += calculate_rsi_crossover_score(df)
        else:
            # 非交易信号触发周期运行其他评分方法
            score += calculate_trend_indicators_and_score(df, current_price, timeframe)
            score += calculate_rsi_score(df, timeframe)
            score += calculate_volume_score(df)
        
        
        # 根据时间框架调整权重 - 移除1w和1d的特殊处理
        if timeframe in ['5m', '15m']:
            score *= 0.8  # 短期时间框架权重较低
        
        # 确定信号
        if score >= 3:
            action = "强烈买入"
        elif score >= 1.5:
            action = "买入"
        elif score <= -3:
            action = "强烈卖出"
        elif score <= -1.5:
            action = "卖出"
        else:
            action = "观望"
        
        strength = min(abs(score) / 4.0, 1.0)
        return action, strength
    
    def get_required_timeframes(self) -> Dict[str, int]:
        """
        获取策略所需的时间框架和数据长度
        
        Returns:
            字典，键为时间框架名称，值为所需数据长度
        """
        return TRADING_CONFIG.get('TIMEFRAME_DATA_LENGTHS', {
            '4h': 168,   # 4小时
            '1h': 168,   # 1小时
            '15m': 168   # 15分钟
        })
    
    def save_trade_signals(self, opportunities: List[Any]) -> Optional[str]:
        """保存交易信号到文件，并发送到API
        
        参数:
            opportunities: 交易机会列表，支持不同类型的信号对象
        
        返回:
            生成的文件路径，如果没有信号则返回None
        """
        # 筛选符合条件的交易信号
        trade_signals = []
        
        for op in opportunities:
            # 检查信号对象是否具有基本必要属性
            if not (hasattr(op, 'symbol') and hasattr(op, 'overall_action')):
                continue
            
            # 检查是否是买入信号
            if hasattr(op, 'total_score') and op.total_score >= self.config.get('BUY_THRESHOLD') and op.overall_action == "买入":
                # 如果是MultiTimeframeSignal类型，应用特定的过滤规则
                if isinstance(op, MultiTimeframeSignal):
                    # 检查任一周期是否有卖出信号
                    has_sell_signal = False
                    # 优先使用timeframe_signals字典检查所有配置的时间框架
                    if hasattr(op, 'timeframe_signals') and isinstance(op.timeframe_signals, dict):
                        has_sell_signal = any("卖出" in signal for signal in op.timeframe_signals.values())
                    
                    if has_sell_signal:
                        logger.info(f"{op.symbol} 买入信号因任一周期有卖出信号而被过滤掉")
                        continue
                    
                    # 应用交易信号触发周期过滤
                    signal_trigger_timeframe = self.config.get('SIGNAL_TRIGGER_TIMEFRAME', '15m')
                    
                    # 检查交易信号触发周期的条件
                    # 优先使用timeframe_signals字典
                    if hasattr(op, 'timeframe_signals') and isinstance(op.timeframe_signals, dict):
                        if signal_trigger_timeframe in op.timeframe_signals:
                            if "买入" not in op.timeframe_signals[signal_trigger_timeframe]:
                                continue
                  
                    
                    # 符合交易信号触发周期的条件，继续处理
                        # 添加止损价格过滤
                        if hasattr(op, 'entry_price') and hasattr(op, 'stop_loss'):
                            price_diff_percent = abs(op.entry_price - op.stop_loss) / op.entry_price * 100
                            if price_diff_percent >= 0.3 and price_diff_percent <= 10:
                                trade_signals.append(op)
                            elif price_diff_percent < 0.3:
                                logger.info(f"{op.symbol} 买入信号因止损价格距离当前价格不足0.3%而被过滤掉: {price_diff_percent:.2f}%")
                            else:
                                logger.info(f"{op.symbol} 买入信号因止损价格距离当前价格超过10%而被过滤掉: {price_diff_percent:.2f}%")
                        else:
                            trade_signals.append(op)
                else:
                    # 对于非MultiTimeframeSignal类型，应用通用过滤规则
                    trade_signals.append(op)
                         
            # 检查是否是卖出信号
            elif hasattr(op, 'total_score') and op.total_score <= self.config.get('SELL_THRESHOLD') and op.overall_action == "卖出":
                # 如果是MultiTimeframeSignal类型，应用特定的过滤规则
                if isinstance(op, MultiTimeframeSignal):
                    # 检查任一周期是否有买入信号
                    has_buy_signal = False
                    # 优先使用timeframe_signals字典检查所有配置的时间框架
                    if hasattr(op, 'timeframe_signals') and isinstance(op.timeframe_signals, dict):
                        has_buy_signal = any("买入" in signal for signal in op.timeframe_signals.values())
                  
                     
                    if has_buy_signal:
                        logger.info(f"{op.symbol} 卖出信号因任一周期有买入信号而被过滤掉")
                        continue
                    
                    # 应用交易信号触发周期过滤
                    signal_trigger_timeframe = self.config.get('SIGNAL_TRIGGER_TIMEFRAME', '15m')
                    
                    # 检查交易信号触发周期的条件
                    # 优先使用timeframe_signals字典
                    if hasattr(op, 'timeframe_signals') and isinstance(op.timeframe_signals, dict):
                        if signal_trigger_timeframe in op.timeframe_signals:
                            if "卖出" not in op.timeframe_signals[signal_trigger_timeframe]:
                                continue
                
                    
                    # 符合交易信号触发周期的条件，继续处理
                        # 添加止损价格过滤
                        if hasattr(op, 'entry_price') and hasattr(op, 'stop_loss'):
                            price_diff_percent = abs(op.entry_price - op.stop_loss) / op.entry_price * 100
                            if price_diff_percent >= 0.3 and price_diff_percent <= 10:
                                trade_signals.append(op)
                            elif price_diff_percent < 0.3:
                                logger.info(f"{op.symbol} 卖出信号因止损价格距离当前价格不足0.3%而被过滤掉: {price_diff_percent:.2f}%")
                            else:
                                logger.info(f"{op.symbol} 卖出信号因止损价格距离当前价格超过10%而被过滤掉: {price_diff_percent:.2f}%")
                        else:
                            trade_signals.append(op)
                else:
                    # 对于非MultiTimeframeSignal类型，应用通用过滤规则
                    trade_signals.append(op)
        
        # 如果有交易信号，检查已持有的标的并过滤
        if len(trade_signals) > 0:
            try:
                # 使用OKX接口获取当前仓位
                print("=== 开始获取OKX当前仓位数据 ===")
                
                # 创建OKX AccountAPI实例
                try:
                    account_api = AccountAPI(
                        api_key=OKX_CONFIG['api_key'],
                        api_secret_key=OKX_CONFIG['secret'],
                        passphrase=OKX_CONFIG['passphrase'],
                        use_server_time=True,
                        flag='1' if OKX_CONFIG['sandbox'] else '0',  # 1=测试环境, 0=正式环境
                        debug=False
                    )
                    
                    # 调用lib中的函数获取仓位数据
                    formatted_positions = get_okx_positions(self.exchange)
                    print(formatted_positions)
                    
                    # 提取已持有的标的（格式：KAITO/USDT）
                    held_symbols_converted = []
                    for position in formatted_positions:
                        symbol = position.get('symbol', '')
                        if symbol:
                            held_symbols_converted.append(symbol)
                    
                    # 检查持仓数量是否超过最大限制
                    max_positions = self.config.get('MAX_POSITIONS', 10)
                    current_position_count = len(held_symbols_converted)
                    
                    if current_position_count >= max_positions:
                        # 如果已持仓数量超过最大限制，放弃所有交易信号
                        logger.info(f"当前持仓数量({current_position_count})已达到或超过最大限制({max_positions})，放弃所有交易信号")
                        trade_signals = []
                    else:
                        # 过滤掉已持有的标的
                        original_count = len(trade_signals)

                        # logger.info(f"当前持仓标的: {held_symbols_converted}")
                        # logger.info(f"当前持仓标的: {trade_signals}")
                        trade_signals = [signal for signal in trade_signals if signal.symbol not in held_symbols_converted]
                        
                        # 记录过滤信息
                        filtered_count = original_count - len(trade_signals)
                        if filtered_count > 0:
                            logger.info(f"已从交易信号中过滤掉 {filtered_count} 个已持有的标的")
                except Exception as e:
                    logger.error(f"创建OKX API实例失败: {e}")
                    # 继续处理交易信号，不中断主流程
            except Exception as e:
                logger.error(f"获取OKX仓位数据时发生错误: {e}")
                # 即使获取仓位数据出错，也继续处理交易信号，不中断主流程

        # 只有当有交易信号时才生成文件
        if len(trade_signals) > 0:
            # 创建交易信号目录
            signal_dir = "reports/trade_signals"
            os.makedirs(signal_dir, exist_ok=True)
            
            # 文件名格式：trade_signals_YYYYMMDD_HHMMSS.txt
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{signal_dir}/trade_signals_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("📊 交易信号记录\n")
                f.write("=" * 80 + "\n")
                f.write(f"记录时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"记录信号: {len(trade_signals)} 个\n")
                f.write(f"策略名称: {self.get_name()}\n")
                f.write("=" * 80 + "\n\n")
                
                for i, signal in enumerate(trade_signals, 1):
                    f.write(f"【信号 {i}】 {signal.symbol}\n")
                    f.write("-" * 60 + "\n")
                    f.write(f"操作: {signal.overall_action}\n")
                    f.write(f"评分: {signal.total_score:.3f}\n")
                    f.write(f"当前价格: {signal.entry_price:.6f} USDT\n")
                    f.write(f"短期目标 (1.5倍ATR): {signal.target_short:.6f} USDT\n")
                    f.write(f"止损价格 (1倍ATR反向价格): {signal.stop_loss:.6f} USDT\n")
                    f.write(f"时间戳: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"分析依据: {'; '.join(signal.reasoning)}\n")
                    f.write("\n" + "=" * 80 + "\n\n")
            
            # 发送HTTP POST请求到指定API
            for signal in trade_signals:
                try:
                    # 格式化name参数：从KAITO/USDT转换为KAITO（去掉-USDT后缀）
                    name = signal.symbol.replace('/', '-').replace(':USDT', '')
                    
                    # 使用lib2.py中的send_trading_signal_to_api方法发送交易信号，传入LOSS参数
                    # 从配置中获取LOSS值，如果不存在则使用默认值1
                    loss_value = self.config.get('LOSS', 1)
                    send_trading_signal_to_api(signal, name, logger, LOSS=loss_value)  
                except Exception as e:
                    logger.error(f"发送交易信号到API时发生错误: {e}")
                     
            return filename
        
        # 没有交易信号时返回None
        return None
        
    def analyze_positions(self, current_positions: List[Dict[str, Any]], opportunities: List[Any]) -> List[Dict[str, Any]]:
        # 修复括号不匹配问题，移除了多余的右括号
        positions_needing_attention = []
        
        for position in current_positions:
            # 获取持仓的交易对
            pos_symbol = position.get('symbol', '')
            if not pos_symbol:
                continue
            
            # 提取标的名称（去掉合约后缀）
            if ':' in pos_symbol:
                base_symbol = pos_symbol.split(':')[0]  # 例如 BTC/USDT:USDT -> BTC/USDT
            else:
                base_symbol = pos_symbol
            
            # 检查多头仓位
            if position.get('posSide') == 'long':
                # 查找是否有策略建议卖出
                related_opportunity = next((opp for opp in opportunities if hasattr(opp, 'symbol') and opp.symbol == base_symbol), None)
                if related_opportunity and hasattr(related_opportunity, 'overall_action') and related_opportunity.overall_action == "卖出":
                    positions_needing_attention.append({**position, 'reason': f'{self.get_name()}策略建议平仓'})
            # 检查空头仓位
            elif position.get('posSide') == 'short':
                # 查找是否有策略建议买入
                related_opportunity = next((opp for opp in opportunities if hasattr(opp, 'symbol') and opp.symbol == base_symbol), None)
                if related_opportunity and hasattr(related_opportunity, 'overall_action') and related_opportunity.overall_action == "买入":
                    positions_needing_attention.append({**position, 'reason': f'{self.get_name()}策略建议平仓'})
            
            # 检查持仓时间超过5小时的标的
            if position.get('datetime'):
                try:
                    # 计算持仓时间（小时）
                    entry_time = datetime.strptime(position['datetime'], '%Y-%m-%d %H:%M:%S')
                    holding_hours = (datetime.now() - entry_time).total_seconds() / 3600
                    
                    # 只有持仓超过5小时才记录
                    if holding_hours >= 5:
                        positions_needing_attention.append({**position, 'reason': f'持仓时间超过5小时 ({round(holding_hours, 2)}小时)'})
                        logger.info(f"记录持仓超过5小时的标的: {pos_symbol} (持仓时间: {round(holding_hours, 2)}小时)")
                except Exception as e:
                    logger.error(f"计算持仓时间时发生错误: {e}")
        
        return positions_needing_attention
        
    def save_multi_timeframe_analysis(self, opportunities: List[Any]) -> Optional[str]:
        """生成多时间框架分析报告，格式符合report_viewer_python的解析要求"""
        # 设置报告目录路径
        report_dir = "reports"
        os.makedirs(report_dir, exist_ok=True)
        
        # 保留所有交易机会，不进行过滤
        all_opportunities = opportunities
        
        # 如果没有交易机会，不生成报告
        if not all_opportunities:
            logger.info("没有交易机会，不生成多时间框架分析报告")
            return None
        
        # 按照分数的绝对值倒序排序
        try:
            all_opportunities.sort(key=lambda x: abs(getattr(x, 'total_score', 0)), reverse=True)
        except Exception as e:
            logger.error(f"排序交易机会时发生错误: {e}")
        
        # 文件名固定为multi_timeframe_analysis_new.txt
        filename = os.path.join(report_dir, "multi_timeframe_analysis_new.txt")
        
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入报告头部
            f.write("=" * 80 + "\n")
            f.write("📊 多时间框架专业分析报告\n")
            f.write("=" * 80 + "\n")
            f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"时间框架维度: 周线→日线→4小时→1小时→15分钟\n")
            f.write(f"发现机会: {len(all_opportunities)}\n")
            f.write(f"策略名称: {self.get_name()}\n")
            f.write("=" * 80 + "\n\n")
            
            # 写入每个交易机会
            for i, opportunity in enumerate(all_opportunities, 1):
                # 确保机会对象有必要的属性
                if not hasattr(opportunity, 'symbol'):
                    continue
                
                # 获取所需属性，使用默认值作为后备
                symbol = getattr(opportunity, 'symbol', '未知交易对')
                overall_action = getattr(opportunity, 'overall_action', '未知')
                confidence_level = getattr(opportunity, 'confidence_level', '未知')
                total_score = getattr(opportunity, 'total_score', 0.0)
                entry_price = getattr(opportunity, 'entry_price', 0.0)
                target_short = getattr(opportunity, 'target_short', 0.0)
                stop_loss = getattr(opportunity, 'stop_loss', 0.0)
                
                # 获取时间框架信号，使用默认值作为后备
                h4_signal = getattr(opportunity, 'h4_signal', '未知')
                h1_signal = getattr(opportunity, 'h1_signal', '未知')
                m15_signal = getattr(opportunity, 'm15_signal', '未知')
                
                # 为了兼容解析，设置默认的周线和日线信号
                weekly_trend = getattr(opportunity, 'weekly_trend', '观望')
                daily_trend = getattr(opportunity, 'daily_trend', '观望')
                
                # 获取分析依据
                reasoning = getattr(opportunity, 'reasoning', [])
                reasoning_text = '; '.join(reasoning) if isinstance(reasoning, list) else str(reasoning)
                
                # 写入交易机会信息
                f.write(f"【机会 {i}】\n")
                f.write("-" * 60 + "\n")
                f.write(f"交易对: {symbol}\n")
                f.write(f"综合建议: {overall_action}\n")
                f.write(f"信心等级: {confidence_level}\n")
                f.write(f"总评分: {total_score:.3f}\n")
                f.write(f"当前价格: {entry_price:.6f}\n")
                
                # 写入多时间框架分析
                f.write(f"周线趋势: {weekly_trend}\n")
                f.write(f"日线趋势: {daily_trend}\n")
                f.write(f"4小时信号: {h4_signal}\n")
                f.write(f"1小时信号: {h1_signal}\n")
                f.write(f"15分钟信号: {m15_signal}\n")
                
                # 写入目标价格和止损价格
                f.write(f"短期目标: {target_short:.6f}\n")
                f.write(f"止损价格: {stop_loss:.6f}\n")
                
                # 写入分析依据
                f.write(f"分析依据: {reasoning_text}\n")
                f.write("\n" + "=" * 80 + "\n\n")
        
        logger.info(f"✅ 多时间框架分析报告已保存至: {filename}")
        return filename
        
    def save_positions_needing_attention(self, positions: List[Dict[str, Any]]) -> str:
        """保存需要关注的持仓信息"""
        # 创建需要关注的持仓目录
        attention_dir = "reports/positions_needing_attention"
        os.makedirs(attention_dir, exist_ok=True)
        
        # 文件名格式：positions_needing_attention_YYYYMMDD_HHMMSS.txt
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{attention_dir}/positions_needing_attention_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("⚠️  需要关注的持仓记录\n")
            f.write("=" * 80 + "\n")
            f.write(f"记录时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"记录持仓: {len(positions)} 个\n")
            f.write(f"策略名称: {self.get_name()}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, pos in enumerate(positions, 1):
                f.write(f"【持仓 {i}】 {pos.get('symbol', '未知')}\n")
                f.write("-" * 60 + "\n")
                f.write(f"持仓方向: {pos.get('posSide', '未知')}\n")
                f.write(f"持仓数量: {pos.get('amount', '0')}\n")
                f.write(f"持仓均价: {pos.get('entry_price', '0.0')}\n")
                f.write(f"当前价格: {pos.get('current_price', '0.0')}\n")
                f.write(f"开仓时间: {pos.get('datetime', '未知')}\n")
                f.write(f"关注原因: {pos.get('reason', '未知')}\n")
                f.write("\n" + "=" * 80 + "\n\n")
        
        return filename
