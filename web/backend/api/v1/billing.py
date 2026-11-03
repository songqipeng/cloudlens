#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单查询 API 模块
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from cloudlens.core.cache import CacheManager
from cloudlens.core.config import ConfigManager
from web.backend.api_base import handle_api_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _get_billing_cycle_default() -> str:
    return datetime.now().strftime("%Y-%m")


def _bss_query_bill_overview(account_config, billing_cycle: str) -> List[Dict[str, Any]]:
    """调用阿里云 BSS OpenAPI QueryBillOverview"""
    try:
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkcore.request import CommonRequest
    except Exception as e:
        raise RuntimeError(f"阿里云 SDK 不可用：{e}")

    import json

    client = AcsClient(
        account_config.access_key_id,
        account_config.access_key_secret,
        "cn-hangzhou",
    )
    request = CommonRequest()
    request.set_domain("business.aliyuncs.com")
    request.set_version("2017-12-14")
    request.set_action_name("QueryBillOverview")
    request.set_method("POST")
    request.add_query_param("BillingCycle", billing_cycle)

    resp = client.do_action_with_exception(request)
    data = json.loads(resp)
    data_node = (data.get("Data") or {})
    items_node = ((data_node.get("Items") or {}).get("Item")) or []
    if not isinstance(items_node, list):
        items_node = [items_node]
    return [i for i in items_node if isinstance(i, dict)]


