import os
import sys
from decimal import Decimal, getcontext

# 设置Decimal精度
getcontext().prec = 20

# 添加项目根目录到Python路径，以便导入models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从数据库获取合约信息
from models.variety_model import Variety
from models.db_connection import db

class ContractInfoCache:
    """合约信息缓存类，用于高效查询合约的乘数信息"""
    def __init__(self):
        self.cache = {}
        self.load_all_contracts()
        
    def load_all_contracts(self):
        """从数据库加载所有合约信息到缓存"""
        try:
            # 从数据库获取所有合约信息
            contract_records = Variety.get_all()
            if contract_records:
                for record in contract_records:
                    # 使用合约名称作为缓存键（小写以便不区分大小写查询）
                    symbol = record.get('variety_name', '').lower()
                    min_qty = Decimal(str(record.get('minQty', '0')))
                    self.cache[symbol] = min_qty
                print(f"成功加载{len(self.cache)}个合约信息到缓存")
        except Exception as e:
            print(f"加载合约信息失败: {e}")
    
    def get_contract_min_qty(self, symbol):
        """获取指定合约的乘数（一张合约等于多少个币）"""
        # 标准化交易对格式，尝试多种可能的格式
        symbol = symbol.replace('/', '-').replace('_', '-').lower()
        
        # 首先在缓存中查找
        if symbol in self.cache:
            return self.cache[symbol]
        
        # 如果缓存中没有，尝试从数据库直接查询
        try:
            # 尝试多种可能的格式
            formats_to_try = [
                symbol,
                symbol.replace('-', '/'),
                symbol.upper(),
                symbol.replace('-', '/').upper()
            ]
            
            for format_attempt in formats_to_try:
                # 使用数据库模型查询
                contract_info = Variety.get(variety_name=format_attempt)
                if contract_info and 'minQty' in contract_info:
                    min_qty = Decimal(str(contract_info['minQty']))
                    # 更新缓存
                    self.cache[symbol] = min_qty
                    return min_qty
            
            # 如果找不到，默认返回1.0
            print(f"未找到合约信息: {symbol}")
            return Decimal('1.0')
        except Exception as e:
            print(f"查询合约信息失败: {e}")
            # 出错时默认返回1.0
            return Decimal('1.0')

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