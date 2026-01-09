#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号管理API v1

提供以下功能：
- 账号管理 (CRUD)
- 规则配置
- 通知配置
- 分析触发
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path
import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from typing import List, Dict, Any, Optional
import logging

from web.backend.api_base import (
    limiter,
    AccountInfo,
    AccountCreateRequest,
    AccountUpdateRequest,
    TriggerAnalysisRequest,
    handle_api_error
)
from core.progress_manager import ProgressManager
from web.backend.services.account_service import AccountService

logger = logging.getLogger(__name__)

# 可选依赖：AnalysisService 需要 aliyunsdkcore
try:
    from core.services.analysis_service import AnalysisService
    ANALYSIS_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AnalysisService not available: {e}")
    ANALYSIS_SERVICE_AVAILABLE = False
    AnalysisService = None

# 创建路由器（保持向后兼容，使用/api前缀）
router = APIRouter(prefix="/api")

# 创建Service实例（可以使用依赖注入优化）
account_service = AccountService()


# ==================== 账号管理 ====================

@router.get("/accounts")
@limiter.limit("100/minute")
def list_accounts(request: Request) -> List[Dict]:
    """
    列出所有已配置的账号

    限流: 100次/分钟
    """
    try:
        return account_service.list_accounts()
    except Exception as e:
        raise handle_api_error(e, "list_accounts")


@router.get("/settings/accounts")
def list_accounts_settings():
    """获取账号列表（用于设置页面）"""
    try:
        return account_service.list_accounts_for_settings()
    except Exception as e:
        raise handle_api_error(e, "list_accounts_settings")


@router.post("/settings/accounts")
def add_account(account_data: AccountCreateRequest):
    """添加账号"""
    try:
        return account_service.add_account(
            name=account_data.name,
            provider=account_data.provider,
            access_key_id=account_data.access_key_id,
            access_key_secret=account_data.access_key_secret,
            region=account_data.region,
            alias=account_data.alias,
        )
    except Exception as e:
        raise handle_api_error(e, "add_account")


@router.put("/settings/accounts/{account_name}")
def update_account(account_name: str, account_data: AccountUpdateRequest):
    """更新账号"""
    try:
        return account_service.update_account(
            account_name=account_name,
            alias=account_data.alias,
            provider=account_data.provider,
            access_key_id=account_data.access_key_id,
            access_key_secret=account_data.access_key_secret,
            region=account_data.region,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "update_account")


@router.delete("/settings/accounts/{account_name}")
def delete_account(account_name: str):
    """删除账号"""
    try:
        return account_service.delete_account(account_name)
    except Exception as e:
        raise handle_api_error(e, "delete_account")


# ==================== 规则配置 ====================

@router.get("/config/rules")
def get_rules() -> Dict[str, Any]:
    """获取当前优化规则"""
    try:
        return account_service.get_rules()
    except Exception as e:
        raise handle_api_error(e, "get_rules")


@router.post("/config/rules")
def set_rules(rules: Dict[str, Any]):
    """更新优化规则"""
    try:
        return account_service.set_rules(rules)
    except Exception as e:
        raise handle_api_error(e, "set_rules")


# ==================== 通知配置 ====================

@router.get("/config/notifications")
def get_notification_config() -> Dict[str, Any]:
    """获取通知配置（SMTP等）"""
    try:
        return account_service.get_notification_config()
    except Exception as e:
        raise handle_api_error(e, "get_notification_config")


@router.post("/config/notifications")
def set_notification_config(config: Dict[str, Any]):
    """保存通知配置（SMTP等）"""
    try:
        return account_service.set_notification_config(config)
    except Exception as e:
        raise handle_api_error(e, "set_notification_config")


# ==================== 分析触发 ====================

@router.post("/analyze/trigger")
def trigger_analysis(req: TriggerAnalysisRequest, background_tasks: BackgroundTasks):
    """触发闲置资源分析（后台执行，支持进度查询）"""
    if not ANALYSIS_SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="分析服务不可用：缺少必要的依赖（aliyunsdkcore）。请运行 'pip install aliyun-python-sdk-core>=2.16.0' 安装依赖，然后重启后端服务。"
        )

    try:
        logger.info(f"收到分析请求: 账号={req.account}, days={req.days}, force={req.force}")
        
        # 初始化进度管理器
        progress_manager = ProgressManager()
        task_id = req.account
        
        # 立即初始化进度，让前端可以立即开始轮询
        progress_manager.set_progress(
            task_id, 
            0, 
            100, 
            "正在初始化扫描任务...", 
            "initializing"
        )
        
        # 定义进度回调函数
        def progress_callback(current: int, total: int, message: str, stage: str):
            progress_manager.set_progress(task_id, current, total, message, stage)
        
        # 定义后台任务函数
        def _run_analysis_background():
            try:
                data, cached = AnalysisService.analyze_idle_resources(
                    req.account,
                    req.days,
                    req.force,
                    progress_callback=progress_callback
                )
                
                # 标记任务完成
                progress_manager.set_completed(task_id, {
                    "count": len(data),
                    "cached": cached
                })
                
                logger.info(f"分析完成: 找到 {len(data)} 个闲置资源")
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"分析失败: {str(e)}\n{error_trace}")
                progress_manager.set_failed(task_id, str(e))
        
        # 将分析任务放到后台执行
        background_tasks.add_task(_run_analysis_background)
        
        # 立即返回，让前端开始轮询进度
        return {
            "status": "processing",
            "message": "扫描任务已启动，请通过 /api/analyze/progress 查询进度",
            "task_id": task_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"触发分析失败: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/analyze/progress")
def get_analysis_progress(account: str):
    """获取分析进度"""
    try:
        progress_manager = ProgressManager()
        progress = progress_manager.get_progress(account)
        
        if not progress:
            return {
                "status": "not_found",
                "message": "未找到该任务"
            }
        
        return progress
    except Exception as e:
        logger.error(f"获取进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取进度失败: {str(e)}")
