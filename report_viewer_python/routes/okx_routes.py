from flask import Blueprint, render_template, jsonify, session
from datetime import datetime
import json
from control.okx_control import OKXControl

# 创建OKX相关路由蓝图
okx_bp = Blueprint('okx', __name__, url_prefix='/')

# 初始化OKX控制器（将在app.py中设置API客户端）
okx_control = OKXControl()

@okx_bp.route('/balance')
def balance():
    # 检查用户是否已登录
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401
    
    # 创建当前时间对象
    now = datetime.now()
    
    try:
        # 使用OKXControl获取余额
        balances = okx_control.get_balances(use_ccxt=False)  # 使用官方API
        
        # 处理错误情况
        if 'error' in balances:
            return render_template('balance.html', error=balances['error'], username=session.get('username'), now=now)
        
        return render_template('balance.html', balances=balances, username=session.get('username'), now=now)
    except Exception as e:
        error_msg = f'获取余额失败: {str(e)}'
        print(error_msg)
        return render_template('balance.html', error=error_msg, username=session.get('username'), now=now)

@okx_bp.route('/api/balance')
def api_get_balance():
    # 检查用户是否已登录
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401
    
    try:
        # 使用OKXControl获取详细余额
        result = okx_control.get_detailed_okx_balance()
        
        if result['success']:
            return jsonify({'status': 'success', 'data': result['data']})
        else:
            return jsonify({'status': 'error', 'message': result['error']})
    except Exception as e:
        error_msg = f'获取余额失败: {str(e)}'
        print(error_msg)
        return jsonify({'status': 'error', 'message': error_msg})



@okx_bp.route('/orders')
def orders():
    # 检查用户是否已登录
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401
    
    # 创建当前时间对象
    now = datetime.now()
    
    try:
        # 使用OKXControl获取订单
        orders_data = okx_control.get_orders()
        
        if 'error' in orders_data:
            return render_template('orders.html', error=orders_data['error'], username=session.get('username'), now=now)
        
        return render_template('orders.html', orders=orders_data, username=session.get('username'), now=now)
    except Exception as e:
        error_msg = f'获取订单失败: {str(e)}'
        print(error_msg)
        return render_template('orders.html', error=error_msg, username=session.get('username'), now=now)

@okx_bp.route('/stop_orders')
def stop_orders():
    # 检查用户是否已登录
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401
    
    # 创建当前时间对象
    now = datetime.now()
    
    try:
        # 使用OKXControl获取止损止盈订单
        stop_orders_data = okx_control.get_stop_orders()
        
        if 'error' in stop_orders_data:
            return render_template('stop_orders.html', error=stop_orders_data['error'], username=session.get('username'), now=now)
        
        return render_template('stop_orders.html', stop_orders=stop_orders_data, username=session.get('username'), now=now)
    except Exception as e:
        error_msg = f'获取止损止盈订单失败: {str(e)}'
        print(error_msg)
        return render_template('stop_orders.html', error=error_msg, username=session.get('username'), now=now)

@okx_bp.route('/history_positions')
def history_positions():
    # 检查用户是否已登录
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401
    
    # 创建当前时间对象
    now = datetime.now()
    
    try:
        # 使用OKXControl获取历史持仓
        history_positions_data = okx_control.get_history_positions()
        
        if 'error' in history_positions_data:
            return render_template('history_positions.html', error=history_positions_data['error'], username=session.get('username'), now=now)
        
        return render_template('history_positions.html', positions=history_positions_data, username=session.get('username'), now=now)
    except Exception as e:
        error_msg = f'获取历史持仓失败: {str(e)}'
        print(error_msg)
        return render_template('history_positions.html', error=error_msg, username=session.get('username'), now=now)