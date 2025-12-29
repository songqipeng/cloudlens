"""
缓存模块

提供缓存管理器和装饰器：
- CacheManager: 资源缓存管理器（支持SQLite和MySQL）
- cache_response: 同步函数缓存装饰器
- cache_async_response: 异步函数缓存装饰器
- SmartCache: 智能缓存类
"""

from .manager import CacheManager

try:
    from .decorators import cache_response, cache_async_response, SmartCache
    __all__ = ['CacheManager', 'cache_response', 'cache_async_response', 'SmartCache']
except ImportError:
    # 装饰器模块不存在时的降级
    __all__ = ['CacheManager']
