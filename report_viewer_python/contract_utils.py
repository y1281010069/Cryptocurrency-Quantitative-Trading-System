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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)


class ContractInfoCache:
    """合约信息缓存类，避免重复查询数据库"""
    def __init__(self):
        self.cache = {}  # 缓存每个符号的乘数
        self.all_contracts = None  # 存储所有合约信息的字典
        self.contracts_loaded = False  # 标记是否已加载所有合约信息
    
    def _load_all_contracts(self):
        """一次性加载所有合约信息到内存"""
        if not self.contracts_loaded:
            try:
                logger.info("正在一次性加载所有合约信息...")
                # 一次性获取所有合约信息
                all_contracts_data = variety_model.get_all()
                # 创建名称到合约信息的映射字典
                self.all_contracts = {}
                for contract in all_contracts_data:
                    name = contract.get('name', '').lower()
                    self.all_contracts[name] = contract
                self.contracts_loaded = True
                logger.info(f"成功加载{len(self.all_contracts)}条合约信息")
            except Exception as e:
                logger.error(f"加载所有合约信息时发生错误: {e}")
                self.all_contracts = {}
                self.contracts_loaded = True  # 即使出错也标记为已加载，避免重复尝试
    
    def get_contract_multiplier(self, symbol: str) -> float:
        """
        获取合约乘数（一张合约等于几个币）
        
        Args:
            symbol: 交易对符号，如'BTC/USDT'或'BTC-USDT-SWAP'
            
        Returns:
            float: 合约乘数，如果获取失败返回1.0（默认值）
        """
        # 检查缓存中是否已有结果
        if symbol in self.cache:
            return self.cache[symbol]
        
        try:
            # 确保已加载所有合约信息
            self._load_all_contracts()
            
            # 处理OKX API返回的格式
            base_symbol = symbol
            
            # 处理带-SWAP后缀的合约名称
            if '-SWAP' in base_symbol:
                # 提取基础交易对，如LINK-USDT-SWAP -> LINK-USDT
                base_symbol_without_swap = base_symbol.replace('-SWAP', '')
                logger.debug(f"处理SWAP格式: {symbol} -> {base_symbol_without_swap}")
            else:
                base_symbol_without_swap = base_symbol
                
            # 处理带冒号的格式，如'BTC:USDT'
            if base_symbol_without_swap.find(':') != -1:
                base_symbol_without_swap = base_symbol_without_swap.split(':')[0]
                logger.debug(f"处理冒号格式: {symbol} -> {base_symbol_without_swap}")
            
            # 尝试多种可能的格式，因为数据库中使用的是连字符格式
            formats_to_try = [
                base_symbol_without_swap.replace('/', '-'),  # 转换为连字符格式
                base_symbol_without_swap.upper().replace('/', '-'),  # 大写并转换为连字符格式
                base_symbol_without_swap.lower().replace('/', '-'),  # 小写并转换为连字符格式
                base_symbol_without_swap,  # 保持原始格式
                base_symbol_without_swap.upper(),  # 大写原始格式
                base_symbol_without_swap.lower(),  # 小写原始格式
                base_symbol,  # 保持完整的原始格式（包括SWAP后缀）
                base_symbol.upper(),  # 大写完整的原始格式
                base_symbol.lower()  # 小写完整的原始格式
            ]
            
            contract_info = None
            # 在内存中尝试所有可能的格式
            for db_symbol in formats_to_try:
                if db_symbol.lower() in self.all_contracts:
                    contract_info = self.all_contracts[db_symbol.lower()]
                    break
            
            # 如果内存中没有找到，再尝试单条查询（作为备选）
            if not contract_info:
                for db_symbol in formats_to_try:
                    contract_info = variety_model.get(name=db_symbol)
                    if contract_info:
                        # 将找到的合约信息添加到内存字典中
                        self.all_contracts[db_symbol.lower()] = contract_info
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