
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Optional, Any
from core.config import ConfigManager, CloudAccount
from core.context import ContextManager
from core.cost_trend_analyzer import CostTrendAnalyzer
from core.cache import CacheManager as ResourceCacheManager
from core.cache import CacheManager  # For idle_result and other caches
from core.rules_manager import RulesManager
from core.services.analysis_service import AnalysisService
from pydantic import BaseModel

router = APIRouter(prefix="/api")

class AccountInfo(BaseModel):
    name: str
    region: str
    access_key_id: str

class DashboardSummary(BaseModel):
    account: str
    total_cost: float
    idle_count: int
    cost_trend: str
    trend_pct: float

class TriggerAnalysisRequest(BaseModel):
    account: str
    days: int = 7
    force: bool = True

@router.get("/accounts")
def list_accounts() -> List[Dict]:
    """List all configured accounts"""
    cm = ConfigManager()
    accounts = cm.list_accounts()
    result = []
    for account in accounts:
        if isinstance(account, CloudAccount):
            result.append({
                "name": account.name,
                "region": account.region,
                "access_key_id": account.access_key_id,
            })
    return result

@router.get("/config/rules")
def get_rules() -> Dict[str, Any]:
    """Get current optimization rules"""
    rm = RulesManager()
    return rm.get_rules()

@router.post("/config/rules")
def set_rules(rules: Dict[str, Any]):
    """Update optimization rules"""
    rm = RulesManager()
    try:
        rm.set_rules(rules)
        return {"status": "success", "message": "Rules updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/trigger")
def trigger_analysis(req: TriggerAnalysisRequest, background_tasks: BackgroundTasks):
    """Trigger idle resource analysis"""
    # For MVP, we run it synchronously to provide immediate feedback, 
    # but in production this should be a background task. 
    # To avoid timeout for long requests, we could use background_tasks.
    # But for now, let's try synchronous for simplicity as user requested "Scan Now" button.
    # Actually, user might wait 10-20s.
    try:
        data, cached = AnalysisService.analyze_idle_resources(req.account, req.days, req.force)
        return {
            "status": "success", 
            "count": len(data), 
            "cached": cached,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/summary")
def get_summary(account: Optional[str] = None, force_refresh: bool = Query(False, description="强制刷新缓存")):
    """Get dashboard summary metrics（带24小时缓存）"""
    import logging
    logger = logging.getLogger(__name__)
    
    cm = ConfigManager()
    
    # Resolve account - 必须明确指定账号，不允许自动选择
    if not account:
        raise HTTPException(status_code=400, detail="账号参数是必需的，请在前端选择账号")
    
    # 调试日志
    logger.info(f"[get_summary] 收到账号参数: {account}, force_refresh: {force_refresh}")
    print(f"[DEBUG get_summary] 收到账号参数: {account}, force_refresh: {force_refresh}")
    print(f"[DEBUG get_summary] 收到账号参数: {account}, force_refresh: {force_refresh}")

    # 初始化缓存管理器，TTL设置为24小时（86400秒）
    cache_manager = ResourceCacheManager(ttl_seconds=86400)
    
    # 尝试从缓存获取数据
    cached_result = None
    if not force_refresh:
        cached_result = cache_manager.get(resource_type="dashboard_summary", account_name=account)
        if cached_result:
            print(f"[DEBUG get_summary] 使用缓存数据，账号: {account}")
    
    # 如果缓存有效，直接使用缓存数据
    if cached_result is not None:
        return {
            **cached_result,
            "cached": True,
        }

    print(f"[DEBUG get_summary] 缓存未命中，重新计算，账号: {account}")
    account_config = cm.get_account(account)
    if not account_config:
        print(f"[DEBUG get_summary] 账号 '{account}' 未找到")
        raise HTTPException(status_code=404, detail=f"Account '{account}' not found")
    
    print(f"[DEBUG get_summary] 使用账号配置: {account_config.name}, region: {account_config.region}, AK: {account_config.access_key_id[:8]}...")

    # 账单全量口径：优先用当月 BillOverview 的 PretaxAmount 汇总作为 total_cost
    billing_total_cost = None
    try:
        billing_total_cost = float(_get_billing_overview_totals(account_config).get("total_pretax") or 0.0)
        if billing_total_cost <= 0:
            billing_total_cost = None
    except Exception:
        billing_total_cost = None

    # Get Cost Data
    analyzer = CostTrendAnalyzer()
    try:
        history, analysis = analyzer.get_cost_trend(account, days=30)
        # 当历史数据不足时，analysis 会包含 error；不要把 total_cost 误置为 0（会影响汇总与节省潜力）
        if isinstance(analysis, dict) and "error" in analysis:
            total_cost = None
            trend = "N/A"
            trend_pct = 0.0
        else:
            total_cost = analysis.get("latest_cost", 0.0)
            trend = analysis.get("trend", "Unknown")
            trend_pct = analysis.get("total_change_pct", 0.0)
    except Exception:
        total_cost = None
        trend = "N/A"
        trend_pct = 0.0

    # Get Idle Data
    cache = CacheManager(ttl_seconds=86400)
    idle_data = cache.get("idle_result", account)
    idle_count = len(idle_data) if idle_data else 0

    # Get Resource Statistics (Task 1.1)
    try:
        from cli.utils import get_provider
        provider = get_provider(account_config)
        instances = provider.list_instances()
        rds_list = provider.list_rds()
        redis_list = provider.list_redis()
        
        resource_breakdown = {
            "ecs": len(instances),
            "rds": len(rds_list),
            "redis": len(redis_list),
        }
        total_resources = sum(resource_breakdown.values())
        
        # Tag Coverage
        tagged_count = sum(1 for inst in instances if hasattr(inst, 'tags') and inst.tags)
        tag_coverage = (tagged_count / len(instances) * 100) if instances else 0
        
        # Alert Count (simplified - TODO: implement actual alert system)
        alert_count = 0
        
        # Savings Potential: Calculate based on actual cost of idle resources
        savings_potential = 0.0
        if idle_data and account_config:
            # Get cost map for ECS resources (idle_data typically contains ECS instances)
            cost_map = _get_cost_map("ecs", account_config)
            
            # Calculate total cost of idle resources
            for idle_item in idle_data:
                instance_id = idle_item.get("instance_id") or idle_item.get("id")
                if instance_id:
                    # Try to get real cost from cost_map
                    cost = cost_map.get(instance_id)
                    if cost is None:
                        # If not found, try to estimate from resource spec
                        spec = idle_item.get("spec", "")
                        if spec:
                            cost = _estimate_monthly_cost_from_spec(spec, "ecs")
                        else:
                            # Default fallback estimate
                            cost = 300  # Average ECS cost
                    savings_potential += cost
            
            # Ensure savings potential doesn't exceed total cost
            if total_cost is not None:
                savings_potential = min(savings_potential, float(total_cost) * 0.95)  # Cap at 95% of total cost

        # 如果成本趋势没有历史数据，则用“当前资源月度成本（折后优先）”作为统一口径的 total_cost
        if total_cost is None and account_config:
            ecs_cost_map = _get_cost_map("ecs", account_config)
            rds_cost_map = _get_cost_map("rds", account_config)
            redis_cost_map = _get_cost_map("redis", account_config)

            estimated_total = 0.0
            for inst in instances:
                cost = ecs_cost_map.get(inst.id)
                if cost is None:
                    cost = _estimate_monthly_cost(inst)
                estimated_total += float(cost or 0)
            for rds in rds_list:
                cost = rds_cost_map.get(rds.id)
                if cost is None:
                    cost = _estimate_monthly_cost(rds)
                estimated_total += float(cost or 0)
            for r in redis_list:
                cost = redis_cost_map.get(r.id)
                if cost is None:
                    cost = _estimate_monthly_cost(r)
                estimated_total += float(cost or 0)

            total_cost = round(float(estimated_total), 2)
            # 再做一次 savings cap（此时 total_cost 已可用）
            savings_potential = min(float(savings_potential), float(total_cost) * 0.95) if total_cost else 0.0

        # 用账单全量口径覆盖 total_cost（更贴近真实账单）
        if billing_total_cost is not None:
            total_cost = round(float(billing_total_cost), 2)
            savings_potential = min(float(savings_potential), float(total_cost) * 0.95) if total_cost else 0.0
        
    except Exception as e:
        # Fallback if resource query fails
        total_resources = 0
        resource_breakdown = {"ecs": 0, "rds": 0, "redis": 0}
        tag_coverage = 0
        alert_count = 0
        savings_potential = 0
        if total_cost is None:
            total_cost = 0.0

    result_data = {
        "account": account,
        "total_cost": total_cost,
        "idle_count": idle_count,
        "cost_trend": trend,
        "trend_pct": trend_pct,
        "total_resources": total_resources,
        "resource_breakdown": resource_breakdown,
        "alert_count": alert_count,
        "tag_coverage": round(tag_coverage, 2),
        "savings_potential": savings_potential,
    }
    
    # 保存到缓存（24小时有效）
    cache_manager.set(resource_type="dashboard_summary", account_name=account, data=result_data)
    
    return {
        **result_data,
        "cached": False,
    }


@router.get("/dashboard/trend")
def get_trend(account: Optional[str] = None, days: int = 30, force_refresh: bool = Query(False, description="强制刷新缓存")):
    """Get cost trend chart data（带24小时缓存）"""
    if not account:
        raise HTTPException(status_code=400, detail="账号参数是必需的")
    print(f"[DEBUG get_trend] 收到账号参数: {account}, days: {days}")
    # 初始化缓存管理器，TTL设置为24小时（86400秒）
    cache_manager = ResourceCacheManager(ttl_seconds=86400)
    
    # 生成缓存键（包含 days 参数）
    cache_key = f"dashboard_trend_{days}"
    
    # 尝试从缓存获取数据
    cached_result = None
    if not force_refresh:
        cached_result = cache_manager.get(resource_type=cache_key, account_name=account)
    
    # 如果缓存有效，直接使用缓存数据
    if cached_result is not None:
        return {
            **cached_result,
            "cached": True,
        }
    
    analyzer = CostTrendAnalyzer()
    try:
        report = analyzer.generate_trend_report(account, days)
        if "error" in report:
            # 趋势图常见的“无数据/数据不足”不应该作为服务端错误；
            # 返回 200 + 空 chart_data，前端可自然降级为“不展示趋势图”。
            err = report.get("error") or "No trend data"
            if err in ("No cost history available", "Insufficient data for trend analysis"):
                return {
                    "account": account,
                    "period_days": days,
                    "analysis": {"error": err},
                    "chart_data": None,
                    "cost_by_type": {},
                    "cost_by_region": {},
                    "snapshots_count": 0,
                    "cached": False,
                }
            raise HTTPException(status_code=404, detail=err)
        
        # 保存到缓存（24小时有效）
        cache_manager.set(resource_type=cache_key, account_name=account, data=report)
        
        return {
            **report,
            "cached": False,
        }
    except HTTPException:
        # 不要把 4xx 再包装成 500，否则前端只能看到 “Internal Server Error”
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/idle")
def get_idle_resources(account: Optional[str] = None, force_refresh: bool = Query(False, description="强制刷新缓存")):
    """Get idle resources list（带24小时缓存）"""
    if not account:
        raise HTTPException(status_code=400, detail="账号参数是必需的")
    print(f"[DEBUG get_idle_resources] 收到账号参数: {account}")
    # 初始化缓存管理器，TTL设置为24小时（86400秒）
    cache_manager = ResourceCacheManager(ttl_seconds=86400)
    
    # 尝试从缓存获取数据
    cached_result = None
    if not force_refresh:
        cached_result = cache_manager.get(resource_type="dashboard_idle", account_name=account)
    
    # 如果缓存有效，直接使用缓存数据
    if cached_result is not None:
        return {
            "success": True,
            "data": cached_result,
            "cached": True,
        }
    
    try:
        from core.services.analysis_service import AnalysisService
        data, _ = AnalysisService.analyze_idle_resources(account, days=7, force_refresh=False)
        result_data = data if data else []
        
        # 保存到缓存（24小时有效）
        cache_manager.set(resource_type="dashboard_idle", account_name=account, data=result_data)
        
        return {
            "success": True,
            "data": result_data,
            "cached": False,
        }
    except Exception as e:
        return {
            "success": True,
            "data": [],
            "cached": False,
        }


# ==================== Phase 1 Week 2: Resource Management APIs ====================

def _get_provider_for_account(account: Optional[str] = None):
    """Helper to get provider instance"""
    cm = ConfigManager()
    if not account:
        ctx = ContextManager()
        account = ctx.get_last_account()
    if not account:
        accounts = cm.list_accounts()
        if accounts:
            # list_accounts() returns a list of CloudAccount objects, not a dict
            account = accounts[0].name
        else:
            raise HTTPException(status_code=404, detail="No accounts configured")
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"Account '{account}' not found")
    
    from cli.utils import get_provider
    return get_provider(account_config), account


