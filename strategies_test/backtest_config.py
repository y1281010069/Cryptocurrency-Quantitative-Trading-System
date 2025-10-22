# 回测配置文件
import datetime

# 回测时间范围配置
START_YEAR = 2024
START_MONTH = 1
START_DAY = 1
BACKTEST_DAYS = 605  # 回测天数

# 初始资金配置
INITIAL_CAPITAL = 10000.0

# 回测策略配置
# 指定要测试的策略，空列表表示测试所有策略
# 交易对配置
# SYMBOLS = ["BTC-USDT", "ETH-USDT"]  # 交易对列表
SYMBOLS = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "ADA-USDT", "DOGE-USDT", "ARB-USDT", "LTC-USDT"]  # 交易对列表

# 可以填写策略文件名（不含.py后缀）或策略类名
STRATEGIES_TO_TEST = ["multi_timeframe_strategy_ema", "multi_timeframe_strategy", "test3"]  # 测试所有策略
# STRATEGIES_TO_TEST = ["multi_timeframe_strategy"]  # 只测试指定文件名的策略
# STRATEGIES_TO_TEST = ["MultiTimeframeStrategy"]  # 只测试指定类名的策略

# 其他回测相关配置
MAX_RETRY_COUNT = 3  # API请求最大重试次数
REQUEST_TIMEOUT = 30  # API请求超时时间（秒）

# 计算开始和结束日期
START_DATE = datetime.datetime(START_YEAR, START_MONTH, START_DAY)
END_DATE = START_DATE + datetime.timedelta(days=BACKTEST_DAYS)