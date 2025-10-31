#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一错误处理器
提供统一的错误分类和处理机制
"""

import logging
from typing import Optional, Callable, Any
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """可重试的错误"""
    pass


class BusinessError(Exception):
    """业务错误（不应重试）"""
    pass


class ErrorHandler:
    """统一错误处理器"""
    
    @staticmethod
    def handle_api_error(e: Exception, resource_type: str, region: str = None, 
                        instance_id: str = None) -> Optional[Exception]:
        """
        处理API错误
        
        Args:
            e: 异常对象
            resource_type: 资源类型
            region: 区域（可选）
            instance_id: 实例ID（可选）
        
        Returns:
            如果是可重试错误，返回RetryableError；如果是业务错误，返回BusinessError；否则返回None
        """
        context = f"{resource_type}"
        if region:
            context += f" {region}"
        if instance_id:
            context += f" {instance_id}"
        
        # 阿里云API异常
        if isinstance(e, (ClientException, ServerException)):
            error_code = getattr(e, 'error_code', None)
            error_msg = getattr(e, 'message', str(e))
            
            # 业务错误（4xx）：权限、参数错误等，不应重试
            if error_code and error_code.startswith('4'):
                logger.warning(f"{context}: 业务错误 {error_code} - {error_msg}")
                return BusinessError(f"业务错误 {error_code}: {error_msg}")
            
            # 服务器错误（5xx）：可重试
            elif error_code and error_code.startswith('5'):
                logger.error(f"{context}: 服务器错误 {error_code} - {error_msg}，可重试")
                return RetryableError(f"服务器错误 {error_code}: {error_msg}")
            
            # 网络错误：可重试
            elif 'Connection' in str(e) or 'Timeout' in str(e) or 'Network' in str(e):
                logger.error(f"{context}: 网络错误 - {error_msg}，可重试")
                return RetryableError(f"网络错误: {error_msg}")
            
            # 其他API错误：默认不重试
            else:
                logger.warning(f"{context}: API错误 {error_code} - {error_msg}")
                return BusinessError(f"API错误 {error_code}: {error_msg}")
        
        # 通用网络错误
        elif isinstance(e, (ConnectionError, TimeoutError, OSError)):
            logger.error(f"{context}: 网络错误 - {e}，可重试")
            return RetryableError(f"网络错误: {e}")
        
        # 其他异常：不重试
        else:
            logger.error(f"{context}: 未知错误 - {e}")
            return BusinessError(f"未知错误: {e}")
    
    @staticmethod
    def handle_region_error(e: Exception, region: str, resource_type: str):
        """
        处理区域级错误（错误隔离，继续处理其他区域）
        
        Args:
            e: 异常对象
            region: 区域
            resource_type: 资源类型
        """
        error_type = ErrorHandler.handle_api_error(e, resource_type, region)
        
        if isinstance(error_type, RetryableError):
            logger.warning(f"区域 {region} ({resource_type}) 分析失败（可重试错误）: {e}")
        else:
            logger.warning(f"区域 {region} ({resource_type}) 分析失败（业务错误）: {e}")
        
        # 继续处理其他区域（不抛出异常）
    
    @staticmethod
    def handle_instance_error(e: Exception, instance_id: str, region: str, 
                             resource_type: str, continue_on_error: bool = True):
        """
        处理实例级错误
        
        Args:
            e: 异常对象
            instance_id: 实例ID
            region: 区域
            resource_type: 资源类型
            continue_on_error: 是否在错误时继续处理其他实例
        
        Returns:
            如果continue_on_error=True，返回None；否则抛出异常
        """
        error_type = ErrorHandler.handle_api_error(e, resource_type, region, instance_id)
        
        if isinstance(error_type, RetryableError):
            logger.warning(f"实例 {instance_id} ({resource_type}) 处理失败（可重试错误）: {e}")
        else:
            logger.warning(f"实例 {instance_id} ({resource_type}) 处理失败（业务错误）: {e}")
        
        if not continue_on_error:
            raise error_type or e
        
        return None
    
    @staticmethod
    def is_retryable(e: Exception) -> bool:
        """
        判断错误是否可重试
        
        Args:
            e: 异常对象
        
        Returns:
            是否可重试
        """
        error_type = ErrorHandler.handle_api_error(e, "unknown")
        return isinstance(error_type, RetryableError)
    
    @staticmethod
    def wrap_function(func: Callable, resource_type: str, 
                     error_handler: Optional[Callable] = None) -> Callable:
        """
        包装函数，自动处理错误
        
        Args:
            func: 要包装的函数
            resource_type: 资源类型
            error_handler: 自定义错误处理函数（可选）
        
        Returns:
            包装后的函数
        """
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if error_handler:
                    return error_handler(e, *args, **kwargs)
                else:
                    ErrorHandler.handle_api_error(e, resource_type)
                    raise
        return wrapper

