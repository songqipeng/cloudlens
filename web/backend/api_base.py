#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API基础模块 - 共享工具和依赖

所有API模块共享的基础组件：
- 常用导入
- Pydantic模型
- 工具函数
- 限流器配置
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Body, Depends, Request
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
import logging

# 日志配置
logger = logging.getLogger(__name__)

# 限流器（使用IP地址作为key）
limiter = Limiter(key_func=get_remote_address)

# ========================
# Pydantic模型定义
# ========================

class AccountInfo(BaseModel):
    """账号信息"""
    name: str
    region: str
    access_key_id: str

class AccountUpdateRequest(BaseModel):
    """账号更新请求"""
    alias: Optional[str] = None
    provider: Optional[str] = None
    region: Optional[str] = None
    access_key_id: Optional[str] = None
    access_key_secret: Optional[str] = None

class AccountCreateRequest(BaseModel):
    """账号创建请求"""
    name: str
    alias: Optional[str] = None
    provider: str = "aliyun"
    region: str = "cn-hangzhou"
    access_key_id: str
    access_key_secret: str

class DashboardSummary(BaseModel):
    """仪表盘摘要"""
    account: str
    total_cost: float
    idle_count: int
    cost_trend: str
    trend_pct: float

class TriggerAnalysisRequest(BaseModel):
    """触发分析请求"""
    account: str
    days: int = 7
    force: bool = True

class BudgetCreateRequest(BaseModel):
    """预算创建请求"""
    name: str
    account_name: str
    amount: float
    period: str = "monthly"  # monthly, quarterly, yearly
    alert_threshold: float = 0.8
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class BudgetUpdateRequest(BaseModel):
    """预算更新请求"""
    name: Optional[str] = None
    amount: Optional[float] = None
    period: Optional[str] = None
    alert_threshold: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class ReportGenerateRequest(BaseModel):
    """报告生成请求"""
    account: str
    report_type: str  # cost, security, optimization
    start_date: str
    end_date: str
    format: str = "pdf"  # pdf, excel, json

# ========================
# 工具函数
# ========================

def format_cost(amount: float, currency: str = "CNY") -> str:
    """格式化成本显示"""
    if currency == "CNY":
        return f"¥{amount:,.2f}"
    elif currency == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"

def parse_date_range(start_date: Optional[str], end_date: Optional[str]) -> tuple:
    """解析日期范围"""
    if start_date:
        start = datetime.fromisoformat(start_date)
    else:
        start = datetime.now() - timedelta(days=30)

    if end_date:
        end = datetime.fromisoformat(end_date)
    else:
        end = datetime.now()

    return start, end

def calculate_trend_percentage(current: float, previous: float) -> float:
    """计算趋势百分比"""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100

def get_trend_direction(percentage: float) -> str:
    """获取趋势方向"""
    if percentage > 5:
        return "up"
    elif percentage < -5:
        return "down"
    else:
        return "stable"

# ========================
# 错误处理
# ========================

class APIError(HTTPException):
    """API统一错误"""
    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        super().__init__(
            status_code=status_code,
            detail={
                "message": message,
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            }
        )

def handle_api_error(e: Exception, context: str = "") -> HTTPException:
    """统一API错误处理"""
    logger.error(f"API Error in {context}: {str(e)}", exc_info=True)

    if isinstance(e, HTTPException):
        return e

    return APIError(
        status_code=500,
        message=f"Internal server error: {str(e)}",
        details={"context": context}
    )
