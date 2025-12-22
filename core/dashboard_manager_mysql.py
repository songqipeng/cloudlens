#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仪表盘存储管理器（MySQL版本）
使用数据库抽象层，支持SQLite和MySQL
"""

import logging
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from core.database import DatabaseFactory, DatabaseAdapter
from core.dashboard_manager import Dashboard, WidgetConfig

logger = logging.getLogger(__name__)


class DashboardStorage:
    """仪表盘存储管理器（支持SQLite和MySQL）"""
    
    def __init__(self, db_path: Optional[str] = None, db_type: Optional[str] = None):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径（仅SQLite使用）
            db_type: 数据库类型（'sqlite' 或 'mysql'），None则从环境变量读取
        """
        self.db_type = db_type or os.getenv("DB_TYPE", "mysql").lower()
        
        if self.db_type == "mysql":
            self.db = DatabaseFactory.create_adapter("mysql")
            self.db_path = None
        else:
            if db_path is None:
                db_dir = Path.home() / ".cloudlens"
                db_dir.mkdir(parents=True, exist_ok=True)
                db_path = str(db_dir / "dashboards.db")
            self.db_path = db_path
            self.db = DatabaseFactory.create_adapter("sqlite", db_path=db_path)
        
        self._init_database()
    
    def _get_placeholder(self) -> str:
        """获取SQL占位符"""
        return "%s" if self.db_type == "mysql" else "?"
    
    def _init_database(self):
        """初始化数据库表结构"""
        if self.db_type == "mysql":
            # MySQL表结构已在init_mysql_schema.sql中创建
            try:
                self.db.query("SELECT 1 FROM dashboards LIMIT 1")
                logger.info("MySQL仪表盘表已存在")
            except Exception:
                logger.warning("MySQL仪表盘表不存在，请先运行sql/init_mysql_schema.sql")
        else:
            # SQLite表结构
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS dashboards (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    layout TEXT DEFAULT 'grid',
                    widgets TEXT NOT NULL,
                    account_id TEXT,
                    is_shared INTEGER DEFAULT 0,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def create_dashboard(self, dashboard: Dashboard) -> str:
        """创建仪表盘"""
        if not dashboard.id:
            dashboard.id = str(uuid.uuid4())
        
        now = datetime.now()
        dashboard.created_at = now
        dashboard.updated_at = now
        
        placeholder = self._get_placeholder()
        widgets_json = json.dumps([w.to_dict() for w in dashboard.widgets], ensure_ascii=False)
        
        if self.db_type == "mysql":
            sql = f"""
                INSERT INTO dashboards (
                    id, name, description, layout, widgets, account_id, is_shared,
                    created_by, created_at, updated_at
                ) VALUES ({', '.join([placeholder] * 10)})
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    description = VALUES(description),
                    layout = VALUES(layout),
                    widgets = VALUES(widgets),
                    account_id = VALUES(account_id),
                    is_shared = VALUES(is_shared),
                    created_by = VALUES(created_by),
                    updated_at = VALUES(updated_at)
            """
        else:
            sql = f"""
                INSERT OR REPLACE INTO dashboards (
                    id, name, description, layout, widgets, account_id, is_shared,
                    created_by, created_at, updated_at
                ) VALUES ({', '.join([placeholder] * 10)})
            """
        
        params = (
            dashboard.id,
            dashboard.name,
            dashboard.description,
            dashboard.layout,
            widgets_json,
            dashboard.account_id,
            1 if dashboard.is_shared else 0,
            dashboard.created_by,
            dashboard.created_at,
            dashboard.updated_at
        )
        
        self.db.execute(sql, params)
        return dashboard.id
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """获取仪表盘"""
        placeholder = self._get_placeholder()
        result = self.db.query_one(
            f"SELECT * FROM dashboards WHERE id = {placeholder}",
            (dashboard_id,)
        )
        
        if not result:
            return None
        
        # 解析widgets
        widgets_data = json.loads(result['widgets']) if isinstance(result['widgets'], str) else result['widgets']
        widgets = [WidgetConfig(**w) for w in widgets_data]
        
        return Dashboard(
            id=result['id'],
            name=result['name'],
            description=result.get('description'),
            layout=result.get('layout', 'grid'),
            widgets=widgets,
            account_id=result.get('account_id'),
            is_shared=bool(result.get('is_shared', 0)),
            created_by=result.get('created_by'),
            created_at=result.get('created_at'),
            updated_at=result.get('updated_at')
        )
    
    def list_dashboards(self, account_id: Optional[str] = None, include_shared: bool = True) -> List[Dashboard]:
        """列出仪表盘"""
        placeholder = self._get_placeholder()
        conditions = []
        params = []
        
        if account_id:
            conditions.append(f"account_id = {placeholder}")
            params.append(account_id)
        
        if include_shared:
            conditions.append(f"(is_shared = 1 OR account_id = {placeholder})")
            if account_id:
                params.append(account_id)
        else:
            if account_id:
                conditions.append(f"account_id = {placeholder}")
                params.append(account_id)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        results = self.db.query(
            f"SELECT * FROM dashboards WHERE {where_clause} ORDER BY updated_at DESC",
            tuple(params) if params else None
        )
        
        dashboards = []
        for row in results:
            widgets_data = json.loads(row['widgets']) if isinstance(row['widgets'], str) else row['widgets']
            widgets = [WidgetConfig(**w) for w in widgets_data]
            
            dashboards.append(Dashboard(
                id=row['id'],
                name=row['name'],
                description=row.get('description'),
                layout=row.get('layout', 'grid'),
                widgets=widgets,
                account_id=row.get('account_id'),
                is_shared=bool(row.get('is_shared', 0)),
                created_by=row.get('created_by'),
                created_at=row.get('created_at'),
                updated_at=row.get('updated_at')
            ))
        
        return dashboards
    
    def update_dashboard(self, dashboard: Dashboard) -> bool:
        """更新仪表盘"""
        dashboard.updated_at = datetime.now()
        
        placeholder = self._get_placeholder()
        widgets_json = json.dumps([w.to_dict() for w in dashboard.widgets], ensure_ascii=False)
        
        sql = f"""
            UPDATE dashboards SET
                name = {placeholder},
                description = {placeholder},
                layout = {placeholder},
                widgets = {placeholder},
                account_id = {placeholder},
                is_shared = {placeholder},
                created_by = {placeholder},
                updated_at = {placeholder}
            WHERE id = {placeholder}
        """
        
        params = (
            dashboard.name,
            dashboard.description,
            dashboard.layout,
            widgets_json,
            dashboard.account_id,
            1 if dashboard.is_shared else 0,
            dashboard.created_by,
            dashboard.updated_at,
            dashboard.id
        )
        
        self.db.execute(sql, params)
        return True
    
    def delete_dashboard(self, dashboard_id: str) -> bool:
        """删除仪表盘"""
        placeholder = self._get_placeholder()
        self.db.execute(
            f"DELETE FROM dashboards WHERE id = {placeholder}",
            (dashboard_id,)
        )
        return True


