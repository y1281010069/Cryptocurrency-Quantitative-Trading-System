#!/usr/bin/env python3
"""
策略基类模块
为多策略系统提供统一的接口和基础功能
"""

import abc
import json
import os
import redis
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from lib2 import get_okx_positions, send_trading_signal_to_api

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class BaseStrategy(abc.ABC):
    """策略基类，定义所有策略必须实现的接口"""
    
    def __init__(self, strategy_name: str, config: Dict[str, Any] = None):
        """
        初始化策略
        Args:
            strategy_name: 策略名称
            config: 策略配置参数
        """
        self.strategy_name = strategy_name
        self.config = config or {}
        self.exchange = None  # 交易所连接对象
        self.logger = logging.getLogger(__name__)
        
    @abc.abstractmethod
    def analyze(self, symbol: str, data: Dict[str, pd.DataFrame]) -> Any:
        """
        使用策略分析交易对
        Args:
            symbol: 交易对符号
            data: 多时间框架数据，格式为 {timeframe: dataframe}
        Returns:
            分析结果，可以是任何格式，取决于具体策略
        """
        pass
        
    @abc.abstractmethod
    def get_required_timeframes(self) -> Dict[str, int]:
        """
        获取策略所需的时间框架和数据长度
        Returns:
            字典，键为时间框架名称，值为所需数据长度
        """
        pass

    def get_name(self) -> str:
        """获取策略名称"""
        return self.strategy_name

    def set_config(self, config: Dict[str, Any]):
        """更新策略配置"""
        self.config.update(config)

    def get_config(self) -> Dict[str, Any]:
        """获取当前策略配置"""
        return self.config.copy()
    
    def _init_exchange(self):
        """初始化交易所连接"""
        try:
            import ccxt
            # 配置OKX交易所连接
            # 从子类获取OKX_CONFIG配置
            if hasattr(self, 'OKX_CONFIG'):
                # 配置OKX交易所连接
                self.exchange = ccxt.okx({'apiKey': self.OKX_CONFIG['api_key'], 'secret': self.OKX_CONFIG['secret'], 'password': self.OKX_CONFIG['passphrase'], 'timeout': self.OKX_CONFIG.get('timeout', 30000), 'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
            else:
                raise AttributeError("子类必须定义OKX_CONFIG属性")
            
        except Exception as e:
            self.logger.error(f"❌ 交易所连接失败: {e}")
            raise
    
    @abc.abstractmethod
    def save_trade_signals(self, opportunities: List[Any]) -> Optional[str]:
        """保存交易信号到文件，并发送到API
        参数:
            opportunities: 交易机会列表，支持不同类型的信号对象
        返回:
            生成的文件路径，如果没有信号则返回None
        """
        pass
        
    @abc.abstractmethod
    def analyze_positions(self, current_positions: List[Dict[str, Any]], opportunities: List[Any]) -> List[Dict[str, Any]]:
        """分析当前持仓并筛选出需要关注的持仓
        参数:
            current_positions: 当前持仓列表
            opportunities: 交易机会列表
        返回:
            需要关注的持仓列表
        """
        pass
        
    def save_trade_signals(self, opportunities: List[Any]) -> Optional[str]:
        """保存交易信号到文件，并发送到API
        参数:
            opportunities: 交易机会列表，支持不同类型的信号对象
        返回:
            生成的文件路径，如果没有信号则返回None
        """
        import os
        import json
        from datetime import datetime
        from typing import List, Optional, Any
        
        # 筛选符合条件的交易信号
        trade_signals = []
        
        for op in opportunities:
            # 检查信号对象是否具有基本必要属性
            if hasattr(op, 'symbol') and hasattr(op, 'overall_action') and hasattr(op, 'total_score'):
                trade_signals.append(op)
        
        # 只有当有交易信号时才生成文件
        if len(trade_signals) > 0:
            # 创建交易信号目录
            signal_dir = "trade_signals"
            os.makedirs(signal_dir, exist_ok=True)
            
            # 文件名格式：trade_signals_YYYYMMDD_HHMMSS.txt
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{signal_dir}/trade_signals_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n📊 交易信号记录\n" + "=" * 80 + f"\n记录时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n记录信号: {len(trade_signals)} 个\n策略名称: {self.get_name()}\n" + "=" * 80 + "\n\n")
                
                for i, signal in enumerate(trade_signals, 1):
                    f.write(f"【信号 {i}】 {signal.symbol}\n{'-' * 60}\n操作: {signal.overall_action}\n评分: {signal.total_score:.3f}\n")
                    
                    # 尝试获取额外信息，如果存在
                    if hasattr(signal, 'entry_price'):
                        f.write(f"当前价格: {signal.entry_price:.6f} USDT\n")
                    if hasattr(signal, 'target_short'):
                        f.write(f"短期目标: {signal.target_short:.6f} USDT\n")
                    if hasattr(signal, 'stop_loss'):
                        f.write(f"止损价格: {signal.stop_loss:.6f} USDT\n")
                    if hasattr(signal, 'timestamp'):
                        f.write(f"时间戳: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    if hasattr(signal, 'reasoning'):
                        f.write(f"分析依据: {'; '.join(signal.reasoning)}\n")
                    
                    f.write("\n" + "=" * 80 + "\n\n")
            
            self.logger.info(f"已生成交易信号文件: {filename}")
            return filename
        
        # 没有交易信号时返回None
        return None
        
    def _save_trade_signals(self, opportunities: List[Any]):
        """保存交易信号到文件和Redis
        参数:
            opportunities: 交易机会列表
        """
        try:
            if not opportunities:
                self.logger = logging.getLogger(__name__)
                self.logger.info(f"策略 '{self.get_name()}' 没有交易信号需要保存")
                return
            
            # 确保输出目录存在
            signals_dir = os.path.join("reports", "signals")
            os.makedirs(signals_dir, exist_ok=True)
            
            # 创建信号数据列表
            signals_data = []
            for opportunity in opportunities:
                signal_data = {'symbol': getattr(opportunity, 'symbol', '未知'), 'timestamp': datetime.now().isoformat(), 'strategy': self.get_name(), 'overall_action': getattr(opportunity, 'overall_action', '未知'), 'confidence_level': getattr(opportunity, 'confidence_level', '未知'), 'total_score': getattr(opportunity, 'total_score', 0), 'entry_price': getattr(opportunity, 'entry_price', 0), 'stop_loss': getattr(opportunity, 'stop_loss', 0), 'take_profit': getattr(opportunity, 'take_profit', 0), 'timeframe_scores': {}}
                
                # 添加各时间框架的信号和分数（如果有）
                if hasattr(opportunity, 'timeframe_signals'):
                    for tf, signal in opportunity.timeframe_signals.items():
                        signal_data['timeframe_scores'][tf] = {'signal': getattr(signal, 'signal', 0),'score': getattr(signal, 'score', 0),'action': getattr(signal, 'action', 'unknown')}
                
                signals_data.append(signal_data)
            
            # 保存到JSON文件
            filename = f"{self.get_name()}_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(signals_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(signals_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 策略 '{self.get_name()}' 的 {len(opportunities)} 个交易信号已保存至: {filepath}")
            
            
            # 发送信号到API
            for signal_data in signals_data:
                try:
                    # 注意：lib2.py中的函数期望的第一个参数是具有属性的对象，而不是字典
                    # 创建一个具有所需属性的简单对象，并确保包含所有必需的属性
                    class SignalObject:
                        def __init__(self, data):
                            # 将字典的键值对转换为对象属性
                            for key, value in data.items():
                                setattr(self, key, value)
                            
                            # 确保包含lib2.py中所需的所有属性，设置默认值避免AttributeError
                            required_attrs = ['symbol', 'overall_action', 'target_short', 'stop_loss']
                            for attr in required_attrs:
                                if not hasattr(self, attr):
                                    # 为缺失的属性设置默认值
                                    default_value = '' if attr in ['symbol', 'overall_action'] else 0.0
                                    setattr(self, attr, default_value)
                    
                    # 将字典转换为对象
                    signal_obj = SignalObject(signal_data)
                    send_trading_signal_to_api(signal_obj, logger)
                except Exception as api_error:
                    self.logger.warning(f"⚠️  发送交易信号到API失败: {api_error}")
                    
        except Exception as e:
            self.logger.error(f"❌ 保存交易信号时发生错误: {e}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")
        
    def save_positions_needing_attention(self, positions: List[Dict[str, Any]]) -> str:
        """保存需要关注的持仓信息
        参数:
            positions: 需要关注的持仓列表
        返回:
            生成的文件路径
        """
        import os
        from datetime import datetime
        
        # 创建需要关注的持仓目录
        attention_dir = "reports/positions_needing_attention"
        os.makedirs(attention_dir, exist_ok=True)
        
        # 文件名格式：positions_needing_attention_YYYYMMDD_HHMMSS.txt
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{attention_dir}/positions_needing_attention_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n⚠️  需要关注的持仓记录\n" + "=" * 80 + f"\n记录时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n记录持仓: {len(positions)} 个\n策略名称: {self.get_name()}\n" + "=" * 80 + "\n\n")
            
            for i, pos in enumerate(positions, 1):
                f.write(f"【持仓 {i}】 {pos.get('symbol', '未知')}\n{'-' * 60}\n持仓方向: {pos.get('posSide', '未知')}\n持仓数量: {pos.get('amount', '0')}\n持仓均价: {pos.get('entry_price', '0.0')}\n当前价格: {pos.get('current_price', '0.0')}\n开仓时间: {pos.get('datetime', '未知')}\n关注原因: {pos.get('reason', '未知')}\n\n{'=' * 80}\n\n")
        
        self.logger.info(f"已生成需要关注的持仓记录: {filename}")
        return filename
        
    def filter_by_positions(self, trade_signals: List[Any]) -> List[Any]:
        """根据已持仓情况过滤交易信号
        参数:
            trade_signals: 交易信号列表
        返回:
            过滤后的交易信号列表
        """

        # 增加日志记录，确认方法被调用
        self.logger.info(f"🔍 filter_by_positions方法被调用，接收到的信号数量: {len(trade_signals)}")
        
        # 检查self.exchange是否存在
        if not hasattr(self, 'exchange') or self.exchange is None:
            self.logger.error("❌ self.exchange不存在或为None，无法获取仓位数据")
            return trade_signals
        
        # 检查self.config是否存在
        if not hasattr(self, 'config') or self.config is None:
            self.logger.error("❌ self.config不存在或为None，无法获取配置")
            # 设置默认配置
            self.config = {'MAX_POSITIONS': 10}
        
        # 如果有交易信号，检查已持有的标的并过滤
        if len(trade_signals) > 0:
            try:
                # 使用OKX接口获取当前仓位
                self.logger.info("=== 开始获取OKX当前仓位数据 ===")
                
                # 记录获取仓位前的配置信息
                max_positions = self.config.get('MAX_POSITIONS', 10)
                self.logger.info(f"当前配置: MAX_POSITIONS={max_positions}")
                
                # 调用lib中的函数获取仓位数据
                self.logger.info(f"调用get_okx_positions，传入的exchange对象: {type(self.exchange).__name__}")
                formatted_positions = get_okx_positions(self.exchange)
                self.logger.info(f"获取到的持仓数据数量: {len(formatted_positions)}")
                if formatted_positions:
                    self.logger.info(f"当前持仓数据示例: {formatted_positions[:2]}")  # 只显示前2个持仓，避免日志过长
                
                # 提取已持有的标的并标准化格式
                held_symbols_converted = []
                for position in formatted_positions:
                    symbol = position.get('symbol', '')
                    if symbol:
                        # 标准化持仓标的格式
                        # 1. 移除永续合约后缀（如'-SWAP'）
                        # 2. 统一转换为大写
                        standard_symbol = symbol.replace('-SWAP', '').upper()
                        held_symbols_converted.append(standard_symbol)
                
                # 检查持仓数量是否超过最大限制
                max_positions = self.config.get('MAX_POSITIONS', 10)
                current_position_count = len(held_symbols_converted)
                
                # 记录持仓信息
                self.logger.info(f"当前持仓数量: {current_position_count}, 持仓标的: {held_symbols_converted}")
                
                if current_position_count >= max_positions:
                    # 如果已持仓数量超过最大限制，放弃所有交易信号
                    self.logger.info(f"当前持仓数量({current_position_count})已达到或超过最大限制({max_positions})，放弃所有交易信号")
                    trade_signals = []
                else:
                    # 过滤掉已持有的标的
                    original_count = len(trade_signals)
                    filtered_signals = []
                    
                    # 遍历所有交易信号，应用标准化匹配
                    for signal in trade_signals:
                        try:
                            # 获取交易信号中的标的名称
                            signal_symbol = getattr(signal, 'symbol', '')
                            if not signal_symbol:
                                continue
                                
                            # 标准化交易信号中的标的格式
                            standard_signal_symbol = signal_symbol.replace('-SWAP', '').upper()
                            
                            # 检查是否匹配已持仓
                            if standard_signal_symbol not in held_symbols_converted:
                                filtered_signals.append(signal)
                            else:
                                self.logger.info(f"过滤掉已持仓标的: {signal_symbol} (标准化: {standard_signal_symbol})")
                        except Exception as e:
                            self.logger.error(f"处理交易信号时出错: {e}")
                            # 出错时保留该信号，避免误过滤
                            filtered_signals.append(signal)
                    
                    # 记录过滤信息
                    filtered_count = original_count - len(filtered_signals)
                    if filtered_count > 0:
                        self.logger.info(f"已从交易信号中过滤掉 {filtered_count} 个已持有的标的")
                    
                    trade_signals = filtered_signals
            except Exception as e:
                    self.logger.error(f"❌ 获取OKX仓位数据时发生错误: {e}")
                    import traceback
                    self.logger.error(f"错误详情: {traceback.format_exc()}")
                    # 即使获取仓位数据出错，也继续处理交易信号，不中断主流程
        else:
            self.logger.info("📭 没有接收到交易信号，跳过仓位过滤")
        
        self.logger.info(f"✅ filter_by_positions方法执行完成，返回的信号数量: {len(trade_signals)}")
        return trade_signals

    def filter_trade_signals(self, opportunities: List[Any]) -> List[Any]:
        """过滤交易信号，根据配置的阈值和规则筛选符合条件的信号
        参数:
            opportunities: 交易机会列表，支持不同类型的信号对象
        返回:
            过滤后的交易信号列表
        """

        trade_signals = []
        
        for op in opportunities:
            # 检查信号对象是否具有基本必要属性
            if not (hasattr(op, 'symbol') and hasattr(op, 'overall_action')):
                continue
            
            # 检查是否是买入信号
            if hasattr(op, 'total_score') and op.total_score >= self.config.get('BUY_THRESHOLD') and op.overall_action == "买入":
                # 如果是MultiTimeframeSignal类型，应用特定的过滤规则
                if 'MultiTimeframeSignal' in str(type(op)):
                    # 检查任一周期是否有卖出信号
                    has_sell_signal = False
                    # 优先使用timeframe_signals字典检查所有配置的时间框架
                    if hasattr(op, 'timeframe_signals') and isinstance(op.timeframe_signals, dict):
                        has_sell_signal = any("卖出" in signal for signal in op.timeframe_signals.values())
                    
                    if has_sell_signal:
                        self.logger.info(f"{op.symbol} 买入信号因任一周期有卖出信号而被过滤掉")
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
                                self.logger.info(f"{op.symbol} 买入信号因止损价格距离当前价格不足0.3%而被过滤掉: {price_diff_percent:.2f}%")
                            else:
                                self.logger.info(f"{op.symbol} 买入信号因止损价格距离当前价格超过10%而被过滤掉: {price_diff_percent:.2f}%")
                        else:
                            trade_signals.append(op)
                else:
                    # 对于非MultiTimeframeSignal类型，应用通用过滤规则
                    trade_signals.append(op)
                          
            # 检查是否是卖出信号
            elif hasattr(op, 'total_score') and op.total_score <= self.config.get('SELL_THRESHOLD') and op.overall_action == "卖出":
                # 如果是MultiTimeframeSignal类型，应用特定的过滤规则
                if 'MultiTimeframeSignal' in str(type(op)):
                    # 检查任一周期是否有买入信号
                    has_buy_signal = False
                    # 优先使用timeframe_signals字典检查所有配置的时间框架
                    if hasattr(op, 'timeframe_signals') and isinstance(op.timeframe_signals, dict):
                        has_buy_signal = any("买入" in signal for signal in op.timeframe_signals.values())
                  
                    if has_buy_signal:
                        self.logger.info(f"{op.symbol} 卖出信号因任一周期有买入信号而被过滤掉")
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
                                self.logger.info(f"{op.symbol} 卖出信号因止损价格距离当前价格不足0.3%而被过滤掉: {price_diff_percent:.2f}%")
                            else:
                                self.logger.info(f"{op.symbol} 卖出信号因止损价格距离当前价格超过10%而被过滤掉: {price_diff_percent:.2f}%")
                        else:
                            trade_signals.append(op)
                else:
                    # 对于非MultiTimeframeSignal类型，应用通用过滤规则
                    trade_signals.append(op)
        
        return trade_signals

    def save_multi_timeframe_analysis(self, opportunities: List[Any]) -> Optional[str]:
        """生成多时间框架分析报告，格式符合report_viewer_python的解析要求
        参数:
            opportunities: 交易机会列表，支持不同类型的信号对象
        返回:
            生成的文件路径，如果没有信号则返回None
        """
        import os
        import logging
        from datetime import datetime
        from typing import List, Optional, Any
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        
        # 保留所有交易机会，不进行过滤
        all_opportunities = opportunities
        
        # 如果没有交易机会，不生成报告
        if not all_opportunities:
            self.logger.info("没有交易机会，不生成多时间框架分析报告")
            return None
        
        # 按照分数的绝对值倒序排序
        try:
            all_opportunities.sort(key=lambda x: abs(getattr(x, 'total_score', 0)), reverse=True)
        except Exception as e:
            self.logger.error(f"排序交易机会时发生错误: {e}")
        
        # 设置报告目录路径
        report_dir = "reports"
        os.makedirs(report_dir, exist_ok=True)
        
        # 文件名固定为multi_timeframe_analysis_new.txt
        filename = os.path.join(report_dir, "multi_timeframe_analysis_new.txt")
        
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入报告头部
            f.write("=" * 80 + "\n📊 多时间框架专业分析报告\n" + "=" * 80 + f"\n分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n时间框架维度: 周线→日线→4小时→1小时→15分钟\n发现机会: {len(all_opportunities)}\n策略名称: {self.get_name()}\n" + "=" * 80 + "\n\n")
            
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
                
                f.write(f"【机会 {i}】\n" + "-" * 60 + "\n" + f"交易对: {symbol}\n" + f"综合建议: {overall_action}\n" + f"信心等级: {confidence_level}\n" + f"总评分: {total_score:.3f}\n" + f"当前价格: {entry_price:.6f}\n" + f"周线趋势: {weekly_trend}\n" + f"日线趋势: {daily_trend}\n" + f"4小时信号: {h4_signal}\n" + f"1小时信号: {h1_signal}\n" + f"15分钟信号: {m15_signal}\n" + f"短期目标: {target_short:.6f}\n" + f"止损价格: {stop_loss:.6f}\n" + f"分析依据: {reasoning_text}\n" + "\n" + "=" * 80 + "\n\n")
        
        self.logger.info(f"✅ 多时间框架分析报告已保存至: {filename}")
        return filename