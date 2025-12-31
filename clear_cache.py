#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清除缓存脚本"""
import sys
import os
sys.path.insert(0, '.')

from core.cache import CacheManager

account = 'ydzn'
cm = CacheManager()

print(f'清除账号 {account} 的缓存...')

# 清除各种缓存
cache_types = [
    'ecs',
    'dashboard_summary', # 仪表盘缓存
    'dashboard_idle',    # 闲置资源缓存
    'idle_result',       # 优化建议缓存
    'cost_overview',     # 成本分析概览缓存 (24h)
    'resource_list_ydzn',
]

for cache_type in cache_types:
    try:
        # 清除缓存
        cm.clear(resource_type=cache_type, account_name=account)
        print(f'  ✅ 已清除缓存: {cache_type}')
    except Exception as e:
        print(f'  ❌ 清除失败 {cache_type}: {e}')

print('\n✅ 所有指定缓存已清理完成。请刷新前端页面查看最新数据。')
