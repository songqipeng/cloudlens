#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康检查和就绪探针
用于Kubernetes liveness/readiness probes和监控系统
"""

from fastapi import APIRouter, Response
from datetime import datetime
import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    健康检查（存活探针）

    用途：
    - Kubernetes liveness probe
    - 监控系统检查应用是否存活
    - 负载均衡器健康检查

    返回示例：
    {
        "status": "healthy",
        "timestamp": "2024-12-29T10:30:00",
        "uptime_seconds": 3600
    }
    """
    # 记录应用启动时间（简化版，生产环境应使用全局变量）
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "cloudlens-api",
        "version": "1.1.0"
    }


@router.get("/ready")
async def readiness_check() -> Response:
    """
    就绪检查（就绪探针）

    用途：
    - Kubernetes readiness probe
    - 检查应用是否准备好接收流量
    - 依赖服务健康检查

    检查项：
    1. 数据库连接
    2. 缓存系统
    3. 关键配置

    返回：
    - 200: 就绪，可以接收流量
    - 503: 未就绪，不应接收流量
    """
    start_time = time.time()
    checks = {}
    all_healthy = True

    # 1. 检查数据库连接
    db_healthy, db_details = await _check_database()
    checks['database'] = db_details
    if not db_healthy:
        all_healthy = False

    # 2. 检查缓存系统
    cache_healthy, cache_details = await _check_cache()
    checks['cache'] = cache_details
    if not cache_healthy:
        all_healthy = False

    # 3. 检查配置管理
    config_healthy, config_details = await _check_config()
    checks['config'] = config_details
    if not config_healthy:
        all_healthy = False

    # 计算检查耗时
    duration_ms = round((time.time() - start_time) * 1000, 2)

    # 构建响应
    status_code = 200 if all_healthy else 503
    response_data = {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
        "duration_ms": duration_ms
    }

    # 记录日志
    if not all_healthy:
        failed_checks = [k for k, v in checks.items() if v.get('status') != 'ok']
        logger.warning(f"Readiness check failed. Failed checks: {failed_checks}")

    return Response(
        content=_to_json(response_data),
        status_code=status_code,
        media_type="application/json"
    )


async def _check_database() -> tuple[bool, Dict[str, Any]]:
    """检查数据库连接"""
    try:
        from core.database import DatabaseFactory

        start = time.time()
        db = DatabaseFactory.create()

        # 执行简单查询测试连接
        result = db.query_one("SELECT 1 as test")

        duration_ms = round((time.time() - start) * 1000, 2)

        if result and result.get('test') == 1:
            return True, {
                "status": "ok",
                "message": "Database connection successful",
                "response_time_ms": duration_ms,
                "type": db.db_type if hasattr(db, 'db_type') else "unknown"
            }
        else:
            return False, {
                "status": "error",
                "message": "Database query returned unexpected result",
                "response_time_ms": duration_ms
            }

    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return False, {
            "status": "error",
            "message": f"Database connection failed: {str(e)}"
        }


async def _check_cache() -> tuple[bool, Dict[str, Any]]:
    """检查缓存系统"""
    try:
        from core.cache import CacheManager

        start = time.time()
        cache = CacheManager()

        # 简单测试：写入并读取
        test_key = "_health_check_test_"
        test_value = {"timestamp": datetime.now().isoformat()}

        cache.set(
            resource_type=test_key,
            account_name="health_check",
            data=test_value
        )

        cached = cache.get(
            resource_type=test_key,
            account_name="health_check"
        )

        duration_ms = round((time.time() - start) * 1000, 2)

        if cached is not None:
            return True, {
                "status": "ok",
                "message": "Cache system operational",
                "response_time_ms": duration_ms
            }
        else:
            return False, {
                "status": "degraded",
                "message": "Cache write/read test failed",
                "response_time_ms": duration_ms
            }

    except Exception as e:
        logger.error(f"Cache health check failed: {e}", exc_info=True)
        # 缓存失败不应导致应用不可用（降级服务）
        return True, {
            "status": "degraded",
            "message": f"Cache unavailable (degraded mode): {str(e)}"
        }


async def _check_config() -> tuple[bool, Dict[str, Any]]:
    """检查配置管理"""
    try:
        from core.config_manager import ConfigManager

        start = time.time()
        cm = ConfigManager()

        # 检查是否能访问配置
        accounts = cm.list_accounts()

        duration_ms = round((time.time() - start) * 1000, 2)

        return True, {
            "status": "ok",
            "message": f"Config loaded successfully ({len(accounts)} accounts)",
            "response_time_ms": duration_ms
        }

    except Exception as e:
        logger.error(f"Config health check failed: {e}", exc_info=True)
        return False, {
            "status": "error",
            "message": f"Config system failed: {str(e)}"
        }


def _to_json(data: Dict[str, Any]) -> str:
    """将字典转换为JSON字符串"""
    import json
    return json.dumps(data, ensure_ascii=False, indent=2)


@router.get("/ping")
async def ping():
    """
    简单的ping端点

    最轻量的健康检查，无任何依赖检查
    用于快速验证应用是否响应
    """
    return {"status": "pong"}


@router.get("/metrics/health")
async def health_metrics() -> Dict[str, Any]:
    """
    健康指标（详细版）

    包含更详细的系统指标，用于监控仪表盘
    """
    import psutil
    import os

    try:
        # 系统资源使用情况
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # 进程信息
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory.percent, 2),
                "memory_available_mb": round(memory.available / 1024 / 1024, 2),
                "disk_percent": round(disk.percent, 2),
                "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2)
            },
            "process": {
                "pid": os.getpid(),
                "memory_mb": round(process_memory.rss / 1024 / 1024, 2),
                "cpu_percent": round(process.cpu_percent(interval=0.1), 2),
                "threads": process.num_threads()
            }
        }
    except ImportError:
        # psutil未安装，返回基本信息
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "message": "Install psutil for detailed metrics"
        }
    except Exception as e:
        logger.error(f"Failed to get health metrics: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
