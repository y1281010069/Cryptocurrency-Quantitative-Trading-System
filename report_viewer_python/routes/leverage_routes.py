from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import time

# 创建杠杆相关路由蓝图
leverage_bp = Blueprint('leverage', __name__)

# 声明全局变量，这些变量将在app.py中初始化
okx_public_api = None
okx_account_api = None

@leverage_bp.route('/set_max_leverage')
def set_max_leverage_page():
    """设置最大杠杆页面"""
    return render_template('set_max_leverage.html', now=datetime.now())

@leverage_bp.route('/api/set_max_leverage', methods=['POST'])
def set_max_leverage_api():
    """设置最大杠杆API端点"""
    logs = []
    success_count = 0
    failed_count = 0
    
    try:
        # 检查API实例是否初始化
        if not okx_public_api or not okx_account_api:
            return jsonify({
                'success': False,
                'message': 'OKX API未初始化成功，请检查API密钥配置',
                'logs': logs
            })
        
        logs.append({'message': '开始获取永续合约交易对信息...', 'error': False})
        
        # 调用 /api/v5/public/instruments 获取永续合约交易对信息
        instruments_response = okx_public_api.get_instruments(
            instType='SWAP'
        )
        
        if not instruments_response or instruments_response.get('code') != '0':
            error_msg = f'获取交易对信息失败: {instruments_response.get("msg", "未知错误")}'
            logs.append({'message': error_msg, 'error': True})
            return jsonify({
                'success': False,
                'message': error_msg,
                'logs': logs
            })
        
        instruments = instruments_response.get('data', [])
        total_instruments = len(instruments)
        logs.append({'message': f'成功获取到{total_instruments}个永续合约交易对', 'error': False})
        
        # 遍历交易对，设置最大杠杆
        for idx, instrument in enumerate(instruments):
            inst_id = instrument.get('instId')
            max_lever = instrument.get('lever')
            
            if not inst_id or not max_lever:
                failed_count += 1
                logs.append({'message': f'跳过无效交易对: {instrument}', 'error': True})
                continue
            
            try:
                # 调用 /api/v5/account/set-leverage 设置杠杆
                leverage_response = okx_account_api.set_leverage(
                    instId=inst_id,
                    mgnMode='cross',  # 交叉保证金模式
                    lever=max_lever,  # 使用交易对的最大杠杆
                    posSide='long'    # 多头方向
                )
                
                if leverage_response and leverage_response.get('code') == '0':
                    # 同时设置空头方向的杠杆
                    short_response = okx_account_api.set_leverage(
                        instId=inst_id,
                        mgnMode='cross',
                        lever=max_lever,
                        posSide='short'   # 空头方向
                    )
                    
                    if short_response and short_response.get('code') == '0':
                        success_count += 1
                        logs.append({'message': f'成功设置 {inst_id} 杠杆为 {max_lever}x', 'error': False})
                    else:
                        failed_count += 1
                        error_msg = f'设置空头杠杆失败: {short_response.get("msg", "未知错误")}'
                        logs.append({'message': f'{inst_id}: {error_msg}', 'error': True})
                else:
                    failed_count += 1
                    error_msg = f'设置多头杠杆失败: {leverage_response.get("msg", "未知错误")}'
                    logs.append({'message': f'{inst_id}: {error_msg}', 'error': True})
                    
            except Exception as e:
                failed_count += 1
                logs.append({'message': f'{inst_id}: 设置杠杆时发生异常: {str(e)}', 'error': True})
            
            # 避免API请求过于频繁，添加短暂延迟
            if idx < total_instruments - 1:
                time.sleep(0.1)
        
        return jsonify({
            'success': True,
            'message': '设置最大杠杆操作完成',
            'total': total_instruments,
            'successCount': success_count,
            'failedCount': failed_count,
            'logs': logs
        })
        
    except Exception as e:
        logs.append({'message': f'执行过程中发生异常: {str(e)}', 'error': True})
        return jsonify({
            'success': False,
            'message': str(e),
            'logs': logs
        })