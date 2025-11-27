# -*- coding: utf-8 -*-
from typing import Any, Dict, Optional, Type

from core.base_analyzer import BaseResourceAnalyzer


class AnalyzerRegistry:
    """分析器注册中心"""

    _analyzers: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, resource_type: str, display_name: str, emoji: str = "📦"):
        """
        注册分析器装饰器

        Args:
            resource_type: 资源类型标识（如 'ecs', 'rds'）
            display_name: 显示名称（如 'ECS云服务器'）
            emoji: 显示图标
        """

        def decorator(analyzer_class: Type[BaseResourceAnalyzer]):
            cls._analyzers[resource_type] = {
                "class": analyzer_class,
                "display_name": display_name,
                "emoji": emoji,
            }
            return analyzer_class

        return decorator

    @classmethod
    def get_analyzer_info(cls, resource_type: str) -> Optional[Dict[str, Any]]:
        """获取分析器信息"""
        return cls._analyzers.get(resource_type)

    @classmethod
    def get_analyzer_class(cls, resource_type: str) -> Optional[Type[BaseResourceAnalyzer]]:
        """获取分析器类"""
        info = cls.get_analyzer_info(resource_type)
        return info["class"] if info else None

    @classmethod
    def list_analyzers(cls) -> Dict[str, Dict[str, Any]]:
        """列出所有已注册的分析器"""
        return cls._analyzers
