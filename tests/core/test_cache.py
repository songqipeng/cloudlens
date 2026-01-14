"""现代缓存管理器单元测试（CacheManager - SQLite/MySQL）"""
import pytest
import tempfile
import os
from pathlib import Path
from cloudlens.core.cache import CacheManager


class TestCacheManager:
    """CacheManager测试类（SQLite/MySQL缓存）"""

    @pytest.fixture
    def cache_manager(self):
        """创建缓存管理器实例（使用SQLite）"""
        return CacheManager(ttl_seconds=3600, db_type="sqlite")

    def test_save_and_get_data(self, cache_manager):
        """测试: 保存和获取数据"""
        test_data = [
            {"id": "i-001", "name": "test-instance"},
            {"id": "i-002", "name": "test-instance-2"},
        ]

        # 保存
        cache_manager.set(
            resource_type="ecs",
            account_name="test_account",
            data=test_data
        )

        # 获取
        loaded = cache_manager.get(
            resource_type="ecs",
            account_name="test_account"
        )

        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0]["id"] == "i-001"

    def test_cache_with_different_accounts(self, cache_manager):
        """测试: 不同账号的缓存应该分开"""
        data_account1 = [{"id": "i-001", "account": "account1"}]
        data_account2 = [{"id": "i-002", "account": "account2"}]

        # 保存不同账号的数据
        cache_manager.set(
            resource_type="ecs",
            account_name="account1",
            data=data_account1
        )
        cache_manager.set(
            resource_type="ecs",
            account_name="account2",
            data=data_account2
        )

        # 获取数据
        loaded1 = cache_manager.get(resource_type="ecs", account_name="account1")
        loaded2 = cache_manager.get(resource_type="ecs", account_name="account2")

        assert loaded1[0]["id"] == "i-001"
        assert loaded2[0]["id"] == "i-002"

    def test_cache_miss(self, cache_manager):
        """测试: 缓存未命中 - 未保存过数据"""
        result = cache_manager.get(
            resource_type="non_existent",
            account_name="test_account"
        )
        assert result is None

    def test_cache_clear(self, cache_manager):
        """测试: 清除缓存"""
        test_data = [{"id": "i-001"}]
        
        # 保存数据
        cache_manager.set(
            resource_type="ecs",
            account_name="test_account",
            data=test_data
        )

        # 确认数据存在
        assert cache_manager.get(
            resource_type="ecs",
            account_name="test_account"
        ) is not None

        # 清除缓存
        cache_manager.clear(
            resource_type="ecs",
            account_name="test_account"
        )

        # 应该返回None
        assert cache_manager.get(
            resource_type="ecs",
            account_name="test_account"
        ) is None

    def test_cache_clear_all(self, cache_manager):
        """测试: 清除所有缓存"""
        # 保存多个缓存
        cache_manager.set("ecs", "account1", [{"id": "1"}])
        cache_manager.set("rds", "account1", [{"id": "2"}])
        cache_manager.set("ecs", "account2", [{"id": "3"}])

        # 清除所有缓存
        cache_manager.clear_all()

        # 所有缓存应该都被清除
        assert cache_manager.get("ecs", "account1") is None
        assert cache_manager.get("rds", "account1") is None
        assert cache_manager.get("ecs", "account2") is None

    def test_cache_validity(self, cache_manager):
        """测试: 缓存有效性检查"""
        test_data = [{"id": "i-001"}]

        # 未保存时无效
        assert cache_manager.get("ecs", "test_account") is None

        # 保存后有效
        cache_manager.set("ecs", "test_account", test_data)
        result = cache_manager.get("ecs", "test_account")
        assert result is not None
        assert len(result) == 1

    def test_cache_with_different_resource_types(self, cache_manager):
        """测试: 不同资源类型的缓存应该分开"""
        ecs_data = [{"id": "i-001", "type": "ecs"}]
        rds_data = [{"id": "rm-001", "type": "rds"}]

        # 保存不同资源类型的数据
        cache_manager.set("ecs", "test_account", ecs_data)
        cache_manager.set("rds", "test_account", rds_data)

        # 获取数据
        loaded_ecs = cache_manager.get("ecs", "test_account")
        loaded_rds = cache_manager.get("rds", "test_account")

        assert loaded_ecs[0]["type"] == "ecs"
        assert loaded_rds[0]["type"] == "rds"


class TestCacheExpiration:
    """缓存过期测试"""

    def test_cache_ttl(self):
        """测试: 缓存TTL过期"""
        import time
        
        # 创建TTL为1秒的缓存管理器
        cache_manager = CacheManager(ttl_seconds=1, db_type="sqlite")
        
        # 保存数据
        cache_manager.set("ecs", "test_account", [{"id": "i-001"}])
        
        # 立即获取应该有效
        result = cache_manager.get("ecs", "test_account")
        assert result is not None
        
        # 等待2秒后应该过期
        time.sleep(2)
        result = cache_manager.get("ecs", "test_account")
        assert result is None

    def test_cache_ttl_custom(self):
        """测试: 自定义TTL"""
        # 创建TTL为3600秒（1小时）的缓存管理器
        cache_manager = CacheManager(ttl_seconds=3600, db_type="sqlite")
        
        # 保存数据
        cache_manager.set("ecs", "test_account", [{"id": "i-001"}])
        
        # 应该有效
        result = cache_manager.get("ecs", "test_account")
        assert result is not None
        assert len(result) == 1

