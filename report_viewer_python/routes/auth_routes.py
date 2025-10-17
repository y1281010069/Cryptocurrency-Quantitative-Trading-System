from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps

# 创建认证相关路由蓝图
auth_bp = Blueprint('auth', __name__)

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面路由"""
    if request.method == 'POST':
        # 支持JSON和表单数据两种方式
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            remember_me = data.get('remember_me', False)
        else:
            username = request.form.get('username')
            password = request.form.get('password')
            remember_me = request.form.get('remember_me', False)
        
        # 验证用户名和密码
        if username == 'admin' and password == 'adminadmin':
            # 登录成功
            session['logged_in'] = True
            session['username'] = username
            
            # 如果选择了"记住我"，设置会话为永久会话（30天）
            if remember_me or remember_me == 'on':
                session.permanent = True
            
            return jsonify({'success': True, 'message': '登录成功'})
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误'})
    
    # GET请求，显示登录页面
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """登出路由"""
    session.clear()
    return redirect(url_for('auth.login'))