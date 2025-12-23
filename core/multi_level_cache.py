# -*- coding: utf-8 -*-
"""
多级缓存管理器
实现内存缓存 + 数据库缓存的两级缓存策略，提升性能
"""

import json
import logging
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, List, Optional

from core.cache import CacheManager

logger = logging.getLogger(__name__)


class LRUCache:
    """简单的LRU缓存实现（内存缓存）"""
    
    def __init__(self, max_size: int = 100):
        """
        初始化LRU缓存
        
        Args:
            max_size: 最大缓存条目数
        """
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            # 移动到末尾（最近使用）
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        if key in self.cache:
            # 更新现有值
            self.cache.move_to_end(key)
        else:
            # 添加新值
            if len(self.cache) >= self.max_size:
                # 删除最旧的项（FIFO）
                self.cache.popitem(last=False)
        self.cache[key] = value
    
    def clear(self, key: Optional[str] = None):
        """清除缓存"""
        if key:
            self.cache.pop(key, None)
        else:
            self.cache.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)


class MultiLevelCache:
    """
    多级缓存管理器
    第一级：内存缓存（LRU，快速访问）
    第二级：数据库缓存（持久化，大容量）
    """
    
    def __init__(self, ttl_seconds: int = 86400, memory_cache_size: int = 100, db_type: Optional[str] = None):
        """
        初始化多级缓存
        
        Args:
            ttl_seconds: 缓存过期时间（秒），默认24小时
            memory_cache_size: 内存缓存最大条目数，默认100
            db_type: 数据库类型（'sqlite' 或 'mysql'），None则从环境变量读取
        """
        self.memory_cache = LRUCache(max_size=memory_cache_size)
        self.db_cache = CacheManager(ttl_seconds=ttl_seconds, db_type=db_type)
        self.ttl_seconds = ttl_seconds
        logger.info(f"多级缓存初始化完成（内存缓存大小: {memory_cache_size}, TTL: {ttl_seconds}秒）")
    
    def _generate_key(self, resource_type: str, account_name: str, region: Optional[str] = None) -> str:
        """生成缓存键"""
        parts = [resource_type, account_name]
        if region:
            parts.append(region)
        return ":".join(parts)
    
    def get(self, resource_type: str, account_name: str, region: Optional[str] = None) -> Optional[List[Any]]:
        """
        获取缓存数据（多级查找）
        
        1. 先查内存缓存（最快）
        2. 如果未命中，查数据库缓存
        3. 如果数据库缓存命中，写入内存缓存
        
        Args:
            resource_type: 资源类型
            account_name: 账号名称
            region: 区域（可选）
            
        Returns:
            缓存的资源列表，如果不存在或已过期则返回 None
        """
        cache_key = self._generate_key(resource_type, account_name, region)
        
        # 1. 先查内存缓存
        cached_data = self.memory_cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"内存缓存命中: {cache_key}")
            return cached_data
        
        # 2. 查数据库缓存
        cached_data = self.db_cache.get(resource_type, account_name, region)
        if cached_data is not None:
            # 3. 写入内存缓存（提升下次访问速度）
            self.memory_cache.set(cache_key, cached_data)
            logger.debug(f"数据库缓存命中: {cache_key}")
            return cached_data
        
        logger.debug(f"缓存未命中: {cache_key}")
        return None
    
    def set(self, resource_type: str, account_name: str, data: List[Any], region: Optional[str] = None):
        """
        设置缓存数据（多级写入）
        
        同时写入内存缓存和数据库缓存
        
        Args:
            resource_type: 资源类型
            account_name: 账号名称
            data: 资源数据列表
            region: 区域（可选）
        """
        cache_key = self._generate_key(resource_type, account_name, region)
        
        # 1. 写入内存缓存
        self.memory_cache.set(cache_key, data)
        
        # 2. 写入数据库缓存
        self.db_cache.set(resource_type, account_name, data, region)
        
        logger.debug(f"缓存已设置: {cache_key}")
    
    def clear(self, resource_type: Optional[str] = None, account_name: Optional[str] = None):
        """
        清除缓存（多级清除）
        
        Args:
            resource_type: 如果指定，只清除该类型的缓存
            account_name: 如果指定，只清除该账号的缓存
        """
        # 清除内存缓存
        if resource_type and account_name:
            # 清除特定资源类型和账号的缓存
            # 由于LRU缓存使用完整key，需要遍历清除
            keys_to_remove = []
            for key in self.memory_cache.cache.keys():
                if key.startswith(f"{resource_type}:{account_name}"):
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                self.memory_cache.clear(key)
        elif resource_type:
            # 清除特定资源类型的缓存
            keys_to_remove = [key for key in self.memory_cache.cache.keys() if key.startswith(f"{resource_type}:")]
            for key in keys_to_remove:
                self.memory_cache.clear(key)
        elif account_name:
            # 清除特定账号的缓存
            keys_to_remove = [key for key in self.memory_cache.cache.keys() if f":{account_name}" in key]
            for key in keys_to_remove:
                self.memory_cache.clear(key)
        else:
            # 清除所有内存缓存
            self.memory_cache.clear()
        
        # 清除数据库缓存
        self.db_cache.clear(resource_type, account_name)
        
        logger.info(f"缓存已清除（resource_type={resource_type}, account_name={account_name}）")
    
    def clear_all(self):
        """清除所有缓存"""
        self.memory_cache.clear()
        self.db_cache.clear_all()
        logger.info("所有缓存已清除")
    
    def cleanup_expired(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的缓存条目数
        """
        # 数据库缓存会自动处理过期，这里只清理内存缓存
        # 内存缓存使用LRU策略，不需要清理过期（会自动淘汰）
        return self.db_cache.cleanup_expired()
    
    def get_stats(self) -> dict:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计字典
        """
        return {
            "memory_cache_size": self.memory_cache.size(),
            "memory_cache_max_size": self.memory_cache.max_size,
            "memory_cache_hit_rate": "N/A",  # 需要添加命中率统计
            "db_cache_ttl": self.ttl_seconds,
        }

