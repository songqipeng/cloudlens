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


# 初始化存储管理器（延迟初始化，避免导入时连接MySQL）
_dashboard_storage = None

def get_dashboard_storage():
    """获取仪表盘存储管理器（单例模式）"""
    global _dashboard_storage
    if _dashboard_storage is None:
        _dashboard_storage = DashboardStorage()
    return _dashboard_storage


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
                account_id = account  # Use account name directly
        
        storage = get_dashboard_storage()
        dashboards = storage.list_dashboards(account_id, include_shared=True)
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
        storage = get_dashboard_storage()
        dashboard = storage.get_dashboard(dashboard_id)
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
                account_id = account  # Use account name directly
        
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
        
        storage = get_dashboard_storage()
        dashboard_id = storage.create_dashboard(dashboard)
        created_dashboard = storage.get_dashboard(dashboard_id)
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
        storage = get_dashboard_storage()
        existing = storage.get_dashboard(dashboard_id)
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
        
        storage = get_dashboard_storage()
        storage.update_dashboard(updated)
        return {"success": True, "message": "Dashboard updated"}
    except Exception as e:
        raise handle_api_error(e, "update_dashboard")


@router.delete("/dashboards/{dashboard_id}")
def delete_dashboard(dashboard_id: str) -> Dict[str, Any]:
    """删除自定义仪表盘"""
    try:
        storage = get_dashboard_storage()
        success = storage.delete_dashboard(dashboard_id)
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

        # ✅ 新增：初始化缓存验证器（dashboard_summary不需要深度检查，只验证时间戳）
        from cloudlens.core.cache_validator import SmartCacheValidator
        from datetime import datetime

        # Dashboard摘要数据变化频繁，使用较高验证概率
        validator = SmartCacheValidator(db_adapter=None, verification_probability=0.2)

        # 尝试从缓存获取数据
        cached_result = None
        if not force_refresh:
            # 获取原始缓存数据（包含metadata）
            cached_raw = cache_manager.get(resource_type="dashboard_summary", account_name=account, raw=True)

            if cached_raw:
                # ✅ 新增：验证缓存有效性（只做基础+时间戳检查，不做深度检查）
                now = datetime.now()
                current_cycle = now.strftime("%Y-%m")

                is_valid, reason, should_refresh = validator.validate(
                    cached_data=cached_raw,
                    billing_cycle=current_cycle,  # Dashboard使用当月数据
                    account_id=account,
                    force_deep_check=False
                )

                if is_valid:
                    # 返回data部分（兼容旧格式）
                    if isinstance(cached_raw, dict) and 'data' in cached_raw:
                        cached_result = cached_raw['data']
                    else:
                        cached_result = cached_raw  # 向后兼容旧格式

                    # 同步 idle_count（确保与最近一次扫描一致）
                    idle_data = cache_manager.get(resource_type="dashboard_idle", account_name=account)
                    if not idle_data:
                        idle_data = cache_manager.get(resource_type="idle_result", account_name=account)

                    if idle_data:
                        cached_result["idle_count"] = len(idle_data)

                    logger.info(f"✅ Dashboard缓存有效: {account}")
                    return {"success": True, "data": cached_result, "cached": True}
                else:
                    logger.warning(f"⚠️ Dashboard缓存验证失败: {reason}，查询数据库")

        # 缓存未命中，直接从数据库查询（不再返回"加载中"）
        from cloudlens.core.database import get_database_adapter
        from datetime import datetime, timedelta

        db = get_database_adapter()

        # 获取当前月份和上月
        now = datetime.now()
        current_cycle = now.strftime("%Y-%m")
        first_day_this_month = now.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        last_cycle = last_day_last_month.strftime("%Y-%m")

        # 查询本月成本
        current_month_query = f"""
            SELECT SUM(payment_amount) as total_cost
            FROM bill_items
            WHERE account_id = '{account}'
            AND billing_cycle = '{current_cycle}'
        """
        current_result = db.query(current_month_query)
        current_cost = float(current_result[0]['total_cost'] or 0) if current_result else 0.0

        # 查询上月成本
        last_month_query = f"""
            SELECT SUM(payment_amount) as total_cost
            FROM bill_items
            WHERE account_id = '{account}'
            AND billing_cycle = '{last_cycle}'
        """
        last_result = db.query(last_month_query)
        last_cost = float(last_result[0]['total_cost'] or 0) if last_result else 0.0

        # 计算趋势
        if last_cost > 0:
            trend_pct = ((current_cost - last_cost) / last_cost) * 100
            if trend_pct > 5:
                cost_trend = f"上升 {trend_pct:.1f}%"
            elif trend_pct < -5:
                cost_trend = f"下降 {abs(trend_pct):.1f}%"
            else:
                cost_trend = "基本持平"
        else:
            trend_pct = 0.0
            cost_trend = "数据不足" if current_cost == 0 else "首月数据"

        # 查询总记录数和金额
        total_query = f"""
            SELECT
                COUNT(DISTINCT billing_cycle) as total_months,
                COUNT(*) as total_records,
                SUM(payment_amount) as total_amount
            FROM bill_items
            WHERE account_id = '{account}'
        """
        total_result = db.query(total_query)
        total_info = total_result[0] if total_result else {}

        db_result = {
            "account": account,
            "total_cost": current_cost,
            "idle_count": 0,
            "cost_trend": cost_trend,
            "trend_pct": round(trend_pct, 2),
            "total_resources": 0,
            "resource_breakdown": {"ecs": 0, "rds": 0, "redis": 0},
            "alert_count": 0,
            "tag_coverage": 0.0,
            "savings_potential": 0.0,
            "loading": False,
            "data_info": {
                "total_months": total_info.get('total_months', 0),
                "total_records": total_info.get('total_records', 0),
                "total_amount": float(total_info.get('total_amount') or 0),
                "current_cycle": current_cycle,
                "last_cycle": last_cycle
            }
        }

        # 后台异步更新缓存（延迟导入，避免触发其他模块的导入）
        import threading

        cm = ConfigManager()
        account_config = cm.get_account(account)

        def update_cache_task():
            try:
                if account_config:
                    # 延迟导入，避免在导入时触发其他模块的初始化
                    from web.backend.api import _update_dashboard_summary_cache
                    _update_dashboard_summary_cache(account, account_config)
            except Exception as e:
                logger.error(f"Background summary update failed: {e}")

        thread = threading.Thread(target=update_cache_task, daemon=True)
        thread.start()

        return {"success": True, "data": db_result, "cached": False, "from_db": True}
    except HTTPException:
        raise
    except Exception as e:
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
        
        # 复用原有趋势计算逻辑 (api.py 中的 get_trend)
        from web.backend.api import get_trend
        return await get_trend(
            account=account, 
            days=days, 
            start_date=start_date, 
            end_date=end_date,
            granularity=granularity,
            force_refresh=force_refresh
        )
    except Exception as e:
        raise handle_api_error(e, "get_dashboard_trend")


@router.get("/dashboard/idle")
def get_dashboard_idle(account: Optional[str] = None):
    """获取闲置资源"""
    try:
        provider, account_name = _get_provider_for_account(account)
        from web.backend.api import get_idle_resources
        return get_idle_resources(account=account_name)
    except Exception as e:
        raise handle_api_error(e, "get_dashboard_idle")
