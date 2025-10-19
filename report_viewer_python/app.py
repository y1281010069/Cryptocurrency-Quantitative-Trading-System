from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import re
import os
import sys
import json
import time
import ccxt
from datetime import datetime, timedelta
from functools import wraps

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入合约工具模块
from lib.tool import contract_utils

# 导入OKX官方Python包
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib', 'python-okx-master'))
from okx.Trade import TradeAPI
from okx.Account import AccountAPI
from okx.PublicData import PublicAPI

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

# 会话配置 - 设置一个安全的密钥用于会话管理
app.secret_key = 'your-secret-key-here-change-in-production'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # 30天免验证

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# 配置默认的报告文件路径
DEFAULT_REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports', 'multi_timeframe_analysis_new.txt')

# 导入路由蓝图
from routes.auth_routes import auth_bp
from routes.report_routes import report_bp
from routes.okx_routes import okx_bp
from routes.config_routes import config_bp
from routes.leverage_routes import leverage_bp


# 导入控制器
from control.report_control import ReportControl
from control.okx_control import OKXControl
from control.config_control import ConfigControl
from control.auth_control import AuthControl

# 初始化OKX交易所连接
okx_exchange = None
okx_official_api = None  # OKX官方包的TradeAPI实例
okx_account_api = None  # OKX官方包的AccountAPI实例
okx_public_api = None  # OKX官方包的PublicAPI实例
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
            global okx_official_api, okx_account_api, okx_public_api
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
            
            # 创建OKX官方包AccountAPI实例
            print("正在创建OKX官方包AccountAPI实例...")
            okx_account_api = AccountAPI(
                api_key=config.okx_api_key,
                api_secret_key=config.okx_api_secret,
                passphrase=config.okx_api_passphrase,
                use_server_time=True,
                flag='0',
                debug=False,
                proxy=proxy_config
            )
            print("OKX官方包AccountAPI实例创建成功")
            
            # 创建OKX官方包PublicAPI实例
            print("正在创建OKX官方包PublicAPI实例...")
            okx_public_api = PublicAPI(
                api_key=config.okx_api_key,
                api_secret_key=config.okx_api_secret,
                passphrase=config.okx_api_passphrase,
                use_server_time=True,
                flag='0',
                debug=False,
                proxy=proxy_config
            )
            print("OKX官方包PublicAPI实例创建成功")
        except Exception as e:
            print(f"创建OKX官方包API实例失败: {e}")
            okx_official_api = None
            okx_account_api = None
            okx_public_api = None
        
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


# 初始化全局控制器实例
global_report_control = ReportControl()
global_okx_control = OKXControl()
global_config_control = ConfigControl()
global_auth_control = AuthControl()

# 将API实例注入到控制器中
global_okx_control.set_api_clients(okx_public_api=okx_public_api, okx_account_api=okx_account_api, okx_official_api=okx_official_api, okx_exchange=okx_exchange)
print("=== 控制器API实例注入完成 ===")



# OKX相关功能已合并到OKXControl类中


def get_okx_balance():
    """获取OKX交易所的账户余额数据"""
    return global_okx_control.get_okx_balance()


def get_detailed_okx_balance():
    """获取详细的OKX账户余额数据"""
    return global_okx_control.get_detailed_okx_balance()


def get_okx_positions():
    """获取OKX交易所的当前仓位数据"""
    return global_okx_control.get_okx_positions()


def get_okx_open_orders():
    """获取OKX交易所的当前挂单数据"""
    return global_okx_control.get_okx_open_orders()


def cancel_okx_order(order_id, symbol):
    """取消OKX交易所的订单"""
    return global_okx_control.cancel_okx_order(order_id, symbol)


def modify_okx_order(order_id, symbol, new_price, new_amount):
    """修改OKX交易所的订单"""
    return global_okx_control.modify_okx_order(order_id, symbol, new_price, new_amount)


def get_okx_stop_orders():
    """获取OKX交易所的止盈止损订单数据"""
    # 调用OKXControl实例的方法并返回格式化的订单数据
    result = global_okx_control.get_okx_stop_orders()
    # 从结果中提取stop_orders列表（兼容原有代码的返回格式）
    return result.get('stop_orders', [])


