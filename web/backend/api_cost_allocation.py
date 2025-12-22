"""
成本分配API端点
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging
import json

from core.cost_allocation import (
    CostAllocationStorage, CostAllocator, AllocationRule, AllocationMethod
)
from core.bill_storage import BillStorageManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cost-allocation", tags=["cost-allocation"])

# 初始化存储和服务
_allocation_storage = CostAllocationStorage()
_allocator = CostAllocator(_allocation_storage, "data/bills.db")


# Pydantic模型
class AllocationRuleRequest(BaseModel):
    name: str
    description: Optional[str] = None
    method: str = AllocationMethod.EQUAL.value
    account_id: Optional[str] = None
    service_filter: Optional[str] = None
    tag_filter: Optional[str] = None
    date_range: Optional[str] = None
    allocation_targets: Optional[str] = None
    allocation_weights: Optional[str] = None
    enabled: bool = True


# API端点
@router.get("/rules")
def list_allocation_rules(
    account: Optional[str] = None,
    enabled_only: bool = Query(False, description="仅返回启用的规则")
) -> Dict[str, Any]:
    """获取成本分配规则列表"""
    try:
        account_id = None
        if account:
            from core.config import ConfigManager
            cm = ConfigManager()
            account_config = cm.get_account(account)
            if account_config:
                account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        rules = _allocation_storage.list_rules(account_id=account_id, enabled_only=enabled_only)
        
        return {
            "success": True,
            "data": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "method": rule.method,
                    "account_id": rule.account_id,
                    "enabled": rule.enabled,
                    "created_at": rule.created_at.isoformat() if rule.created_at else None,
                    "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
                }
                for rule in rules
            ]
        }
    except Exception as e:
        logger.error(f"获取成本分配规则列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取成本分配规则列表失败: {str(e)}")


@router.get("/rules/{rule_id}")
def get_allocation_rule(rule_id: str) -> Dict[str, Any]:
    """获取成本分配规则详情"""
    try:
        rule = _allocation_storage.get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"成本分配规则 {rule_id} 不存在")
        
        return {
            "success": True,
            "data": {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "method": rule.method,
                "account_id": rule.account_id,
                "service_filter": rule.service_filter,
                "tag_filter": rule.tag_filter,
                "date_range": rule.date_range,
                "allocation_targets": rule.allocation_targets,
                "allocation_weights": rule.allocation_weights,
                "enabled": rule.enabled,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取成本分配规则详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取成本分配规则详情失败: {str(e)}")


@router.post("/rules")
def create_allocation_rule(req: AllocationRuleRequest, account: Optional[str] = None) -> Dict[str, Any]:
    """创建成本分配规则"""
    try:
        account_id = req.account_id
        if not account_id and account:
            from core.config import ConfigManager
            cm = ConfigManager()
            account_config = cm.get_account(account)
            if account_config:
                account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        rule = AllocationRule(
            id="",  # 将在存储时生成
            name=req.name,
            description=req.description,
            method=req.method,
            account_id=account_id,
            service_filter=req.service_filter,
            tag_filter=req.tag_filter,
            date_range=req.date_range,
            allocation_targets=req.allocation_targets,
            allocation_weights=req.allocation_weights,
            enabled=req.enabled
        )
        
        rule_id = _allocation_storage.create_rule(rule)
        rule.id = rule_id
        
        return {
            "success": True,
            "data": {
                "id": rule.id,
                "name": rule.name,
                "method": rule.method
            }
        }
    except Exception as e:
        logger.error(f"创建成本分配规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建成本分配规则失败: {str(e)}")


@router.put("/rules/{rule_id}")
def update_allocation_rule(rule_id: str, req: AllocationRuleRequest) -> Dict[str, Any]:
    """更新成本分配规则"""
    try:
        existing_rule = _allocation_storage.get_rule(rule_id)
        if not existing_rule:
            raise HTTPException(status_code=404, detail=f"成本分配规则 {rule_id} 不存在")
        
        rule = AllocationRule(
            id=rule_id,
            name=req.name,
            description=req.description,
            method=req.method,
            account_id=req.account_id or existing_rule.account_id,
            service_filter=req.service_filter,
            tag_filter=req.tag_filter,
            date_range=req.date_range,
            allocation_targets=req.allocation_targets,
            allocation_weights=req.allocation_weights,
            enabled=req.enabled,
            created_at=existing_rule.created_at
        )
        
        success = _allocation_storage.update_rule(rule)
        if not success:
            raise HTTPException(status_code=500, detail="更新成本分配规则失败")
        
        return {
            "success": True,
            "data": {
                "id": rule.id,
                "name": rule.name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新成本分配规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新成本分配规则失败: {str(e)}")


@router.delete("/rules/{rule_id}")
def delete_allocation_rule(rule_id: str) -> Dict[str, Any]:
    """删除成本分配规则"""
    try:
        success = _allocation_storage.delete_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"成本分配规则 {rule_id} 不存在")
        
        return {
            "success": True,
            "message": "成本分配规则已删除"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除成本分配规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除成本分配规则失败: {str(e)}")


@router.post("/rules/{rule_id}/execute")
def execute_allocation(rule_id: str, account: Optional[str] = None) -> Dict[str, Any]:
    """执行成本分配"""
    try:
        rule = _allocation_storage.get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"成本分配规则 {rule_id} 不存在")
        
        if not rule.enabled:
            raise HTTPException(status_code=400, detail="成本分配规则未启用")
        
        # 执行分配
        result = _allocator.allocate(rule)
        
        # 保存结果
        result_id = _allocation_storage.save_result(result)
        result.id = result_id
        
        return {
            "success": True,
            "data": {
                "id": result.id,
                "rule_id": result.rule_id,
                "rule_name": result.rule_name,
                "period": result.period,
                "total_cost": result.total_cost,
                "allocated_cost": result.allocated_cost,
                "unallocated_cost": result.unallocated_cost,
                "allocations": json.loads(result.allocations) if result.allocations else []
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行成本分配失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"执行成本分配失败: {str(e)}")


@router.get("/results")
def list_allocation_results(
    rule_id: Optional[str] = None,
    period: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """获取成本分配结果列表"""
    try:
        results = _allocation_storage.list_results(rule_id=rule_id, period=period, limit=limit)
        
        return {
            "success": True,
            "data": [
                {
                    "id": result.id,
                    "rule_id": result.rule_id,
                    "rule_name": result.rule_name,
                    "period": result.period,
                    "total_cost": result.total_cost,
                    "allocated_cost": result.allocated_cost,
                    "unallocated_cost": result.unallocated_cost,
                    "allocations": json.loads(result.allocations) if result.allocations else [],
                    "created_at": result.created_at.isoformat() if result.created_at else None
                }
                for result in results
            ]
        }
    except Exception as e:
        logger.error(f"获取成本分配结果列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取成本分配结果列表失败: {str(e)}")


@router.get("/results/{result_id}")
def get_allocation_result(result_id: str) -> Dict[str, Any]:
    """获取成本分配结果详情"""
    try:
        results = _allocation_storage.list_results(limit=1000)
        result = next((r for r in results if r.id == result_id), None)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"成本分配结果 {result_id} 不存在")
        
        return {
            "success": True,
            "data": {
                "id": result.id,
                "rule_id": result.rule_id,
                "rule_name": result.rule_name,
                "period": result.period,
                "total_cost": result.total_cost,
                "allocated_cost": result.allocated_cost,
                "unallocated_cost": result.unallocated_cost,
                "allocations": json.loads(result.allocations) if result.allocations else [],
                "created_at": result.created_at.isoformat() if result.created_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取成本分配结果详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取成本分配结果详情失败: {str(e)}")




