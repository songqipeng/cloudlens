#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟标签管理API模块
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging
from pydantic import BaseModel

from web.backend.api_base import handle_api_error
from core.virtual_tags import VirtualTagStorage, VirtualTag, TagRule, TagEngine
from core.config import ConfigManager
from core.context import ContextManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# ==================== 请求模型 ====================

class TagRuleRequest(BaseModel):
    """标签规则请求模型"""
    field: str
    operator: str
    pattern: str
    priority: int = 0


class VirtualTagRequest(BaseModel):
    """虚拟标签请求模型"""
    name: str
    tag_key: str
    tag_value: str
    rules: List[TagRuleRequest]
    priority: int = 0


class TagPreviewRequest(BaseModel):
    """标签预览请求模型"""
    tag_id: Optional[str] = None
    rules: Optional[List[TagRuleRequest]] = None
    account: Optional[str] = None
    resource_type: Optional[str] = None


# 初始化存储管理器
_tag_storage = VirtualTagStorage()


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

    from cli.utils import get_provider
    return get_provider(account_config), account


# ==================== 虚拟标签端点 ====================

@router.get("/virtual-tags")
def list_virtual_tags() -> Dict[str, Any]:
    """获取所有虚拟标签列表"""
    try:
        tags = _tag_storage.list_tags()
        return {
            "success": True,
            "data": [tag.to_dict() for tag in tags],
            "count": len(tags)
        }
    except Exception as e:
        raise handle_api_error(e, "list_virtual_tags")


@router.get("/virtual-tags/{tag_id}")
def get_virtual_tag(tag_id: str) -> Dict[str, Any]:
    """获取虚拟标签详情"""
    try:
        tag = _tag_storage.get_tag(tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail=f"标签 {tag_id} 不存在")
        return {
            "success": True,
            "data": tag.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "get_virtual_tag")


@router.post("/virtual-tags")
def create_virtual_tag(req: VirtualTagRequest) -> Dict[str, Any]:
    """创建虚拟标签"""
    try:
        # 验证标签key和value
        if not req.tag_key or not req.tag_value:
            raise HTTPException(status_code=400, detail="标签key和value不能为空")
        
        # 验证规则
        if not req.rules:
            raise HTTPException(status_code=400, detail="至少需要一个规则")
        
        # 转换为TagRule对象
        rules = [
            TagRule(
                id="",  # 将在存储时生成
                tag_id="",  # 将在存储时设置
                field=rule.field,
                operator=rule.operator,
                pattern=rule.pattern,
                priority=rule.priority
            )
            for rule in req.rules
        ]
        
        # 创建VirtualTag对象
        tag = VirtualTag(
            id="",  # 将在存储时生成
            name=req.name,
            tag_key=req.tag_key,
            tag_value=req.tag_value,
            rules=rules,
            priority=req.priority
        )
        
        # 保存到数据库
        tag_id = _tag_storage.create_tag(tag)
        
        # 返回创建的标签
        created_tag = _tag_storage.get_tag(tag_id)
        return {
            "success": True,
            "message": "标签创建成功",
            "data": created_tag.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "create_virtual_tag")


@router.put("/virtual-tags/{tag_id}")
def update_virtual_tag(tag_id: str, req: VirtualTagRequest) -> Dict[str, Any]:
    """更新虚拟标签"""
    try:
        # 检查标签是否存在
        existing_tag = _tag_storage.get_tag(tag_id)
        if not existing_tag:
            raise HTTPException(status_code=404, detail=f"标签 {tag_id} 不存在")
        
        # 验证规则
        if not req.rules:
            raise HTTPException(status_code=400, detail="至少需要一个规则")
        
        # 转换为TagRule对象
        rules = [
            TagRule(
                id="",  # 将在存储时生成
                tag_id=tag_id,
                field=rule.field,
                operator=rule.operator,
                pattern=rule.pattern,
                priority=rule.priority
            )
            for rule in req.rules
        ]
        
        # 更新标签
        tag = VirtualTag(
            id=tag_id,
            name=req.name,
            tag_key=req.tag_key,
            tag_value=req.tag_value,
            rules=rules,
            priority=req.priority,
            created_at=existing_tag.created_at,
            updated_at=None  # 将在存储时更新
        )
        
        # 保存到数据库
        success = _tag_storage.update_tag(tag)
        if not success:
            raise HTTPException(status_code=500, detail="更新标签失败")
        
        # 返回更新的标签
        updated_tag = _tag_storage.get_tag(tag_id)
        return {
            "success": True,
            "message": "标签更新成功",
            "data": updated_tag.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "update_virtual_tag")


