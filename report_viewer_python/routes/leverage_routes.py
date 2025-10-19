from flask import Blueprint, render_template, jsonify, request, session, current_app
from datetime import datetime
from .auth_routes import login_required

# 创建杠杆相关路由蓝图
leverage_bp = Blueprint('leverage', __name__, url_prefix='/')

@leverage_bp.route('/set_max_leverage')
def set_max_leverage_page():
    # 检查用户是否已登录
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401
    
    # 创建当前时间对象
    now = datetime.now()
    
    try:
        # 使用注入的OKX控制实例
        try:
            okx_control = current_app.blueprints['leverage'].okx_control
        except (AttributeError, KeyError):
            # 如果blueprint中没有，则尝试使用模块级别的实例
            try:
                import routes.leverage_routes as lr
                okx_control = lr.okx_control
            except (ImportError, AttributeError):
                raise ValueError('OKX控制实例未初始化')
        
        if not okx_control:
            raise ValueError('OKX控制实例未初始化')
        
        # 使用OKXControl获取永续合约交易对及其最大杠杆信息
        symbols_result = okx_control.get_perpetual_symbols_with_leverage()
        
        # 处理返回结果
        if isinstance(symbols_result, dict) and 'error' in symbols_result:
            error_message = symbols_result['error']
            symbols = symbols_result.get('symbols', [])
            return render_template('set_max_leverage.html', error=error_message, symbols=symbols, username=session.get('username'), now=now)
        else:
            # 如果不是错误字典，直接使用返回值
            symbols = symbols_result
            return render_template('set_max_leverage.html', symbols=symbols, username=session.get('username'), now=now)
    except Exception as e:
        error_msg = f'获取交易对失败: {str(e)}'
        print(error_msg)
        return render_template('set_max_leverage.html', error=error_msg, username=session.get('username'), now=now)

@leverage_bp.route('/api/set_max_leverage', methods=['POST'])
@login_required
def api_set_max_leverage():
    """设置最大杠杆API"""
    try:
        # 获取请求参数
        data = request.get_json() or {}
        symbols = data.get('symbols', [])
        leverage = data.get('leverage')
        mgn_mode = data.get('mgn_mode', 'isolated')

        # 验证参数
        if not symbols or not leverage:
            return jsonify({
                'status': 'error',
                'message': '请提供交易对和杠杆倍数'
            })

        # 转换杠杆为浮点数
        try:
            leverage = float(leverage)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': '杠杆倍数必须是数字'
            })

        # 验证杠杆范围
        if leverage < 1 or leverage > 100:
            return jsonify({
                'status': 'error',
                'message': '杠杆倍数必须在1到100之间'
            })

        # 使用注入的OKX控制实例
        try:
            okx_control = current_app.blueprints['leverage'].okx_control
        except (AttributeError, KeyError):
            # 如果blueprint中没有，则尝试使用模块级别的实例
            try:
                import routes.leverage_routes as lr
                okx_control = lr.okx_control
            except (ImportError, AttributeError):
                return jsonify({
                    'status': 'error',
                    'message': 'OKX控制实例未初始化'
                })
        
        if not okx_control:
            return jsonify({
                'status': 'error',
                'message': 'OKX控制实例未初始化'
            })
        
        # 根据交易对数量决定调用单个还是批量设置
        if len(symbols) == 1:
            # 单个交易对设置
            result = okx_control.set_max_leverage(symbols[0], leverage, mgn_mode)
            
            if result.get('success'):
                return jsonify({
                    'status': 'success',
                    'message': result.get('message'),
                    'details': {
                        'total': 1,
                        'success_count': 1,
                        'fail_count': 0,
                        'results': [result]
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': result.get('message'),
                    'details': {
                        'total': 1,
                        'success_count': 0,
                        'fail_count': 1,
                        'results': [result]
                    }
                })
        else:
            # 批量设置
            result = okx_control.batch_set_leverage(symbols, leverage, mgn_mode)
            
            if result.get('success') or result.get('success_count', 0) > 0:
                return jsonify({
                    'status': 'success',
                    'message': f'成功设置{result["success_count"]}/{result["total"]}个交易对的杠杆',
                    'details': result
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'所有交易对设置失败，总数: {result["total"]}',
                    'details': result
                })

    except Exception as e:
        error_msg = f'设置杠杆失败: {str(e)}'
        print(error_msg)
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': error_msg
        })

@leverage_bp.route('/api/set_all_max_leverage', methods=['POST'])
@login_required
def api_set_all_max_leverage():
    """一键设置所有交易对为最大杠杆API"""
    try:
        # 获取请求参数
        data = request.get_json() or {}
        mgn_mode = data.get('mgn_mode', 'isolated')

        # 使用注入的OKX控制实例
        try:
            okx_control = current_app.blueprints['leverage'].okx_control
        except (AttributeError, KeyError):
            # 如果blueprint中没有，则尝试使用模块级别的实例
            try:
                import routes.leverage_routes as lr
                okx_control = lr.okx_control
            except (ImportError, AttributeError):
                return jsonify({
                    'status': 'error',
                    'message': 'OKX控制实例未初始化'
                })
        
        if not okx_control:
            return jsonify({
                'status': 'error',
                'message': 'OKX控制实例未初始化'
            })
        
        # 调用OKX控制实例的方法设置所有交易对的最大杠杆
        result = okx_control.set_all_max_leverage(mgn_mode)
        
        if result.get('success') or result.get('success_count', 0) > 0:
            return jsonify({
                'status': 'success',
                'message': f'成功为{result["success_count"]}/{result["total"]}个交易对设置最大杠杆',
                'details': result
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'所有交易对设置失败，总数: {result["total"]}',
                'details': result
            })

    except Exception as e:
        error_msg = f'一键设置最大杠杆失败: {str(e)}'
        print(error_msg)
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': error_msg
        })