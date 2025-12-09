"""缓存管理器单元测试"""
import pytest
import tempfile
import os
import shutil
from pathlib import Path
from core.cache_manager import CacheManager


class TestCacheManager:
    """CacheManager测试类"""

    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """创建缓存管理器实例"""
        return CacheManager(cache_dir=temp_cache_dir)

    def test_save_and_load_data(self, cache_manager):
        """测试: 保存和加载数据"""
        test_data = [
            {"id": "i-001", "name": "test-instance"},
            {"id": "i-002", "name": "test-instance-2"},
        ]

        # 保存
        cache_manager.save(test_data)

        # 加载
        loaded = cache_manager.load()

        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0]["id"] == "i-001"

    def test_cache_with_different_regions(self, temp_cache_dir):
        """测试: 不同区域的缓存应该分开"""
        # 创建两个不同的缓存管理器,分别用于不同区域
        cache_hz = CacheManager(
            resource_type="ecs", tenant_name="test_account", cache_dir=temp_cache_dir
        )
        cache_bj = CacheManager(
            resource_type="ecs",
            tenant_name="test_account",
            cache_file="ecs_beijing.pkl",
            cache_dir=temp_cache_dir,
        )

        data_hz = [{"id": "i-hz-001"}]
        data_bj = [{"id": "i-bj-001"}]

        cache_hz.save(data_hz)
        cache_bj.save(data_bj)

        loaded_hz = cache_hz.load()
        loaded_bj = cache_bj.load()

        assert loaded_hz[0]["id"] == "i-hz-001"
        assert loaded_bj[0]["id"] == "i-bj-001"

    def test_cache_miss(self, cache_manager):
        """测试: 缓存未命中 - 未保存过数据"""
        result = cache_manager.load()
        assert result is None

    def test_cache_clear(self, cache_manager):
        """测试: 清除缓存"""
        test_data = [{"id": "i-001"}]
        cache_manager.save(test_data)

        # 确认数据存在
        assert cache_manager.load() is not None

        # 清除缓存
        cache_manager.clear()

        # 应该返回None
        assert cache_manager.load() is None

    def test_cache_validity(self, cache_manager):
        """测试: 缓存有效性检查"""
        test_data = [{"id": "i-001"}]

        # 未保存时无效
        assert cache_manager.is_valid() is False

        # 保存后有效
        cache_manager.save(test_data)
        assert cache_manager.is_valid() is True

    def test_cache_age(self, cache_manager):
        """测试: 缓存年龄"""
        import time

        # 未保存时age应该是无穷大
        age = cache_manager.get_age_hours()
        assert age == float("inf")

        # 保存后age应该接近0
        cache_manager.save([{"id": "i-001"}])
        age = cache_manager.get_age_hours()
        assert age < 0.01  # 小于0.01小时(36秒)


class TestCacheExpiration:
    """缓存过期测试"""

    def test_cache_ttl_default(self):
        """测试: 默认TTL"""
        # 这个测试需要CacheManager支持TTL
        # 如果未实现,可以跳过
        pytest.skip("TTL feature not implemented yet")

    def test_cache_ttl_custom(self):
        """测试: 自定义TTL"""
        pytest.skip("TTL feature not implemented yet")
