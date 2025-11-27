#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ErrorHandler 单元测试
"""

import pytest
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException

from utils.error_handler import BusinessError, ErrorHandler, RetryableError


class TestErrorHandler:
    """错误处理器测试类"""

    def test_handle_business_error(self):
        """测试处理业务错误（4xx）"""
        error = ClientException("400", "InvalidParameter", "参数错误")
        result = ErrorHandler.handle_api_error(error, "RDS", "cn-hangzhou", "rds-001")

        assert isinstance(result, BusinessError)

    def test_handle_retryable_error(self):
        """测试处理可重试错误（5xx）"""
        error = ServerException("500", "InternalError", "服务器错误")
        result = ErrorHandler.handle_api_error(error, "RDS", "cn-hangzhou", "rds-001")

        assert isinstance(result, RetryableError)

    def test_handle_network_error(self):
        """测试处理网络错误"""
        error = ConnectionError("网络连接失败")
        result = ErrorHandler.handle_api_error(error, "RDS")

        assert isinstance(result, RetryableError)

    def test_is_retryable(self):
        """测试判断是否可重试"""
        business_error = ClientException("400", "InvalidParameter", "参数错误")
        retryable_error = ServerException("500", "InternalError", "服务器错误")

        assert ErrorHandler.is_retryable(business_error) is False
        assert ErrorHandler.is_retryable(retryable_error) is True

    def test_handle_region_error(self, caplog):
        """测试区域级错误处理"""
        error = ClientException("403", "Forbidden", "权限不足")
        ErrorHandler.handle_region_error(error, "cn-hangzhou", "RDS")

        # 验证错误已记录但不抛出异常
        assert "cn-hangzhou" in caplog.text