def _get_billing_cycle_default() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m")


def _get_billing_overview_from_db(
    account_name: str,
    billing_cycle: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    从本地账单数据库读取成本概览（优先使用，速度快）
    
    Returns:
        成本概览数据，如果数据库不存在或读取失败则返回 None
    """
    import sqlite3
    import os
    from datetime import datetime
    
    db_path = os.path.expanduser("~/.cloudlens/bills.db")
    if not os.path.exists(db_path):
        return None
    
    try:
        if billing_cycle is None:
            billing_cycle = datetime.now().strftime("%Y-%m")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查找匹配的 account_id
        cursor.execute("""
            SELECT DISTINCT account_id 
            FROM bill_items 
            WHERE account_id LIKE ?
            LIMIT 1
        """, (f"%{account_name}%",))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return None
        
        account_id = result[0]
        
        # 按产品聚合当月成本
        cursor.execute("""
            SELECT 
                product_name,
                product_code,
                subscription_type,
                SUM(pretax_amount) as total_pretax
            FROM bill_items
            WHERE account_id = ?
                AND billing_cycle = ?
                AND pretax_amount IS NOT NULL
            GROUP BY product_name, product_code, subscription_type
        """, (account_id, billing_cycle))
        
        by_product: Dict[str, float] = {}
        by_product_name: Dict[str, str] = {}
        by_product_subscription: Dict[str, Dict[str, float]] = {}
        total = 0.0
        
        for row in cursor.fetchall():
            product_name = row[0] or "unknown"
            product_code = row[1] or "unknown"
            subscription_type = row[2] or "Unknown"
            pretax = row[3] or 0.0
            
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
        
        conn.close()
        
        if total <= 0:
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
    调用阿里云 BSS OpenAPI QueryInstanceBill，返回原始条目列表。
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

        # 兼容不同返回结构：Data.Items.Item 或 Data.Item
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


def _get_cost_map_from_billing(resource_type: str, account_config: CloudAccount, billing_cycle: Optional[str] = None) -> Dict[str, float]:
    """
    用 BSS 账单数据构建实例成本映射（尽量真实、含折扣）。
    - 对于按量付费：PaymentAmount 经常为 0（未结算），使用 PretaxAmount
    - 对于包年包月：PaymentAmount 通常有值，也可用 PretaxAmount；这里统一用 PretaxAmount（税前折后口径）
    """
    if billing_cycle is None:
        billing_cycle = _get_billing_cycle_default()

    # BSS 产品代码映射
    product_code_map = {
        "ecs": "ecs",
        "rds": "rds",
        "redis": "kvstore",
        # 全量资源（尽量映射到可被 QueryInstanceBill 按实例返回的产品）
        "slb": "slb",
        "eip": "eip",
        "nat": "nat_gw",
        "nat_gw": "nat_gw",
        "yundisk": "yundisk",
        "disk": "yundisk",
        "snapshot": "snapshot",
        "oss": "oss",
        "nas": "nas",
    }
    product_code = product_code_map.get(resource_type)
    if not product_code:
        return {}

    expected_prefix_map = {
        "ecs": "i-",
        "rds": "rm-",
        "redis": "r-",
        "slb": "lb-",
        "eip": "eip-",
        "nat": "ngw-",
        "nat_gw": "ngw-",
        "yundisk": "d-",
        "disk": "d-",
        "snapshot": "s-",
    }
    expected_prefix = expected_prefix_map.get(resource_type)

    cache_manager = ResourceCacheManager(ttl_seconds=86400)
    cache_key = f"billing_cost_map_{resource_type}_{billing_cycle}"
    cached = cache_manager.get(resource_type=cache_key, account_name=account_config.name)
    if isinstance(cached, dict) and cached:
        return cached

    cost_map: Dict[str, float] = {}
    try:
        # 分别拉 PayAsYouGo / Subscription，覆盖两类实例
        for sub_type in ("PayAsYouGo", "Subscription"):
            rows = _bss_query_instance_bill(account_config, billing_cycle, product_code, subscription_type=sub_type)
            for row in rows:
                instance_id = (
                    row.get("InstanceID")
                    or row.get("InstanceId")
                    or row.get("instanceId")
                    or row.get("instance_id")
                )
                if not instance_id:
                    continue
                # 某些产品（如 snapshot）QueryInstanceBill 的 InstanceID 可能返回 RegionId 等非资源ID
                # 这里做前缀校验，不符合则跳过，后续在资源列表侧做“按账单总额分摊”的兜底。
                if expected_prefix and not str(instance_id).startswith(expected_prefix):
                    continue
                # 关键：PayAsYouGo 的 PaymentAmount 可能为 0（未结算），用 PretaxAmount 更稳定
                pretax = row.get("PretaxAmount")
                try:
                    pretax_f = float(pretax) if pretax is not None else 0.0
                except Exception:
                    pretax_f = 0.0

                if pretax_f <= 0:
                    continue
                # 多条计费项可能汇总到同一实例：累加
                cost_map[instance_id] = float(cost_map.get(instance_id, 0.0) + pretax_f)

        cache_manager.set(resource_type=cache_key, account_name=account_config.name, data=cost_map)
        return cost_map
    except Exception:
        # 账单不可用时，静默回退到其他成本来源
        return {}


def _bss_query_bill_overview(account_config: CloudAccount, billing_cycle: str) -> List[Dict[str, Any]]:
    """
    调用阿里云 BSS OpenAPI QueryBillOverview，返回 Item 列表。
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
    从账单概览计算：
    - total_pretax: 按产品聚合后的总额（使用 PretaxAmount）
    - by_product: {product_code: pretax_amount_sum}

    说明：
    - PayAsYouGo 的 PaymentAmount 经常为 0（未结算），OutstandingAmount 为未结算金额
      为了让“总成本”贴近账单发生额，这里统一使用 PretaxAmount。
    """
    if billing_cycle is None:
        billing_cycle = _get_billing_cycle_default()

    cache_key = f"billing_overview_totals_{billing_cycle}"
    cache_manager = ResourceCacheManager(ttl_seconds=86400)
    if not force_refresh:
        cached = cache_manager.get(resource_type=cache_key, account_name=account_config.name)
        if isinstance(cached, dict) and "total_pretax" in cached and "by_product" in cached:
            return cached

    # 优先尝试从本地数据库读取（快速）
    if not force_refresh:
        db_result = _get_billing_overview_from_db(account_config.name, billing_cycle)
        if db_result is not None:
            logger.info(f"✅ 从本地数据库读取账单概览: {account_config.name}, {billing_cycle}")
            cache_manager.set(resource_type=cache_key, account_name=account_config.name, data=db_result)
            return db_result
        logger.warning(f"⚠️  本地数据库不可用，回退到云API查询: {account_config.name}")

    items = _bss_query_bill_overview(account_config, billing_cycle)
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

        by_product[product_code] = float(by_product.get(product_code, 0.0) + pretax_f)
        by_product_subscription.setdefault(product_code, {})
        by_product_subscription[product_code][subscription_type] = float(
            by_product_subscription[product_code].get(subscription_type, 0.0) + pretax_f
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
    }
    cache_manager.set(resource_type=cache_key, account_name=account_config.name, data=result)
    return result


def _get_cost_map(resource_type: str, account_config: CloudAccount) -> Dict[str, float]:
    """Get cost map for all resources of a type from CostAnalyzer"""
    cost_map = {}
    try:
        from resource_modules.cost_analyzer import CostAnalyzer
        
        cost_analyzer = CostAnalyzer(
            tenant_name=account_config.name,
            access_key_id=account_config.access_key_id,
            access_key_secret=account_config.access_key_secret
        )

        # 最高优先级：BSS 账单（按实例真实成本，含折扣）
        billing_costs = _get_cost_map_from_billing(resource_type, account_config)
        for instance_id, monthly_cost in (billing_costs or {}).items():
            if instance_id and monthly_cost and monthly_cost > 0:
                cost_map[instance_id] = float(monthly_cost)
        
        # 尝试从折扣分析器获取（最准确）
        costs = cost_analyzer.get_cost_from_discount_analyzer(resource_type)
        for cost_item in costs:
            instance_id = cost_item.get("instance_id")
            monthly_cost = cost_item.get("monthly_cost", 0)
            if instance_id and monthly_cost and monthly_cost > 0:
                if instance_id not in cost_map:
                    cost_map[instance_id] = float(monthly_cost)
        
        # 再从数据库补全缺失项（常见：按量付费资源只有数据库/账单侧有成本）
        db_costs = cost_analyzer.get_cost_from_database(resource_type)
        for cost_item in db_costs:
            instance_id = cost_item.get("instance_id")
            monthly_cost = cost_item.get("monthly_cost", 0)
            if not instance_id or not monthly_cost or monthly_cost <= 0:
                continue
            if instance_id not in cost_map:
                cost_map[instance_id] = float(monthly_cost)
    except Exception as e:
        # 如果获取失败，返回空字典，使用估算值
        pass
    
    return cost_map


def _estimate_monthly_cost_from_spec(spec: str, resource_type: str = "ecs") -> float:
    """Estimate monthly cost from spec string"""
    cost_map = {
        "ecs.t5-lc1m1.small": 50,
        "ecs.t5-lc1m2.small": 80,
        "ecs.g6.large": 400,
        "ecs.g6.xlarge": 800,
        "rds.mysql.s1.small": 200,
        "rds.mysql.s2.large": 500,
        "redis.master.small.default": 150,
        "redis.master.mid.default": 300,
    }
    
    if spec and spec in cost_map:
        return cost_map[spec]

    # 更通用的 ECS 规格估算：ecs.{family}.{size}
    # 目的：避免“未知规格全部落到同一个默认值”，导致不同实例成本看起来完全一致
    if resource_type == "ecs" and isinstance(spec, str) and spec.startswith("ecs."):
        parts = spec.split(".")
        # 常见：ecs.r8i.xlarge / ecs.c8i.2xlarge / ecs.hfr9i.xlarge
        if len(parts) >= 3:
            family = parts[-2] or ""
            size = parts[-1] or ""

            # size multiplier（以 large=1, xlarge=2, 2xlarge=4, ...）
            size_mul = 1.0
            s = size.lower()
            if s == "small":
                size_mul = 0.25
            elif s == "medium":
                size_mul = 0.5
            elif s == "large":
                size_mul = 1.0
            elif s == "xlarge":
                size_mul = 2.0
            else:
                import re
                m = re.match(r"^(\d+)xlarge$", s)
                if m:
                    n = int(m.group(1))
                    size_mul = max(1.0, float(n) * 2.0)

            # family multiplier（粗略：r>g>c>t）
            fam = (family or "").lower()
            prefix = fam[:1]
            fam_mul = 1.1
            if prefix == "t":
                fam_mul = 0.55
            elif prefix == "c":
                fam_mul = 1.0
            elif prefix == "g":
                fam_mul = 1.15
            elif prefix == "r":
                fam_mul = 1.45
            elif prefix == "h":
                fam_mul = 1.35

            # generation multiplier（按代际略增：6 代基线）
            import re
            m2 = re.search(r"(\d+)", fam)
            gen_mul = 1.0
            if m2:
                gen = int(m2.group(1))
                if gen > 6:
                    gen_mul = min(1.30, 1.0 + (gen - 6) * 0.05)

            # base price（large 的基准月价，CNY 粗估）
            base_large = 320.0
            est = base_large * size_mul * fam_mul * gen_mul
            return round(est, 2)
    
    # Default estimates by resource type
    if resource_type == "ecs":
        return 300
    elif resource_type == "rds":
        return 400
    elif resource_type == "redis":
        return 200
    
    return 200  # Default


def _estimate_monthly_cost(resource) -> float:
    """Estimate monthly cost for a resource (fallback when real cost is not available)"""
    spec = getattr(resource, "spec", None) or ""
    resource_type = "ecs"
    if hasattr(resource, "resource_type"):
        rt = resource.resource_type.value if hasattr(resource.resource_type, 'value') else str(resource.resource_type)
        if "rds" in rt.lower():
            resource_type = "rds"
        elif "redis" in rt.lower():
            resource_type = "redis"
    
    return _estimate_monthly_cost_from_spec(spec, resource_type)


@router.get("/resources")
def list_resources(
    type: str = Query("ecs", description="资源类型"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    account: Optional[str] = None,
    sortBy: Optional[str] = None,
    sortOrder: Optional[str] = Query("asc", regex="^(asc|desc)$"),
    filter: Optional[str] = None,
    force_refresh: bool = Query(False, description="强制刷新缓存"),
):
    """获取资源列表（支持分页、排序、筛选，带24小时缓存）"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[list_resources] 收到账号参数: {account}, type: {type}")
    print(f"[DEBUG list_resources] 收到账号参数: {account}, type: {type}")
    
    provider, account_name = _get_provider_for_account(account)
    logger.info(f"[list_resources] 使用账号: {account_name}")
    print(f"[DEBUG list_resources] 使用账号: {account_name}")
    
    # 初始化缓存管理器，TTL设置为24小时（86400秒）
    cache_manager = ResourceCacheManager(ttl_seconds=86400)
    
    # 尝试从缓存获取数据
    cached_result = None
    if not force_refresh:
        cached_result = cache_manager.get(resource_type=type, account_name=account_name)
    
    # 如果缓存有效，直接使用缓存数据
    if cached_result is not None:
        result = cached_result
    else:
        # 缓存无效或不存在，从provider查询
        cm = ConfigManager()
        account_config = cm.get_account(account_name)

        # 根据类型获取资源
        if type == "ecs":
            resources = provider.list_instances()
        elif type == "rds":
            resources = provider.list_rds()
        elif type == "redis":
            resources = provider.list_redis()
        elif type == "slb":
            resources = provider.list_slb() if hasattr(provider, "list_slb") else []
        elif type == "nat":
            resources = provider.list_nat_gateways() if hasattr(provider, "list_nat_gateways") else []
        elif type == "eip":
            # EIP provider 返回 dict 列表
            resources = provider.list_eip() if hasattr(provider, "list_eip") else []
        elif type == "oss":
            # OSS bucket 列表（如果安装了 oss2）
            resources = provider.list_oss() if hasattr(provider, "list_oss") else []
        elif type == "disk":
            resources = provider.list_disks() if hasattr(provider, "list_disks") else []
        elif type == "snapshot":
            resources = provider.list_snapshots() if hasattr(provider, "list_snapshots") else []
        elif type == "vpc":
            vpcs = provider.list_vpcs()
            # Convert VPC dict to list format
            resources = []
            for vpc in vpcs:
                from models.resource import UnifiedResource, ResourceType, ResourceStatus

                resources.append(
                    UnifiedResource(
                        id=vpc.get("VpcId", ""),
                        name=vpc.get("VpcName", ""),
                        resource_type=ResourceType.VPC,
                        status=ResourceStatus.RUNNING,
                        provider=provider.provider_name,
                        region=vpc.get("RegionId", account_name),
                    )
                )
        else:
            raise HTTPException(status_code=400, detail=f"不支持的资源类型: {type}")

        # 批量获取真实成本映射（提高效率）
        cost_map = {}
        if account_config and type not in ("vpc",):
            cost_map = _get_cost_map(type, account_config)

        # 转换为统一格式，使用真实成本
        result = []

        # dict 资源（EIP/OSS 等）
        if resources and isinstance(resources[0], dict):
            # 快照：QueryInstanceBill 很多情况下返回 RegionId 而不是 SnapshotId，导致无法逐实例对齐
            # 这种情况改用账单总额按容量比例分摊到每个快照，保证“实例级 cost 之和 == 账单全量”
            if account_config and type == "snapshot":
                has_snapshot_keys = any(str(k).startswith("s-") for k in (cost_map or {}).keys())
                if not has_snapshot_keys:
                    cost_map = {}
                try:
                    totals = _get_billing_overview_totals(account_config, force_refresh=force_refresh)
                    product_total = float(((totals or {}).get("by_product") or {}).get("snapshot") or 0.0)
                except Exception:
                    product_total = 0.0

                if product_total > 0:
                    weights = []
                    for r in resources:
                        rid = r.get("id")
                        if not rid:
                            continue
                        w = r.get("size_gb") or 0
                        try:
                            w = float(w)
                        except Exception:
                            w = 0.0
                        weights.append((rid, max(0.0, w)))

                    total_w = sum(w for _, w in weights)
                    if total_w <= 0:
                        # 没有容量信息，均分
                        n = len(weights)
                        if n > 0:
                            per = product_total / n
                            for rid, _ in weights:
                                cost_map[rid] = per
                    else:
                        for rid, w in weights:
                            cost_map[rid] = product_total * (w / total_w)

            for r in resources:
                rid = r.get("id") or r.get("Id") or r.get("ResourceId") or r.get("name")
                if not rid:
                    continue

                # EIP：id=AllocationId；OSS：id=bucket name
                cost = cost_map.get(rid, 0.0)

                name = r.get("name") or r.get("ip_address") or r.get("id") or "-"
                spec = "-"
                region_val = r.get("region") or r.get("RegionId") or getattr(provider, "region", "")
                status_val = r.get("status") or r.get("Status") or "-"

                if type == "eip":
                    spec = f"{r.get('bandwidth', '-') }Mbps"
                elif type == "disk":
                    size_gb = r.get("size_gb", "-")
                    cat = r.get("disk_category", "-")
                    dtyp = r.get("disk_type", "-")
                    spec = f"{cat} / {dtyp} / {size_gb}GB"
                elif type == "snapshot":
                    src = r.get("source_disk_id") or "-"
                    size_gb = r.get("size_gb", "-")
                    spec = f"源盘: {src} / {size_gb}GB"

                result.append(
                    {
                        "id": rid,
                        "name": name,
                        "type": type,
                        "status": str(status_val),
                        "region": str(region_val),
                        "spec": str(spec),
                        "cost": float(cost or 0),
                        "tags": {},
                    "created_time": r.get("created_time") if isinstance(r.get("created_time"), str) else None,
                        "public_ips": [r.get("ip_address")] if r.get("ip_address") else [],
                        "private_ips": [],
                    }
                )
        else:
            for r in resources:
                # 从成本映射中获取真实成本，如果没有则使用估算值
                cost = cost_map.get(r.id)
                if cost is None:
                    cost = _estimate_monthly_cost(r)

                result.append(
                    {
                        "id": r.id,
                        "name": r.name or "-",
                        "type": type,
                        "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                        "region": r.region,
                        "spec": r.spec or "-",
                        "cost": float(cost or 0),
                        "tags": r.tags if hasattr(r, "tags") and r.tags else {},
                        "created_time": r.created_time.isoformat()
                        if hasattr(r, "created_time") and r.created_time
                        else None,
                        "public_ips": r.public_ips if hasattr(r, "public_ips") else [],
                        "private_ips": r.private_ips if hasattr(r, "private_ips") else [],
                    }
                )

        # 保存到缓存（24小时有效）
        cache_manager.set(resource_type=type, account_name=account_name, data=result)
    
    # 排序（在缓存数据上排序）
    if sortBy:
        reverse = sortOrder == "desc"
        try:
            result.sort(key=lambda x: x.get(sortBy, ""), reverse=reverse)
        except:
            pass  # Ignore sort errors
    
    # 筛选（在缓存数据上筛选）
    if filter:
        try:
            import json
            filter_dict = json.loads(filter)
            filtered_result = []
            for item in result:
                match = True
                for key, value in filter_dict.items():
                    if item.get(key) != value:
                        match = False
                        break
                if match:
                    filtered_result.append(item)
            result = filtered_result
        except:
            pass  # Ignore filter errors
    
    # 分页（在缓存数据上分页）
    total = len(result)
    start = (page - 1) * pageSize
    end = start + pageSize
    paginated_resources = result[start:end]
    
    return {
        "success": True,
        "data": paginated_resources,
        "pagination": {
            "page": page,
            "pageSize": pageSize,
            "total": total,
            "totalPages": (total + pageSize - 1) // pageSize,
        },
        "cached": cached_result is not None,  # 标识是否来自缓存
    }


