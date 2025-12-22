#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库存储基类
提供统一的数据库存储接口，支持SQLite和MySQL
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from core.database import DatabaseFactory, DatabaseAdapter

logger = logging.getLogger(__name__)


class BaseStorage:
    """数据库存储基类"""
    
    def __init__(self, db_type: Optional[str] = None, table_name: str = None, **kwargs):
        """
        初始化存储管理器
        
        Args:
            db_type: 数据库类型（'sqlite' 或 'mysql'），None则从环境变量读取
            table_name: 主表名
            **kwargs: 数据库配置参数
        """
        self.db_type = db_type or os.getenv("DB_TYPE", "mysql").lower()
        self.table_name = table_name
        
        # 创建数据库适配器
        if self.db_type == "mysql":
            self.db = DatabaseFactory.create_adapter("mysql", **kwargs)
        else:
            # SQLite使用默认路径
            db_path = kwargs.get('db_path') or os.getenv("SQLITE_DB_PATH")
            if not db_path and 'db_name' in kwargs:
                db_dir = Path.home() / ".cloudlens"
                db_path = str(db_dir / kwargs['db_name'])
            elif not db_path:
                db_dir = Path.home() / ".cloudlens"
                db_name = kwargs.get('db_name', f"{table_name or 'data'}.db")
                db_path = str(db_dir / db_name)
            self.db = DatabaseFactory.create_adapter("sqlite", db_path=db_path)
    
    def _normalize_json(self, value: Any) -> Any:
        """标准化JSON字段"""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except:
                return value
        if isinstance(value, (dict, list)):
            return value
        return value
    
    def _serialize_json(self, value: Any) -> str:
        """序列化JSON字段"""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)
    
    def _get_placeholder(self) -> str:
        """获取SQL占位符"""
        return "%s" if self.db_type == "mysql" else "?"
    
    def _quote_identifier(self, identifier: str) -> str:
        """引用标识符（处理MySQL保留关键字）"""
        reserved_keywords = ['usage', 'key', 'order', 'group', 'select', 'table', 'index']
        if identifier.lower() in reserved_keywords:
            return f"`{identifier}`"
        return identifier


