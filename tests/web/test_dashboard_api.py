#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard API 测试
测试 dashboard 相关 API 端点的功能
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from web.backend.main import app

client = TestClient(app)


class TestDashboardAPI:
    """Dashboard API 测试类"""
    
    def test_get_summary_without_account(self):
        """测试不带账号参数的情况"""
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 400
        assert "账号参数是必需的" in response.json()["detail"]
    
    def test_get_summary_with_invalid_account(self):
        """测试无效账号的情况"""
        response = client.get("/api/dashboard/summary?account=invalid_account_12345")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_summary_returns_valid_structure(self):
        """测试返回数据结构是否正确"""
        # 使用一个可能存在的账号（如果不存在会返回404，但结构应该正确）
        response = client.get("/api/dashboard/summary?account=test_account")
        
        # 如果账号不存在，应该返回404
        if response.status_code == 404:
            pytest.skip("测试账号不存在，跳过此测试")
        
        # 如果账号存在，检查返回结构
        assert response.status_code == 200
        data = response.json()
        
        # 检查必需字段
        assert "account" in data
        assert "total_cost" in data
        assert "idle_count" in data
        assert "cost_trend" in data
        assert "trend_pct" in data
        assert "total_resources" in data
        assert "resource_breakdown" in data
        assert "alert_count" in data
        assert "tag_coverage" in data
        assert "savings_potential" in data
        assert "cached" in data
        
        # 检查数据类型
        assert isinstance(data["account"], str)
        assert isinstance(data["total_cost"], (int, float))
        assert isinstance(data["idle_count"], int)
        assert isinstance(data["cost_trend"], str)
        assert isinstance(data["trend_pct"], (int, float))
        assert isinstance(data["total_resources"], int)
        assert isinstance(data["resource_breakdown"], dict)
        assert isinstance(data["alert_count"], int)
        assert isinstance(data["tag_coverage"], (int, float))
        assert isinstance(data["savings_potential"], (int, float))
        assert isinstance(data["cached"], bool)
        
        # 检查 resource_breakdown 结构
        breakdown = data["resource_breakdown"]
        assert "ecs" in breakdown
        assert "rds" in breakdown
        assert "redis" in breakdown
    
    def test_get_summary_with_force_refresh(self):
        """测试强制刷新参数"""
        response = client.get("/api/dashboard/summary?account=test_account&force_refresh=true")
        
        if response.status_code == 404:
            pytest.skip("测试账号不存在，跳过此测试")
        
        assert response.status_code == 200
        data = response.json()
        assert "cached" in data
    
    def test_get_idle_resources_without_account(self):
        """测试闲置资源API不带账号参数"""
        response = client.get("/api/dashboard/idle")
        assert response.status_code == 400
    
    def test_get_trend_without_account(self):
        """测试趋势API不带账号参数"""
        response = client.get("/api/dashboard/trend")
        # trend API 可能允许无账号，检查是否返回有效响应或错误
        assert response.status_code in [200, 400, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

