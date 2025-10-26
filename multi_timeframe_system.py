import time
import json
import os
import logging
import redis
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Tuple
import ccxt
import pandas as pd
import numpy as np
import talib as ta
from lib2 import send_trading_signal_to_api
from strategies.base_strategy import BaseStrategy
from strategies.multi_timeframe_strategy import MultiTimeframeStrategy, MultiTimeframeSignal
import sys
import os
import importlib
import inspect
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# 导入lib.py文件作为一个模块
import importlib.util
# 动态导入lib.py文件
spec = importlib.util.spec_from_file_location("lib_module", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib2.py"))
lib_module = importlib.util.module_from_spec(spec)
sys.modules["lib_module"] = lib_module
spec.loader.exec_module(lib_module)
# 从导入的模块中获取函数
calculate_atr = lib_module.calculate_atr
send_position_info_to_api = lib_module.send_position_info_to_api
send_trading_signal_to_api = lib_module.send_trading_signal_to_api
get_okx_positions = lib_module.get_okx_positions
# 只导入必要的配置，不再导入TRADING_CONFIG
from config import REDIS_CONFIG, API_KEY, SECRET_KEY, PASSPHRASE, OKX_CONFIG

# 配置日志
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class MultiTimeframeProfessionalSystem:
    """多时间框架专业投资系统"""
    
    def __init__(self):
        """初始化系统"""
        self.exchange = None
        self.strategies = {}
        self.output_dir = "reports"
        self.logger = logging.getLogger(__name__)  # 使用与全局相同的logger名称
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化交易所连接
        self._init_exchange()
        
        # 策略启用配置
        self.ENABLED_STRATEGIES = ["test3"]  # 空列表表示启用所有加载的策略
        
        # 动态加载策略
        self._load_strategies()
    
    def _init_exchange(self):
        """初始化交易所连接"""
        try:
            # 配置OKX交易所连接
            # 不设置defaultType，先获取现货交易对数据
            # 如果需要合约交易，可以在获取具体数据时指定类型
            self.exchange = ccxt.okx({'apiKey': API_KEY,'secret': SECRET_KEY,'password': PASSPHRASE,'timeout': 30000,'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'  # 默认使用现货市场
                }
            })
            # 测试连接是否成功
            self.exchange.fetch_balance()
            self.logger.info("✅ 交易所连接成功!")
        except Exception as e:
            self.logger.error(f"❌ 交易所连接失败: {e}")
            raise
    
    def register_strategy(self, name: str, strategy: BaseStrategy):
        """注册交易策略"""
        self.strategies[name] = strategy
        self.logger.info(f"✅ 策略 '{name}' 已注册")
    
    def _load_strategies(self):
        """
        动态加载strategies文件夹中所有继承自BaseStrategy的策略类
        并根据ENABLED_STRATEGIES配置决定是否启用
        """
        try:
            # 加载策略类
            strategy_classes = self._get_strategy_classes()
            
            # 注册并初始化策略
            for strategy_class, module_name in strategy_classes.items():
                strategy_name = strategy_class.__name__
                
                # 检查是否需要启用该策略
                if self.ENABLED_STRATEGIES and strategy_name not in self.ENABLED_STRATEGIES and module_name not in self.ENABLED_STRATEGIES:
                    self.logger.info(f"⏩ 跳过策略 '{strategy_name}' (未在启用列表中)")
                    continue
                
                try:
                    # 安全地初始化策略实例
                    # 优先尝试无参数构造
                    strategy_instance = strategy_class()
                    self.register_strategy(strategy_name, strategy_instance)
                except Exception as e:
                    self.logger.error(f"❌ 初始化策略 '{strategy_name}' 失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"❌ 动态加载策略时发生错误: {str(e)}")
    
    def _get_strategy_classes(self):
        """
        动态加载strategies文件夹中的策略类，只加载继承自BaseStrategy的类
        
        Returns:
            dict: 策略类到文件名的映射字典
        """
        strategy_class_to_filename = {}
        strategies_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'strategies')
        
        # 需要排除的文件
        exclude_files = ['base_strategy.py', '__init__.py']
        # 需要排除的工具类文件
        tool_files = ['condition_analyzer.py']
        
        try:
            self.logger.info(f"开始扫描策略目录: {strategies_dir}")
            self.logger.info(f"排除的文件: {exclude_files + tool_files}")
            self.logger.info(f"启用的策略: {self.ENABLED_STRATEGIES if self.ENABLED_STRATEGIES else '所有策略'}")
            
            # 检查strategies目录是否存在
            if not os.path.exists(strategies_dir):
                self.logger.error(f"策略目录不存在: {strategies_dir}")
                return strategy_class_to_filename
            
            # 遍历strategies目录下的所有.py文件
            for filename in os.listdir(strategies_dir):
                if filename.endswith('.py') and filename not in exclude_files + tool_files:
                    module_name = filename[:-3]  # 去掉.py后缀
                    
                    try:
                        # 动态导入模块
                        module_path = f'strategies.{module_name}'
                        self.logger.info(f"尝试导入模块: {module_path}")
                        module = importlib.import_module(module_path)
                        
                        # 遍历模块中的所有属性
                        for name, obj in inspect.getmembers(module):
                            # 检查是否是类
                            if inspect.isclass(obj):
                                # 检查是否继承自BaseStrategy但不是BaseStrategy本身
                                try:
                                    is_strategy_class = issubclass(obj, BaseStrategy) and obj is not BaseStrategy
                                except TypeError:
                                    # 处理非类对象的情况
                                    is_strategy_class = False
                                    
                                if is_strategy_class:
                                    self.logger.info(f"找到策略类: {obj.__name__} (来自模块: {module_name})")
                                    strategy_class_to_filename[obj] = module_name
                    except Exception as e:
                        self.logger.error(f"导入模块 {module_name} 时出错: {str(e)}")
            
            self.logger.info(f"成功加载 {len(strategy_class_to_filename)} 个策略类")
        except Exception as e:
            self.logger.error(f"加载策略类时发生错误: {str(e)}")
        
        return strategy_class_to_filename
    
    def run_analysis(self):
        """运行多时间框架分析"""
        try:
            # 记录各步骤开始时间
            step_times = {}
            
            # 步骤1: 获取活跃交易对
            step_start = time.time()
            symbols = self._get_active_symbols()
            step_times['获取活跃交易对'] = time.time() - step_start
            self.logger.info(f"🎯 已获取 {len(symbols)} 个活跃交易对")
            
            # 步骤2: 筛选高流动性交易对
            step_start = time.time()
            filtered_symbols = self._filter_high_liquidity_symbols(symbols)
            step_times['筛选高流动性交易对'] = time.time() - step_start
            self.logger.info(f"📊 筛选后剩余 {len(filtered_symbols)} 个高流动性交易对")
            
            # 步骤2.5: 过滤禁用的交易对
            step_start = time.time()
            filtered_symbols = self._filter_disabled_symbols(filtered_symbols)
            step_times['过滤禁用交易对'] = time.time() - step_start
            self.logger.info(f"🚫 应用禁用交易对过滤后，剩余 {len(filtered_symbols)} 个交易对")
            
            # 步骤3: 收集时间框架信息
            step_start = time.time()
            timeframes_info = self._collect_timeframes_info()
            step_times['收集时间框架信息'] = time.time() - step_start
            self.logger.info(f"⏱️  收集了 {len(timeframes_info)} 个策略的时间框架信息")
            
            # 步骤4: 获取K线数据
            step_start = time.time()
            all_data = self._fetch_klines_data(filtered_symbols, timeframes_info)
            step_times['获取K线数据'] = time.time() - step_start
            self.logger.info(f"📈 成功获取 {len(all_data)} 个交易对的K线数据")
            
            # 步骤5: 策略分析
            step_start = time.time()
            all_opportunities = self._analyze_with_strategies(all_data)
            step_times['策略分析'] = time.time() - step_start
            self.logger.info(f"🔍 分析完成，找到 {sum(len(ops) for ops in all_opportunities.values())} 个交易机会")

             # 步骤6: 生成报告和保存信号
            step_start = time.time()
            self._generate_reports(all_opportunities)
            step_times['生成报告'] = time.time() - step_start

            # 过滤信号
            step_start = time.time()
            filtered_opportunities = {}
            for strategy_name, opportunities in all_opportunities.items():
                # 从策略实例中获取过滤后的信号
                strategy_instance = self.strategies[strategy_name]
                filtered_opportunities[strategy_name] = strategy_instance.filter_trade_signals(opportunities)
            step_times['信号过滤'] = time.time() - step_start
            self.logger.info(f"🧹 信号过滤完成，过滤后剩余 {sum(len(ops) for ops in filtered_opportunities.values())} 个交易信号")
            
            # 仓位过滤
            step_start = time.time()
            # 对过滤后的信号再进行仓位过滤
            for strategy_name, signals in filtered_opportunities.items():
                strategy_instance = self.strategies[strategy_name]
                filtered_opportunities[strategy_name] = strategy_instance.filter_by_positions(signals)
            step_times['仓位过滤'] = time.time() - step_start
            self.logger.info(f"📊 仓位过滤完成，过滤后剩余 {sum(len(ops) for ops in filtered_opportunities.values())} 个交易信号")
            self.logger.info(f"过滤后的交易信号示例: {next(iter(filtered_opportunities.values()))[:2]}")  # 只显示前2个信号，避免日志过长.

            # 保存交易信号
            step_start = time.time()
            for strategy_name, opportunities in filtered_opportunities.items():
                # 获取策略实例并调用其保存交易信号的方法
                strategy_instance = self.strategies[strategy_name]
                strategy_instance.save_trade_signals(opportunities)
            step_times['保存交易信号'] = time.time() - step_start
            self.logger.info("📝 所有策略的交易信号已保存完成")

            # # 步骤7: 持仓分析
            step_start = time.time()
            self._analyze_and_report_positions(opportunities)
            step_times['持仓分析'] = time.time() - step_start
            # 打印各步骤用时
            self.logger.info("\n=== 各步骤用时分析 ===")
            for step, duration in step_times.items():
                self.logger.info(f"{step}: {duration:.2f}秒")
            total_time = sum(step_times.values())
            self.logger.info(f"总用时: {total_time:.2f}秒")
            return all_opportunities
        except Exception as e:
            self.logger.error(f"❌ 分析过程中发生错误: {e}")
            raise
    
    def _get_active_symbols(self) -> List[str]:
        """获取活跃交易对"""
        try:
            # 获取交易所所有交易对
            markets = self.exchange.fetch_markets()
            # 筛选活跃的现货交易对
            # 1. 只保留USDT交易对
            # 2. 只保留可交易的交易对
            # 3. 移除不活跃的交易对
            symbols = [
                market['symbol']
                for market in markets
                if market['active'] and 
                   market['quote'] == 'USDT' and 
                   market['type'] == 'spot'
            ]
            return symbols
        except Exception as e:
            self.logger.error(f"获取活跃交易对失败: {e}")
            return []
    
    def _filter_high_liquidity_symbols(self, symbols: List[str]) -> List[str]:
        """筛选高流动性交易对"""
        try:
            # 从策略中获取VOLUME_THRESHOLD配置
            # 注意：现在从策略实例中获取配置，而不是从TRADING_CONFIG中获取
            volume_threshold = 100000  # 默认值
            if self.strategies and hasattr(self.strategies.get("MultiTimeframeStrategy"), 'config'):
                volume_threshold = self.strategies["MultiTimeframeStrategy"].config.get('VOLUME_THRESHOLD', 100000)
            
            # 获取最新24小时成交量数据
            tickers = self.exchange.fetch_tickers(symbols)
            
            # 筛选符合交易量阈值的交易对
            high_liquidity_symbols = []
            for symbol, ticker in tickers.items():
                if isinstance(ticker, dict):
                    # 获取交易量（以USDT为单位）
                    volume = ticker.get('quoteVolume', 0)
                    if volume >= volume_threshold:
                        high_liquidity_symbols.append(symbol)
            
            # 按照成交量降序排序
            high_liquidity_symbols.sort(key=lambda s: tickers[s].get('quoteVolume', 0), reverse=True)
            return high_liquidity_symbols
        except Exception as e:
            self.logger.error(f"筛选高流动性交易对失败: {e}")
            return symbols  # 出错时返回所有交易对
    
    def _filter_disabled_symbols(self, symbols: List[str]) -> List[str]:
        """根据所有策略的DISABLED_SYMBOLS配置过滤交易对"""
        if not self.strategies:
            return symbols
        
        # 收集所有策略中配置的DISABLED_SYMBOLS
        all_disabled_symbols = set()
        for strategy_name, strategy in self.strategies.items():
            if hasattr(strategy, 'config') and 'DISABLED_SYMBOLS' in strategy.config:
                disabled_symbols = strategy.config['DISABLED_SYMBOLS']
                if disabled_symbols:
                    for symbol in disabled_symbols:
                        # 添加多种格式的交易对表示，确保能匹配交易所返回的不同格式
                        # 原始格式
                        all_disabled_symbols.add(symbol)
                        # 斜杠转破折号格式
                        all_disabled_symbols.add(symbol.replace('/', '-'))
                        # 大写格式
                        all_disabled_symbols.add(symbol.replace('/', '-').upper())
                        # 小写格式
                        all_disabled_symbols.add(symbol.replace('/', '-').lower())
                    self.logger.info(f"策略 '{strategy_name}' 的禁用交易对: {disabled_symbols}")
        
        if all_disabled_symbols:
            # 打印所有交易对，用于调试
            self.logger.info(f"当前交易对列表（前10个）: {symbols[:10]}")
            
            # 过滤掉禁用的交易对
            filtered_symbols = []
            for symbol in symbols:
                # 检查symbol是否与任何禁用的交易对匹配（忽略格式差异）
                is_disabled = False
                # 转换symbol为统一格式进行比较
                symbol_normalized = symbol.upper().replace('/', '-')
                for disabled in all_disabled_symbols:
                    disabled_normalized = disabled.upper().replace('/', '-')
                    if symbol_normalized == disabled_normalized:
                        is_disabled = True
                        self.logger.info(f"过滤掉禁用交易对: {symbol} (匹配: {disabled})")
                        break
                
                if not is_disabled:
                    filtered_symbols.append(symbol)
            
            self.logger.info(f"应用禁用交易对过滤: 移除 {len(symbols) - len(filtered_symbols)} 个交易对")
            self.logger.info(f"禁用的交易对格式列表: {list(all_disabled_symbols)}")
            return filtered_symbols
        
        return symbols
    
    def _collect_timeframes_info(self) -> Dict[str, Dict[str, int]]:
        """收集所有策略需要的时间框架信息"""
        timeframes_info = {}
        
        for name, strategy in self.strategies.items():
            if hasattr(strategy, 'get_required_timeframes'):
                timeframes = strategy.get_required_timeframes()
                timeframes_info[name] = timeframes
                self.logger.info(f"策略 '{name}' 需要的时间框架: {timeframes}")
        return timeframes_info
    
    def _fetch_klines_data(self, symbols: List[str], timeframes_info: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """获取K线数据"""
        all_data = {}
        
        # 合并所有策略需要的时间框架
        all_timeframes = set()
        for timeframes in timeframes_info.values():
            all_timeframes.update(timeframes.keys())
        
        # 每个策略的最小数据长度要求
        min_lengths = {}
        for strategy_name, timeframes in timeframes_info.items():
            for tf, length in timeframes.items():
                if tf not in min_lengths or length > min_lengths[tf]:
                    min_lengths[tf] = length
        
        # 为每个交易对获取所有需要的K线数据
        for symbol in symbols:
            symbol_data = {}
            try:
                # self.logger.info(f"正在获取 {symbol} 的K线数据...")
                for tf in all_timeframes:
                    try:
                        # 获取足够的历史数据
                        limit = min_lengths[tf] + 10  # 多获取10根K线作为缓冲
                        ohlcv = self.exchange.fetch_ohlcv(symbol, tf, limit=limit)
                        if ohlcv:
                            # 转换为DataFrame
                            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                            df.set_index('timestamp', inplace=True)
                            # 确保数据类型正确
                            df = df.astype({'open': 'float64','high': 'float64','low': 'float64','close': 'float64','volume': 'float64'})
                            symbol_data[tf] = df
                        else:
                            self.logger.warning(f"未获取到 {symbol} 的 {tf} 数据")
                            symbol_data[tf] = pd.DataFrame()
                    except Exception as e:
                        self.logger.error(f"获取 {symbol} 的 {tf} 数据失败: {e}")
                        symbol_data[tf] = pd.DataFrame()
                # 检查是否有足够的数据
                valid_timeframes = [tf for tf, df in symbol_data.items() if not df.empty and len(df) >= min_lengths[tf]]
                # 如果至少有一半时间框架的数据，则保留
                if len(valid_timeframes) >= len(all_timeframes) / 2:
                    all_data[symbol] = symbol_data
            except Exception as e:
                self.logger.error(f"处理 {symbol} 的数据时发生错误: {e}")
        return all_data
    
    def _analyze_with_strategies(self, all_data: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, List[Any]]:
        """使用所有注册的策略进行分析"""
        all_opportunities = {name: [] for name in self.strategies}
        # 创建线程池，用于并行分析
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 提交所有分析任务
            futures = {}
            for symbol, data in all_data.items():
                for strategy_name, strategy in self.strategies.items():
                    # 检查策略是否有analyze方法
                    if hasattr(strategy, 'analyze'):
                        # 检查该策略需要的时间框架数据是否可用
                        required_timeframes = strategy.get_required_timeframes() if hasattr(strategy, 'get_required_timeframes') else {}
                        # 检查是否所有必需的时间框架都有数据
                        has_required_data = True
                        missing_timeframes = []
                        for tf in required_timeframes:
                            if tf not in data or data[tf].empty or len(data[tf]) < required_timeframes[tf]:
                                has_required_data = False
                                missing_timeframes.append(tf)
                        # 如果没有足够的时间框架数据，跳过该策略的分析
                        if not has_required_data:
                            self.logger.info(f"跳过 {symbol} 的 {strategy_name} 分析：缺少必需的时间框架数据 - 缺少的周期: {missing_timeframes}")
                            continue
                        # 提交分析任务
                        future_key = (symbol, strategy_name)
                        futures[future_key] = executor.submit(strategy.analyze, symbol, data)
            # 收集分析结果
            for (symbol, strategy_name), future in futures.items():
                try:
                    result = future.result()
                    if result is not None:
                        all_opportunities[strategy_name].append(result)
                except Exception as e:
                    self.logger.error(f"{strategy_name} 分析 {symbol} 时发生错误: {e}")
        return all_opportunities
    
    def _generate_reports(self, all_opportunities: Dict[str, List[Any]]):
        """生成分析报告"""
        for strategy_name, opportunities in all_opportunities.items():
            if not opportunities:
                self.logger.info(f"策略 '{strategy_name}' 未找到交易机会")
                continue
            
            # 按总分排序（买入信号降序，卖出信号降序）
            # 由于我们之前修改了策略返回的信号结构，现在需要确保能够正确排序
            try:
                opportunities.sort(key=lambda x: getattr(x, 'total_score', 0), reverse=True)
            except Exception as e:
                self.logger.error(f"排序交易机会时发生错误: {e}")
                # 如果排序失败，继续执行，不中断流程
            self.logger.info(f"📝 策略 '{strategy_name}' 找到 {len(opportunities)} 个交易机会")
    
            # 调用策略实例的方法保存交易信号
            strategy_instance = self.strategies[strategy_name]
            # strategy_instance._save_trade_signals(opportunities)
            
            # 调用策略的save_multi_timeframe_analysis方法生成多时间框架分析报告
            if strategy_instance and hasattr(strategy_instance, 'save_multi_timeframe_analysis'):
                try:
                    file_path = strategy_instance.save_multi_timeframe_analysis(opportunities)
                    if file_path:
                        self.logger.info(f"✅ 多时间框架分析报告已保存至: {file_path}")
                except Exception as e:
                    self.logger.error(f"保存多时间框架分析报告时发生错误: {e}")
    
    def _analyze_and_report_positions(self, all_opportunities):
        """分析当前持仓并报告需要关注的持仓"""
        try:
            # 获取当前持仓
            current_positions = get_okx_positions(self.exchange)
            if not current_positions:
                self.logger.info("📋 当前没有持仓")
                return
            self.logger.info(f"📋 获取到 {len(current_positions)} 个当前持仓")
            # 收集所有交易机会到一个列表
            all_opportunities_list = []
            # 添加类型检查，处理all_opportunities可能是列表或字典的情况
            if isinstance(all_opportunities, dict):
                for opportunities in all_opportunities.values():
                    all_opportunities_list.extend(opportunities)
            elif isinstance(all_opportunities, list):
                all_opportunities_list.extend(all_opportunities)
            # 对每个策略调用analyze_positions方法
            for strategy_name, strategy in self.strategies.items():
                if hasattr(strategy, 'analyze_positions'):
                    try:
                        positions_needing_attention = strategy.analyze_positions(current_positions, all_opportunities_list)
                        if positions_needing_attention:
                            logger.info(f"⚠️  策略 '{strategy_name}' 发现 {len(positions_needing_attention)} 个需要关注的持仓")
                            # 保存需要关注的持仓
                            if hasattr(strategy, 'save_positions_needing_attention'):
                                file_path = strategy.save_positions_needing_attention(positions_needing_attention)
                                if file_path:
                                    logger.info(f"✅ 需要关注的持仓已保存至: {file_path}")
                            # 发送需要关注的持仓信息到API
                            for pos in positions_needing_attention:
                                try:
                                    # 格式化symbol，将AAVE/USDT:USDT转换为AAVE-USDT格式
                                    symbol_formatted = pos['symbol'].split(':')[0].replace('/', '-')
                                    send_position_info_to_api(pos, symbol_formatted, self.logger)
                                except Exception as e:
                                    self.logger.error(f"发送持仓信息到API时发生错误: {e}")
                    except Exception as e:
                        self.logger.error(f"策略 '{strategy_name}' 分析持仓时发生错误: {e}")
        except Exception as e:
            self.logger.error(f"获取或分析持仓时发生错误: {e}")

# 主函数入口
if __name__ == "__main__":
    try:
        # 初始化系统
        system = MultiTimeframeProfessionalSystem()
        # 运行分析
        system.logger.info("🚀 开始多时间框架分析...")
        all_opportunities = system.run_analysis()
        system.logger.info("✅ 多时间框架分析完成!")
    except Exception as e:
        # 使用全局logger记录错误
        logger.error(f"❌ 系统运行失败: {e}")
        # 保留命令行，方便查看错误信息
        input("按Enter键退出...")