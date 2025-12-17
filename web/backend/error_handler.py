"""
统一API错误处理装饰器
提供一致的错误响应格式和日志记录
"""

from functools import wraps
from fastapi import HTTPException
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)


def api_error_handler(func: Callable) -> Callable:
    """
    统一API错误处理装饰器
    
    用法:
        @router.get("/endpoint")
        @api_error_handler
        async def my_endpoint():
            # ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # 如果是异步函数，使用await
            if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except HTTPException:
            # 重新抛出HTTPException，保持原有状态码和详情
            raise
        except Exception as e:
            # 记录详细错误信息
            logger.error(
                f"API error in {func.__name__}: {e}",
                exc_info=True,
                extra={
                    "function": func.__name__,
                    "args": str(args)[:200],  # 限制长度
                    "kwargs": str(kwargs)[:200]
                }
            )
            
            # 统一错误响应格式
            error_detail = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "endpoint": func.__name__
            }
            
            # 根据错误类型设置状态码
            status_code = 500
            if "not found" in str(e).lower() or "不存在" in str(e):
                status_code = 404
            elif "permission" in str(e).lower() or "权限" in str(e) or "forbidden" in str(e).lower():
                status_code = 403
            elif "invalid" in str(e).lower() or "无效" in str(e) or "bad request" in str(e).lower():
                status_code = 400
            
            raise HTTPException(status_code=status_code, detail=error_detail)
    
    return wrapper

