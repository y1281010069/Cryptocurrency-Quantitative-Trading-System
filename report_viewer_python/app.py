from flask import Flask, render_template, request, jsonify
import re
import os
import sys
import json
import time
import ccxt
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 尝试导入配置
config = None
try:
    # 先尝试导入Config类（适配app.py的期望结构）
    from config import Config
    config = Config()
except ImportError:
    try:
        # 如果没有Config类，尝试直接导入配置变量（适配config_template.py的结构）
        from config import API_KEY, SECRET_KEY, PASSPHRASE, OKX_CONFIG
        class ImportedConfig:
            def __init__(self):
                self.okx_api_key = API_KEY or OKX_CONFIG.get('api_key', '')
                self.okx_api_secret = SECRET_KEY or OKX_CONFIG.get('secret', '')
                self.okx_api_passphrase = PASSPHRASE or OKX_CONFIG.get('passphrase', '')
                self.use_official_api = OKX_CONFIG.get('use_official_api', False)
        config = ImportedConfig()
        print("信息: 从config.py成功导入配置变量")
    except ImportError:
        print("警告: 无法导入config.py文件，将使用默认配置")
        # 创建一个默认配置类
        class DefaultConfig:
            def __init__(self):
                # 使用与env.example和config_template.py一致的环境变量名称
                self.okx_api_key = os.environ.get('OKX_API_KEY', '')
                self.okx_api_secret = os.environ.get('OKX_SECRET_KEY', '')
                self.okx_api_passphrase = os.environ.get('OKX_PASSPHRASE', '')
                self.use_official_api = False
        config = DefaultConfig()

app = Flask(__name__)

# 配置默认的报告文件路径
DEFAULT_REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'multi_timeframe_reports', 'multi_timeframe_analysis_new.txt')