def cancel_okx_stop_order(order_id, symbol):
    """取消OKX交易所的止盈止损订单"""
    # 调用OKXControl实例的方法并返回成功状态（兼容原有代码的返回格式）
    result = global_okx_control.cancel_okx_stop_order(order_id, symbol)
    # 从结果中提取success状态（兼容原有代码的返回格式）
    return result.get('success', False)


def modify_okx_stop_order(order_id, symbol, new_tp_ord_price=None, new_tp_trigger_price=None, new_amount=None, new_sl_trigger_price=None):
    """修改OKX交易所的止盈止损订单"""
    # 调用OKXControl实例的方法并返回成功状态（兼容原有代码的返回格式）
    result = global_okx_control.modify_okx_stop_order(order_id, symbol, new_tp_ord_price, new_tp_trigger_price, new_amount, new_sl_trigger_price)
    # 从结果中提取success状态（兼容原有代码的返回格式）
    return result.get('success', False)


@app.route('/')
@login_required
def index():
    """主页面路由 - 多时间框架分析报告"""
    # 从URL参数获取报告文件路径
    report_path = request.args.get('file', DEFAULT_REPORT_PATH)
    # 解析报告数据
    report_data = global_report_control.parse_report_content(report_path)
    
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
@login_required
def api_data():
    """API接口，返回JSON格式的报告数据"""
    report_path = request.args.get('file', DEFAULT_REPORT_PATH)
    report_data = global_report_control.parse_report_content(report_path)
    return jsonify(report_data)


@app.route('/api/filter')
@login_required
def filter_data():
    """API接口，根据筛选条件返回过滤后的数据"""
    # 获取筛选参数
    filter_type = request.args.get('type', 'all')
    search_term = request.args.get('search', '')
    report_path = request.args.get('file', DEFAULT_REPORT_PATH)
    
    # 使用report_control中的筛选方法
    filtered_data = global_report_control.filter_opportunities(
        file_path=report_path,
        filter_type=filter_type,
        search_term=search_term
    )
    
    # 返回过滤后的数据
    return jsonify(filtered_data)


@app.route('/balance')
@app.route('/okx_balance')
@login_required
def balance():
    """OKX余额查询页面路由"""
    return render_template('balance.html', now=datetime.now())


@app.route('/api/balance')
@login_required
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


# 仓位API路由已在文件末尾定义


@app.route('/orders')
@app.route('/okx_orders')
@login_required
def orders():
    """OKX当前挂单查询页面路由"""
    return render_template('orders.html', now=datetime.now())


@app.route('/api/orders')
@login_required
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
@login_required
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
@login_required
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
            return jsonify({
                'success': True,
                'message': '订单修改成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '订单修改失败'
            })
    except Exception as e:
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


@app.route('/api/cancel_stop_order', methods=['POST'])
@login_required
def api_cancel_stop_order():
    """API接口，取消OKX止盈止损订单"""
    print("=== 收到/api/cancel_stop_order请求 ===")
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
        print(f"取消止盈止损订单: {order_id}, {symbol}")
        
        # 取消止盈止损订单
        result = cancel_okx_stop_order(order_id, symbol)
        
        if result:
            print("止盈止损订单取消成功")
            return jsonify({
                'success': True,
                'message': '止盈止损订单取消成功'
            })
        else:
            print("止盈止损订单取消失败")
            return jsonify({
                'success': False,
                'error': '止盈止损订单取消失败'
            })
    except Exception as e:
        print(f"取消止盈止损订单时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'errorType': type(e).__name__
        })







# 导入合约工具函数 - 供后续可能使用
from lib.tool import contract_utils


