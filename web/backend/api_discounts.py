from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta

from web.backend.api_base import handle_api_error
from cloudlens.core.config import ConfigManager, CloudAccount
from cloudlens.core.context import ContextManager
from cloudlens.core.cache import CacheManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


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


@router.get("/discounts/trend")
def get_discounts_trend(
    account: Optional[str] = Query(None, description="账号名称"),
    months: int = Query(19, ge=1, le=999, description="分析月数"),
    force_refresh: bool = Query(False, description="强制刷新缓存"),
):
    """折扣趋势分析"""
    from cloudlens.core.discount_analyzer_db import DiscountAnalyzerDB
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        # 构造账号ID（必须与数据同步时的格式一致）
        account_id = _get_account_id(account_config, account_name)
        
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
def get_discounts_quarterly(account: Optional[str] = None, quarters: int = 8):
    """季度折扣分析"""
    from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_quarterly_comparison(account_id, quarters)
        return {"success": True, "data": result}
    except Exception as e:
        raise handle_api_error(e, "get_discounts_quarterly")


@router.get("/discounts/yearly")
def get_discounts_yearly(account: Optional[str] = None):
    """年度折扣分析"""
    from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_yearly_comparison(account_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise handle_api_error(e, "get_discounts_yearly")


@router.get("/discounts/product-trends")
def get_product_discount_trends(account: Optional[str] = None, months: int = 19):
    """产品折扣趋势"""
    from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_product_discount_trends(account_id, months)
        return {"success": True, "data": result}
    except Exception as e:
        raise handle_api_error(e, "get_product_discount_trends")


@router.get("/discounts/regions")
def get_discounts_by_regions(account: Optional[str] = None, months: int = 19):
    """按地域统计折扣"""
    from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_region_discount_ranking(account_id, months)
        return {"success": True, "data": result}
    except Exception as e:
        raise handle_api_error(e, "get_discounts_by_regions")


@router.get("/discounts/subscription-types")
def get_discounts_by_subscription_types(account: Optional[str] = None, months: int = 19):
    """按订阅类型统计折扣"""
    from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_subscription_type_comparison(account_id, months)
        return {"success": True, "data": result}
    except Exception as e:
        raise handle_api_error(e, "get_discounts_by_subscription_types")


@router.get("/discounts/optimization-suggestions")
def get_discount_optimization_suggestions(account: Optional[str] = None):
    """折扣优化建议"""
    from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.get_optimization_suggestions(account_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise handle_api_error(e, "get_discount_optimization_suggestions")


@router.get("/discounts/anomalies")
def get_discount_anomalies(account: Optional[str] = None, months: int = 19):
    """折扣异常检测"""
    from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.detect_anomalies(account_id, months)
        return {"success": True, "data": result}
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
    from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        account_id = _get_account_id(account_config, account_name)
        
        analyzer = AdvancedDiscountAnalyzer()
        result = analyzer.generate_insights(account_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise handle_api_error(e, "get_discount_insights")


@router.get("/discounts/export")
def export_discounts(account: Optional[str] = None):
    """导出折扣数据"""
    return {"success": True, "message": "导出功能正在通过报告模块实现"}

