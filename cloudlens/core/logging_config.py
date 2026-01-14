# -*- coding: utf-8 -*-
"""
统一日志配置模块
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True,
) -> logging.Logger:
    """
    配置统一的日志系统

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件名，如果为None则不写文件
        log_dir: 日志目录
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的备份文件数量
        console_output: 是否输出到控制台

    Returns:
        配置好的root logger
    """
    # 获取root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # 清除现有handlers
    root_logger.handlers.clear()

    # 创建格式化器
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    # 控制台handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(simple_formatter)
        console_handler.setLevel(logging.INFO)  # 控制台只显示INFO及以上
        root_logger.addHandler(console_handler)

    # 文件handler（可选）
    if log_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        file_path = log_path / log_file

        file_handler = logging.handlers.RotatingFileHandler(
            file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取命名logger

    Args:
        name: logger名称，通常使用 __name__

    Returns:
        Logger实例
    """
    return logging.getLogger(name)


# 为不同模块预设logger
class LoggerNames:
    """Logger名称常量"""

    PROVIDER = "cloudlens.provider"
    ANALYZER = "cloudlens.analyzer"
    REPORT = "cloudlens.report"
    CLI = "cloudlens.cli"
    CACHE = "cloudlens.cache"
    REMEDIATION = "cloudlens.remediation"
