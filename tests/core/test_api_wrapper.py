"""
API封装增强功能单元测试
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from web.frontend.lib.api import apiGet, apiPost, ApiError


class TestApiWrapper:
    """API封装测试类"""

    @pytest.mark.asyncio
    async def test_api_get_success(self):
        """测试: GET请求成功"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json = Mock(return_value={"success": True})
        
        with patch("web.frontend.lib.api.fetch", return_value=mock_response):
            result = await apiGet("/test")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_api_get_retry_on_failure(self):
        """测试: GET请求失败时重试"""
        mock_response_fail = Mock()
        mock_response_fail.ok = False
        mock_response_fail.status = 500
        mock_response_fail.json = Mock(return_value={})
        
        mock_response_success = Mock()
        mock_response_success.ok = True
        mock_response_success.json = Mock(return_value={"success": True})
        
        fetch_mock = AsyncMock(side_effect=[mock_response_fail, mock_response_success])
        
        with patch("web.frontend.lib.api.fetch", fetch_mock):
            result = await apiGet("/test", {}, {"retries": 2})
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_api_get_timeout(self):
        """测试: GET请求超时处理"""
        with patch("web.frontend.lib.api.fetch", side_effect=TimeoutError("Request timeout")):
            with pytest.raises(ApiError):
                await apiGet("/test", {}, {"timeout": 1000})

    @pytest.mark.asyncio
    async def test_api_get_deduplication(self):
        """测试: GET请求去重"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json = Mock(return_value={"success": True})
        
        fetch_mock = AsyncMock(return_value=mock_response)
        
        with patch("web.frontend.lib.api.fetch", fetch_mock):
            # 同时发起两个相同请求
            results = await Promise.all([
                apiGet("/test"),
                apiGet("/test")
            ])
            
            # fetch应该只被调用一次
            assert fetch_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_api_post_success(self):
        """测试: POST请求成功"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json = Mock(return_value={"success": True})
        
        with patch("web.frontend.lib.api.fetch", return_value=mock_response):
            result = await apiPost("/test", {"data": "test"})
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_api_error_class(self):
        """测试: ApiError类"""
        error = ApiError(404, {"error": "Not found"}, "Resource not found")
        assert error.status == 404
        assert error.detail == {"error": "Not found"}
        assert str(error) == "Resource not found"

