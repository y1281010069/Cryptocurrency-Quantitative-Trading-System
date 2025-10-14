#!/usr/bin/env python3
"""
策略基类模块
为多策略系统提供统一的接口和基础功能
"""

import abc
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any


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
        
        logger.info(f"已生成需要关注的持仓记录: {filename}")
        return filename