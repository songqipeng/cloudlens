# -*- coding: utf-8 -*-
"""
Redis缓存管理器
用于缓存API响应，提升性能
"""

import json
import hashlib
import logging
import os
from functools import wraps
from typing import Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Redis客户端单例
_redis_client = None


def get_redis_client():
    """获取Redis客户端（懒加载）"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", 6379))
            redis_db = int(os.getenv("REDIS_DB", 0))
            _redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # 测试连接
            _redis_client.ping()
            logger.info(f"Redis连接成功: {redis_host}:{redis_port}")
        except Exception as e:
            logger.warning(f"Redis连接失败，将跳过缓存: {e}")
            _redis_client = None
    return _redis_client


def cache_key(prefix: str, *args, **kwargs) -> str:
    """生成缓存键"""
    key_parts = [prefix]
    for arg in args:
        key_parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        if v is not None:
            key_parts.append(f"{k}={v}")
    key_str = ":".join(key_parts)
    return f"cloudlens:{hashlib.md5(key_str.encode()).hexdigest()[:16]}:{prefix}"


def redis_cache(prefix: str, ttl: int = 300):
    """
    Redis缓存装饰器
    
    Args:
        prefix: 缓存键前缀
        ttl: 缓存过期时间（秒），默认5分钟
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            redis_client = get_redis_client()
            
            # 如果Redis不可用，直接执行函数
            if redis_client is None:
                return func(*args, **kwargs)
            
            # 生成缓存键
            key = cache_key(prefix, *args, **kwargs)
            
            try:
                # 尝试从缓存获取
                cached = redis_client.get(key)
                if cached:
                    logger.debug(f"Redis缓存命中: {key}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis读取失败: {e}")
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 写入缓存
            try:
                redis_client.setex(key, ttl, json.dumps(result, default=str))
                logger.debug(f"Redis缓存已设置: {key}, TTL={ttl}s")
            except Exception as e:
                logger.warning(f"Redis写入失败: {e}")
            
            return result
        return wrapper
    return decorator


class DiscountAnalysisCache:
    """折扣分析缓存管理"""
    
    DEFAULT_TTL = 300  # 5分钟
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """从缓存获取数据"""
        redis_client = get_redis_client()
        if redis_client is None:
            return None
        try:
            cached = redis_client.get(f"discount:{key}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis读取失败: {e}")
        return None
    
    @staticmethod
    def set(key: str, value: Any, ttl: int = None):
        """设置缓存数据"""
        redis_client = get_redis_client()
        if redis_client is None:
            return
        try:
            ttl = ttl or DiscountAnalysisCache.DEFAULT_TTL
            redis_client.setex(f"discount:{key}", ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.warning(f"Redis写入失败: {e}")
    
    @staticmethod
    def clear_pattern(pattern: str = "*"):
        """清除匹配模式的缓存"""
        redis_client = get_redis_client()
        if redis_client is None:
            return 0
        try:
            keys = redis_client.keys(f"discount:{pattern}")
            if keys:
                return redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis清除失败: {e}")
        return 0
