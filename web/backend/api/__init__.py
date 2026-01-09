"""
API模块 - 路由注册中心

所有模块使用/api前缀（保持向后兼容），直接注册即可
"""
from fastapi import APIRouter

# 创建API路由器
api_router = APIRouter()

# 延迟导入，避免循环依赖
def register_v1_routes():
    """注册v1路由（延迟导入）"""
    from .v1 import (
        accounts,
        resources,
        costs,
        billing,
        discounts,
        security,
        budgets,
        alerts,
        reports,
        tags,
        dashboards,
        optimization,
        cost_allocation,
        ai,
    )
    
    # 注册所有路由（所有模块已使用/api前缀，直接注册）
    api_router.include_router(accounts.router, tags=["accounts"])
    api_router.include_router(resources.router, tags=["resources"])
    api_router.include_router(costs.router, tags=["costs"])
    api_router.include_router(billing.router, tags=["billing"])
    api_router.include_router(discounts.router, tags=["discounts"])
    api_router.include_router(security.router, tags=["security"])
    api_router.include_router(budgets.router, tags=["budgets"])
    api_router.include_router(alerts.router, tags=["alerts"])
    api_router.include_router(reports.router, tags=["reports"])
    api_router.include_router(tags.router, tags=["tags"])
    api_router.include_router(dashboards.router, tags=["dashboards"])
    api_router.include_router(optimization.router, tags=["optimization"])
    api_router.include_router(cost_allocation.router, tags=["cost-allocation"])
    api_router.include_router(ai.router, tags=["ai"])

# 立即注册路由
register_v1_routes()

__all__ = ["api_router"]