@router.get("/resources/{resource_id}")
def get_resource(resource_id: str, account: Optional[str] = None):
    """获取资源详情"""
    provider, account_name = _get_provider_for_account(account)
    
    # 获取账号配置用于成本查询
    cm = ConfigManager()
    account_config = cm.get_account(account_name)
    
    # 尝试从各种资源类型中查找（资源量较大时建议按 type 查；这里为通用详情入口做尽量覆盖）
    # UnifiedResource 类资源
    resources = []
    try:
        resources.extend(provider.list_instances())
        resources.extend(provider.list_rds())
        resources.extend(provider.list_redis())
        if hasattr(provider, "list_slb"):
            resources.extend(provider.list_slb())
        if hasattr(provider, "list_nat_gateways"):
            resources.extend(provider.list_nat_gateways())
    except Exception:
        pass

    resource = next((r for r in resources if getattr(r, "id", None) == resource_id), None)

    # dict 资源（EIP/OSS）
    dict_resource = None
    if resource is None:
        try:
            if hasattr(provider, "list_eip"):
                for e in provider.list_eip():
                    if e.get("id") == resource_id:
                        dict_resource = ("eip", e)
                        break
            if dict_resource is None and hasattr(provider, "list_oss"):
                for b in provider.list_oss():
                    if b.get("id") == resource_id:
                        dict_resource = ("oss", b)
                        break
            if dict_resource is None and hasattr(provider, "list_disks"):
                for d in provider.list_disks():
                    if d.get("id") == resource_id:
                        dict_resource = ("disk", d)
                        break
            if dict_resource is None and hasattr(provider, "list_snapshots"):
                for s in provider.list_snapshots():
                    if s.get("id") == resource_id:
                        dict_resource = ("snapshot", s)
                        break
        except Exception:
            dict_resource = None

    if resource is None and dict_resource is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    # 确定资源类型
    resource_type = "ecs"
    if dict_resource is not None:
        resource_type = dict_resource[0]
    elif hasattr(resource, "resource_type"):
        rt = resource.resource_type.value if hasattr(resource.resource_type, "value") else str(resource.resource_type)
        if "rds" in rt.lower():
            resource_type = "rds"
        elif "redis" in rt.lower():
            resource_type = "redis"
        elif "vpc" in rt.lower():
            resource_type = "vpc"
        elif "slb" in rt.lower():
            resource_type = "slb"
        elif "nat" in rt.lower():
            resource_type = "nat"
    
    # 获取真实成本映射
    cost_map = {}
    if account_config and resource_type not in ("vpc",):
        cost_map = _get_cost_map(resource_type, account_config)

    if dict_resource is not None:
        _, r = dict_resource
        cost = float(cost_map.get(resource_id) or 0.0)
        spec = "-"
        if resource_type == "eip":
            spec = f"{r.get('bandwidth', '-') }Mbps"
        elif resource_type == "disk":
            spec = f"{r.get('disk_category', '-') } / {r.get('disk_type', '-') } / {r.get('size_gb', '-') }GB"
        elif resource_type == "snapshot":
            spec = f"源盘: {r.get('source_disk_id') or '-'}"
        return {
            "success": True,
            "data": {
                "id": resource_id,
                "name": r.get("name") or r.get("ip_address") or resource_id,
                "type": resource_type,
                "status": str(r.get("status") or "-"),
                "region": str(r.get("region") or getattr(provider, "region", "")),
                "spec": spec,
                "cost": cost,
                "tags": {},
                "created_time": r.get("created_time") if isinstance(r.get("created_time"), str) else None,
                "public_ips": [r.get("ip_address")] if r.get("ip_address") else [],
                "private_ips": [],
                "raw_data": r,
            },
        }

    # UnifiedResource
    cost = cost_map.get(resource_id)
    if cost is None:
        cost = _estimate_monthly_cost(resource)

    return {
        "success": True,
        "data": {
            "id": resource.id,
            "name": resource.name or "-",
            "type": resource_type,
            "status": resource.status.value if hasattr(resource.status, "value") else str(resource.status),
            "region": resource.region,
            "spec": resource.spec or "-",
            "cost": float(cost or 0),
            "tags": resource.tags if hasattr(resource, "tags") and resource.tags else {},
            "created_time": resource.created_time.isoformat()
            if hasattr(resource, "created_time") and resource.created_time
            else None,
            "public_ips": resource.public_ips if hasattr(resource, "public_ips") else [],
            "private_ips": resource.private_ips if hasattr(resource, "private_ips") else [],
            "raw_data": getattr(resource, "raw_data", {}),
        },
    }


