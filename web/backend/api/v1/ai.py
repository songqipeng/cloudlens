"""
AI优化建议API端点
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from cloudlens.core.ai_optimizer import AIOptimizer, OptimizationSuggestion
from cloudlens.core.cache.decorators import cache_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-optimizer", tags=["ai-optimizer"])

# 初始化AI优化器
_ai_optimizer = AIOptimizer()


# API端点
@router.get("/suggestions")
@cache_response(ttl_seconds=1800, key_prefix="ai_optimizer_suggestions")  # 缓存30分钟
def get_optimization_suggestions(
    account: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    force_refresh: bool = Query(False, description="强制刷新缓存")
) -> Dict[str, Any]:
    """获取优化建议列表（已缓存30分钟）"""
    try:
        account_id = None
        if account:
            from cloudlens.core.config import ConfigManager
            cm = ConfigManager()
            account_config = cm.get_account(account)
            if account_config:
                account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        suggestions = _ai_optimizer.generate_suggestions(account_id=account_id, limit=limit)
        
        return {
            "success": True,
            "data": [
                {
                    "id": s.id,
                    "type": s.type,
                    "priority": s.priority,
                    "title": s.title,
                    "description": s.description,
                    "resource_id": s.resource_id,
                    "resource_type": s.resource_type,
                    "current_cost": s.current_cost,
                    "potential_savings": s.potential_savings,
                    "confidence": s.confidence,
                    "action": s.action,
                    "estimated_savings": s.estimated_savings,
                    "account_id": s.account_id,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "status": s.status
                }
                for s in suggestions
            ]
        }
    except Exception as e:
        logger.error(f"获取优化建议失败: {str(e)}")
        # 返回空数据而不是抛出异常，避免前端显示错误
        return {
            "success": False,
            "data": [],
            "error": f"获取优化建议失败: {str(e)}",
            "message": "无法加载优化建议，请稍后重试或检查数据是否充足"
        }


@router.get("/predict")
@cache_response(ttl_seconds=3600, key_prefix="ai_optimizer_predict")  # 缓存1小时
def predict_cost(
    account: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    force_refresh: bool = Query(False, description="强制刷新缓存")
) -> Dict[str, Any]:
    """预测未来成本（已缓存1小时）"""
    try:
        account_id = None
        if account:
            from cloudlens.core.config import ConfigManager
            cm = ConfigManager()
            account_config = cm.get_account(account)
            if account_config:
                account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        prediction = _ai_optimizer.predict_cost(account_id=account_id, days=days)
        
        if not prediction:
            return {
                "success": False,
                "data": None,
                "message": "无法生成成本预测（数据不足）"
            }
        
        return {
            "success": True,
            "data": prediction
        }
    except Exception as e:
        logger.error(f"成本预测失败: {str(e)}")
        # 返回空数据而不是抛出异常
        return {
            "success": False,
            "data": None,
            "error": f"成本预测失败: {str(e)}",
            "message": "无法生成成本预测，请稍后重试或检查数据是否充足"
        }


@router.get("/analyze/{resource_type}/{resource_id}")
def analyze_resource(
    resource_type: str,
    resource_id: str,
    account: Optional[str] = None
) -> Dict[str, Any]:
    """分析资源使用情况"""
    try:
        account_id = None
        if account:
            from cloudlens.core.config import ConfigManager
            cm = ConfigManager()
            account_config = cm.get_account(account)
            if account_config:
                account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        analysis = _ai_optimizer.analyze_resource_usage(
            resource_id=resource_id,
            resource_type=resource_type,
            account_id=account_id
        )
        
        if not analysis:
            return {
                "success": False,
                "message": "无法分析资源使用情况"
            }
        
        return {
            "success": True,
            "data": analysis
        }
    except Exception as e:
        logger.error(f"资源分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"资源分析失败: {str(e)}")






