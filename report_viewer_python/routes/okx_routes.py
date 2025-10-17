from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import time

# 创建OKX相关路由蓝图
okx_bp = Blueprint('okx', __name__)

# 声明全局变量，这些变量将在app.py中初始化
okx_official_api = None
okx_account_api = None
okx_exchange = None

@okx_bp.route('/balance')
def balance_page():
    """OKX余额查询页面"""
    return render_template('balance.html', now=datetime.now())

@okx_bp.route('/api/get_balance')
def api_get_balance():
    """API接口，获取OKX账户余额信息"""
    print("=== 收到/api/get_balance请求 ===")
    try:
        # 检查API实例是否初始化
        if not okx_account_api:
            return jsonify({
                'success': False,
                'message': 'OKX API未初始化成功，请检查API密钥配置'
            })
        
        # 调用 /api/v5/account/balance 获取账户余额
        balance_response = okx_account_api.get_balances()
        
        if not balance_response or balance_response.get('code') != '0':
            error_msg = f'获取余额失败: {balance_response.get("msg", "未知错误")}'
            print(error_msg)
            return jsonify({
                'success': False,
                'message': error_msg
            })
        
        # 处理余额数据
        balances = balance_response.get('data', [])
        print(f"成功获取OKX账户余额信息，包含{len(balances)}个币种")
        
        # 返回余额数据
        return jsonify({
            'success': True,
            'data': balances
        })
        
    except Exception as e:
        print(f"获取余额时发生错误: {e}")
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'获取余额时发生错误: {str(e)}'
        })

@okx_bp.route('/positions')
def positions_page():
    """OKX持仓查询页面"""
    return render_template('positions.html', now=datetime.now())

@okx_bp.route('/api/get_positions')
def api_get_positions():
    """API接口，获取OKX账户持仓信息"""
    print("=== 收到/api/get_positions请求 ===")
    try:
        # 检查API实例是否初始化
        if not okx_account_api:
            return jsonify({
                'success': False,
                'message': 'OKX API未初始化成功，请检查API密钥配置'
            })
        
        # 调用 /api/v5/account/positions 获取持仓信息
        positions_response = okx_account_api.get_positions()
        
        if not positions_response or positions_response.get('code') != '0':
            error_msg = f'获取持仓失败: {positions_response.get("msg", "未知错误")}'
            print(error_msg)
            return jsonify({
                'success': False,
                'message': error_msg
            })
        
        # 处理持仓数据
        positions = positions_response.get('data', [])
        print(f"成功获取OKX账户持仓信息，包含{len(positions)}个持仓")
        
        # 返回持仓数据
        return jsonify({
            'success': True,
            'data': positions
        })
        
    except Exception as e:
        print(f"获取持仓时发生错误: {e}")
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'获取持仓时发生错误: {str(e)}'
        })

@okx_bp.route('/orders')
def orders_page():
    """OKX订单查询页面"""
    return render_template('orders.html', now=datetime.now())

@okx_bp.route('/stop_orders')
def stop_orders_page():
    """OKX止损止盈订单查询页面"""
    return render_template('stop_orders.html', now=datetime.now())

@okx_bp.route('/history_positions')
def history_positions_page():
    """OKX历史持仓查询页面"""
    return render_template('history_positions.html', now=datetime.now())