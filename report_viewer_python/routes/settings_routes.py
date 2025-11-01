from flask import Blueprint, render_template, request, jsonify, session
import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 尝试导入配置
try:
    from config import REDIS_CONFIG
except ImportError:
    # 如果没有REDIS_CONFIG，使用默认配置
    REDIS_CONFIG = {
        'ADDR': 'localhost:6379',
        'PASSWORD': ''
    }

# 创建settings蓝图
settings_bp = Blueprint('settings', __name__)

# 全局控制器实例（将在app.py中设置）
settings_control = None

@settings_bp.route('/settings')
def settings():
    """系统设置页面路由"""
    # 获取当前交易倍率
    current_trade_mul = settings_control.get_trade_mul()
    return render_template('settings.html', now=datetime.now(), current_trade_mul=current_trade_mul)

@settings_bp.route('/api/settings/update', methods=['POST'])
def update_settings():
    """API接口，更新系统设置"""
    try:
        # 获取请求参数
        data = request.get_json()
        trade_mul = data.get('trade_mul')
        
        print(f"DEBUG: 接收到的trade_mul值: {trade_mul}, 类型: {type(trade_mul)}")
        
        if trade_mul is None:
            return jsonify({
                'success': False,
                'message': '缺少必要参数: trade_mul'
            })
        
        # 获取当前用户信息（如果有）
        operator = session.get('username', 'system')
        
        # 使用控制器更新设置
        result = settings_control.update_trade_mul(trade_mul, operator)
        
        print(f"DEBUG: 控制器返回结果: {result}")
        
        return jsonify(result)
    
    except Exception as e:
        print(f"更新设置时发生错误: {e}")
        import traceback
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'更新设置失败: {str(e)}'
        })