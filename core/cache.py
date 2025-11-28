# -*- coding: utf-8 -*-
"""
Resource Cache Manager
使用 SQLite 实现资源查询缓存，提升重复查询性能
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Any

class CacheManager:
    """资源缓存管理器"""
    
    CACHE_DB = Path.home() / ".cloudlens" / "cache.db"
    DEFAULT_TTL = 300  # 5 minutes
    
    def __init__(self, ttl_seconds: int = DEFAULT_TTL):
        self.cache_db = self.CACHE_DB
        self.cache_db.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resource_cache (
                cache_key TEXT PRIMARY KEY,
                resource_type TEXT,
                account_name TEXT,
                region TEXT,
                data TEXT,
                created_at TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def get(self, resource_type: str, account_name: str, region: str = None) -> Optional[List[Any]]:
        """
        从缓存获取资源数据
        
        Args:
            resource_type: 资源类型 (ecs, rds, etc.)
            account_name: 账号名称
            region: 区域 (可选)
        
        Returns:
            缓存的资源列表，如果不存在或已过期则返回 None
        """
        cache_key = self._generate_key(resource_type, account_name, region)
        
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data, expires_at FROM resource_cache 
            WHERE cache_key = ? AND expires_at > ?
        ''', (cache_key, datetime.now().isoformat()))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    def set(self, resource_type: str, account_name: str, data: List[Any], region: str = None):
        """
        缓存资源数据
        
        Args:
            resource_type: 资源类型
            account_name: 账号名称
            data: 资源数据列表
            region: 区域 (可选)
        """
        cache_key = self._generate_key(resource_type, account_name, region)
        created_at = datetime.now()
        expires_at = created_at + timedelta(seconds=self.ttl_seconds)
        
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO resource_cache 
            (cache_key, resource_type, account_name, region, data, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            cache_key,
            resource_type,
            account_name,
            region,
            json.dumps(data, ensure_ascii=False),
            created_at.isoformat(),
            expires_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def clear(self, resource_type: str = None, account_name: str = None):
        """
        清除缓存
        
        Args:
            resource_type: 如果指定，只清除该类型的缓存
            account_name: 如果指定，只清除该账号的缓存
        """
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        if resource_type and account_name:
            cursor.execute('''
                DELETE FROM resource_cache 
                WHERE resource_type = ? AND account_name = ?
            ''', (resource_type, account_name))
        elif resource_type:
            cursor.execute('''
                DELETE FROM resource_cache WHERE resource_type = ?
            ''', (resource_type,))
        elif account_name:
            cursor.execute('''
                DELETE FROM resource_cache WHERE account_name = ?
            ''', (account_name,))
        else:
            # 清除所有缓存
            cursor.execute('DELETE FROM resource_cache')
        
        conn.commit()
        conn.close()
    
    def cleanup_expired(self):
        """清理过期缓存"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM resource_cache WHERE expires_at < ?
        ''', (datetime.now().isoformat(),))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def _generate_key(self, resource_type: str, account_name: str, region: str = None) -> str:
        """生成缓存键"""
        parts = [resource_type, account_name]
        if region:
            parts.append(region)
        key_str = ":".join(parts)
        return hashlib.md5(key_str.encode()).hexdigest()
