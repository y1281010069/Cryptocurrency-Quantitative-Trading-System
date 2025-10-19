import os
import sys
from decimal import Decimal, getcontext

# 设置Decimal精度
getcontext().prec = 20

# 添加项目根目录到Python路径，以便导入models
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 从数据库获取合约信息
from models.variety_model import Variety, variety_model
from models.db_connection import db


def get_ticker(symbol):
    """获取指定交易对的ticker信息
    
    参数:
        symbol: 交易对，例如 'BTC/USDT'
        
    返回:
        ticker信息字典，包含价格等相关数据
    """
    # 示例实现：使用模拟数据
    # 在实际应用中，这里应该调用真实的交易所API
    mock_data = {
        'BTC/USDT': {'price': 50000.0, 'timestamp': 1678886400},
        'ETH/USDT': {'price': 3000.0, 'timestamp': 1678886400},
        'BNB/USDT': {'price': 400.0, 'timestamp': 1678886400}
    }
    
    if symbol in mock_data:
        return mock_data[symbol]
    else:
        raise ValueError(f"未找到交易对 {symbol} 的ticker信息")

def get_contract_info(symbol):
    """获取指定交易对的合约信息
    
    参数:
        symbol: 交易对，例如 'BTC/USDT'
        
    返回:
        合约信息字典，包含最小变动价位、合约乘数等
    """
    # 示例实现：使用模拟数据
    # 在实际应用中，这里应该调用真实的交易所API
    mock_data = {
        'BTC/USDT': {'min_price_change': 0.5, 'contract_multiplier': 1.0, 'symbol': 'BTC/USDT'},
        'ETH/USDT': {'min_price_change': 0.05, 'contract_multiplier': 1.0, 'symbol': 'ETH/USDT'},
        'BNB/USDT': {'min_price_change': 0.1, 'contract_multiplier': 1.0, 'symbol': 'BNB/USDT'}
    }
    
    if symbol in mock_data:
        return mock_data[symbol]
    else:
        raise ValueError(f"未找到交易对 {symbol} 的合约信息")

class ContractInfoCache:
    """合约信息缓存类，用于高效查询合约的乘数信息和最小价格变动单位
    """
    
    def __init__(self):
        """初始化合约信息缓存
        """
        # 示例实现：使用模拟数据初始化缓存
        # 在实际应用中，这里应该从数据库或其他持久化存储加载数据
        self.contract_data = {
            'BTC/USDT': {'min_price_change': 0.5, 'contract_multiplier': 1.0, 'symbol': 'BTC/USDT'},
            'ETH/USDT': {'min_price_change': 0.05, 'contract_multiplier': 1.0, 'symbol': 'ETH/USDT'},
            'BNB/USDT': {'min_price_change': 0.1, 'contract_multiplier': 1.0, 'symbol': 'BNB/USDT'},
            'XRP/USDT': {'min_price_change': 0.0001, 'contract_multiplier': 1.0, 'symbol': 'XRP/USDT'},
            'ADA/USDT': {'min_price_change': 0.001, 'contract_multiplier': 1.0, 'symbol': 'ADA/USDT'}
        }
    
    def get_contract_multiplier(self, symbol):
        """根据交易对获取合约乘数
        
        参数:
            symbol: 交易对，例如 'BTC/USDT'
            
        返回:
            合约乘数
        """
        # 从缓存中查询合约乘数
        if symbol in self.contract_data:
            return self.contract_data[symbol]['contract_multiplier']
        else:
            raise ValueError(f"未找到交易对 {symbol} 的合约信息")
    
    def get_min_price_change(self, symbol):
        """根据交易对获取最小价格变动单位
        
        参数:
            symbol: 交易对，例如 'BTC/USDT'
            
        返回:
            最小价格变动单位
        """
        # 从缓存中查询最小价格变动单位
        if symbol in self.contract_data:
            return self.contract_data[symbol]['min_price_change']
        else:
            raise ValueError(f"未找到交易对 {symbol} 的合约信息")

# 创建全局的合约信息缓存实例
contract_cache = ContractInfoCache()

def calculate_cost(contract_amount, price, symbol):
    """根据合约张数、价格和交易对计算实际成本
    
    参数:
        contract_amount: 合约张数
        price: 价格
        symbol: 交易对
        
    返回:
        实际成本（USDT）
    """
    try:
        # 获取合约乘数
        min_qty = contract_cache.get_contract_min_qty(symbol)
        
        # 计算实际成本: 合约张数 * 合约乘数 * 价格
        cost = Decimal(str(contract_amount)) * min_qty * Decimal(str(price))
        
        return float(cost)
    except Exception as e:
        print(f"计算成本失败: {e}")
        # 出错时返回原始计算方式的结果
        return float(contract_amount) * float(price)

def calculate_position_value(contract_amount, price, symbol):
    """计算仓位市值
    
    参数:
        contract_amount: 合约张数
        price: 当前价格
        symbol: 交易对
        
    返回:
        仓位市值（USDT）
    """
    return calculate_cost(contract_amount, price, symbol)

def convert_contracts_to_coins(contract_amount, symbol):
    """将合约张数转换为实际币种数量
    
    参数:
        contract_amount: 合约张数
        symbol: 交易对
        
    返回:
        实际币种数量
    """
    min_qty = contract_cache.get_contract_min_qty(symbol)
    return float(Decimal(str(contract_amount)) * min_qty)

# 测试函数
if __name__ == "__main__":
    test_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
    
    for symbol in test_symbols:
        min_qty = contract_cache.get_contract_min_qty(symbol)
        print(f"合约 {symbol} 的乘数: {min_qty}")
        
        # 测试计算成本
        test_amount = 10  # 10张合约
        test_price = 10000  # 假设价格
        cost = calculate_cost(test_amount, test_price, symbol)
        print(f"{test_amount}张 {symbol} 在价格 {test_price} 时的成本: {cost}")
        
        # 测试转换为币种数量
        coins = convert_contracts_to_coins(test_amount, symbol)
        print(f"{test_amount}张 {symbol} 等于 {coins} 个币")
        print("---")