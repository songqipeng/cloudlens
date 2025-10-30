#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ConfigManager 单元测试
"""

import pytest
import json
import os
from pathlib import Path
from core.config_manager import ConfigManager


class TestConfigManager:
    """ConfigManager测试类"""

    @pytest.fixture
    def sample_config(self):
        """示例配置数据"""
        return {
            'default_tenant': 'tenant1',
            'tenants': {
                'tenant1': {
                    'access_key_id': 'ak1',
                    'access_key_secret': 'sk1',
                    'display_name': 'Tenant 1'
                },
                'tenant2': {
                    'access_key_id': 'ak2',
                    'access_key_secret': 'sk2',
                    'display_name': 'Tenant 2'
                }
            },
            'some_setting': 'value'
        }

    @pytest.fixture
    def config_file(self, tmp_path, sample_config):
        """创建临时配置文件"""
        config_path = tmp_path / "test_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(sample_config, f)
        return config_path

    def test_init_success(self, config_file):
        """测试成功初始化"""
        cm = ConfigManager(str(config_file))

        assert cm.config_file == Path(config_file)
        assert 'tenants' in cm.config
        assert cm.config['default_tenant'] == 'tenant1'

    def test_init_file_not_found(self, tmp_path):
        """测试配置文件不存在"""
        nonexistent = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError) as exc_info:
            ConfigManager(str(nonexistent))

        assert '配置文件不存在' in str(exc_info.value)

    def test_get_tenant_config_default(self, config_file):
        """测试获取默认租户配置"""
        cm = ConfigManager(str(config_file))

        tenant_config = cm.get_tenant_config()

        assert tenant_config['access_key_id'] == 'ak1'
        assert tenant_config['display_name'] == 'Tenant 1'

    def test_get_tenant_config_specific(self, config_file):
        """测试获取指定租户配置"""
        cm = ConfigManager(str(config_file))

        tenant_config = cm.get_tenant_config('tenant2')

        assert tenant_config['access_key_id'] == 'ak2'
        assert tenant_config['display_name'] == 'Tenant 2'

    def test_get_tenant_config_not_found(self, config_file):
        """测试租户不存在"""
        cm = ConfigManager(str(config_file))

        with pytest.raises(ValueError) as exc_info:
            cm.get_tenant_config('nonexistent')

        assert '未找到租户配置: nonexistent' in str(exc_info.value)
        assert 'tenant1' in str(exc_info.value)  # 应该列出可用租户

    def test_get_tenant_config_no_default(self, tmp_path):
        """测试没有默认租户时"""
        config_data = {
            'tenants': {
                'tenant1': {'key': 'value'}
            }
        }
        config_path = tmp_path / "no_default.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        cm = ConfigManager(str(config_path))

        with pytest.raises(ValueError) as exc_info:
            cm.get_tenant_config()

        assert '未指定租户名称' in str(exc_info.value)

    def test_env_var_replacement(self, tmp_path):
        """测试环境变量替换"""
        # 设置测试环境变量
        os.environ['TEST_ACCESS_KEY'] = 'test_ak_from_env'
        os.environ['TEST_SECRET_KEY'] = 'test_sk_from_env'

        try:
            config_data = {
                'default_tenant': 'test',
                'tenants': {
                    'test': {
                        'access_key_id': '${TEST_ACCESS_KEY}',
                        'access_key_secret': '${TEST_SECRET_KEY}',
                        'normal_field': 'normal_value'
                    }
                }
            }
            config_path = tmp_path / "env_config.json"
            with open(config_path, 'w') as f:
                json.dump(config_data, f)

            cm = ConfigManager(str(config_path))
            tenant_config = cm.get_tenant_config('test')

            assert tenant_config['access_key_id'] == 'test_ak_from_env'
            assert tenant_config['access_key_secret'] == 'test_sk_from_env'
            assert tenant_config['normal_field'] == 'normal_value'
        finally:
            # 清理环境变量
            del os.environ['TEST_ACCESS_KEY']
            del os.environ['TEST_SECRET_KEY']

    def test_env_var_not_set(self, tmp_path):
        """测试环境变量未设置时保留原值"""
        config_data = {
            'default_tenant': 'test',
            'tenants': {
                'test': {
                    'key_with_env': '${NONEXISTENT_VAR}'
                }
            }
        }
        config_path = tmp_path / "unset_env.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        cm = ConfigManager(str(config_path))
        tenant_config = cm.get_tenant_config('test')

        # 环境变量未设置，应该保留原值
        assert tenant_config['key_with_env'] == '${NONEXISTENT_VAR}'

    def test_env_var_in_nested_structure(self, tmp_path):
        """测试嵌套结构中的环境变量替换"""
        os.environ['NESTED_VALUE'] = 'replaced_value'

        try:
            config_data = {
                'default_tenant': 'test',
                'nested': {
                    'level1': {
                        'level2': '${NESTED_VALUE}'
                    }
                },
                'tenants': {
                    'test': {
                        'key': 'value'
                    }
                }
            }
            config_path = tmp_path / "nested_env.json"
            with open(config_path, 'w') as f:
                json.dump(config_data, f)

            cm = ConfigManager(str(config_path))

            assert cm.config['nested']['level1']['level2'] == 'replaced_value'
        finally:
            del os.environ['NESTED_VALUE']

    def test_env_var_in_list(self, tmp_path):
        """测试列表中的环境变量替换"""
        os.environ['LIST_ITEM'] = 'list_value'

        try:
            config_data = {
                'default_tenant': 'test',
                'list_field': ['item1', '${LIST_ITEM}', 'item3'],
                'tenants': {
                    'test': {
                        'key': 'value'
                    }
                }
            }
            config_path = tmp_path / "list_env.json"
            with open(config_path, 'w') as f:
                json.dump(config_data, f)

            cm = ConfigManager(str(config_path))

            assert cm.config['list_field'] == ['item1', 'list_value', 'item3']
        finally:
            del os.environ['LIST_ITEM']

    def test_get_method(self, config_file):
        """测试get方法"""
        cm = ConfigManager(str(config_file))

        assert cm.get('default_tenant') == 'tenant1'
        assert cm.get('some_setting') == 'value'
        assert cm.get('nonexistent', 'default') == 'default'
        assert cm.get('nonexistent') is None

    def test_validate_success(self, config_file):
        """测试配置验证 - 成功"""
        cm = ConfigManager(str(config_file))

        cm.validate()  # 不应抛异常

    def test_validate_missing_field(self, tmp_path):
        """测试配置验证 - 缺少必需字段"""
        config_data = {
            'default_tenant': 'test'
            # 缺少tenants字段
        }
        config_path = tmp_path / "invalid_config.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        cm = ConfigManager(str(config_path))

        with pytest.raises(ValueError) as exc_info:
            cm.validate()

        assert '配置缺少必需字段: tenants' in str(exc_info.value)

    def test_chinese_config(self, tmp_path):
        """测试中文配置"""
        config_data = {
            'default_tenant': '租户1',
            'tenants': {
                '租户1': {
                    '显示名称': '中文租户',
                    '描述': '这是一个中文配置'
                }
            }
        }
        config_path = tmp_path / "chinese_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False)

        cm = ConfigManager(str(config_path))
        tenant_config = cm.get_tenant_config('租户1')

        assert tenant_config['显示名称'] == '中文租户'
        assert tenant_config['描述'] == '这是一个中文配置'

    def test_empty_tenants(self, tmp_path):
        """测试空租户列表"""
        config_data = {
            'default_tenant': 'test',
            'tenants': {}
        }
        config_path = tmp_path / "empty_tenants.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        cm = ConfigManager(str(config_path))

        with pytest.raises(ValueError):
            cm.get_tenant_config('test')