@router.get("/resources/{resource_id}/metrics")
def get_resource_metrics(
    resource_id: str,
    days: int = Query(7, ge=1, le=30),
    account: Optional[str] = None,
):
    """获取资源监控数据"""
    provider, account_name = _get_provider_for_account(account)
    
    # 获取资源
    resources = []
    try:
        resources.extend(provider.list_instances())
    except:
        pass
    
    resource = next((r for r in resources if r.id == resource_id), None)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    
    # 获取监控数据
    try:
        from core.idle_detector import IdleDetector
        metrics = IdleDetector.fetch_ecs_metrics(provider, resource_id, days)
        
        # 转换为图表数据格式
        chart_data = {
            "cpu": [],
            "memory": [],
            "network_in": [],
            "network_out": [],
            "dates": [],
        }
        
        # 简化：返回平均值（实际应该返回时间序列数据）
        return {
            "success": True,
            "data": {
                "metrics": metrics,
                "chart_data": chart_data,
            }
        }
    except Exception as e:
        return {
            "success": True,
            "data": {
                "metrics": {},
                "chart_data": {},
                "error": str(e),
            }
        }


# ==================== Phase 1 Week 3: Account Management APIs ====================

@router.get("/settings/accounts")
def list_accounts_settings():
    """获取账号列表（用于设置页面）"""
    cm = ConfigManager()
    accounts = cm.list_accounts()
    result = []
    for account in accounts:
        if isinstance(account, CloudAccount):
            result.append({
                "name": account.name,
                "region": account.region,
                "provider": account.provider,
                "access_key_id": account.access_key_id,
            })
    return {"success": True, "data": result}


@router.post("/settings/accounts")
def add_account(account_data: Dict[str, Any]):
    """添加账号"""
    cm = ConfigManager()
    try:
        cm.add_account(
            name=account_data["name"],
            provider=account_data.get("provider", "aliyun"),
            access_key_id=account_data["access_key_id"],
            access_key_secret=account_data["access_key_secret"],
            region=account_data.get("region", "cn-hangzhou"),
        )
        return {"success": True, "message": "账号添加成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/settings/accounts/{account_name}")
