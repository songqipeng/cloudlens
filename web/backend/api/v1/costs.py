#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成本分析API

提供以下功能：
- 成本概览 (MoM/YoY对比)
- 成本构成分析
- 预算管理
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

from cloudlens.core.config import ConfigManager, CloudAccount
from cloudlens.core.context import ContextManager
from cloudlens.core.cache import CacheManager
from cloudlens.core.database import DatabaseFactory

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api")


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

    from cloudlens.cli.utils import get_provider
    return get_provider(account_config), account


def _get_billing_cycle_default() -> str:
    """获取默认账期（当前月份）"""
    return datetime.now().strftime("%Y-%m")


def _get_billing_overview_from_db(
    account_config: CloudAccount,
    billing_cycle: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    从本地账单数据库读取成本概览（优先使用，速度快）

    Args:
        account_config: 账号配置对象
        billing_cycle: 账期，格式 YYYY-MM，默认当前月

    Returns:
        成本概览数据，如果数据库不存在或读取失败则返回 None
    """
    try:
        if billing_cycle is None:
            billing_cycle = datetime.now().strftime("%Y-%m")

        db = DatabaseFactory.create_adapter("mysql")

        # 构造正确的 account_id 格式：{access_key_id[:10]}-{account_name}
        account_id = f"{account_config.access_key_id[:10]}-{account_config.name}"

        # 验证 account_id 是否存在（精确匹配）
        account_result = db.query_one("""
            SELECT DISTINCT account_id
            FROM bill_items
            WHERE account_id = %s
            LIMIT 1
        """, (account_id,))

        if not account_result:
            # 尝试模糊匹配（兼容旧数据）
            logger.warning(f"精确匹配失败，尝试模糊匹配: {account_id}")
            account_result = db.query_one("""
                SELECT DISTINCT account_id
                FROM bill_items
                WHERE account_id LIKE %s
                LIMIT 1
            """, (f"%{account_config.name}%",))

            if not account_result:
                logger.warning(f"未找到账号 '{account_config.name}' 的账单数据")
                return None

            # 处理字典格式的结果（MySQL）
            if isinstance(account_result, dict):
                matched_account_id = account_result.get('account_id')
            else:
                matched_account_id = account_result[0] if account_result else None

            if matched_account_id and matched_account_id != account_id:
                logger.warning(f"使用模糊匹配的 account_id: {matched_account_id}")
                account_id = matched_account_id

        # 按产品聚合当月成本
        product_results = db.query("""
            SELECT
                product_name,
                product_code,
                subscription_type,
                SUM(pretax_amount) as total_pretax
            FROM bill_items
            WHERE account_id = %s
                AND billing_cycle = %s
                AND pretax_amount IS NOT NULL
            GROUP BY product_name, product_code, subscription_type
        """, (account_id, billing_cycle))

        by_product: Dict[str, float] = {}
        by_product_name: Dict[str, str] = {}
        by_product_subscription: Dict[str, Dict[str, float]] = {}
        total = 0.0

        for row in product_results:
            # 处理字典格式的结果（MySQL）
            if isinstance(row, dict):
                product_name = row.get('product_name') or "unknown"
                product_code = row.get('product_code') or "unknown"
                subscription_type = row.get('subscription_type') or "Unknown"
                pretax = float(row.get('total_pretax') or 0)
            else:
                product_name = row[0] or "unknown"
                product_code = row[1] or "unknown"
                subscription_type = row[2] or "Unknown"
                pretax = float(row[3] or 0)

            if pretax <= 0:
                continue

            if product_code not in by_product_name:
                by_product_name[product_code] = product_name

            by_product[product_code] = by_product.get(product_code, 0.0) + pretax
            by_product_subscription.setdefault(product_code, {})
            by_product_subscription[product_code][subscription_type] = (
                by_product_subscription[product_code].get(subscription_type, 0.0) + pretax
            )

            total += pretax

        # 检查是否有任何记录
        if len(by_product) == 0:
            logger.info(f"数据库中没有账期 {billing_cycle} 的数据，将使用API查询")
            return None

        return {
            "billing_cycle": billing_cycle,
            "total_pretax": round(total, 2),
            "by_product": {k: round(v, 2) for k, v in by_product.items()},
            "by_product_name": by_product_name,
            "by_product_subscription": {
                code: {k: round(v, 2) for k, v in sub.items()}
                for code, sub in by_product_subscription.items()
            },
            "data_source": "local_db"
        }

    except Exception as e:
        logger.error(f"从本地数据库读取账单概览失败: {str(e)}")
        return None


def _bss_query_instance_bill(
    account_config: CloudAccount,
    billing_cycle: str,
    product_code: str,
    subscription_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    调用阿里云 BSS OpenAPI QueryInstanceBill，返回原始条目列表
    """
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

    items: List[Dict[str, Any]] = []
    page_num = 1
    page_size = 100

    while True:
        request = CommonRequest()
        request.set_domain("business.aliyuncs.com")
        request.set_version("2017-12-14")
        request.set_action_name("QueryInstanceBill")
        request.set_method("POST")

        request.add_query_param("BillingCycle", billing_cycle)
        request.add_query_param("ProductCode", product_code)
        if subscription_type:
            request.add_query_param("SubscriptionType", subscription_type)
        request.add_query_param("PageNum", page_num)
        request.add_query_param("PageSize", page_size)

        resp = client.do_action_with_exception(request)
        data = json.loads(resp)

        # 兼容不同返回结构
        data_node = data.get("Data") or {}
        items_node = (data_node.get("Items") or {}).get("Item")
        if items_node is None:
            items_node = data_node.get("Item")
        if items_node is None:
            items_node = []
        if not isinstance(items_node, list):
            items_node = [items_node]

        items.extend([i for i in items_node if isinstance(i, dict)])

        total_count = int(data.get("TotalCount") or data_node.get("TotalCount") or 0)
        if total_count and len(items) >= total_count:
            break
        if len(items_node) < page_size:
            break
        page_num += 1

    return items


def _bss_query_bill_overview(
    account_config: CloudAccount,
    billing_cycle: str
) -> List[Dict[str, Any]]:
    """
    调用阿里云 BSS OpenAPI QueryBillOverview，返回 Item 列表
    """
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


def _get_billing_overview_totals(
    account_config: CloudAccount,
    billing_cycle: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    从账单概览计算总额和分类

    返回：
    - total_pretax: 按产品聚合后的总额（使用 PretaxAmount）
    - by_product: {product_code: pretax_amount_sum}
    """
    if billing_cycle is None:
        billing_cycle = _get_billing_cycle_default()

    cache_key = f"billing_overview_totals_{billing_cycle}"
    cache_manager = CacheManager(ttl_seconds=86400)

    # 检查缓存
    if not force_refresh:
        cached = cache_manager.get(
            resource_type=cache_key,
            account_name=account_config.name
        )
        if cached and isinstance(cached, list) and len(cached) > 0:
            cached_dict = cached[0] if isinstance(cached[0], dict) else None
            if cached_dict and "total_pretax" in cached_dict:
                return cached_dict

    # 优先从本地数据库读取
    if not force_refresh:
        db_result = _get_billing_overview_from_db(account_config, billing_cycle)
        if db_result is not None:
            logger.info(
                f"✅ 从本地数据库读取账单概览: {account_config.name}, "
                f"{billing_cycle}, 总成本={db_result.get('total_pretax', 0)}"
            )
            cache_manager.set(
                resource_type=cache_key,
                account_name=account_config.name,
                data=[db_result]
            )
            return db_result
        logger.info(f"📡 数据库中没有账期 {billing_cycle} 的数据，通过API查询")

    # 从API查询
    logger.info(f"正在通过BSS API查询账单概览: {account_config.name}, {billing_cycle}")
    try:
        items = _bss_query_bill_overview(account_config, billing_cycle)
        if not items:
            logger.warning(f"⚠️  API查询返回空数据: {account_config.name}, {billing_cycle}")
    except Exception as e:
        logger.error(f"❌ BSS API查询失败: {account_config.name}, {billing_cycle}")
        raise

    by_product: Dict[str, float] = {}
    by_product_name: Dict[str, str] = {}
    by_product_subscription: Dict[str, Dict[str, float]] = {}
    total = 0.0

    for it in items:
        product_code = (it.get("ProductCode") or it.get("PipCode") or "unknown")
        product_name = it.get("ProductName") or ""
        subscription_type = it.get("SubscriptionType") or "Unknown"

        pretax = it.get("PretaxAmount")
        try:
            pretax_f = float(pretax) if pretax is not None else 0.0
        except Exception:
            pretax_f = 0.0
        if pretax_f == 0:
            continue

        if product_code not in by_product_name and product_name:
            by_product_name[product_code] = str(product_name)

        by_product[product_code] = float(
            by_product.get(product_code, 0.0) + pretax_f
        )
        by_product_subscription.setdefault(product_code, {})
        by_product_subscription[product_code][subscription_type] = float(
            by_product_subscription[product_code].get(subscription_type, 0.0) +
            pretax_f
        )

        total += pretax_f

    result = {
        "billing_cycle": billing_cycle,
        "total_pretax": round(float(total), 2),
        "by_product": {k: round(float(v), 2) for k, v in by_product.items()},
        "by_product_name": by_product_name,
        "by_product_subscription": {
            code: {k: round(float(v), 2) for k, v in sub.items()}
            for code, sub in by_product_subscription.items()
        },
        "data_source": "bss_api",
    }

    if total == 0:
        logger.warning(f"⚠️  API查询账期 {billing_cycle} 的总成本为0")

    cache_manager.set(
        resource_type=cache_key,
        account_name=account_config.name,
        data=[result]
    )
    logger.info(f"✅ 通过API获取账单概览成功: {account_config.name}, {billing_cycle}")
    return result


# ==================== 成本分析端点 ====================

@router.get("/cost/overview")
def get_cost_overview(
    account: Optional[str] = None,
    force_refresh: bool = Query(False, description="强制刷新缓存")
):
    """获取成本概览（优先账单口径，带24小时缓存）"""
    provider, account_name = _get_provider_for_account(account)

    # 初始化缓存管理器，TTL设置为24小时
    cache_manager = CacheManager(ttl_seconds=86400)

    # 尝试从缓存获取数据
    if not force_refresh:
        cached_result = cache_manager.get(
            resource_type="cost_overview",
            account_name=account_name
        )
        if cached_result is not None:
            return {
                "success": True,
                "data": cached_result,
                "cached": True,
            }

    # 计算新数据
    cm = ConfigManager()
    account_config = cm.get_account(account_name)

    try:
        now = datetime.now()
        current_cycle = now.strftime("%Y-%m")

        # 计算上月账期
        first_day_this_month = now.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        last_cycle = last_day_last_month.strftime("%Y-%m")

        logger.info(
            f"📊 成本概览查询: 账号={account_name}, "
            f"当前账期={current_cycle}, 上月账期={last_cycle}"
        )

        # 获取当月数据
        current_totals = _get_billing_overview_totals(
            account_config,
            billing_cycle=current_cycle,
            force_refresh=False
        ) if account_config else None

        # 获取上月数据
        last_totals = None
        if account_config:
            last_totals = _get_billing_overview_totals(
                account_config,
                billing_cycle=last_cycle,
                force_refresh=False
            )
            # 如果数据库没有数据，强制通过API获取
            if last_totals is None or (
                last_totals.get("total_pretax", 0) == 0 and
                last_totals.get("data_source") == "local_db"
            ):
                logger.info(f"🔄 上月数据不可用，强制通过API获取: {last_cycle}")
                try:
                    last_totals = _get_billing_overview_totals(
                        account_config,
                        billing_cycle=last_cycle,
                        force_refresh=True
                    )
                except Exception as e:
                    logger.error(f"❌ 强制刷新上月数据失败: {str(e)}")
                    last_totals = None

        # 计算本月已过天数（用于环比对比）
        current_day = now.day
        first_day_this_month = now.replace(day=1)
        
        # 本月成本：1月1日到1月6日（如果今天是6号）
        current_month_start = first_day_this_month
        current_month_end = now
        
        # 上月相同天数：12月1日到12月6日
        last_month_end = first_day_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        last_month_comparable_end = last_month_start + timedelta(days=current_day - 1)
        if last_month_comparable_end > last_month_end:
            last_month_comparable_end = last_month_end
        
        # 使用成本趋势分析器获取指定日期范围的成本（更准确）
        from cloudlens.core.cost_trend_analyzer import CostTrendAnalyzer
        analyzer = CostTrendAnalyzer()
        
        # 获取本月成本（从1月1日到今天）
        current_month_cost = 0.0
        try:
            current_cost_data = analyzer.get_real_cost_from_bills(
                account_name=account_name,
                start_date=current_month_start.strftime("%Y-%m-%d"),
                end_date=current_month_end.strftime("%Y-%m-%d")
            )
            if current_cost_data and "error" not in current_cost_data:
                if "chart_data" in current_cost_data and "costs" in current_cost_data["chart_data"]:
                    costs = current_cost_data["chart_data"]["costs"]
                    if isinstance(costs, list) and len(costs) > 0:
                        current_month_cost = float(sum(costs))
                        logger.info(f"✅ 本月成本（从chart_data计算）: {current_month_cost}")
                    else:
                        current_totals = _get_billing_overview_totals(account_config, billing_cycle=current_cycle, force_refresh=False) if account_config else None
                        current_month_cost = float((current_totals or {}).get("total_pretax") or 0.0)
                elif "total_cost" in current_cost_data:
                    current_month_cost = float(current_cost_data.get("total_cost", 0.0))
                else:
                    current_totals = _get_billing_overview_totals(account_config, billing_cycle=current_cycle, force_refresh=False) if account_config else None
                    current_month_cost = float((current_totals or {}).get("total_pretax") or 0.0)
            else:
                current_totals = _get_billing_overview_totals(account_config, billing_cycle=current_cycle, force_refresh=False) if account_config else None
                current_month_cost = float((current_totals or {}).get("total_pretax") or 0.0)
        except Exception as e:
            logger.warning(f"⚠️  获取本月成本失败，回退到账单概览API: {str(e)}")
            current_totals = _get_billing_overview_totals(account_config, billing_cycle=current_cycle, force_refresh=False) if account_config else None
            current_month_cost = float((current_totals or {}).get("total_pretax") or 0.0)
        
        # 获取上月相同天数的成本
        last_month_cost = 0.0
        try:
            last_cost_data = analyzer.get_real_cost_from_bills(
                account_name=account_name,
                start_date=last_month_start.strftime("%Y-%m-%d"),
                end_date=last_month_comparable_end.strftime("%Y-%m-%d")
            )
            if last_cost_data and "error" not in last_cost_data:
                if "chart_data" in last_cost_data and "costs" in last_cost_data["chart_data"]:
                    costs = last_cost_data["chart_data"]["costs"]
                    if isinstance(costs, list) and len(costs) > 0:
                        last_month_cost = float(sum(costs))
                        logger.info(f"✅ 上月成本（从chart_data计算）: {last_month_cost}")
                    else:
                        last_totals = _get_billing_overview_totals(account_config, billing_cycle=last_cycle, force_refresh=False) if account_config else None
                        if last_totals:
                            last_month_total = float(last_totals.get("total_pretax") or 0.0)
                            last_month_days = last_month_end.day
                            last_month_cost = last_month_total * (current_day / last_month_days) if last_month_days > 0 else 0.0
                elif "total_cost" in last_cost_data:
                    last_month_cost = float(last_cost_data.get("total_cost", 0.0))
                else:
                    last_totals = _get_billing_overview_totals(account_config, billing_cycle=last_cycle, force_refresh=False) if account_config else None
                    if last_totals:
                        last_month_total = float(last_totals.get("total_pretax") or 0.0)
                        last_month_days = last_month_end.day
                        last_month_cost = last_month_total * (current_day / last_month_days) if last_month_days > 0 else 0.0
            else:
                last_totals = _get_billing_overview_totals(account_config, billing_cycle=last_cycle, force_refresh=False) if account_config else None
                if last_totals:
                    last_month_total = float(last_totals.get("total_pretax") or 0.0)
                    last_month_days = last_month_end.day
                    last_month_cost = last_month_total * (current_day / last_month_days) if last_month_days > 0 else 0.0
        except Exception as e:
            logger.warning(f"⚠️  获取上月成本失败，回退到账单概览API（按比例计算）: {str(e)}")
            last_totals = _get_billing_overview_totals(account_config, billing_cycle=last_cycle, force_refresh=False) if account_config else None
            if last_totals:
                last_month_total = float(last_totals.get("total_pretax") or 0.0)
                last_month_days = last_month_end.day
                last_month_cost = last_month_total * (current_day / last_month_days) if last_month_days > 0 else 0.0

        logger.info(
            f"💰 成本数据: 本月（{current_day}天）={current_month_cost}, 上月（{current_day}天）={last_month_cost}"
        )

        mom = (
            (current_month_cost - last_month_cost) / last_month_cost * 100
            if last_month_cost > 0 else 0.0
        )
        
        # 计算同比（去年同期相同天数：2025年1月1日-1月6日 vs 2026年1月1日-1月6日）
        yoy = 0.0
        last_year_cost = 0.0
        try:
            # 去年同期范围
            last_year_start = datetime(now.year - 1, now.month, 1)
            last_year_end = datetime(now.year - 1, now.month, current_day)
            
            logger.info(f"📊 计算同比: 去年同期范围 {last_year_start.strftime('%Y-%m-%d')} 至 {last_year_end.strftime('%Y-%m-%d')}")
            
            last_year_cost_data = analyzer.get_real_cost_from_bills(
                account_name=account_name,
                start_date=last_year_start.strftime("%Y-%m-%d"),
                end_date=last_year_end.strftime("%Y-%m-%d")
            )
            if last_year_cost_data and "error" not in last_year_cost_data:
                if "chart_data" in last_year_cost_data and "costs" in last_year_cost_data["chart_data"]:
                    costs = last_year_cost_data["chart_data"]["costs"]
                    if isinstance(costs, list) and len(costs) > 0:
                        last_year_cost = float(sum(costs))
                        logger.info(f"✅ 去年同期成本（从chart_data计算）: {last_year_cost}")
                    else:
                        # 如果数据库查询失败，尝试从账单概览API获取（按比例计算）
                        last_year_cycle = last_year_start.strftime("%Y-%m")
                        last_year_totals = _get_billing_overview_totals(account_config, billing_cycle=last_year_cycle, force_refresh=False) if account_config else None
                        if last_year_totals:
                            last_year_total = float(last_year_totals.get("total_pretax") or 0.0)
                            # 按比例计算：去年同期总成本 * (已过天数 / 该月总天数)
                            last_year_month_days = (datetime(last_year_start.year, last_year_start.month + 1, 1) - timedelta(days=1)).day if last_year_start.month < 12 else 31
                            last_year_cost = last_year_total * (current_day / last_year_month_days) if last_year_month_days > 0 else 0.0
                            logger.info(f"   去年同期总成本={last_year_total}, 总天数={last_year_month_days}, 已过天数={current_day}, 按比例计算={last_year_cost}")
                elif "total_cost" in last_year_cost_data:
                    last_year_cost = float(last_year_cost_data.get("total_cost", 0.0))
                else:
                    # 回退到账单概览API（按比例计算）
                    last_year_cycle = last_year_start.strftime("%Y-%m")
                    last_year_totals = _get_billing_overview_totals(account_config, billing_cycle=last_year_cycle, force_refresh=False) if account_config else None
                    if last_year_totals:
                        last_year_total = float(last_year_totals.get("total_pretax") or 0.0)
                        last_year_month_days = (datetime(last_year_start.year, last_year_start.month + 1, 1) - timedelta(days=1)).day if last_year_start.month < 12 else 31
                        last_year_cost = last_year_total * (current_day / last_year_month_days) if last_year_month_days > 0 else 0.0
        except Exception as e:
            logger.warning(f"⚠️  获取去年同期成本失败: {str(e)}")
            # 尝试从账单概览API获取（按比例计算）
            try:
                last_year_cycle = datetime(now.year - 1, now.month, 1).strftime("%Y-%m")
                last_year_totals = _get_billing_overview_totals(account_config, billing_cycle=last_year_cycle, force_refresh=False) if account_config else None
                if last_year_totals:
                    last_year_total = float(last_year_totals.get("total_pretax") or 0.0)
                    last_year_month_days = (datetime(now.year - 1, now.month + 1, 1) - timedelta(days=1)).day if now.month < 12 else 31
                    last_year_cost = last_year_total * (current_day / last_year_month_days) if last_year_month_days > 0 else 0.0
            except:
                last_year_cost = 0.0
        
        # 计算同比
        yoy = (
            (current_month_cost - last_year_cost) / last_year_cost * 100
            if last_year_cost > 0 else 0.0
        )
        
        logger.info(f"📊 同比数据: 今年（{current_day}天）={current_month_cost}, 去年（{current_day}天）={last_year_cost}, 同比={yoy:.2f}%")

        result_data = {
            "current_month": round(current_month_cost, 2),
            "last_month": round(last_month_cost, 2),
            "yoy": round(yoy, 2),
            "mom": round(mom, 2),
            "current_cycle": current_cycle,
            "last_cycle": last_cycle,
            "current_days": current_day,
            "comparable_days": current_day,
        }

        # 保存到缓存
        cache_manager.set(
            resource_type="cost_overview",
            account_name=account_name,
            data=result_data
        )

        return {
            "success": True,
            "data": result_data,
            "cached": False,
        }
    except Exception as e:
        logger.error(f"❌ 获取成本概览失败: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": {
                "current_month": 0,
                "last_month": 0,
                "yoy": 0,
                "mom": 0,
            },
            "cached": False,
        }


@router.get("/cost/attribution")
def get_cost_attribution(
    account: Optional[str] = None,
    current_cycle: Optional[str] = Query(None, description="当前账期 YYYY-MM，默认上一个自然月"),
    compare_cycle: Optional[str] = Query(None, description="对比账期 YYYY-MM"),
    compare_type: str = Query("mom", description="对比类型：mom / yoy / custom"),
):
    """对比两个账期的账单，拆解成本变化原因。

    只读本地 bill_items，不调用云厂商写接口。多云账单只要落入同一张表即可复用。
    """
    _, account_name = _get_provider_for_account(account)
    cm = ConfigManager()
    account_config = cm.get_account(account_name)
    access_key_id = account_config.access_key_id if account_config else None

    try:
        from cloudlens.core.cost_attribution import CostAttributionEngine

        engine = CostAttributionEngine()
        report = engine.analyze(
            account_name=account_name,
            current_cycle=current_cycle,
            compare_cycle=compare_cycle,
            compare_type=compare_type,
            access_key_id=access_key_id,
        )
        return {
            "success": True,
            "data": report,
        }
    except ValueError as e:
        logger.error("成本归因参数错误: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("成本归因分析失败")
        raise HTTPException(status_code=500, detail=f"成本归因分析失败: {e}")


@router.get("/cost/breakdown")
def get_cost_breakdown(
    account: Optional[str] = None,
    force_refresh: bool = Query(False, description="强制刷新缓存"),
    billing_cycle: Optional[str] = Query(None, description="账期 yyyy-MM，默认当月"),
):
    """获取成本构成（优先账单口径，带24小时缓存）"""
    provider, account_name = _get_provider_for_account(account)

    # 初始化缓存管理器
    cache_manager = CacheManager(ttl_seconds=86400)

    # 尝试从缓存获取数据
    if not force_refresh:
        cached_result = cache_manager.get(
            resource_type="cost_breakdown",
            account_name=account_name
        )
        if cached_result is not None:
            return {
                "success": True,
                "data": cached_result,
                "cached": True,
            }

    # 计算新数据
    cm = ConfigManager()
    account_config = cm.get_account(account_name)

    try:
        totals = _get_billing_overview_totals(
            account_config,
            billing_cycle=billing_cycle
        ) if account_config else None

        by_product = (totals or {}).get("by_product") or {}
        total = float((totals or {}).get("total_pretax") or 0.0)
        by_product_name = (totals or {}).get("by_product_name") or {}
        by_product_subscription = (totals or {}).get("by_product_subscription") or {}

        # 构建分类列表
        categories = []
        for code, amount in by_product.items():
            try:
                amount_f = float(amount or 0.0)
            except Exception:
                amount_f = 0.0
            if amount_f <= 0:
                continue
            categories.append({
                "code": code,
                "name": by_product_name.get(code) or code,
                "amount": round(amount_f, 2),
                "subscription": by_product_subscription.get(code) or {},
            })
        categories.sort(key=lambda x: float(x.get("amount") or 0.0), reverse=True)

        result_data = {
            "by_type": by_product,
            "total": round(float(total), 2),
            "billing_cycle": (totals or {}).get("billing_cycle") or billing_cycle,
            "source": "billing_overview",
            "categories": categories,
            "by_product_name": by_product_name,
        }

        # 保存到缓存
        cache_manager.set(
            resource_type="cost_breakdown",
            account_name=account_name,
            data=result_data
        )

        return {
            "success": True,
            "data": result_data,
            "cached": False,
        }
    except Exception as e:
        logger.error(f"获取成本构成失败: {str(e)}")
        return {
            "success": True,
            "data": {
                "by_type": {},
                "total": 0,
            },
            "cached": False,
        }


@router.get("/cost/budget")
def get_budget(account: Optional[str] = None):
    """获取预算信息"""
    from cloudlens.core.budget_manager import BudgetStorage
    from cloudlens.core.bill_storage import BillStorageManager
    
    provider, account_name = _get_provider_for_account(account)
    cm = ConfigManager()
    account_config = cm.get_account(account_name)
    
    # 构造正确的 account_id 格式：{access_key_id[:10]}-{account_name}
    account_id = f"{account_config.access_key_id[:10]}-{account_config.name}"
    
    storage = BudgetStorage()
    budgets = storage.list_budgets(account_id=account_id)
    
    bill_storage = BillStorageManager()
    
    results = []
    total_monthly_budget = 0.0
    total_spent = 0.0
    
    for b in budgets:
        status = storage.calculate_budget_status(b, account_id, bill_storage)
        results.append({
            "budget": b.to_dict(),
            "status": status.to_dict()
        })
        if b.period == "monthly":
            total_monthly_budget += b.amount
            total_spent += status.spent

    return {
        "success": True,
        "data": {
            "budgets": results,
            "monthly_budget": round(total_monthly_budget, 2),
            "current_month_spent": round(total_spent, 2),
            "usage_rate": round((total_spent / total_monthly_budget * 100) if total_monthly_budget > 0 else 0, 2),
        }
    }


@router.post("/cost/budget")
def set_budget(budget_data: Dict[str, Any], account: Optional[str] = None):
    """设置或更新预算"""
    from cloudlens.core.budget_manager import BudgetStorage, Budget, AlertThreshold
    from datetime import datetime
    
    provider, account_name = _get_provider_for_account(account)
    cm = ConfigManager()
    account_config = cm.get_account(account_name)
    account_id = f"{account_config.access_key_id[:10]}-{account_config.name}"
    
    storage = BudgetStorage()
    
    # 简单的默认逻辑：如果是设置总预算
    name = budget_data.get("name", "Default Monthly Budget")
    amount = float(budget_data.get("amount", 0))
    period = budget_data.get("period", "monthly")
    
    # 构建预算对象
    now = datetime.now()
    if period == "monthly":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            end_date = datetime(now.year + 1, 1, 1)
        else:
            end_date = datetime(now.year, now.month + 1, 1)
    else:
        # 简化处理
        start_date = now
        end_date = now + timedelta(days=30)

    # 检查是否已存在同名预算以决定是更新还是创建
    existing = storage.list_budgets(account_id=account_id)
    target_budget = None
    for b in existing:
        if b.name == name:
            target_budget = b
            break
            
    if target_budget:
        target_budget.amount = amount
        target_budget.period = period
        target_budget.start_date = start_date
        target_budget.end_date = end_date
        storage.update_budget(target_budget)
    else:
        new_budget = Budget(
            id=str(uuid.uuid4()),
            name=name,
            amount=amount,
            period=period,
            type="total",
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            alerts=[
                AlertThreshold(percentage=80),
                AlertThreshold(percentage=100)
            ]
        )
        storage.create_budget(new_budget)
    
    return {
        "success": True,
        "message": "预算设置成功"
    }
