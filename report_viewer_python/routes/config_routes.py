from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import os
import re
import json
import traceback

# 创建配置相关路由蓝图
config_bp = Blueprint('config', __name__)

@config_bp.route('/trading_config')
def trading_config():
    """交易配置修改页面路由"""
    return render_template('trading_config.html', now=datetime.now())

@config_bp.route('/api/get_trading_config')
def api_get_trading_config():
    """API接口，获取当前交易配置"""
    print("=== 收到/api/get_trading_config请求 ===")
    try:
        # 打印请求信息
        print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 尝试导入配置
        from config import TRADING_CONFIG
        print("交易配置获取成功")
        return jsonify({
            'success': True,
            'config': TRADING_CONFIG
        })
    except Exception as e:
        print(f"获取交易配置时发生错误: {e}")
        # 打印更详细的错误信息
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'errorType': type(e).__name__
        })

@config_bp.route('/api/save_trading_config', methods=['POST'])
def api_save_trading_config():
    """API接口，保存交易配置"""
    print("=== 收到/api/save_trading_config请求 ===")
    try:
        # 打印请求信息
        print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 获取请求数据
        config_data = request.get_json()
        print(f"接收到的配置数据: {config_data}")
        
        # 读取当前config.py文件内容
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config.py')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        # 找到TRADING_CONFIG部分并替换
        # 定义新的TRADING_CONFIG内容
        # 使用json.dumps转换，然后将JSON的小写布尔值替换为Python的大写布尔值
        new_config_str = json.dumps(config_data, ensure_ascii=False, indent=4)
        # 替换小写的true/false为大写的True/False
        new_config_str = new_config_str.replace('true', 'True').replace('false', 'False')
        new_config_content = f"TRADING_CONFIG = {new_config_str}"
        
        # 替换文件中的TRADING_CONFIG部分
        updated_config_content = re.sub(r'TRADING_CONFIG = \{[\s\S]*?\}', new_config_content, config_content, flags=re.MULTILINE)
        
        # 写回文件
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(updated_config_content)
        
        print("交易配置保存成功")
        return jsonify({
            'success': True,
            'message': '交易配置保存成功'
        })
    except Exception as e:
        print(f"保存交易配置时发生错误: {e}")
        # 打印更详细的错误信息
        print(f"错误堆栈:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'errorType': type(e).__name__
        })