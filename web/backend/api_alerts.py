"""
告警系统API端点
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
import logging

from cloudlens.core.alert_manager import AlertStorage, AlertRule, Alert, AlertType, AlertSeverity, AlertCondition
from cloudlens.core.alert_engine import AlertEngine
from cloudlens.core.notification_service import NotificationService
from cloudlens.core.bill_storage import BillStorageManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# 初始化存储和服务
_alert_storage = AlertStorage()
_bill_storage = BillStorageManager()
_alert_engine = AlertEngine(_alert_storage, _bill_storage)

# 从配置文件加载通知配置
def _load_notification_config():
    """加载通知配置"""
    import json
    import os
    from pathlib import Path
    
    config_dir = Path(os.path.expanduser("~/.cloudlens"))
    config_file = config_dir / "notifications.json"
    
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _get_notification_service():
    """获取通知服务实例（每次调用时重新加载配置）"""
    config = _load_notification_config()
    return NotificationService(config=config)

_notification_service = _get_notification_service()


# Pydantic模型
class AlertRuleRequest(BaseModel):
    name: str
    description: Optional[str] = None
    type: str = AlertType.COST_THRESHOLD.value
    severity: str = AlertSeverity.WARNING.value
    enabled: bool = True
    condition: str = AlertCondition.GT.value
    threshold: Optional[float] = None
    metric: Optional[str] = None
    account_id: Optional[str] = None
    tag_filter: Optional[str] = None
    service_filter: Optional[str] = None
    notify_email: Optional[str] = None
    notify_webhook: Optional[str] = None
    notify_sms: Optional[str] = None
    check_interval: int = 60
    cooldown_period: int = 300


class AlertRuleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    type: str
    severity: str
    enabled: bool
    condition: str
    threshold: Optional[float] = None
    metric: Optional[str] = None
    account_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AlertResponse(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    severity: str
    status: str
    title: str
    message: str
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    account_id: Optional[str] = None
    triggered_at: Optional[str] = None


# API端点
@router.get("/rules")
def list_alert_rules(
    account: Optional[str] = None,
    enabled_only: bool = Query(False, description="仅返回启用的规则")
) -> Dict[str, Any]:
    """获取告警规则列表"""
    try:
        account_id = None
        if account:
            from cloudlens.core.config import ConfigManager
            cm = ConfigManager()
            account_config = cm.get_account(account)
            if account_config:
                account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        rules = _alert_storage.list_rules(account_id=account_id, enabled_only=enabled_only)
        
        return {
            "success": True,
            "data": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "type": rule.type,
                    "severity": rule.severity,
                    "enabled": rule.enabled,
                    "condition": rule.condition,
                    "threshold": rule.threshold,
                    "metric": rule.metric,
                    "account_id": rule.account_id,
                    "created_at": rule.created_at.isoformat() if rule.created_at else None,
                    "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
                }
                for rule in rules
            ]
        }
    except Exception as e:
        logger.error(f"获取告警规则列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取告警规则列表失败: {str(e)}")


@router.get("/rules/{rule_id}")
def get_alert_rule(rule_id: str) -> Dict[str, Any]:
    """获取告警规则详情"""
    try:
        rule = _alert_storage.get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"告警规则 {rule_id} 不存在")
        
        return {
            "success": True,
            "data": {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "type": rule.type,
                "severity": rule.severity,
                "enabled": rule.enabled,
                "condition": rule.condition,
                "threshold": rule.threshold,
                "metric": rule.metric,
                "account_id": rule.account_id,
                "tag_filter": rule.tag_filter,
                "service_filter": rule.service_filter,
                "notify_email": rule.notify_email,
                "notify_webhook": rule.notify_webhook,
                "notify_sms": rule.notify_sms,
                "check_interval": rule.check_interval,
                "cooldown_period": rule.cooldown_period,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取告警规则详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取告警规则详情失败: {str(e)}")


@router.post("/rules")
def create_alert_rule(req: AlertRuleRequest, account: Optional[str] = None) -> Dict[str, Any]:
    """创建告警规则"""
    try:
        account_id = req.account_id
        if not account_id and account:
            from cloudlens.core.config import ConfigManager
            cm = ConfigManager()
            account_config = cm.get_account(account)
            if account_config:
                account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        # 如果没有指定接收邮箱，使用默认接收邮箱
        notify_email = req.notify_email
        if not notify_email:
            notification_config = _load_notification_config()
            default_receiver_email = notification_config.get("default_receiver_email", "")
            if default_receiver_email:
                notify_email = default_receiver_email
        
        rule = AlertRule(
            id="",  # 将在存储时生成
            name=req.name,
            description=req.description,
            type=req.type,
            severity=req.severity,
            enabled=req.enabled,
            condition=req.condition,
            threshold=req.threshold,
            metric=req.metric,
            account_id=account_id,
            tag_filter=req.tag_filter,
            service_filter=req.service_filter,
            notify_email=notify_email,
            notify_webhook=req.notify_webhook,
            notify_sms=req.notify_sms,
            check_interval=req.check_interval,
            cooldown_period=req.cooldown_period
        )
        
        rule_id = _alert_storage.create_rule(rule)
        rule.id = rule_id
        
        return {
            "success": True,
            "data": {
                "id": rule.id,
                "name": rule.name,
                "type": rule.type,
                "severity": rule.severity,
                "enabled": rule.enabled
            }
        }
    except Exception as e:
        logger.error(f"创建告警规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建告警规则失败: {str(e)}")


@router.put("/rules/{rule_id}")
def update_alert_rule(rule_id: str, req: AlertRuleRequest) -> Dict[str, Any]:
    """更新告警规则"""
    try:
        existing_rule = _alert_storage.get_rule(rule_id)
        if not existing_rule:
            raise HTTPException(status_code=404, detail=f"告警规则 {rule_id} 不存在")
        
        # 如果没有指定接收邮箱，使用默认接收邮箱
        notify_email = req.notify_email
        if not notify_email:
            notification_config = _load_notification_config()
            default_receiver_email = notification_config.get("default_receiver_email", "")
            if default_receiver_email:
                notify_email = default_receiver_email
        
        rule = AlertRule(
            id=rule_id,
            name=req.name,
            description=req.description,
            type=req.type,
            severity=req.severity,
            enabled=req.enabled,
            condition=req.condition,
            threshold=req.threshold,
            metric=req.metric,
            account_id=req.account_id or existing_rule.account_id,
            tag_filter=req.tag_filter,
            service_filter=req.service_filter,
            notify_email=notify_email,
            notify_webhook=req.notify_webhook,
            notify_sms=req.notify_sms,
            check_interval=req.check_interval,
            cooldown_period=req.cooldown_period,
            created_at=existing_rule.created_at
        )
        
        success = _alert_storage.update_rule(rule)
        if not success:
            raise HTTPException(status_code=500, detail="更新告警规则失败")
        
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
        logger.error(f"更新告警规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新告警规则失败: {str(e)}")


@router.delete("/rules/{rule_id}")
def delete_alert_rule(rule_id: str) -> Dict[str, Any]:
    """删除告警规则"""
    try:
        success = _alert_storage.delete_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"告警规则 {rule_id} 不存在")
        
        return {
            "success": True,
            "message": "告警规则已删除"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除告警规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除告警规则失败: {str(e)}")


@router.get("")
def list_alerts(
    account: Optional[str] = None,
    rule_id: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """获取告警列表"""
    try:
        account_id = None
        if account:
            from cloudlens.core.config import ConfigManager
            cm = ConfigManager()
            account_config = cm.get_account(account)
            if account_config:
                account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        alerts = _alert_storage.list_alerts(
            account_id=account_id,
            rule_id=rule_id,
            status=status,
            severity=severity,
            limit=limit
        )
        
        return {
            "success": True,
            "data": [
                {
                    "id": alert.id,
                    "rule_id": alert.rule_id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity,
                    "status": alert.status,
                    "title": alert.title,
                    "message": alert.message,
                    "metric_value": alert.metric_value,
                    "threshold": alert.threshold,
                    "account_id": alert.account_id,
                    "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None
                }
                for alert in alerts
            ]
        }
    except Exception as e:
        logger.error(f"获取告警列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取告警列表失败: {str(e)}")


@router.post("/rules/{rule_id}/check")
def check_alert_rule(rule_id: str, account: Optional[str] = None) -> Dict[str, Any]:
    """手动触发告警规则检查"""
    try:
        account_id = None
        if account:
            from cloudlens.core.config import ConfigManager
            cm = ConfigManager()
            account_config = cm.get_account(account)
            if account_config:
                account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        alert = _alert_engine.check_rule(rule_id, account_id)
        
        if alert:
            # 发送通知
            rule = _alert_storage.get_rule(rule_id)
            if rule:
                notification_service = _get_notification_service()
                notification_service.send_alert_notification(alert, rule)
            
            return {
                "success": True,
                "triggered": True,
                "data": {
                    "id": alert.id,
                    "title": alert.title,
                    "message": alert.message
                }
            }
        else:
            return {
                "success": True,
                "triggered": False,
                "message": "告警规则未触发"
            }
    except Exception as e:
        logger.error(f"检查告警规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检查告警规则失败: {str(e)}")


@router.post("/check-all")
def check_all_rules(account: Optional[str] = None) -> Dict[str, Any]:
    """检查所有告警规则"""
    try:
        account_id = None
        if account:
            from cloudlens.core.config import ConfigManager
            cm = ConfigManager()
            account_config = cm.get_account(account)
            if account_config:
                account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        triggered_alerts = _alert_engine.check_all_rules(account_id)
        
        # 发送通知
        notification_service = _get_notification_service()
        for alert in triggered_alerts:
            rule = _alert_storage.get_rule(alert.rule_id)
            if rule:
                notification_service.send_alert_notification(alert, rule)
        
        return {
            "success": True,
            "triggered_count": len(triggered_alerts),
            "data": [
                {
                    "id": alert.id,
                    "rule_id": alert.rule_id,
                    "title": alert.title,
                    "severity": alert.severity
                }
                for alert in triggered_alerts
            ]
        }
    except Exception as e:
        logger.error(f"检查所有告警规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检查所有告警规则失败: {str(e)}")


@router.put("/{alert_id}/status")
def update_alert_status(
    alert_id: str,
    status: str,
    performed_by: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """更新告警状态"""
    try:
        success = _alert_storage.update_alert_status(alert_id, status, performed_by, notes)
        if not success:
            raise HTTPException(status_code=404, detail=f"告警 {alert_id} 不存在")
        
        return {
            "success": True,
            "message": "告警状态已更新"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新告警状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新告警状态失败: {str(e)}")






