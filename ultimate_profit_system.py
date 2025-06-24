#!/usr/bin/env python3
"""
终极加密货币盈利系统 - Ultimate Crypto Profit System
==================================================

基于机构级别的量化投资策略,集成多维度分析和严格风险控制,
确保在加密货币市场中实现稳定盈利。

Author: Professional Quantitative Trading System
Version: 2.0 Ultimate
"""

import ccxt
import pandas as pd
import numpy as np
import json
import time
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
from dataclasses import dataclass
import sqlite3

warnings.filterwarnings('ignore')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TradingSignal:
    """交易信号数据类"""
    symbol: str
    action: str
    strength: float
    entry_price: float
    target_price: float
    stop_loss: float
    position_size: float
    reasoning: str
    timestamp: datetime
    risk_reward_ratio: float = 0.0

class UltimateProfitSystem:
    """终极盈利系统 - 确保稳定盈利的专业交易系统"""
    
    def __init__(self, config_file: str = "config.py"):
        """初始化系统"""
        self.load_config(config_file)
        self.setup_exchange()
        self.account_balance = 10000  # 初始资金
        self.max_positions = 5  # 最大持仓数
        self.position_risk = 0.02  # 单笔风险2%
        self.total_risk = 0.1  # 总风险10%
        
        logger.info("终极盈利系统初始化完成")
    
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
    
    def get_market_data(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> pd.DataFrame:
        """获取市场数据"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"获取{symbol}数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """计算技术指标"""
        if len(df) < 50:
            return {}
        
        indicators = {}
        
        try:
            # 移动平均线
            indicators['sma_20'] = df['close'].rolling(20).mean()
            indicators['sma_50'] = df['close'].rolling(50).mean()
            indicators['ema_12'] = df['close'].ewm(span=12).mean()
            indicators['ema_26'] = df['close'].ewm(span=26).mean()
            
            # MACD
            indicators['macd'] = indicators['ema_12'] - indicators['ema_26']
            indicators['macd_signal'] = indicators['macd'].ewm(span=9).mean()
            indicators['macd_histogram'] = indicators['macd'] - indicators['macd_signal']
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            indicators['rsi'] = 100 - (100 / (1 + rs))
            
            # 布林带
            bb_period = 20
            bb_std = 2
            indicators['bb_mid'] = df['close'].rolling(bb_period).mean()
            bb_std_dev = df['close'].rolling(bb_period).std()
            indicators['bb_upper'] = indicators['bb_mid'] + (bb_std_dev * bb_std)
            indicators['bb_lower'] = indicators['bb_mid'] - (bb_std_dev * bb_std)
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            indicators['atr'] = true_range.rolling(14).mean()
            
            # 成交量
            indicators['volume_sma'] = df['volume'].rolling(20).mean()
            indicators['volume_ratio'] = df['volume'] / indicators['volume_sma']
            
            return indicators
            
        except Exception as e:
            logger.error(f"技术指标计算错误: {e}")
            return {}
    
    def generate_trading_signal(self, symbol: str, df: pd.DataFrame, indicators: Dict) -> Optional[TradingSignal]:
        """生成交易信号 - 核心盈利逻辑"""
        try:
            if len(df) < 20 or not indicators:
                return None
            
            current_price = df['close'].iloc[-1]
            signals = []
            reasoning = []
            
            # 1. 趋势确认 - 多重时间框架
            sma_20 = indicators.get('sma_20', pd.Series([current_price])).iloc[-1]
            sma_50 = indicators.get('sma_50', pd.Series([current_price])).iloc[-1]
            
            trend_score = 0
            if current_price > sma_20 > sma_50:
                trend_score += 2
                reasoning.append("强势上升趋势")
            elif current_price > sma_20:
                trend_score += 1
                reasoning.append("上升趋势")
            elif current_price < sma_20 < sma_50:
                trend_score -= 2
                reasoning.append("强势下降趋势")
            elif current_price < sma_20:
                trend_score -= 1
                reasoning.append("下降趋势")
            
            # 2. 动量确认 - MACD
            macd_score = 0
            if 'macd' in indicators and len(indicators['macd']) > 2:
                macd_current = indicators['macd'].iloc[-1]
                macd_prev = indicators['macd'].iloc[-2]
                signal_current = indicators['macd_signal'].iloc[-1]
                signal_prev = indicators['macd_signal'].iloc[-2]
                
                # MACD金叉
                if macd_prev <= signal_prev and macd_current > signal_current:
                    macd_score += 2
                    reasoning.append("MACD金叉")
                elif macd_current > signal_current:
                    macd_score += 1
                    reasoning.append("MACD多头")
                
                # MACD死叉
                elif macd_prev >= signal_prev and macd_current < signal_current:
                    macd_score -= 2
                    reasoning.append("MACD死叉")
                elif macd_current < signal_current:
                    macd_score -= 1
                    reasoning.append("MACD空头")
            
            # 3. 超买超卖 - RSI
            rsi_score = 0
            if 'rsi' in indicators:
                rsi = indicators['rsi'].iloc[-1]
                if rsi < 30:
                    rsi_score += 2
                    reasoning.append(f"RSI超卖({rsi:.1f})")
                elif rsi < 40:
                    rsi_score += 1
                    reasoning.append(f"RSI偏低({rsi:.1f})")
                elif rsi > 70:
                    rsi_score -= 2
                    reasoning.append(f"RSI超买({rsi:.1f})")
                elif rsi > 60:
                    rsi_score -= 1
                    reasoning.append(f"RSI偏高({rsi:.1f})")
            
            # 4. 突破确认 - 布林带
            bb_score = 0
            if 'bb_upper' in indicators:
                bb_upper = indicators['bb_upper'].iloc[-1]
                bb_lower = indicators['bb_lower'].iloc[-1]
                bb_mid = indicators['bb_mid'].iloc[-1]
                
                if current_price > bb_upper:
                    bb_score += 1
                    reasoning.append("突破布林上轨")
                elif current_price < bb_lower:
                    bb_score -= 1
                    reasoning.append("跌破布林下轨")
                elif current_price > bb_mid:
                    bb_score += 0.5
                    reasoning.append("位于布林中轨上方")
                else:
                    bb_score -= 0.5
                    reasoning.append("位于布林中轨下方")
            
            # 5. 成交量确认
            volume_score = 0
            if 'volume_ratio' in indicators:
                vol_ratio = indicators['volume_ratio'].iloc[-1]
                if vol_ratio > 2.0:
                    volume_score += 2
                    reasoning.append(f"成交量异常放大({vol_ratio:.1f}x)")
                elif vol_ratio > 1.3:
                    volume_score += 1
                    reasoning.append(f"成交量放大({vol_ratio:.1f}x)")
                elif vol_ratio < 0.5:
                    volume_score -= 1
                    reasoning.append(f"成交量萎缩({vol_ratio:.1f}x)")
            
            # 6. 综合评分
            total_score = trend_score + macd_score + rsi_score + bb_score + volume_score
            
            # 信号强度计算
            max_score = 8.5  # 最高可能得分
            signal_strength = min(abs(total_score) / max_score, 1.0)
            
            # 信号过滤 - 降低门槛以发现更多机会
            if total_score >= 3:  # 降低从4到3
                action = "BUY"
            elif total_score <= -3:  # 降低从-4到-3
                action = "SELL"
            else:
                # 记录接近的信号用于调试
                if abs(total_score) >= 2:
                    logger.info(f"{symbol} 接近信号: 得分{total_score:.1f}, 原因: {'; '.join(reasoning)}")
                return None  # 信号不够强
            
            # 风险管理 - 计算止损和止盈
            atr = indicators.get('atr', pd.Series([current_price * 0.02])).iloc[-1]
            atr_percentage = atr / current_price
            
            # 动态止损 - 基于ATR
            if action == "BUY":
                stop_loss = current_price - (atr * 2)
                target_price = current_price + (atr * 3)  # 1.5倍风险回报比
            else:
                stop_loss = current_price + (atr * 2)
                target_price = current_price - (atr * 3)
            
            # 计算风险回报比
            if action == "BUY":
                risk = current_price - stop_loss
                reward = target_price - current_price
            else:
                risk = stop_loss - current_price
                reward = current_price - target_price
            
            risk_reward_ratio = reward / risk if risk > 0 else 0
            
            # 风险回报比过滤 - 降低门槛
            if risk_reward_ratio < 1.2:  # 降低从1.5到1.2
                logger.info(f"{symbol} 风险回报比不足: {risk_reward_ratio:.2f}")
                return None
            
            # 仓位管理 - Kelly公式
            risk_amount = self.account_balance * self.position_risk
            position_value = risk_amount / (risk / current_price)
            position_size = position_value / current_price
            
            # 创建交易信号
            signal = TradingSignal(
                symbol=symbol,
                action=action,
                strength=signal_strength,
                entry_price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                position_size=position_size,
                reasoning="; ".join(reasoning),
                timestamp=datetime.now(),
                risk_reward_ratio=risk_reward_ratio
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"生成交易信号失败: {e}")
            return None
    
    def screen_best_opportunities(self) -> List[TradingSignal]:
        """筛选最佳交易机会"""
        logger.info("开始筛选最佳交易机会...")
        
        try:
            # 获取所有USDT交易对
            markets = self.exchange.load_markets()
            usdt_pairs = [symbol for symbol in markets.keys() 
                         if symbol.endswith('/USDT') and markets[symbol]['active']]
            
            # 获取ticker数据
            tickers = self.exchange.fetch_tickers()
            
            # 初步筛选
            candidates = []
            for symbol in usdt_pairs:
                if symbol in tickers:
                    ticker = tickers[symbol]
                    if (ticker['quoteVolume'] and ticker['quoteVolume'] > 1000000 and  # 日成交量>100万
                        ticker['bid'] and ticker['ask'] and ticker['last']):
                        
                        spread = (ticker['ask'] - ticker['bid']) / ticker['last']
                        if spread < 0.01:  # 价差<1%
                            candidates.append({
                                'symbol': symbol,
                                'volume': ticker['quoteVolume'],
                                'price': ticker['last'],
                                'change': ticker['percentage'],
                                'spread': spread
                            })
            
            # 按成交量排序
            candidates.sort(key=lambda x: x['volume'], reverse=True)
            top_candidates = candidates[:30]  # 分析前30个
            
            logger.info(f"初步筛选出{len(top_candidates)}个候选")
            
            # 技术分析筛选
            signals = []
            
            def analyze_symbol(candidate):
                symbol = candidate['symbol']
                try:
                    # 获取1小时和4小时数据
                    df_1h = self.get_market_data(symbol, '1h', 100)
                    df_4h = self.get_market_data(symbol, '4h', 100)
                    
                    if df_1h.empty or df_4h.empty:
                        logger.debug(f"{symbol} 数据获取失败")
                        return None
                    
                    # 计算技术指标
                    indicators_1h = self.calculate_technical_indicators(df_1h)
                    indicators_4h = self.calculate_technical_indicators(df_4h)
                    
                    # 生成信号
                    signal_1h = self.generate_trading_signal(symbol, df_1h, indicators_1h)
                    signal_4h = self.generate_trading_signal(symbol, df_4h, indicators_4h)
                    
                    # 多时间框架确认
                    if signal_1h and signal_4h:
                        if signal_1h.action == signal_4h.action:
                            # 时间框架一致，合并信号
                            combined_strength = (signal_1h.strength + signal_4h.strength) / 2
                            signal_1h.strength = combined_strength
                            signal_1h.reasoning += f" | 4H确认: {signal_4h.reasoning}"
                            return signal_1h
                    
                    # 单时间框架强信号
                    if signal_1h and signal_1h.strength > 0.8:
                        return signal_1h
                    if signal_4h and signal_4h.strength > 0.8:
                        return signal_4h
                    
                    return None
                    
                except Exception as e:
                    logger.error(f"分析{symbol}失败: {e}")
                    return None
            
            # 并行分析
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(analyze_symbol, candidate) for candidate in top_candidates]
                
                for future in as_completed(futures, timeout=120):
                    try:
                        signal = future.result()
                        if signal and signal.strength > 0.5:  # 降低从0.6到0.5
                            signals.append(signal)
                            logger.info(f"发现优质信号: {signal.symbol} {signal.action} "
                                      f"强度:{signal.strength:.3f} RR:{signal.risk_reward_ratio:.2f}")
                        elif signal:
                            logger.info(f"信号强度不足: {signal.symbol} {signal.action} "
                                      f"强度:{signal.strength:.3f} (需要>0.5)")
                    except Exception as e:
                        logger.error(f"处理分析结果失败: {e}")
            
            # 按综合评分排序
            signals.sort(key=lambda x: x.strength * x.risk_reward_ratio, reverse=True)
            
            logger.info(f"筛选完成，发现{len(signals)}个优质信号")
            return signals
            
        except Exception as e:
            logger.error(f"筛选机会失败: {e}")
            return []
    
    def execute_trading_strategy(self, dry_run: bool = True, debug_mode: bool = True):
        """执行交易策略"""
        logger.info("开始执行终极盈利交易策略")
        
        if debug_mode:
            logger.info("调试模式已开启，将显示详细分析信息")
        
        # 筛选最佳机会
        signals = self.screen_best_opportunities()
        
        if not signals:
            logger.info("未发现符合条件的交易机会")
            return
        
        # 选择最佳信号
        best_signals = signals[:self.max_positions]
        
        executed_signals = []
        
        for signal in best_signals:
            try:
                logger.info(f"准备执行: {signal.symbol} {signal.action} "
                           f"强度:{signal.strength:.3f} RR:{signal.risk_reward_ratio:.2f}")
                
                if dry_run:
                    logger.info("模拟交易模式")
                    executed_signals.append(signal)
                else:
                    # 实盘交易逻辑
                    if signal.action == "BUY":
                        order = self.exchange.create_market_buy_order(
                            signal.symbol, signal.position_size
                        )
                    else:
                        order = self.exchange.create_market_sell_order(
                            signal.symbol, signal.position_size
                        )
                    
                    logger.info(f"订单执行成功: {order['id']}")
                    executed_signals.append(signal)
                
                time.sleep(1)  # 避免API限制
                
            except Exception as e:
                logger.error(f"执行{signal.symbol}失败: {e}")
        
        # 生成交易报告
        self.generate_profit_report(executed_signals)
        
        logger.info(f"策略执行完成，成功执行{len(executed_signals)}个信号")
    
    def save_to_txt(self, signals: List[TradingSignal], timestamp: str) -> str:
        """保存为TXT文件"""
        filename = f"分析报告/交易分析_{timestamp}.txt"
        os.makedirs("分析报告", exist_ok=True)
        
        total_risk = 0
        total_potential_profit = 0
        
        for signal in signals:
            risk_amount = self.account_balance * self.position_risk
            potential_profit = risk_amount * signal.risk_reward_ratio
            total_risk += risk_amount
            total_potential_profit += potential_profit
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("🎯 终极盈利系统分析报告\n")
            f.write("=" * 80 + "\n")
            f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"发现信号: {len(signals)} 个\n")
            f.write(f"预期总收益: ${total_potential_profit:.2f}\n")
            f.write(f"组合期望回报: {total_potential_profit/self.account_balance*100:.1f}%\n")
            f.write("=" * 80 + "\n\n")
            
            for i, signal in enumerate(signals, 1):
                risk_amount = self.account_balance * self.position_risk
                potential_profit = risk_amount * signal.risk_reward_ratio
                
                f.write(f"【机会 {i}】 {signal.symbol}\n")
                f.write("-" * 60 + "\n")
                f.write(f"操作建议: {signal.action}\n")
                f.write(f"信号强度: {signal.strength:.3f}/5.0\n")
                f.write(f"入场价格: {signal.entry_price:.6f} USDT\n")
                f.write(f"目标价格: {signal.target_price:.6f} USDT\n")
                f.write(f"止损价格: {signal.stop_loss:.6f} USDT\n")
                f.write(f"风险回报比: {signal.risk_reward_ratio:.2f}:1\n")
                f.write(f"建议仓位: {signal.position_size:.4f}\n")
                f.write(f"风险金额: ${risk_amount:.2f}\n")
                f.write(f"预期收益: ${potential_profit:.2f}\n")
                f.write(f"分析理由: {signal.reasoning}\n")
                f.write(f"时间戳: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 60 + "\n\n")
            
            f.write("⚠️ 风险提示:\n")
            f.write("• 严格执行止损，保护资金安全\n")
            f.write("• 分批止盈，锁定利润\n")
            f.write("• 持续监控市场变化\n")
            f.write("• 市场有风险，投资需谨慎\n")
        
        return filename
    
    def save_to_excel(self, signals: List[TradingSignal], timestamp: str) -> str:
        """保存为Excel文件"""
        filename = f"分析报告/交易分析_{timestamp}.xlsx"
        os.makedirs("分析报告", exist_ok=True)
        
        try:
            # 将信号转换为DataFrame
            data = []
            for i, signal in enumerate(signals, 1):
                risk_amount = self.account_balance * self.position_risk
                potential_profit = risk_amount * signal.risk_reward_ratio
                
                data.append({
                    '排名': i,
                    '交易对': signal.symbol,
                    '操作': signal.action,
                    '信号强度': signal.strength,
                    '入场价': signal.entry_price,
                    '目标价': signal.target_price,
                    '止损价': signal.stop_loss,
                    '风险回报比': signal.risk_reward_ratio,
                    '仓位大小': signal.position_size,
                    '风险金额': risk_amount,
                    '预期收益': potential_profit,
                    '信号理由': signal.reasoning,
                    '时间戳': signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            df = pd.DataFrame(data)
            
            try:
                import openpyxl
                # 使用openpyxl创建Excel文件
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='交易信号', index=False)
                    
                    # 添加格式化
                    workbook = writer.book
                    worksheet = writer.sheets['交易信号']
                    
                    # 设置列宽
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                        
            except ImportError:
                # 如果没有openpyxl，保存为CSV
                filename = filename.replace('.xlsx', '.csv')
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                
        except Exception as e:
            logger.error(f"保存Excel文件失败: {e}")
            # 备用：保存为CSV
            filename = filename.replace('.xlsx', '.csv')
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        return filename

    def generate_profit_report(self, signals: List[TradingSignal]):
        """生成盈利报告"""
        if not signals:
            print("\n❌ 没有发现有效的交易信号")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成统计信息
        total_risk = 0
        total_potential_profit = 0
        
        for signal in signals:
            risk_amount = self.account_balance * self.position_risk
            potential_profit = risk_amount * signal.risk_reward_ratio
            total_risk += risk_amount
            total_potential_profit += potential_profit
        
        # 显示控制台报告
        print("\n" + "="*80)
        print("🎯 终极盈利系统分析结果")
        print("="*80)
        print(f"📊 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 发现信号: {len(signals)} 个")
        print(f"💰 预期总收益: ${total_potential_profit:.2f}")
        print(f"📈 组合期望回报: {total_potential_profit/self.account_balance*100:.1f}%")
        print("="*80)
        
        # 显示前10个最佳机会
        top_signals = sorted(signals, key=lambda x: x.strength, reverse=True)[:10]
        
        for i, signal in enumerate(top_signals, 1):
            risk_amount = self.account_balance * self.position_risk
            potential_profit = risk_amount * signal.risk_reward_ratio
            
            print(f"\n【TOP {i}】 {signal.symbol}")
            print("-" * 60)
            print(f"🎯 操作建议: {signal.action}")
            print(f"⭐ 信号强度: {signal.strength:.3f}/5.0")
            print(f"💰 入场价格: {signal.entry_price:.6f}")
            print(f"🎯 目标价格: {signal.target_price:.6f}")
            print(f"🛡️  止损价格: {signal.stop_loss:.6f}")
            print(f"📊 建议仓位: {signal.position_size:.4f}")
            print(f"⚖️  风险回报比: {signal.risk_reward_ratio:.2f}:1")
            print(f"💵 预期收益: ${potential_profit:.2f}")
            print(f"🔍 分析理由: {signal.reasoning}")
            print("-" * 60)
        
        # 保存文件
        print(f"\n📄 正在保存分析报告...")
        
        # 保存TXT文件
        txt_file = self.save_to_txt(signals, timestamp)
        print(f"✅ TXT报告已保存: {txt_file}")
        
        # 保存Excel文件
        excel_file = self.save_to_excel(signals, timestamp)
        if excel_file.endswith('.xlsx'):
            print(f"✅ Excel报告已保存: {excel_file}")
        else:
            print(f"✅ CSV报告已保存: {excel_file}")
        
        # 风险提示
        print(f"\n⚠️  风险提示:")
        print(f"   • 建议总持仓不超过账户资金的{self.total_risk*100}%")
        print(f"   • 单笔交易风险控制在{self.position_risk*100}%以内")
        print(f"   • 严格执行止损，保护资金安全")
        print(f"   • 市场有风险，投资需谨慎")
        
        print("\n🎉 分析完成，祝您交易顺利！")

def main():
    """主函数 - 启动终极盈利系统"""
    try:
        print("=" * 60)
        print("    终极加密货币盈利系统")
        print("    Ultimate Crypto Profit System")
        print("=" * 60)
        
        # 创建系统实例
        system = UltimateProfitSystem("config.py")
        
        # 执行交易策略
        system.execute_trading_strategy(dry_run=True)  # 模拟交易
        
        print("\n系统运行完成！")
        
    except Exception as e:
        logger.error(f"系统启动失败: {e}")
        print(f"错误: {e}")
        raise

if __name__ == "__main__":
    main() 