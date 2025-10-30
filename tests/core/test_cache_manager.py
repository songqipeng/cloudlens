#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CacheManager 单元测试
"""

import pytest
import time
import pickle
from pathlib import Path
from core.cache_manager import CacheManager


class TestCacheManager:
    """CacheManager测试类"""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """临时缓存目录fixture"""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        return str(cache_dir)

    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """CacheManager实例fixture"""
        return CacheManager('test.cache', ttl_hours=1, cache_dir=temp_cache_dir)

    def test_init(self, temp_cache_dir):
        """测试初始化"""
        cache = CacheManager('test.cache', ttl_hours=2, cache_dir=temp_cache_dir)

        assert cache.cache_path.name == 'test.cache'
        assert cache.ttl_seconds == 2 * 3600
        assert cache.cache_path.parent.exists()

    def test_save_and_load_simple_data(self, cache_manager):
        """测试保存和加载简单数据"""
        test_data = {'key': 'value', 'number': 42}

        cache_manager.save(test_data)
        loaded = cache_manager.load()

        assert loaded == test_data

    def test_save_and_load_complex_data(self, cache_manager):
        """测试保存和加载复杂数据"""
        test_data = {
            'string': 'hello',
            'int': 123,
            'float': 3.14,
            'list': [1, 2, 3],
            'dict': {'nested': 'value'},
            'bool': True,
            'none': None
        }

        cache_manager.save(test_data)
        loaded = cache_manager.load()

        assert loaded == test_data
        # 注意：msgpack会将tuple转换为list，这是正常行为

    def test_is_valid_fresh_cache(self, cache_manager):
        """测试is_valid - 新鲜缓存"""
        cache_manager.save({'test': 'data'})

        assert cache_manager.is_valid() is True

    def test_is_valid_expired_cache(self, temp_cache_dir):
        """测试is_valid - 过期缓存"""
        cache = CacheManager('test.cache', ttl_hours=0.001, cache_dir=temp_cache_dir)
        cache.save({'test': 'data'})

        time.sleep(4)  # 等待缓存过期（0.001小时 = 3.6秒）

        assert cache.is_valid() is False

    def test_is_valid_nonexistent_cache(self, cache_manager):
        """测试is_valid - 不存在的缓存"""
        assert cache_manager.is_valid() is False

    def test_load_expired_cache_returns_none(self, temp_cache_dir):
        """测试加载过期缓存返回None"""
        cache = CacheManager('test.cache', ttl_hours=0.001, cache_dir=temp_cache_dir)
        cache.save({'test': 'data'})

        time.sleep(4)

        assert cache.load() is None

    def test_load_nonexistent_cache_returns_none(self, cache_manager):
        """测试加载不存在的缓存返回None"""
        assert cache_manager.load() is None

    def test_backward_compatibility_pickle(self, temp_cache_dir):
        """测试向后兼容 - 读取pickle格式缓存"""
        cache_file = Path(temp_cache_dir) / 'old.cache'

        # 创建pickle格式的旧缓存
        old_data = {'timestamp': time.time(), 'data': {'old': 'format', 'value': 99}}
        with open(cache_file, 'wb') as f:
            pickle.dump(old_data, f)

        # 用CacheManager读取
        cache = CacheManager('old.cache', ttl_hours=1, cache_dir=temp_cache_dir)
        loaded = cache.load()

        assert loaded == old_data['data']

    def test_clear_cache(self, cache_manager):
        """测试清除缓存"""
        cache_manager.save({'test': 'data'})
        assert cache_manager.cache_path.exists()

        cache_manager.clear()
        assert not cache_manager.cache_path.exists()

    def test_clear_nonexistent_cache(self, cache_manager):
        """测试清除不存在的缓存（不应抛异常）"""
        cache_manager.clear()  # 不应抛异常
        assert not cache_manager.cache_path.exists()

    def test_get_age_hours_fresh(self, cache_manager):
        """测试get_age_hours - 新鲜缓存"""
        cache_manager.save({'test': 'data'})

        age = cache_manager.get_age_hours()
        assert 0 <= age < 0.01  # 应该非常小

    def test_get_age_hours_nonexistent(self, cache_manager):
        """测试get_age_hours - 不存在的缓存"""
        age = cache_manager.get_age_hours()
        assert age == float('inf')

    def test_corrupted_cache_returns_none(self, temp_cache_dir):
        """测试损坏的缓存文件返回None"""
        cache_file = Path(temp_cache_dir) / 'corrupted.cache'

        # 写入无效数据
        with open(cache_file, 'wb') as f:
            f.write(b'this is not valid msgpack or pickle data!!!')

        cache = CacheManager('corrupted.cache', ttl_hours=1, cache_dir=temp_cache_dir)
        loaded = cache.load()

        assert loaded is None

    def test_empty_cache_file_returns_none(self, temp_cache_dir):
        """测试空缓存文件返回None"""
        cache_file = Path(temp_cache_dir) / 'empty.cache'
        cache_file.touch()  # 创建空文件

        cache = CacheManager('empty.cache', ttl_hours=1, cache_dir=temp_cache_dir)
        loaded = cache.load()

        assert loaded is None

    def test_save_overwrites_existing(self, cache_manager):
        """测试保存会覆盖现有缓存"""
        cache_manager.save({'first': 'data'})
        cache_manager.save({'second': 'data'})

        loaded = cache_manager.load()
        assert loaded == {'second': 'data'}

    def test_multiple_caches_independent(self, temp_cache_dir):
        """测试多个缓存相互独立"""
        cache1 = CacheManager('cache1.cache', ttl_hours=1, cache_dir=temp_cache_dir)
        cache2 = CacheManager('cache2.cache', ttl_hours=1, cache_dir=temp_cache_dir)

        cache1.save({'cache': 1})
        cache2.save({'cache': 2})

        assert cache1.load() == {'cache': 1}
        assert cache2.load() == {'cache': 2}

    def test_unicode_data(self, cache_manager):
        """测试Unicode数据"""
        test_data = {
            'chinese': '中文测试',
            'emoji': '😀🎉✅',
            'special': 'Ñoño'
        }

        cache_manager.save(test_data)
        loaded = cache_manager.load()

        assert loaded == test_data

    def test_large_data(self, cache_manager):
        """测试大数据"""
        test_data = {'large_list': list(range(10000))}

        cache_manager.save(test_data)
        loaded = cache_manager.load()

        assert loaded == test_data
