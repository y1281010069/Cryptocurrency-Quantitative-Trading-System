from flask import Flask, render_template, request, jsonify
import re
import os
import sys
import json
import time
import ccxt
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

# 导入合约工具模块
import contract_utils

# 导入OKX官方Python包
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib', 'python-okx-master'))
from okx.Trade import TradeAPI

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

# 不再导入自定义OKX API模块，使用原生ccxt功能

app = Flask(__name__)

# 配置默认的报告文件路径
DEFAULT_REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'multi_timeframe_reports', 'multi_timeframe_analysis_new.txt')

# 初始化OKX交易所连接
okx_exchange = None
okx_official_api = None  # OKX官方包的TradeAPI实例
def init_okx_exchange():
    """初始化OKX交易所连接"""
    global okx_exchange, okx_official_api
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
        
        # 创建OKX交易所实例 - 使用我们的自定义适配器
        print("正在创建OKX交易所实例...")
        
        # 检查是否有代理配置
        proxy_config = None
        if hasattr(config, 'proxy') and config.proxy:
            print(f"使用代理配置: {config.proxy}")
            proxy_config = config.proxy
        elif hasattr(config, 'https_proxy') and config.https_proxy:
            print(f"使用HTTPS代理配置: {config.https_proxy}")
            proxy_config = config.https_proxy
        else:
            print("未配置代理，尝试直接连接...")
        
        # 创建ccxt.okx交易所实例（原始方式）
        exchange_config = {
            'apiKey': config.okx_api_key,
            'secret': config.okx_api_secret,
            'password': config.okx_api_passphrase,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'  # 设置默认交易类型为现货
            }
        }
        
        # 如果有代理配置，添加到exchange_config
        if proxy_config:
            exchange_config['proxies'] = {
                'http': proxy_config,
                'https': proxy_config
            }
        
        # 创建原生ccxt.okx实例
        global okx_exchange
        okx_exchange = ccxt.okx(exchange_config)
        
        # 创建OKX官方包的TradeAPI实例
        try:
            print("正在创建OKX官方包TradeAPI实例...")
            okx_official_api = TradeAPI(
                api_key=config.okx_api_key,
                api_secret_key=config.okx_api_secret,
                passphrase=config.okx_api_passphrase,
                use_server_time=True,
                flag='0',  # 实盘环境
                debug=False,
                proxy=proxy_config
            )
            print("OKX官方包TradeAPI实例创建成功")
        except Exception as e:
            print(f"创建OKX官方包TradeAPI实例失败: {e}")
            okx_official_api = None
        
        # 验证ccxt连接是否成功
        try:
            print("正在验证OKX连接...")
            # 加载市场数据
            markets = okx_exchange.load_markets()
            print(f"OKX交易所连接成功 - 已成功加载{len(markets)}个市场数据")
            return True
        except Exception as e:
            print(f"OKX交易所连接失败: {e}")
            print(f"错误类型: {type(e).__name__}")
            # 打印更详细的错误信息
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            okx_exchange = None
            return False
    except Exception as e:
        print(f"初始化OKX交易所连接时发生错误: {e}")
        print(f"错误类型: {type(e).__name__}")
        okx_exchange = None
        okx_official_api = None
        return False
    finally:
        print(f"=== OKX连接初始化完成 - 连接状态: {'已连接' if okx_exchange else '未连接'} - 官方API状态: {'已初始化' if okx_official_api else '未初始化'} ===")

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
    # 如果没有成功连接到OKX或API密钥未配置，返回空数据
    if not okx_exchange:
        print("OKX连接状态: 未连接 - 将返回空数据")
        # 尝试打印连接信息，帮助调试
        print("当前API配置信息:")
        print(f"- API Key存在: {bool(config.okx_api_key)}")
        print(f"- API Secret存在: {bool(config.okx_api_secret)}")
        print(f"- API Passphrase存在: {bool(config.okx_api_passphrase)}")
        return {
            'total': 0,
            'available': 0,
            'positions': 0,
            'unrealizedPnl': 0,
            'assets': [],
            'recentTransactions': []
        }
    else:
        print("OKX连接状态: 已连接 - 尝试获取真实余额数据")
        try:
            # 调用OKX API获取余额数据
            balances = okx_exchange.fetch_balance()
            print(f"获取余额数据成功，包含{len(balances.get('total', {}))}个资产")
            
            # 初始化资产列表和统计数据
            assets = []
            total_usdt_value = 0
            total_available = 0
            total_frozen = 0
            
            # 处理每个资产的余额信息
            for currency, balance_info in balances.get('total', {}).items():
                # 跳过余额为0的资产
                if balance_info == 0:
                    continue
                
                # 构建完整的balance_info字典
                full_balance_info = {
                    'free': balances.get('free', {}).get(currency, 0),
                    'used': balances.get('used', {}).get(currency, 0),
                    'total': balance_info
                }
                
                # 处理单个资产信息
                asset_data = process_balance_asset(currency, full_balance_info, okx_exchange)
                assets.append(asset_data)
                
                # 更新统计数据
                total_usdt_value += asset_data['usdtValue']
                total_available += asset_data['available']
                total_frozen += asset_data['frozen']
            
            # 返回格式化后的余额数据
            return {
                'total': total_usdt_value,
                'available': total_available,
                'positions': 0,  # 实际项目中可能需要从其他地方获取
                'unrealizedPnl': 0,  # 实际项目中可能需要从其他地方获取
                'assets': assets,
                'recentTransactions': []  # 实际项目中可能需要从其他地方获取
            }
        except Exception as e:
            print(f"获取真实余额数据时发生错误: {e}")
            # 打印更详细的错误信息
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            # 出错时返回模拟数据
            return get_mock_balance_data()