def delete_account(account_name: str):
    """删除账号"""
    cm = ConfigManager()
    try:
        cm.remove_account(account_name)
        return {"success": True, "message": "账号删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Phase 2: Cost Analysis APIs ====================

@router.get("/cost/overview")
def get_cost_overview(account: Optional[str] = None, force_refresh: bool = Query(False, description="强制刷新缓存")):
    """获取成本概览（优先账单口径，带24小时缓存）"""
    provider, account_name = _get_provider_for_account(account)
    
    # 初始化缓存管理器，TTL设置为24小时（86400秒）
    cache_manager = ResourceCacheManager(ttl_seconds=86400)
    
    # 尝试从缓存获取数据
    cached_result = None
    if not force_refresh:
        cached_result = cache_manager.get(resource_type="cost_overview", account_name=account_name)
    
    # 如果缓存有效，直接使用缓存数据
    if cached_result is not None:
        return {
            "success": True,
            "data": cached_result,
            "cached": True,
        }
    
    # 缓存无效或不存在，计算新数据
    cm = ConfigManager()
    account_config = cm.get_account(account_name)
    
    try:
        # 账单优先：使用 BSS 账单概览作为“全量成本”口径
        from datetime import datetime
        now = datetime.now()
        current_cycle = now.strftime("%Y-%m")
        last_cycle = (now.replace(day=1) - __import__("datetime").timedelta(days=1)).strftime("%Y-%m")

        current_totals = _get_billing_overview_totals(account_config, billing_cycle=current_cycle) if account_config else None
        last_totals = _get_billing_overview_totals(account_config, billing_cycle=last_cycle) if account_config else None

        current_month_cost = float((current_totals or {}).get("total_pretax") or 0.0)
        last_month_cost = float((last_totals or {}).get("total_pretax") or 0.0)
        mom = ((current_month_cost - last_month_cost) / last_month_cost * 100) if last_month_cost > 0 else 0.0
        yoy = 0.0  # TODO: 支持去年同期账期对比
        
        result_data = {
            "current_month": round(current_month_cost, 2),
            "last_month": round(last_month_cost, 2),
            "yoy": round(yoy, 2),
            "mom": round(mom, 2),
        }
        
        # 保存到缓存（24小时有效）
        cache_manager.set(resource_type="cost_overview", account_name=account_name, data=result_data)
        
        return {
            "success": True,
            "data": result_data,
            "cached": False,
        }
    except Exception as e:
        return {
            "success": True,
            "data": {
                "current_month": 0,
                "last_month": 0,
                "yoy": 0,
                "mom": 0,
            },
            "cached": False,
        }


@router.get("/cost/breakdown")
def get_cost_breakdown(
    account: Optional[str] = None,
    force_refresh: bool = Query(False, description="强制刷新缓存"),
    billing_cycle: Optional[str] = Query(None, description="账期 yyyy-MM，默认当月"),
):
    """获取成本构成（优先账单口径，带24小时缓存）"""
    provider, account_name = _get_provider_for_account(account)
    
    # 初始化缓存管理器，TTL设置为24小时（86400秒）
    cache_manager = ResourceCacheManager(ttl_seconds=86400)
    
    # 尝试从缓存获取数据
    cached_result = None
    if not force_refresh:
        cached_result = cache_manager.get(resource_type="cost_breakdown", account_name=account_name)
    
    # 如果缓存有效，直接使用缓存数据
    if cached_result is not None:
        return {
            "success": True,
            "data": cached_result,
            "cached": True,
        }
    
    # 缓存无效或不存在，计算新数据
    cm = ConfigManager()
    account_config = cm.get_account(account_name)

    try:
        # 账单优先：用 BSS BillOverview 的 ProductCode 聚合得到“全量成本构成”
        totals = _get_billing_overview_totals(account_config, billing_cycle=billing_cycle) if account_config else None
        by_product = (totals or {}).get("by_product") or {}
        total = float((totals or {}).get("total_pretax") or 0.0)
        by_product_name = (totals or {}).get("by_product_name") or {}
        by_product_subscription = (totals or {}).get("by_product_subscription") or {}

        # 便于前端展示的列表结构（排序后）
        categories = []
        for code, amount in by_product.items():
            try:
                amount_f = float(amount or 0.0)
            except Exception:
                amount_f = 0.0
            if amount_f <= 0:
                continue
            categories.append(
                {
                    "code": code,
                    "name": by_product_name.get(code) or code,
                    "amount": round(amount_f, 2),
                    "subscription": by_product_subscription.get(code) or {},
                }
            )
        categories.sort(key=lambda x: float(x.get("amount") or 0.0), reverse=True)

        result_data = {
            # 兼容旧前端字段：by_type 仍返回 {code: amount}
            "by_type": by_product,
            "total": round(float(total), 2),
            "billing_cycle": (totals or {}).get("billing_cycle") or billing_cycle,
            "source": "billing_overview",
            # 新字段：前端直接用 categories 渲染更友好
            "categories": categories,
            "by_product_name": by_product_name,
        }
        
        # 保存到缓存（24小时有效）
        cache_manager.set(resource_type="cost_breakdown", account_name=account_name, data=result_data)
        
        return {
            "success": True,
            "data": result_data,
            "cached": False,
        }
    except Exception as e:
        return {
            "success": True,
            "data": {
                "by_type": {},
                "total": 0,
            },
            "cached": False,
        }


# ==================== Phase 2: Security APIs ====================

@router.get("/security/overview")
def get_security_overview(account: Optional[str] = None, force_refresh: bool = Query(False, description="强制刷新缓存")):
    """获取安全概览（带24小时缓存）"""
    provider, account_name = _get_provider_for_account(account)
    
    # 初始化缓存管理器，TTL设置为24小时（86400秒）
    cache_manager = ResourceCacheManager(ttl_seconds=86400)
    
    # 尝试从缓存获取数据
    cached_result = None
    if not force_refresh:
        cached_result = cache_manager.get(resource_type="security_overview", account_name=account_name)
    
    # 如果缓存有效，直接使用缓存数据
    if cached_result is not None:
        return {
            "success": True,
            "data": cached_result,
            "cached": True,
        }
    
    try:
        from core.security_compliance import SecurityComplianceAnalyzer
        
        instances = provider.list_instances()
        rds_list = provider.list_rds()
        redis_list = provider.list_redis()
        all_resources = instances + rds_list + redis_list
        
        analyzer = SecurityComplianceAnalyzer()
        
        # 公网暴露检测
        exposed = analyzer.detect_public_exposure(all_resources)
        
        # 安全检查
        stopped = analyzer.check_stopped_instances(instances)
        tag_coverage, no_tags = analyzer.check_missing_tags(all_resources)
        
        # 磁盘加密检查
        encryption_info = analyzer.check_disk_encryption(instances)
        
        # 抢占式实例检查
        preemptible = analyzer.check_preemptible_instances(instances)
        
        # EIP使用情况（如果有EIP数据）
        eip_info = {"total": 0, "bound": 0, "unbound": 0, "unbound_rate": 0}
        try:
            eips = provider.list_eips() if hasattr(provider, 'list_eips') else []
            if eips:
                eip_info = analyzer.analyze_eip_usage(eips)
        except:
            pass
        
        # 计算安全评分（更详细的评分逻辑）
        security_score = 100
        score_deductions = []
        
        if len(exposed) > 0:
            deduction = min(len(exposed) * 5, 30)  # 最多扣30分
            security_score -= deduction
            score_deductions.append({"reason": f"公网暴露 {len(exposed)} 个资源", "deduction": deduction})
        
        if len(stopped) > 0:
            deduction = min(len(stopped) * 2, 20)  # 最多扣20分
            security_score -= deduction
            score_deductions.append({"reason": f"长期停止 {len(stopped)} 个实例", "deduction": deduction})
        
        if tag_coverage < 80:
            deduction = 10 if tag_coverage < 50 else 5
            security_score -= deduction
            score_deductions.append({"reason": f"标签覆盖率仅 {tag_coverage}%", "deduction": deduction})
        
        if encryption_info.get("encryption_rate", 100) < 50:
            deduction = 15
            security_score -= deduction
            score_deductions.append({"reason": f"磁盘加密率仅 {encryption_info.get('encryption_rate', 0)}%", "deduction": deduction})
        
        if len(preemptible) > 0:
            deduction = min(len(preemptible) * 3, 15)  # 最多扣15分
            security_score -= deduction
            score_deductions.append({"reason": f"抢占式实例 {len(preemptible)} 个", "deduction": deduction})
        
        if eip_info.get("unbound_rate", 0) > 20:
            deduction = 5
            security_score -= deduction
            score_deductions.append({"reason": f"未绑定EIP率 {eip_info.get('unbound_rate', 0)}%", "deduction": deduction})
        
        security_score = max(0, min(100, security_score))
        
        # 生成安全改进建议
        security_summary = {
            "exposed_count": len(exposed),
            "stopped_count": len(stopped),
            "tag_coverage_rate": tag_coverage,
            "encryption_rate": encryption_info.get("encryption_rate", 100),
            "preemptible_count": len(preemptible),
            "unbound_eip": eip_info.get("unbound", 0),
        }
        suggestions = analyzer.suggest_security_improvements(security_summary)
        
        result_data = {
            "security_score": security_score,
            "exposed_count": len(exposed),
            "stopped_count": len(stopped),
            "tag_coverage": tag_coverage,
            "missing_tags_count": len(no_tags),
            "alert_count": len(exposed) + len(stopped) + len(preemptible),
            "encryption_rate": encryption_info.get("encryption_rate", 100),
            "encrypted_count": encryption_info.get("encrypted", 0),
            "unencrypted_count": encryption_info.get("unencrypted_count", 0),
            "preemptible_count": len(preemptible),
            "eip_total": eip_info.get("total", 0),
            "eip_bound": eip_info.get("bound", 0),
            "eip_unbound": eip_info.get("unbound", 0),
            "eip_unbound_rate": eip_info.get("unbound_rate", 0),
            "score_deductions": score_deductions,
            "suggestions": suggestions,
        }
        
        # 保存到缓存（24小时有效）
        cache_manager.set(resource_type="security_overview", account_name=account_name, data=result_data)
        
        return {
            "success": True,
            "data": result_data,
            "cached": False,
        }
    except Exception as e:
        return {
            "success": True,
            "data": {
                "security_score": 0,
                "exposed_count": 0,
                "stopped_count": 0,
                "tag_coverage": 0,
                "missing_tags_count": 0,
                "alert_count": 0,
                "encryption_rate": 0,
                "encrypted_count": 0,
                "unencrypted_count": 0,
                "preemptible_count": 0,
                "eip_total": 0,
                "eip_bound": 0,
                "eip_unbound": 0,
                "eip_unbound_rate": 0,
                "score_deductions": [],
                "suggestions": [],
            },
            "cached": False,
        }


@router.get("/security/checks")
def get_security_checks(account: Optional[str] = None, force_refresh: bool = Query(False, description="强制刷新缓存")):
    """获取安全检查结果（带24小时缓存）"""
    provider, account_name = _get_provider_for_account(account)
    
    # 初始化缓存管理器，TTL设置为24小时（86400秒）
    cache_manager = ResourceCacheManager(ttl_seconds=86400)
    
    # 尝试从缓存获取数据
    cached_result = None
    if not force_refresh:
        cached_result = cache_manager.get(resource_type="security_checks", account_name=account_name)
    
    # 如果缓存有效，直接使用缓存数据
    if cached_result is not None:
        return {
            "success": True,
            "data": cached_result,
            "cached": True,
        }
    
    try:
        from core.security_compliance import SecurityComplianceAnalyzer
        
        instances = provider.list_instances()
        rds_list = provider.list_rds()
        redis_list = provider.list_redis()
        all_resources = instances + rds_list + redis_list
        
        analyzer = SecurityComplianceAnalyzer()
        
        exposed = analyzer.detect_public_exposure(all_resources)
        stopped = analyzer.check_stopped_instances(instances)
        tag_coverage, no_tags = analyzer.check_missing_tags(all_resources)
        encryption_info = analyzer.check_disk_encryption(instances)
        preemptible = analyzer.check_preemptible_instances(instances)
        
        # EIP使用情况
        eip_info = {"total": 0, "bound": 0, "unbound": 0, "unbound_eips": []}
        try:
            eips = provider.list_eips() if hasattr(provider, 'list_eips') else []
            if eips:
                eip_info = analyzer.analyze_eip_usage(eips)
        except:
            pass
        
        checks = []
        
        # 公网暴露检查
        if exposed:
            checks.append({
                "type": "public_exposure",
                "title": "公网暴露检测",
                "description": "检测到有资源暴露在公网，存在安全风险",
                "status": "failed",
                "severity": "HIGH",
                "count": len(exposed),
                "resources": exposed[:20],
                "recommendation": "评估是否真的需要公网访问，配置安全组白名单限制访问源，考虑使用 NAT 网关或 SLB",
            })
        else:
            checks.append({
                "type": "public_exposure",
                "title": "公网暴露检测",
                "description": "未发现公网暴露的资源",
                "status": "passed",
                "severity": "INFO",
                "count": 0,
                "resources": [],
            })
        
        # 停止实例检查
        if stopped:
            checks.append({
                "type": "stopped_instances",
                "title": "停止实例检测",
                "description": "检测到长期停止的实例，仍产生磁盘费用",
                "status": "warning",
                "severity": "MEDIUM",
                "count": len(stopped),
                "resources": stopped[:20],
                "recommendation": "评估是否需要这些实例，如不需要建议释放以节省成本",
            })
        else:
            checks.append({
                "type": "stopped_instances",
                "title": "停止实例检测",
                "description": "未发现长期停止的实例",
                "status": "passed",
                "severity": "INFO",
                "count": 0,
                "resources": [],
            })
        
        # 标签检查
        checks.append({
            "type": "tag_coverage",
            "title": "标签覆盖率检查",
            "description": "检查资源标签完整性，影响成本分摊和管理",
            "status": "passed" if tag_coverage >= 80 else "warning",
            "severity": "MEDIUM" if tag_coverage < 80 else "INFO",
            "coverage": tag_coverage,
            "missing_count": len(no_tags),
            "resources": no_tags[:20],
            "recommendation": f"当前标签覆盖率为 {tag_coverage}%，建议完善资源标签以便于管理和成本分摊",
        })
        
        # 磁盘加密检查
        encryption_rate = encryption_info.get("encryption_rate", 100)
        if encryption_rate < 100:
            checks.append({
                "type": "disk_encryption",
                "title": "磁盘加密检查",
                "description": "检查实例磁盘加密状态",
                "status": "warning" if encryption_rate < 50 else "passed",
                "severity": "HIGH" if encryption_rate < 50 else "MEDIUM",
                "encryption_rate": encryption_rate,
                "encrypted_count": encryption_info.get("encrypted", 0),
                "unencrypted_count": encryption_info.get("unencrypted_count", 0),
                "resources": encryption_info.get("unencrypted_instances", [])[:20],
                "recommendation": f"当前加密率为 {encryption_rate}%，建议为所有实例启用磁盘加密以保护数据安全",
            })
        else:
            checks.append({
                "type": "disk_encryption",
                "title": "磁盘加密检查",
                "description": "所有实例已启用磁盘加密",
                "status": "passed",
                "severity": "INFO",
                "encryption_rate": encryption_rate,
                "encrypted_count": encryption_info.get("encrypted", 0),
                "unencrypted_count": 0,
                "resources": [],
            })
        
        # 抢占式实例检查
        if preemptible:
            checks.append({
                "type": "preemptible_instances",
                "title": "抢占式实例检查",
                "description": "检测到抢占式实例，生产环境不建议使用",
                "status": "warning",
                "severity": "MEDIUM",
                "count": len(preemptible),
                "resources": preemptible[:20],
                "recommendation": "抢占式实例可能随时被回收，生产环境建议使用包年包月或按量付费实例",
            })
        else:
            checks.append({
                "type": "preemptible_instances",
                "title": "抢占式实例检查",
                "description": "未发现抢占式实例",
                "status": "passed",
                "severity": "INFO",
                "count": 0,
                "resources": [],
            })
        
        # EIP使用情况检查
        if eip_info.get("total", 0) > 0:
            unbound_rate = eip_info.get("unbound_rate", 0)
            if unbound_rate > 20:
                checks.append({
                    "type": "eip_usage",
                    "title": "EIP使用情况检查",
                    "description": "检测到未绑定的EIP，产生不必要的费用",
                    "status": "warning",
                    "severity": "MEDIUM",
                    "total": eip_info.get("total", 0),
                    "bound": eip_info.get("bound", 0),
                    "unbound": eip_info.get("unbound", 0),
                    "unbound_rate": unbound_rate,
                    "resources": eip_info.get("unbound_eips", [])[:20],
                    "recommendation": f"发现 {eip_info.get('unbound', 0)} 个未绑定的EIP，建议释放以节省成本",
                })
            else:
                checks.append({
                    "type": "eip_usage",
                    "title": "EIP使用情况检查",
                    "description": "EIP使用情况良好",
                    "status": "passed",
                    "severity": "INFO",
                    "total": eip_info.get("total", 0),
                    "bound": eip_info.get("bound", 0),
                    "unbound": eip_info.get("unbound", 0),
                    "unbound_rate": unbound_rate,
                    "resources": [],
                })
        
        # 保存到缓存（24小时有效）
        cache_manager.set(resource_type="security_checks", account_name=account_name, data=checks)
        
        return {
            "success": True,
            "data": checks,
            "cached": False,
        }
    except Exception as e:
        return {
            "success": True,
            "data": [],
            "cached": False,
        }


# ==================== Phase 2: Optimization APIs ====================

@router.get("/optimization/suggestions")
def get_optimization_suggestions(account: Optional[str] = None, force_refresh: bool = Query(False, description="强制刷新缓存")):
    """获取优化建议（带24小时缓存）"""
    provider, account_name = _get_provider_for_account(account)
    
    # 初始化缓存管理器，TTL设置为24小时（86400秒）
    cache_manager = ResourceCacheManager(ttl_seconds=86400)
    
    # 尝试从缓存获取数据
    cached_result = None
    if not force_refresh:
        cached_result = cache_manager.get(resource_type="optimization_suggestions", account_name=account_name)
    
    # 如果缓存有效，直接使用缓存数据
    if cached_result is not None:
        return {
            "success": True,
            "data": cached_result,
            "cached": True,
        }
    
    try:
        from core.optimization_engine import OptimizationEngine
        from core.security_compliance import SecurityComplianceAnalyzer
        from core.cost_analyzer import CostAnalyzer
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        suggestions = []
        all_opportunities = []
        
        # 1. 使用 OptimizationEngine 分析优化机会
        try:
            engine = OptimizationEngine()
            opportunities = engine.analyze_optimization_opportunities(account_name)
            all_opportunities.extend(opportunities)
        except Exception as e:
            pass  # 如果失败，继续其他分析
        
        # 2. 闲置资源建议（基于真实成本）
        cache = CacheManager(ttl_seconds=86400)
        idle_data = cache.get("idle_result", account_name)
        if idle_data:
            # 计算真实节省潜力
            total_savings = 0.0
            if account_config:
                cost_map = _get_cost_map("ecs", account_config)
                for idle_item in idle_data:
                    instance_id = idle_item.get("instance_id") or idle_item.get("id")
                    if instance_id:
                        cost = cost_map.get(instance_id)
                        if cost is None:
                            cost = _estimate_monthly_cost_from_spec(idle_item.get("spec", ""), "ecs")
                        total_savings += cost
            
            suggestions.append({
                "type": "idle_resources",
                "category": "成本优化",
                "priority": "high",
                "title": "闲置资源优化",
                "description": f"发现 {len(idle_data)} 个闲置资源，CPU和内存利用率极低，建议释放或降配",
                "savings_potential": round(total_savings, 2),
                "resource_count": len(idle_data),
                "resources": idle_data[:10],  # 返回前10个
                "action": "release_or_downgrade",
                "recommendation": "评估资源使用情况，如确实不需要可释放，如需保留可考虑降配以节省成本",
            })
        
        # 3. 停止实例建议
        instances = provider.list_instances()
        analyzer = SecurityComplianceAnalyzer()
        stopped = analyzer.check_stopped_instances(instances)
        if stopped:
            # 计算停止实例的成本
            stopped_savings = 0.0
            if account_config:
                cost_map = _get_cost_map("ecs", account_config)
                for stop_item in stopped:
                    instance_id = stop_item.get("id")
                    if instance_id:
                        cost = cost_map.get(instance_id)
                        if cost is None:
                            cost = 300  # 默认估算
                        # 停止实例仍产生磁盘费用，假设可节省70%
                        stopped_savings += cost * 0.7
            
            suggestions.append({
                "type": "stopped_instances",
                "category": "成本优化",
                "priority": "medium",
                "title": "停止实例优化",
                "description": f"发现 {len(stopped)} 个长期停止的实例，仍产生磁盘费用",
                "savings_potential": round(stopped_savings, 2),
                "resource_count": len(stopped),
                "resources": stopped[:10],
                "action": "release",
                "recommendation": "评估是否需要这些实例，如不需要建议释放以节省磁盘费用",
            })
        
        # 4. 未绑定EIP建议
        try:
            eips = provider.list_eips() if hasattr(provider, 'list_eips') else []
            if eips:
                eip_info = analyzer.analyze_eip_usage(eips)
                unbound_eips = eip_info.get("unbound_eips", [])
                if unbound_eips:
                    # EIP 费用估算：每个未绑定EIP约20元/月
                    eip_savings = len(unbound_eips) * 20
                    suggestions.append({
                        "type": "unbound_eips",
                        "category": "成本优化",
                        "priority": "high",
                        "title": "未绑定EIP优化",
                        "description": f"发现 {len(unbound_eips)} 个未绑定的EIP，产生不必要的费用",
                        "savings_potential": eip_savings,
                        "resource_count": len(unbound_eips),
                        "resources": unbound_eips[:10],
                        "action": "release",
                        "recommendation": "未绑定的EIP持续产生费用，建议释放以节省成本",
                    })
        except:
            pass
        
        # 5. 标签完善建议
        tag_coverage, no_tags = analyzer.check_missing_tags(instances)
        if len(no_tags) > 0:
            suggestions.append({
                "type": "missing_tags",
                "category": "资源管理",
                "priority": "medium",
                "title": "标签完善",
                "description": f"发现 {len(no_tags)} 个资源缺少标签，影响成本分摊和资源管理",
                "savings_potential": 0,
                "resource_count": len(no_tags),
                "resources": no_tags[:10],
                "action": "add_tags",
                "recommendation": "为资源添加标签（如：Environment、Project、Owner等）以便于成本分摊和资源管理",
            })
        
        # 6. 规格降配建议（从 OptimizationEngine 获取）
        downgrade_opportunities = [opp for opp in all_opportunities if opp.get("action") == "downgrade"]
        if downgrade_opportunities:
            total_downgrade_savings = sum(opp.get("estimated_savings", 0) for opp in downgrade_opportunities)
            suggestions.append({
                "type": "spec_downgrade",
                "category": "成本优化",
                "priority": "medium",
                "title": "规格降配建议",
                "description": f"发现 {len(downgrade_opportunities)} 个实例可降配，资源利用率较低",
                "savings_potential": round(total_downgrade_savings, 2),
                "resource_count": len(downgrade_opportunities),
                "resources": downgrade_opportunities[:10],
                "action": "downgrade",
                "recommendation": "根据实际使用情况降配实例规格，可节省约30%成本",
            })
        
        # 7. 公网暴露优化建议
        exposed = analyzer.detect_public_exposure(instances)
        if exposed:
            suggestions.append({
                "type": "public_exposure",
                "category": "安全优化",
                "priority": "high",
                "title": "公网暴露优化",
                "description": f"发现 {len(exposed)} 个资源暴露在公网，存在安全风险",
                "savings_potential": 0,
                "resource_count": len(exposed),
                "resources": exposed[:10],
                "action": "secure",
                "recommendation": "评估是否真的需要公网访问，配置安全组白名单，考虑使用 NAT 网关或 SLB",
            })
        
        # 8. 磁盘加密建议
        encryption_info = analyzer.check_disk_encryption(instances)
        if encryption_info.get("encryption_rate", 100) < 50:
            suggestions.append({
                "type": "disk_encryption",
                "category": "安全优化",
                "priority": "high",
                "title": "磁盘加密优化",
                "description": f"发现 {encryption_info.get('unencrypted_count', 0)} 个实例未启用磁盘加密",
                "savings_potential": 0,
                "resource_count": encryption_info.get("unencrypted_count", 0),
                "resources": encryption_info.get("unencrypted_instances", [])[:10],
                "action": "enable_encryption",
                "recommendation": "为所有实例启用磁盘加密以保护数据安全，符合合规要求",
            })
        
        # 按优先级和节省潜力排序
        suggestions.sort(key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "low"), 2),
            -x.get("savings_potential", 0)
        ))
        
        # 计算总节省潜力
        total_savings = sum(s.get("savings_potential", 0) for s in suggestions)
        
        result = {
            "suggestions": suggestions,
            "summary": {
                "total_suggestions": len(suggestions),
                "total_savings_potential": round(total_savings, 2),
                "high_priority_count": sum(1 for s in suggestions if s.get("priority") == "high"),
                "medium_priority_count": sum(1 for s in suggestions if s.get("priority") == "medium"),
                "low_priority_count": sum(1 for s in suggestions if s.get("priority") == "low"),
            }
        }
        
        # 保存到缓存（24小时有效）
        cache_manager.set(resource_type="optimization_suggestions", account_name=account_name, data=result)
        
        return {
            "success": True,
            "data": result,
            "cached": False,
        }
    except Exception as e:
        return {
            "success": True,
            "data": {
                "suggestions": [],
                "summary": {
                    "total_suggestions": 0,
                    "total_savings_potential": 0,
                    "high_priority_count": 0,
                    "medium_priority_count": 0,
                    "low_priority_count": 0,
                }
            },
            "cached": False,
        }


