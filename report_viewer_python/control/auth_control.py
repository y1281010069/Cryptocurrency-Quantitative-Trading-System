class AuthControl:
    """认证控制器，处理用户登录、注销等认证相关业务逻辑"""
    
    def __init__(self):
        # 在实际应用中，这里可以初始化数据库连接或其他认证服务
        pass
    
    def authenticate_user(self, username, password):
        """
        验证用户凭据
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            dict: {"success": bool, "message": str}
        """
        # 这里使用硬编码的用户凭据验证
        # 在实际应用中，应该从数据库或其他安全存储中验证用户
        if username == 'admin' and password == 'adminadmin':
            return {"success": True, "message": "登录成功", "user_info": {"username": username}}
        else:
            return {"success": False, "message": "用户名或密码错误"}
    
    def validate_user_session(self, session_data):
        """
        验证用户会话是否有效
        
        Args:
            session_data: Flask session对象
            
        Returns:
            bool: 会话是否有效
        """
        return 'logged_in' in session_data and session_data['logged_in']
    
    def get_current_user(self, session_data):
        """
        获取当前登录用户信息
        
        Args:
            session_data: Flask session对象
            
        Returns:
            dict or None: 用户信息或None（未登录时）
        """
        if self.validate_user_session(session_data):
            return {
                "username": session_data.get('username')
            }
        return None
    
    def logout_user(self, session_data):
        """
        用户登出，清除会话数据
        
        Args:
            session_data: Flask session对象
            
        Returns:
            dict: {"success": True, "message": str}
        """
        session_data.clear()
        return {"success": True, "message": "成功登出"}