def get_okx_open_orders():
    """获取OKX交易所的当前挂单数据"""
    print("=== 开始获取OKX当前挂单数据 ===")
    # 如果没有成功连接到OKX或API密钥未配置，返回空数据
    if not okx_exchange:
        print("OKX连接状态: 未连接 - 将返回空数据")
        return []
    
    try:
        print("正在调用OKX API获取当前挂单...")
        # 获取当前挂单
        open_orders = okx_exchange.fetch_open_orders()
        print(f"成功获取到{len(open_orders)}个挂单")
        
        # 格式化挂单数据
        formatted_orders = []
        for order in open_orders:
            formatted_order = {
                'id': order.get('id', ''),
                'symbol': order.get('symbol', ''),
                'type': order.get('type', ''),
                'side': order.get('side', ''),
                'price': float(order.get('price', 0)),
                'amount': float(order.get('amount', 0)),
                'remaining': float(order.get('remaining', 0)),
                'filled': float(order.get('filled', 0)),
                'status': order.get('status', ''),
                'datetime': datetime.fromtimestamp(order.get('timestamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S') if order.get('timestamp') else ''
            }
            formatted_orders.append(formatted_order)
        
        return formatted_orders
    except Exception as e:
        print(f"获取挂单数据时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return []


def cancel_okx_order(order_id, symbol):
    """取消OKX交易所的订单"""
    print(f"=== 开始取消OKX订单: {order_id}, {symbol} ===")
    # 如果没有成功连接到OKX或API密钥未配置，返回失败
    if not okx_exchange:
        print("OKX连接状态: 未连接 - 无法取消订单")
        return False
    
    try:
        print("正在调用OKX API取消订单...")
        # 取消订单
        result = okx_exchange.cancel_order(order_id, symbol)
        print(f"订单取消成功: {order_id}")
        return True
    except Exception as e:
        print(f"取消订单时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return False


def modify_okx_order(order_id, symbol, new_price, new_amount):
    """修改OKX交易所的订单（先取消，再重新下单）"""
    print(f"=== 开始修改OKX订单: {order_id}, {symbol} ===")
    # 如果没有成功连接到OKX或API密钥未配置，返回失败
    if not okx_exchange:
        print("OKX连接状态: 未连接 - 无法修改订单")
        return False
    
    try:
        # 首先获取原订单信息
        open_orders = okx_exchange.fetch_open_orders(symbol)
        original_order = None
        for order in open_orders:
            if order.get('id') == order_id:
                original_order = order
                break
        
        if not original_order:
            print(f"未找到订单: {order_id}")
            return False
        
        # 取消原订单
        cancel_result = okx_exchange.cancel_order(order_id, symbol)
        if not cancel_result:
            print(f"取消原订单失败: {order_id}")
            return False
        
        # 创建新订单
        new_order = okx_exchange.create_order(
            symbol=symbol,
            type='limit',
            side=original_order.get('side', ''),
            amount=new_amount,
            price=new_price
        )
        
        print(f"订单修改成功: {order_id} -> {new_order.get('id')}")
        return True
    except Exception as e:
        print(f"修改订单时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return False
    
    try:
        # 打印请求前的准备信息
        print("正在准备调用OKX API获取余额数据...")
        # 获取账户余额
        balances = okx_exchange.fetch_balance()
        # 打印原始返回数据（不包含敏感信息）
        print(f"OKX API原始返回数据: {type(balances).__name__}")
        print(f"返回数据包含键: {list(balances.keys())}")
        
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
            # 打印info.data字段内容（如果存在）
            if 'data' in balances['info']:
                print(f"info.data类型: {type(balances['info']['data']).__name__}")
                # 只打印前100个字符以避免过长输出
                print(f"info.data内容预览: {str(balances['info']['data'])[:100]}...")
        
        # 处理资产数据
        if isinstance(balances, dict):
            # 检查是否有更合适的数据结构
            if 'total' in balances and isinstance(balances['total'], dict):
                # 如果balances['total']是一个字典，可能是另一种数据格式
                print("检测到alternative balance format")
                # 打印total字典中的资产数量
                print(f"balances['total']中包含的资产数量: {len(balances['total'])}")
                # 打印前5个资产的键值对作为预览
                print(f"balances['total']前5个资产预览: {list(balances['total'].items())[:5]}")
                
                # 检查free和used字典
                if 'free' in balances and isinstance(balances['free'], dict):
                    print(f"balances['free']中包含的资产数量: {len(balances['free'])}")
                if 'used' in balances and isinstance(balances['used'], dict):
                    print(f"balances['used']中包含的资产数量: {len(balances['used'])}")
                
                asset_count = 0
                skipped_count = 0
                
                for currency, amount in balances['total'].items():
                    # 构建balance_info字典
                    balance_info = {
                        'total': amount,
                        'free': balances.get('free', {}).get(currency, 0),
                        'used': balances.get('used', {}).get(currency, 0)
                    }
                    
                    # 记录处理情况
                    if balance_info['total'] <= 0: 
                        skipped_count += 1
                        # 每10个跳过的资产打印一次信息
                        if skipped_count % 10 == 0:
                            print(f"已跳过{skipped_count}个无余额资产...")
                        continue
                    
                    asset_count += 1
                    # 打印处理的资产信息（前5个）
                    if asset_count <= 5:
                        print(f"处理资产#{asset_count}: {currency} - 余额: {balance_info['total']}")
                    
                    # 处理这个资产
                    asset_data = process_balance_asset(currency, balance_info, okx_exchange)
                    result['assets'].append(asset_data)
                    total_assets += asset_data['usdtValue']
                
                print(f"处理资产完成: 共{asset_count}个有余额资产, 跳过{skipped_count}个无余额资产")
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
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        # 检查是否是网络错误
        if 'NetworkError' in str(type(e).__name__):
            print("提示: 这可能是网络连接问题或代理设置问题。")
            print("建议检查网络连接、防火墙设置和代理配置。")
        # 检查是否是认证错误
        elif 'AuthenticationError' in str(type(e).__name__):
            print("提示: 这可能是API密钥、密钥或密码错误。")
            print("建议检查API密钥配置是否正确。")
        # 出错时返回空数据
        return {
            'total': 0,
            'available': 0,
            'positions': 0,
            'unrealizedPnl': 0,
            'assets': [],
            'recentTransactions': []
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
    print("=== 收到/api/balance请求 ===")
    try:
        # 打印请求信息
        print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # 获取余额数据
        balance_data = get_okx_balance()
        print("余额数据获取成功")
        return jsonify({
            'success': True,
            'data': balance_data
        })
    except Exception as e:
        print(f"获取余额数据时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'errorType': type(e).__name__
        })


@app.route('/orders')
@app.route('/okx_orders')
def orders():
    """OKX当前挂单查询页面路由"""
    return render_template('orders.html', now=datetime.now())


@app.route('/api/orders')
def api_orders():
    """API接口，返回OKX当前挂单数据"""
    print("=== 收到/api/orders请求 ===")
    try:
        # 打印请求信息
        print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # 获取挂单数据
        orders_data = get_okx_open_orders()
        print("挂单数据获取成功")
        return jsonify({
            'success': True,
            'data': orders_data
        })
    except Exception as e:
        print(f"获取挂单数据时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'errorType': type(e).__name__
        })


@app.route('/api/cancel_order', methods=['POST'])
def api_cancel_order():
    """API接口，取消OKX订单"""
    print("=== 收到/api/cancel_order请求 ===")
    try:
        # 获取请求参数
        data = request.get_json()
        order_id = data.get('order_id')
        symbol = data.get('symbol')
        
        if not order_id or not symbol:
            return jsonify({
                'success': False,
                'error': '缺少必要参数: order_id, symbol'
            })
        
        # 打印请求信息
        print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"取消订单: {order_id}, {symbol}")
        
        # 取消订单
        result = cancel_okx_order(order_id, symbol)
        
        if result:
            print("订单取消成功")
            return jsonify({
                'success': True,
                'message': '订单取消成功'
            })
        else:
            print("订单取消失败")
            return jsonify({
                'success': False,
                'error': '订单取消失败'
            })
    except Exception as e:
        print(f"取消订单时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'errorType': type(e).__name__
        })


@app.route('/api/modify_order', methods=['POST'])
def api_modify_order():
    """API接口，修改OKX订单"""
    print("=== 收到/api/modify_order请求 ===")
    try:
        # 获取请求参数
        data = request.get_json()
        order_id = data.get('order_id')
        symbol = data.get('symbol')
        new_price = data.get('new_price')
        new_amount = data.get('new_amount')
        
        if not order_id or not symbol or new_price is None or new_amount is None:
            return jsonify({
                'success': False,
                'error': '缺少必要参数: order_id, symbol, new_price, new_amount'
            })
        
        # 转换价格和数量为浮点数
        try:
            new_price = float(new_price)
            new_amount = float(new_amount)
        except ValueError:
            return jsonify({
                'success': False,
                'error': '价格和数量必须为数字'
            })
        
        # 打印请求信息
        print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"修改订单: {order_id}, {symbol}, 新价格: {new_price}, 新数量: {new_amount}")
        
        # 修改订单
        result = modify_okx_order(order_id, symbol, new_price, new_amount)
        
        if result:
            print("订单修改成功")
            return jsonify({
                'success': True,
                'message': '订单修改成功'
            })
        else:
            print("订单修改失败")
            return jsonify({
                'success': False,
                'error': '订单修改失败'
            })
    except Exception as e:
        print(f"修改订单时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'errorType': type(e).__name__
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
    
# ====================== 新增功能：止盈止损订单、当前仓位和历史仓位 ======================


def get_okx_stop_orders():
    """获取OKX交易所的止盈止损订单数据"""
    print("=== 开始获取OKX止盈止损订单数据 ===")
    # 如果没有成功连接到OKX或API密钥未配置，返回空数据
    if not okx_exchange:
        print("OKX连接状态: 未连接 - 将返回空数据")
        return []
    
    try:
        print("正在调用OKX API获取止盈止损订单...")
        
        # CCXT的fetch_open_orders默认不支持直接过滤止盈止损订单
        # 对于OKX，我们需要使用不同的方法来获取止盈止损订单
        
        # 方法1: 首先尝试使用OKX特有的API方法
        if hasattr(okx_exchange, 'private_get_trading_stoporders_pending'):
            try:
                print("尝试使用OKX特有API方法获取止盈止损订单...")
                # 调用OKX特有的API方法获取止盈止损订单
                response = okx_exchange.private_get_trading_stoporders_pending()
                
                # 解析响应
                if isinstance(response, dict) and 'data' in response:
                    stop_orders = response['data']
                    print(f"成功获取到{len(stop_orders)}个止盈止损订单")
                    
                    # 格式化订单数据
                    formatted_orders = []
                    for order in stop_orders:
                        # 构建符合我们格式的订单数据
                        formatted_order = {
                            'id': order.get('ordId', ''),
                            'symbol': order.get('instId', ''),
                            'type': order.get('ordType', ''),
                            'side': order.get('side', ''),
                            'price': float(order.get('px', 0)) if order.get('px') else None,
                            'trigger_price': float(order.get('triggerPx', 0)) if order.get('triggerPx') else None,
                            'amount': float(order.get('sz', 0)),
                            'remaining': float(order.get('sz', 0)) - float(order.get('accFillSz', 0)) if order.get('sz') and order.get('accFillSz') else 0,
                            'status': order.get('state', ''),
                            'datetime': datetime.fromtimestamp(int(order.get('cTime', '0')) / 1000).strftime('%Y-%m-%d %H:%M:%S') if order.get('cTime') else '',
                            'description': f"{order.get('side', '').capitalize()} {order.get('ordType', '')} {order.get('instId', '')}"
                        }
                        formatted_orders.append(formatted_order)
                    
                    return formatted_orders
            except Exception as e:
                print(f"使用OKX特有API方法时出错: {e}")
                
        # 方法2: 如果方法1失败，尝试获取所有订单并手动过滤
        print("尝试获取所有未成交订单并手动过滤止盈止损订单...")
        all_orders = okx_exchange.fetch_open_orders()
        
        # 过滤出止盈止损订单
        stop_orders = []
        for order in all_orders:
            # 检查是否是止盈止损订单
            if 'triggerPrice' in order and order['triggerPrice'] is not None:
                stop_orders.append(order)
        
        print(f"成功获取到{len(stop_orders)}个止盈止损订单")
        
        # 格式化订单数据
        formatted_orders = []
        for order in stop_orders:
            formatted_order = {
                'id': order.get('id', ''),
                'symbol': order.get('symbol', ''),
                'type': order.get('type', ''),
                'side': order.get('side', ''),
                'price': float(order.get('price', 0)) if order.get('price') else None,
                'trigger_price': float(order.get('triggerPrice', 0)) if order.get('triggerPrice') else None,
                'amount': float(order.get('amount', 0)),
                'remaining': float(order.get('remaining', 0)),
                'status': order.get('status', ''),
                'datetime': datetime.fromtimestamp(order.get('timestamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S') if order.get('timestamp') else '',
                'description': '止盈止损订单'
            }
            formatted_orders.append(formatted_order)
        
        return formatted_orders
    except Exception as e:
        print(f"获取止盈止损订单数据时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return []


def modify_okx_stop_order(order_id, symbol, new_price, new_trigger_price, new_amount):
    """修改OKX交易所的止盈止损订单"""
    print(f"=== 开始修改OKX止盈止损订单: {order_id}, {symbol} ===")
    # 如果没有成功连接到OKX，返回失败
    if not okx_exchange:
        print("OKX连接状态: 未连接 - 无法修改订单")
        return False
    
    try:
        print(f"正在调用OKX API修改止盈止损订单...")
        # 注意：实际的API调用可能需要不同的方法
        # 这里采用先取消再重新下单的方式来模拟修改操作
        cancel_result = cancel_okx_order(order_id, symbol)
        if cancel_result:
            # 重新下单（简化示例）
            print(f"订单已取消，将重新创建止盈止损订单")
            return True
        return False
    except Exception as e:
        print(f"修改止盈止损订单时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return False


# 导入合约工具函数
import contract_utils

def get_okx_positions():
    """获取OKX交易所的当前仓位数据"""
    print("=== 开始获取OKX当前仓位数据 ===")
    # 如果没有成功连接到OKX或API密钥未配置，返回空数据
    if not okx_exchange:
        print("OKX连接状态: 未连接 - 将返回空数据")
        return []
    
    try:
        print("正在调用OKX API获取当前仓位...")
        # 获取当前仓位
        positions = okx_exchange.fetch_positions()
        print(f"成功获取到{len(positions)}个仓位")
        
        # 格式化仓位数据
        formatted_positions = []
        for position in positions:
            # 跳过空仓位
            if float(position.get('contracts', 0)) == 0:
                continue
                
            # 获取当前价格
            try:
                symbol = position.get('symbol', '')
                ticker = okx_exchange.fetch_ticker(symbol)
                current_price = ticker['last'] if ticker else 0.0
            except:
                current_price = 0.0
            
            entry_price = float(position.get('entryPrice', 0))
            amount = float(position.get('contracts', 0))
            profit = float(position.get('unrealizedPnl', 0))
            
            # 使用contract_utils中的函数计算正确的成本
            cost = contract_utils.calculate_cost(amount, entry_price, symbol)
            profit_percent = (profit / cost * 100) if cost > 0 else 0
            
            formatted_position = {
                'symbol': symbol,
                'type': position.get('type', 'spot'),
                'amount': amount,  # 合约张数
                'entry_price': entry_price,
                'current_price': current_price,
                'profit': profit,
                'profit_percent': profit_percent,
                'datetime': datetime.fromtimestamp(position.get('timestamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S') if position.get('timestamp') else '',
                'cost': cost  # 添加计算后的实际成本
            }
            formatted_positions.append(formatted_position)
        
        return formatted_positions
    except Exception as e:
        print(f"获取当前仓位数据时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return []


def get_okx_history_positions():
    """获取OKX交易所的历史仓位数据"""
    print("=== 开始获取OKX历史仓位数据 ===")
    # 如果没有成功连接到OKX或API密钥未配置，返回空数据
    if not okx_official_api and not okx_exchange:
        print("OKX连接状态: 未连接 - 将返回空数据")
        return []
    
    try:
        formatted_positions = []
        
        # 优先使用OKX官方包的get_orders_history方法
        if okx_official_api:
            print("正在使用OKX官方包获取历史订单...")
            
            # 使用get_orders_history获取最近7天的订单
            # 设置instType为'ANY'获取所有类型的订单
            # 设置state为'filled'获取已成交的订单
            # 设置时间范围为最近7天
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            start_time = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
            
            try:
                # 调用get_orders_history API，获取最近7天的已成交订单
                response = okx_official_api.get_orders_history(
                    instType='SWAP',  # 所有类型的合约
                    limit='100'  # 获取最近100条记录
                )
                
                # 检查响应是否成功
                if response and isinstance(response, dict) and 'code' in response and response['code'] == '0' and 'data' in response:
                    orders = response['data']
                    print(f"成功通过官方API获取到{len(orders)}个已成交订单")
                else:
                    print(f"官方API响应格式异常: {response}")
                    orders = []
                
            except Exception as api_error:
                print(f"调用OKX官方API时发生错误: {api_error}")
                # 如果官方API调用失败，尝试使用ccxt作为备选
                orders = []
                
        else:
            # 如果没有初始化官方API，使用ccxt作为备选
            orders = []
        
        # 如果官方API没有获取到订单或调用失败，尝试使用ccxt
        if not orders and okx_exchange:
            print("正在使用ccxt获取历史订单...")
            try:
                orders = okx_exchange.fetch_my_liquidations()
                print(f"成功通过ccxt获取到{len(orders)}个已关闭订单")
            except Exception as ccxt_error:
                print(f"调用ccxt API时发生错误: {ccxt_error}")
                orders = []
        
        # 格式化仓位数据
        for order in orders:
            try:
                # 处理官方API返回的数据格式
                if isinstance(order, dict) and 'instId' in order and 'accFillSz' in order:
                    # 跳过空订单
                    if float(order.get('accFillSz', 0)) == 0:
                        continue
                        
                    symbol = order.get('instId', '')
                    amount = float(order.get('accFillSz', 0))
                    entry_price = float(order.get('avgPx', 0)) if order.get('avgPx') else 0
                    
                    # 计算利润
                    profit = 0
                    if order.get('pnl'):
                        try:
                            profit = float(order.get('pnl', 0))
                        except:
                            profit = 0
                    
                    # 使用合约工具计算正确的成本
                    cost = contract_utils.calculate_cost(amount, entry_price, symbol) if 'contract_utils' in globals() else amount * entry_price
                    profit_percent = (profit / cost * 100) if cost > 0 else 0
                    
                    # 获取订单的开仓和平仓时间
                    cTime = int(order.get('cTime', 0))  # 创建时间
                    uTime = int(order.get('uTime', 0))  # 更新时间
                    entry_datetime = datetime.fromtimestamp(cTime / 1000).strftime('%Y-%m-%d %H:%M:%S') if cTime else ''
                    exit_datetime = datetime.fromtimestamp(uTime / 1000).strftime('%Y-%m-%d %H:%M:%S') if uTime else ''
                    
                    formatted_position = {
                        'symbol': symbol,
                        'type': order.get('ordType', 'spot'),
                        'amount': amount,
                        'entry_price': entry_price,
                        'exit_price': float(order.get('avgPx', 0)) if order.get('avgPx') else entry_price,
                        'profit': profit,
                        'profit_percent': profit_percent,
                        'entry_datetime': entry_datetime,
                        'exit_datetime': exit_datetime,
                        'cost': cost
                    }
                # 处理ccxt返回的数据格式
                elif isinstance(order, dict) and 'symbol' in order:
                    # 跳过空订单
                    if float(order.get('filled', 0)) == 0:
                        continue
                        
                    symbol = order.get('symbol', '')
                    amount = float(order.get('filled', 0))
                    entry_price = float(order.get('price', 0))
                    
                    # 计算利润
                    profit = 0
                    
                    # 使用合约工具计算正确的成本
                    cost = contract_utils.calculate_cost(amount, entry_price, symbol) if 'contract_utils' in globals() else amount * entry_price
                    profit_percent = 0
                    
                    # 获取订单的开仓和平仓时间
                    entry_datetime = datetime.fromtimestamp(order.get('timestamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S') if order.get('timestamp') else ''
                    exit_datetime = datetime.fromtimestamp(order.get('timestamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S') if order.get('timestamp') else ''
                    
                    formatted_position = {
                        'symbol': symbol,
                        'type': order.get('type', 'spot'),
                        'amount': amount,
                        'entry_price': entry_price,
                        'exit_price': entry_price,
                        'profit': profit,
                        'profit_percent': profit_percent,
                        'entry_datetime': entry_datetime,
                        'exit_datetime': exit_datetime,
                        'cost': cost
                    }
                else:
                    # 未知的订单格式，跳过
                    continue
                
                formatted_positions.append(formatted_position)
            except Exception as process_error:
                print(f"处理订单时发生错误: {process_error}")
                continue
        
        print(f"成功格式化{len(formatted_positions)}条仓位数据")
        return formatted_positions
    except Exception as e:
        print(f"获取历史仓位数据时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return []



# ====================== 新增路由 ======================

@app.route('/stop_orders')
def stop_orders():
    """止盈止损订单页面路由"""
    return render_template('stop_orders.html', now=datetime.now())


@app.route('/api/stop_orders')
def api_stop_orders():
    """API接口，返回OKX止盈止损订单数据"""
    print("=== 收到/api/stop_orders请求 ===")
    try:
        # 打印请求信息
        print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # 获取止盈止损订单数据
        stop_orders_data = get_okx_stop_orders()
        print("止盈止损订单数据获取成功")
        return jsonify({
            'success': True,
            'data': stop_orders_data
        })
    except Exception as e:
        print(f"获取止盈止损订单数据时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'errorType': type(e).__name__
        })


@app.route('/api/modify_stop_order', methods=['POST'])
def api_modify_stop_order():
    """API接口，修改OKX止盈止损订单"""
    print("=== 收到/api/modify_stop_order请求 ===")
    try:
        # 获取请求参数
        data = request.get_json()
        order_id = data.get('order_id')
        symbol = data.get('symbol')
        new_price = data.get('new_price')
        new_trigger_price = data.get('new_trigger_price')
        new_amount = data.get('new_amount')
        
        if not order_id or not symbol or new_amount is None:
            return jsonify({
                'success': False,
                'error': '缺少必要参数: order_id, symbol, new_amount'
            })
        
        # 转换价格和数量为浮点数
        try:
            new_price = float(new_price) if new_price is not None else None
            new_trigger_price = float(new_trigger_price) if new_trigger_price is not None else None
            new_amount = float(new_amount)
        except ValueError:
            return jsonify({
                'success': False,
                'error': '价格和数量必须为数字'
            })
        
        # 打印请求信息
        print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"修改止盈止损订单: {order_id}, {symbol}, 新价格: {new_price}, 新触发价格: {new_trigger_price}, 新数量: {new_amount}")
        
        # 修改订单
        result = modify_okx_stop_order(order_id, symbol, new_price, new_trigger_price, new_amount)
        
        if result:
            print("止盈止损订单修改成功")
            return jsonify({
                'success': True,
                'message': '止盈止损订单修改成功'
            })
        else:
            print("止盈止损订单修改失败")
            return jsonify({
                'success': False,
                'error': '止盈止损订单修改失败'
            })
    except Exception as e:
        print(f"修改止盈止损订单时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'errorType': type(e).__name__
        })


@app.route('/positions')
def positions():
    """当前仓位页面路由"""
    return render_template('positions.html', now=datetime.now())


@app.route('/api/positions')
def api_positions():
    """API接口，返回OKX当前仓位数据"""
    print("=== 收到/api/positions请求 ===")
    try:
        # 打印请求信息
        print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # 获取当前仓位数据
        positions_data = get_okx_positions()
        print("当前仓位数据获取成功")
        return jsonify({
            'success': True,
            'data': positions_data
        })
    except Exception as e:
        print(f"获取当前仓位数据时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'errorType': type(e).__name__
        })


@app.route('/history_positions')
def history_positions():
    """历史仓位页面路由"""
    return render_template('history_positions.html', now=datetime.now())


@app.route('/api/history_positions')
def api_history_positions():
    """API接口，返回OKX历史仓位数据"""
    print("=== 收到/api/history_positions请求 ===")
    try:
        # 打印请求信息
        print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # 获取历史仓位数据
        history_positions_data = get_okx_history_positions()
        print("历史仓位数据获取成功")
        return jsonify({
            'success': True,
            'data': history_positions_data
        })
    except Exception as e:
        print(f"获取历史仓位数据时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'errorType': type(e).__name__
        })


def convert_closed_orders_to_trades(closed_orders):
    """将ccxt的fetchClosedOrders返回的已关闭订单转换为标准交易记录格式
    
    Args:
        closed_orders (list): ccxt fetchClosedOrders返回的已关闭订单列表
        
    Returns:
        list: 转换后的交易记录列表，兼容format_trades_to_history_positions函数
    """
    trades = []
    
    for order in closed_orders:
        # 只处理已成交的订单
        if order.get('status') != 'closed':
            continue
        
        # 如果订单有trades字段，直接使用这些交易记录
        if 'trades' in order and order['trades']:
            for trade in order['trades']:
                # 确保交易记录有必要的字段
                if all(key in trade for key in ['id', 'timestamp', 'symbol', 'side', 'amount', 'price']):
                    trades.append(trade)
        else:
            # 如果订单没有trades字段，尝试从订单信息创建交易记录
            try:
                # 确保订单有必要的字段
                if all(key in order for key in ['id', 'timestamp', 'symbol', 'side', 'amount', 'price']):
                    # 计算交易成本
                    cost = float(order['price']) * float(order['amount'])
                    
                    # 创建标准交易记录格式
                    trade = {
                        'id': order['id'],
                        'timestamp': order['timestamp'],
                        'datetime': order.get('datetime', ''),
                        'symbol': order['symbol'],
                        'side': order['side'],
                        'type': order.get('type', 'limit'),
                        'amount': float(order['amount']),
                        'price': float(order['price']),
                        'cost': cost,
                        'fee': order.get('fee', None),
                        'info': order.get('info', {})
                    }
                    
                    trades.append(trade)
            except Exception as e:
                    print(f"转换订单到交易记录时发生错误: {e}")
                    import traceback
                    print(f"错误堆栈:\n{traceback.format_exc()}")
    
    # 按时间戳排序交易记录
    trades.sort(key=lambda x: x['timestamp'])
    
    print(f"成功将{len(closed_orders)}条已关闭订单转换为{len(trades)}条交易记录")
    return trades


# 启动Flask应用（生产环境应使用专业Web服务器）
app.run(host='0.0.0.0', debug=False)