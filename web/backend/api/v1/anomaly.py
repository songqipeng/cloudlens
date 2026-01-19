#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成本异常检测API模块
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta

from web.backend.api_base import handle_api_error
from cloudlens.core.anomaly_detector import AnomalyDetector
from cloudlens.core.notification_service import NotificationService
from cloudlens.core.config import ConfigManager
from cloudlens.core.context import ContextManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/anomaly", tags=["anomaly"])

# 初始化服务
_anomaly_detector = AnomalyDetector()
_notification_service = NotificationService()


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


@router.post("/detect")
def detect_anomaly(
    account: Optional[str] = None,
    date: Optional[str] = None,
    baseline_days: int = Query(30, ge=7, le=90),
    threshold_std: float = Query(2.0, ge=1.0, le=5.0)
) -> Dict[str, Any]:
    """检测成本异常"""
    try:
        account_id = _get_account_id(account)
        if not account_id:
            raise HTTPException(status_code=400, detail="请指定账号")
        
        anomalies = _anomaly_detector.detect(
            account_id=account_id,
            date=date,
            baseline_days=baseline_days,
            threshold_std=threshold_std
        )
        
        # 发送告警（如果有异常）
        notification_results = {}
        for anomaly in anomalies:
            if anomaly.severity in ["high", "critical"]:
                results = _notification_service.send_anomaly_alert(
                    {
                        "account_id": anomaly.account_id,
                        "date": anomaly.date,
                        "current_cost": anomaly.current_cost,
                        "baseline_cost": anomaly.baseline_cost,
                        "deviation_pct": anomaly.deviation_pct,
                        "severity": anomaly.severity,
                        "root_cause": anomaly.root_cause
                    }
                )
                notification_results[anomaly.id] = results
        
        return {
            "success": True,
            "data": [
                {
                    "id": a.id,
                    "account_id": a.account_id,
                    "date": a.date,
                    "current_cost": a.current_cost,
                    "baseline_cost": a.baseline_cost,
                    "deviation_pct": a.deviation_pct,
                    "severity": a.severity,
                    "root_cause": a.root_cause,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in anomalies
            ],
            "count": len(anomalies),
            "notifications": notification_results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "detect_anomaly")


@router.get("/list")
def list_anomalies(
    account: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """获取异常记录列表"""
    try:
        account_id = _get_account_id(account) if account else None
        
        # 默认查询最近30天
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        anomalies = _anomaly_detector.get_anomalies(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            severity=severity,
            limit=limit
        )
        
        return {
            "success": True,
            "data": anomalies,
            "count": len(anomalies)
        }
    except Exception as e:
        raise handle_api_error(e, "list_anomalies")


@router.post("/notify/{anomaly_id}")
def notify_anomaly(
    anomaly_id: str,
    channels: List[str] = Query(["email", "dingtalk", "wechat"])
) -> Dict[str, Any]:
    """手动发送异常告警"""
    try:
        # 获取异常记录
        anomalies = _anomaly_detector.get_anomalies(limit=1000)
        anomaly = next((a for a in anomalies if a["id"] == anomaly_id), None)
        
        if not anomaly:
            raise HTTPException(status_code=404, detail="异常记录不存在")
        
        results = _notification_service.send_anomaly_alert(anomaly, channels)
        
        return {
            "success": True,
            "message": "告警发送完成",
            "results": results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "notify_anomaly")
