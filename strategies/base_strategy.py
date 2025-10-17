#!/usr/bin/env python3
"""
策略基类模块
为多策略系统提供统一的接口和基础功能
"""

import abc
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging


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
                self.exchange = ccxt.okx({
                    'apiKey': self.OKX_CONFIG['api_key'],
                    'secret': self.OKX_CONFIG['secret'],
                    'password': self.OKX_CONFIG['passphrase'],
                    'timeout': self.OKX_CONFIG.get('timeout', 30000),
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot'  # 默认使用现货市场
                    }
                })
            else:
                raise AttributeError("子类必须定义OKX_CONFIG属性")
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"❌ 交易所连接失败: {e}")
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
        import logging
        from datetime import datetime
        from typing import List, Optional, Any
        
        # 配置日志
        logger = logging.getLogger(__name__)
        
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
            
            logger.info(f"已生成交易信号文件: {filename}")
            return filename
        
        # 没有交易信号时返回None
        return None
        
    def save_positions_needing_attention(self, positions: List[Dict[str, Any]]) -> str:
        """保存需要关注的持仓信息
        
        参数:
            positions: 需要关注的持仓列表
        
        返回:
            生成的文件路径
        """
        import os
        import logging
        from datetime import datetime
        
        # 配置日志
        logger = logging.getLogger(__name__)
        
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
        
        logger.info(f"已生成需要关注的持仓记录: {filename}")
        return filename
        
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
        logger = logging.getLogger(__name__)
        
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
        
        # 设置报告目录路径
        report_dir = "reports"
        os.makedirs(report_dir, exist_ok=True)
        
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