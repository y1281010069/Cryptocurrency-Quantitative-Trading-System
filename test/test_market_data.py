import os
import sys
import ccxt
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_KEY, SECRET_KEY, PASSPHRASE, TRADING_CONFIG

# 配置日志
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def test_market_data():
    """测试获取市场数据的功能"""
    try:
        # 初始化OKX交易所连接，测试不同的配置
        exchange = ccxt.okx({
            'apiKey': API_KEY,
            'secret': SECRET_KEY,
            'password': PASSPHRASE,
            'enableRateLimit': True,
            # 先不设置defaultType，测试获取所有类型的交易对
        })
        
        print("\n" + "="*60)
        print("🔍 测试市场数据获取")
        print("="*60)
        
        # 测试连接
        exchange.fetch_balance()
        print("✅ OKX交易所连接成功")
        
        # 加载市场数据
        print("\n📊 加载市场数据...")
        markets = exchange.load_markets()
        print(f"✅ 成功加载{len(markets)}个交易对")
        
        # 获取活跃的USDT交易对
        usdt_pairs = [symbol for symbol in markets.keys() if symbol.endswith('/USDT') and markets[symbol]['active']]
        print(f"📈 活跃的USDT交易对数量: {len(usdt_pairs)}")
        
        if usdt_pairs:
            print(f"📋 前5个活跃USDT交易对: {usdt_pairs[:5]}")
        
        # 获取tickers数据
        print("\n📊 获取tickers数据...")
        tickers = exchange.fetch_tickers()
        print(f"✅ 成功获取{len(tickers)}个ticker数据")
        
        # 使用与主脚本相同的逻辑筛选高流动性交易对
        print("\n🔍 筛选高流动性交易对（模仿主脚本逻辑）...")
        
        # 从配置中获取交易量阈值
        volume_threshold = TRADING_CONFIG.get('VOLUME_THRESHOLD', 100000)
        print(f"💹 使用交易量阈值: {volume_threshold} USDT")
        
        volume_filtered = []
        
        for symbol in usdt_pairs:
            if symbol in tickers:
                ticker = tickers[symbol]
                volume = ticker.get('quoteVolume', 0)
                if volume > volume_threshold:
                    volume_filtered.append((symbol, volume))
        
        print(f"📈 满足阈值的交易对数量: {len(volume_filtered)}")
        
        # 打印ticker数据中的一些交易对详情，用于调试
        print("\n📊 检查部分交易对的ticker数据:")
        sample_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'DOGE/USDT']
        
        for symbol in sample_symbols:
            if symbol in usdt_pairs:
                print(f"\n🔍 {symbol}:")
                if symbol in tickers:
                    ticker = tickers[symbol]
                    print(f"   - 存在于tickers中")
                    print(f"   - quoteVolume: {ticker.get('quoteVolume', 'N/A')}")
                    print(f"   - 完整ticker数据: {ticker}")
                else:
                    print(f"   - 不存在于tickers中")
            else:
                print(f"\n🔍 {symbol}:")
                print(f"   - 不在活跃USDT交易对列表中")
        
        # 打印所有活跃USDT交易对的前10个
        print("\n📋 前10个活跃USDT交易对:")
        for symbol in usdt_pairs[:10]:
            print(f"   - {symbol}")
        
        print("\n" + "="*60)
        print("✅ 市场数据测试完成")
        print("="*60)
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_market_data()