#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDSAnalyzer 单元测试
"""

import pytest
import json
import sqlite3
import os
from unittest.mock import Mock, MagicMock, patch
from resource_modules.rds_analyzer import RDSAnalyzer


class TestRDSAnalyzer:
    """RDS分析器测试类"""

    @pytest.fixture
    def analyzer(self):
        """创建RDS分析器实例"""
        return RDSAnalyzer('test_key_id', 'test_key_secret')

    @pytest.fixture
    def temp_db(self, tmp_path):
        """临时数据库文件"""
        db_file = tmp_path / "test_rds.db"
        return str(db_file)

    def test_init(self, analyzer):
        """测试初始化"""
        assert analyzer.access_key_id == 'test_key_id'
        assert analyzer.access_key_secret == 'test_key_secret'
        assert analyzer.db_name == 'rds_monitoring_data.db'

    def test_init_database(self, analyzer, temp_db, monkeypatch):
        """测试数据库初始化"""
        monkeypatch.setattr(analyzer, 'db_name', temp_db)

        analyzer.init_database()

        # 验证数据库文件已创建
        assert os.path.exists(temp_db)

        # 验证表结构
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # 检查rds_instances表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rds_instances'")
        assert cursor.fetchone() is not None

        # 检查rds_monitoring_data表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rds_monitoring_data'")
        assert cursor.fetchone() is not None

        conn.close()

    @patch('resource_modules.rds_analyzer.AcsClient')
    @patch('resource_modules.rds_analyzer.CommonRequest')
    def test_get_all_regions(self, mock_request_class, mock_client_class, analyzer):
        """测试获取所有区域"""
        # Mock API响应
        mock_response = json.dumps({
            'Regions': {
                'Region': [
                    {'RegionId': 'cn-hangzhou'},
                    {'RegionId': 'cn-beijing'},
                    {'RegionId': 'cn-shanghai'}
                ]
            }
        })

        mock_client = MagicMock()
        mock_client.do_action_with_exception.return_value = mock_response
        mock_client_class.return_value = mock_client

        regions = analyzer.get_all_regions()

        assert len(regions) == 3
        assert 'cn-hangzhou' in regions
        assert 'cn-beijing' in regions
        assert 'cn-shanghai' in regions

        # 验证API调用参数
        mock_client_class.assert_called_once_with('test_key_id', 'test_key_secret', 'cn-hangzhou')

    @patch('resource_modules.rds_analyzer.AcsClient')
    @patch('resource_modules.rds_analyzer.DescribeDBInstancesRequest.DescribeDBInstancesRequest')
    def test_get_rds_instances(self, mock_request_class, mock_client_class, analyzer):
        """测试获取RDS实例"""
        # Mock API响应
        mock_response = json.dumps({
            'Items': {
                'DBInstance': [
                    {
                        'DBInstanceId': 'rds-test-001',
                        'DBInstanceDescription': 'Test RDS Instance',
                        'DBInstanceType': 'Primary',
                        'Engine': 'MySQL',
                        'EngineVersion': '8.0',
                        'DBInstanceClass': 'mysql.n2.small.1',
                        'DBInstanceStatus': 'Running',
                        'CreateTime': '2023-01-01T00:00:00Z',
                        'ExpireTime': '2024-01-01T00:00:00Z'
                    },
                    {
                        'DBInstanceId': 'rds-test-002',
                        'DBInstanceDescription': 'Test RDS Instance 2',
                        'DBInstanceType': 'Primary',
                        'Engine': 'PostgreSQL',
                        'EngineVersion': '13.0',
                        'DBInstanceClass': 'pg.n2.small.1',
                        'DBInstanceStatus': 'Running',
                        'CreateTime': '2023-02-01T00:00:00Z',
                        'ExpireTime': '2024-02-01T00:00:00Z'
                    }
                ]
            }
        })

        mock_client = MagicMock()
        mock_client.do_action_with_exception.return_value = mock_response
        mock_client_class.return_value = mock_client

        instances = analyzer.get_rds_instances('cn-hangzhou')

        assert len(instances) == 2
        assert instances[0]['InstanceId'] == 'rds-test-001'
        assert instances[0]['DBInstanceDescription'] == 'Test RDS Instance'
        assert instances[1]['InstanceId'] == 'rds-test-002'

    @patch('resource_modules.rds_analyzer.AcsClient')
    @patch('resource_modules.rds_analyzer.DescribeDBInstancesRequest.DescribeDBInstancesRequest')
    def test_get_rds_instances_empty(self, mock_request_class, mock_client_class, analyzer):
        """测试获取RDS实例（空结果）"""
        # Mock空响应
        mock_response = json.dumps({
            'Items': {
                'DBInstance': []
            }
        })

        mock_client = MagicMock()
        mock_client.do_action_with_exception.return_value = mock_response
        mock_client_class.return_value = mock_client

        instances = analyzer.get_rds_instances('cn-hangzhou')

        assert len(instances) == 0

    @patch('resource_modules.rds_analyzer.AcsClient')
    @patch('resource_modules.rds_analyzer.DescribeDBInstancesRequest.DescribeDBInstancesRequest')
    def test_get_rds_instances_error(self, mock_request_class, mock_client_class, analyzer):
        """测试获取RDS实例（API错误）"""
        mock_client = MagicMock()
        mock_client.do_action_with_exception.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        instances = analyzer.get_rds_instances('cn-hangzhou')

        # 异常情况应该返回空列表
        assert instances == []

    def test_is_instance_idle_low_cpu(self):
        """测试闲置判断 - 低CPU利用率"""
        analyzer = RDSAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 5.0,  # < 10%
            'MemoryUsage': 50.0,
            'ConnectionUsage': 50.0,
            'QPS': 500
        }

        # 只要有一个指标满足闲置条件，就应该判定为闲置
        # 这里CPU < 10%满足条件
        is_idle, reasons = analyzer.is_instance_idle(metrics)

        assert is_idle is True
        assert 'CPU利用率过低' in str(reasons) or 'CpuUsage' in str(reasons)

    def test_is_instance_idle_low_memory(self):
        """测试闲置判断 - 低内存利用率"""
        analyzer = RDSAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 50.0,
            'MemoryUsage': 15.0,  # < 20%
            'ConnectionUsage': 50.0,
            'QPS': 500
        }

        is_idle, reasons = analyzer.is_instance_idle(metrics)

        assert is_idle is True
        assert 'MemoryUsage' in str(reasons) or '内存' in str(reasons)

    def test_is_instance_idle_low_qps(self):
        """测试闲置判断 - 低QPS"""
        analyzer = RDSAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 50.0,
            'MemoryUsage': 50.0,
            'ConnectionUsage': 50.0,
            'QPS': 50  # < 100
        }

        is_idle, reasons = analyzer.is_instance_idle(metrics)

        assert is_idle is True
        assert 'QPS' in str(reasons) or 'qps' in str(reasons).lower()

    def test_is_instance_idle_all_high(self):
        """测试闲置判断 - 所有指标都高（不闲置）"""
        analyzer = RDSAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 50.0,
            'MemoryUsage': 50.0,
            'ConnectionUsage': 50.0,
            'QPS': 500,
            'TPS': 50,
            'ConnectionCount': 50
        }

        is_idle, reasons = analyzer.is_instance_idle(metrics)

        assert is_idle is False

    def test_is_instance_idle_missing_metrics(self):
        """测试闲置判断 - 缺少指标数据"""
        analyzer = RDSAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 50.0
            # 缺少其他指标
        }

        # 应该能处理缺失的指标
        is_idle, reasons = analyzer.is_instance_idle(metrics)

        # 返回结果应该是布尔值
        assert isinstance(is_idle, bool)

    def test_get_optimization_suggestion_low_cpu(self):
        """测试优化建议 - 低CPU"""
        analyzer = RDSAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 5.0,
            'MemoryUsage': 5.0,
            'QPS': 10
        }

        suggestion = analyzer.get_optimization_suggestion(metrics)

        assert '降配' in suggestion or '降低规格' in suggestion or '优化' in suggestion

    def test_get_optimization_suggestion_normal(self):
        """测试优化建议 - 正常使用"""
        analyzer = RDSAnalyzer('test_key', 'test_secret')

        metrics = {
            'CpuUsage': 50.0,
            'MemoryUsage': 50.0,
            'QPS': 500
        }

        suggestion = analyzer.get_optimization_suggestion(metrics)

        # 正常使用的实例不应该有降配建议
        assert '保持当前配置' in suggestion or '正常' in suggestion or len(suggestion) == 0

    @patch('resource_modules.rds_analyzer.AcsClient')
    def test_get_rds_instances_with_different_engines(self, mock_client_class, analyzer):
        """测试获取不同引擎的RDS实例"""
        mock_response = json.dumps({
            'Items': {
                'DBInstance': [
                    {
                        'DBInstanceId': 'rds-mysql-001',
                        'Engine': 'MySQL',
                        'EngineVersion': '8.0',
                        'DBInstanceClass': 'mysql.n2.small.1'
                    },
                    {
                        'DBInstanceId': 'rds-pg-001',
                        'Engine': 'PostgreSQL',
                        'EngineVersion': '13.0',
                        'DBInstanceClass': 'pg.n2.small.1'
                    },
                    {
                        'DBInstanceId': 'rds-sqlserver-001',
                        'Engine': 'SQLServer',
                        'EngineVersion': '2019',
                        'DBInstanceClass': 'mssql.n2.small.1'
                    }
                ]
            }
        })

        with patch('resource_modules.rds_analyzer.DescribeDBInstancesRequest.DescribeDBInstancesRequest') as mock_request:
            mock_client = MagicMock()
            mock_client.do_action_with_exception.return_value = mock_response
            mock_client_class.return_value = mock_client

            instances = analyzer.get_rds_instances('cn-hangzhou')

            assert len(instances) == 3
            engines = [inst.get('Engine') for inst in instances if 'Engine' in inst]
            assert 'MySQL' in engines
            assert 'PostgreSQL' in engines
            assert 'SQLServer' in engines

    def test_database_table_structure(self, analyzer, temp_db, monkeypatch):
        """测试数据库表结构"""
        monkeypatch.setattr(analyzer, 'db_name', temp_db)

        analyzer.init_database()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # 检查rds_instances表的列
        cursor.execute("PRAGMA table_info(rds_instances)")
        columns = [row[1] for row in cursor.fetchall()]

        assert 'instance_id' in columns
        assert 'instance_name' in columns
        assert 'instance_type' in columns
        assert 'engine' in columns
        assert 'engine_version' in columns
        assert 'region' in columns
        assert 'status' in columns

        # 检查rds_monitoring_data表的列
        cursor.execute("PRAGMA table_info(rds_monitoring_data)")
        columns = [row[1] for row in cursor.fetchall()]

        assert 'id' in columns
        assert 'instance_id' in columns
        assert 'metric_name' in columns
        assert 'metric_value' in columns
        assert 'timestamp' in columns

        conn.close()
