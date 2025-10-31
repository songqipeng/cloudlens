#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RedisAnalyzer 单元测试
"""

import pytest
import json
import sqlite3
import os
from unittest.mock import Mock, MagicMock, patch
from resource_modules.redis_analyzer import RedisAnalyzer


class TestRedisAnalyzer:
    """Redis分析器测试类"""

    @pytest.fixture
    def analyzer(self):
        """创建Redis分析器实例"""
        return RedisAnalyzer('test_key_id', 'test_key_secret')

    @pytest.fixture
    def temp_db(self, tmp_path):
        """临时数据库文件"""
        db_file = tmp_path / "test_redis.db"
        return str(db_file)

    def test_init(self, analyzer):
        """测试初始化"""
        assert analyzer.access_key_id == 'test_key_id'
        assert analyzer.access_key_secret == 'test_key_secret'
        assert analyzer.db_name == 'redis_monitoring_data.db'

    def test_init_database(self, analyzer, temp_db, monkeypatch):
        """测试数据库初始化"""
        monkeypatch.setattr(analyzer, 'db_name', temp_db)

        analyzer.init_database()

        # 验证数据库文件已创建
        assert os.path.exists(temp_db)

        # 验证表结构
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # 检查redis_instances表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='redis_instances'")
        assert cursor.fetchone() is not None

        # 检查redis_monitoring_data表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='redis_monitoring_data'")
        assert cursor.fetchone() is not None

        conn.close()

    @patch('resource_modules.redis_analyzer.AcsClient')
    @patch('resource_modules.redis_analyzer.CommonRequest')
    def test_get_all_regions(self, mock_request_class, mock_client_class, analyzer):
        """测试获取所有区域"""
        mock_response = json.dumps({
            'Regions': {
                'Region': [
                    {'RegionId': 'cn-hangzhou'},
                    {'RegionId': 'cn-beijing'}
                ]
            }
        })

        mock_client = MagicMock()
        mock_client.do_action_with_exception.return_value = mock_response
        mock_client_class.return_value = mock_client

        regions = analyzer.get_all_regions()

        assert len(regions) == 2
        assert 'cn-hangzhou' in regions
        assert 'cn-beijing' in regions

    @patch('resource_modules.redis_analyzer.AcsClient')
    @patch('resource_modules.redis_analyzer.CommonRequest')
    def test_get_redis_instances(self, mock_request_class, mock_client_class, analyzer):
        """测试获取Redis实例"""
        mock_response = json.dumps({
            'Instances': {
                'KVStoreInstance': [
                    {
                        'InstanceId': 'r-test-001',
                        'InstanceName': 'Test Redis 1',
                        'InstanceType': 'Redis',
                        'InstanceClass': 'redis.master.small.default',
                        'InstanceStatus': 'Normal',
                        'CreateTime': '2023-01-01T00:00:00Z',
                        'EndTime': '2024-01-01T00:00:00Z',
                        'Capacity': 1024
                    },
                    {
                        'InstanceId': 'r-test-002',
                        'InstanceName': 'Test Redis 2',
                        'InstanceType': 'Redis',
                        'InstanceClass': 'redis.master.mid.default',
                        'InstanceStatus': 'Normal',
                        'CreateTime': '2023-02-01T00:00:00Z',
                        'EndTime': '2024-02-01T00:00:00Z',
                        'Capacity': 2048
                    }
                ]
            }
        })

        mock_client = MagicMock()
        mock_client.do_action_with_exception.return_value = mock_response
        mock_client_class.return_value = mock_client

        mock_request = MagicMock()
        mock_request_class.return_value = mock_request

        instances = analyzer.get_redis_instances('cn-hangzhou')

        assert len(instances) == 2
        assert instances[0]['InstanceId'] == 'r-test-001'
        assert instances[0]['Capacity'] == 1024
        assert instances[1]['InstanceId'] == 'r-test-002'
        assert instances[1]['Capacity'] == 2048

    @patch('resource_modules.redis_analyzer.AcsClient')
    @patch('resource_modules.redis_analyzer.CommonRequest')
    def test_get_redis_instances_empty(self, mock_request_class, mock_client_class, analyzer):
        """测试获取Redis实例（空结果）"""
        mock_response = json.dumps({
            'Instances': {
                'KVStoreInstance': []
            }
        })

        mock_client = MagicMock()
        mock_client.do_action_with_exception.return_value = mock_response
        mock_client_class.return_value = mock_client

        mock_request = MagicMock()
        mock_request_class.return_value = mock_request

        instances = analyzer.get_redis_instances('cn-hangzhou')

        assert len(instances) == 0

    @patch('resource_modules.redis_analyzer.AcsClient')
    @patch('resource_modules.redis_analyzer.CommonRequest')
    def test_get_redis_instances_error(self, mock_request_class, mock_client_class, analyzer):
        """测试获取Redis实例（API错误）"""
        mock_client = MagicMock()
        mock_client.do_action_with_exception.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        mock_request = MagicMock()
        mock_request_class.return_value = mock_request

        instances = analyzer.get_redis_instances('cn-hangzhou')

        # 异常情况应该返回空列表
        assert instances == []

    def test_is_instance_idle_low_cpu(self):
        """测试闲置判断 - 低CPU利用率"""
        analyzer = RedisAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 5.0,  # < 10%
            'MemoryUsage': 50.0,
            'ConnectionUsage': 50.0
        }

        is_idle, reasons = analyzer.is_instance_idle(metrics)

        assert is_idle is True
        assert 'CPU' in str(reasons) or 'cpu' in str(reasons).lower()

    def test_is_instance_idle_low_memory(self):
        """测试闲置判断 - 低内存利用率"""
        analyzer = RedisAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 50.0,
            'MemoryUsage': 15.0,  # < 20%
            'ConnectionUsage': 50.0
        }

        is_idle, reasons = analyzer.is_instance_idle(metrics)

        assert is_idle is True
        assert 'Memory' in str(reasons) or '内存' in str(reasons)

    def test_is_instance_idle_low_connection(self):
        """测试闲置判断 - 低连接数"""
        analyzer = RedisAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 50.0,
            'MemoryUsage': 50.0,
            'ConnectionUsage': 10.0  # < 20%
        }

        is_idle, reasons = analyzer.is_instance_idle(metrics)

        assert is_idle is True
        assert 'Connection' in str(reasons) or '连接' in str(reasons)

    def test_is_instance_idle_low_traffic(self):
        """测试闲置判断 - 低流量"""
        analyzer = RedisAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 50.0,
            'MemoryUsage': 50.0,
            'ConnectionUsage': 50.0,
            'IntranetIn': 50.0,  # < 100 KB/s
            'IntranetOut': 50.0   # < 100 KB/s
        }

        is_idle, reasons = analyzer.is_instance_idle(metrics)

        assert is_idle is True
        # 流量低应该被判定为闲置
        assert 'Intranet' in str(reasons) or '流量' in str(reasons) or 'traffic' in str(reasons).lower()

    def test_is_instance_idle_all_high(self):
        """测试闲置判断 - 所有指标都高（不闲置）"""
        analyzer = RedisAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 50.0,
            'MemoryUsage': 50.0,
            'ConnectionUsage': 50.0,
            'IntranetIn': 500.0,
            'IntranetOut': 500.0,
            'UsedMemory': 500 * 1024 * 1024  # 500MB
        }

        is_idle, reasons = analyzer.is_instance_idle(metrics)

        assert is_idle is False

    def test_is_instance_idle_very_low_memory_usage(self):
        """测试闲置判断 - 极低内存使用量"""
        analyzer = RedisAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 50.0,
            'MemoryUsage': 50.0,
            'ConnectionUsage': 50.0,
            'UsedMemory': 5 * 1024 * 1024  # 5MB < 10MB
        }

        is_idle, reasons = analyzer.is_instance_idle(metrics)

        assert is_idle is True
        assert 'UsedMemory' in str(reasons) or '内存' in str(reasons)

    def test_get_optimization_suggestion_low_usage(self):
        """测试优化建议 - 低使用率"""
        analyzer = RedisAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 5.0,
            'MemoryUsage': 5.0,
            'ConnectionUsage': 5.0
        }

        suggestion = analyzer.get_optimization_suggestion(metrics)

        assert '降配' in suggestion or '降低规格' in suggestion or '优化' in suggestion

    def test_get_optimization_suggestion_normal(self):
        """测试优化建议 - 正常使用"""
        analyzer = RedisAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 50.0,
            'MemoryUsage': 50.0,
            'ConnectionUsage': 50.0
        }

        suggestion = analyzer.get_optimization_suggestion(metrics)

        # 正常使用的实例不应该有激进的降配建议
        assert '保持' in suggestion or '正常' in suggestion or len(suggestion) == 0

    def test_database_table_structure(self, analyzer, temp_db, monkeypatch):
        """测试数据库表结构"""
        monkeypatch.setattr(analyzer, 'db_name', temp_db)

        analyzer.init_database()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # 检查redis_instances表的列
        cursor.execute("PRAGMA table_info(redis_instances)")
        columns = [row[1] for row in cursor.fetchall()]

        assert 'instance_id' in columns
        assert 'instance_name' in columns
        assert 'instance_type' in columns
        assert 'instance_class' in columns
        assert 'region' in columns
        assert 'status' in columns

        # 检查redis_monitoring_data表的列
        cursor.execute("PRAGMA table_info(redis_monitoring_data)")
        columns = [row[1] for row in cursor.fetchall()]

        assert 'id' in columns
        assert 'instance_id' in columns
        assert 'metric_name' in columns
        assert 'metric_value' in columns
        assert 'timestamp' in columns

        conn.close()

    @patch('resource_modules.redis_analyzer.AcsClient')
    @patch('resource_modules.redis_analyzer.CommonRequest')
    def test_get_redis_instances_with_different_types(self, mock_request_class, mock_client_class, analyzer):
        """测试获取不同类型的Redis实例"""
        mock_response = json.dumps({
            'Instances': {
                'KVStoreInstance': [
                    {
                        'InstanceId': 'r-cluster-001',
                        'InstanceType': 'Redis',
                        'ArchitectureType': 'cluster',
                        'InstanceClass': 'redis.cluster.sharding.small.default'
                    },
                    {
                        'InstanceId': 'r-standard-001',
                        'InstanceType': 'Redis',
                        'ArchitectureType': 'standard',
                        'InstanceClass': 'redis.master.small.default'
                    },
                    {
                        'InstanceId': 'r-rwsplit-001',
                        'InstanceType': 'Redis',
                        'ArchitectureType': 'rwsplit',
                        'InstanceClass': 'redis.logic.sharding.2g.8db.0rodb.8proxy.default'
                    }
                ]
            }
        })

        mock_client = MagicMock()
        mock_client.do_action_with_exception.return_value = mock_response
        mock_client_class.return_value = mock_client

        mock_request = MagicMock()
        mock_request_class.return_value = mock_request

        instances = analyzer.get_redis_instances('cn-hangzhou')

        assert len(instances) == 3
        arch_types = [inst.get('ArchitectureType') for inst in instances if 'ArchitectureType' in inst]
        assert 'cluster' in arch_types
        assert 'standard' in arch_types
        assert 'rwsplit' in arch_types
