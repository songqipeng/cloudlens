# -*- coding: utf-8 -*-
"""
通用工具函数模块

提取常用的公共函数，避免代码重复
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    安全的JSON解析

    Args:
        json_str: JSON字符串
        default: 解析失败时的默认值

    Returns:
        解析结果或默认值
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"JSON解析失败: {e}")
        return default


def safe_get_nested(data: Dict, keys: List[str], default: Any = None) -> Any:
    """
    安全获取嵌套字典的值

    Args:
        data: 字典数据
        keys: 键路径列表，如 ['a', 'b', 'c'] 获取 data['a']['b']['c']
        default: 未找到时的默认值

    Returns:
        值或默认值

    Example:
        >>> data = {'a': {'b': {'c': 123}}}
        >>> safe_get_nested(data, ['a', 'b', 'c'])
        123
    """
    result = data
    for key in keys:
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            return default
    return result


def format_bytes(bytes_val: int, precision: int = 2) -> str:
    """
    格式化字节数为人类可读格式

    Args:
        bytes_val: 字节数
        precision: 小数位数

    Returns:
        格式化字符串，如 "1.5 GB"
    """
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    size = float(bytes_val)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.{precision}f} {units[unit_index]}"


def calculate_days_until(target_date: datetime) -> int:
    """
    计算距离目标日期还有多少天

    Args:
        target_date: 目标日期

    Returns:
        天数（负数表示已过期）
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    target = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    delta = target - today
    return delta.days


def parse_datetime(date_str: str, formats: Optional[List[str]] = None) -> Optional[datetime]:
    """
    尝试解析多种格式的日期字符串

    Args:
        date_str: 日期字符串
        formats: 日期格式列表

    Returns:
        datetime对象或None
    """
    if formats is None:
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d",
            "%Y-%m-%dT%H:%M:%S.%fZ",
        ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    logger.warning(f"无法解析日期: {date_str}")
    return None


def batch_process(items: List[Any], batch_size: int = 100):
    """
    将列表分批处理

    Args:
        items: 项目列表
        batch_size: 批次大小

    Yields:
        子列表

    Example:
        >>> for batch in batch_process(range(250), 100):
        >>>     process(batch)
    """
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符

    Args:
        filename: 原始文件名

    Returns:
        清理后的文件名
    """
    import re

    # 移除非法字符
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # 移除多余的空格和点
    sanitized = re.sub(r"\s+", "_", sanitized)
    sanitized = re.sub(r"\.+", ".", sanitized)
    # 限制长度
    if len(sanitized) > 200:
        name, ext = sanitized.rsplit(".", 1) if "." in sanitized else (sanitized, "")
        sanitized = name[: 200 - len(ext) - 1] + (f".{ext}" if ext else "")

    return sanitized


def retry_on_exception(
    func, max_retries: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)
):
    """
    自动重试装饰器

    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        delay: 重试延迟（秒）
        exceptions: 需要捕获的异常类型

    Returns:
        函数执行结果
    """
    import time

    for attempt in range(max_retries):
        try:
            return func()
        except exceptions as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"函数执行失败（尝试 {attempt + 1}/{max_retries}）: {e}")
            time.sleep(delay * (attempt + 1))  # 递增延迟

    raise RuntimeError("不应该到达这里")


def calculate_percentage(value: float, total: float, precision: int = 2) -> float:
    """
    计算百分比

    Args:
        value: 值
        total: 总数
        precision: 小数位数

    Returns:
        百分比（0-100）
    """
    if total == 0:
        return 0.0

    percentage = (value / total) * 100
    return round(percentage, precision)
