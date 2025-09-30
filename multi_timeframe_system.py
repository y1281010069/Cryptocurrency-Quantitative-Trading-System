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
from lib import calculate_atr

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
        'DISABLED_SYMBOLS': ['USDC/USDT']
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
        """初始化系统"""
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
        """设置交易所连接"""
        try:
            self.exchange = ccxt.okx({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'password': self.passphrase,
                'sandbox': False,
                'enableRateLimit': True,
                'timeout': 30000,
            })
            self.exchange.load_markets()
            logger.info("交易所连接成功")
        except Exception as e:
            logger.error(f"交易所连接失败: {e}")
            raise
    
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
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # 计算ATR (平均真实波动幅度)
        atr_value = calculate_atr(df.copy())
        
        # 成交量
        volume_avg = df['volume'].rolling(20).mean().iloc[-1]
        volume_current = df['volume'].iloc[-1]
        volume_ratio = volume_current / volume_avg if volume_avg > 0 else 1
        
        # 计算ATR值
        atr_value = calculate_atr(df.copy())
        
        # 评分系统
        score = 0
        
        # 趋势评分
        if current_price > sma_20 > sma_50:
            score += 2
        elif current_price > sma_20:
            score += 1
        elif current_price < sma_20 < sma_50:
            score -= 2
        elif current_price < sma_20:
            score -= 1
        
        # RSI评分
        if 30 < rsi < 70:
            score += 1
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
            
            # 根据交易方向计算ATR相关价格（做多/做空）
            if overall_action == "买入":
                # 买入方向：
                # - 1.5倍ATR作为短期目标（当前价格 + 1.5*ATR）
                # - 1倍ATR作为止损价格（当前价格 - ATR）
                atr_one = current_price + atr_value
                target_short = current_price + 1.5 * atr_value
                stop_loss = current_price - atr_value
            else:
                # 卖出方向：
                # - 1.5倍ATR作为短期目标（当前价格 - 1.5*ATR）
                # - 1倍ATR作为止损价格（当前价格 + ATR）
                atr_one = current_price - atr_value
                target_short = current_price - 1.5 * atr_value
                stop_loss = current_price + atr_value
            
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
        trade_signals = [
            op for op in opportunities 
            if (op.total_score >= TRADING_CONFIG['BUY_THRESHOLD'] and op.overall_action == "买入") or 
               (op.total_score <= TRADING_CONFIG['SELL_THRESHOLD'] and op.overall_action == "卖出")
        ]
        
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
                    # 格式化name参数：从KAITO/USDT转换为KAITO-USDT
                    name = signal.symbol.replace('/', '-')
                    
                    # 设置ac_type参数：买入对应o_l，卖出对应o_s
                    ac_type = 'o_l' if signal.overall_action == '买入' else 'o_s'
                    
                    # 构造请求参数
                    payload = {
                        'name': name,
                        'mechanism_id': 13,
                        'stop_win_price': signal.target_short,
                        'stop_loss_price': signal.stop_loss,
                        'ac_type': ac_type,
                        'loss': 1
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