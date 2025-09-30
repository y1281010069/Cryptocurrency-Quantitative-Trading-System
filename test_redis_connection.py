#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Redis连接测试脚本
测试从Redis服务器读取okx_positions_data字段的内容
"""

import redis
import time
from config import REDIS_CONFIG


def test_redis_connection():
    """测试Redis连接并读取okx_positions_data字段"""
    try:
        print("开始测试Redis连接...")
        print(f"连接信息: 地址={REDIS_CONFIG['ADDR']}, 密码={'*' * len(REDIS_CONFIG['PASSWORD'])}")
        
        # 解析Redis地址
        host, port = REDIS_CONFIG['ADDR'].split(':')
        port = int(port)
        
        # 创建Redis连接对象
        start_time = time.time()
        r = redis.Redis(
            host=host,
            port=port,
            password=REDIS_CONFIG['PASSWORD'],
            decode_responses=True,  # 自动将返回的字节转为字符串
            socket_timeout=10       # 设置超时时间为10秒
            # 注意：retry_on_timeout参数在Redis 6.0.0后已被移除，TimeoutError默认包含在重试逻辑中
        )
        
        # 测试连接
        response = r.ping()
        connect_time = time.time() - start_time
        print(f"✅ Redis连接成功! 响应时间: {connect_time:.3f}秒")
        
        # 读取okx_positions_data字段
        print("\n尝试读取okx_positions_data字段...")
        start_time = time.time()
        positions_data = r.get('okx_positions_data')
        read_time = time.time() - start_time
        
        if positions_data:
            print(f"✅ 成功读取okx_positions_data字段! 读取时间: {read_time:.3f}秒")
            print(f"数据长度: {len(positions_data)} 字符")
            # 显示部分数据内容预览
            preview_length = min(500, len(positions_data))
            print(f"数据预览 (前{preview_length}字符):")
            print("=" * 60)
            print(positions_data[:preview_length])
            print("=" * 60)
        else:
            print("⚠️ okx_positions_data字段不存在或为空")
            
        # 获取Redis服务器信息
        print("\nRedis服务器信息:")
        info = r.info()
        print(f"服务器版本: {info.get('redis_version', '未知')}")
        print(f"运行模式: {info.get('redis_mode', '未知')}")
        print(f"内存使用: {info.get('used_memory_human', '未知')}")
        
    except redis.RedisError as e:
        print(f"❌ Redis连接错误: {str(e)}")
    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")
    

if __name__ == "__main__":
    test_redis_connection()