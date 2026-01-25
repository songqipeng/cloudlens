#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置和账号管理API

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

from web.backend.api_base import (
    limiter,
    AccountInfo,
    AccountCreateRequest,
    AccountUpdateRequest,
    TriggerAnalysisRequest,
    handle_api_error
)
from cloudlens.core.config import ConfigManager, CloudAccount
from cloudlens.core.rules_manager import RulesManager
from cloudlens.core.cache import CacheManager
from cloudlens.core.progress_manager import ProgressManager

logger = logging.getLogger(__name__)

# 可选依赖：AnalysisService 需要 aliyunsdkcore
try:
    from cloudlens.core.services.analysis_service import AnalysisService
    ANALYSIS_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AnalysisService not available: {e}")
    ANALYSIS_SERVICE_AVAILABLE = False
    AnalysisService = None

# 创建路由器
router = APIRouter(prefix="/api")


# ==================== 账号管理 ====================

@router.get("/accounts")
@limiter.limit("100/minute")
def list_accounts(request: Request) -> List[Dict]:
    """
    列出所有已配置的账号

    限流: 100次/分钟
    """
    try:
        cm = ConfigManager()
        accounts = cm.list_accounts()
        result = []
        for account in accounts:
            if isinstance(account, CloudAccount):
                result.append({
                    "name": account.name,
                    "region": account.region,
                    "access_key_id": account.access_key_id,
                })
        return result
    except Exception as e:
        raise handle_api_error(e, "list_accounts")


@router.get("/settings/accounts")
def list_accounts_settings():
    """获取账号列表（用于设置页面）"""
    try:
        cm = ConfigManager()
        accounts = cm.list_accounts()
        result = []
        for account in accounts:
            if isinstance(account, CloudAccount):
                result.append({
                    "name": account.name,
                    "alias": getattr(account, 'alias', None),
                    "region": account.region,
                    "provider": account.provider,
                    "access_key_id": account.access_key_id,
                })
        return {"success": True, "data": result}
    except Exception as e:
        raise handle_api_error(e, "list_accounts_settings")


@router.post("/settings/accounts")
def add_account(account_data: AccountCreateRequest):
    """添加账号"""
    try:
        cm = ConfigManager()
        cm.add_account(
            name=account_data.name,
            provider=account_data.provider,
            access_key_id=account_data.access_key_id,
            access_key_secret=account_data.access_key_secret,
            region=account_data.region,
            alias=account_data.alias,
        )
        return {"success": True, "message": "账号添加成功"}
    except Exception as e:
        raise handle_api_error(e, "add_account")


