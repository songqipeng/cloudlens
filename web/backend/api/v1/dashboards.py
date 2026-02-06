#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仪表盘API模块

提供仪表盘、摘要和趋势等核心监控功能
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pydantic import BaseModel

from web.backend.api_base import handle_api_error
from cloudlens.core.dashboard_manager import DashboardStorage, Dashboard, WidgetConfig
from cloudlens.core.config import ConfigManager, CloudAccount
from cloudlens.core.context import ContextManager
from cloudlens.core.cache import CacheManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# ==================== 请求模型 ====================

class WidgetConfigRequest(BaseModel):
    """Widget配置请求模型"""
    id: str
    type: str
    title: str
    position: Dict[str, int]
    config: Dict[str, Any]
    data_source: Optional[str] = None


class DashboardRequest(BaseModel):
    """仪表盘请求模型"""
    name: str
    description: Optional[str] = None
    widgets: List[WidgetConfigRequest] = []
    layout: str = "grid"
    is_shared: bool = False


# 初始化存储管理器
_dashboard_storage = DashboardStorage()


# ==================== 辅助函数 ====================

def _get_provider_for_account(account: Optional[str] = None):
    """获取账号的Provider实例"""
    cm = ConfigManager()
    if not account:
        ctx = ContextManager()
        account = ctx.get_last_account()
    if not account:
        accounts = cm.list_accounts()
        if accounts:
            account = accounts[0].name
        else:
            raise HTTPException(status_code=404, detail="No accounts configured")

    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"Account '{account}' not found")

    from cloudlens.cli.utils import get_provider
    return get_provider(account_config), account


# ==================== 仪表盘CRUD端点 ====================

@router.get("/dashboards")
def list_dashboards(account: Optional[str] = None) -> Dict[str, Any]:
    """获取自定义仪表盘列表"""
    try:
        account_id = None
        if account:
            cm = ConfigManager()
            account_config = cm.get_account(account)
            if account_config:
                account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        dashboards = _dashboard_storage.list_dashboards(account_id, include_shared=True)
        return {
            "success": True,
            "data": [dashboard.to_dict() for dashboard in dashboards],
            "count": len(dashboards)
        }
    except Exception as e:
        raise handle_api_error(e, "list_dashboards")


@router.get("/dashboards/{dashboard_id}")
def get_dashboard_detail(dashboard_id: str) -> Dict[str, Any]:
    """获取仪表盘详情"""
    try:
        dashboard = _dashboard_storage.get_dashboard(dashboard_id)
        if not dashboard:
            raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
        return {
            "success": True,
            "data": dashboard.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "get_dashboard_detail")


@router.post("/dashboards")
def create_dashboard(req: DashboardRequest, account: Optional[str] = None) -> Dict[str, Any]:
    """创建自定义仪表盘"""
    try:
        account_id = None
        if account:
            cm = ConfigManager()
            account_config = cm.get_account(account)
            if account_config:
                account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        widgets = [
            WidgetConfig(
                id=w.id,
                type=w.type,
                title=w.title,
                position=w.position,
                config=w.config,
                data_source=w.data_source
            )
            for w in req.widgets
        ]
        
        dashboard = Dashboard(
            id="", 
            name=req.name,
            description=req.description,
            widgets=widgets,
            layout=req.layout,
            account_id=account_id,
            is_shared=req.is_shared
        )
        
        dashboard_id = _dashboard_storage.create_dashboard(dashboard)
        created_dashboard = _dashboard_storage.get_dashboard(dashboard_id)
        return {
            "success": True,
            "message": "Dashboard created",
            "data": created_dashboard.to_dict() if created_dashboard else None
        }
    except Exception as e:
        raise handle_api_error(e, "create_dashboard")