# ==================== Phase 3: Reports APIs ====================

@router.post("/reports/generate")
def generate_report(report_data: Dict[str, Any]):
    """生成报告"""
    account = report_data.get("account")
    report_type = report_data.get("type", "comprehensive")
    format_type = report_data.get("format", "excel")
    
    try:
        from core.report_generator import ReportGenerator
        
        provider, account_name = _get_provider_for_account(account)
        instances = provider.list_instances()
        rds_list = provider.list_rds()
        
        # 构建报告数据
        data = {
            "account": account_name,
            "instances": instances,
            "rds": rds_list,
        }
        
        if format_type == "html":
            report_content = ReportGenerator.generate_html(account_name, data)
            return {
                "success": True,
                "data": {
                    "format": "html",
                    "content": report_content,
                }
            }
        elif format_type == "excel":
            # TODO: 实现Excel生成
            return {
                "success": True,
                "data": {
                    "format": "excel",
                    "message": "Excel报告生成功能开发中",
                }
            }
        else:
            raise HTTPException(status_code=400, detail=f"不支持的格式: {format_type}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# Additional API endpoints to append to api.py

# ==================== Phase 2: Budget Management APIs ====================

@router.get("/cost/budget")
def get_budget(account: Optional[str] = None):
    """获取预算信息"""
    # TODO: 实现预算存储和查询（可以使用文件或数据库）
    return {
        "success": True,
        "data": {
            "monthly_budget": 0,
            "annual_budget": 0,
            "current_month_spent": 0,
            "usage_rate": 0,
        }
    }


# ==================== Billing APIs (BSS OpenAPI) ====================

@router.get("/billing/overview")
def get_billing_overview(
    account: str,
    billing_cycle: Optional[str] = Query(None, description="账期，格式 yyyy-MM，默认当月"),
    product_code: Optional[str] = Query(None, description="产品代码过滤（可选）"),
    subscription_type: Optional[str] = Query(None, description="订阅类型过滤：Subscription / PayAsYouGo（可选）"),
):
    """
    获取账单概览（阿里云 BSS OpenAPI）。

    用途：
    - 验证当前账号 AK 是否具备账单读取权限
    - 为后续“按实例真实成本（含折扣）”打通数据源
    """
    cm = ConfigManager()
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"Account '{account}' not found")

    provider = getattr(account_config, "provider", None) or "aliyun"
    if provider != "aliyun":
        raise HTTPException(status_code=400, detail="当前仅支持阿里云账单（BSS OpenAPI）")

    # 默认当月账期
    if not billing_cycle:
        from datetime import datetime
        billing_cycle = datetime.now().strftime("%Y-%m")

    # 动态导入：避免在未安装 SDK 的环境下直接 import 失败
    try:
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkcore.request import CommonRequest
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"阿里云 SDK 不可用：{e}")

    try:
        import json

        # BSS OpenAPI 不区分地域，但 SDK 需要 region 参数
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
        if product_code:
            request.add_query_param("ProductCode", product_code)
        if subscription_type:
            request.add_query_param("SubscriptionType", subscription_type)

        resp = client.do_action_with_exception(request)
        data = json.loads(resp)
        return {"success": True, "data": data}
    except Exception as e:
        # 常见：UnauthorizedOperation / Forbidden / InvalidAccessKeyId.NotFound / SignatureDoesNotMatch
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/billing/instance-bill")
def get_billing_instance_bill(
    account: str,
    billing_cycle: Optional[str] = Query(None, description="账期 yyyy-MM，默认当月"),
    product_code: str = Query(..., description="产品代码，如 ecs/rds/kvstore/yundisk/snapshot/slb/eip/nat_gw"),
    subscription_type: Optional[str] = Query(None, description="Subscription / PayAsYouGo（可选）"),
    limit: int = Query(50, ge=1, le=500, description="返回前 N 条用于调试"),
):
    """
    调试接口：拉取 BSS QueryInstanceBill 原始数据，便于确认 InstanceID 的字段与格式。
    """
    cm = ConfigManager()
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"Account '{account}' not found")
    provider = getattr(account_config, "provider", None) or "aliyun"
    if provider != "aliyun":
        raise HTTPException(status_code=400, detail="当前仅支持阿里云账单（BSS OpenAPI）")

    if not billing_cycle:
        billing_cycle = _get_billing_cycle_default()

    try:
        rows = _bss_query_instance_bill(
            account_config=account_config,
            billing_cycle=billing_cycle,
            product_code=product_code,
            subscription_type=subscription_type,
        )
        return {
            "success": True,
            "data": {
                "billing_cycle": billing_cycle,
                "product_code": product_code,
                "subscription_type": subscription_type,
                "count": len(rows),
                "items": rows[:limit],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discounts/trend")
def get_discount_trend(
    account: Optional[str] = Query(None, description="账号名称"),
    months: int = Query(19, ge=1, le=999, description="分析月数，默认19个月，设置为99或更大表示全部历史数据"),
    force_refresh: bool = Query(False, description="强制刷新缓存"),
):
    """
    折扣趋势分析 - 基于数据库全量数据分析
    
    数据来源：SQLite数据库（自动同步最新账单数据）
    支持：
    - 查看长期折扣趋势（最多19个月历史）
    - 分析商务合同折扣效果
    - 按产品/实例/合同维度查看折扣分布
    - 实时更新，无需手动下载CSV
    """
    from core.discount_analyzer_db import DiscountAnalyzerDB
    import os
    
    try:
        # 获取账号信息
        cm = ConfigManager()
        if not account:
            # 尝试获取当前账号
            ctx = ContextManager()
            account = ctx.get_last_account()
        if not account:
            # 使用第一个账号
            accounts = cm.list_accounts()
            if accounts:
                account = accounts[0].name
            else:
                raise HTTPException(status_code=400, detail="未找到账号配置")
        
        account_config = cm.get_account(account)
        if not account_config:
            raise HTTPException(status_code=404, detail=f"账号 '{account}' 不存在")
        
        # 生成账号ID（与bill_fetcher保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        # 使用数据库版折扣分析器
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = DiscountAnalyzerDB(db_path=db_path)
        
        # 分析折扣趋势
        result = analyzer.analyze_discount_trend(
            account_id=account_id,
            months=months
        )
        
        if 'error' in result:
            return {
                "success": False,
                "error": result['error']
            }
        
        # 转换数据格式以匹配前端期望的结构
        from datetime import datetime
        
        # 提取数据
        monthly_trend = result.get('monthly_trend', [])
        product_discounts = result.get('product_discounts', [])
        instance_discounts = result.get('instance_discounts', [])
        contract_discounts = result.get('contract_discounts', [])
        summary = result.get('summary', {})
        
        # 构建前端期望的数据结构
        response_data = {
            "account_name": account,
            "analysis_periods": [m['month'] for m in monthly_trend],
            
            # trend_analysis 格式
            "trend_analysis": {
                "timeline": [
                    {
                        "period": m['month'],
                        "official_price": m['official_price'],
                        "discount_amount": m['discount_amount'],
                        "discount_rate": m['discount_rate'],
                        "payable_amount": m['actual_amount']
                    }
                    for m in monthly_trend
                ],
                "latest_period": monthly_trend[-1]['month'] if monthly_trend else "",
                "latest_discount_rate": summary.get('latest_discount_rate', 0),
                "discount_rate_change": summary.get('trend_change_pct', 0) / 100,
                "discount_rate_change_pct": summary.get('trend_change_pct', 0),
                "discount_amount_change": 0,  # 可以计算
                "trend_direction": summary.get('trend', '平稳'),
                "average_discount_rate": summary.get('avg_discount_rate', 0),
                "max_discount_rate": max([m['discount_rate'] for m in monthly_trend], default=0),
                "min_discount_rate": min([m['discount_rate'] for m in monthly_trend], default=0),
                "total_savings_6m": summary.get('total_discount', 0),
            },
            
            # product_analysis 格式
            "product_analysis": {
                p['product']: {
                    "total_discount": p['discount_amount'],
                    "avg_discount_rate": p['discount_rate'],
                    "latest_discount_rate": p['discount_rate'],
                    "rate_change": 0,
                    "trend": "平稳",
                    "periods": [m['month'] for m in monthly_trend],
                    "discount_rates": [p['discount_rate']] * len(monthly_trend),
                }
                for p in product_discounts
            },
            
            # contract_analysis 格式（如果有合同数据）
            "contract_analysis": {
                c['contract_name']: {
                    "discount_name": c['contract_name'],
                    "total_discount": c.get('total_discount', 0),
                    "avg_discount_rate": c.get('avg_discount_rate', 0),
                    "latest_discount_rate": c.get('latest_discount_rate', 0),
                    "periods": c.get('periods', []),
                    "discount_amounts": c.get('discount_amounts', []),
                }
                for c in contract_discounts
            },
            
            # top_instance_discounts 格式
            "top_instance_discounts": [
                {
                    "instance_id": i['instance_id'],
                    "instance_name": i.get('instance_name', i['instance_id']),
                    "product_name": i['product'],
                    "official_price": i['official_price'],
                    "discount_amount": i['discount_amount'],
                    "payable_amount": i['actual_amount'],
                    "discount_rate": i['discount_rate'],
                    "discount_pct": i['discount_rate'] * 100,
                }
                for i in instance_discounts
            ],
            
            "generated_at": datetime.now().isoformat(),
        }
        
        return {
            "success": True,
            "data": response_data,
            "cached": False,
            "source": "database",
            "account": account,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discounts/products")
def get_product_discounts(
    account: Optional[str] = Query(None, description="账号名称"),
    product: Optional[str] = Query(None, description="产品名称过滤"),
    months: int = Query(19, ge=1, le=999, description="分析月数，设置为99或更大表示全部历史数据"),
    force_refresh: bool = Query(False, description="强制刷新缓存"),
):
    """
    产品折扣详情 - 基于数据库查看特定产品的折扣明细
    """
    from core.discount_analyzer_db import DiscountAnalyzerDB
    import os
    
    try:
        # 获取账号信息
        cm = ConfigManager()
        if not account:
            ctx = ContextManager()
            account = ctx.get_last_account()
        if not account:
            accounts = cm.list_accounts()
            if accounts:
                account = accounts[0].name
            else:
                raise HTTPException(status_code=400, detail="未找到账号配置")
        
        account_config = cm.get_account(account)
        if not account_config:
            raise HTTPException(status_code=404, detail=f"账号 '{account}' 不存在")
        
        # 生成账号ID
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        # 使用数据库版折扣分析器
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = DiscountAnalyzerDB(db_path=db_path)
        
        result = analyzer.analyze_discount_trend(account_id=account_id, months=months)
        
        if 'error' in result:
            return {"success": False, "error": result['error']}
        
        # 提取产品折扣数据
        product_data = result['product_analysis']
        
        # 如果指定了产品过滤
        if product:
            product_data = {k: v for k, v in product_data.items() if product.lower() in k.lower()}
        
        return {
            "success": True,
            "data": {
                "products": product_data,
                "analysis_periods": result['analysis_periods'],
            },
            "source": "database",
            "account": account,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/billing/discounts")
def get_billing_discounts(
    account: str,
    billing_cycle: Optional[str] = Query(None, description="账期 yyyy-MM，默认当月"),
    force_refresh: bool = Query(False, description="强制刷新缓存"),
):
    """
    折扣梳理（按产品 + 计费方式聚合）- 基于BSS API实时查询
    
    注意：这是实时API接口，与 /discounts/trend（基于CSV离线分析）互补。
    - 实时API：查询当前月折扣情况
    - CSV分析：查看历史6个月折扣趋势

    口径说明：
    - PretaxGrossAmount：税前原价（未折扣/未优惠抵扣前）
    - PretaxAmount：税前应付（折扣/优惠抵扣后）
    - 对 PayAsYouGo，PaymentAmount 常为 0（未出账/未结算），请以 PretaxAmount/OutstandingAmount 为主
    """
    cm = ConfigManager()
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"Account '{account}' not found")
    provider = getattr(account_config, "provider", None) or "aliyun"
    if provider != "aliyun":
        raise HTTPException(status_code=400, detail="当前仅支持阿里云账单（BSS OpenAPI）")

    if not billing_cycle:
        billing_cycle = _get_billing_cycle_default()

    cache_manager = ResourceCacheManager(ttl_seconds=86400)
    cache_key = f"billing_discounts_{billing_cycle}"
    if not force_refresh:
        cached = cache_manager.get(resource_type=cache_key, account_name=account_config.name)
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
        code = (it.get("ProductCode") or it.get("PipCode") or "unknown")
        sub = (it.get("SubscriptionType") or "Unknown")
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

        # “没有使用/没有发生费用”的产品不展示：所有金额字段均为 0
        # 注意：如果是“免单/全额减免”，一般表现为 gross>0 但 pretax=0，这种要展示为“免费”
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
        # 折扣口径：按“实付比例”计算折扣（x.x折），例如 30/100 => 0.3 => 3.0折
        # 注意：0.0折通常意味着“全额减免/完全被优惠抵扣”，不应展示为 0.0折，改用 free 标识在前端展示“免费”
        discount_rate = (pretax / gross) if gross > 0 else None
        is_free = (gross > 0 and pretax == 0)
        discount_zhe = (float(discount_rate) * 10.0) if (discount_rate is not None and pretax > 0) else None
        row["pretax_gross_amount"] = round(gross, 2)
        row["pretax_amount"] = round(pretax, 2)
        row["discount_amount"] = round(discount_amount, 2)
        row["discount_rate"] = round(float(discount_rate), 6) if discount_rate is not None else None
        row["discount_pct"] = round((1.0 - float(discount_rate)) * 100, 2) if discount_rate is not None else None
        row["discount_zhe"] = round(float(discount_zhe), 1) if discount_zhe is not None else None
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
    overall_free = (total_gross > 0 and total_pretax == 0)
    overall_zhe = (float(overall_rate) * 10.0) if (overall_rate is not None and total_pretax > 0) else None
    result = {
        "billing_cycle": billing_cycle,
        "summary": {
            "total_pretax_gross_amount": round(total_gross, 2),
            "total_pretax_amount": round(total_pretax, 2),
            "total_discount_amount": round(total_discount_amount, 2),
            "discount_rate": round(float(overall_rate), 6) if overall_rate is not None else None,
            "discount_pct": round((1.0 - float(overall_rate)) * 100, 2) if overall_rate is not None else None,
            "discount_zhe": round(float(overall_zhe), 1) if overall_zhe is not None else None,
            "free": bool(overall_free),
        },
        "rows": rows,
    }

    cache_manager.set(resource_type=cache_key, account_name=account_config.name, data=result)
    return {"success": True, "data": result, "cached": False}


@router.post("/cost/budget")
def set_budget(budget_data: Dict[str, Any]):
    """设置预算"""
    # TODO: 实现预算保存
    return {
        "success": True,
        "message": "预算设置成功"
    }


# ==================== Phase 2: CIS Compliance APIs ====================

@router.get("/security/cis")
def get_cis_compliance(account: Optional[str] = None):
    """获取CIS合规检查结果"""
    provider, account_name = _get_provider_for_account(account)
    
    try:
        from core.cis_compliance import CISBenchmark
        
        # 获取资源
        instances = provider.list_instances()
        rds_list = provider.list_rds()
        all_resources = instances + rds_list
        
        # 运行CIS检查
        checker = CISBenchmark()
        results = checker.run_all_checks(all_resources, provider)
        
        # 计算合规度
        total_checks = len(results.get("results", []))
        passed_checks = sum(1 for check in results.get("results", []) if check.get("status") == "PASS")
        compliance_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        return {
            "success": True,
            "data": {
                "compliance_rate": round(compliance_rate, 2),
                "checks": results.get("results", []),
                "summary": results.get("summary", {}),
            }
        }
    except Exception as e:
        # 如果CIS检查器不存在或出错，返回提示
        return {
            "success": True,
            "data": {
                "compliance_rate": 0,
                "checks": [],
                "message": f"CIS合规检查功能开发中: {str(e)}"
            }
        }




@router.get("/reports")
def list_reports(account: Optional[str] = None, limit: int = Query(50, ge=1, le=100)):
    """获取报告历史列表"""
    # TODO: 实现报告历史存储和查询
    return {
        "success": True,
        "data": []
    }


# ==================== Phase 1: 高级折扣分析API ====================

@router.get("/discounts/quarterly")
def get_quarterly_discount_comparison(
    account: Optional[str] = Query(None, description="账号名称"),
    quarters: int = Query(8, ge=1, le=20, description="分析季度数"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM格式)"),
):
    """
    季度折扣对比分析
    
    返回季度维度的折扣率、消费金额、环比变化等数据
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.get_quarterly_comparison(account_id, quarters, start_date, end_date)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        return {
            "success": True,
            "data": result,
            "account": account,
            "source": "database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"季度对比分析失败: {str(e)}")


@router.get("/discounts/yearly")
def get_yearly_discount_comparison(
    account: Optional[str] = Query(None, description="账号名称"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM格式)"),
):
    """
    年度折扣对比分析
    
    返回年度维度的折扣率、消费金额、同比变化等数据
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.get_yearly_comparison(account_id, start_date, end_date)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        return {
            "success": True,
            "data": result,
            "account": account,
            "source": "database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"年度对比分析失败: {str(e)}")


@router.get("/discounts/product-trends")
def get_product_discount_trends(
    account: Optional[str] = Query(None, description="账号名称"),
    months: int = Query(19, ge=1, le=999, description="分析月数"),
    top_n: int = Query(20, ge=1, le=50, description="TOP N产品"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM格式)"),
):
    """
    产品折扣趋势分析
    
    返回每个产品的月度折扣趋势、波动率、趋势变化等数据
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.get_product_discount_trends(account_id, months, top_n, start_date, end_date)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        return {
            "success": True,
            "data": result,
            "account": account,
            "source": "database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"产品趋势分析失败: {str(e)}")


@router.get("/discounts/regions")
def get_region_discount_ranking(
    account: Optional[str] = Query(None, description="账号名称"),
    months: int = Query(19, ge=1, le=999, description="分析月数"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM格式)"),
):
    """
    区域折扣排行分析
    
    返回各区域的折扣率、消费金额、实例数等数据
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.get_region_discount_ranking(account_id, months, start_date, end_date)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        return {
            "success": True,
            "data": result,
            "account": account,
            "source": "database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"区域排行分析失败: {str(e)}")


@router.get("/discounts/subscription-types")
def get_subscription_type_comparison(
    account: Optional[str] = Query(None, description="账号名称"),
    months: int = Query(19, ge=1, le=999, description="分析月数"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM格式)"),
):
    """
    计费方式对比分析（包年包月 vs 按量付费）
    
    返回不同计费方式的折扣率、消费金额、实例数对比，以及月度趋势
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.get_subscription_type_comparison(account_id, months, start_date, end_date)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        return {
            "success": True,
            "data": result,
            "account": account,
            "source": "database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计费方式对比分析失败: {str(e)}")


@router.get("/discounts/optimization-suggestions")
def get_optimization_suggestions(
    account: Optional[str] = Query(None, description="账号名称"),
    min_running_months: int = Query(6, ge=1, le=24, description="最少运行月数"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM格式)"),
):
    """
    优化建议：识别长期运行的按量付费实例
    
    返回建议转为包年包月的实例列表及潜在节省金额
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.get_optimization_suggestions(account_id, min_running_months, start_date, end_date)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        return {
            "success": True,
            "data": result,
            "account": account,
            "source": "database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"优化建议生成失败: {str(e)}")


@router.get("/discounts/anomalies")
def detect_discount_anomalies(
    account: Optional[str] = Query(None, description="账号名称"),
    months: int = Query(19, ge=1, le=999, description="分析月数"),
    threshold: float = Query(0.10, ge=0.01, le=0.50, description="异常阈值"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM格式)"),
):
    """
    折扣异常检测
    
    识别折扣率波动异常的月份（环比变化超过阈值）
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.detect_anomalies(account_id, months, threshold, start_date, end_date)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        return {
            "success": True,
            "data": result,
            "account": account,
            "source": "database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"异常检测失败: {str(e)}")


# ==================== Phase 2: 交叉维度分析API ====================

@router.get("/discounts/product-region-matrix")
def get_product_region_matrix(
    account: Optional[str] = Query(None, description="账号名称"),
    top_products: int = Query(10, ge=1, le=20, description="TOP N产品"),
    top_regions: int = Query(10, ge=1, le=20, description="TOP N区域"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM格式)"),
):
    """
    产品 × 区域交叉分析矩阵
    
    返回产品和区域交叉维度的折扣率热力图数据
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.get_product_region_matrix(account_id, top_products, top_regions, start_date, end_date)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        return {
            "success": True,
            "data": result,
            "account": account,
            "source": "database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"产品×区域矩阵分析失败: {str(e)}")


@router.get("/discounts/moving-average")
def get_discount_moving_average(
    account: Optional[str] = Query(None, description="账号名称"),
    windows: str = Query("3,6,12", description="移动窗口大小（逗号分隔）"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM格式)"),
):
    """
    折扣率移动平均分析
    
    返回不同窗口大小的移动平均数据，用于平滑趋势
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        # 解析窗口大小
        window_sizes = [int(w.strip()) for w in windows.split(',')]
        
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.get_moving_average(account_id, window_sizes, start_date, end_date)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        return {
            "success": True,
            "data": result,
            "account": account,
            "source": "database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"移动平均分析失败: {str(e)}")


@router.get("/discounts/cumulative")
def get_cumulative_discount(
    account: Optional[str] = Query(None, description="账号名称"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM格式)"),
):
    """
    累计折扣金额分析
    
    返回折扣金额的累计爬升曲线数据
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.get_cumulative_discount(account_id, start_date, end_date)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        return {
            "success": True,
            "data": result,
            "account": account,
            "source": "database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"累计折扣分析失败: {str(e)}")


@router.get("/discounts/instance-lifecycle")
def get_instance_lifecycle(
    account: Optional[str] = Query(None, description="账号名称"),
    top_n: int = Query(50, ge=1, le=100, description="TOP N实例"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM格式)"),
):
    """
    实例生命周期分析
    
    分析每个实例的生命周期折扣变化
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.get_instance_lifecycle_analysis(account_id, top_n, start_date, end_date)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        return {
            "success": True,
            "data": result,
            "account": account,
            "source": "database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"实例生命周期分析失败: {str(e)}")


# ==================== Phase 3: 智能分析与导出API ====================

@router.get("/discounts/insights")
def get_discount_insights(
    account: Optional[str] = Query(None, description="账号名称"),
):
    """
    智能洞察生成
    
    基于历史数据自动生成分析洞察和建议
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.generate_insights(account_id)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
        
        return {
            "success": True,
            "data": result,
            "account": account,
            "source": "database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能洞察生成失败: {str(e)}")


@router.get("/discounts/export")
def export_discount_data(
    account: Optional[str] = Query(None, description="账号名称"),
    export_type: str = Query("all", description="导出类型: all, products, regions, instances"),
):
    """
    导出折扣数据为CSV
    
    支持导出产品、区域、实例等维度的数据
    """
    import os
    from core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    from fastapi.responses import Response
    
    cm = ConfigManager()
    
    # 解析账号
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未找到任何账号配置")
        account = accounts[0].name if isinstance(accounts[0], CloudAccount) else accounts[0].get('name')
    
    account_config = cm.get_account(account)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"账号 '{account}' 未找到")
    
    try:
        db_path = os.path.expanduser("~/.cloudlens/bills.db")
        analyzer = AdvancedDiscountAnalyzer(db_path)
        
        # 构造账号ID（与bill_cmd.py保持一致）
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        result = analyzer.export_to_csv(account_id, export_type)
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '导出失败'))
        
        # 返回CSV文件
        from datetime import datetime
        filename = f"discount_analysis_{account}_{export_type}_{datetime.now().strftime('%Y%m%d')}.csv"
        
        return Response(
            content=result['csv_content'].encode('utf-8-sig'),  # BOM for Excel compatibility
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据导出失败: {str(e)}")
