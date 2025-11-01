import redis
import json
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

class SettingsControl:
    """系统设置控制器"""
    
    def __init__(self):
        """初始化设置控制器"""
        self.redis_client = self._get_redis_client()
    
    def _get_redis_client(self):
        """获取Redis客户端连接"""
        try:
            # 解析Redis地址
            addr = REDIS_CONFIG.get('ADDR', 'localhost:6379')
            password = REDIS_CONFIG.get('PASSWORD', '')
            
            if ':' in addr:
                host, port = addr.split(':')
                port = int(port)
            else:
                host = addr
                port = 6379
            
            # 创建Redis连接
            if password:
                redis_client = redis.Redis(host=host, port=port, password=password, decode_responses=True)
            else:
                redis_client = redis.Redis(host=host, port=port, decode_responses=True)
            
            # 测试连接
            redis_client.ping()
            return redis_client
        
        except Exception as e:
            print(f"连接Redis失败: {e}")
            return None
    
    def get_trade_mul(self):
        """从Redis获取交易倍率，如果不存在则返回默认值1.0"""
        try:
            if self.redis_client:
                trade_mul = self.redis_client.get('trade_mul')
                if trade_mul:
                    return float(trade_mul)
            
            # 如果Redis中没有值或连接失败，返回默认值
            return 1.0
        
        except Exception as e:
            print(f"获取交易倍率失败: {e}")
            return 1.0
    
    def update_trade_mul(self, trade_mul, operator='system'):
        """更新交易倍率
        
        Args:
            trade_mul (float): 新的交易倍率
            operator (str): 操作者
            
        Returns:
            dict: 操作结果
        """
        try:
            # 如果trade_mul是字符串，尝试转换为数字
            if isinstance(trade_mul, str):
                try:
                    trade_mul = float(trade_mul)
                except ValueError:
                    return {
                        'success': False,
                        'message': '交易倍率必须是数字'
                    }
            
            # 验证trade_mul值
            if not isinstance(trade_mul, (int, float)):
                return {
                    'success': False,
                    'message': '交易倍率必须是数字'
                }
            
            if trade_mul < 0.1 or trade_mul > 10:
                return {
                    'success': False,
                    'message': '交易倍率必须在0.1到10之间'
                }
            
            if not self.redis_client:
                return {
                    'success': False,
                    'message': '无法连接到Redis服务器'
                }
            
            # 获取当前值
            current_value = self.get_trade_mul()
            
            # 更新trade_mul值
            self.redis_client.set('trade_mul', str(trade_mul))
            
            return {
                'success': True,
                'message': '设置已保存',
                'trade_mul': trade_mul
            }
        
        except Exception as e:
            print(f"更新交易倍率失败: {e}")
            import traceback
            print(f"错误堆栈:\n{traceback.format_exc()}")
            return {
                'success': False,
                'message': f'更新交易倍率失败: {str(e)}'
            }