@router.put("/settings/accounts/{account_name}")
def update_account(account_name: str, account_data: AccountUpdateRequest):
    """更新账号"""
    import keyring

    try:
        cm = ConfigManager()

        # 检查账号是否存在
        existing_account = cm.get_account(account_name)
        if not existing_account:
            raise HTTPException(status_code=404, detail=f"账号 '{account_name}' 不存在")

        # 获取别名
        alias = account_data.alias.strip() if account_data.alias else None

        # 获取新密钥，如果没有提供则使用现有密钥
        new_secret = account_data.access_key_secret
        if not new_secret:
            try:
                existing_secret = keyring.get_password(
                    "cloudlens",
                    f"{account_name}_access_key_secret"
                )
                if existing_secret:
                    new_secret = existing_secret
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="无法获取现有密钥，请提供新密钥"
                    )
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="无法获取现有密钥，请提供新密钥"
                )

        # 更新账号配置
        cm.add_account(
            name=account_name,
            provider=account_data.provider or existing_account.provider,
            access_key_id=account_data.access_key_id or existing_account.access_key_id,
            access_key_secret=new_secret,
            region=account_data.region or existing_account.region,
            alias=alias,
        )

        return {"success": True, "message": "账号更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "update_account")


@router.delete("/settings/accounts/{account_name}")
def delete_account(account_name: str):
    """删除账号"""
    try:
        cm = ConfigManager()
        cm.remove_account(account_name)
        return {"success": True, "message": "账号删除成功"}
    except Exception as e:
        raise handle_api_error(e, "delete_account")


# ==================== 规则配置 ====================

@router.get("/config/rules")
def get_rules() -> Dict[str, Any]:
    """获取当前优化规则"""
    try:
        rm = RulesManager()
        return rm.get_rules()
    except Exception as e:
        raise handle_api_error(e, "get_rules")


@router.post("/config/rules")
def set_rules(rules: Dict[str, Any]):
    """更新优化规则"""
    try:
        rm = RulesManager()
        rm.set_rules(rules)
        return {"status": "success", "message": "规则已更新"}
    except Exception as e:
        raise handle_api_error(e, "set_rules")


# ==================== 通知配置 ====================

def _get_smtp_config_by_email(email: str) -> Dict[str, Any]:
    """根据邮箱地址自动获取SMTP配置"""
    email_lower = email.lower().strip()

    # QQ邮箱
    if email_lower.endswith("@qq.com"):
        return {
            "smtp_host": "smtp.qq.com",
            "smtp_port": 587,
            "smtp_use_tls": True
        }
    # Gmail
    elif email_lower.endswith("@gmail.com"):
        return {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_use_tls": True
        }
    # 163邮箱
    elif email_lower.endswith("@163.com"):
        return {
            "smtp_host": "smtp.163.com",
            "smtp_port": 465,
            "smtp_use_tls": False,
            "smtp_use_ssl": True
        }
    # 126邮箱
    elif email_lower.endswith("@126.com"):
        return {
            "smtp_host": "smtp.126.com",
            "smtp_port": 465,
            "smtp_use_tls": False,
            "smtp_use_ssl": True
        }
    # 默认配置
    else:
        return {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_use_tls": True
        }


@router.get("/config/notifications")
def get_notification_config() -> Dict[str, Any]:
    """获取通知配置（SMTP等）"""
    try:
        config_dir = Path(os.path.expanduser("~/.cloudlens"))
        config_file = config_dir / "notifications.json"

        default_config = {
            "email": "",
            "auth_code": "",
            "default_receiver_email": "",
            "smtp_host": "",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_password": "",
            "smtp_from": ""
        }

        if not config_file.exists():
            return default_config

        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            result = {**default_config, **config}

            # 转换旧格式配置
            if result.get("smtp_user") and not result.get("email"):
                result["email"] = result.get("smtp_user", "")
            if result.get("smtp_password") and not result.get("auth_code"):
                result["auth_code"] = result.get("smtp_password", "")

            return result
    except Exception as e:
        logger.error(f"读取通知配置失败: {e}")
        return default_config


@router.post("/config/notifications")
def set_notification_config(config: Dict[str, Any]):
    """保存通知配置（SMTP等）"""
    try:
        config_dir = Path(os.path.expanduser("~/.cloudlens"))
        config_file = config_dir / "notifications.json"

        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)

        # 获取用户输入
        email = config.get("email", "").strip()
        auth_code = config.get("auth_code", "").strip()
        default_receiver_email = config.get("default_receiver_email", "").strip()

        # 根据邮箱自动配置SMTP
        smtp_config = {}
        if email:
            smtp_config = _get_smtp_config_by_email(email)
            smtp_config["smtp_user"] = email
            smtp_config["smtp_from"] = email
            smtp_config["smtp_password"] = auth_code

        # 保存完整配置
        full_config = {
            "email": email,
            "auth_code": auth_code,
            "default_receiver_email": default_receiver_email,
            **smtp_config
        }

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(full_config, f, indent=2, ensure_ascii=False)

        return {"status": "success", "message": "通知配置已更新"}
    except Exception as e:
        logger.error(f"保存通知配置失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"保存通知配置失败: {str(e)}"
        )


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
                
                # 保存结果到缓存，确保仪表盘能获取最新数据
                from cloudlens.core.cache import CacheManager
                cache_manager = CacheManager(ttl_seconds=86400)
                cache_manager.set(resource_type="dashboard_idle", account_name=req.account, data=data)
                cache_manager.set(resource_type="idle_result", account_name=req.account, data=data)
                logger.info(f"已将 {len(data)} 个闲置资源保存到缓存")
                
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
