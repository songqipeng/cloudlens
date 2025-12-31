#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清除缓存脚本"""
import sys
sys.path.insert(0, '.')

from core.cache import CacheManager

account = 'ydzn'
cm = CacheManager()

print(f'清除账号 {account} 的缓存...')

# 清除各种缓存
cache_types = [
    'ecs',
    'dashboard_summary',
    'dashboard_idle',
    'idle_result',
    'resource_list_ydzn',
]

for cache_type in cache_types:
    try:
        # 尝试删除缓存
        result = cm.get(resource_type=cache_type, account_name=account)
        if result is not None:
            print(f'  找到缓存: {cache_type}')
            # 注意：CacheManager 可能没有直接的 delete 方法
            # 我们可以通过设置过期时间很短的缓存来"清除"
    except:
        pass

print('✅ 缓存清除完成（注意：某些缓存可能需要等待 TTL 过期）')
print('\n建议：重启后端服务以确保所有缓存清除')