def get_okx_history_positions():
    """获取OKX交易所的历史仓位数据，使用positions-history接口"""
    print("=== 开始获取OKX历史仓位数据 ===")
    # 如果没有成功连接到OKX或API密钥未配置，返回空数据
    if not hasattr(config, 'okx_api_key') or not config.okx_api_key:
        print("OKX API密钥未配置 - 将返回空数据")
        return []
    
    try:
        formatted_positions = []
        
        # 创建AccountAPI实例来调用positions-history接口
        try:
            print("正在创建OKX AccountAPI实例...")
            # 获取代理配置（如果有）
            proxy_config = None
            if hasattr(config, 'proxy') and config.proxy:
                proxy_config = config.proxy
            elif hasattr(config, 'https_proxy') and config.https_proxy:
                proxy_config = config.https_proxy
            
            # 创建AccountAPI实例
            account_api = AccountAPI(
                api_key=config.okx_api_key,
                api_secret_key=config.okx_api_secret,
                passphrase=config.okx_api_passphrase,
                use_server_time=True,
                flag='0',  # 实盘环境
                debug=False,
                proxy=proxy_config
            )
            
            print("正在使用OKX positions-history接口获取历史仓位数据...")
            
            # 调用positions-history接口，获取最新的历史仓位（最近24小时）
            end_timestamp = int(time.time() * 1000)  # 当前时间戳（毫秒）
            start_timestamp = end_timestamp - 24 * 60 * 60 * 1000  # 1天前的时间戳
            
            response = account_api.get_positions_history(
                instType='SWAP',  # 合约类型，SWAP表示永续合约
                mgnMode='cross',  # 保证金模式，isolated表示逐仓
                limit='100'  # 获取最近100条记录
            )
            
            # 检查响应是否成功
            if response and isinstance(response, dict) and 'code' in response and response['code'] == '0' and 'data' in response:
                positions_history = response['data']
                print(f"成功通过positions-history接口获取到{len(positions_history)}条历史仓位数据")
            else:
                print(f"positions-history接口响应格式异常: {response}")
                # 尝试使用之前的方法作为备选
                if okx_official_api:
                    print("备选方案: 使用get_orders_history接口")
                    response = okx_official_api.get_orders_history(
                        instType='SWAP',
                        limit='100'
                    )
                    if response and isinstance(response, dict) and 'code' in response and response['code'] == '0' and 'data' in response:
                        positions_history = response['data']
                    else:
                        positions_history = []
                else:
                    positions_history = []
                
        except Exception as api_error:
            print(f"调用OKX positions-history接口时发生错误: {api_error}")
            # 当接口调用失败时，直接返回空列表
            positions_history = []
        
        # 格式化仓位数据
        for position in positions_history:
            try:
                # 处理positions-history接口返回的数据格式
                # 放宽过滤条件，不再严格要求adjEq字段存在
                if isinstance(position, dict) and 'instId' in position:
                    # 打印原始数据以便调试
                    # print(f"处理原始仓位数据: {position}")
                    
                    # 获取必要的数据
                    symbol = position.get('instId', '')
                    pos_side = position.get('posSide', '')  # 仓位方向
                    # 尝试从不同可能的字段获取仓位数量
                    amount = 0
                    try:
                        # 优先尝试API实际返回的字段
                        amount = float(position.get('closeTotalPos', position.get('openMaxPos', 0)))
                        # 如果上述字段为空，再尝试其他可能的字段
                        if amount == 0:
                            amount = float(position.get('vol', position.get('accFillSz', position.get('filled', 0))))
                    except Exception as e:
                        amount = 0
                        print(f"无法解析仓位数量: {position}, 错误: {e}")
                    
                    # 尝试从不同可能的字段获取入场价格
                    entry_price = 0
                    try:
                        # 优先使用openAvgPx作为入场价格
                        entry_price = float(position.get('openAvgPx', position.get('avgPx', position.get('price', 0))))
                    except:
                        entry_price = 0
                        print(f"无法解析入场价格: {position}")
                    
                    # 尝试从不同可能的字段获取出场价格
                    exit_price = 0
                    try:
                        # 优先使用closeAvgPx作为出场价格
                        exit_price = float(position.get('closeAvgPx', position.get('lastPx', position.get('avgPx', position.get('price', 0)))))
                    except:
                        exit_price = 0
                        print(f"无法解析出场价格: {position}")
                    
                    # 计算利润
                    profit = 0
                    try:
                        # 尝试从不同可能的字段获取利润
                        profit = float(position.get('pnl', position.get('unrealizedPnl', 0)))
                    except:
                        profit = 0
                        print(f"无法解析利润: {position}")
                    
                    # 使用合约工具计算正确的成本
                    cost = 0
                    try:
                        cost = contract_utils.calculate_cost(amount, entry_price, symbol) if 'contract_utils' in globals() else amount * entry_price
                    except:
                        cost = amount * entry_price
                        print(f"无法计算成本: {position}")
                    
                    profit_percent = (profit / cost * 100) if cost > 0 else 0
                    
                    # 获取订单的开仓和平仓时间
                    cTime = 0
                    uTime = 0
                    try:
                        cTime = int(position.get('cTime', position.get('openTime', position.get('timestamp', 0))))
                        uTime = int(position.get('uTime', position.get('closeTime', position.get('timestamp', 0))))
                    except:
                        print(f"无法解析时间戳: {position}")
                    
                    entry_datetime = ''
                    exit_datetime = ''
                    try:
                        entry_datetime = datetime.fromtimestamp(cTime / 1000).strftime('%Y-%m-%d %H:%M:%S') if cTime else ''
                        exit_datetime = datetime.fromtimestamp(uTime / 1000).strftime('%Y-%m-%d %H:%M:%S') if uTime else ''
                    except:
                        print(f"无法格式化时间: {cTime}, {uTime}")
                    
                    # 获取订单类型（包含post_only等信息）
                    ord_type = position.get('ordType', 'limit')
                    
                    # 只有当金额大于0时才添加到结果中
                    if amount > 0:
                        formatted_position = {
                            'symbol': symbol,
                            'type': ord_type,
                            'amount': amount,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'profit': profit,
                            'profit_percent': profit_percent,
                            'entry_datetime': entry_datetime,
                            'exit_datetime': exit_datetime,
                            'cost': cost,
                            'posSide': pos_side  # 添加仓位方向信息
                        }
                        formatted_positions.append(formatted_position)
                        # print(f"成功格式化一条历史仓位数据: {formatted_position}")
                    else:
                        print(f"跳过空仓位: {position}")
                # 处理get_orders_history接口返回的数据格式（备选方案）
                elif isinstance(position, dict) and 'instId' in position and 'accFillSz' in position:
                    # 跳过空订单
                    if float(position.get('accFillSz', 0)) == 0:
                        continue
                        
                    symbol = position.get('instId', '')
                    amount = float(position.get('accFillSz', 0))
                    # 优先使用openAvgPx作为入场价格
                    entry_price = float(position.get('openAvgPx', position.get('avgPx', 0))) if position.get('avgPx') or position.get('openAvgPx') else 0
                    
                    # 计算利润
                    profit = 0
                    if position.get('pnl'):
                        try:
                            profit = float(position.get('pnl', 0))
                        except:
                            profit = 0
                    
                    # 使用合约工具计算正确的成本
                    cost = contract_utils.calculate_cost(amount, entry_price, symbol) if 'contract_utils' in globals() else amount * entry_price
                    profit_percent = (profit / cost * 100) if cost > 0 else 0
                    
                    # 获取订单的开仓和平仓时间
                    cTime = int(position.get('cTime', 0))  # 创建时间
                    uTime = int(position.get('uTime', 0))  # 更新时间
                    entry_datetime = datetime.fromtimestamp(cTime / 1000).strftime('%Y-%m-%d %H:%M:%S') if cTime else ''
                    exit_datetime = datetime.fromtimestamp(uTime / 1000).strftime('%Y-%m-%d %H:%M:%S') if uTime else ''
                    
                    formatted_position = {
                        'symbol': symbol,
                        'type': position.get('ordType', 'spot'),
                        'amount': amount,
                        'entry_price': entry_price,
                        # 优先使用closeAvgPx作为出场价格
                        'exit_price': float(position.get('closeAvgPx', position.get('avgPx', 0))) if position.get('avgPx') or position.get('closeAvgPx') else entry_price,
                        'profit': profit,
                        'profit_percent': profit_percent,
                        'entry_datetime': entry_datetime,
                        'exit_datetime': exit_datetime,
                        'cost': cost
                    }
                    formatted_positions.append(formatted_position)
                    print(f"成功格式化一条历史仓位数据: {formatted_position}")
                # 处理ccxt返回的数据格式（备选方案）
                elif isinstance(position, dict) and 'symbol' in position:
                    # 跳过空订单
                    if float(position.get('filled', 0)) == 0:
                        continue
                        
                    symbol = position.get('symbol', '')
                    amount = float(position.get('filled', 0))
                    entry_price = float(position.get('price', 0))
                    
                    # 计算利润
                    profit = 0
                    
                    # 使用合约工具计算正确的成本
                    cost = contract_utils.calculate_cost(amount, entry_price, symbol) if 'contract_utils' in globals() else amount * entry_price
                    profit_percent = 0
                    
                    # 获取订单的开仓和平仓时间
                    entry_datetime = datetime.fromtimestamp(position.get('timestamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S') if position.get('timestamp') else ''
                    exit_datetime = datetime.fromtimestamp(position.get('timestamp', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S') if position.get('timestamp') else ''
                    
                    formatted_position = {
                        'symbol': symbol,
                        'type': position.get('type', 'spot'),
                        'amount': amount,
                        'entry_price': entry_price,
                        'exit_price': entry_price,
                        'profit': profit,
                        'profit_percent': profit_percent,
                        'entry_datetime': entry_datetime,
                        'exit_datetime': exit_datetime,
                        'cost': cost
                    }
                    formatted_positions.append(formatted_position)
                    print(f"成功格式化一条历史仓位数据: {formatted_position}")
                else:
                    # 未知的订单格式，跳过
                    continue
            except Exception as process_error:
                print(f"处理仓位数据时发生错误: {process_error}")
                continue
        
        print(f"成功格式化{len(formatted_positions)}条历史仓位数据")
        return formatted_positions
    except Exception as e:
        print(f"获取历史仓位数据时发生错误: {e}")
        # 打印更详细的错误信息
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return []



# ====================== 新增路由 ======================

@app.route('/stop_orders')
@login_required
def stop_orders():
    """止盈止损订单页面路由"""
    return render_template('stop_orders.html', now=datetime.now())


@app.route('/api/stop_orders')
@login_required
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
@login_required
def api_modify_stop_order():
    """API接口，修改OKX止盈止损订单"""
    print("=== 收到/api/modify_stop_order请求 ===")
    try:
        # 获取请求参数
        data = request.get_json()
        
        # 调用OKXControl实例的处理方法
        result = global_okx_control.handle_modify_stop_order_request(data)
        
        # 返回JSON响应
        return jsonify(result)
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
@login_required
def positions():
    """当前仓位页面路由"""
    return render_template('positions.html', now=datetime.now())


@app.route('/api/positions')
@login_required
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
@login_required
def history_positions():
    """历史仓位页面路由"""
    return render_template('history_positions.html', now=datetime.now())


@app.route('/api/history_positions')
@login_required
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


# 将全局API实例注入到控制器中
global_report_control.default_report_path = DEFAULT_REPORT_PATH
global_okx_control.set_api_clients(
    okx_exchange=okx_exchange,
    okx_official_api=okx_official_api,
    okx_account_api=okx_account_api,
    okx_public_api=okx_public_api
)

# 将控制器实例注入到路由模块
import routes.report_routes
import routes.okx_routes
import routes.config_routes
import routes.leverage_routes
import routes.auth_routes

routes.report_routes.report_control = global_report_control
routes.okx_routes.okx_control = global_okx_control
routes.config_routes.config_control = global_config_control
routes.leverage_routes.okx_control = global_okx_control
routes.auth_routes.auth_control = global_auth_control

# 注册路由蓝图到Flask应用
app.register_blueprint(auth_bp)
app.register_blueprint(report_bp)
app.register_blueprint(okx_bp)
app.register_blueprint(config_bp)
app.register_blueprint(leverage_bp)

# 启动Flask应用（生产环境应使用专业Web服务器）
app.run(host='0.0.0.0', debug=False)