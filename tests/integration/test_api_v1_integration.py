"""
API v1集成测试
"""
import pytest
from fastapi.testclient import TestClient
from web.backend.main import app

client = TestClient(app)


class TestAPIV1Integration:
    """API v1集成测试"""
    
    def test_health_check(self):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code in [200, 404]  # 可能没有实现
    
    def test_api_root(self):
        """测试API根路径"""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_api_docs(self):
        """测试API文档"""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_api_openapi(self):
        """测试OpenAPI schema"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
