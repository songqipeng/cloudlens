#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DatabaseManager 单元测试
"""

import pytest
import sqlite3
import tempfile
import os
from core.db_manager import DatabaseManager


class TestDatabaseManager:
    """数据库管理器测试类"""

    @pytest.fixture
    def db_manager(self, tmp_path):
        """创建临时数据库管理器"""
        db_file = tmp_path / "test.db"
        return DatabaseManager(str(db_file), db_dir=str(tmp_path))

    def test_init(self, db_manager):
        """测试初始化"""
        assert db_manager.db_path.exists()

    def test_create_resource_table(self, db_manager):
        """测试创建资源表"""
        db_manager.create_resource_table("test_resource")
        
        # 验证表已创建
        conn = sqlite3.connect(str(db_manager.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_resource_instances'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_create_monitoring_table(self, db_manager):
        """测试创建监控表"""
        db_manager.create_resource_table("test_resource")
        db_manager.create_monitoring_table("test_resource")
        
        # 验证表已创建
        conn = sqlite3.connect(str(db_manager.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_resource_monitoring_data'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_save_instance(self, db_manager):
        """测试保存实例"""
        db_manager.create_resource_table("test_resource")
        
        instance = {
            'InstanceId': 'test-001',
            'InstanceName': 'Test Instance',
            'InstanceType': 'ecs.t5-lc1m1.small',
            'Region': 'cn-hangzhou',
            'Status': 'Running'
        }
        
        db_manager.save_instance("test_resource", instance)
        
        # 验证数据已保存
        saved = db_manager.get_instance("test_resource", "test-001")
        assert saved is not None
        assert saved['instance_id'] == 'test-001'

    def test_save_metric(self, db_manager):
        """测试保存监控指标"""
        db_manager.create_resource_table("test_resource")
        db_manager.create_monitoring_table("test_resource")
        db_manager.save_instance("test_resource", {'InstanceId': 'test-001'})
        
        db_manager.save_metric("test_resource", "test-001", "CPU利用率", 50.0)
        
        # 验证指标已保存
        metrics = db_manager.get_metrics("test_resource", "test-001")
        assert "CPU利用率" in metrics
        assert metrics["CPU利用率"] == 50.0

    def test_get_all_instances(self, db_manager):
        """测试获取所有实例"""
        db_manager.create_resource_table("test_resource")
        
        instance1 = {'InstanceId': 'test-001', 'Region': 'cn-hangzhou'}
        instance2 = {'InstanceId': 'test-002', 'Region': 'cn-shanghai'}
        
        db_manager.save_instance("test_resource", instance1)
        db_manager.save_instance("test_resource", instance2)
        
        all_instances = db_manager.get_all_instances("test_resource")
        assert len(all_instances) == 2
        
        # 测试区域过滤
        hangzhou_instances = db_manager.get_all_instances("test_resource", region="cn-hangzhou")
        assert len(hangzhou_instances) == 1
        assert hangzhou_instances[0]['instance_id'] == 'test-001'

