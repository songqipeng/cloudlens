#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThresholdManager 单元测试
"""

import pytest
import yaml
from pathlib import Path
from core.threshold_manager import ThresholdManager


class TestThresholdManager:
    """ThresholdManager测试类"""

    @pytest.fixture
    def sample_thresholds(self):
        """示例阈值配置"""
        return {
            'ecs': {
                'with_agent': {
                    'cpu_utilization': 10,
                    'memory_utilization': 30,
                    'custom_field': 'test_value'
                },
                'without_agent': {
                    'cpu_utilization': 8
                }
            },
            'rds': {
                'cpu_utilization': 15,
                'memory_utilization': 25
            },
            'custom_resource': {
                'custom_metric': 100
            }
        }

    @pytest.fixture
    def threshold_file(self, tmp_path, sample_thresholds):
        """创建临时阈值配置文件"""
        threshold_path = tmp_path / "thresholds.yaml"
        with open(threshold_path, 'w', encoding='utf-8') as f:
            yaml.dump(sample_thresholds, f, allow_unicode=True)
        return threshold_path

    def test_init_with_file(self, threshold_file):
        """测试使用配置文件初始化"""
        tm = ThresholdManager(str(threshold_file))

        assert tm.threshold_file == Path(threshold_file)
        assert 'ecs' in tm.thresholds
        assert 'rds' in tm.thresholds

    def test_init_without_file(self):
        """测试不使用配置文件初始化（使用默认阈值）"""
        tm = ThresholdManager()

        assert tm.threshold_file is None
        assert 'ecs' in tm.thresholds
        assert 'rds' in tm.thresholds
        assert 'redis' in tm.thresholds
        assert 'mongodb' in tm.thresholds
        assert 'oss' in tm.thresholds

    def test_init_with_nonexistent_file(self, tmp_path):
        """测试文件不存在时使用默认阈值"""
        nonexistent = tmp_path / "nonexistent.yaml"
        tm = ThresholdManager(str(nonexistent))

        # 应该使用默认阈值
        assert tm.thresholds == tm._get_default_thresholds()

    def test_load_valid_yaml(self, threshold_file):
        """测试加载有效的YAML文件"""
        tm = ThresholdManager(str(threshold_file))

        assert tm.thresholds['ecs']['with_agent']['cpu_utilization'] == 10
        assert tm.thresholds['ecs']['with_agent']['custom_field'] == 'test_value'
        assert tm.thresholds['rds']['cpu_utilization'] == 15

    def test_load_empty_yaml(self, tmp_path):
        """测试加载空YAML文件"""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text('', encoding='utf-8')

        tm = ThresholdManager(str(empty_file))

        # 空文件会被yaml.safe_load解析为None，代码中使用 or {} 处理
        assert tm.thresholds == {}

    def test_load_corrupted_yaml(self, tmp_path):
        """测试加载损坏的YAML文件"""
        corrupted_file = tmp_path / "corrupted.yaml"
        corrupted_file.write_text('invalid: yaml: content: [[[', encoding='utf-8')

        tm = ThresholdManager(str(corrupted_file))

        # 损坏文件应该返回默认阈值
        assert tm.thresholds == tm._get_default_thresholds()

    def test_default_thresholds_structure(self):
        """测试默认阈值结构完整性"""
        tm = ThresholdManager()

        # 检查ECS阈值
        assert 'with_agent' in tm.thresholds['ecs']
        assert 'without_agent' in tm.thresholds['ecs']
        assert tm.thresholds['ecs']['with_agent']['cpu_utilization'] == 5
        assert tm.thresholds['ecs']['with_agent']['memory_utilization'] == 20

        # 检查RDS阈值
        assert tm.thresholds['rds']['cpu_utilization'] == 10
        assert tm.thresholds['rds']['memory_utilization'] == 20
        assert tm.thresholds['rds']['connection_usage'] == 20

        # 检查Redis阈值
        assert tm.thresholds['redis']['cpu_utilization'] == 10
        assert tm.thresholds['redis']['memory_utilization'] == 20

        # 检查MongoDB阈值
        assert tm.thresholds['mongodb']['cpu_utilization'] == 10
        assert tm.thresholds['mongodb']['qps'] == 100

        # 检查OSS阈值
        assert tm.thresholds['oss']['storage_capacity_gb'] == 1
        assert tm.thresholds['oss']['object_count'] == 100

    def test_get_thresholds_simple_resource(self, threshold_file):
        """测试获取简单资源类型阈值"""
        tm = ThresholdManager(str(threshold_file))

        rds_thresholds = tm.get_thresholds('rds')

        assert rds_thresholds['cpu_utilization'] == 15
        assert rds_thresholds['memory_utilization'] == 25

    def test_get_thresholds_with_subtype(self, threshold_file):
        """测试获取带子类型的阈值"""
        tm = ThresholdManager(str(threshold_file))

        ecs_with_agent = tm.get_thresholds('ecs', 'with_agent')
        ecs_without_agent = tm.get_thresholds('ecs', 'without_agent')

        assert ecs_with_agent['cpu_utilization'] == 10
        assert ecs_with_agent['memory_utilization'] == 30
        assert ecs_without_agent['cpu_utilization'] == 8

    def test_get_thresholds_nonexistent_resource(self):
        """测试获取不存在的资源类型"""
        tm = ThresholdManager()

        thresholds = tm.get_thresholds('nonexistent_resource')

        assert thresholds == {}

    def test_get_thresholds_nonexistent_subtype(self, threshold_file):
        """测试获取不存在的子类型（返回资源级别阈值）"""
        tm = ThresholdManager(str(threshold_file))

        # 请求不存在的子类型，应返回整个ecs阈值字典
        thresholds = tm.get_thresholds('ecs', 'nonexistent_subtype')

        assert 'with_agent' in thresholds
        assert 'without_agent' in thresholds

    def test_get_thresholds_default_values(self):
        """测试使用默认阈值获取各种资源类型"""
        tm = ThresholdManager()

        # 测试ECS
        ecs_with_agent = tm.get_thresholds('ecs', 'with_agent')
        assert ecs_with_agent['cpu_utilization'] == 5
        assert ecs_with_agent['load_average_percent'] == 5
        assert ecs_with_agent['disk_utilization'] == 20

        # 测试RDS
        rds = tm.get_thresholds('rds')
        assert rds['cpu_utilization'] == 10
        assert rds['qps'] == 100

        # 测试Redis
        redis = tm.get_thresholds('redis')
        assert redis['connection_usage'] == 20

        # 测试MongoDB
        mongodb = tm.get_thresholds('mongodb')
        assert mongodb['disk_utilization'] == 20
        assert mongodb['connection_utilization'] == 20

        # 测试OSS
        oss = tm.get_thresholds('oss')
        assert oss['get_request_count'] == 50
        assert oss['put_request_count'] == 10

    def test_yaml_with_chinese_content(self, tmp_path):
        """测试包含中文内容的YAML文件"""
        chinese_thresholds = {
            'custom': {
                '描述': '自定义阈值',
                'cpu_utilization': 15,
                '备注': '中文注释'
            }
        }
        threshold_path = tmp_path / "chinese.yaml"
        with open(threshold_path, 'w', encoding='utf-8') as f:
            yaml.dump(chinese_thresholds, f, allow_unicode=True)

        tm = ThresholdManager(str(threshold_path))

        assert tm.thresholds['custom']['描述'] == '自定义阈值'
        assert tm.thresholds['custom']['备注'] == '中文注释'

    def test_partial_override(self, tmp_path):
        """测试部分覆盖默认阈值"""
        # 只定义部分资源的阈值
        partial_thresholds = {
            'rds': {
                'cpu_utilization': 50  # 只覆盖这一项
            }
        }
        threshold_path = tmp_path / "partial.yaml"
        with open(threshold_path, 'w', encoding='utf-8') as f:
            yaml.dump(partial_thresholds, f)

        tm = ThresholdManager(str(threshold_path))

        # RDS应该使用配置文件中的值
        assert tm.thresholds['rds']['cpu_utilization'] == 50
        # 但不应该有其他默认字段（完全覆盖）
        assert 'memory_utilization' not in tm.thresholds['rds']

    def test_nested_structure_preservation(self, threshold_file):
        """测试嵌套结构的保留"""
        tm = ThresholdManager(str(threshold_file))

        # 验证多层嵌套结构被正确保留
        assert isinstance(tm.thresholds['ecs'], dict)
        assert isinstance(tm.thresholds['ecs']['with_agent'], dict)
        assert isinstance(tm.thresholds['ecs']['with_agent']['cpu_utilization'], int)

    def test_threshold_file_path_type(self, threshold_file):
        """测试阈值文件路径类型"""
        # 使用字符串路径
        tm1 = ThresholdManager(str(threshold_file))
        assert tm1.threshold_file == Path(threshold_file)

        # 测试None路径
        tm2 = ThresholdManager(None)
        assert tm2.threshold_file is None

    def test_yaml_with_numeric_types(self, tmp_path):
        """测试YAML中的各种数值类型"""
        numeric_thresholds = {
            'test': {
                'integer': 100,
                'float': 3.14,
                'string_number': '42',
                'boolean': True,
                'null_value': None
            }
        }
        threshold_path = tmp_path / "numeric.yaml"
        with open(threshold_path, 'w', encoding='utf-8') as f:
            yaml.dump(numeric_thresholds, f)

        tm = ThresholdManager(str(threshold_path))

        assert tm.thresholds['test']['integer'] == 100
        assert tm.thresholds['test']['float'] == 3.14
        assert tm.thresholds['test']['string_number'] == '42'
        assert tm.thresholds['test']['boolean'] is True
        assert tm.thresholds['test']['null_value'] is None
