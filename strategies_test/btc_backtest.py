#!/usr/bin/env python3
"""
BTC多时间框架策略回测脚本
使用OKX官方API获取历史K线数据，回测过去3个月的交易收益
"""

import os
import sys
import pandas as pd
import numpy as np
import time
import time as time_module
from datetime import datetime, timedelta
import logging
import json

# ===== 配置参数 =====
# 交易标的配置
symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "ADA-USDT", "DOGE-USDT", "ARB-USDT", "LTC-USDT"]  # 交易对列表

# 回测时间范围配置
start_date = datetime(2025, 1, 1)  # 开始日期
end_date = start_date + timedelta(days=240)  # 结束日期（开始日期往后240天）

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 添加OKX库到路径
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib', 'python-okx-master'))

# 导入OKX市场数据API
from okx.MarketData import MarketAPI
# 导入策略类
from strategies.multi_timeframe_strategy_ema import MultiTimeframeStrategy

# 配置日志
logging.basicConfig(
    level=logging.INFO,  # 设置为DEBUG级别以输出详细的时间框架验证日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, strategy_class, initial_capital=10000.0, symbol=None):
        """
        初始化回测引擎
        
        Args:
            strategy_class: 策略类
            initial_capital: 初始资金
            symbol: 交易对
        """
        self.strategy = strategy_class()
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = 0  # 持仓数量 (正数为多仓，负数为空仓)
        self.entry_price = 0.0  # 入场价格
        self.stop_loss = 0.0  # 仓位止损价格
        self.take_profit = 0.0  # 仓位止盈价格
        self.symbol = symbol  # 使用传入的交易对
        self.trades = []  # 交易记录
        self.timeframe_data = {}  # 多时间框架数据
        self.api_timeframe_map = {}  # API时间框架映射
        self.market_api = MarketAPI()
        logger.info(f"初始化回测引擎，策略需要的时间框架: {list(self.strategy.get_required_timeframes().keys())}")
    
    def fetch_historical_data(self, timeframe, start_time, end_time):
        """
        获取历史K线数据（优先从Excel读取，不存在则从OKX API获取并保存）
        
        Args:
            timeframe: 时间框架
            start_time: 开始时间（毫秒时间戳）
            end_time: 结束时间（毫秒时间戳）
            
        Returns:
            pandas.DataFrame: K线数据
        """
        # 创建数据目录
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'historical_data')
        os.makedirs(data_dir, exist_ok=True)
        
        # 生成Excel文件名
        start_date = pd.to_datetime(start_time, unit='ms').strftime('%Y%m%d')
        end_date = pd.to_datetime(end_time, unit='ms').strftime('%Y%m%d')
        excel_file = os.path.join(data_dir, f'{self.symbol}_{timeframe}_{start_date}_{end_date}.xlsx')
        
        # 尝试从Excel读取数据
        start_datetime = pd.to_datetime(start_time, unit='ms')
        end_datetime = pd.to_datetime(end_time, unit='ms')
        
        try:
            if os.path.exists(excel_file):
                logger.info(f"尝试从Excel文件读取{timeframe}数据: {excel_file}")
                df = pd.read_excel(excel_file)
                
                # 检查数据时间范围是否覆盖需求
                df_start = df['datetime'].min()
                df_end = df['datetime'].max()
                
                if df_start <= start_datetime and df_end >= end_datetime:
                    # 过滤出需要的时间范围
                    df = df[(df['datetime'] >= start_datetime) & (df['datetime'] <= end_datetime)]
                    logger.info(f"成功从Excel读取数据，共{len(df)}条，时间范围: {df['datetime'].min()} 至 {df['datetime'].max()}")
                    return df
                else:
                    logger.info(f"Excel数据时间范围不完整，需要从API获取，当前Excel范围: {df_start} - {df_end}，需要范围: {start_datetime} - {end_datetime}")
            else:
                logger.info(f"Excel文件不存在，将从API获取数据: {excel_file}")
        except Exception as e:
            logger.warning(f"读取Excel文件失败: {str(e)}，将从API获取数据")
        
        # 从API获取数据
        all_data = []
        limit = 300  # 恢复官方limit为300
        request_count = 0  # 记录请求次数
        
        try:
            logger.info(f"开始获取{timeframe}数据，时间范围: {pd.to_datetime(start_time, unit='ms')} 至 {pd.to_datetime(end_time, unit='ms')}")
            
            # 根据不同时间框架计算after值，确保第一条数据是20250101 00:00:00
            # 解析时间框架，确定每个周期的毫秒数
            period_ms = 0
            
            if timeframe.endswith('m'):
                # 分钟级别
                minutes = int(timeframe[:-1])
                period_ms = minutes * 60 * 1000
            elif timeframe.endswith('H'):
                # 小时级别
                hours = int(timeframe[:-1])
                period_ms = hours * 60 * 60 * 1000
            elif timeframe.endswith('D'):
                # 日级别
                days = int(timeframe[:-1])
                period_ms = days * 24 * 60 * 60 * 1000
            
            # 初始化period_ms
            period_ms = 0
            if timeframe.endswith('m'):
                minutes = int(timeframe[:-1])
                period_ms = minutes * 60 * 1000
            elif timeframe.endswith('H'):
                hours = int(timeframe[:-1])
                period_ms = hours * 60 * 60 * 1000
            elif timeframe.endswith('D'):
                days = int(timeframe[:-1])
                period_ms = days * 24 * 60 * 60 * 1000
            
            # 初始after值设为start_time加上适当数量的周期
            cycles_to_add = 300
            if period_ms > 0:
                current_after = start_time + (cycles_to_add * period_ms)
                logger.info(f"为{timeframe}时间框架设置初始after值: {current_after} ({pd.to_datetime(current_after, unit='ms')})，计算逻辑: {pd.to_datetime(start_time, unit='ms')} + ({cycles_to_add} * {period_ms/1000}秒)")
            else:
                current_after = start_time
                logger.warning(f"无法解析时间框架{timeframe}，使用start_time作为after值")
            
            # 添加循环分页获取数据的逻辑
            max_requests = 1000  # 限制最大请求次数，避免无限循环
            while request_count < max_requests:
                request_count += 1
                logger.info(f"第{request_count}次请求{timeframe}数据，使用after={current_after}")
                
                try:
                    response = self.market_api.get_history_candlesticks(
                        instId=self.symbol,
                        bar=timeframe,
                        after=str(current_after),  # 使用当前after值
                        limit=str(limit)
                    )
                    
                    if response['code'] == '0':
                        if response['data']:
                            data = response['data']
                            logger.info(f"第{request_count}次请求获取到{timeframe}数据: {len(data)}条，当前累计: {len(all_data) + len(data)}条")
                            
                            # 记录数据的时间范围
                            try:
                                # OKX API返回的字段顺序: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                                # data[0][0] = 最新数据的时间戳(ts)
                                # data[-1][0] = 最早数据的时间戳(ts)
                                first_timestamp = int(data[0][0])  # 第一个数据点的时间戳(最新)
                                last_timestamp = int(data[-1][0])  # 最后一个数据点的时间戳(最早)
                                # 安全地转换时间戳
                                first_datetime = pd.to_datetime(first_timestamp, unit='ms', errors='coerce')
                                last_datetime = pd.to_datetime(last_timestamp, unit='ms', errors='coerce')
                                logger.info(f"本次获取数据时间范围: {first_datetime} 至 {last_datetime}")
                            except Exception as e:
                                logger.warning(f"解析时间戳时出错: {e}")
                            
                            all_data.extend(data)
                            
                            # 更新current_after为本次数据中最早的数据点时间戳，用于获取更旧的数据
                            # 由于OKX API的after参数是获取此时间戳之后的数据，我们需要调整逻辑
                            # 这里我们使用最新的数据点时间戳作为下一次请求的after值
                            if data:
                                # 获取本次数据中最新的数据点时间戳
                                latest_timestamp = int(data[0][0])
                                
                                # 检查是否已经获取了足够的数据（达到结束时间或数据量上限）
                                if latest_timestamp >= end_time:  # 设置一个合理的数据量上限
                                    logger.info(f"已获取足够数据，达到结束时间或数据量上限")
                                    break
                                
                                # 更新after值，确保获取更新的数据
                                # 更新after值为本次数据中最晚时间加上适当数量的周期
                                latest_timestamp = int(data[0][0])
                                # 重新计算周期毫秒数
                                period_ms = 0
                                if timeframe.endswith('m'):
                                    minutes = int(timeframe[:-1])
                                    period_ms = minutes * 60 * 1000
                                elif timeframe.endswith('H'):
                                    hours = int(timeframe[:-1])
                                    period_ms = hours * 60 * 60 * 1000
                                elif timeframe.endswith('D'):
                                    days = int(timeframe[:-1])
                                    period_ms = days * 24 * 60 * 60 * 1000
                                
                                # 对于15m时间框架，增加每次跳跃的周期数，确保能获取到完整时间范围
                                cycles_to_add = 300      
                                if period_ms > 0:
                                    current_after = latest_timestamp + (cycles_to_add * period_ms)
                                    logger.info(f"更新after值为: {current_after} ({pd.to_datetime(current_after, unit='ms')})，计算逻辑: {pd.to_datetime(latest_timestamp, unit='ms')} + ({cycles_to_add} * {period_ms/1000}秒)")
                                else:
                                    current_after = latest_timestamp
                                    logger.warning(f"无法解析时间框架{timeframe}，使用最新时间戳作为after值")
                            
                            # 如果本次返回的数据少于limit，说明可能已经获取了所有可用数据
                            if len(data) < limit:
                                logger.info(f"返回数据少于limit，可能已获取所有可用数据")
                                break
                            
                            # 避免请求过快，添加短暂延迟
                            time.sleep(0.1)
                        else:
                            logger.warning(f"第{request_count}次请求{timeframe}数据返回空结果")
                            break
                    else:
                        logger.error(f"第{request_count}次请求{timeframe}数据失败: 错误码={response['code']}, 消息={response['msg']}")
                        # 尝试减小limit再请求一次
                        if limit > 50 and request_count == 1:  # 只在第一次请求失败时尝试减小limit
                            limit = 50
                            logger.info(f"减小limit至{limit}并重试")
                            continue
                        break
                except Exception as api_error:
                    logger.error(f"第{request_count}次API调用异常: {str(api_error)}")
                    # 尝试减小limit再请求一次
                    if limit > 50 and request_count == 1:  # 只在第一次请求异常时尝试减小limit
                        limit = 50
                        logger.info(f"减小limit至{limit}并重试")
                        continue
                    break
        except Exception as e:
            logger.error(f"获取数据过程中出现异常: {str(e)}")
        
        logger.info(f"数据获取完成，累计获取{len(all_data)}条原始数据，请求次数: {request_count}")
        
        # 检查数据是否为空
        if not all_data:
            logger.warning(f"未获取到{timeframe}数据，返回空DataFrame")
            return pd.DataFrame()
        
        # 转换数据为DataFrame
        try:
            # 转换为DataFrame，使用OKX API返回的字段顺序
            # ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm
            df = pd.DataFrame(all_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 
                'volume_ccy', 'volume_ccy_quote', 'confirm'
            ])
            
            # 转换时间戳为datetime类型
            df['datetime'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            
            # 转换数值列的数据类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                              'volume_ccy', 'volume_ccy_quote']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 按时间排序（升序）
            df = df.sort_values('datetime', ascending=True).reset_index(drop=True)
            
            # 去重处理，避免分页拉取时出现重复数据
            original_len = len(df)
            df = df.drop_duplicates(subset=['timestamp'], keep='last')
            duplicate_count = original_len - len(df)
            if duplicate_count > 0:
                logger.info(f"移除了{duplicate_count}条重复数据，剩余{len(df)}条数据")
            
            # 过滤掉超出指定时间范围的数据
            start_datetime = pd.to_datetime(start_time, unit='ms')
            end_datetime = pd.to_datetime(end_time, unit='ms')
            original_len = len(df)
            df = df[(df['datetime'] >= start_datetime) & (df['datetime'] <= end_datetime)]
            filtered_count = original_len - len(df)
            if filtered_count > 0:
                logger.info(f"过滤掉{filtered_count}条超出时间范围的数据，剩余{len(df)}条")
            
            # 保存数据到Excel文件，方便下次读取
            try:
                # 确保excel_file变量在这个作用域内可见
                if 'excel_file' in locals():
                    df.to_excel(excel_file, index=False)
                    logger.info(f"数据已保存到Excel文件: {excel_file}")
            except Exception as e:
                logger.warning(f"保存数据到Excel失败: {str(e)}")
            
            return df
        except Exception as e:
            logger.error(f"处理{timeframe}数据时出错: {str(e)}")
            return pd.DataFrame()
            
            # 去重处理，避免重复数据
            if all_data:
                # 转换为DataFrame进行去重
                temp_df = pd.DataFrame(all_data)
                # 基于时间戳去重
                temp_df = temp_df.drop_duplicates(subset=[0])
                # 转回列表
                all_data = temp_df.values.tolist()
                logger.info(f"去重后剩余{len(all_data)}条数据")
            
            # 将数据转换为DataFrame
            if all_data:
                # 反转数据，使其按时间升序排列
                all_data.reverse()
                
                # OKX API返回的字段顺序: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                # ts = 时间戳(毫秒), o = 开盘价, h = 最高价, l = 最低价, c = 收盘价
                # vol = 交易量(张), volCcy = 交易量(币), volCcyQuote = 交易量(计价币), confirm = K线状态
                df = pd.DataFrame(all_data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume', 
                    'volume_ccy', 'volume_ccy_quote', 'confirm'
                ])
                
                # 将数据信息写入日志文件
                log_file_path = f"{timeframe}_data_analysis.txt"
                with open(log_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"=== {timeframe} 时间框架数据统计 ===\n")
                    f.write(f"总行数: {len(df)}\n")
                    if not df.empty:
                        f.write(f"时间范围: {df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}\n")
                    f.write(f"请求次数: {request_count}\n")
                    f.write(f"数据点分布:\n")
                    # 写入前10行和后10行数据用于检查
                    f.write("\n前10行数据:\n")
                    f.write(df.head(10).to_string())
                    f.write("\n\n后10行数据:\n")
                    f.write(df.tail(10).to_string())
                logger.info(f"数据分析信息已保存到 {log_file_path}")
                
                # 转换数据类型
                # 安全地转换时间戳，避免无效值
                df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms', errors='coerce')
                # 过滤掉无效的时间戳
                df = df.dropna(subset=['timestamp'])
                df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
                df['volume'] = df['volume'].astype(float)
                
                # 过滤掉超出指定时间范围的数据
                start_datetime = pd.to_datetime(start_time, unit='ms')
                end_datetime = pd.to_datetime(end_time, unit='ms')
                original_len = len(df)
                df = df[(df['timestamp'] >= start_datetime) & (df['timestamp'] <= end_datetime)]
                filtered_count = original_len - len(df)
                if filtered_count > 0:
                    logger.info(f"过滤掉{filtered_count}条超出时间范围的数据，剩余{len(df)}条")
                
                # 重命名列以匹配策略期望的格式
                df = df.rename(columns={
                    'timestamp': 'datetime',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume'
                })
                
                # 只保留需要的列
                df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
                
                logger.info(f"成功获取{timeframe}数据，共{len(df)}条")
                return df
            else:
                logger.warning(f"未获取到{timeframe}数据")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取历史数据时出错: {str(e)}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return pd.DataFrame()
    
    def prepare_backtest_data(self):
        """准备回测数据，获取指定时间范围的多时间框架K线"""
        logger.info("开始准备回测数据...")
        
        # 设置固定时间范围：20250101 往后3个月
        start_date = datetime(2025, 1, 1)
        # 计算3个月后的日期
        end_date = start_date + timedelta(days=240)  # 简化计算，使用90天近似3个月
        
        # 转换为毫秒时间戳
        end_time_ms = int(end_date.timestamp() * 1000)
        start_time_ms = int(start_date.timestamp() * 1000)
        
        # 使用配置中的时间范围
        logger.info(f"使用配置的回测时间范围: {start_date} 至 {end_date}")
        
        # 获取策略所需的时间框架
        strategy_timeframes = self.strategy.get_required_timeframes()
        logger.info(f"策略需要的时间框架: {list(strategy_timeframes.keys())}")
        
        # 创建时间框架映射（策略时间框架 -> API时间框架）
        for tf in strategy_timeframes.keys():
            if tf.endswith('h'):
                self.api_timeframe_map[tf] = tf.replace('h', 'H')
            elif tf.endswith('m'):
                self.api_timeframe_map[tf] = tf
            elif tf.endswith('d'):
                self.api_timeframe_map[tf] = tf.replace('d', 'D')
            else:
                self.api_timeframe_map[tf] = tf
        
        logger.info(f"时间框架映射关系: {self.api_timeframe_map}")
        
        # 获取每个时间框架的数据
        for strategy_tf, api_tf in self.api_timeframe_map.items():
            logger.info(f"正在获取{strategy_tf} (API: {api_tf}) 时间框架的数据...")
            df = self.fetch_historical_data(api_tf, start_time_ms, end_time_ms)
            if not df.empty:
                self.timeframe_data[api_tf] = df
                logger.info(f"成功获取{strategy_tf}数据，共{len(df)}条记录")
            else:
                logger.error(f"无法获取{strategy_tf} ({api_tf}) 数据，回测无法继续")
                return False
        
        return True
    
    def validate_timeframe_continuity(self):
        """校验所有时间框架数据是否连续
        
        检查每个时间框架的K线数据是否连续，允许一定的容差范围。
        
        Returns:
            bool: 所有时间框架数据都连续返回True，否则返回False
        """
        logger.info("开始校验时间框架数据连续性...")
        
        # 定义每个时间框架的预期间隔（秒）和允许的容差（秒）
        timeframe_intervals = {
            '15m': {'expected': 15 * 60, 'tolerance': 30},  # 15分钟，允许30秒容差
            '1H': {'expected': 60 * 60, 'tolerance': 60},   # 1小时，允许60秒容差
            '4H': {'expected': 4 * 60 * 60, 'tolerance': 120}  # 4小时，允许120秒容差
        }
        
        all_continuous = True
        
        # 校验每个时间框架的数据连续性
        for api_tf, df in self.timeframe_data.items():
            if df.empty:
                logger.error(f"时间框架{api_tf}数据为空")
                all_continuous = False
                continue
            
            logger.info(f"校验{api_tf}时间框架数据连续性...")
            
            # 获取对应的预期间隔和容差
            interval_info = timeframe_intervals.get(api_tf)
            
            if not interval_info:
                logger.warning(f"未定义{api_tf}的时间间隔信息，跳过校验")
                continue
            
            expected_interval = interval_info['expected']
            tolerance = interval_info['tolerance']
            
            # 计算相邻K线的时间差（秒）
            df['time_diff'] = df['datetime'].diff().dt.total_seconds()
            
            # 找出不连续的K线（跳过第一条记录的NaN值）
            gaps = df.iloc[1:][
                (df['time_diff'] < (expected_interval - tolerance)) | 
                (df['time_diff'] > (expected_interval + tolerance))
            ]
            
            if not gaps.empty:
                logger.error(f"在{api_tf}时间框架中发现{gaps.shape[0]}个不连续的K线数据点")
                
                # 记录前5个不连续的点作为示例
                for idx, row in gaps.head().iterrows():
                    prev_time = df['datetime'].iloc[idx-1]
                    curr_time = df['datetime'].iloc[idx]
                    logger.error(f"  位置{idx}: {prev_time} -> {curr_time}, 时间差: {row['time_diff']:.2f}秒")
                
                all_continuous = False
            else:
                logger.info(f"✅ {api_tf}时间框架数据连续性校验通过")
                
                # 记录数据统计信息
                logger.info(f"  数据点数: {len(df)}")
                logger.info(f"  时间范围: {df['datetime'].iloc[0]} 至 {df['datetime'].iloc[-1]}")
                
                # 计算并记录平均时间间隔
                avg_interval = df['time_diff'].mean()
                logger.info(f"  平均时间间隔: {avg_interval:.2f}秒 (预期: {expected_interval}秒)")
        
        if all_continuous:
            logger.info("✅ 所有时间框架数据连续性校验通过")
        else:
            logger.error("❌ 时间框架数据连续性校验失败")
        
        return all_continuous

    def run_backtest(self):
        """运行回测"""
        logger.info("开始回测...")
        
        # 准备回测数据
        if not self.prepare_backtest_data():
            return
        # 以最细粒度的时间框架（15分钟）作为回测的基准
        base_tf = '15m'
        base_df = self.timeframe_data.get(base_tf)
        
        if base_df is None or base_df.empty:
            logger.error("无法获取15分钟时间框架数据，回测无法继续")
            return
        
        logger.info(f"回测数据点数 (15分钟): {len(base_df)}")
        logger.info(f"数据时间范围: {base_df['datetime'].iloc[0]} 至 {base_df['datetime'].iloc[-1]}")
        
        # 回测主循环 - 只在15分钟时间框架上迭代
        logger.info(f"开始回测主循环，将处理从索引168到{len(base_df)-1}的15分钟数据点")
        
        # 为每个时间框架建立时间戳到索引的映射，提高查找效率
        tf_index_maps = {}
        for api_tf, df in self.timeframe_data.items():
            # 将时间戳转换为datetime对象并创建映射
            tf_index_maps[api_tf] = {}
            for idx, dt in enumerate(df['datetime']):
                tf_index_maps[api_tf][dt] = idx
        
        # 校验所有时间框架数据是否连续
        # if not self.validate_timeframe_continuity():
        #     logger.error("时间框架数据连续性校验失败，回测无法继续")
        #     return
        # logger.debug(f"校验完成")

        for i in range(168, len(base_df)):  # 跳过前168个数据点，确保有足够的历史数据计算指标
            logger.debug(f"迭代索引: {i}/{len(base_df)-1}")
            
            # 获取当前15分钟K线的时间
            current_time_15m = base_df['datetime'].iloc[i]
            
            # 为每个时间框架提取当前时间点对应的数据窗口
            current_data = {}
            
            for api_tf, df in self.timeframe_data.items():
                # 将API时间框架转换回策略时间框架
                strategy_tf = None
                for stf, atf in self.api_timeframe_map.items():
                    if atf == api_tf:
                        strategy_tf = stf
                        break
                
                if not strategy_tf:
                    logger.warning(f"无法找到{api_tf}对应的策略时间框架")
                    continue
                
                # 获取该时间框架需要的数据长度
                window_size = self.strategy.get_required_timeframes().get(strategy_tf, 168)
                
                # 查找当前15分钟时间对应的该时间框架的索引
                # 对于1小时和4小时时间框架，我们需要找到不晚于当前15分钟时间的最新K线
                closest_idx = None
                
                # 使用预构建的索引映射进行查找
                if api_tf in tf_index_maps:
                    # 查找不晚于current_time_15m的最新时间戳
                    valid_times = [dt for dt in tf_index_maps[api_tf].keys() if dt <= current_time_15m]
                    if valid_times:
                        closest_time = max(valid_times)
                        closest_idx = tf_index_maps[api_tf][closest_time]
                
                # 如果没有找到对应的索引，使用二分查找作为备选
                if closest_idx is None:
                    # 使用二分查找找到不大于current_time_15m的最大索引
                    closest_idx = df['datetime'].searchsorted(current_time_15m, side='right') - 1
                
                # 确保索引有效
                if closest_idx >= 0:
                    # 计算起始索引
                    start_idx = max(0, closest_idx - window_size + 1)
                    current_data[strategy_tf] = df.iloc[start_idx:closest_idx+1].copy()
                    
                    # 验证数据窗口大小
                    if len(current_data[strategy_tf]) < window_size:
                        logger.warning(f"{strategy_tf}时间框架数据窗口不足，当前{len(current_data[strategy_tf])}条，需要{window_size}条")
                else:
                    logger.warning(f"无法找到{strategy_tf}时间框架中对应{current_time_15m}的K线")
                    continue
            
            # 验证是否获取了所有需要的时间框架数据
            required_tfs = set(self.strategy.get_required_timeframes().keys())
            current_tfs = set(current_data.keys())
            missing_tfs = required_tfs - current_tfs
            if missing_tfs:
                logger.warning(f"缺少以下时间框架的数据: {missing_tfs}")
                continue
            
            # 添加详细日志来验证时间框架数据的对应关系
            logger.debug(f"【时间框架数据验证】")
            # 获取基准时间（15m时间框架的当前时间）
            base_time = None
            if '15m' in current_data:
                base_time = current_data['15m']['datetime'].iloc[-1]
            
            # 记录每个时间框架的数据时间范围和最新时间点
            for tf, df in current_data.items():
                # 获取数据的时间范围
                data_start_time = df['datetime'].min()
                data_end_time = df['datetime'].max()
                latest_time = df['datetime'].iloc[-1]
                latest_close = df['close'].iloc[-1]
                
                # 计算与基准时间的时间差（如果有基准时间）
                time_diff = None
                if base_time:
                    time_diff = (base_time - latest_time).total_seconds() / 60  # 转换为分钟
                
                logger.debug(f"  - {tf}时间框架:")
                logger.debug(f"    数据范围: {data_start_time} 至 {data_end_time}")
                logger.debug(f"    数据点数: {len(df)} 条")
                logger.debug(f"    最新K线: 时间={latest_time}, 收盘价={latest_close}")
                if time_diff is not None:
                    logger.debug(f"    与基准时间差: {time_diff:.2f} 分钟")
                    # 检查时间差异是否合理
                    if tf == '15m' and abs(time_diff) > 7.5:  # 15分钟K线允许50%偏差
                        logger.warning(f"    ⚠️  {tf}时间框架与基准时间差异过大: {time_diff:.2f}分钟")
                    elif tf == '1h' and abs(time_diff) > 60:  # 1小时K线允许50%偏差
                        logger.warning(f"    ⚠️  {tf}时间框架与基准时间差异过大: {time_diff:.2f}分钟")
                    elif tf == '4h' and abs(time_diff) > 240:  # 4小时K线允许50%偏差
                        logger.warning(f"    ⚠️  {tf}时间框架与基准时间差异过大: {time_diff:.2f}分钟")
            
            # 获取当前价格、最高价、最低价和时间（优先使用15m时间框架的数据，以获得更细粒度的日志记录）
            if '15m' in current_data:
                current_price = current_data['15m']['close'].iloc[-1]
                current_high = current_data['15m']['high'].iloc[-1]
                current_low = current_data['15m']['low'].iloc[-1]
                current_date = current_data['15m']['datetime'].iloc[-1]
            elif '1h' in current_data:
                current_price = current_data['1h']['close'].iloc[-1]
                current_high = current_data['1h']['high'].iloc[-1]
                current_low = current_data['1h']['low'].iloc[-1]
                current_date = current_data['1h']['datetime'].iloc[-1]
            elif current_data:
                # 如果没有15m和1h数据，使用第一个可用时间框架的数据
                first_tf = list(current_data.keys())[0]
                current_price = current_data[first_tf]['close'].iloc[-1]
                current_high = current_data[first_tf]['high'].iloc[-1]
                current_low = current_data[first_tf]['low'].iloc[-1]
                current_date = current_data[first_tf]['datetime'].iloc[-1]
                logger.warning(f"使用{first_tf}时间框架作为价格和时间参考")
            else:
                logger.error("没有可用的时间框架数据，跳过当前迭代")
                continue
            
            # 记录当前迭代的基本信息
            logger.info(f"[{current_date}] 迭代索引: {i}/{len(base_df)-1}, 处理数据点")
            # 记录各时间框架的最新收盘价，便于比较价格一致性
            price_info = []
            for tf in sorted(current_data.keys()):
                price = current_data[tf]['close'].iloc[-1]
                price_info.append(f"{tf}:{price:.2f}")
            # logger.info(f"  当前价格各时间框架: {', '.join(price_info)}")
            
            #反转current_data的下每个k线的顺序
            # current_data2 = {tf: df.sort_values('datetime', ascending=False).reset_index(drop=True) for tf, df in current_data.items()}
            # 使用策略生成信号
            signal = self.strategy.analyze(self.symbol, current_data)

            # filter_trade_signals 过滤交易信号
            signal = [signal]
            signal = self.strategy.filter_trade_signals(signal)
            if signal:
                signal = signal[0]

            # 记录生成的信号详情
            if signal:
                # 获取15分钟时间框架的信号
                signal_trigger_timeframe = self.strategy.config.get('SIGNAL_TRIGGER_TIMEFRAME', '15m')
                
                logger.info(f"[{current_date}] 生成信号: 操作={signal.overall_action}, 评分={signal.total_score:.3f}")
                
                # 记录各个时间框架的信号，便于分析信号一致性
                logger.debug("  各时间框架信号详情:")
                for tf in sorted(current_data.keys()):
                    # 构建对应的属性名（例如：4h -> h4_signal）
                    attr_name = None
                    if tf == '4h':
                        attr_name = 'h4_signal'
                    elif tf == '1h':
                        attr_name = 'h1_signal'
                    elif tf == '15m':
                        attr_name = 'm15_signal'
                    else:
                        attr_name = f'{tf}_signal'
                    
                    tf_signal = getattr(signal, attr_name, '未知')
                    is_trigger_signal = "(触发信号)" if tf == signal_trigger_timeframe else ""
                    logger.debug(f"  - {tf}: {tf_signal} {is_trigger_signal}")
            else:
                logger.info(f"[{current_date}] 未生成信号")
            
            # 执行交易（模拟记录，不调用实际API）
            if signal:
                # 获取15分钟时间框架的信号
              
                if signal.overall_action == "买入" and self.position == 0:
                    # 全仓买入（模拟）
                    self.position = self.capital / current_price  # 多仓为正数
                    self.entry_price = current_price
                    self.stop_loss = signal.stop_loss  # 记录仓位的止损价格
                    self.take_profit = signal.target_short  # 记录仓位的止盈价格
                    
                    # 记录模拟交易
                    trade = {
                        'type': 'BUY',
                        'date': current_date,
                        'price': current_price,
                        'amount': self.position,
                        'capital': self.capital,
                        'stop_loss': signal.stop_loss,
                        'target': signal.target_short,
                        'signal_score': signal.total_score,
                        'timeframe_signals': {}
                    }
                    
                    # 记录各个时间框架的信号
                    for tf in current_data.keys():
                        trade['timeframe_signals'][tf] = getattr(signal, f'{tf.replace("4h", "h4").replace("1h", "h1").replace("15m", "m15")}_signal', '未知')
                    
                    self.trades.append(trade)
                    logger.info(f"[{current_date}] 模拟买入信号: {current_price:.2f}, 持仓数量: {self.position:.6f}, 信号评分: {signal.total_score:.3f}")
                
                # 卖出信号且当前有持仓，同时检查15分钟时间框架信号
                elif signal.overall_action == "卖出" and self.position > 0:
                    # 全仓卖出（模拟）
                    self.capital = self.position * current_price
                    profit = self.capital - self.initial_capital
                    profit_rate = (profit / self.initial_capital) * 100
                    trade_profit = self.capital - (self.position * self.entry_price)
                    
                    trade = {
                        'type': 'SELL',
                        'date': current_date,
                        'price': current_price,
                        'amount': self.position,
                        'capital': self.capital,
                        'profit': profit,
                        'profit_rate': profit_rate,
                        'trade_profit': trade_profit,
                        'trade_profit_rate': (trade_profit / (self.position * self.entry_price)) * 100,
                        'signal_score': signal.total_score,
                        'timeframe_signals': {}
                    }
                    
                    # 记录各个时间框架的信号
                    for tf in current_data.keys():
                        trade['timeframe_signals'][tf] = getattr(signal, f'{tf.replace("4h", "h4").replace("1h", "h1").replace("15m", "m15")}_signal', '未知')
                    
                    self.trades.append(trade)
                    logger.info(f"[{current_date}] 模拟卖出信号: {current_price:.2f}, 当前资金: {self.capital:.2f}, 总收益: {profit_rate:.2f}%, 单笔收益: {trade_profit:.2f}")
                    
                    # 重置持仓
                    self.position = 0
                    self.entry_price = 0.0
                    self.stop_loss = 0.0  # 重置止损价格
                    self.take_profit = 0.0  # 重置止盈价格
            
            # 检查止损止盈 - 每根K线都检查
            if self.position > 0:
                # 检查止损 - 多仓情况
                if current_low <= self.stop_loss:
                    # 触发止损（模拟）- 多仓
                    self.capital = self.position * current_price
                    profit = self.capital - self.initial_capital
                    profit_rate = (profit / self.initial_capital) * 100
                    trade_profit = self.capital - (self.position * self.entry_price)
                    
                    trade = {
                        'type': 'STOP_LOSS',
                        'date': current_date,
                        'price': current_price,
                        'amount': self.position,
                        'capital': self.capital,
                        'profit': profit,
                        'profit_rate': profit_rate,
                        'trade_profit': trade_profit,
                        'trade_profit_rate': (trade_profit / (self.position * self.entry_price)) * 100,
                        'stop_loss_price': self.stop_loss
                    }
                    self.trades.append(trade)
                    logger.info(f"[{current_date}] 触发止损(多仓): {current_price:.2f}, 止损价: {self.stop_loss:.2f}, 当前资金: {self.capital:.2f}, 总收益: {profit_rate:.2f}%")
                    
                    # 重置持仓
                    self.position = 0
                    self.entry_price = 0.0
                    self.stop_loss = 0.0
                    self.take_profit = 0.0
                
                # 检查止盈 - 多仓情况
                elif current_high >= self.take_profit:
                    # 触发止盈（模拟）- 多仓
                    self.capital = self.position * current_price
                    profit = self.capital - self.initial_capital
                    profit_rate = (profit / self.initial_capital) * 100
                    trade_profit = self.capital - (self.position * self.entry_price)
                    
                    trade = {
                        'type': 'TAKE_PROFIT',
                        'date': current_date,
                        'price': current_price,
                        'amount': self.position,
                        'capital': self.capital,
                        'profit': profit,
                        'profit_rate': profit_rate,
                        'trade_profit': trade_profit,
                        'trade_profit_rate': (trade_profit / (self.position * self.entry_price)) * 100,
                        'target_price': self.take_profit
                    }
                    self.trades.append(trade)
                    logger.info(f"[{current_date}] 触发止盈(多仓): {current_price:.2f}, 目标价: {self.take_profit:.2f}, 当前资金: {self.capital:.2f}, 总收益: {profit_rate:.2f}%")
                    
                    # 重置持仓
                    self.position = 0
                    self.entry_price = 0.0
                    self.stop_loss = 0.0
                    self.take_profit = 0.0
            
            elif self.position < 0:
                # 检查止损 - 空仓情况
                if current_high >= self.stop_loss:
                    # 触发止损（模拟）- 空仓
                    # 计算当前资本：持仓数量 * 当前价格
                    self.capital = abs(self.position) * current_price
                    # 计算总收益
                    profit = self.capital - self.initial_capital
                    # 计算收益率
                    profit_rate = (profit / self.initial_capital) * 100
                    # 计算本次交易的盈利
                    trade_profit = self.capital - (abs(self.position) * self.entry_price)
                    
                    # 创建交易记录
                    trade = {
                        'type': 'STOP_LOSS',
                        'date': current_date,
                        'price': current_price,
                        'amount': abs(self.position),
                        'capital': self.capital,
                        'profit': profit,
                        'profit_rate': profit_rate,
                        'trade_profit': trade_profit,
                        'trade_profit_rate': (trade_profit / (abs(self.position) * self.entry_price)) * 100,
                        'stop_loss_price': self.stop_loss
                    }
                    self.trades.append(trade)
                    logger.info(f"[{current_date}] 触发止损(空仓): {current_price:.2f}, 止损价: {self.stop_loss:.2f}, 当前资金: {self.capital:.2f}, 总收益: {profit_rate:.2f}%")
                    
                    # 重置持仓
                    self.position = 0
                    self.entry_price = 0.0
                    self.stop_loss = 0.0
                    self.take_profit = 0.0
                    
                # 检查止盈 - 空仓情况
                elif current_low <= self.take_profit:
                    # 触发止盈（模拟）- 空仓
                    # 计算当前资本：持仓数量 * 当前价格
                    self.capital = abs(self.position) * current_price
                    # 计算总收益
                    profit = self.capital - self.initial_capital
                    # 计算收益率
                    profit_rate = (profit / self.initial_capital) * 100
                    # 计算本次交易的盈利
                    trade_profit = self.capital - (abs(self.position) * self.entry_price)
                    
                    # 创建交易记录
                    trade = {
                        'type': 'TAKE_PROFIT',
                        'date': current_date,
                        'price': current_price,
                        'amount': abs(self.position),
                        'capital': self.capital,
                        'profit': profit,
                        'profit_rate': profit_rate,
                        'trade_profit': trade_profit,
                        'trade_profit_rate': (trade_profit / (abs(self.position) * self.entry_price)) * 100,
                        'target_price': self.take_profit
                    }
                    self.trades.append(trade)
                    logger.info(f"[{current_date}] 触发止盈(空仓): {current_price:.2f}, 目标价: {self.take_profit:.2f}, 当前资金: {self.capital:.2f}, 总收益: {profit_rate:.2f}%")
                    
                    # 重置持仓
                    self.position = 0
                    self.entry_price = 0.0
                    self.stop_loss = 0.0
                    self.take_profit = 0.0
        
        # 回测结束，如果仍有持仓则平仓
        if self.position > 0:
            logger.info("回测结束，处理剩余持仓...")
            latest_data = {}
            for api_tf, df in self.timeframe_data.items():
                # 将API时间框架转换回策略时间框架
                strategy_tf = None
                for stf, atf in self.api_timeframe_map.items():
                    if atf == api_tf:
                        strategy_tf = stf
                        break
                
                if strategy_tf:
                    window_size = self.strategy.get_required_timeframes().get(strategy_tf, 168)
                    start_idx = max(0, len(base_df) - window_size)
                    latest_data[strategy_tf] = df.iloc[start_idx:len(base_df)].copy()
            
            logger.info(f"处理剩余持仓，使用的最新时间框架数据: {list(latest_data.keys())}")
            
            # 优先使用15m时间框架的数据，然后是1h，最后是其他时间框架
            if '15m' in latest_data:
                final_price = latest_data['15m']['close'].iloc[-1]
                final_date = latest_data['15m']['datetime'].iloc[-1]
            elif '1h' in latest_data:
                final_price = latest_data['1h']['close'].iloc[-1]
                final_date = latest_data['1h']['datetime'].iloc[-1]
            else:
                # 使用第一个可用的时间框架
                final_price = list(latest_data.values())[0]['close'].iloc[-1]
                final_date = list(latest_data.values())[0]['datetime'].iloc[-1]
            
            self.capital = self.position * final_price
            profit = self.capital - self.initial_capital
            profit_rate = (profit / self.initial_capital) * 100
            
            trade = {
                'type': 'CLOSE_POSITION',
                'date': final_date,
                'price': final_price,
                'amount': self.position,
                'capital': self.capital,
                'profit': profit,
                'profit_rate': profit_rate
            }
            self.trades.append(trade)
            logger.info(f"[{final_date}] 回测结束，平仓: {final_price:.2f}, 最终资金: {self.capital:.2f}, 总收益: {profit_rate:.2f}%")
        
        # 生成回测报告
        self.generate_report()
    
    def generate_report(self):
        """生成回测报告"""
        logger.info("\n===== BTC多时间框架策略回测报告 =====")
        logger.info(f"初始资金: {self.initial_capital:.2f} USDT")
        logger.info(f"最终资金: {self.capital:.2f} USDT")
        
        total_profit = self.capital - self.initial_capital
        total_profit_rate = (total_profit / self.initial_capital) * 100
        logger.info(f"总收益: {total_profit:.2f} USDT ({total_profit_rate:.2f}%)")
        
        # 计算交易统计
        buy_trades = len([t for t in self.trades if t['type'] == 'BUY'])
        sell_trades = len([t for t in self.trades if t['type'] == 'SELL'])
        stop_loss_trades = len([t for t in self.trades if t['type'] == 'STOP_LOSS'])
        take_profit_trades = len([t for t in self.trades if t['type'] == 'TAKE_PROFIT'])
        close_position_trades = len([t for t in self.trades if t['type'] == 'CLOSE_POSITION'])
        
        logger.info(f"交易统计:")
        logger.info(f"  - 买入次数: {buy_trades}")
        logger.info(f"  - 卖出次数: {sell_trades + stop_loss_trades + take_profit_trades + close_position_trades}")
        logger.info(f"  - 止损次数: {stop_loss_trades}")
        logger.info(f"  - 止盈次数: {take_profit_trades}")
        logger.info(f"  - 回测结束平仓次数: {close_position_trades}")
        
        # 计算胜率
        winning_trades = 0
        losing_trades = 0
        total_trade_profit = 0
        
        for trade in self.trades:
            if trade['type'] in ['SELL', 'TAKE_PROFIT', 'STOP_LOSS', 'CLOSE_POSITION']:
                if 'trade_profit' in trade:
                    total_trade_profit += trade['trade_profit']
                    if trade['trade_profit'] > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1
        
        total_completed_trades = winning_trades + losing_trades
        win_rate = (winning_trades / total_completed_trades * 100) if total_completed_trades > 0 else 0
        
        logger.info(f"\n绩效统计:")
        logger.info(f"  - 胜率: {win_rate:.2f}% ({winning_trades}/{total_completed_trades})")
        logger.info(f"  - 总交易收益: {total_trade_profit:.2f} USDT")
        
        # 记录多时间框架使用情况
        logger.info(f"\n多时间框架使用情况:")
        logger.info(f"  - 使用的时间框架: {list(self.api_timeframe_map.keys())}")
        
        # 保存交易记录（模拟记录）
        if self.trades:
            # 创建结果目录 - 使用绝对路径确保在strategies_test目录下
            base_reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
            # 创建年月日时分秒格式的子文件夹
            timestamp_dir = datetime.now().strftime('%Y%m%d_%H%M%S')
            reports_dir = os.path.join(base_reports_dir, timestamp_dir, 'multi_timeframe_reports')
            os.makedirs(reports_dir, exist_ok=True)
            report_filename = os.path.join(reports_dir, f'{self.symbol}_backtest_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            
            with open(report_filename, 'w', encoding='utf-8') as f:
                # 将datetime转换为字符串以便JSON序列化
                serializable_trades = []
                for trade in self.trades:
                    serializable_trade = trade.copy()
                    if isinstance(serializable_trade['date'], pd.Timestamp):
                        serializable_trade['date'] = serializable_trade['date'].strftime('%Y-%m-%d %H:%M:%S')
                    serializable_trades.append(serializable_trade)
                
                # 添加回测元数据
                backtest_results = {
                    'metadata': {
                        'strategy': 'MultiTimeframeStrategy',
                        'symbol': self.symbol,
                        'initial_capital': self.initial_capital,
                        'final_capital': self.capital,
                        'total_profit': total_profit,
                        'total_profit_rate': total_profit_rate,
                        'win_rate': win_rate,
                        'backtest_start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'timeframes_used': list(self.api_timeframe_map.keys())
                    },
                    'trades': serializable_trades
                }
                
                json.dump(backtest_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"模拟交易记录已保存到: {report_filename}")
            logger.info("注意: 所有交易均为模拟记录，未调用实际的OKX API进行真实交易")


if __name__ == "__main__":
    logger.info("启动多交易对多时间框架策略回测")
    logger.info("注意: 本回测使用模拟记录方式，不会调用实际的OKX仓位API")
    
    # 遍历每个交易对执行回测
    for symbol in symbols:
        logger.info(f"开始交易对 {symbol} 的回测")
        
        # 创建回测引擎
        backtest = BacktestEngine(
            strategy_class=MultiTimeframeStrategy,
            initial_capital=10000.0,
            symbol=symbol
        )
        
        # 运行回测
        backtest.run_backtest()
        
        logger.info(f"交易对 {symbol} 回测完成")
    
    logger.info("所有交易对回测完成")
    logger.info("所有交易均为模拟记录，已保存到reports/multi_timeframe_reports目录")