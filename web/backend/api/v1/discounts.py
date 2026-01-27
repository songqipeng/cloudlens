from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging
import hashlib
import json
import random
from datetime import datetime, timedelta

from web.backend.api_base import handle_api_error
from cloudlens.core.config import ConfigManager, CloudAccount
from cloudlens.core.context import ContextManager
from cloudlens.cli.utils import is_mock_mode

logger = logging.getLogger(__name__)

# 使用固定种子确保Mock数据一致性
random.seed(42)

router = APIRouter(prefix="/api")

# Redis缓存客户端（懒加载）
_redis_client = None
CACHE_TTL = 1800  # 30分钟缓存（折扣数据更新频率低，延长缓存时间）


def _get_redis():
    """获取Redis客户端"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            import os
            _redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "cloudlens-redis"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=0, decode_responses=True,
                socket_connect_timeout=5, socket_timeout=10
            )
            _redis_client.ping()
            logger.info("Redis缓存已连接")
        except Exception as e:
            logger.warning(f"Redis不可用: {e}")
            _redis_client = False  # 标记为不可用
    return _redis_client if _redis_client else None


def _cache_get(key: str):
    """从缓存获取"""
    r = _get_redis()
    if r:
        try:
            data = r.get(key)
            if data:
                logger.info(f"缓存命中: {key}")
                return json.loads(data)
            else:
                logger.info(f"缓存未命中: {key}")
        except Exception as e:
            logger.warning(f"缓存读取失败: {e}")
    return None


def _cache_set(key: str, value: Any, ttl: int = CACHE_TTL):
    """设置缓存"""
    r = _get_redis()
    if r:
        try:
            r.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")


# ==================== 辅助函数 (Billing & Providers) ====================

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
    return datetime.now().strftime("%Y-%m")


def _bss_query_bill_overview(account_config: CloudAccount, billing_cycle: str) -> List[Dict[str, Any]]:
    """调用阿里云 BSS OpenAPI QueryBillOverview"""
    try:
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkcore.request import CommonRequest
    except Exception as e:
        raise RuntimeError(f"阿里云 SDK 不可用：{e}")

    import json
    client = AcsClient(account_config.access_key_id, account_config.access_key_secret, "cn-hangzhou")
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


# ==================== 折扣分析端点 ====================

def _get_account_id(account_config, account_name: str) -> str:
    """
    构造统一的 account_id 格式。
    重要：必须与 BillFetcher 存储时使用的格式一致！
    格式：{access_key_id前10位}-{account_name}
    """
    return f"{account_config.access_key_id[:10]}-{account_name}"


# ==================== Mock 数据生成函数 ====================

def _generate_mock_quarterly_data(quarters: int = 8) -> Dict[str, Any]:
    """生成Mock季度折扣数据"""
    quarters_list = []
    today = datetime.now()
    
    for i in range(quarters):
        quarter_date = today - timedelta(days=90 * (quarters - i))
        year = quarter_date.year
        quarter = (quarter_date.month - 1) // 3 + 1
        period = f"{year}Q{quarter}"
        
        # 基础数据：月均500万，季度约1500万
        base_total = 15000000
        variation = random.uniform(-0.1, 0.1)
        total_pretax = base_total * (1 + variation)
        
        # 折扣率：25%-35%
        avg_discount_rate = random.uniform(0.25, 0.35)
        total_discount = total_pretax * avg_discount_rate
        total_paid = total_pretax - total_discount
        
        quarters_list.append({
            "period": period,
            "year": year,
            "quarter": quarter,
            "month_count": 3,
            "total_pretax": total_pretax,
            "total_discount": total_discount,
            "total_paid": total_paid,
            "avg_discount_rate": avg_discount_rate,
            "rate_change": random.uniform(-2, 2),  # 环比变化
        })
    
    return {"quarters": quarters_list}


def _generate_mock_yearly_data() -> Dict[str, Any]:
    """生成Mock年度折扣数据"""
    years_list = []
    today = datetime.now()
    
    for i in range(3):  # 最近3年
        year = today.year - (2 - i)
        
        # 年度总成本：约6000万（500万*12）
        base_total = 60000000
        variation = random.uniform(-0.15, 0.15)
        total_pretax = base_total * (1 + variation)
        
        # 折扣率：25%-35%
        avg_discount_rate = random.uniform(0.25, 0.35)
        total_discount = total_pretax * avg_discount_rate
        total_paid = total_pretax - total_discount
        
        years_list.append({
            "year": year,
            "total_pretax": total_pretax,
            "total_discount": total_discount,
            "total_paid": total_paid,
            "avg_discount_rate": avg_discount_rate,
            "month_count": 12,
        })
    
    return {"years": years_list}


def _generate_mock_product_trends_data(months: int = 19, top_n: int = 10) -> Dict[str, Any]:
    """生成Mock产品折扣趋势数据"""
    products = [
        {"code": "ecs", "name": "云服务器 ECS"},
        {"code": "rds", "name": "云数据库RDS版"},
        {"code": "kvstore", "name": "云数据库Redis版"},
        {"code": "slb", "name": "负载均衡"},
        {"code": "eip", "name": "弹性公网IP"},
        {"code": "oss", "name": "对象存储OSS"},
        {"code": "vpc", "name": "专有网络VPC"},
        {"code": "nat", "name": "NAT网关"},
        {"code": "cdn", "name": "CDN"},
        {"code": "mongodb", "name": "MongoDB"},
    ]
    
    product_list = []
    today = datetime.now()
    
    for product in products[:top_n]:
        # 生成月度趋势
        trends = []
        total_consumption = 0
        total_discount = 0
        
        for i in range(months):
            month_date = today - timedelta(days=30 * (months - i))
            month = month_date.strftime("%Y-%m")
            
            # 月度成本
            base_cost = random.uniform(100000, 2000000)
            discount_rate = random.uniform(0.20, 0.40)  # 不同产品折扣不同
            discount_amount = base_cost * discount_rate
            paid_amount = base_cost - discount_amount
            
            total_consumption += paid_amount
            total_discount += discount_amount
            
            trends.append({
                "month": month,
                "consumption": paid_amount,
                "discount_rate": discount_rate,
                "discount_amount": discount_amount,
            })
        
        avg_discount_rate = total_discount / (total_consumption + total_discount) if (total_consumption + total_discount) > 0 else 0.3
        volatility = random.uniform(0.05, 0.15)  # 波动率
        trend_change_pct = random.uniform(-5, 5)  # 趋势变化
        
        product_list.append({
            "product_code": product["code"],
            "product_name": product["name"],
            "total_consumption": total_consumption,
            "total_discount": total_discount,
            "avg_discount_rate": avg_discount_rate,
            "volatility": volatility,
            "trend_change_pct": trend_change_pct,
            "trends": trends,
        })
    
    return {"products": product_list}


def _generate_mock_regions_data(months: int = 19) -> Dict[str, Any]:
    """生成Mock区域折扣数据"""
    regions = [
        {"code": "cn-hangzhou", "name": "华东1（杭州）"},
        {"code": "cn-shanghai", "name": "华东2（上海）"},
        {"code": "cn-beijing", "name": "华北2（北京）"},
        {"code": "cn-shenzhen", "name": "华南1（深圳）"},
        {"code": "cn-hongkong", "name": "香港"},
        {"code": "ap-southeast-1", "name": "亚太东南1（新加坡）"},
        {"code": "us-west-1", "name": "美国西部1（硅谷）"},
    ]
    
    region_list = []
    total_consumption = 0
    
    for region in regions:
        # 区域成本分配
        region_ratio = random.uniform(0.05, 0.30)
        total_paid = 5000000 * months * region_ratio
        total_consumption += total_paid
        
        # 折扣率
        avg_discount_rate = random.uniform(0.25, 0.35)
        total_discount = total_paid / (1 - avg_discount_rate) * avg_discount_rate
        
        region_list.append({
            "region_code": region["code"],
            "region_name": region["name"],
            "total_paid": total_paid,
            "total_discount": total_discount,
            "avg_discount_rate": avg_discount_rate,
            "instance_count": random.randint(50, 300),
            "product_count": random.randint(5, 12),
            "consumption_percentage": region_ratio * 100,
        })
    
    # 归一化百分比
    total_pct = sum(r["consumption_percentage"] for r in region_list)
    for r in region_list:
        r["consumption_percentage"] = (r["consumption_percentage"] / total_pct) * 100
    
    return {"regions": region_list}


def _generate_mock_subscription_types_data(months: int = 19) -> Dict[str, Any]:
    """生成Mock订阅类型折扣数据"""
    # 包年包月占比70%，按量付费30%
    subscription_total = 5000000 * months * 0.7
    payasyougo_total = 5000000 * months * 0.3
    
    subscription_discount_rate = random.uniform(0.30, 0.40)  # 包年包月折扣更高
    payasyougo_discount_rate = random.uniform(0.15, 0.25)  # 按量付费折扣较低
    
    subscription_discount = subscription_total / (1 - subscription_discount_rate) * subscription_discount_rate
    payasyougo_discount = payasyougo_total / (1 - payasyougo_discount_rate) * payasyougo_discount_rate
    
    return {
        "subscription_types": {
            "Subscription": {
                "total_paid": subscription_total,
                "total_discount": subscription_discount,
                "avg_discount_rate": subscription_discount_rate,
                "instance_count": random.randint(500, 800),
                "consumption_percentage": 70.0,
            },
            "PayAsYouGo": {
                "total_paid": payasyougo_total,
                "total_discount": payasyougo_discount,
                "avg_discount_rate": payasyougo_discount_rate,
                "instance_count": random.randint(200, 400),
                "consumption_percentage": 30.0,
            },
        },
        "rate_difference": subscription_discount_rate - payasyougo_discount_rate,
    }


def _generate_mock_optimization_suggestions() -> Dict[str, Any]:
    """生成Mock优化建议数据"""
    suggestions = []
    products = ["ecs", "rds", "kvstore", "slb", "eip"]
    regions = ["cn-hangzhou", "cn-shanghai", "cn-beijing", "cn-shenzhen"]
    
    for i in range(50):  # 50个优化建议
        product = random.choice(products)
        region = random.choice(regions)
        running_months = random.randint(3, 24)
        current_discount = random.uniform(0.15, 0.25)  # 当前折扣较低
        estimated_discount = random.uniform(0.30, 0.40)  # 预估折扣更高
        total_cost = random.uniform(10000, 100000)
        annual_savings = total_cost * 12 * (estimated_discount - current_discount)
        
        suggestions.append({
            "instance_id": f"{product}-mock-{i+1:06d}",
            "product_name": product.upper(),
            "region_name": region,
            "running_months": running_months,
            "total_cost": total_cost,
            "current_discount_rate": current_discount,
            "estimated_subscription_rate": estimated_discount,
            "annual_potential_savings": annual_savings,
        })
    
    total_savings = sum(s["annual_potential_savings"] for s in suggestions)
    
    return {
        "suggestions": suggestions,
        "total_suggestions": len(suggestions),
        "total_potential_savings": total_savings,
    }


def _generate_mock_anomalies_data(months: int = 19) -> Dict[str, Any]:
    """生成Mock异常检测数据"""
    anomalies = []
    today = datetime.now()
    
    # 随机生成几个异常月份
    for i in range(random.randint(2, 5)):
        month_date = today - timedelta(days=30 * random.randint(1, months))
        month = month_date.strftime("%Y-%m")
        change_pct = random.uniform(-20, -10) if random.random() > 0.5 else random.uniform(10, 20)
        severity = "严重" if abs(change_pct) > 15 else "一般"
        
        anomalies.append({
            "month": month,
            "change_pct": change_pct,
            "severity": severity,
            "description": f"折扣率异常波动 {change_pct:+.1f}%",
        })
    
    return {
        "anomalies": anomalies,
        "total_anomalies": len(anomalies),
    }


@router.get("/discounts/trend")
def get_discounts_trend(
    account: Optional[str] = Query(None, description="账号名称"),
    months: int = Query(19, ge=1, le=999, description="分析月数"),
    force_refresh: bool = Query(False, description="强制刷新缓存"),
):
    """折扣趋势分析"""
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        # Mock模式返回模拟数据
        if is_mock_mode() or account_config.provider == "mock":
            today = datetime.now()
            timeline = []
            total_discount = 0
            total_official = 0
            
            for i in range(months):
                month_date = today - timedelta(days=30 * (months - i))
                month = month_date.strftime("%Y-%m")
                
                # 基础月成本约500万
                base_total = 5000000
                variation = random.uniform(-0.15, 0.15)
                official_price = base_total * (1 + variation)
                
                # 折扣率：25%-35%
                discount_rate = random.uniform(0.25, 0.35)
                discount_amount = official_price * discount_rate
                payable_amount = official_price - discount_amount
                
                total_official += official_price
                total_discount += discount_amount
                
                timeline.append({
                    "period": month,
                    "official_price": official_price,
                    "discount_amount": discount_amount,
                    "discount_rate": discount_rate,
                    "payable_amount": payable_amount,
                })
            
            avg_discount_rate = total_discount / total_official if total_official > 0 else 0.3
            latest_discount_rate = timeline[-1]["discount_rate"] if timeline else 0.3
            
            response_data = {
                "account_name": account_name,
                "analysis_periods": [t["period"] for t in timeline],
                "trend_analysis": {
                    "timeline": timeline,
                    "latest_discount_rate": latest_discount_rate,
                    "trend_direction": "平稳",
                    "average_discount_rate": avg_discount_rate,
                    "total_savings_6m": sum(t["discount_amount"] for t in timeline[-6:]) if len(timeline) >= 6 else total_discount,
                },
                "generated_at": datetime.now().isoformat(),
            }
            
            return {"success": True, "data": response_data}
        
        # 构造账号ID（必须与数据同步时的格式一致）
        account_id = _get_account_id(account_config, account_name)
        
        from cloudlens.core.discount_analyzer_db import DiscountAnalyzerDB
        analyzer = DiscountAnalyzerDB()
        result = analyzer.analyze_discount_trend(account_id=account_id, months=months)
        
        if 'error' in result:
            return {"success": False, "error": result['error']}
        
        # 转换格式以匹配前端
        monthly_trend = result.get('monthly_trend', [])
        summary = result.get('summary', {})
        
        response_data = {
            "account_name": account_name,
            "analysis_periods": [m['month'] for m in monthly_trend],
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
                "latest_discount_rate": summary.get('latest_discount_rate', 0),
                "trend_direction": summary.get('trend', '平稳'),
                "average_discount_rate": summary.get('avg_discount_rate', 0),
                "total_savings_6m": summary.get('total_discount', 0),
            },
            "generated_at": datetime.now().isoformat(),
        }
        
        return {"success": True, "data": response_data}
    except Exception as e:
        raise handle_api_error(e, "get_discounts_trend")


@router.get("/discounts/products")
def get_discounts_by_products(
    account: Optional[str] = Query(None, description="账号名称"),
    months: int = Query(19, ge=1, le=999, description="分析月数"),
):
    """按产品统计折扣"""
    from cloudlens.core.discount_analyzer_db import DiscountAnalyzerDB
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        analyzer = DiscountAnalyzerDB()
        result = analyzer.analyze_discount_trend(account_id=account_id, months=months)
        
        return {
            "success": True, 
            "data": {
                "products": result.get('product_analysis', {}),
                "analysis_periods": [m['month'] for m in result.get('monthly_trend', [])]
            }
        }
    except Exception as e:
        raise handle_api_error(e, "get_discounts_by_products")


@router.get("/discounts/quarterly")
def get_discounts_quarterly(
    account: Optional[str] = None, 
    quarters: int = 8,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM")
):
    """季度折扣分析"""
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        # Mock模式返回模拟数据
        if is_mock_mode() or account_config.provider == "mock":
            result = _generate_mock_quarterly_data(quarters)
            return {"success": True, "data": result}
        
        account_id = _get_account_id(account_config, account_name)
        
        # 尝试从缓存获取
        cache_key = f"quarterly:{account_id}:{quarters}:{start_date}:{end_date}"
        cached = _cache_get(cache_key)
        if cached:
            return cached
        
        from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_quarterly_comparison(account_id, quarters, start_date, end_date)
        response = {"success": True, "data": result}
        _cache_set(cache_key, response)
        return response
    except Exception as e:
        raise handle_api_error(e, "get_discounts_quarterly")


@router.get("/discounts/yearly")
def get_discounts_yearly(
    account: Optional[str] = None,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM")
):
    """年度折扣分析"""
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        # Mock模式返回模拟数据
        if is_mock_mode() or account_config.provider == "mock":
            result = _generate_mock_yearly_data()
            return {"success": True, "data": result}
        
        account_id = _get_account_id(account_config, account_name)
        
        # 尝试从缓存获取
        cache_key = f"yearly:{account_id}:{start_date}:{end_date}"
        cached = _cache_get(cache_key)
        if cached:
            return cached
        
        from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_yearly_comparison(account_id, start_date, end_date)
        response = {"success": True, "data": result}
        _cache_set(cache_key, response)
        return response
    except Exception as e:
        raise handle_api_error(e, "get_discounts_yearly")


@router.get("/discounts/product-trends")
def get_product_discount_trends(
    account: Optional[str] = None, 
    months: int = 19,
    top_n: int = 10,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM")
):
    """产品折扣趋势"""
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        # Mock模式返回模拟数据
        if is_mock_mode() or account_config.provider == "mock":
            result = _generate_mock_product_trends_data(months, top_n)
            return {"success": True, "data": result}
        
        account_id = _get_account_id(account_config, account_name)
        
        # 尝试从缓存获取
        cache_key = f"products:{account_id}:{months}:{top_n}:{start_date}:{end_date}"
        cached = _cache_get(cache_key)
        if cached:
            return cached
        
        from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_product_discount_trends(account_id, months, top_n, start_date, end_date)
        response = {"success": True, "data": result}
        _cache_set(cache_key, response)
        return response
    except Exception as e:
        raise handle_api_error(e, "get_product_discount_trends")


@router.get("/discounts/regions")
def get_discounts_by_regions(
    account: Optional[str] = None, 
    months: int = 19,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM")
):
    """按地域统计折扣"""
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        # Mock模式返回模拟数据
        if is_mock_mode() or account_config.provider == "mock":
            result = _generate_mock_regions_data(months)
            return {"success": True, "data": result}
        
        account_id = _get_account_id(account_config, account_name)
        
        # 尝试从缓存获取
        cache_key = f"regions:{account_id}:{months}:{start_date}:{end_date}"
        cached = _cache_get(cache_key)
        if cached:
            return cached
        
        from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_region_discount_ranking(account_id, months, start_date, end_date)
        response = {"success": True, "data": result}
        _cache_set(cache_key, response)
        return response
    except Exception as e:
        raise handle_api_error(e, "get_discounts_by_regions")


@router.get("/discounts/subscription-types")
def get_discounts_by_subscription_types(
    account: Optional[str] = None, 
    months: int = 19,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM")
):
    """按订阅类型统计折扣"""
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        # Mock模式返回模拟数据
        if is_mock_mode() or account_config.provider == "mock":
            result = _generate_mock_subscription_types_data(months)
            return {"success": True, "data": result}
        
        account_id = _get_account_id(account_config, account_name)
        
        # 尝试从缓存获取
        cache_key = f"subscription:{account_id}:{months}:{start_date}:{end_date}"
        cached = _cache_get(cache_key)
        if cached:
            return cached
        
        from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_subscription_type_comparison(account_id, months, start_date, end_date)
        response = {"success": True, "data": result}
        _cache_set(cache_key, response)
        return response
    except Exception as e:
        raise handle_api_error(e, "get_discounts_by_subscription_types")


@router.get("/discounts/optimization-suggestions")
def get_discount_optimization_suggestions(
    account: Optional[str] = None,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM")
):
    """折扣优化建议"""
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        # Mock模式返回模拟数据
        if is_mock_mode() or account_config.provider == "mock":
            result = _generate_mock_optimization_suggestions()
            return {"success": True, "data": result}
        
        account_id = _get_account_id(account_config, account_name)
        
        # 尝试从缓存获取
        cache_key = f"optimization:{account_id}:{start_date}:{end_date}"
        cached = _cache_get(cache_key)
        if cached:
            return cached
        
        from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_optimization_suggestions(account_id, 6, start_date, end_date)
        response = {"success": True, "data": result}
        _cache_set(cache_key, response)
        return response
    except Exception as e:
        raise handle_api_error(e, "get_discount_optimization_suggestions")


@router.get("/discounts/anomalies")
def get_discount_anomalies(
    account: Optional[str] = None, 
    months: int = 19,
    threshold: float = 0.10,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM")
):
    """折扣异常检测"""
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        # Mock模式返回模拟数据
        if is_mock_mode() or account_config.provider == "mock":
            result = _generate_mock_anomalies_data(months)
            return {"success": True, "data": result}
        
        account_id = _get_account_id(account_config, account_name)
        
        # 尝试从缓存获取
        cache_key = f"anomalies:{account_id}:{months}:{threshold}:{start_date}:{end_date}"
        cached = _cache_get(cache_key)
        if cached:
            return cached
        
        from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.detect_anomalies(account_id, months, threshold, start_date, end_date)
        response = {"success": True, "data": result}
        _cache_set(cache_key, response)
        return response
    except Exception as e:
        raise handle_api_error(e, "get_discount_anomalies")


@router.get("/discounts/product-region-matrix")
def get_product_region_discount_matrix(account: Optional[str] = None):
    """产品-地域折扣矩阵"""
    from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_product_region_matrix(account_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise handle_api_error(e, "get_product_region_discount_matrix")


@router.get("/discounts/moving-average")
def get_discounts_moving_average(account: Optional[str] = None, windows: str = "3,6,12"):
    """折扣移动平均"""
    from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        window_sizes = [int(w.strip()) for w in windows.split(',')]
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_moving_average(account_id, window_sizes)
        return {"success": True, "data": result}
    except Exception as e:
        raise handle_api_error(e, "get_discounts_moving_average")


@router.get("/discounts/cumulative")
def get_discounts_cumulative(account: Optional[str] = None):
    """折扣累计统计"""
    from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_cumulative_discount(account_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise handle_api_error(e, "get_discounts_cumulative")


@router.get("/discounts/instance-lifecycle")
def get_instance_lifecycle_discounts(account: Optional[str] = None):
    """实例生命周期折扣"""
    from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_instance_lifecycle_analysis(account_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise handle_api_error(e, "get_instance_lifecycle_discounts")


@router.get("/discounts/insights")
def get_discount_insights(account: Optional[str] = None):
    """折扣洞察"""
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        # Mock模式返回模拟数据
        if is_mock_mode() or account_config.provider == "mock":
            insights = [
                {
                    "category": "折扣优化",
                    "level": "success",
                    "title": "包年包月折扣优势明显",
                    "description": "当前包年包月资源平均折扣率35%，比按量付费高12个百分点。建议将长期运行的按量付费实例转为包年包月。",
                    "recommendation": "预计年度可节省约180万元"
                },
                {
                    "category": "区域分布",
                    "level": "warning",
                    "title": "华东区域成本占比过高",
                    "description": "华东1（杭州）和华东2（上海）合计占比超过60%，建议评估是否可以将部分资源迁移到成本更低的区域。",
                    "recommendation": "考虑使用华北或华南区域，预计可节省5-10%成本"
                },
                {
                    "category": "产品优化",
                    "level": "info",
                    "title": "ECS折扣率稳定",
                    "description": "ECS产品在过去12个月平均折扣率保持在30%左右，折扣策略执行良好。",
                    "recommendation": "继续保持当前折扣策略"
                },
            ]
            return {"success": True, "data": {"insights": insights}}
        
        account_id = _get_account_id(account_config, account_name)
        
        # 尝试从缓存获取
        cache_key = f"insights:{account_id}"
        cached = _cache_get(cache_key)
        if cached:
            return cached
        
        from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.generate_insights(account_id)
        response = {"success": True, "data": result}
        _cache_set(cache_key, response)
        return response
    except Exception as e:
        raise handle_api_error(e, "get_discount_insights")


@router.get("/discounts/export")
def export_discounts(account: Optional[str] = None):
    """导出折扣数据"""
    return {"success": True, "message": "导出功能正在通过报告模块实现"}

