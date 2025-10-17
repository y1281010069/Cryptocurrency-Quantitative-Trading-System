from flask import Blueprint, render_template, jsonify, request, session
from control.leverage_control import LeverageControl
from datetime import datetime

# 创建杠杆相关路由蓝图
leverage_bp = Blueprint('leverage', __name__, url_prefix='/')

# 初始化杠杆控制器（将在app.py中设置API客户端）
leverage_control = LeverageControl()

@leverage_bp.route('/set_max_leverage')
def set_max_leverage_page():
    # 检查用户是否已登录
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401
    
    # 创建当前时间对象
    now = datetime.now()
    
    try:
        # 使用LeverageControl获取永续合约交易对
        symbols = leverage_control.get_perpetual_symbols()
        
        if 'error' in symbols:
            return render_template('set_max_leverage.html', error=symbols['error'], username=session.get('username'), now=now)
        
        return render_template('set_max_leverage.html', symbols=symbols, username=session.get('username'), now=now)
    except Exception as e:
        error_msg = f'获取交易对失败: {str(e)}'
        print(error_msg)
        return render_template('set_max_leverage.html', error=error_msg, username=session.get('username'), now=now)

@leverage_bp.route('/api/set_max_leverage', methods=['POST'])
def api_set_max_leverage():
    # 检查用户是否已登录
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401
    
    try:
        # 获取请求数据
        data = request.get_json()
        symbols = data.get('symbols', [])
        leverage = data.get('leverage')
        mgn_mode = data.get('mgn_mode', 'isolated')
        
        # 验证参数
        if not symbols or leverage is None:
            return jsonify({'status': 'error', 'message': '缺少必要参数'})
        
        # 如果只有一个交易对，使用单个设置方法
        if len(symbols) == 1:
            result = leverage_control.set_max_leverage(symbols[0], leverage, mgn_mode)
            
            if result['success']:
                return jsonify({'status': 'success', 'message': result['message']})
            else:
                return jsonify({'status': 'error', 'message': result['message']})
        else:
            # 批量设置杠杆
            results = leverage_control.batch_set_leverage(symbols, leverage, mgn_mode)
            return jsonify({
                'status': 'success' if results['success_count'] > 0 else 'error',
                'message': f'成功设置{results["success_count"]}/{results["total"]}个交易对的杠杆',
                'details': results
            })
    except Exception as e:
        error_msg = f'设置杠杆失败: {str(e)}'
        print(error_msg)
        return jsonify({'status': 'error', 'message': error_msg})