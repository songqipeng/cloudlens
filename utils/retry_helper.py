#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API重试机制
使用tenacity库实现智能重试，提升稳定性
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
    before_sleep_log
)
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def retry_api_call(
    max_attempts: int = 3,
    min_wait: int = 2,
    max_wait: int = 10,
    retry_exceptions: tuple = None
):
    """
    API调用重试装饰器
    
    Args:
        max_attempts: 最大重试次数（默认3次）
        min_wait: 最小等待时间（秒）
        max_wait: 最大等待时间（秒）
        retry_exceptions: 需要重试的异常类型元组
    
    Returns:
        装饰器函数
    """
    if retry_exceptions is None:
        # 默认只重试网络错误和服务器错误，不重试400/403等业务错误
        retry_exceptions = (
            ConnectionError,
            TimeoutError,
            OSError,
        )
    
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(retry_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 检查是否是HTTP错误（400, 403等），这些不应该重试
                error_str = str(e)
                if any(code in error_str for code in ['400', '403', '404', 'Invalid', 'Forbidden']):
                    logger.debug(f"业务错误，不重试: {func.__name__} - {error_str[:100]}")
                    raise  # 直接抛出，不重试
                logger.warning(f"API调用失败，将重试: {func.__name__} - {e}")
                raise
        
        return wrapper
    return decorator


# 便捷函数：直接包装API调用
def call_with_retry(func: Callable, *args, **kwargs) -> Any:
    """
    直接调用带重试的函数
    
    Args:
        func: 要调用的函数
        *args, **kwargs: 函数参数
    
    Returns:
        函数返回值
    """
    @retry_api_call()
    def _call():
        return func(*args, **kwargs)
    
    return _call()

