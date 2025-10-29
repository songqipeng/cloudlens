#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理工具
统一日志配置，支持文件和控制台输出
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logger(
    name: str = 'aliyunidle',
    log_file: str = None,
    level: str = 'INFO',
    console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
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
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
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
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = 'aliyunidle') -> logging.Logger:
    """
    获取已配置的日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        Logger对象
    """
    return logging.getLogger(name)

