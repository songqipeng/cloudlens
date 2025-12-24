#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入验证模块
提供统一的输入验证功能，防止注入攻击和数据错误
"""

import re
from typing import Any, List, Optional, Union
from datetime import datetime, date
from enum import Enum

from core.constants import ResourceType, CloudProvider, RegexPattern, ErrorMessage


class ValidationError(Exception):
    """验证错误异常"""
    pass


class Validator:
    """输入验证器基类"""

    @staticmethod
    def validate_required(value: Any, field_name: str) -> None:
        """验证必填字段"""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(
                ErrorMessage.MISSING_REQUIRED_FIELD.format(field=field_name)
            )

    @staticmethod
    def validate_string_length(
        value: str,
        min_length: int = 0,
        max_length: int = 1000,
        field_name: str = "字段"
    ) -> None:
        """验证字符串长度"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name}必须是字符串")

        length = len(value)
        if length < min_length:
            raise ValidationError(f"{field_name}长度不能少于{min_length}个字符")
        if length > max_length:
            raise ValidationError(f"{field_name}长度不能超过{max_length}个字符")

    @staticmethod
    def validate_regex(
        value: str,
        pattern: str,
        field_name: str = "字段",
        error_message: Optional[str] = None
    ) -> None:
        """验证正则表达式"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name}必须是字符串")

        if not re.match(pattern, value):
            msg = error_message or f"{field_name}格式不正确"
            raise ValidationError(msg)

    @staticmethod
    def validate_enum(
        value: Any,
        enum_class: type[Enum],
        field_name: str = "字段"
    ) -> None:
        """验证枚举值"""
        if isinstance(value, enum_class):
            return

        valid_values = [e.value for e in enum_class]
        if value not in valid_values:
            raise ValidationError(
                f"{field_name}必须是以下值之一: {', '.join(map(str, valid_values))}"
            )

    @staticmethod
    def validate_integer(
        value: Any,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        field_name: str = "字段"
    ) -> None:
        """验证整数"""
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name}必须是整数")

        if min_value is not None and int_value < min_value:
            raise ValidationError(f"{field_name}不能小于{min_value}")
        if max_value is not None and int_value > max_value:
            raise ValidationError(f"{field_name}不能大于{max_value}")

    @staticmethod
    def validate_float(
        value: Any,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        field_name: str = "字段"
    ) -> None:
        """验证浮点数"""
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name}必须是数字")

        if min_value is not None and float_value < min_value:
            raise ValidationError(f"{field_name}不能小于{min_value}")
        if max_value is not None and float_value > max_value:
            raise ValidationError(f"{field_name}不能大于{max_value}")

    @staticmethod
    def validate_date(
        value: Union[str, datetime, date],
        date_format: str = "%Y-%m-%d",
        field_name: str = "日期"
    ) -> datetime:
        """验证日期格式"""
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())

        if not isinstance(value, str):
            raise ValidationError(f"{field_name}格式不正确")

        try:
            return datetime.strptime(value, date_format)
        except ValueError as e:
            raise ValidationError(f"{field_name}格式不正确: {e}")

    @staticmethod
    def validate_date_range(
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        field_name: str = "日期范围"
    ) -> tuple[datetime, datetime]:
        """验证日期范围"""
        start = Validator.validate_date(start_date, field_name=f"{field_name}开始日期")
        end = Validator.validate_date(end_date, field_name=f"{field_name}结束日期")

        if start > end:
            raise ValidationError(f"{field_name}开始日期不能大于结束日期")

        return start, end

    @staticmethod
    def validate_email(value: str, field_name: str = "邮箱") -> None:
        """验证邮箱格式"""
        Validator.validate_regex(
            value,
            RegexPattern.EMAIL,
            field_name,
            f"{field_name}格式不正确"
        )

    @staticmethod
    def validate_list(
        value: Any,
        min_length: int = 0,
        max_length: Optional[int] = None,
        field_name: str = "列表"
    ) -> None:
        """验证列表"""
        if not isinstance(value, list):
            raise ValidationError(f"{field_name}必须是列表")

        length = len(value)
        if length < min_length:
            raise ValidationError(f"{field_name}至少需要{min_length}个元素")
        if max_length is not None and length > max_length:
            raise ValidationError(f"{field_name}最多{max_length}个元素")


class AccountValidator(Validator):
    """账号验证器"""

    @staticmethod
    def validate_account_name(account_name: str) -> None:
        """验证账号名称"""
        Validator.validate_required(account_name, "账号名称")
        Validator.validate_string_length(account_name, 1, 128, "账号名称")
        Validator.validate_regex(
            account_name,
            RegexPattern.ACCOUNT_NAME,
            "账号名称",
            "账号名称只能包含字母、数字、下划线和连字符"
        )

    @staticmethod
    def validate_access_key(access_key: str, field_name: str = "AccessKey") -> None:
        """验证AccessKey"""
        Validator.validate_required(access_key, field_name)
        Validator.validate_string_length(access_key, 16, 128, field_name)

    @staticmethod
    def validate_provider(provider: str) -> None:
        """验证云平台类型"""
        Validator.validate_required(provider, "云平台类型")
        Validator.validate_enum(provider, CloudProvider, "云平台类型")

    @staticmethod
    def validate_region(region: str) -> None:
        """验证区域"""
        Validator.validate_required(region, "区域")
        Validator.validate_string_length(region, 1, 64, "区域")


class ResourceValidator(Validator):
    """资源验证器"""

    @staticmethod
    def validate_resource_type(resource_type: str) -> None:
        """验证资源类型"""
        Validator.validate_required(resource_type, "资源类型")
        Validator.validate_enum(resource_type, ResourceType, "资源类型")

    @staticmethod
    def validate_instance_id(instance_id: str) -> None:
        """验证实例ID"""
        Validator.validate_required(instance_id, "实例ID")
        Validator.validate_string_length(instance_id, 1, 128, "实例ID")

    @staticmethod
    def validate_tag_key(tag_key: str) -> None:
        """验证标签键"""
        Validator.validate_required(tag_key, "标签键")
        Validator.validate_string_length(tag_key, 1, 128, "标签键")

    @staticmethod
    def validate_tag_value(tag_value: str) -> None:
        """验证标签值"""
        Validator.validate_string_length(tag_value, 0, 256, "标签值")


class QueryValidator(Validator):
    """查询参数验证器"""

    @staticmethod
    def validate_limit(limit: Any) -> int:
        """验证分页限制"""
        if limit is None:
            return 100  # 默认值

        Validator.validate_integer(limit, 1, 10000, "limit")
        return int(limit)

    @staticmethod
    def validate_offset(offset: Any) -> int:
        """验证分页偏移"""
        if offset is None:
            return 0  # 默认值

        Validator.validate_integer(offset, 0, 1000000, "offset")
        return int(offset)

    @staticmethod
    def validate_days(days: Any) -> int:
        """验证天数参数"""
        if days is None:
            return 7  # 默认值

        Validator.validate_integer(days, 1, 365, "days")
        return int(days)


# 便捷验证函数
def validate_account_input(
    account_name: str,
    provider: str,
    region: str,
    access_key_id: str,
    access_key_secret: str
) -> None:
    """验证账号输入（统一入口）"""
    AccountValidator.validate_account_name(account_name)
    AccountValidator.validate_provider(provider)
    AccountValidator.validate_region(region)
    AccountValidator.validate_access_key(access_key_id, "AccessKeyID")
    AccountValidator.validate_access_key(access_key_secret, "AccessKeySecret")


def validate_resource_query(
    account: str,
    resource_type: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> dict:
    """验证资源查询参数（统一入口）"""
    AccountValidator.validate_account_name(account)
    ResourceValidator.validate_resource_type(resource_type)

    return {
        'account': account,
        'resource_type': resource_type,
        'limit': QueryValidator.validate_limit(limit),
        'offset': QueryValidator.validate_offset(offset)
    }


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """
    清理用户输入，防止注入攻击

    Args:
        value: 输入值
        max_length: 最大长度

    Returns:
        清理后的字符串
    """
    if not isinstance(value, str):
        return str(value)[:max_length]

    # 移除控制字符
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)

    # 移除SQL关键字（可选，根据需要启用）
    # sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE']
    # for keyword in sql_keywords:
    #     cleaned = re.sub(rf'\b{keyword}\b', '', cleaned, flags=re.IGNORECASE)

    # 截断到最大长度
    return cleaned[:max_length]
