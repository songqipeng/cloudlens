# -*- coding: utf-8 -*-
"""
Resource Cache Manager
支持SQLite和MySQL的资源查询缓存，提升重复查询性能
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Optional

from core.database import DatabaseFactory, DatabaseAdapter


class CacheManager:
    """资源缓存管理器（支持SQLite和MySQL）"""

    DEFAULT_TTL = 86400  # 24 hours

    def __init__(self, ttl_seconds: int = DEFAULT_TTL, db_type: Optional[str] = None):
        """
        初始化缓存管理器
        
        Args:
            ttl_seconds: 缓存过期时间（秒），默认24小时
            db_type: 数据库类型（'sqlite' 或 'mysql'），None则从环境变量读取
        """
        self.ttl_seconds = ttl_seconds
        self.db_type = db_type or os.getenv("DB_TYPE", "mysql").lower()
        
        # 创建数据库适配器
        if self.db_type == "mysql":
            self.db = DatabaseFactory.create_adapter("mysql")
            self._table_name = "resource_cache"
        else:
            # SQLite使用默认路径
            db_path = os.getenv("SQLITE_CACHE_DB_PATH")
            if not db_path:
                db_dir = Path.home() / ".cloudlens"
                db_path = str(db_dir / "cache.db")
            self.db = DatabaseFactory.create_adapter("sqlite", db_path=db_path)
            self._table_name = "resource_cache"
        
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        if self.db_type == "mysql":
            # MySQL表结构已在init_mysql_schema.sql中创建
            # 这里只检查表是否存在
            try:
                self.db.query("SELECT 1 FROM resource_cache LIMIT 1")
            except Exception:
                # 表不存在，创建表
                self.db.execute("""
                    CREATE TABLE IF NOT EXISTS resource_cache (
                        cache_key VARCHAR(255) PRIMARY KEY,
                        resource_type VARCHAR(50) NOT NULL,
                        account_name VARCHAR(100) NOT NULL,
                        region VARCHAR(50),
                        data JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        INDEX idx_resource_type_account (resource_type, account_name),
                        INDEX idx_expires_at (expires_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
        else:
            # SQLite表结构
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS resource_cache (
                    cache_key TEXT PRIMARY KEY,
                    resource_type TEXT,
                    account_name TEXT,
                    region TEXT,
                    data TEXT,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            # 创建索引（SQLite支持IF NOT EXISTS）
            try:
                self.db.execute("CREATE INDEX IF NOT EXISTS idx_resource_type_account ON resource_cache(resource_type, account_name)")
                self.db.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON resource_cache(expires_at)")
            except Exception:
                pass  # 索引可能已存在

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
        now = datetime.now()

        if self.db_type == "mysql":
            # MySQL使用TIMESTAMP比较
            sql = """
                SELECT data, expires_at FROM resource_cache 
                WHERE cache_key = %s AND expires_at > %s
            """
            params = (cache_key, now)
        else:
            # SQLite使用ISO格式字符串比较
            sql = """
                SELECT data, expires_at FROM resource_cache 
                WHERE cache_key = ? AND expires_at > ?
            """
            params = (cache_key, now.isoformat())

        result = self.db.query_one(sql, params)

        if result:
            if self.db_type == "mysql":
                # MySQL的JSON类型可以直接解析
                data = result['data']
                if isinstance(data, str):
                    return json.loads(data)
                return data
            else:
                # SQLite存储为TEXT，需要解析
                return json.loads(result['data'])
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

        # 准备数据
        if self.db_type == "mysql":
            # MySQL使用JSON类型
            data_json = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
            sql = """
                INSERT INTO resource_cache 
                (cache_key, resource_type, account_name, region, data, created_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    resource_type = VALUES(resource_type),
                    account_name = VALUES(account_name),
                    region = VALUES(region),
                    data = VALUES(data),
                    created_at = VALUES(created_at),
                    expires_at = VALUES(expires_at)
            """
            params = (cache_key, resource_type, account_name, region, data_json, created_at, expires_at)
        else:
            # SQLite使用TEXT类型
            data_json = json.dumps(data, ensure_ascii=False)
            sql = """
                INSERT OR REPLACE INTO resource_cache 
                (cache_key, resource_type, account_name, region, data, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (cache_key, resource_type, account_name, region, data_json, created_at.isoformat(), expires_at.isoformat())

        self.db.execute(sql, params)

    def clear(self, resource_type: str = None, account_name: str = None):
        """
        清除缓存

        Args:
            resource_type: 如果指定，只清除该类型的缓存
            account_name: 如果指定，只清除该账号的缓存
        """
        if self.db_type == "mysql":
            if resource_type and account_name:
                sql = "DELETE FROM resource_cache WHERE resource_type = %s AND account_name = %s"
                params = (resource_type, account_name)
            elif resource_type:
                sql = "DELETE FROM resource_cache WHERE resource_type = %s"
                params = (resource_type,)
            elif account_name:
                sql = "DELETE FROM resource_cache WHERE account_name = %s"
                params = (account_name,)
            else:
                sql = "DELETE FROM resource_cache"
                params = None
        else:
            if resource_type and account_name:
                sql = "DELETE FROM resource_cache WHERE resource_type = ? AND account_name = ?"
                params = (resource_type, account_name)
            elif resource_type:
                sql = "DELETE FROM resource_cache WHERE resource_type = ?"
                params = (resource_type,)
            elif account_name:
                sql = "DELETE FROM resource_cache WHERE account_name = ?"
                params = (account_name,)
            else:
                sql = "DELETE FROM resource_cache"
                params = None

        self.db.execute(sql, params)

    def cleanup_expired(self):
        """清理过期缓存"""
        now = datetime.now()
        
        if self.db_type == "mysql":
            # 先查询要删除的数量
            count_sql = "SELECT COUNT(*) as count FROM resource_cache WHERE expires_at < %s"
            count_result = self.db.query_one(count_sql, (now,))
            count = count_result['count'] if count_result else 0
            
            # 执行删除
            sql = "DELETE FROM resource_cache WHERE expires_at < %s"
            self.db.execute(sql, (now,))
            return count
        else:
            # SQLite先查询再删除
            count_sql = "SELECT COUNT(*) as count FROM resource_cache WHERE expires_at < ?"
            params = (now.isoformat(),)
            count_result = self.db.query_one(count_sql, params)
            count = count_result['count'] if count_result else 0
            
            if count > 0:
                sql = "DELETE FROM resource_cache WHERE expires_at < ?"
                self.db.execute(sql, params)
            
            return count

    def _generate_key(self, resource_type: str, account_name: str, region: str = None) -> str:
        """生成缓存键"""
        parts = [resource_type, account_name]
        if region:
            parts.append(region)
        key_str = ":".join(parts)
        return hashlib.md5(key_str.encode()).hexdigest()