@router.get("/billing/overview")
def get_billing_overview(
    account: Optional[str] = None,
    billing_cycle: Optional[str] = Query(None),
):
    """获取账单概览（委托成本模块的 BSS 聚合）"""
    try:
        from web.backend.api.v1.costs import _get_billing_overview_totals

        cm = ConfigManager()
        if not account:
            accounts = cm.list_accounts()
            if not accounts:
                raise HTTPException(status_code=404, detail="No accounts configured")
            account = accounts[0].name
        account_config = cm.get_account(account)
        if not account_config:
            raise HTTPException(status_code=404, detail=f"Account '{account}' not found")
        totals = _get_billing_overview_totals(account_config, billing_cycle)
        return {
            "success": True,
            "data": {
                "total": totals.get("total_pretax") or 0,
                "by_product": totals.get("by_product") or {},
                "billing_cycle": billing_cycle or _get_billing_cycle_default(),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "get_billing_overview")


@router.get("/billing/instance-bill")
def get_instance_bill(
    account: Optional[str] = None,
    billing_cycle: Optional[str] = Query(None),
    product_code: Optional[str] = Query(None),
):
    """获取实例账单（占位：请使用 /cost 相关接口）"""
    return {
        "success": True,
        "data": [],
        "message": "请使用 /api/cost 相关接口查看实例成本明细",
    }


@router.get("/billing/discounts")
def get_billing_discounts(
    account: Optional[str] = Query(None),
    billing_cycle: Optional[str] = Query(None, description="账期 yyyy-MM，默认当月"),
    force_refresh: bool = Query(False, description="强制刷新缓存"),
):
    """
    折扣梳理（按产品 + 计费方式聚合）- 基于 BSS API 实时查询。

    用于折扣页在本地无折扣明细时的产品列表兜底。
    """
    try:
        cm = ConfigManager()
        if not account:
            accounts = cm.list_accounts()
            if not accounts:
                raise HTTPException(status_code=404, detail="No accounts configured")
            account = accounts[0].name
        account_config = cm.get_account(account)
        if not account_config:
            raise HTTPException(status_code=404, detail=f"Account '{account}' not found")
        provider = getattr(account_config, "provider", None) or "aliyun"
        if provider != "aliyun":
            raise HTTPException(status_code=400, detail="当前仅支持阿里云账单（BSS OpenAPI）")

        if not billing_cycle:
            billing_cycle = _get_billing_cycle_default()

        cache_manager = CacheManager(ttl_seconds=86400)
        cache_key = f"billing_discounts_{billing_cycle}"
        if not force_refresh:
            cached = cache_manager.get(
                resource_type=cache_key, account_name=account_config.name
            )
            if isinstance(cached, dict) and cached.get("billing_cycle") == billing_cycle:
                return {"success": True, "data": cached, "cached": True}

        def f(x: Any) -> float:
            try:
                return float(x or 0)
            except Exception:
                return 0.0

        items = _bss_query_bill_overview(account_config, billing_cycle)

        agg: Dict[str, Dict[str, Any]] = {}
        for it in items:
            code = it.get("ProductCode") or it.get("PipCode") or "unknown"
            sub = it.get("SubscriptionType") or "Unknown"
            key = f"{code}::{sub}"
            if key not in agg:
                agg[key] = {
                    "product_code": code,
                    "product_name": it.get("ProductName") or code,
                    "subscription_type": sub,
                    "pretax_gross_amount": 0.0,
                    "pretax_amount": 0.0,
                    "payment_amount": 0.0,
                    "outstanding_amount": 0.0,
                    "invoice_discount": 0.0,
                    "round_down_discount": 0.0,
                    "deducted_by_coupons": 0.0,
                    "deducted_by_cash_coupons": 0.0,
                    "deducted_by_prepaid_card": 0.0,
                    "adjust_amount": 0.0,
                    "cash_amount": 0.0,
                    "currency": it.get("Currency") or "CNY",
                }

            row = agg[key]
            row["pretax_gross_amount"] += f(it.get("PretaxGrossAmount"))
            row["pretax_amount"] += f(it.get("PretaxAmount"))
            row["payment_amount"] += f(it.get("PaymentAmount"))
            row["outstanding_amount"] += f(it.get("OutstandingAmount"))
            row["invoice_discount"] += f(it.get("InvoiceDiscount"))
            row["round_down_discount"] += f(it.get("RoundDownDiscount"))
            row["deducted_by_coupons"] += f(it.get("DeductedByCoupons"))
            row["deducted_by_cash_coupons"] += f(it.get("DeductedByCashCoupons"))
            row["deducted_by_prepaid_card"] += f(it.get("DeductedByPrepaidCard"))
            row["adjust_amount"] += f(it.get("AdjustAmount"))
            row["cash_amount"] += f(it.get("CashAmount"))

        rows = []
        total_gross = 0.0
        total_pretax = 0.0
        total_discount_amount = 0.0
        for row in agg.values():
            gross = float(row.get("pretax_gross_amount") or 0.0)
            pretax = float(row.get("pretax_amount") or 0.0)
            payment_amount = float(row.get("payment_amount") or 0.0)
            outstanding_amount = float(row.get("outstanding_amount") or 0.0)
            invoice_discount = float(row.get("invoice_discount") or 0.0)
            round_down_discount = float(row.get("round_down_discount") or 0.0)
            deducted_by_coupons = float(row.get("deducted_by_coupons") or 0.0)
            deducted_by_cash_coupons = float(row.get("deducted_by_cash_coupons") or 0.0)
            deducted_by_prepaid_card = float(row.get("deducted_by_prepaid_card") or 0.0)
            adjust_amount = float(row.get("adjust_amount") or 0.0)
            cash_amount = float(row.get("cash_amount") or 0.0)

            has_any_amount = any(
                abs(x) > 0
                for x in (
                    gross,
                    pretax,
                    payment_amount,
                    outstanding_amount,
                    invoice_discount,
                    round_down_discount,
                    deducted_by_coupons,
                    deducted_by_cash_coupons,
                    deducted_by_prepaid_card,
                    adjust_amount,
                    cash_amount,
                )
            )
            if not has_any_amount:
                continue

            discount_amount = max(0.0, gross - pretax) if gross > 0 else 0.0
            discount_rate = (pretax / gross) if gross > 0 else None
            is_free = gross > 0 and pretax == 0
            discount_zhe = (
                float(discount_rate) * 10.0
                if (discount_rate is not None and pretax > 0)
                else None
            )
            row["pretax_gross_amount"] = round(gross, 2)
            row["pretax_amount"] = round(pretax, 2)
            row["discount_amount"] = round(discount_amount, 2)
            row["discount_rate"] = (
                round(float(discount_rate), 6) if discount_rate is not None else None
            )
            row["discount_pct"] = (
                round((1.0 - float(discount_rate)) * 100, 2)
                if discount_rate is not None
                else None
            )
            row["discount_zhe"] = (
                round(float(discount_zhe), 1) if discount_zhe is not None else None
            )
            row["free"] = bool(is_free)
            row["payment_amount"] = round(payment_amount, 2)
            row["outstanding_amount"] = round(outstanding_amount, 2)
            row["invoice_discount"] = round(invoice_discount, 2)
            row["round_down_discount"] = round(round_down_discount, 6)
            row["deducted_by_coupons"] = round(deducted_by_coupons, 2)
            row["deducted_by_cash_coupons"] = round(deducted_by_cash_coupons, 2)
            row["deducted_by_prepaid_card"] = round(deducted_by_prepaid_card, 2)
            row["adjust_amount"] = round(adjust_amount, 2)
            row["cash_amount"] = round(cash_amount, 2)

            total_gross += gross
            total_pretax += pretax
            total_discount_amount += discount_amount
            rows.append(row)

        rows.sort(key=lambda r: float(r.get("discount_amount") or 0.0), reverse=True)

        overall_rate = (total_pretax / total_gross) if total_gross > 0 else None
        overall_free = total_gross > 0 and total_pretax == 0
        overall_zhe = (
            float(overall_rate) * 10.0
            if (overall_rate is not None and total_pretax > 0)
            else None
        )
        result = {
            "billing_cycle": billing_cycle,
            "summary": {
                "total_pretax_gross_amount": round(total_gross, 2),
                "total_pretax_amount": round(total_pretax, 2),
                "total_discount_amount": round(total_discount_amount, 2),
                "discount_rate": (
                    round(float(overall_rate), 6) if overall_rate is not None else None
                ),
                "discount_pct": (
                    round((1.0 - float(overall_rate)) * 100, 2)
                    if overall_rate is not None
                    else None
                ),
                "discount_zhe": (
                    round(float(overall_zhe), 1) if overall_zhe is not None else None
                ),
                "free": bool(overall_free),
            },
            "rows": rows,
        }

        cache_manager.set(
            resource_type=cache_key, account_name=account_config.name, data=result
        )
        return {"success": True, "data": result, "cached": False}
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "get_billing_discounts")
