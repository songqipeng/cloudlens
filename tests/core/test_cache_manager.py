#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CacheManager 单元测试
"""

import pytest
import time
import tempfile
from pathlib import Path
from core.cache_manager import CacheManager


class TestCacheManager:
    """缓存管理器测试类"""

    @pytest.fixture
    def cache_manager(self, tmp_path):
        """创建临时缓存管理器"""
        return CacheManager(
            resource_type="test",
            tenant_name="test_tenant",
            cache_dir=str(tmp_path)
        )

    def test_init(self, cache_manager):
        """测试初始化"""
        assert cache_manager.cache_path.parent.exists()

    def test_save_and_load(self, cache_manager):
        """测试保存和加载缓存"""
        test_data = {'key': 'value', 'number': 123}
        
        cache_manager.save(test_data)
        assert cache_manager.cache_path.exists()
        
        loaded_data = cache_manager.load()
        assert loaded_data == test_data

    def test_is_valid(self, cache_manager):
        """测试缓存有效性检查"""
        cache_manager.save({'test': 'data'})
        assert cache_manager.is_valid() is True

    def test_expired_cache(self, cache_manager):
        """测试过期缓存"""
        cache_manager.save({'test': 'data'})
        
        # 修改TTL为0，使缓存立即过期
        cache_manager.ttl_seconds = 0
        
        assert cache_manager.is_valid() is False
        assert cache_manager.load() is None

    def test_clear(self, cache_manager):
        """测试清除缓存"""
        cache_manager.save({'test': 'data'})
        assert cache_manager.cache_path.exists()
        
        cache_manager.clear()
        assert not cache_manager.cache_path.exists()

    def test_get_cache_key(self, cache_manager):
        """测试生成缓存键"""
        key1 = cache_manager.get_cache_key("cn-hangzhou", "i-001", "CPU")
        assert "region:cn-hangzhou" in key1
        assert "instance:i-001" in key1
        assert "metric:CPU" in key1
        
        key2 = cache_manager.get_cache_key(region="cn-hangzhou")
        assert key2 == "region:cn-hangzhou"

