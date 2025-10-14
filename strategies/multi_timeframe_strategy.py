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
from dataclasses import dataclass
import logging

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
    "FILTER_BY_15M": True,
    "FILTER_BY_1H": False,
    "MAX_POSITIONS": 3,
    "MECHANISM_ID": 13,
    "LOSS": 0.2
}

from strategies.base_strategy import BaseStrategy
from lib import calculate_atr, send_trading_signal_to_api

# 配置日志记录器
logger = logging.getLogger(__name__)

# 导入其他必要配置
from config import REDIS_CONFIG


@dataclass
class MultiTimeframeSignal:
    """多时间框架交易信号"""
    symbol: str
    weekly_trend: str
    daily_trend: str
    h4_signal: str
    h1_signal: str
    m15_signal: str
    overall_action: str
    confidence_level: str
    total_score: float
    entry_price: float
    target_short: float  # 1.5倍ATR值 (作为短期目标)
    target_medium: float  # 保留字段以确保兼容性
    target_long: float  # 保留字段以确保兼容性
    stop_loss: float  # 基于1倍ATR反向计算的止损价格
    atr_one: float  # 保留字段以确保兼容性
    reasoning: List[str]
    timestamp: datetime


class MultiTimeframeStrategy(BaseStrategy):
    """多时间框架分析策略实现"""
    
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
            
            return MultiTimeframeSignal(
                symbol=symbol,
                weekly_trend="观望",  # 默认值，不再使用
                daily_trend="观望",   # 默认值，不再使用
                h4_signal=signals.get('4h', '观望'),
                h1_signal=signals.get('1h', '观望'),
                m15_signal=signals.get('15m', '观望'),
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
        
        # 计算技术指标
        sma_20 = df['close'].rolling(20).mean().iloc[-1]
        sma_50 = df['close'].rolling(50).mean() if len(df) >= 50 else pd.Series([current_price])
        sma_50 = sma_50.iloc[-1] if not sma_50.empty else current_price
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi = rsi_series.iloc[-1]
        
        # 计算ATR (平均真实波动幅度)
        atr_value = calculate_atr(df.copy())
        
        # 成交量
        volume_avg = df['volume'].rolling(20).mean().iloc[-1]
        volume_current = df['volume'].iloc[-1]
        volume_ratio = volume_current / volume_avg if volume_avg > 0 else 1
        
        # 评分系统
        score = 0
        
        # 趋势评分 - 移除1w和1d的特殊判断
        if (timeframe != "15m"):
            if current_price > sma_20 > sma_50:
                score += 2
            elif current_price > sma_20:
                score += 1
            elif current_price < sma_20 < sma_50:
                score -= 2
            elif current_price < sma_20:
                score -= 1
        
        # RSI评分
        if timeframe == "15m" and len(rsi_series) >= 2:
            # 15分钟时间框架特殊处理 - 交叉分析
            prev_rsi = rsi_series.iloc[-2]
            if prev_rsi < 30 and rsi > 30:
                score += 2  # 前一根k小于30，当前k大于30 +2分
            elif prev_rsi > 70 and rsi < 70:
                score -= 2  # 前一根k大于70，当前k小于70 -2分
            elif 30 < rsi < 70:
                score += 0
        else:
            # 其他时间框架保持原有逻辑
            if 30 < rsi < 70:
                score += 0
            elif rsi < 30:
                score += 2  # 超卖
            elif rsi > 70:
                score -= 2  # 超买
        
        # 成交量评分
        if volume_ratio > 1.5:
            score += 1
        elif volume_ratio < 0.7:
            score -= 0.5
        
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
        return {
            '4h': 168,   # 4小时
            '1h': 168,   # 1小时
            '15m': 168   # 15分钟
        }
    
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
            if hasattr(op, 'total_score') and op.total_score >= TRADING_CONFIG.get('BUY_THRESHOLD') and op.overall_action == "买入":
                # 如果是MultiTimeframeSignal类型，应用特定的过滤规则
                if isinstance(op, MultiTimeframeSignal):
                    # 检查任一周期是否有卖出信号
                    has_sell_signal = False
                    if all(hasattr(op, attr) for attr in ['h4_signal', 'h1_signal', 'm15_signal']):
                        has_sell_signal = ("卖出" in op.h4_signal or 
                                          "卖出" in op.h1_signal or 
                                          "卖出" in op.m15_signal)
                    
                    if has_sell_signal:
                        logger.info(f"{op.symbol} 买入信号因任一周期有卖出信号而被过滤掉")
                        continue
                    
                    # 应用时间框架过滤
                    filter_by_15m = TRADING_CONFIG.get('FILTER_BY_15M', False)
                    filter_by_1h = TRADING_CONFIG.get('FILTER_BY_1H', False)
                    
                    # 检查时间框架条件
                    is_15m_buy = "买入" in op.m15_signal if hasattr(op, 'm15_signal') else True
                    is_1h_buy = "买入" in op.h1_signal if hasattr(op, 'h1_signal') else True
                    
                    # 根据过滤开关决定是否添加信号
                    if ((not filter_by_15m or is_15m_buy) and 
                        (not filter_by_1h or is_1h_buy)):
                        # 添加止损价格过滤
                        if hasattr(op, 'entry_price') and hasattr(op, 'stop_loss'):
                            price_diff_percent = abs(op.entry_price - op.stop_loss) / op.entry_price * 100
                            if price_diff_percent >= 0.3:
                                trade_signals.append(op)
                            else:
                                logger.info(f"{op.symbol} 买入信号因止损价格距离当前价格不足0.3%而被过滤掉: {price_diff_percent:.2f}%")
                        else:
                            trade_signals.append(op)
                else:
                    # 对于非MultiTimeframeSignal类型，应用通用过滤规则
                    trade_signals.append(op)
                         
            # 检查是否是卖出信号
            elif hasattr(op, 'total_score') and op.total_score <= TRADING_CONFIG.get('SELL_THRESHOLD') and op.overall_action == "卖出":
                # 如果是MultiTimeframeSignal类型，应用特定的过滤规则
                if isinstance(op, MultiTimeframeSignal):
                    # 检查任一周期是否有买入信号
                    has_buy_signal = False
                    if all(hasattr(op, attr) for attr in ['h4_signal', 'h1_signal', 'm15_signal']):
                        has_buy_signal = ("买入" in op.h4_signal or 
                                          "买入" in op.h1_signal or 
                                          "买入" in op.m15_signal)
                     
                    if has_buy_signal:
                        logger.info(f"{op.symbol} 卖出信号因任一周期有买入信号而被过滤掉")
                        continue
                    
                    # 应用时间框架过滤
                    filter_by_15m = TRADING_CONFIG.get('FILTER_BY_15M', False)
                    filter_by_1h = TRADING_CONFIG.get('FILTER_BY_1H', False)
                    
                    # 检查时间框架条件
                    is_15m_sell = "卖出" in op.m15_signal if hasattr(op, 'm15_signal') else True
                    is_1h_sell = "卖出" in op.h1_signal if hasattr(op, 'h1_signal') else True
                    
                    # 根据过滤开关决定是否添加信号
                    if ((not filter_by_15m or is_15m_sell) and 
                        (not filter_by_1h or is_1h_sell)):
                        # 添加止损价格过滤
                        if hasattr(op, 'entry_price') and hasattr(op, 'stop_loss'):
                            price_diff_percent = abs(op.entry_price - op.stop_loss) / op.entry_price * 100
                            if price_diff_percent >= 0.3:
                                trade_signals.append(op)
                            else:
                                logger.info(f"{op.symbol} 卖出信号因止损价格距离当前价格不足0.3%而被过滤掉: {price_diff_percent:.2f}%")
                        else:
                            trade_signals.append(op)
                else:
                    # 对于非MultiTimeframeSignal类型，应用通用过滤规则
                    trade_signals.append(op)
        
        # 如果有交易信号，检查Redis中已持有的标的并过滤
        if len(trade_signals) > 0:
            try:
                # 连接Redis
                host, port = REDIS_CONFIG['ADDR'].split(':')
                r = redis.Redis(
                    host=host,
                    port=int(port),
                    password=REDIS_CONFIG['PASSWORD'],
                    decode_responses=True,
                    socket_timeout=5
                )
                
                # 读取okx_positions_data
                positions_data = r.get('okx_positions_data')
                
                if positions_data:
                    # 解析JSON数据
                    positions_info = json.loads(positions_data)
                    
                    # 提取已持有的标的（格式：KAITO-USDT-SWAP）
                    held_symbols = []
                    if 'm' in positions_info and 'data' in positions_info['m']:
                        for pos in positions_info['m']['data']:
                            if 'instId' in pos:
                                held_symbols.append(pos['instId'])
                    
                    # 将Redis中的格式（KAITO-USDT-SWAP）转换为系统中的格式（KAITO/USDT）
                    held_symbols_converted = []
                    for symbol in held_symbols:
                        # 处理格式转换：KAITO-USDT-SWAP -> KAITO/USDT
                        parts = symbol.split('-')
                        if len(parts) >= 3:
                            # 例如：KAITO-USDT-SWAP -> KAITO/USDT
                            converted_symbol = f"{parts[0]}/{parts[1]}"
                            held_symbols_converted.append(converted_symbol)
                    
                    # 检查持仓数量是否超过最大限制
                    max_positions = TRADING_CONFIG.get('MAX_POSITIONS', 10)
                    current_position_count = len(held_symbols_converted)
                    
                    if current_position_count >= max_positions:
                        # 如果已持仓数量超过最大限制，放弃所有交易信号
                        logger.info(f"当前持仓数量({current_position_count})已达到或超过最大限制({max_positions})，放弃所有交易信号")
                        trade_signals = []
                    else:
                        # 过滤掉已持有的标的
                        original_count = len(trade_signals)
                        trade_signals = [signal for signal in trade_signals if signal.symbol not in held_symbols_converted]
                        
                        # 记录过滤信息
                        filtered_count = original_count - len(trade_signals)
                        if filtered_count > 0:
                            logger.info(f"已从交易信号中过滤掉 {filtered_count} 个已持有的标的")
                
            except Exception as e:
                logger.error(f"Redis连接或数据处理失败: {e}")
                # 即使Redis出错，也继续处理交易信号，不中断主流程
        
        # 只有当有交易信号时才生成文件
        if len(trade_signals) > 0:
            # 创建交易信号目录
            signal_dir = "trade_signals"
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
                    
                    # 使用lib.py中的send_trading_signal_to_api方法发送交易信号
                    send_trading_signal_to_api(signal, name, logger)  
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
        
    def save_positions_needing_attention(self, positions: List[Dict[str, Any]]) -> str:
        """保存需要关注的持仓信息"""
        # 创建需要关注的持仓目录
        attention_dir = "positions_needing_attention"
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
