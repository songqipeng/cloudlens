#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存装饰器
简化API缓存的使用
"""

from functools import wraps
from typing import Callable, Optional, Any
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


def cache_response(
    ttl_seconds: int = 3600,
    key_prefix: str = "",
    include_params: bool = True
):
    """
    缓存API响应装饰器

    Args:
        ttl_seconds: 缓存时间（秒），默认1小时
        key_prefix: 缓存键前缀
        include_params: 是否将函数参数包含在缓存键中

    Example:
        @cache_response(ttl_seconds=1800, key_prefix="cost_overview")
        def get_cost_overview(account: str, month: str):
            # 计算逻辑
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from core.cache import CacheManager

            # 提取account参数（用于缓存隔离）
            account = kwargs.get('account') or kwargs.get('account_name')
            force_refresh = kwargs.get('force_refresh', False)

            # 生成缓存键
            if include_params:
                # 包含所有参数的哈希
                param_str = json.dumps({
                    'args': str(args),
                    'kwargs': {k: v for k, v in kwargs.items() if k != 'force_refresh'}
                }, sort_keys=True)
                param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
                cache_key = f"{key_prefix or func.__name__}_{param_hash}"
            else:
                cache_key = key_prefix or func.__name__

            # 初始化缓存管理器
            cache_manager = CacheManager(ttl_seconds=ttl_seconds)

            # 检查缓存
            if not force_refresh and account:
                cached = cache_manager.get(
                    resource_type=cache_key,
                    account_name=account
                )
                if cached is not None:
                    logger.debug(f"Cache hit: {cache_key} for account {account}")
                    # 如果返回值是字典，添加cached标记
                    if isinstance(cached, dict):
                        cached['_cached'] = True
                    return cached

            # 执行函数
            logger.debug(f"Cache miss: {cache_key} for account {account}")
            result = func(*args, **kwargs)

            # 保存到缓存
            if account and result is not None:
                cache_manager.set(
                    resource_type=cache_key,
                    account_name=account,
                    data=result
                )
                # 添加cached=False标记
                if isinstance(result, dict):
                    result['_cached'] = False

            return result

        return wrapper
    return decorator


def cache_async_response(
    ttl_seconds: int = 3600,
    key_prefix: str = "",
    include_params: bool = True
):
    """
    异步版本的缓存装饰器

    Args:
        ttl_seconds: 缓存时间（秒）
        key_prefix: 缓存键前缀
        include_params: 是否将函数参数包含在缓存键中

    Example:
        @cache_async_response(ttl_seconds=600)
        async def get_resource_list(account: str):
            # 异步查询
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from core.cache import CacheManager

            # 提取参数
            account = kwargs.get('account') or kwargs.get('account_name')
            force_refresh = kwargs.get('force_refresh', False)

            # 生成缓存键
            if include_params:
                param_str = json.dumps({
                    'args': str(args),
                    'kwargs': {k: v for k, v in kwargs.items() if k != 'force_refresh'}
                }, sort_keys=True)
                param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
                cache_key = f"{key_prefix or func.__name__}_{param_hash}"
            else:
                cache_key = key_prefix or func.__name__

            # 缓存管理器
            cache_manager = CacheManager(ttl_seconds=ttl_seconds)

            # 检查缓存
            if not force_refresh and account:
                cached = cache_manager.get(
                    resource_type=cache_key,
                    account_name=account
                )
                if cached is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    if isinstance(cached, dict):
                        cached['_cached'] = True
                    return cached

            # 执行异步函数
            result = await func(*args, **kwargs)

            # 保存到缓存
            if account and result is not None:
                cache_manager.set(
                    resource_type=cache_key,
                    account_name=account,
                    data=result
                )
                if isinstance(result, dict):
                    result['_cached'] = False

            return result

        return wrapper
    return decorator


class SmartCache:
    """
    智能缓存类

    提供更高级的缓存功能：
    - 自动过期
    - 缓存预热
    - 缓存统计
    """

    def __init__(self, ttl_seconds: int = 3600):
        from core.cache import CacheManager
        self.cache = CacheManager(ttl_seconds=ttl_seconds)
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0
        }

    def get_or_compute(
        self,
        key: str,
        compute_func: Callable,
        account: str,
        **kwargs
    ) -> Any:
        """
        获取缓存或计算

        Args:
            key: 缓存键
            compute_func: 计算函数
            account: 账号名
            **kwargs: 传递给compute_func的参数

        Returns:
            缓存值或计算结果
        """
        # 尝试从缓存获取
        cached = self.cache.get(resource_type=key, account_name=account)
        if cached is not None:
            self.stats['hits'] += 1
            logger.debug(f"Smart cache hit: {key}")
            return cached

        # 缓存未命中，执行计算
        self.stats['misses'] += 1
        logger.debug(f"Smart cache miss: {key}, computing...")

        result = compute_func(**kwargs)

        # 保存到缓存
        self.cache.set(
            resource_type=key,
            account_name=account,
            data=result
        )
        self.stats['sets'] += 1

        return result

    def invalidate(self, key: str, account: str):
        """使缓存失效"""
        # 当前CacheManager没有delete方法，这里可以扩展
        logger.info(f"Cache invalidated: {key} for {account}")
        # TODO: 实现缓存删除

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0

        return {
            **self.stats,
            'total_requests': total,
            'hit_rate_percent': round(hit_rate, 2)
        }
