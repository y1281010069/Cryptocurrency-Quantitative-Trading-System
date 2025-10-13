#!/usr/bin/env python3
"""
多时间框架专业投资系统
====================

专业的多时间框架投资分析系统，兼顾日内交易和长期投资
- 长期趋势：周线、日线分析
- 中期波段：4小时、1小时分析  
- 短期入场：15分钟、5分钟分析
"""

import ccxt
import pandas as pd
import numpy as np
import time
import logging
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import os
import redis
from lib import calculate_atr, get_okx_positions

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 尝试导入配置文件，如果不存在则使用默认值
try:
    from config import TRADING_CONFIG, REDIS_CONFIG
except ImportError:
    # 使用默认配置
    TRADING_CONFIG = {
        'BUY_THRESHOLD': 0.5,     # 买入信号评分阈值（大于等于）
        'SELL_THRESHOLD': -0.5,   # 卖出信号评分阈值（小于等于）
        'ATR_PERIOD': 14,
        'TARGET_MULTIPLIER': 4.5,
        'STOP_LOSS_MULTIPLIER': 3,
        'ENABLED_SYMBOLS': [],
        'DISABLED_SYMBOLS': ['USDC/USDT'],
        
        # 时间框架过滤配置
        'FILTER_BY_15M': False,   # 是否按15分钟时间框架过滤（买入信号需要15分钟也为买入）
        'FILTER_BY_1H': False,    # 是否按1小时时间框架过滤（买入信号需要1小时也为买入）
        
        # 持仓控制配置
        'MAX_POSITIONS': 10       # 最大持仓数量限制，超过此数量将放弃新的交易机会
    }
    # 默认Redis配置
    REDIS_CONFIG = {
        'ADDR': "localhost:6379",
        'PASSWORD': ""
    }
    logger.warning("配置文件未找到，使用默认配置")

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

