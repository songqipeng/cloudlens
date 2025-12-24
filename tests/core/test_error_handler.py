"""
统一错误处理装饰器单元测试
"""

import pytest
from fastapi import HTTPException
from web.backend.error_handler import api_error_handler


class TestApiErrorHandler:
    """API错误处理装饰器测试类"""

    @pytest.mark.asyncio
    async def test_successful_request(self):
        """测试: 正常请求应该通过"""
        @api_error_handler
        async def test_func():
            return {"success": True, "data": "test"}
        
        result = await test_func()
        assert result["success"] is True
        assert result["data"] == "test"

    @pytest.mark.asyncio
    async def test_http_exception_passthrough(self):
        """测试: HTTPException应该直接抛出"""
        @api_error_handler
        async def test_func():
            raise HTTPException(status_code=404, detail="Not found")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"

    @pytest.mark.asyncio
    async def test_generic_exception_handling(self):
        """测试: 通用异常应该被转换为HTTPException"""
        @api_error_handler
        async def test_func():
            raise ValueError("Test error")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == 500
        assert "success" in exc_info.value.detail
        assert exc_info.value.detail["success"] is False
        assert "error" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_not_found_error_detection(self):
        """测试: 404错误检测"""
        @api_error_handler
        async def test_func():
            raise Exception("Resource not found")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_permission_error_detection(self):
        """测试: 403错误检测"""
        @api_error_handler
        async def test_func():
            raise Exception("Permission denied")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_request_error_detection(self):
        """测试: 400错误检测"""
        @api_error_handler
        async def test_func():
            raise Exception("Invalid request")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == 400






