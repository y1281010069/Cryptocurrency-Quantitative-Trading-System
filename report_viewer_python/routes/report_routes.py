from flask import Blueprint, render_template, request, jsonify, session
from datetime import datetime
from control.report_control import ReportControl

# 创建报告相关路由蓝图
report_bp = Blueprint('report', __name__)

# 初始化报告控制器
report_control = ReportControl()

@report_bp.route('/')
def index():
    # 检查用户是否已登录
    if 'username' not in session:
        now = datetime.now()
        return render_template('login.html', error='请先登录', now=now)
    
    # 创建当前时间对象
    now = datetime.now()
    
    # 获取用户选择的报告
    report_type = request.args.get('report_type', 'default')
    
    # 尝试获取报告数据
    try:
        report_data = report_control.get_report_data(report_type)
        return render_template('index.html', report_data=report_data, report_type=report_type, username=session.get('username'), now=now)
    except Exception as e:
        error_msg = f"获取报告数据失败: {str(e)}"
        print(error_msg)
        return render_template('index.html', error=error_msg, username=session.get('username'), now=now)