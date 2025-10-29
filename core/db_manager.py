#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据库管理器
"""

import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path


class DatabaseManager:
    """统一数据库管理器"""

    def __init__(self, db_name: str, db_dir: str = './data/db'):
        """
        初始化数据库管理器
        
        Args:
            db_name: 数据库文件名
            db_dir: 数据库目录
        """
        self.db_path = Path(db_dir) / db_name
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None

    def connect(self):
        """建立连接"""
        if not self.conn:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, sql: str, params: tuple = None):
        """执行SQL"""
        conn = self.connect()
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        conn.commit()
        return cursor

    def query(self, sql: str, params: tuple = None) -> List[Dict]:
        """查询并返回字典列表"""
        cursor = self.execute(sql, params)
        columns = [col[0] for col in cursor.description] if cursor.description else []
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def query_one(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """查询单条记录"""
        results = self.query(sql, params)
        return results[0] if results else None

    def init_schema(self, schema_sql: str):
        """初始化数据库schema"""
        self.execute(schema_sql)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

