"""
Advanced Filter Engine
支持复杂的资源筛选表达式
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, List

logger = logging.getLogger("FilterEngine")


class FilterEngine:
    """高级筛选引擎"""

    @staticmethod
    def parse_filter(filter_str: str) -> List[tuple]:
        """
        解析过滤表达式

        支持的格式:
        - key=value
        - key!=value
        - key>value
        - key<value
        - AND / OR 连接

        示例: "charge_type=PrePaid AND expire_days<7"

        Returns:
            解析后的条件列表 [(field, operator, value, logic)]
        """
        if not filter_str:
            return []

        conditions = []

        # 分割AND/OR
        parts = re.split(r"\s+(AND|OR)\s+", filter_str, flags=re.IGNORECASE)

        current_logic = "AND"
        for i, part in enumerate(parts):
            part = part.strip()

            if part.upper() in ("AND", "OR"):
                current_logic = part.upper()
                continue

            # 解析单个条件
            match = re.match(r"(\w+)\s*(!=|<=|>=|=|<|>)\s*(.+)", part)
            if match:
                field, operator, value = match.groups()
                value = value.strip().strip('"').strip("'")

                # 类型转换
                if value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit():
                    value = float(value)

                conditions.append((field, operator, value, current_logic))

        return conditions

    @staticmethod
    def apply_filter(resources: List[Any], filter_str: str) -> List[Any]:
        """
        应用筛选条件

        Args:
            resources: 资源列表
            filter_str: 筛选表达式

        Returns:
            筛选后的资源列表
        """
        if not filter_str:
            return resources

        conditions = FilterEngine.parse_filter(filter_str)
        if not conditions:
            return resources

        result = []
        for resource in resources:
            if FilterEngine._match_resource(resource, conditions):
                result.append(resource)

        return result

    @staticmethod
    def _match_resource(resource: Any, conditions: List[tuple]) -> bool:
        """检查资源是否匹配所有条件"""
        if not conditions:
            return True

        # 处理第一个条件
        field, operator, value, _ = conditions[0]
        match_result = FilterEngine._match_condition(resource, field, operator, value)

        # 处理后续条件
        for condition in conditions[1:]:
            field, operator, value, logic = condition
            current_match = FilterEngine._match_condition(resource, field, operator, value)

            if logic == "AND":
                match_result = match_result and current_match
            else:  # OR
                match_result = match_result or current_match

        return match_result

    @staticmethod
    def _match_condition(resource: Any, field: str, operator: str, value: Any) -> bool:
        """匹配单个条件"""
        # 获取资源字段值
        if hasattr(resource, field):
            resource_value = getattr(resource, field)
        elif isinstance(resource, dict) and field in resource:
            resource_value = resource[field]
        else:
            # 特殊字段处理
            if field == "expire_days":
                if hasattr(resource, "expired_time") and resource.expired_time:
                    resource_value = (resource.expired_time - datetime.now()).days
                else:
                    return False
            else:
                return False

        # 处理枚举类型
        if hasattr(resource_value, "value"):
            resource_value = resource_value.value

        # 比较操作
        try:
            if operator == "=":
                return str(resource_value).lower() == str(value).lower()
            elif operator == "!=":
                return str(resource_value).lower() != str(value).lower()
            elif operator == ">":
                return float(resource_value) > float(value)
            elif operator == "<":
                return float(resource_value) < float(value)
            elif operator == ">=":
                return float(resource_value) >= float(value)
            elif operator == "<=":
                return float(resource_value) <= float(value)
        except (ValueError, TypeError):
            return False

        return False
