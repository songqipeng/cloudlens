#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预算管理API模块
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging
from pydantic import BaseModel
from datetime import datetime

from web.backend.api_base import handle_api_error
from cloudlens.core.budget_manager import BudgetStorage, Budget, BudgetPeriod, BudgetType, AlertThreshold, BudgetCalculator, BudgetStatus
from cloudlens.core.bill_storage import BillStorageManager
from cloudlens.core.config import ConfigManager
from cloudlens.core.context import ContextManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# ==================== 请求模型 ====================

class AlertThresholdRequest(BaseModel):
    """告警阈值请求模型"""
    percentage: float
    enabled: bool = True
    notification_channels: List[str] = []


class BudgetRequest(BaseModel):
    """预算请求模型"""
    name: str
    amount: float
    period: str  # monthly/quarterly/yearly
    type: str    # total/tag/service
    start_date: str  # ISO格式日期
    tag_filter: Optional[str] = None
    service_filter: Optional[str] = None
    alerts: List[AlertThresholdRequest] = []
    account_id: Optional[str] = None


# 初始化存储管理器（延迟初始化，避免导入时连接MySQL）
_budget_storage = None
_bill_storage = None

def _get_budget_storage():
    """获取预算存储管理器（懒加载）"""
    global _budget_storage
    if _budget_storage is None:
        _budget_storage = BudgetStorage()
    return _budget_storage

def _get_bill_storage():
    """获取账单存储管理器（懒加载）"""
    global _bill_storage
    if _bill_storage is None:
        _bill_storage = BillStorageManager()
    return _bill_storage


# ==================== 辅助函数 ====================

def _get_account_id(account: Optional[str] = None) -> Optional[str]:
    """获取格式化的账号ID"""
    cm = ConfigManager()
    if not account:
        ctx = ContextManager()
        account = ctx.get_last_account()
    
    if not account:
        return None
        
    account_config = cm.get_account(account)
    if account_config:
        return f"{account_config.access_key_id[:10]}-{account}"
    return None


@router.get("/budgets")
def list_budgets(account: Optional[str] = None) -> Dict[str, Any]:
    """获取预算列表"""
    try:
        account_id = _get_account_id(account)
        budgets = _get_budget_storage().list_budgets(account_id)
        
        budget_list = []
        for budget in budgets:
            try:
                budget_list.append(budget.to_dict())
            except Exception as e:
                logger.warning(f"跳过有问题的预算 {getattr(budget, 'id', 'unknown')}: {str(e)}")
                continue
        
        return {
            "success": True,
            "data": budget_list,
            "count": len(budget_list)
        }
    except Exception as e:
        raise handle_api_error(e, "list_budgets")


@router.get("/budgets/{budget_id}")
def get_budget(budget_id: str) -> Dict[str, Any]:
    """获取预算详情"""
    try:
        budget = _get_budget_storage().get_budget(budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail=f"预算 {budget_id} 不存在")
        return {
            "success": True,
            "data": budget.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "get_budget")


@router.post("/budgets")
def create_budget(req: BudgetRequest, account: Optional[str] = None) -> Dict[str, Any]:
    """创建预算"""
    try:
        account_id = req.account_id or _get_account_id(account)
        
        # 解析开始日期
        try:
            start_date_str = req.start_date.replace('Z', '+00:00').split('.')[0] # 简化处理，移除微秒和Z
            if '+' in start_date_str:
                start_date = datetime.strptime(start_date_str.split('+')[0], "%Y-%m-%dT%H:%M:%S")
            else:
                start_date = datetime.fromisoformat(start_date_str)
        except:
            start_date = datetime.now()

        # 计算结束日期
        calculator = BudgetCalculator()
        start_date, end_date = calculator.calculate_period_dates(req.period, start_date)
        
        # 转换告警规则
        alerts = [
            AlertThreshold(
                percentage=alert.percentage,
                enabled=alert.enabled,
                notification_channels=alert.notification_channels
            )
            for alert in req.alerts
        ]
        
        # 创建预算对象
        import uuid
        budget = Budget(
            id=str(uuid.uuid4()),
            name=req.name,
            amount=req.amount,
            period=req.period,
            type=req.type,
            start_date=start_date,
            end_date=end_date,
            tag_filter=req.tag_filter,
            service_filter=req.service_filter,
            alerts=alerts,
            account_id=account_id
        )
        
        # 保存到数据库
        budget_id = _get_budget_storage().create_budget(budget)
        created_budget = _get_budget_storage().get_budget(budget_id)
        
        return {
            "success": True,
            "message": "预算创建成功",
            "data": created_budget.to_dict() if created_budget else None
        }
    except Exception as e:
        raise handle_api_error(e, "create_budget")


@router.put("/budgets/{budget_id}")
def update_budget(budget_id: str, req: BudgetRequest) -> Dict[str, Any]:
    """更新预算"""
    try:
        existing_budget = _get_budget_storage().get_budget(budget_id)
        if not existing_budget:
            raise HTTPException(status_code=404, detail=f"预算 {budget_id} 不存在")
        
        # 解析日期
        try:
            start_date = datetime.fromisoformat(req.start_date.replace('Z', ''))
        except:
            start_date = existing_budget.start_date

        calculator = BudgetCalculator()
        start_date, end_date = calculator.calculate_period_dates(req.period, start_date)
        
        alerts = [
            AlertThreshold(
                percentage=alert.percentage,
                enabled=alert.enabled,
                notification_channels=alert.notification_channels
            )
            for alert in req.alerts
        ]
        
        updated_budget = Budget(
            id=budget_id,
            name=req.name,
            amount=req.amount,
            period=req.period,
            type=req.type,
            start_date=start_date,
            end_date=end_date,
            tag_filter=req.tag_filter,
            service_filter=req.service_filter,
            alerts=alerts,
            account_id=req.account_id or existing_budget.account_id,
            created_at=existing_budget.created_at
        )
        
        _get_budget_storage().update_budget(updated_budget)
        return {
            "success": True,
            "message": "预算更新成功",
            "data": updated_budget.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "update_budget")


@router.delete("/budgets/{budget_id}")
def delete_budget(budget_id: str) -> Dict[str, Any]:
    """删除预算"""
    try:
        success = _get_budget_storage().delete_budget(budget_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"预算 {budget_id} 不存在")
        return {
            "success": True,
            "message": "预算删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "delete_budget")


@router.get("/budgets/{budget_id}/status")
def get_budget_status(budget_id: str) -> Dict[str, Any]:
    """获取预算状态"""
    try:
        budget = _get_budget_storage().get_budget(budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail=f"预算 {budget_id} 不存在")
        
        status = _get_budget_storage().calculate_budget_status(budget, budget.account_id, _get_bill_storage())
        return {
            "success": True,
            "data": status.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "get_budget_status")


@router.get("/budgets/{budget_id}/trend")
def get_budget_trend(budget_id: str, days: int = Query(30, ge=1, le=90)) -> Dict[str, Any]:
    """获取预算趋势"""
    try:
        history = _get_budget_storage().get_spend_history(budget_id, days)
        return {
            "success": True,
            "data": history
        }
    except Exception as e:
        raise handle_api_error(e, "get_budget_trend")
