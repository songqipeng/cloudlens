#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理工具
统一日志配置，支持文件和控制台输出，支持结构化日志
"""

import json
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


def setup_logger(
    name: str = "aliyunidle",
    log_file: str = None,
    level: str = "INFO",
    console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志记录器名称
        log_file: 日志文件路径（None则只输出到控制台）
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）
        console: 是否输出到控制台
        max_bytes: 日志文件最大大小（字节）
        backup_count: 备份文件数量

    Returns:
        配置好的Logger对象
    """
    logger = logging.getLogger(name)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 设置日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台输出
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 文件输出
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用RotatingFileHandler实现日志轮转
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "aliyunidle") -> logging.Logger:
    """
    获取已配置的日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        Logger对象
    """
    return logging.getLogger(name)


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化结构化日志记录器

        Args:
            logger: 基础Logger对象（None则使用默认logger）
        """
        self.logger = logger or get_logger()

    def _log_event(self, level: str, event: str, **kwargs):
        """记录结构化日志事件"""
        log_data = {"event": event, "timestamp": datetime.now().isoformat(), **kwargs}

        message = json.dumps(log_data, ensure_ascii=False)
        log_func = getattr(self.logger, level.lower())
        log_func(message)

    def log_analysis_start(self, resource_type: str, tenant: str, regions_count: int, **kwargs):
        """记录分析开始事件"""
        self._log_event(
            "info",
            "analysis_start",
            resource_type=resource_type,
            tenant=tenant,
            regions_count=regions_count,
            **kwargs,
        )

    def log_analysis_complete(
        self,
        resource_type: str,
        tenant: str,
        total_instances: int,
        idle_count: int,
        duration_seconds: float,
        **kwargs,
    ):
        """记录分析完成事件"""
        self._log_event(
            "info",
            "analysis_complete",
            resource_type=resource_type,
            tenant=tenant,
            total_instances=total_instances,
            idle_count=idle_count,
            duration_seconds=duration_seconds,
            **kwargs,
        )

    def log_instance_processed(
        self, resource_type: str, instance_id: str, region: str, is_idle: bool, **kwargs
    ):
        """记录实例处理事件"""
        self._log_event(
            "debug",
            "instance_processed",
            resource_type=resource_type,
            instance_id=instance_id,
            region=region,
            is_idle=is_idle,
            **kwargs,
        )

    def log_api_call(
        self,
        resource_type: str,
        api_name: str,
        region: str = None,
        success: bool = True,
        duration_ms: float = None,
        **kwargs,
    ):
        """记录API调用事件"""
        self._log_event(
            "debug",
            "api_call",
            resource_type=resource_type,
            api_name=api_name,
            region=region,
            success=success,
            duration_ms=duration_ms,
            **kwargs,
        )

    def log_error(
        self,
        resource_type: str,
        error_type: str,
        error_message: str,
        region: str = None,
        instance_id: str = None,
        **kwargs,
    ):
        """记录错误事件"""
        self._log_event(
            "error",
            "error_occurred",
            resource_type=resource_type,
            error_type=error_type,
            error_message=error_message,
            region=region,
            instance_id=instance_id,
            **kwargs,
        )

    def log_metric(
        self,
        resource_type: str,
        metric_name: str,
        metric_value: float,
        instance_id: str = None,
        **kwargs,
    ):
        """记录指标事件"""
        self._log_event(
            "debug",
            "metric_recorded",
            resource_type=resource_type,
            metric_name=metric_name,
            metric_value=metric_value,
            instance_id=instance_id,
            **kwargs,
        )
