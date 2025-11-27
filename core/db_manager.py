#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据库管理器
提供统一的数据库操作接口，支持资源实例和监控数据的存储
"""

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class DatabaseManager:
    """统一数据库管理器"""

    def __init__(self, db_name: str, db_dir: str = "./data/db"):
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

    def create_resource_table(self, resource_type: str, instance_columns: Dict[str, str] = None):
        """
        创建资源实例表（统一结构）

        Args:
            resource_type: 资源类型（如：rds, redis）
            instance_columns: 额外的列定义 {column_name: column_type}
        """
        table_name = f"{resource_type}_instances"

        # 标准列
        base_columns = {
            "instance_id": "TEXT PRIMARY KEY",
            "instance_name": "TEXT",
            "instance_type": "TEXT",
            "region": "TEXT",
            "status": "TEXT",
            "creation_time": "TEXT",
            "expire_time": "TEXT",
            "monthly_cost": "REAL DEFAULT 0",
        }

        # 合并额外列
        if instance_columns:
            base_columns.update(instance_columns)

        # 构建SQL
        columns_sql = ", ".join([f"{k} {v}" for k, v in base_columns.items()])
        sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {columns_sql}
        )
        """
        self.execute(sql)

    def create_monitoring_table(self, resource_type: str):
        """
        创建监控数据表（统一结构）

        Args:
            resource_type: 资源类型
        """
        table_name = f"{resource_type}_monitoring_data"
        instance_id_col = "instance_id" if resource_type != "eip" else "allocation_id"

        sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {instance_id_col} TEXT,
            metric_name TEXT,
            metric_value REAL,
            timestamp INTEGER,
            FOREIGN KEY ({instance_id_col}) REFERENCES {resource_type}_instances (instance_id)
        )
        """
        self.execute(sql)

    def save_instance(
        self, resource_type: str, instance: Dict[str, Any], instance_id_key: str = "InstanceId"
    ):
        """
        保存资源实例

        Args:
            resource_type: 资源类型
            instance: 实例数据字典
            instance_id_key: 实例ID字段名
        """
        table_name = f"{resource_type}_instances"
        instance_id = (
            instance.get(instance_id_key)
            or instance.get("DBInstanceId")
            or instance.get("InstanceId")
        )

        if not instance_id:
            return

        # 准备数据
        columns = [
            "instance_id",
            "instance_name",
            "instance_type",
            "region",
            "status",
            "creation_time",
            "expire_time",
            "monthly_cost",
        ]
        values = [
            instance_id,
            instance.get("InstanceName") or instance.get("DBInstanceDescription", ""),
            instance.get("InstanceType") or instance.get("DBInstanceClass", ""),
            instance.get("Region") or instance.get("RegionId", ""),
            instance.get("Status", ""),
            instance.get("CreationTime", ""),
            instance.get("ExpireTime", ""),
            instance.get("monthly_cost", 0) or instance.get("MonthlyCost", 0),
        ]

        # 使用INSERT OR REPLACE
        placeholders = ", ".join(["?" for _ in columns])
        columns_sql = ", ".join(columns)
        sql = f"""
        INSERT OR REPLACE INTO {table_name} ({columns_sql})
        VALUES ({placeholders})
        """
        self.execute(sql, tuple(values))

    def save_instances_batch(
        self,
        resource_type: str,
        instances: List[Dict[str, Any]],
        instance_id_key: str = "InstanceId",
    ):
        """
        批量保存资源实例

        Args:
            resource_type: 资源类型
            instances: 实例列表
            instance_id_key: 实例ID字段名
        """
        for instance in instances:
            self.save_instance(resource_type, instance, instance_id_key)

    def save_metric(
        self, resource_type: str, instance_id: str, metric_name: str, metric_value: float
    ):
        """
        保存监控指标

        Args:
            resource_type: 资源类型
            instance_id: 实例ID
            metric_name: 指标名称
            metric_value: 指标值
        """
        table_name = f"{resource_type}_monitoring_data"
        id_col = "instance_id" if resource_type != "eip" else "allocation_id"

        sql = f"""
        INSERT INTO {table_name} ({id_col}, metric_name, metric_value, timestamp)
        VALUES (?, ?, ?, ?)
        """
        self.execute(sql, (instance_id, metric_name, metric_value, int(time.time())))

    def save_metrics_batch(self, resource_type: str, instance_id: str, metrics: Dict[str, float]):
        """
        批量保存监控指标

        Args:
            resource_type: 资源类型
            instance_id: 实例ID
            metrics: 指标字典 {metric_name: value}
        """
        for metric_name, metric_value in metrics.items():
            self.save_metric(resource_type, instance_id, metric_name, metric_value)

    def get_instance(self, resource_type: str, instance_id: str) -> Optional[Dict]:
        """
        获取资源实例

        Args:
            resource_type: 资源类型
            instance_id: 实例ID

        Returns:
            实例数据字典
        """
        table_name = f"{resource_type}_instances"
        sql = f"SELECT * FROM {table_name} WHERE instance_id = ?"
        return self.query_one(sql, (instance_id,))

    def get_all_instances(self, resource_type: str, region: Optional[str] = None) -> List[Dict]:
        """
        获取所有资源实例

        Args:
            resource_type: 资源类型
            region: 区域（可选，None则获取所有区域）

        Returns:
            实例列表
        """
        table_name = f"{resource_type}_instances"
        if region:
            sql = f"SELECT * FROM {table_name} WHERE region = ?"
            return self.query(sql, (region,))
        else:
            sql = f"SELECT * FROM {table_name}"
            return self.query(sql)

    def get_metrics(
        self, resource_type: str, instance_id: str, metric_names: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        获取监控指标

        Args:
            resource_type: 资源类型
            instance_id: 实例ID
            metric_names: 指标名称列表（可选，None则获取所有）

        Returns:
            指标字典 {metric_name: value}
        """
        table_name = f"{resource_type}_monitoring_data"
        id_col = "instance_id" if resource_type != "eip" else "allocation_id"

        if metric_names:
            placeholders = ", ".join(["?" for _ in metric_names])
            sql = f"""
            SELECT metric_name, metric_value 
            FROM {table_name} 
            WHERE {id_col} = ? AND metric_name IN ({placeholders})
            ORDER BY timestamp DESC
            """
            params = (instance_id,) + tuple(metric_names)
        else:
            sql = f"""
            SELECT metric_name, metric_value 
            FROM {table_name} 
            WHERE {id_col} = ?
            ORDER BY timestamp DESC
            """
            params = (instance_id,)

        results = self.query(sql, params)

        # 如果有多条记录，取最新的
        metrics = {}
        seen = set()
        for row in results:
            metric_name = row["metric_name"]
            if metric_name not in seen:
                metrics[metric_name] = row["metric_value"]
                seen.add(metric_name)

        return metrics
