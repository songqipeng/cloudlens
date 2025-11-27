#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源分析器抽象基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from core.cache_manager import CacheManager
from core.db_manager import DatabaseManager
from core.threshold_manager import ThresholdManager


class BaseResourceAnalyzer(ABC):
    """资源分析器抽象基类"""

    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        tenant_name: str,
        threshold_manager: ThresholdManager = None,
        cache_manager: CacheManager = None,
        db_manager: DatabaseManager = None,
    ):
        """
        初始化资源分析器

        Args:
            access_key_id: 阿里云AccessKey ID
            access_key_secret: 阿里云AccessKey Secret
            tenant_name: 租户名称
            threshold_manager: 阈值管理器
            cache_manager: 缓存管理器
            db_manager: 数据库管理器
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.tenant_name = tenant_name
        self.threshold_manager = threshold_manager or ThresholdManager()
        self.cache_manager = cache_manager
        self.db_manager = db_manager

    @abstractmethod
    def get_resource_type(self) -> str:
        """获取资源类型（如：ecs, rds, redis）"""
        pass

    @abstractmethod
    def get_all_regions(self) -> List[str]:
        """获取所有可用区域"""
        pass

    @abstractmethod
    def get_instances(self, region: str) -> List[Dict]:
        """获取指定区域的资源实例列表"""
        pass

    @abstractmethod
    def get_metrics(self, region: str, instance_id: str, days: int = 14) -> Dict[str, float]:
        """
        获取实例的监控指标

        Args:
            region: 区域
            instance_id: 实例ID
            days: 统计天数

        Returns:
            指标字典 {metric_name: value}
        """
        pass

    @abstractmethod
    def is_idle(
        self, instance: Dict, metrics: Dict, thresholds: Dict = None
    ) -> Tuple[bool, List[str]]:
        """
        判断资源是否闲置

        Args:
            instance: 实例信息
            metrics: 监控指标
            thresholds: 阈值配置（None则使用默认阈值）

        Returns:
            (is_idle: bool, conditions: List[str])
        """
        pass

    @abstractmethod
    def get_optimization_suggestions(self, instance: Dict, metrics: Dict) -> str:
        """获取优化建议"""
        pass

    def get_cost(self, region: str, instance_id: str) -> float:
        """
        获取成本信息（可选实现，默认返回0）

        Args:
            region: 区域
            instance_id: 实例ID

        Returns:
            月度成本（元）
        """
        return 0.0

    def analyze(self, regions: List[str] = None, days: int = 14) -> List[Dict]:
        """
        分析资源（通用流程，子类可重写）

        Args:
            regions: 要分析的区域列表（None则分析所有区域）
            days: 统计天数

        Returns:
            闲置资源列表
        """
        if regions is None:
            regions = self.get_all_regions()

        idle_resources = []

        for region in regions:
            try:
                instances = self.get_instances(region)
                for instance in instances:
                    instance_id = instance.get("InstanceId") or instance.get("DBInstanceId", "")
                    metrics = self.get_metrics(region, instance_id, days)

                    is_idle, conditions = self.is_idle(instance, metrics)
                    if is_idle:
                        optimization = self.get_optimization_suggestions(instance, metrics)
                        cost = self.get_cost(region, instance_id)

                        idle_resources.append(
                            {
                                "instance": instance,
                                "metrics": metrics,
                                "idle_conditions": conditions,
                                "optimization": optimization,
                                "cost": cost,
                                "region": region,
                            }
                        )
            except Exception as e:
                # 记录错误但继续处理其他区域
                from utils.error_handler import ErrorHandler

                ErrorHandler.handle_region_error(e, region, self.get_resource_type())
                continue

        return idle_resources
