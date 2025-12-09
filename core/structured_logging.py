# -*- coding: utf-8 -*-
"""
结构化日志配置

使用structlog实现JSON格式的结构化日志，便于日志分析
"""
import logging
import sys
from pathlib import Path

try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


def setup_structured_logging(
    log_level: str = "INFO", log_file: str = None, json_format: bool = True
):
    """
    配置结构化日志

    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        json_format: 是否使用JSON格式
    """
    if not STRUCTLOG_AVAILABLE:
        # 降级到标准logging
        from core.logging_config import setup_logging

        return setup_logging(log_level, log_file)

    # Structlog配置
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 配置标准logging
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=getattr(logging, log_level.upper())
    )

    # 如果有日志文件，添加文件handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        logging.root.addHandler(file_handler)


def get_structured_logger(name: str):
    """获取结构化logger"""
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)


# 使用示例
if __name__ == "__main__":
    setup_structured_logging(json_format=True)

    logger = get_structured_logger("test")

    # 结构化日志记录
    logger.info(
        "api_call_completed",
        provider="aliyun",
        api="DescribeInstances",
        duration_ms=234,
        result_count=15,
        cache_hit=True,
    )

    logger.warning("cache_miss", resource_type="ecs", account="prod-account", region="cn-hangzhou")

    logger.error(
        "api_error",
        provider="aliyun",
        error_code="InvalidAccessKeyId",
        error_message="The AccessKey ID does not exist",
    )
