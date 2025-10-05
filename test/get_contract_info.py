#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从数据库variety表获取合约信息，包括minQty等参数
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.variety_model import variety_model


def get_contract_min_qty(symbol: str) -> dict:
    """
    根据交易对获取合约的minQty信息
    
    Args:
        symbol: 交易对符号，如'BTC/USDT'
        
    Returns:
        dict: 包含合约信息的字典，包括minQty、stepSize等字段
    """
    try:
        # 从数据库查询合约信息
        # 尝试多种可能的格式，因为数据库中使用的是连字符格式
        formats_to_try = [
            symbol.replace('/', '-'),  # 转换为连字符格式
            symbol.upper().replace('/', '-'),  # 大写并转换为连字符格式
            symbol.lower().replace('/', '-'),  # 小写并转换为连字符格式
            symbol,  # 保持原始格式
            symbol.upper(),  # 大写原始格式
            symbol.lower()  # 小写原始格式
        ]
        
        contract_info = None
        # 尝试所有可能的格式
        for db_symbol in formats_to_try:
            contract_info = variety_model.get(name=db_symbol)
            if contract_info:
                break
        
        if not contract_info:
            # 如果找不到精确匹配，尝试获取所有合约信息并打印
            all_contracts = variety_model.get_all()
            print(f"找不到交易对 '{symbol}' 的合约信息，数据库中共有 {len(all_contracts)} 个合约记录")
            
            # 打印前5条记录作为参考
            if all_contracts:
                print("\n数据库中的部分合约记录：")
                for i, contract in enumerate(all_contracts[:5]):
                    print(f"{i+1}. 合约名称: {contract.get('name', '未知')}")
            
            return None
        
        # 提取需要的信息
        result = {
            'symbol': symbol,
            'db_symbol': contract_info.get('name', ''),
            'minQty': contract_info.get('minQty', 0),
            'maxQty': contract_info.get('maxQty', 0),
            'stepSize': contract_info.get('stepSize', 0),
            'minSz': contract_info.get('minSz', 0),
            'pricePrecision': contract_info.get('pricePrecision', 0),
            'quantityPrecision': contract_info.get('quantityPrecision', 0)
        }
        
        return result
        
    except Exception as e:
        print(f"获取合约信息时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    print("=== 合约信息查询工具 ===")
    
    # 示例交易对列表
    example_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
    
    # 用户可以输入交易对，或使用示例
    user_input = input(f"请输入要查询的交易对（如BTC/USDT），或按回车使用示例: ").strip()
    
    if user_input:
        symbols = [user_input]
    else:
        symbols = example_symbols
        print(f"\n将查询以下交易对: {', '.join(symbols)}")
    
    print("\n查询结果:\n" + "-"*60)
    
    for symbol in symbols:
        print(f"\n交易对: {symbol}")
        contract_info = get_contract_min_qty(symbol)
        
        if contract_info:
            print(f"  数据库中的合约名称: {contract_info['db_symbol']}")
            print(f"  最小交易数量(minQty): {contract_info['minQty']}")
            print(f"  最大交易数量(maxQty): {contract_info['maxQty']}")
            print(f"  交易步进(stepSize): {contract_info['stepSize']}")
            print(f"  最小交易金额(minSz): {contract_info['minSz']}")
            print(f"  价格精度(pricePrecision): {contract_info['pricePrecision']}")
            print(f"  数量精度(quantityPrecision): {contract_info['quantityPrecision']}")
            
            # 计算一张等于几个币
            min_qty = contract_info['minQty']
            if min_qty > 0:
                print(f"\n  根据minQty计算结果:")
                print(f"  一张合约等于 {min_qty} 个币")
        else:
            print("  未找到合约信息")
    
    print("\n" + "-"*60)
    print("查询完成！")


if __name__ == "__main__":
    main()