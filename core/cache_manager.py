#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一缓存管理器
使用msgpack替代pickle，提升安全性和性能
"""

import msgpack
import pickle  # 仅用于向后兼容读取旧缓存
import time
from pathlib import Path
from typing import Any, Optional


class CacheManager:
    """统一缓存管理器"""

    def __init__(self, cache_file: str, ttl_hours: int = 24, cache_dir: str = './data/cache'):
        """
        初始化缓存管理器
        
        Args:
            cache_file: 缓存文件名
            ttl_hours: 缓存有效期（小时）
            cache_dir: 缓存目录
        """
        self.cache_path = Path(cache_dir) / cache_file
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600

    def is_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.cache_path.exists():
            return False

        cache_time = self.cache_path.stat().st_mtime
        current_time = time.time()
        return (current_time - cache_time) < self.ttl_seconds

    def save(self, data: Any):
        """
        保存缓存（使用msgpack格式）

        Args:
            data: 要缓存的数据（必须是msgpack可序列化的类型）
        """
        cache_data = {
            'timestamp': time.time(),
            'data': data,
            'format': 'msgpack'  # 标记格式，便于未来升级
        }
        try:
            with open(self.cache_path, 'wb') as f:
                packed = msgpack.packb(cache_data, use_bin_type=True)
                f.write(packed)
        except Exception as e:
            raise Exception(f"保存缓存失败: {e}")

    def load(self) -> Optional[Any]:
        """
        加载缓存（支持msgpack和pickle格式，向后兼容）

        Returns:
            缓存的数据，如果缓存无效或损坏则返回None
        """
        if not self.is_valid():
            return None

        try:
            with open(self.cache_path, 'rb') as f:
                raw_data = f.read()

            # 尝试msgpack解析
            try:
                cache_data = msgpack.unpackb(raw_data, raw=False, strict_map_key=False)
                return cache_data.get('data')
            except (msgpack.exceptions.ExtraData,
                    msgpack.exceptions.UnpackException,
                    TypeError):
                # 不是msgpack格式，尝试pickle（向后兼容旧缓存）
                try:
                    cache_data = pickle.loads(raw_data)
                    return cache_data.get('data')
                except Exception:
                    # 两种格式都无法解析，缓存损坏
                    return None

        except Exception as e:
            # 读取文件失败
            return None

    def clear(self):
        """清除缓存"""
        if self.cache_path.exists():
            self.cache_path.unlink()

    def get_age_hours(self) -> float:
        """获取缓存年龄（小时）"""
        if not self.cache_path.exists():
            return float('inf')
        
        cache_time = self.cache_path.stat().st_mtime
        current_time = time.time()
        return (current_time - cache_time) / 3600

