#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义仪表盘管理模块
支持仪表盘的创建、编辑、保存和分享
"""

import logging
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import uuid

logger = logging.getLogger(__name__)


@dataclass
class WidgetConfig:
    """Widget配置"""
    id: str
    type: str              # widget类型（chart, metric, table等）
    title: str
    position: Dict[str, int]  # {x, y, w, h} 网格位置
    config: Dict[str, Any]    # widget特定配置
    data_source: Optional[str] = None  # 数据源配置
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WidgetConfig':
        return cls(**data)


@dataclass
class Dashboard:
    """仪表盘"""
    id: str
    name: str
    description: Optional[str] = None
    widgets: List[WidgetConfig] = None
    layout: str = "grid"  # grid, freeform
    account_id: Optional[str] = None
    is_shared: bool = False
    created_by: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.widgets is None:
            self.widgets = []
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['widgets'] = [w.to_dict() for w in self.widgets]
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Dashboard':
        widgets = [WidgetConfig.from_dict(w) for w in data.get('widgets', [])]
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        updated_at = datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description'),
            widgets=widgets,
            layout=data.get('layout', 'grid'),
            account_id=data.get('account_id'),
            is_shared=data.get('is_shared', False),
            created_by=data.get('created_by'),
            created_at=created_at,
            updated_at=updated_at
        )


class DashboardStorage:
    """仪表盘存储管理器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径，默认使用~/.cloudlens/dashboards.db
        """
        if db_path is None:
            db_dir = Path.home() / ".cloudlens"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "dashboards.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 创建仪表盘表
            cursor.execute("""
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
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dashboards_account ON dashboards(account_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dashboards_shared ON dashboards(is_shared)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dashboards_created_by ON dashboards(created_by)")
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def create_dashboard(self, dashboard: Dashboard) -> str:
        """创建仪表盘"""
        if not dashboard.id:
            dashboard.id = str(uuid.uuid4())
        
        now = datetime.now()
        dashboard.created_at = now
        dashboard.updated_at = now
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO dashboards (
                    id, name, description, layout,
                    widgets, account_id, is_shared,
                    created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dashboard.id,
                dashboard.name,
                dashboard.description,
                dashboard.layout,
                json.dumps([w.to_dict() for w in dashboard.widgets]),
                dashboard.account_id,
                1 if dashboard.is_shared else 0,
                dashboard.created_by,
                dashboard.created_at.isoformat(),
                dashboard.updated_at.isoformat()
            ))
            
            conn.commit()
            logger.info(f"Created dashboard: {dashboard.name} ({dashboard.id})")
            return dashboard.id
        except Exception as e:
            logger.error(f"Error creating dashboard: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """获取仪表盘"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM dashboards WHERE id = ?", (dashboard_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            widgets_data = json.loads(row['widgets'] or '[]')
            widgets = [WidgetConfig.from_dict(w) for w in widgets_data]
            
            dashboard = Dashboard(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                widgets=widgets,
                layout=row['layout'],
                account_id=row['account_id'],
                is_shared=bool(row['is_shared']),
                created_by=row['created_by'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
            )
            
            return dashboard
        finally:
            conn.close()
    
    def list_dashboards(self, account_id: Optional[str] = None, include_shared: bool = True) -> List[Dashboard]:
        """列出仪表盘"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if account_id:
                if include_shared:
                    cursor.execute("""
                        SELECT id FROM dashboards
                        WHERE account_id = ? OR is_shared = 1
                        ORDER BY updated_at DESC
                    """, (account_id,))
                else:
                    cursor.execute("""
                        SELECT id FROM dashboards
                        WHERE account_id = ?
                        ORDER BY updated_at DESC
                    """, (account_id,))
            else:
                cursor.execute("SELECT id FROM dashboards ORDER BY updated_at DESC")
            
            dashboard_ids = [row['id'] for row in cursor.fetchall()]
            
            dashboards = []
            for dashboard_id in dashboard_ids:
                dashboard = self.get_dashboard(dashboard_id)
                if dashboard:
                    dashboards.append(dashboard)
            
            return dashboards
        finally:
            conn.close()
    
    def update_dashboard(self, dashboard: Dashboard) -> bool:
        """更新仪表盘"""
        dashboard.updated_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE dashboards
                SET name = ?, description = ?, layout = ?,
                    widgets = ?, account_id = ?, is_shared = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                dashboard.name,
                dashboard.description,
                dashboard.layout,
                json.dumps([w.to_dict() for w in dashboard.widgets]),
                dashboard.account_id,
                1 if dashboard.is_shared else 0,
                dashboard.updated_at.isoformat(),
                dashboard.id
            ))
            
            conn.commit()
            logger.info(f"Updated dashboard: {dashboard.name} ({dashboard.id})")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_dashboard(self, dashboard_id: str) -> bool:
        """删除仪表盘"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM dashboards WHERE id = ?", (dashboard_id,))
            conn.commit()
            logger.info(f"Deleted dashboard: {dashboard_id}")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting dashboard: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