@router.delete("/virtual-tags/{tag_id}")
def delete_virtual_tag(tag_id: str) -> Dict[str, Any]:
    """删除虚拟标签"""
    try:
        success = _tag_storage.delete_tag(tag_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"标签 {tag_id} 不存在")
        return {
            "success": True,
            "message": "标签删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "delete_virtual_tag")


@router.post("/virtual-tags/preview")
def preview_tag_matches(req: TagPreviewRequest) -> Dict[str, Any]:
    """预览标签匹配的资源"""
    try:
        # 获取账号配置
        account = req.account
        if not account:
            raise HTTPException(status_code=400, detail="账号参数是必需的")
        
        provider, account_name = _get_provider_for_account(account)
        
        # 获取标签规则
        if req.tag_id:
            # 使用现有标签
            tag = _tag_storage.get_tag(req.tag_id)
            if not tag:
                raise HTTPException(status_code=404, detail=f"标签 {req.tag_id} 不存在")
            rules = tag.rules
        elif req.rules:
            # 使用预览规则
            rules = [
                TagRule(
                    id="",
                    tag_id="",
                    field=rule.field,
                    operator=rule.operator,
                    pattern=rule.pattern,
                    priority=rule.priority
                )
                for rule in req.rules
            ]
        else:
            raise HTTPException(status_code=400, detail="需要提供tag_id或rules")
        
        # 获取资源列表
        resource_type = req.resource_type or "ecs"
        if resource_type == "ecs":
            resources = provider.list_instances()
        elif resource_type == "rds":
            resources = provider.list_rds()
        elif resource_type == "redis":
            resources = provider.list_redis()
        else:
            resources = provider.list_instances()  # 默认ECS
        
        # 转换为字典格式
        resource_dicts = []
        for resource in resources:
            resource_dict = {
                "id": getattr(resource, "id", ""),
                "name": getattr(resource, "name", ""),
                "type": resource_type,
                "region": getattr(resource, "region", ""),
                "status": str(getattr(resource, "status", "")),
                "spec": getattr(resource, "spec", ""),
            }
            resource_dicts.append(resource_dict)
        
        # 匹配资源
        matched_resources = []
        for resource_dict in resource_dicts:
            # 检查是否匹配所有规则
            match = True
            for rule in rules:
                if not TagEngine.match_rule(resource_dict, rule):
                    match = False
                    break
            if match:
                matched_resources.append(resource_dict)
        
        return {
            "success": True,
            "data": {
                "matched_count": len(matched_resources),
                "total_count": len(resource_dicts),
                "resources": matched_resources[:100],  # 限制返回数量
                "rules": [{"field": r.field, "operator": r.operator, "pattern": r.pattern} for r in rules]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "preview_tag_matches")


@router.get("/virtual-tags/{tag_id}/cost")
def get_tag_cost(
    tag_id: str,
    account: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
) -> Dict[str, Any]:
    """获取标签的成本统计"""
    try:
        # 获取标签
        tag = _tag_storage.get_tag(tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail=f"标签 {tag_id} 不存在")
        
        # TODO: 实现成本计算
        # 需要：
        # 1. 获取匹配的资源
        # 2. 从账单数据中计算这些资源的成本
        # 3. 返回成本统计
        
        # 临时返回示例数据
        return {
            "success": True,
            "data": {
                "tag_id": tag_id,
                "tag_name": tag.name,
                "total_cost": 0.0,
                "resource_count": 0,
                "message": "成本计算功能开发中"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "get_tag_cost")


@router.post("/virtual-tags/clear-cache")
def clear_tag_cache(tag_id: Optional[str] = None) -> Dict[str, Any]:
    """清除标签匹配缓存"""
    try:
        _tag_storage.clear_cache(tag_id)
        return {
            "success": True,
            "message": "缓存清除成功"
        }
    except Exception as e:
        raise handle_api_error(e, "clear_tag_cache")
