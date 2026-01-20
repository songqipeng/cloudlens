#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单查询API模块
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging

from web.backend.api_base import handle_api_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/billing/overview")
def get_billing_overview(
    account: Optional[str] = None,
    billing_cycle: Optional[str] = Query(None)
):
    """获取账单概览"""
    # TODO: 从原api.py迁移完整实现（第3024行）
    return {
        "success": True,
        "data": {
            "total": 0,
            "by_product": {}
        }
    }


@router.get("/billing/instance-bill")
def get_instance_bill(
    account: Optional[str] = None,
    billing_cycle: Optional[str] = Query(None),
    product_code: Optional[str] = Query(None)
):
    """获取实例账单"""
    # TODO: 从原api.py迁移完整实现（第3089行）
    return {
        "success": True,
        "data": []
    }


@router.get("/billing/discounts")
def get_billing_discounts(account: Optional[str] = None):
    """获取账单折扣"""
    # TODO: 从原api.py迁移完整实现（第3348行）
    return {
        "success": True,
        "data": []
    }


@router.get("/billing/data-status")
def get_billing_data_status(account: Optional[str] = None):
    """
    获取账单数据完整性状态
    返回已有的账单月份、总记录数、数据覆盖范围等信息
    """
    try:
        from cloudlens.core.database import get_database_adapter
        from datetime import datetime, timedelta

        db = get_database_adapter()

        # 查询账单数据统计
        query = """
            SELECT
                COUNT(DISTINCT billing_cycle) as total_months,
                COUNT(*) as total_records,
                MIN(billing_cycle) as earliest_month,
                MAX(billing_cycle) as latest_month,
                SUM(payment_amount) as total_amount
            FROM bill_items
        """

        if account:
            query += f" WHERE account_id = '{account}'"

        result = db.query(query)

        if not result:
            return {
                "success": True,
                "data": {
                    "has_data": False,
                    "total_months": 0,
                    "total_records": 0,
                    "data_range": None,
                    "total_amount": 0,
                    "is_complete": False,
                    "missing_months": [],
                    "message": "暂无账单数据"
                }
            }

        stats = result[0]
        total_months = stats.get('total_months', 0)
        total_records = stats.get('total_records', 0)
        earliest_month = stats.get('earliest_month')
        latest_month = stats.get('latest_month')
        total_amount = float(stats.get('total_amount', 0))

        # 计算预期的月份数（从最早月份到最新月份应该有多少个月）
        expected_months = []
        missing_months = []
        is_complete = False

        if earliest_month and latest_month:
            # 查询所有已有的月份
            months_query = "SELECT DISTINCT billing_cycle FROM bill_items"
            if account:
                months_query += f" WHERE account_id = '{account}'"
            months_query += " ORDER BY billing_cycle"

            existing_months = [row['billing_cycle'] for row in db.query(months_query)]

            # 计算从earliest到latest之间的所有月份
            current = datetime.strptime(earliest_month, '%Y-%m')
            end = datetime.strptime(latest_month, '%Y-%m')

            while current <= end:
                month_str = current.strftime('%Y-%m')
                expected_months.append(month_str)
                if month_str not in existing_months:
                    missing_months.append(month_str)

                # 手动计算下一个月（避免使用dateutil）
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

            is_complete = len(missing_months) == 0

        return {
            "success": True,
            "data": {
                "has_data": total_records > 0,
                "total_months": total_months,
                "total_records": total_records,
                "data_range": {
                    "start": earliest_month,
                    "end": latest_month
                } if earliest_month else None,
                "total_amount": round(total_amount, 2),
                "is_complete": is_complete,
                "expected_months": len(expected_months),
                "missing_months": missing_months,
                "message": "数据完整" if is_complete else f"数据不完整，缺少{len(missing_months)}个月的数据"
            }
        }

    except Exception as e:
        logger.error(f"获取账单数据状态失败: {str(e)}")
        return handle_api_error(e, "获取账单数据状态失败")
