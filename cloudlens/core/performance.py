#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控模块
提供性能监控装饰器和性能分析工具
"""

import time
import functools
import logging
from typing import Callable, Any, Dict, Optional
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.metrics: Dict[str, list] = {}
        self.slow_threshold = 1.0  # 慢查询阈值（秒）

    def record(self, function_name: str, duration: float, **metadata):
        """记录性能数据"""
        if function_name not in self.metrics:
            self.metrics[function_name] = []

        self.metrics[function_name].append({
            'duration': duration,
            'timestamp': datetime.now(),
            **metadata
        })

        # 保留最近100次记录
        if len(self.metrics[function_name]) > 100:
            self.metrics[function_name] = self.metrics[function_name][-100:]

    def get_stats(self, function_name: str) -> Optional[Dict]:
        """获取性能统计"""
        if function_name not in self.metrics or not self.metrics[function_name]:
            return None

        durations = [m['duration'] for m in self.metrics[function_name]]
        return {
            'count': len(durations),
            'avg': sum(durations) / len(durations),
            'min': min(durations),
            'max': max(durations),
            'p50': sorted(durations)[len(durations) // 2],
            'p95': sorted(durations)[int(len(durations) * 0.95)],
            'p99': sorted(durations)[int(len(durations) * 0.99)],
        }

    def get_all_stats(self) -> Dict[str, Dict]:
        """获取所有函数的性能统计"""
        return {
            func: self.get_stats(func)
            for func in self.metrics.keys()
        }


# 全局性能监控器实例
_monitor = PerformanceMonitor()


def performance_monitor(
    slow_threshold: float = 1.0,
    log_all: bool = False,
    log_level: int = logging.WARNING
):
    """
    性能监控装饰器

    Args:
        slow_threshold: 慢查询阈值（秒），超过此时间会记录WARNING日志
        log_all: 是否记录所有调用（DEBUG级别）
        log_level: 慢查询的日志级别

    Example:
        @performance_monitor(slow_threshold=2.0)
        def analyze_resources(account: str):
            # 自动记录执行时间
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            function_name = f"{func.__module__}.{func.__name__}"
            error = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                elapsed = time.time() - start_time

                # 记录到监控器
                _monitor.record(
                    function_name,
                    elapsed,
                    error=error,
                    args_count=len(args),
                    kwargs_count=len(kwargs)
                )

                # 日志记录
                if error:
                    logger.error(
                        f"{func.__name__} failed after {elapsed:.3f}s: {error}",
                        extra={
                            'function': function_name,
                            'duration': elapsed,
                            'error': error
                        }
                    )
                elif elapsed > slow_threshold:
                    logger.log(
                        log_level,
                        f"⚠️  SLOW: {func.__name__} took {elapsed:.3f}s",
                        extra={
                            'function': function_name,
                            'duration': elapsed,
                            'slow_query': True
                        }
                    )
                elif log_all:
                    logger.debug(
                        f"{func.__name__} took {elapsed:.3f}s",
                        extra={
                            'function': function_name,
                            'duration': elapsed
                        }
                    )

        return wrapper
    return decorator


@contextmanager
def performance_timer(name: str, slow_threshold: float = 1.0):
    """
    性能计时上下文管理器

    Example:
        with performance_timer("database_query"):
            results = db.query("SELECT * FROM table")
    """
    start_time = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start_time
        _monitor.record(name, elapsed)

        if elapsed > slow_threshold:
            logger.warning(
                f"⚠️  SLOW: {name} took {elapsed:.3f}s",
                extra={
                    'operation': name,
                    'duration': elapsed,
                    'slow_query': True
                }
            )
        else:
            logger.debug(
                f"{name} took {elapsed:.3f}s",
                extra={
                    'operation': name,
                    'duration': elapsed
                }
            )


def get_performance_stats(function_name: Optional[str] = None) -> Dict:
    """
    获取性能统计

    Args:
        function_name: 函数名，None表示获取所有统计

    Returns:
        性能统计字典
    """
    if function_name:
        return _monitor.get_stats(function_name)
    return _monitor.get_all_stats()


def reset_performance_stats():
    """重置性能统计"""
    _monitor.metrics.clear()


# 数据库查询性能监控装饰器
def monitor_db_query(func: Callable) -> Callable:
    """
    数据库查询性能监控装饰器
    自动识别慢查询（>500ms）

    Example:
        @monitor_db_query
        def query_bill_items(self, account_id: str):
            return self.db.query("SELECT * FROM bill_items WHERE ...")
    """
    return performance_monitor(slow_threshold=0.5, log_level=logging.WARNING)(func)


# API调用性能监控装饰器
def monitor_api_call(func: Callable) -> Callable:
    """
    API调用性能监控装饰器
    自动识别慢API（>2s）

    Example:
        @monitor_api_call
        def list_ecs_instances(self):
            return self.client.describe_instances()
    """
    return performance_monitor(slow_threshold=2.0, log_level=logging.WARNING)(func)


# 分析任务性能监控装饰器
def monitor_analysis_task(func: Callable) -> Callable:
    """
    分析任务性能监控装饰器
    自动识别慢任务（>5s）

    Example:
        @monitor_analysis_task
        def analyze_idle_resources(self, account: str):
            ...
    """
    return performance_monitor(slow_threshold=5.0, log_level=logging.INFO)(func)
