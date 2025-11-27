#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阈值管理器（支持YAML配置文件）
"""

from pathlib import Path
from typing import Any, Dict, Optional


class ThresholdManager:
    """阈值管理器"""

    def __init__(self, threshold_file: str = None):
        """
        初始化阈值管理器

        Args:
            threshold_file: 阈值配置文件路径（YAML格式），None则使用默认阈值
        """
        self.threshold_file = Path(threshold_file) if threshold_file else None
        self.thresholds = self._load_thresholds()

    def _load_thresholds(self) -> Dict[str, Any]:
        """加载阈值配置"""
        if self.threshold_file and self.threshold_file.exists():
            try:
                import yaml

                with open(self.threshold_file, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except ImportError:
                # PyYAML未安装，使用默认阈值
                pass
            except Exception as e:
                print(f"⚠️  加载阈值配置失败: {e}，使用默认阈值")

        # 返回默认阈值
        return self._get_default_thresholds()

    def _get_default_thresholds(self) -> Dict[str, Any]:
        """获取默认阈值"""
        return {
            "ecs": {
                "with_agent": {
                    "cpu_utilization": 5,
                    "memory_utilization": 20,
                    "disk_iops": 100,
                    "load_average_percent": 5,  # vCPU的5%
                    "eip_bandwidth_percent": 10,  # EIP带宽的10%
                    "disk_utilization": 20,
                },
                "without_agent": {
                    "cpu_utilization": 5,
                    "disk_iops": 100,
                    "eip_bandwidth_percent": 10,
                },
            },
            "rds": {
                "cpu_utilization": 10,
                "memory_utilization": 20,
                "connection_usage": 20,
                "qps": 100,
            },
            "redis": {"cpu_utilization": 10, "memory_utilization": 20, "connection_usage": 20},
            "mongodb": {
                "cpu_utilization": 10,
                "memory_utilization": 20,
                "disk_utilization": 20,
                "connection_utilization": 20,
                "qps": 100,
            },
            "oss": {
                "storage_capacity_gb": 1,
                "object_count": 100,
                "total_request_count": 100,
                "get_request_count": 50,
                "put_request_count": 10,
            },
        }

    def get_thresholds(self, resource_type: str, sub_type: str = None) -> Dict[str, Any]:
        """
        获取资源类型的阈值

        Args:
            resource_type: 资源类型（ecs, rds, redis等）
            sub_type: 子类型（如ecs的with_agent/without_agent）

        Returns:
            阈值字典
        """
        resource_thresholds = self.thresholds.get(resource_type, {})

        if sub_type and sub_type in resource_thresholds:
            return resource_thresholds[sub_type]

        return resource_thresholds
