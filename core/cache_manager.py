#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一缓存管理器
"""

import pickle
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
        """保存缓存"""
        cache_data = {
            'timestamp': time.time(),
            'data': data
        }
        try:
            with open(self.cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            raise Exception(f"保存缓存失败: {e}")

    def load(self) -> Optional[Any]:
        """加载缓存"""
        if not self.is_valid():
            return None

        try:
            with open(self.cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            return cache_data.get('data')
        except Exception as e:
            # 缓存文件损坏，返回None
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