@router.put("/dashboards/{dashboard_id}")
def update_dashboard(dashboard_id: str, req: DashboardRequest) -> Dict[str, Any]:
    """更新自定义仪表盘"""
    try:
        existing = _dashboard_storage.get_dashboard(dashboard_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Dashboard not found")
        
        widgets = [
            WidgetConfig(
                id=w.id,
                type=w.type,
                title=w.title,
                position=w.position,
                config=w.config,
                data_source=w.data_source
            )
            for w in req.widgets
        ]
        
        updated = Dashboard(
            id=dashboard_id,
            name=req.name,
            description=req.description,
            widgets=widgets,
            layout=req.layout,
            account_id=existing.account_id,
            is_shared=req.is_shared,
            created_at=existing.created_at
        )
        
        _dashboard_storage.update_dashboard(updated)
        return {"success": True, "message": "Dashboard updated"}
    except Exception as e:
        raise handle_api_error(e, "update_dashboard")


@router.delete("/dashboards/{dashboard_id}")
def delete_dashboard(dashboard_id: str) -> Dict[str, Any]:
    """删除自定义仪表盘"""
    try:
        success = _dashboard_storage.delete_dashboard(dashboard_id)
        if not success:
            raise HTTPException(status_code=404, detail="Dashboard not found")
        return {"success": True, "message": "Dashboard deleted"}
    except Exception as e:
        raise handle_api_error(e, "delete_dashboard")


# ==================== 仪表盘数据端点 ====================

@router.get("/dashboard/summary")
async def get_summary(
    account: Optional[str] = None, 
    force_refresh: bool = Query(False, description="强制刷新缓存")
):
    """获取仪表盘摘要数据"""
    try:
        # Resolve account name
        if not account:
            ctx = ContextManager()
            account = ctx.get_last_account()
        
        if not account:
            cm = ConfigManager()
            accounts = cm.list_accounts()
            if accounts:
                account = accounts[0].name
            else:
                raise HTTPException(status_code=400, detail="Account parameter is required")

        cache_manager = CacheManager(ttl_seconds=86400)
        
        # 尝试从缓存获取数据
        cached_result = None
        if not force_refresh:
            cached_result = cache_manager.get(resource_type="dashboard_summary", account_name=account)
            if cached_result:
                # 同步 idle_count（确保与最近一次扫描一致）
                idle_data = cache_manager.get(resource_type="dashboard_idle", account_name=account)
                if not idle_data:
                    idle_data = cache_manager.get(resource_type="idle_result", account_name=account)
                
                if idle_data:
                    cached_result["idle_count"] = len(idle_data)
                
                return {"success": True, "data": cached_result, "cached": True}
            
        # 如果缓存未命中，获取账号配置进行同步更新
        cm = ConfigManager()
        account_config = cm.get_account(account)
        if not account_config:
            raise HTTPException(status_code=404, detail=f"Account '{account}' not found")

        logger.info(f"[get_summary] 缓存未命中，同步获取仪表盘数据: {account}")
        
        # 调用 api_service 中的后台任务更新函数
        try:
            from web.backend.api_service import _update_dashboard_summary_cache
            result = _update_dashboard_summary_cache(account, account_config, force_refresh=force_refresh)
            if result:
                return {"success": True, "data": result, "cached": False}
        except Exception as e:
            logger.error(f"同步更新摘要缓存失败: {e}", exc_info=True)

        # 兜底：再次尝试从缓存获取
        result = cache_manager.get(resource_type="dashboard_summary", account_name=account)
        if result:
            return {"success": True, "data": result, "cached": False}
        
        # 如果还是没有数据，返回一个包含基础信息的默认值
        return {
            "success": True, 
            "data": {
                "account": account,
                "total_cost": 0.0,
                "idle_count": 0,
                "cost_trend": "无历史数据",
                "trend_pct": 0.0,
                "total_resources": 0,
                "resource_breakdown": {"ecs": 0, "rds": 0, "redis": 0},
                "alert_count": 0,
                "tag_coverage": 0.0,
                "savings_potential": 0.0,
                "loading": False
            }, 
            "cached": False
        }
    except HTTPException:
        raise
    except Exception as e:
        from web.backend.api_base import handle_api_error
        raise handle_api_error(e, "get_summary")


@router.get("/dashboard/trend")
async def get_dashboard_trend(
    account: Optional[str] = None,
    days: int = 30,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    granularity: Optional[str] = Query("daily", description="数据粒度: daily(按天) 或 monthly(按月)"),
    force_refresh: bool = Query(False, description="强制刷新缓存")
):
    """获取成本趋势数据"""
    try:
        # Resolve account
        if not account:
            ctx = ContextManager()
            account = ctx.get_last_account()
        
        # 使用重命名后的 api_service 避免冲突
        from web.backend.api_service import get_trend
        return await get_trend(
            account=account, 
            days=days, 
            start_date=start_date, 
            end_date=end_date,
            granularity=granularity,
            force_refresh=force_refresh
        )
    except Exception as e:
        logger.error(f"Error in get_dashboard_trend: {str(e)}", exc_info=True)
        raise handle_api_error(e, "get_dashboard_trend")


@router.get("/dashboard/idle")
def get_dashboard_idle(account: Optional[str] = None):
    """获取闲置资源"""
    try:
        provider, account_name = _get_provider_for_account(account)
        
        # 尝试从api.py导入
        import importlib.util
        import os
        
        api_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api.py')
        if os.path.exists(api_file_path):
            spec = importlib.util.spec_from_file_location("api_legacy", api_file_path)
            api_legacy = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(api_legacy)
            if hasattr(api_legacy, 'get_idle_resources'):
                return api_legacy.get_idle_resources(account=account_name)
        
        # 如果无法导入，使用简化实现
        cache_manager = CacheManager(ttl_seconds=86400)
        idle_data = cache_manager.get(resource_type="dashboard_idle", account_name=account_name)
        if not idle_data:
            idle_data = cache_manager.get(resource_type="idle_result", account_name=account_name)
        
        return {
            "success": True,
            "data": idle_data if idle_data else [],
            "cached": True
        }
    except Exception as e:
        raise handle_api_error(e, "get_dashboard_idle")