class MultiTimeframeProfessionalSystem:
    """多时间框架专业投资系统"""
    
    def __init__(self, config_file: str = "config.py"):
        """初始化系统
        
        Args:
            config_file: 配置文件路径
        """
        self.load_config(config_file)
        self.setup_exchange()
        self.output_dir = "multi_timeframe_reports"
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info("多时间框架专业投资系统初始化完成")
    
    def load_config(self, config_file: str):
        """加载API配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_content = f.read()
            config_globals = {}
            exec(config_content, config_globals)
            self.api_key = config_globals.get('API_KEY', '')
            self.secret_key = config_globals.get('SECRET_KEY', '')
            self.passphrase = config_globals.get('PASSPHRASE', '')
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            raise
    
    def setup_exchange(self):
        """设置交易所连接
        """
        try:
            # 使用ccxt连接OKX交易所
                self.exchange = ccxt.okx({
                    'apiKey': self.api_key,
                    'secret': self.secret_key,
                    'password': self.passphrase,
                    'sandbox': False,
                    'enableRateLimit': True,
                    'timeout': 30000,
                })
                self.exchange.load_markets()
                logger.info("CCXT OKX连接成功")
        except Exception as e:
            logger.error(f"交易所连接失败: {e}")
            raise
            

    def save_positions_needing_attention(self, positions):
        """保存需要关注的持仓记录到文件
        
        Args:
            positions (list): 需要关注的持仓列表
        
        Returns:
            str: 保存的文件路径
        """
        try:
            # 创建保存目录
            output_dir = os.path.join(self.output_dir, 'attention_positions')
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名（包含时间戳）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(output_dir, f'positions_attention_{timestamp}.json')
            
            # 保存为JSON文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(positions, f, ensure_ascii=False, indent=2)
            
            logger.info(f"需关注的持仓已保存至: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"保存需关注持仓记录失败: {e}")
            return ''
    
    def get_timeframe_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """获取指定时间框架数据"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"获取{symbol} {timeframe}数据失败: {e}")
            return pd.DataFrame()
    
    def analyze_timeframe(self, df: pd.DataFrame, timeframe: str) -> tuple:
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
        
        # 趋势评分
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
        
        # 根据时间框架调整权重
        if timeframe in ['1w', '1d']:
            score *= 1.2  # 长期时间框架权重更高
        elif timeframe in ['5m', '15m']:
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
    
    def comprehensive_analysis(self, symbol: str) -> Optional[MultiTimeframeSignal]:
        """综合多时间框架分析"""
        try:
            # 获取多时间框架数据
            timeframes = {
                '1w': 100,   # 周线
                '1d': 200,   # 日线
                '4h': 168,   # 4小时
                '1h': 168,   # 1小时
                '15m': 96    # 15分钟
            }
            
            data = {}
            signals = {}
            strengths = {}
            
            for tf, limit in timeframes.items():
                df = self.get_timeframe_data(symbol, tf, limit)
                time.sleep(0.3) 
                if not df.empty:
                    action, strength = self.analyze_timeframe(df, tf)
                    data[tf] = df
                    signals[tf] = action
                    strengths[tf] = strength
            
            if len(data) < 3:  # 至少需要3个时间框架
                return None
            
            current_price = data['1h']['close'].iloc[-1] if '1h' in data else data[list(data.keys())[0]]['close'].iloc[-1]
            
            # 综合评分
            weights = {'1w': 0.25, '1d': 0.25, '4h': 0.20, '1h': 0.20, '15m': 0.10}
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
            if total_score >= TRADING_CONFIG['BUY_THRESHOLD']:
                overall_action = "买入"
                confidence = "高"
            elif total_score <= TRADING_CONFIG['SELL_THRESHOLD']:
                overall_action = "卖出"
                confidence = "高"
            else:
                overall_action = "观望"
                confidence = "低"
            
            # 获取15分钟时间框架的数据来计算ATR
            # 首先检查是否已经有15m的数据
            if '15m' in data:
                df_15m = data['15m']
            else:
                # 如果没有，重新获取数据
                df_15m = self.get_timeframe_data(symbol, '15m', 50)
                time.sleep(0.3)
            
            # 计算ATR值
            atr_value = calculate_atr(df_15m)
            
            # 检查是否所有时间框架都为买入或都为卖出
            logger.debug(f"{symbol} 原始信号组合: {signals}")
            
            # 首先检查是否存在观望信号
            has_neutral = any("观望" in signal for signal in signals.values())
            
            # 过滤掉"观望"信号
            valid_signals = [signal for signal in signals.values() if "观望" not in signal]
            logger.debug(f"{symbol} 过滤后有效信号: {valid_signals}")
            
            # 只有当没有观望信号且所有有效信号方向一致时，才算一致
            all_agreed = False
            if not has_neutral and valid_signals:
                # 检查所有有效信号是否方向一致
                first_direction = "买入" if "买入" in valid_signals[0] else "卖出"
                all_agreed = True
                for signal in valid_signals[1:]:
                    if first_direction not in signal:
                        all_agreed = False
                        break
            
            logger.info(f"{symbol} all_agreed状态: {all_agreed}, 有效信号数量: {len(valid_signals)}, 存在观望信号: {has_neutral}")
            
            # 根据是否所有时间框架一致决定使用的TARGET_MULTIPLIER
            target_multiplier = TRADING_CONFIG['TARGET_MULTIPLIER']
            if all_agreed:
                target_multiplier *= 3  # 所有时间框架一致时，使用3倍的TARGET_MULTIPLIER
                logger.info(f"{symbol} 所有时间框架信号一致且无观望信号，使用3倍盈亏比 (原始乘数: {TRADING_CONFIG['TARGET_MULTIPLIER']}, 调整后乘数: {target_multiplier})")
            else:
                logger.info(f"{symbol} 信号方向不一致或存在观望信号，使用标准盈亏比 (乘数: {target_multiplier})")
            
            # 根据交易方向计算ATR相关价格（做多/做空）
            if overall_action == "买入":
                # 买入方向：
                # - target_multiplier倍ATR作为短期目标（当前价格 + target_multiplier*ATR）
                # - STOP_LOSS_MULTIPLIER倍ATR作为止损价格（当前价格 - STOP_LOSS_MULTIPLIER*ATR）
                atr_one = current_price + atr_value
                target_short = current_price + target_multiplier * atr_value
                stop_loss = current_price - TRADING_CONFIG['STOP_LOSS_MULTIPLIER'] * atr_value
            else:
                # 卖出方向：
                # - target_multiplier倍ATR作为短期目标（当前价格 - target_multiplier*ATR）
                # - STOP_LOSS_MULTIPLIER倍ATR作为止损价格（当前价格 + STOP_LOSS_MULTIPLIER*ATR）
                atr_one = current_price - atr_value
                target_short = current_price - target_multiplier * atr_value
                stop_loss = current_price + TRADING_CONFIG['STOP_LOSS_MULTIPLIER'] * atr_value
            
            # 移除中期和长期目标
            target_medium = 0.0
            target_long = 0.0
            
            return MultiTimeframeSignal(
                symbol=symbol,
                weekly_trend=signals.get('1w', '观望'),
                daily_trend=signals.get('1d', '观望'),
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
            logger.error(f"多时间框架分析{symbol}失败: {e}")
            return None
    
    def run_analysis(self, max_symbols: int = 50):
        """运行多时间框架分析"""
        print("\n" + "="*80)
        print("🚀 多时间框架专业投资系统启动")
        print("="*80)
        print("📊 分析维度: 周线→日线→4H→1H→15M")
        print("🎯 适用场景: 日内交易 + 长期投资")
        print("="*80)
        
        start_time = time.time()
        opportunities = []
        
        try:
            # 获取活跃交易对
            print("🔍 正在获取活跃交易对...")
            markets = self.exchange.load_markets()
            usdt_pairs = [symbol for symbol in markets.keys() 
                         if symbol.endswith('/USDT') and markets[symbol]['active']]
            
            # 获取交易量数据并筛选
            print("📈 正在筛选高流动性交易对...")
            tickers = self.exchange.fetch_tickers()
            volume_filtered = []
            
            for symbol in usdt_pairs:
                if symbol in tickers:
                    ticker = tickers[symbol]
                    volume = ticker.get('quoteVolume', 0)
                    if volume > 2000000:  # 200万USDT以上
                        volume_filtered.append((symbol, volume))
            
            volume_filtered.sort(key=lambda x: x[1], reverse=True)
            selected_symbols = [symbol for symbol, _ in volume_filtered[:max_symbols]]
            
            # 应用币种过滤
            enabled_symbols = TRADING_CONFIG.get('ENABLED_SYMBOLS', [])
            disabled_symbols = TRADING_CONFIG.get('DISABLED_SYMBOLS', [])
            
            # 如果有启用的币种列表，则只保留在列表中的币种
            if enabled_symbols:
                selected_symbols = [sym for sym in selected_symbols if sym in enabled_symbols]
            
            # 排除禁用的币种
            selected_symbols = [sym for sym in selected_symbols if sym not in disabled_symbols]
            
            print(f"📊 开始分析 {len(selected_symbols)} 个高流动性交易对...")
            print("-"*80)
            
            # 并行分析
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_symbol = {
                    executor.submit(self.comprehensive_analysis, symbol): symbol 
                    for symbol in selected_symbols
                }
                
                completed = 0
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    completed += 1
                    try:
                        opportunity = future.result()
                        if opportunity and abs(opportunity.total_score) > 0.1:  # 降低筛选阈值
                            opportunities.append(opportunity)
                            print(f"✅ [{completed:2d}/{len(selected_symbols)}] {symbol:15s} {opportunity.overall_action:6s} (评分: {opportunity.total_score:+.2f})")
                        else:
                            score_text = f"评分: {opportunity.total_score:+.2f}" if opportunity else "分析失败"
                            print(f"⚪ [{completed:2d}/{len(selected_symbols)}] {symbol:15s} 观望   ({score_text})")
                    except Exception as e:
                        print(f"❌ [{completed:2d}/{len(selected_symbols)}] {symbol:15s} 分析失败")
                        logger.error(f"分析{symbol}失败: {e}")
            
            # 按评分排序
            opportunities.sort(key=lambda x: abs(x.total_score), reverse=True)
            
        except Exception as e:
            logger.error(f"筛选失败: {e}")
            print(f"❌ 系统错误: {e}")
        
        print("-"*80)
        
        # 显示结果
        self.print_beautiful_results(opportunities)
        
        # 保存文件
        if opportunities:
            txt_file = self.save_txt_report(opportunities, 'new')
            print(f"\n📄 详细报告已保存: {txt_file}")
            
            # 记录交易信号
            signal_file = self.save_trade_signals(opportunities)
            if signal_file:
                print(f"📊 交易信号已记录至: {signal_file}")
            else:
                print("📊 当前无符合条件的交易信号")


                    # 增加仓位管理
            # 获取当前仓位列表
            current_positions = get_okx_positions(self.exchange)
            
            # 手动为每个position添加datetime字段（不使用use_contract_utils=True）
            for position in current_positions:
                # 格式化timestamp为datetime字符串
                position['datetime'] = datetime.fromtimestamp(
                    position.get('timestamp', 0) / 1000
                ).strftime('%Y-%m-%d %H:%M:%S') if position.get('timestamp') else ''
            
            # 检查是否有需要关注的持仓
            positions_needing_attention = []
            for position in current_positions:
                pos_side = position.get('posSide', '')
                
                # 提取标的名称（去掉合约后缀）
                symbol = position.get('symbol', '')
                if ':' in symbol:
                    base_symbol = symbol.split(':')[0]  # 例如 BTC/USDT:USDT -> BTC/USDT
                else:
                    base_symbol = symbol
                
                # 在opportunities中查找对应标的
                matched_opportunity = next((op for op in opportunities if op.symbol == base_symbol), None)
                
                if matched_opportunity:
                    # 多头仓位逻辑
                    if pos_side == 'long':
                        # 检查是否出现卖出信号、任何周期为卖出信号或所有周期都为观察
                        if ('卖出' in matched_opportunity.overall_action or 
                            '卖出' in matched_opportunity.weekly_trend or 
                            '卖出' in matched_opportunity.daily_trend or 
                            '卖出' in matched_opportunity.h4_signal or 
                            '卖出' in matched_opportunity.h1_signal or 
                            '卖出' in matched_opportunity.m15_signal):
                            # 记录需要关注的持仓
                            positions_needing_attention.append({
                                'symbol': symbol,
                                'direction': pos_side,
                                'amount': position.get('amount', 0),
                                'entry_price': position.get('entry_price', 0),
                                'current_price': position.get('current_price', 0),
                                'profit_percent': position.get('profit_percent', 0),
                                'signal_action': matched_opportunity.overall_action,
                                'confidence_level': matched_opportunity.confidence_level
                            })
                    # 空头仓位逻辑
                    elif pos_side == 'short':
                        # 检查是否出现买入信号、任何周期为买入信号或所有周期都为观察
                        if ('买入' in matched_opportunity.overall_action or 
                            '买入' in matched_opportunity.weekly_trend or 
                            '买入' in matched_opportunity.daily_trend or 
                            '买入' in matched_opportunity.h4_signal or 
                            '买入' in matched_opportunity.h1_signal or 
                            '买入' in matched_opportunity.m15_signal):
                            # 记录需要关注的持仓
                            positions_needing_attention.append({
                                'symbol': symbol,
                                'direction': pos_side,
                                'amount': position.get('amount', 0),
                                'entry_price': position.get('entry_price', 0),
                                'current_price': position.get('current_price', 0),
                                'profit_percent': position.get('profit_percent', 0),
                                'signal_action': matched_opportunity.overall_action,
                                'confidence_level': matched_opportunity.confidence_level
                            })
                else:
                    # 检查持仓时间是否超过5小时再记录
                    try:
                        # 直接从现有position对象获取datetime信息
                        if position.get('datetime'):
                            # 计算持仓时间（小时）
                            entry_time = datetime.strptime(position['datetime'], '%Y-%m-%d %H:%M:%S')
                            holding_hours = (datetime.now() - entry_time).total_seconds() / 3600
                            
                            # 只有持仓超过5小时才记录
                            if holding_hours >= 5:
                                positions_needing_attention.append({
                                    'symbol': symbol,
                                    'direction': pos_side,
                                    'amount': position.get('amount', 0),
                                    'entry_price': position.get('entry_price', 0),
                                    'current_price': position.get('current_price', 0),
                                    'profit_percent': position.get('profit_percent', 0),
                                    'signal_action': '标的不在分析范围内',
                                    'confidence_level': 'N/A',
                                    'holding_hours': round(holding_hours, 2),
                                    'entry_time': entry_time.strftime('%Y-%m-%d %H:%M:%S')
                                })
                                logger.info(f"记录持仓超过5小时的标的: {symbol} (持仓时间: {round(holding_hours, 2)}小时)")
                        else:
                            # 如果无法获取时间信息，默认记录（兼容旧版本）
                            positions_needing_attention.append({
                                'symbol': symbol,
                                'direction': pos_side,
                                'amount': position.get('amount', 0),
                                'entry_price': position.get('entry_price', 0),
                                'current_price': position.get('current_price', 0),
                                'profit_percent': position.get('profit_percent', 0),
                                'signal_action': '标的不在分析范围内',
                                'confidence_level': 'N/A'
                            })
                    except Exception as e:
                        logger.error(f"计算持仓时间时发生错误: {e}")
                        # 出错时默认记录
                        positions_needing_attention.append({
                            'symbol': symbol,
                            'direction': pos_side,
                            'amount': position.get('amount', 0),
                            'entry_price': position.get('entry_price', 0),
                            'current_price': position.get('current_price', 0),
                            'profit_percent': position.get('profit_percent', 0),
                            'signal_action': '标的不在分析范围内',
                            'confidence_level': 'N/A'
                        })
            
            # 如果有需要关注的持仓，保存记录
            if positions_needing_attention:
                attention_file = self.save_positions_needing_attention(positions_needing_attention)
                print(f"⚠️  需关注的持仓已记录至: {attention_file}")
                # 统计各类需关注的持仓数量
                long_count = sum(1 for pos in positions_needing_attention if pos['direction'] == 'long' and pos['signal_action'] != '标的不在分析范围内')
                short_count = sum(1 for pos in positions_needing_attention if pos['direction'] == 'short' and pos['signal_action'] != '标的不在分析范围内')
                not_in_scope_count = sum(1 for pos in positions_needing_attention if pos['signal_action'] == '标的不在分析范围内')
                print(f"📊 需关注的持仓统计: 多头 {long_count} 个, 空头 {short_count} 个, 不在分析范围内 {not_in_scope_count} 个")

                # 记录的这些持仓，循环调用url = 'http://149.129.66.131:81/myOrder'
                for pos in positions_needing_attention:
                    try:
                        # 格式化name参数：从KAITO/USDT转换为KAITO（去掉-USDT后缀）
                        name = pos['symbol'].replace('/', '-').replace(':USDT', '')
                        
                        # 设置ac_type参数：多头对应c_l，空头对应c_s
                        ac_type = 'c_l' if pos['direction'] == 'long' else 'c_s'
                        
                        # 构造请求参数
                        payload = {
                            'name': name,
                            'mechanism_id': TRADING_CONFIG['MECHANISM_ID'],
                            'ac_type': ac_type,
                            'volume_plan': pos['amount']
                        }
                        
                        # 发送POST请求（表单形式）
                        url = 'http://149.129.66.131:81/myOrder'

                        # 打印接口请求信息
                        logger.info(f"发送请求到接口: {url}")
                        logger.info(f"请求参数: {payload}")
                        
                        # 发送请求
                        response = requests.post(url, data=payload, timeout=10)
                        
                        # 打印接口返回信息
                        logger.info(f"接口返回状态码: {response.status_code}")
                        logger.info(f"接口返回内容: {response.text}")
                        
                        # 记录请求结果
                        if response.status_code == 200:
                            logger.info(f"成功发送持仓信息到API: {pos['symbol']} ({pos['direction']})")
                        else:
                            logger.warning(f"发送持仓信息到API失败 (状态码: {response.status_code}): {pos['symbol']}")
                            logger.debug(f"API响应: {response.text}")
                        
                    except Exception as e:
                        logger.error(f"发送持仓信息到API时发生错误: {e}")
                

            else:
                print("✅ 所有持仓状态正常")
        
        print(f"\n⏱️  分析完成！用时: {time.time() - start_time:.1f}秒")
        print("="*80)
    
    def print_beautiful_results(self, opportunities: List[MultiTimeframeSignal]):
        """美观地显示分析结果"""
        print("\n" + "="*100)
        print("🎯 多时间框架投资分析结果")
        print("="*100)
        print(f"📊 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 发现机会: {len(opportunities)} 个")
        
        if not opportunities:
            print("\n❌ 当前市场条件下未发现符合条件的投资机会")
            print("💡 建议: 等待更好的市场时机或降低筛选标准")
            return
        
        print("="*100)
        
        # 统计信息
        buy_ops = [op for op in opportunities if "买入" in op.overall_action]
        sell_ops = [op for op in opportunities if "卖出" in op.overall_action]
        watch_ops = [op for op in opportunities if "观望" in op.overall_action]
        high_confidence = [op for op in opportunities if op.confidence_level == "高"]
        
        print(f"📈 买入机会: {len(buy_ops)} 个 | 📉 卖出机会: {len(sell_ops)} 个 | ⚪ 观望: {len(watch_ops)} 个 | 🎯 高信心: {len(high_confidence)} 个")
        
        # 调试信息：显示所有机会的操作分布
        if opportunities:
            print(f"\n🔍 详细分布:")
            for op in opportunities[:5]:  # 显示前5个
                print(f"   {op.symbol}: {op.overall_action} (评分: {op.total_score:+.2f}, 信心: {op.confidence_level})")
        print("="*100)
        
        for i, op in enumerate(opportunities[:8], 1):
            # 信心等级图标
            confidence_icon = "🔥" if op.confidence_level == "高" else "⭐" if op.confidence_level == "中" else "💫"
            
            # 操作建议图标
            action_icon = "📈" if "买入" in op.overall_action else "📉" if "卖出" in op.overall_action else "⚪"
            
            print(f"\n【{confidence_icon} TOP {i}】 {op.symbol}")
            print("─" * 90)
            print(f"{action_icon} 综合建议: {op.overall_action:8s} | 信心: {op.confidence_level} | 评分: {op.total_score:+.2f}")
            print(f"💰 当前价格: {op.entry_price:.6f} USDT")
            
            print(f"\n🕐 多时间框架分析:")
            print(f"   📅 周线: {op.weekly_trend:8s} | 📊 日线: {op.daily_trend:8s}")
            print(f"   🕐 4H: {op.h4_signal:8s} | ⏰ 1H: {op.h1_signal:8s} | ⏱️  15M: {op.m15_signal:8s}")
            
            print(f"\n🎯 目标价格设定:")
            print(f"   🚀 短期(1-2天): {op.target_short:.6f} USDT ({((op.target_short/op.entry_price-1)*100):+.1f}%)")
            print(f"   🎯 中期(3-7天): {op.target_medium:.6f} USDT ({((op.target_medium/op.entry_price-1)*100):+.1f}%)")
            print(f"   🏆 长期(1-4周): {op.target_long:.6f} USDT ({((op.target_long/op.entry_price-1)*100):+.1f}%)")
            print(f"   🛡️  止损价格: {op.stop_loss:.6f} USDT ({((op.stop_loss/op.entry_price-1)*100):+.1f}%)")
            
            print("─" * 90)
        
        print(f"\n💡 投资建议:")
        print(f"   • 多时间框架确认的机会更可靠")
        print(f"   • 日内交易重点关注15M和1H信号")
        print(f"   • 长期投资以周线和日线趋势为准")
        print(f"   • 严格执行止损，控制风险")
        print("="*100)
    
    def save_trade_signals(self, opportunities: List[MultiTimeframeSignal]) -> Optional[str]:
        """记录交易信号（买入/卖出）到TXT文件，仅当有信号时才生成文件"""
        # 筛选符合条件的交易信号
        trade_signals = []
        
        for op in opportunities:
            # 检查是否是买入信号且评分达到阈值
            if op.total_score >= TRADING_CONFIG['BUY_THRESHOLD'] and op.overall_action == "买入":
                # 检查任一周期是否有卖出信号，如果有则过滤掉
                has_sell_signal = ("卖出" in op.weekly_trend or 
                                  "卖出" in op.daily_trend or 
                                  "卖出" in op.h4_signal or 
                                  "卖出" in op.h1_signal or 
                                  "卖出" in op.m15_signal)
                
                if has_sell_signal:
                    logger.info(f"{op.symbol} 买入信号因任一周期有卖出信号而被过滤掉")
                    continue
                
                # 应用时间框架过滤
                filter_by_15m = TRADING_CONFIG.get('FILTER_BY_15M', False)
                filter_by_1h = TRADING_CONFIG.get('FILTER_BY_1H', False)
                
                # 确定是否需要过滤
                should_filter = filter_by_15m or filter_by_1h
                
                # 如果不需要过滤，直接添加
                if not should_filter:
                    trade_signals.append(op)
                else:
                    # 检查时间框架条件
                    is_15m_buy = "买入" in op.m15_signal
                    is_1h_buy = "买入" in op.h1_signal
                    
                    # 根据过滤开关决定是否添加信号
                    # 逻辑：如果开启了对应过滤，则需要对应时间框架也为买入；如果关闭了过滤，则不考虑该时间框架
                    if ((not filter_by_15m or is_15m_buy) and 
                        (not filter_by_1h or is_1h_buy)):
                        # 添加止损价格过滤：如果止损价格距离当前价格不足0.3%，则过滤掉
                        price_diff_percent = abs(op.entry_price - op.stop_loss) / op.entry_price * 100
                        if price_diff_percent >= 0.3:
                            trade_signals.append(op)
                        else:
                            logger.info(f"{op.symbol} 买入信号因止损价格距离当前价格不足0.3%而被过滤掉: {price_diff_percent:.2f}%")
                        
            # 卖出信号应用时间框架过滤
            elif op.total_score <= TRADING_CONFIG['SELL_THRESHOLD'] and op.overall_action == "卖出":
                # 检查任一周期是否有买入信号，如果有则过滤掉
                has_buy_signal = ("买入" in op.weekly_trend or 
                                  "买入" in op.daily_trend or 
                                  "买入" in op.h4_signal or 
                                  "买入" in op.h1_signal or 
                                  "买入" in op.m15_signal)
                
                if has_buy_signal:
                    logger.info(f"{op.symbol} 卖出信号因任一周期有买入信号而被过滤掉")
                    continue
                
                # 应用时间框架过滤
                filter_by_15m = TRADING_CONFIG.get('FILTER_BY_15M', False)
                filter_by_1h = TRADING_CONFIG.get('FILTER_BY_1H', False)
                
                # 确定是否需要过滤
                should_filter = filter_by_15m or filter_by_1h
                
                # 如果不需要过滤，直接添加
                if not should_filter:
                    trade_signals.append(op)
                else:
                    # 检查时间框架条件（卖出信号）
                    is_15m_sell = "卖出" in op.m15_signal
                    is_1h_sell = "卖出" in op.h1_signal
                    
                    # 根据过滤开关决定是否添加信号
                    # 逻辑：如果开启了对应过滤，则需要对应时间框架也为卖出；如果关闭了过滤，则不考虑该时间框架
                    if ((not filter_by_15m or is_15m_sell) and 
                        (not filter_by_1h or is_1h_sell)):
                        # 添加止损价格过滤：如果止损价格距离当前价格不足0.3%，则过滤掉
                        price_diff_percent = abs(op.entry_price - op.stop_loss) / op.entry_price * 100
                        if price_diff_percent >= 0.3:
                            trade_signals.append(op)
                        else:
                            logger.info(f"{op.symbol} 卖出信号因止损价格距离当前价格不足0.3%而被过滤掉: {price_diff_percent:.2f}%")
        
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
                    
                    # 设置ac_type参数：买入对应o_l，卖出对应o_s
                    ac_type = 'o_l' if signal.overall_action == '买入' else 'o_s'
                    
                    # 构造请求参数
                    payload = {
                        'name': name,
                        'mechanism_id': TRADING_CONFIG['MECHANISM_ID'],
                        'stop_win_price': signal.target_short,
                        'stop_loss_price': signal.stop_loss,
                        'ac_type': ac_type,
                        'loss': TRADING_CONFIG['LOSS']
                    }
                    
                    # 发送POST请求（表单形式）
                    url = 'http://149.129.66.131:81/myOrder'
                    response = requests.post(url, data=payload, timeout=10)
                    
                    # 记录请求结果
                    if response.status_code == 200:
                        logger.info(f"成功发送交易信号到API: {signal.symbol} ({signal.overall_action})")
                    else:
                        logger.warning(f"发送交易信号到API失败 (状态码: {response.status_code}): {signal.symbol}")
                        logger.debug(f"API响应: {response.text}")
                    
                except Exception as e:
                    logger.error(f"发送交易信号到API时发生错误: {e}")
                    
            return filename
        
        # 没有交易信号时返回None
        return None
        
    def save_txt_report(self, opportunities: List[MultiTimeframeSignal], timestamp: str) -> str:
        """保存TXT报告"""
        filename = f"{self.output_dir}/multi_timeframe_analysis_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("🎯 多时间框架专业投资分析报告\n")
            f.write("=" * 100 + "\n")
            f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"分析维度: 周线→日线→4小时→1小时→15分钟\n")
            f.write(f"发现机会: {len(opportunities)} 个\n")
            f.write("=" * 100 + "\n\n")
            
            for i, op in enumerate(opportunities, 1):
                f.write(f"【机会 {i}】 {op.symbol}\n")
                f.write("-" * 80 + "\n")
                f.write(f"综合建议: {op.overall_action}\n")
                f.write(f"信心等级: {op.confidence_level}\n")
                f.write(f"总评分: {op.total_score:.3f}\n")
                f.write(f"当前价格: {op.entry_price:.6f} USDT\n\n")
                
                f.write("多时间框架分析:\n")
                f.write(f"  周线趋势: {op.weekly_trend}\n")
                f.write(f"  日线趋势: {op.daily_trend}\n")
                f.write(f"  4小时信号: {op.h4_signal}\n")
                f.write(f"  1小时信号: {op.h1_signal}\n")
                f.write(f"  15分钟信号: {op.m15_signal}\n\n")
                
                f.write("目标价格:\n")
                f.write(f"  短期目标: {op.target_short:.6f} USDT\n")
                f.write(f"  止损价格: {op.stop_loss:.6f} USDT\n\n")
                
                f.write(f"分析依据: {'; '.join(op.reasoning)}\n")
                f.write("\n" + "=" * 100 + "\n\n")
            
            f.write("⚠️ 投资建议:\n")
            f.write("• 多时间框架分析提供全面视角，建议结合基本面分析\n")
            f.write("• 长期投资关注周线和日线趋势\n")
            f.write("• 日内交易重点关注1小时和15分钟信号\n")
            f.write("• 严格执行止损，控制风险\n")
        
        return filename

def main():
    """主函数"""
    try:
        system = MultiTimeframeProfessionalSystem()
        system.run_analysis(max_symbols=50)
    except KeyboardInterrupt:
        print("\n❌ 用户中断分析")
    except Exception as e:
        print(f"❌ 系统错误: {e}")

if __name__ == "__main__":
    main()