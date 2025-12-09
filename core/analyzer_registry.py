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

    @classmethod
    def load_plugins(cls, group: str = "cloudlens.analyzers"):
        """
        加载外部插件

        通过 Python entry_points 机制加载第三方插件

        Args:
            group: entry_points 组名
        """
        import sys

        if sys.version_info >= (3, 10):
            from importlib.metadata import entry_points
        else:
            # 兼容 Python 3.8/3.9
            try:
                from importlib_metadata import entry_points
            except ImportError:
                try:
                    from importlib.metadata import entry_points
                except ImportError:
                    return

        try:
            # Python 3.10+ 返回 SelectableGroups, 之前返回 dict
            eps = entry_points()
            if hasattr(eps, "select"):
                plugins = eps.select(group=group)
            else:
                plugins = eps.get(group, [])

            for entry_point in plugins:
                try:
                    # 加载插件，通常插件模块导入时会自动执行 @register
                    entry_point.load()
                except Exception as e:
                    print(f"Failed to load plugin {entry_point.name}: {e}")
        except Exception as e:
            print(f"Error loading plugins: {e}")
