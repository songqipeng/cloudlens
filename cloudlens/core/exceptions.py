# -*- coding: utf-8 -*-
"""
CloudLens自定义异常层次结构
"""


class CloudLensException(Exception):
    """CloudLens基础异常类"""

    pass


class ConfigurationError(CloudLensException):
    """配置错误"""

    pass


class ProviderError(CloudLensException):
    """云厂商Provider相关错误"""

    pass


class AuthenticationError(ProviderError):
    """认证失败错误"""

    def __init__(self, provider: str, message: str = None):
        self.provider = provider
        default_msg = f"{provider} 认证失败，请检查AccessKey和SecretKey"
        super().__init__(message or default_msg)


class PermissionError(ProviderError):
    """权限不足错误"""

    def __init__(self, provider: str, action: str, message: str = None):
        self.provider = provider
        self.action = action
        default_msg = f"{provider} 权限不足，无法执行 {action}"
        super().__init__(message or default_msg)


class ResourceNotFoundError(ProviderError):
    """资源未找到错误"""

    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} {resource_id} 未找到")


class APIError(ProviderError):
    """API调用错误"""

    def __init__(self, provider: str, api_name: str, error_code: str = None, message: str = None):
        self.provider = provider
        self.api_name = api_name
        self.error_code = error_code
        super().__init__(message or f"{provider} API调用失败: {api_name} (错误码: {error_code})")


class NetworkError(CloudLensException):
    """网络连接错误"""

    pass


class DataValidationError(CloudLensException):
    """数据验证错误"""

    pass


class CacheError(CloudLensException):
    """缓存操作错误"""

    pass


class ReportGenerationError(CloudLensException):
    """报告生成错误"""

    pass


class RemediationError(CloudLensException):
    """自动修复错误"""

    def __init__(self, action: str, resource_id: str, message: str = None):
        self.action = action
        self.resource_id = resource_id
        super().__init__(message or f"修复操作 {action} 在资源 {resource_id} 上失败")
