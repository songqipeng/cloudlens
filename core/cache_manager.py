#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一缓存管理器
使用msgpack替代pickle，消除安全风险
"""

import msgpack
import time
from pathlib import Path
from typing import Any, Optional, List, Callable


class CacheManager:
    """统一缓存管理器"""

    def __init__(self, resource_type: str = None, tenant_name: str = None, 
                 cache_file: str = None, ttl_hours: int = 24, 
                 cache_dir: str = './data/cache'):
        """
        初始化缓存管理器
        
        Args:
            resource_type: 资源类型（如：rds, redis）- 用于统一缓存路径
            tenant_name: 租户名称 - 用于多租户隔离
            cache_file: 缓存文件名（如果提供，则直接使用）
            ttl_hours: 缓存有效期（小时）
            cache_dir: 缓存目录
        """
        if cache_file:
            # 使用指定的文件名
        self.cache_path = Path(cache_dir) / cache_file
        elif resource_type:
            # 统一路径：cache/{tenant}/{resource_type}.pkl
            if tenant_name:
                self.cache_path = Path(cache_dir) / tenant_name / f"{resource_type}.pkl"
            else:
                self.cache_path = Path(cache_dir) / f"{resource_type}.pkl"
        else:
            # 兼容旧方式
            self.cache_path = Path(cache_dir) / (cache_file or "cache.pkl")
        
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
        """保存缓存（使用msgpack，安全高效）"""
        cache_data = {
            'timestamp': time.time(),
            'data': data
        }
        try:
            with open(self.cache_path, 'wb') as f:
                msgpack.pack(cache_data, f)
        except Exception as e:
            raise Exception(f"保存缓存失败: {e}")

    def load(self) -> Optional[Any]:
        """加载缓存（使用msgpack，安全高效）"""
        if not self.is_valid():
            return None

        try:
            with open(self.cache_path, 'rb') as f:
                cache_data = msgpack.unpack(f, raw=False, strict_map_key=False)
            return cache_data.get('data')
        except Exception as e:
            # 缓存文件损坏或格式不兼容，返回None
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
    
    def get_cache_key(self, region: str = None, instance_id: str = None, 
                     metric: str = None) -> str:
        """
        生成统一缓存键
        
        Args:
            region: 区域
            instance_id: 实例ID
            metric: 指标名称
        
        Returns:
            缓存键字符串
        """
        parts = []
        if region:
            parts.append(f"region:{region}")
        if instance_id:
            parts.append(f"instance:{instance_id}")
        if metric:
            parts.append(f"metric:{metric}")
        return ":".join(parts) if parts else "default"
    
    def warm_up_cache(self, regions: List[str] = None, warm_up_func: Callable = None):
        """
        缓存预热：提前加载常用数据
        
        Args:
            regions: 要预热的区域列表
            warm_up_func: 预热函数，接收(region)参数，返回要缓存的数据
        
        Returns:
            预热的数据字典 {region: data}
        """
        if not warm_up_func:
            # 如果没有提供预热函数，跳过
            return {}
        
        warmed_data = {}
        for region in (regions or []):
            try:
                data = warm_up_func(region)
                if data:
                    # 保存到缓存
                    cache_key = self.get_cache_key(region=region)
                    cache_data = {
                        'timestamp': time.time(),
                        'data': data,
                        'region': region,
                        'cache_key': cache_key
                    }
                    warmed_data[region] = data
            except Exception as e:
                # 预热失败不影响主流程
                pass
        
        # 如果预热了数据，可以保存到一个预热缓存
        if warmed_data:
            try:
                warm_cache_path = self.cache_path.parent / f"{self.cache_path.stem}_warm.pkl"
                with open(warm_cache_path, 'wb') as f:
                    msgpack.pack({'warmed_data': warmed_data, 'timestamp': time.time()}, f)
            except:
                pass  # 预热缓存保存失败不影响
        
        return warmed_data