# 初始化OKX交易所连接
okx_exchange = None
def init_okx_exchange():
    """初始化OKX交易所连接"""
    global okx_exchange
    try:
        print("=== 开始初始化OKX交易所连接 ===")
        # 检查API密钥是否已配置
        has_key = bool(config.okx_api_key)
        has_secret = bool(config.okx_api_secret)
        has_passphrase = bool(config.okx_api_passphrase)
        
        print(f"API密钥配置状态: key={has_key}, secret={has_secret}, passphrase={has_passphrase}")
        print(f"API密钥长度: key={len(config.okx_api_key) if has_key else 0}, secret={len(config.okx_api_secret) if has_secret else 0}, passphrase={len(config.okx_api_passphrase) if has_passphrase else 0}")
        
        if not has_key or not has_secret or not has_passphrase:
            missing = []
            if not has_key: missing.append("API_KEY")
            if not has_secret: missing.append("API_SECRET")
            if not has_passphrase: missing.append("PASSPHRASE")
            print(f"警告: OKX API密钥未完全配置 - 缺少: {', '.join(missing)}，将使用模拟数据")
            return False
        
        # 创建OKX交易所实例
        print("正在创建OKX交易所实例...")
        okx_exchange = ccxt.okx({
            'apiKey': config.okx_api_key,
            'secret': config.okx_api_secret,
            'password': config.okx_api_passphrase,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        
        # 验证连接是否成功
        try:
            print("正在验证OKX连接...")
            okx_exchange.load_markets()
            print("OKX交易所连接成功 - 已成功加载市场数据")
            return True
        except Exception as e:
            print(f"OKX交易所连接失败: {e}")
            print(f"错误类型: {type(e).__name__}")
            okx_exchange = None
            return False
    except Exception as e:
        print(f"初始化OKX交易所连接时发生错误: {e}")
        print(f"错误类型: {type(e).__name__}")
        okx_exchange = None
        return False
    finally:
        print(f"=== OKX连接初始化完成 - 连接状态: {'已连接' if okx_exchange else '未连接'} ===")

# 初始化OKX连接
init_okx_exchange()


def parse_report_content(file_path=DEFAULT_REPORT_PATH):
    """解析报告文件内容并返回结构化数据"""
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"警告: 报告文件不存在 - {file_path}")
            # 返回包含错误信息的数据结构，不使用模拟数据
            error_data = {
                'analysisTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'timeframeDimensions': '周线→日线→4小时→1小时→15分钟',
                'totalOpportunities': 0,
                'error': f"报告文件不存在: {file_path}",
                'opportunities': []
            }
            return error_data
        
        # 记录文件修改时间，用于调试
        file_mtime = os.path.getmtime(file_path)
        print(f"读取文件: {file_path}, 最后修改时间: {datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 尝试使用不同的编码读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
        
        report_data = {
            'analysisTime': '',
            'timeframeDimensions': '',
            'totalOpportunities': 0,
            'opportunities': []
        }

        # 尝试使用更宽松的正则表达式解析报告头部
        # 我们不依赖于特定的符号和文本，而是寻找包含时间、维度和机会数量的部分
        time_match = re.search(r'鍒嗘瀽鏃堕棿:?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2})', content)
        if time_match:
            report_data['analysisTime'] = time_match.group(1).strip()
        else:
            report_data['analysisTime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        # 设置默认的时间框架维度
        report_data['timeframeDimensions'] = '周线→日线→4小时→1小时→15分钟'
        
        # 尝试从文件中提取机会数量
        opportunities_match = re.search(r'鍙戠幇鏈轰細:?\s*(\d+)', content)
        if opportunities_match:
            try:
                report_data['totalOpportunities'] = int(opportunities_match.group(1).strip())
            except:
                report_data['totalOpportunities'] = 0

        # 使用更宽松的正则表达式解析每个交易机会
        # 查找以"銆愭満浼?"或"【机会"开始的行
        opportunity_markers = re.finditer(r'(銆愭満浼?|【机会)\s*(\d+)\s*(銆?|】)', content)
        
        for marker_idx, marker in enumerate(opportunity_markers):
            # 获取匹配的所有组
            groups = marker.groups()
            # 提取需要的信息
            opportunity_type = groups[0]  # 銆愭満浼? 或 【机会
            try:
                rank = int(groups[1])  # 排名数字
            except:
                rank = marker_idx + 1
            closing_char = groups[2]  # 銆? 或 】
            
            # 获取当前匹配的结束位置
            end_pos = marker.end()
            
            # 查找下一个机会的开始位置
            next_opportunity_match = re.search(r'(銆愭満浼?|【机会)', content[end_pos:])
            
            # 确定当前机会的文本块范围
            if next_opportunity_match:
                block_end = end_pos + next_opportunity_match.start()
            else:
                block_end = len(content)
            
            # 提取当前机会的文本块
            block_text = content[end_pos:block_end]
            
            # 从文本块中提取交易对
            symbol_match = re.search(r'([A-Z0-9]+/[A-Z0-9]+)', block_text)
            if symbol_match:
                symbol = symbol_match.group(1)
            else:
                symbol = f'未知交易对_{rank}'
            
            # 提取建议动作
            action_match = re.search(r'(缁煎悎寤鸿:?|综合建议:?)\s*([^\n]+)', block_text)
            action = action_match.group(2).strip() if action_match else '未知'
            
            # 提取信心等级
            confidence_match = re.search(r'(淇″績绛夌骇:?|信心等级:?)\s*([^\n]+)', block_text)
            confidence = confidence_match.group(2).strip() if confidence_match else '未知'
            
            # 提取总评分，支持负数评分
            score_match = re.search(r'(鎬昏瘎鍒?|总评分:?)\s*(-?[\d.]+)', block_text)
            if score_match:
                try:
                    totalScore = float(score_match.group(2).strip())
                except:
                    totalScore = 0.0
            else:
                totalScore = 0.0
            
            # 提取当前价格，支持负数价格
            price_match = re.search(r'(褰撳墠浠锋牸:?|当前价格:?)\s*(-?[\d.]+)', block_text)
            if price_match:
                try:
                    currentPriceValue = float(price_match.group(2).strip())
                except:
                    currentPriceValue = 0.0
            else:
                currentPriceValue = 0.0
            
            # 提取多时间框架分析
            weeklyTrend = dailyTrend = h4Signal = h1Signal = m15Signal = '未知'
            timeframes_match = re.finditer(r'(鍛ㄧ嚎瓒嬪娍:?|周线趋势:?)\s*([^\n]+)', block_text)
            for tm in timeframes_match:
                weeklyTrend = tm.group(2).strip()
            
            timeframes_match = re.finditer(r'(鏃ョ嚎瓒嬪娍:?|日线趋势:?)\s*([^\n]+)', block_text)
            for tm in timeframes_match:
                dailyTrend = tm.group(2).strip()
            
            timeframes_match = re.finditer(r'(4灏忔椂淇″彿:?|4小时信号:?)\s*([^\n]+)', block_text)
            for tm in timeframes_match:
                h4Signal = tm.group(2).strip()
            
            timeframes_match = re.finditer(r'(1灏忔椂淇″彿:?|1小时信号:?)\s*([^\n]+)', block_text)
            for tm in timeframes_match:
                h1Signal = tm.group(2).strip()
            
            timeframes_match = re.finditer(r'(15鍒嗛挓淇″彿:?|15分钟信号:?)\s*([^\n]+)', block_text)
            for tm in timeframes_match:
                m15Signal = tm.group(2).strip()
            
            # 提取目标价格
            targetShort = stopLoss = 0.0
            
            # 提取短期目标 (现在是1.5倍ATR)
            target_match = re.search(r'(鐭湡鐩爣|短期目标).*?:?\s*(-?[\d.]+)', block_text)
            if target_match:
                try:
                    targetShort = float(target_match.group(2).strip())
                except:
                    pass
            
            # 提取止损价格 (现在是1倍ATR的反向价格)
            target_match = re.search(r'(姝㈡崯浠锋牸|止损价格).*?:?\s*(-?[\d.]+)', block_text)
            if target_match:
                try:
                    stopLoss = float(target_match.group(2).strip())
                except:
                    pass
            
            # 计算百分比变化
            try:
                shortPct = ((targetShort / currentPriceValue - 1) * 100) if currentPriceValue > 0 else 0.0
                stopPct = ((stopLoss / currentPriceValue - 1) * 100) if currentPriceValue > 0 else 0.0
                mediumPct = longPct = 0.0  # 不再使用中期和长期目标
            except (ValueError, ZeroDivisionError):
                shortPct = stopPct = mediumPct = longPct = 0.0
            
            # 提取分析依据
            reasoning_match = re.search(r'(鍒嗘瀽渚濇嵁:?|分析依据:?)\s*([^\n]+)', block_text)
            reasoning = reasoning_match.group(2).strip() if reasoning_match else '无'
            
            # 添加到机会列表
            report_data['opportunities'].append({
                'rank': rank,
                'symbol': symbol,
                'action': action,
                'confidence': confidence,
                'totalScore': totalScore,
                'currentPrice': currentPriceValue,
                'weeklyTrend': weeklyTrend,
                'dailyTrend': dailyTrend,
                'h4Signal': h4Signal,
                'h1Signal': h1Signal,
                'm15Signal': m15Signal,
                'targetShort': targetShort,
                'stopLoss': stopLoss,
                'reasoning': reasoning,
                'shortPct': round(shortPct, 1),
                'mediumPct': round(mediumPct, 1),
                'longPct': round(longPct, 1),
                'stopPct': round(stopPct, 1)
            })
        
        # 更新实际找到的机会数量
        report_data['totalOpportunities'] = len(report_data['opportunities'])
        
        # 如果没有找到交易机会，返回空列表
        if not report_data['opportunities']:
            report_data['totalOpportunities'] = 0
            
        return report_data
        
    except Exception as e:
        # 详细记录解析错误
        print(f"解析报告文件失败: {e}")
        
        # 尝试使用更宽松的解析方式或者直接返回错误信息
        try:
            # 读取文件内容作为错误信息的一部分
            with open(file_path, 'r', encoding='utf-8') as f:
                content_preview = f.read(500)  # 只读取前500个字符
            print(f"文件内容预览: {content_preview}")
        except Exception as read_error:
            print(f"读取文件内容失败: {read_error}")
            
        # 返回包含错误信息的特殊数据结构
        error_data = {
            'analysisTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timeframeDimensions': '周线→日线→4小时→1小时→15分钟',
            'totalOpportunities': 0,
            'error': str(e),
            'opportunities': []
        }
        
        # 如果出现解析错误，优先返回错误信息而不是模拟数据
        return error_data



def process_balance_asset(currency, balance_info, okx_exchange):
    """处理单个资产的余额信息"""
    # 获取资产价格（如果无法获取则默认为0）
    try:
        # 获取USDT价格
        if currency == 'USDT':
            price = 1.0
        else:
            # 尝试获取交易对的最新价格
            try:
                ticker = okx_exchange.fetch_ticker(f'{currency}/USDT')
                price = ticker['last'] if ticker else 0.0
            except Exception as ticker_error:
                print(f"获取{currency}/USDT价格失败: {ticker_error}")
                price = 0.0
    except:
        price = 0.0
    
    # 计算USDT价值
    usdt_value = balance_info['total'] * price
    
    # 确定资产类型
    asset_type = 'crypto'
    if currency in ['USD', 'EUR', 'JPY', 'CNY']:
        asset_type = 'fiat'
    elif currency in ['USDT', 'BUSD', 'USDC', 'DAI']:
        asset_type = 'stable'
    
    # 获取资产名称
    asset_name = get_asset_name(currency)
    
    # 返回处理后的资产信息
    return {
        'symbol': currency,
        'name': asset_name,
        'available': balance_info['free'],
        'frozen': balance_info['used'],
        'total': balance_info['total'],
        'usdtValue': usdt_value,
        'type': asset_type
    }


def get_okx_balance():
    """获取OKX交易所的账户余额数据"""
    print("=== 开始获取OKX余额数据 ===")
    # 如果没有成功连接到OKX或API密钥未配置，返回模拟数据
    if not okx_exchange:
        print("OKX连接状态: 未连接 - 将返回模拟数据")
        return get_mock_balance_data()
    else:
        print("OKX连接状态: 已连接 - 尝试获取真实余额数据")
    
    try:
        # 获取账户余额
        balances = okx_exchange.fetch_balance()
        
        # 准备返回数据
        result = {
            'total': 0.0,
            'available': 0.0,
            'positions': 0.0,
            'unrealizedPnl': 0.0,
            'assets': [],
            'recentTransactions': []
        }
        
        # 处理资产数据
        total_assets = 0.0
        
        # 打印balances对象结构信息用于调试
        print(f"OKX返回的余额数据类型: {type(balances).__name__}")
        print(f"余额数据包含的键: {list(balances.keys())}")
        
        # 检查是否存在'info'或其他可能包含真实数据的键
        if 'info' in balances and isinstance(balances['info'], dict):
            print(f"余额数据info字段包含的键: {list(balances['info'].keys())}")
        
        # 处理资产数据
        if isinstance(balances, dict):
            # 检查是否有更合适的数据结构
            if 'total' in balances and isinstance(balances['total'], dict):
                # 如果balances['total']是一个字典，可能是另一种数据格式
                print("检测到alternative balance format")
                for currency, amount in balances['total'].items():
                    # 构建balance_info字典
                    balance_info = {
                        'total': amount,
                        'free': balances.get('free', {}).get(currency, 0),
                        'used': balances.get('used', {}).get(currency, 0)
                    }
                    
                    # 跳过没有余额的资产
                    if balance_info['total'] <= 0: 
                        continue
                    
                    # 处理这个资产
                    asset_data = process_balance_asset(currency, balance_info, okx_exchange)
                    result['assets'].append(asset_data)
                    total_assets += asset_data['usdtValue']
            else:
                # 尝试原始的数据处理方式
                for currency, balance_info in balances.items():
                    # 跳过特定的非资产键
                    if currency in ['info', 'timestamp', 'datetime', 'free', 'used', 'total']:
                        continue
                    
                    # 确保balance_info是字典类型
                    if not isinstance(balance_info, dict):
                        print(f"警告: {currency}的余额信息不是字典类型，而是: {type(balance_info).__name__}")
                        continue
                    
                    # 检查必要的键是否存在
                    if 'total' not in balance_info:
                        print(f"警告: {currency}的余额信息中缺少'total'键，可用键: {list(balance_info.keys())}")
                        # 尝试从其他可能的键获取余额信息
                        if 'amount' in balance_info:
                            balance_info['total'] = balance_info['amount']
                        elif 'balance' in balance_info:
                            balance_info['total'] = balance_info['balance']
                        else:
                            continue  # 跳过无法获取余额的资产
                    
                    # 确保free和used键存在
                    if 'free' not in balance_info:
                        balance_info['free'] = balance_info['total']
                    if 'used' not in balance_info:
                        balance_info['used'] = 0
                    
                    # 跳过没有余额的资产
                    if balance_info['total'] <= 0: 
                        continue
                    
                    # 处理这个资产
                    asset_data = process_balance_asset(currency, balance_info, okx_exchange)
                    result['assets'].append(asset_data)
                    total_assets += asset_data['usdtValue']
            
        
        # 更新总资产信息
        result['total'] = total_assets
        # 改进available计算，考虑所有资产的可用余额的USDT价值
        result['available'] = sum(asset['available'] * (1 if asset['symbol'] == 'USDT' else (asset['usdtValue'] / asset['total'] if asset['total'] > 0 else 0)) for asset in result['assets'])
        
        # 按USDT价值排序资产
        result['assets'].sort(key=lambda x: x['usdtValue'], reverse=True)
        
        # 尝试获取最近交易（需要额外的API调用权限）
        try:
            # 获取最近的5条交易记录
            recent_orders = okx_exchange.fetch_closed_orders(limit=5)
            for order in recent_orders:
                if order['status'] == 'closed' and order['amount'] > 0:
                    # 确定交易类型
                    if order['side'] == 'buy':
                        type_text = 'buy'
                    elif order['side'] == 'sell':
                        type_text = 'sell'
                    else:
                        type_text = 'unknown'
                    
                    # 添加到最近交易列表
                    result['recentTransactions'].append({
                        'symbol': order['symbol'].split('/')[0],
                        'type': type_text,
                        'amount': order['amount'],
                        'price': order['price'],
                        'time': datetime.fromtimestamp(order['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    })
        except Exception as e:
            print(f"获取最近交易记录失败: {e}")
            # 继续执行，不影响主要功能
        
        return result
    except Exception as e:
        print(f"获取OKX余额数据失败: {e}")
        # 出错时返回模拟数据
        return get_mock_balance_data()

def get_mock_balance_data():
    """获取模拟的余额数据"""
    print("=== 获取模拟余额数据 ===")
    print("警告: 当前使用的是模拟数据，而不是真实的OKX账户数据")
    print("可能的原因:")
    print("1. API密钥未正确配置")
    print("2. OKX连接验证失败")
    print("3. 获取余额时API调用出错")
    print("请检查API密钥配置和网络连接状态")
    print("=========================")
    return {
        'total': 12345.67,
        'available': 8901.23,
        'positions': 3444.44,
        'unrealizedPnl': -123.45,
        'assets': [
            {'symbol': 'USDT', 'name': 'Tether', 'available': 5000.00, 'frozen': 200.00, 'total': 5200.00, 'usdtValue': 5200.00, 'type': 'stable'},
            {'symbol': 'BTC', 'name': 'Bitcoin', 'available': 0.1, 'frozen': 0.0, 'total': 0.1, 'usdtValue': 4500.00, 'type': 'crypto'},
            {'symbol': 'ETH', 'name': 'Ethereum', 'available': 1.5, 'frozen': 0.0, 'total': 1.5, 'usdtValue': 2300.00, 'type': 'crypto'},
            {'symbol': 'USD', 'name': 'US Dollar', 'available': 200.00, 'frozen': 0.0, 'total': 200.00, 'usdtValue': 200.00, 'type': 'fiat'},
            {'symbol': 'BUSD', 'name': 'Binance USD', 'available': 150.00, 'frozen': 0.0, 'total': 150.00, 'usdtValue': 150.00, 'type': 'stable'},
            {'symbol': 'SOL', 'name': 'Solana', 'available': 5.0, 'frozen': 0.0, 'total': 5.0, 'usdtValue': 130.50, 'type': 'crypto'},
            {'symbol': 'XRP', 'name': 'Ripple', 'available': 100.0, 'frozen': 0.0, 'total': 100.0, 'usdtValue': 65.17, 'type': 'crypto'},
            {'symbol': 'DOGE', 'name': 'Dogecoin', 'available': 1000.0, 'frozen': 0.0, 'total': 1000.0, 'usdtValue': 50.00, 'type': 'crypto'}
        ],
        'recentTransactions': [
            {'symbol': 'BTC', 'type': 'buy', 'amount': 0.05, 'price': 45000.00, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
            {'symbol': 'ETH', 'type': 'sell', 'amount': 0.5, 'price': 1533.00, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
            {'symbol': 'USDT', 'type': 'deposit', 'amount': 1000.00, 'price': 1.00, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
            {'symbol': 'SOL', 'type': 'buy', 'amount': 5.0, 'price': 26.10, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
            {'symbol': 'XRP', 'type': 'buy', 'amount': 100.0, 'price': 0.6517, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        ]
    }

def get_asset_name(symbol):
    """获取加密货币的完整名称"""
    asset_names = {
        'BTC': 'Bitcoin',
        'ETH': 'Ethereum',
        'USDT': 'Tether',
        'BUSD': 'Binance USD',
        'SOL': 'Solana',
        'XRP': 'Ripple',
        'DOGE': 'Dogecoin',
        'ADA': 'Cardano',
        'DOT': 'Polkadot',
        'LTC': 'Litecoin',
        'LINK': 'Chainlink',
        'UNI': 'Uniswap',
        'USDC': 'USD Coin',
        'DAI': 'Dai',
        'AVAX': 'Avalanche',
        'SOL': 'Solana',
        'DOT': 'Polkadot',
        'MATIC': 'Polygon',
        'SHIB': 'Shiba Inu',
        'TRX': 'Tron',
        'ATOM': 'Cosmos',
        'ALGO': 'Algorand',
        'XTZ': 'Tezos',
        'EOS': 'EOS',
        'XMR': 'Monero',
        'DASH': 'Dash',
        'ZEC': 'Zcash',
        'BCH': 'Bitcoin Cash',
        'ETC': 'Ethereum Classic',
        'BSV': 'Bitcoin SV',
        'FIL': 'Filecoin',
        'AAVE': 'Aave',
        'COMP': 'Compound',
        'MKR': 'Maker',
        'SNX': 'Synthetix',
        'YFI': 'Yearn Finance',
        'USD': 'US Dollar',
        'EUR': 'Euro',
        'JPY': 'Japanese Yen',
        'CNY': 'Chinese Yuan'
    }
    return asset_names.get(symbol, symbol)


@app.route('/')
def index():
    """主页面路由 - 多时间框架分析报告"""
    # 从URL参数获取报告文件路径
    report_path = request.args.get('file', DEFAULT_REPORT_PATH)
    # 解析报告数据
    report_data = parse_report_content(report_path)
    
    # 统计各类机会数量
    buy_count = len([op for op in report_data['opportunities'] if '买入' in op['action']])
    sell_count = len([op for op in report_data['opportunities'] if '卖出' in op['action']])
    watch_count = len([op for op in report_data['opportunities'] if '观望' in op['action']])
    
    # 渲染模板并传递数据
    return render_template('index.html', 
                          report_data=report_data,
                          buy_count=buy_count,
                          sell_count=sell_count,
                          watch_count=watch_count,
                          now=datetime.now())


@app.route('/api/data')
def api_data():
    """API接口，返回JSON格式的报告数据"""
    report_path = request.args.get('file', DEFAULT_REPORT_PATH)
    report_data = parse_report_content(report_path)
    return jsonify(report_data)


@app.route('/api/filter')
def filter_data():
    """API接口，根据筛选条件返回过滤后的数据"""
    # 获取筛选参数
    filter_type = request.args.get('type', 'all')
    search_term = request.args.get('search', '').lower().strip()
    
    # 解析报告数据
    report_path = request.args.get('file', DEFAULT_REPORT_PATH)
    report_data = parse_report_content(report_path)
    
    # 应用筛选条件
    filtered_opportunities = []
    
    for opportunity in report_data['opportunities']:
        # 应用操作类型筛选
        action_match = (filter_type == 'all' or filter_type in opportunity['action'])
        # 应用搜索筛选
        search_match = (search_term == '' or search_term in opportunity['symbol'].lower())
        
        if action_match and search_match:
            filtered_opportunities.append(opportunity)
    
    # 返回过滤后的数据
    return jsonify({
        'opportunities': filtered_opportunities,
        'total': len(filtered_opportunities)
    })


@app.route('/balance')
@app.route('/okx_balance')
def balance():
    """OKX余额查询页面路由"""
    return render_template('balance.html', now=datetime.now())


@app.route('/api/balance')
def api_balance():
    """API接口，返回OKX账户余额数据"""
    try:
        # 获取余额数据
        balance_data = get_okx_balance()
        return jsonify({
            'success': True,
            'data': balance_data
        })
    except Exception as e:
        print(f"获取余额数据时发生错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


if __name__ == '__main__':
    # 获取本地IP地址
    import socket
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except:
        local_ip = '127.0.0.1'
    
    # 打印启动信息
    print('=' * 80)
    print('多时间框架分析报告查看器 - Python版')
    print('=' * 80)
    print(f'本地访问地址: http://127.0.0.1:5000')
    print(f'局域网访问地址: http://{local_ip}:5000')
    print('')
    print('页面导航:')
    print('  - 多时间框架分析报告: /')
    print('  - OKX余额查询: /balance')
    print('')
    print('请在浏览器中打开上述地址查看报告和余额')
    print('手机查看请确保与电脑连接同一Wi-Fi网络，然后访问局域网地址')
    print('=' * 80)
    
    # 启动Flask应用（生产环境应使用专业Web服务器）
    app.run(host='0.0.0.0', debug=False)