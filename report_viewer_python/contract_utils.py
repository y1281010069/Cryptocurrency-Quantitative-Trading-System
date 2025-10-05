#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合约工具函数，提供从数据库获取合约信息的功能
"""
import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.variety_model import variety_model

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ContractInfoCache:
    """合约信息缓存类，避免重复查询数据库"""
    def __init__(self):
        self.cache = {}
        
    def get_contract_multiplier(self, symbol: str) -> float:
        """
        获取合约乘数（一张合约等于几个币）
        
        Args:
            symbol: 交易对符号，如'BTC/USDT'
            
        Returns:
            float: 合约乘数，如果获取失败返回1.0（默认值）
        """
        # 检查缓存中是否已有结果
        if symbol in self.cache:
            return self.cache[symbol]
        
        try:
            # 处理OKX API返回的格式，移除可能的:USDT后缀
            base_symbol = symbol
            if base_symbol.find(':') != -1:
                base_symbol = base_symbol.split(':')[0]
                logger.debug(f"处理交易对格式: {symbol} -> {base_symbol}")
            
            # 尝试多种可能的格式，因为数据库中使用的是连字符格式
            formats_to_try = [
                base_symbol.replace('/', '-'),  # 转换为连字符格式
                base_symbol.upper().replace('/', '-'),  # 大写并转换为连字符格式
                base_symbol.lower().replace('/', '-'),  # 小写并转换为连字符格式
                base_symbol,  # 保持原始格式
                base_symbol.upper(),  # 大写原始格式
                base_symbol.lower()  # 小写原始格式
            ]
            
            contract_info = None
            # 尝试所有可能的格式
            for db_symbol in formats_to_try:
                contract_info = variety_model.get(name=db_symbol)
                if contract_info:
                    break
            
            if contract_info:
                # 获取minQty作为合约乘数
                multiplier = float(contract_info.get('minQty', 1.0))
                logger.info(f"成功获取合约乘数: {symbol} -> {multiplier}")
            else:
                # 如果找不到合约信息，默认返回1.0
                multiplier = 1.0
                logger.warning(f"未找到合约信息，使用默认乘数: {symbol} -> {multiplier}")
            
            # 缓存结果
            self.cache[symbol] = multiplier
            return multiplier
            
        except Exception as e:
            logger.error(f"获取合约乘数时发生错误: {symbol}, 错误: {e}")
            # 出错时返回默认值1.0
            return 1.0


# 创建全局的合约信息缓存实例
contract_cache = ContractInfoCache()


def get_contract_multiplier(symbol: str) -> float:
    """
    便捷函数，获取合约乘数（一张合约等于几个币）
    
    Args:
        symbol: 交易对符号，如'BTC/USDT'
        
    Returns:
        float: 合约乘数
    """
    return contract_cache.get_contract_multiplier(symbol)


def calculate_position_value(amount: float, price: float, symbol: str) -> float:
    """
    计算仓位市值
    
    Args:
        amount: 持仓数量（合约张数）
        price: 当前价格
        symbol: 交易对符号
        
    Returns:
        float: 仓位市值
    """
    # 获取合约乘数
    multiplier = get_contract_multiplier(symbol)
    # 计算市值：合约张数 * 合约乘数 * 当前价格
    return amount * multiplier * price


def calculate_cost(amount: float, entry_price: float, symbol: str) -> float:
    """
    计算持仓成本
    
    Args:
        amount: 持仓数量（合约张数）
        entry_price: 入场价格
        symbol: 交易对符号
        
    Returns:
        float: 持仓成本
    """
    # 获取合约乘数
    multiplier = get_contract_multiplier(symbol)
    # 计算成本：合约张数 * 合约乘数 * 入场价格
    return amount * multiplier * entry_price