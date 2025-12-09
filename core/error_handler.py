"""全局错误处理装饰器"""
import functools
import logging
from rich.console import Console

from core.exceptions import (
    CloudLensException,
    AuthenticationError,
    APIError,
    ConfigurationError,
    ResourceNotFoundError,
)

console = Console()
logger = logging.getLogger(__name__)


def handle_exceptions(func):
    """
    CLI命令级别的全局异常处理装饰器
    
    用法:
        @handle_exceptions
        @click.command()
        def query_ecs(...):
            pass
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except AuthenticationError as e:
            console.print(f"[red]❌ {e}[/red]")
            console.print(
                "\\n[dim]💡 建议: 运行 'cl config verify --account <name>' 验证凭证[/dim]"
            )
            logger.error(f"Authentication failed: {e}")
            return None

        except APIError as e:
            console.print(f"[red]❌ API调用失败[/red]")
            console.print(f"   API: {e.api_name}")
            console.print(f"   错误码: {e.error_code}")
            console.print(f"   信息: {e}")
            logger.error(f"API call failed: {e}")
            return None

        except ConfigurationError as e:
            console.print(f"[yellow]⚠️  配置错误: {e}[/yellow]")
            console.print("\\n[dim]💡 建议: 运行 'cl config list' 查看配置[/dim]")
            logger.warning(f"Configuration error: {e}")
            return None

        except ResourceNotFoundError as e:
            console.print(f"[yellow]⚠️  资源未找到: {e}[/yellow]")
            logger.warning(f"Resource not found: {e}")
            return None

        except CloudLensException as e:
            console.print(f"[yellow]⚠️  {e}[/yellow]")
            logger.warning(str(e))
            return None

        except KeyboardInterrupt:
            console.print("\\n[yellow]⏹️  操作已取消[/yellow]")
            return None

        except Exception as e:
            # 未知异常
            console.print(f"[red]❌ 未知错误: {type(e).__name__}[/red]")
            console.print(f"   {e}")
            console.print(
                "\\n[dim]请查看日志文件或联系技术支持\\n运行 'cl --help' 获取帮助[/dim]"
            )
            logger.exception("Unexpected error")
            return None

    return wrapper


def handle_provider_errors(func):
    """
    Provider层异常处理装饰器
    将SDK异常转换为CloudLens异常
    
    用法:
        @handle_provider_errors
        def list_instances(self):
            pass
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except CloudLensException:
            # 已经是CloudLens异常,直接抛出
            raise

        except Exception as sdk_error:
            # 转换SDK异常为CloudLens异常
            error_msg = str(sdk_error)
            error_code = getattr(sdk_error, "error_code", getattr(sdk_error, "code", "Unknown"))

            # 识别常见错误
            if (
                "InvalidAccessKeyId"  in error_msg
                or "SignatureDoesNotMatch" in error_msg
                or "IncompleteSignature" in error_msg
            ):
                # 认证错误
                provider_name = getattr(args[0], "provider_name", "unknown") if args else "unknown"
                raise AuthenticationError(provider=provider_name, message=error_msg)

            elif "Forbidden" in error_msg or "Denied" in error_msg or "NoPermission" in error_msg:
                # 权限错误
                from core.exceptions import PermissionError

                provider_name = getattr(args[0], "provider_name", "unknown") if args else "unknown"
                raise PermissionError(
                    provider=provider_name, action=func.__name__, message=error_msg
                )

            elif "NotFound" in error_msg or "NotExist" in error_msg:
                # 资源未找到
                resource_id = kwargs.get("resource_id", "unknown")
                raise ResourceNotFoundError(resource_type=func.__name__, resource_id=resource_id)

            else:
                # 通用API错误
                provider_name = getattr(args[0], "provider_name", "unknown") if args else "unknown"
                raise APIError(
                    provider=provider_name,
                    api_name=func.__name__,
                    error_code=error_code,
                    message=error_msg,
                )

    return wrapper
