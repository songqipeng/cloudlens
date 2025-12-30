#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源管理API模块 - 增强版（支持全资源跨区域扫描）
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import concurrent.futures

from web.backend.api_base import handle_api_error
from core.config import ConfigManager, CloudAccount
from core.context import ContextManager
from core.cache import CacheManager
from models.resource import UnifiedResource, ResourceType, ResourceStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

def _get_provider_for_account(account: Optional[str] = None):
    """Helper to get provider instance"""
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
    
    from cli.utils import get_provider
    return get_provider(account_config), account

def _get_billing_cycle_default() -> str:
    return datetime.now().strftime("%Y-%m")

def _bss_query_instance_bill(account_config: CloudAccount, billing_cycle: str, product_code: str, subscription_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """调用阿里云 BSS OpenAPI QueryInstanceBill"""
    try:
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkcore.request import CommonRequest
    except Exception as e:
        raise RuntimeError(f"阿里云 SDK 不可用：{e}")

    import json
    client = AcsClient(account_config.access_key_id, account_config.access_key_secret, "cn-hangzhou")
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
        data_node = data.get("Data") or {}
        items_node = (data_node.get("Items") or {}).get("Item") or data_node.get("Item") or []
        if not isinstance(items_node, list):
            items_node = [items_node]

        items.extend([i for i in items_node if isinstance(i, dict)])
        total_count = int(data.get("TotalCount") or data_node.get("TotalCount") or 0)
        if (total_count and len(items) >= total_count) or len(items_node) < page_size:
            break
        page_num += 1

    return items

def _get_cost_map_from_billing(resource_type: str, account_config: CloudAccount, billing_cycle: Optional[str] = None) -> Dict[str, float]:
    if billing_cycle is None:
        billing_cycle = _get_billing_cycle_default()

    product_code_map = {
        "ecs": "ecs", "rds": "rds", "redis": "kvstore", "slb": "slb",
        "eip": "eip", "nat": "nat_gw", "nat_gw": "nat_gw",
        "yundisk": "yundisk", "disk": "yundisk", "snapshot": "snapshot",
        "oss": "oss", "nas": "nas",
    }
    product_code = product_code_map.get(resource_type)
    if not product_code:
        return {}

    expected_prefix_map = {
        "ecs": "i-", "rds": "rm-", "redis": "r-", "slb": "lb-",
        "eip": "eip-", "nat": "ngw-", "nat_gw": "ngw-",
        "yundisk": "d-", "disk": "d-", "snapshot": "s-",
    }
    expected_prefix = expected_prefix_map.get(resource_type)

    cache_manager = CacheManager(ttl_seconds=86400)
    cache_key = f"billing_cost_map_{resource_type}_{billing_cycle}"
    cached = cache_manager.get(resource_type=cache_key, account_name=account_config.name)
    if isinstance(cached, dict) and cached:
        return cached

    cost_map: Dict[str, float] = {}
    try:
        for sub_type in ("PayAsYouGo", "Subscription"):
            rows = _bss_query_instance_bill(account_config, billing_cycle, product_code, subscription_type=sub_type)
            for row in rows:
                instance_id = row.get("InstanceID") or row.get("InstanceId") or row.get("instanceId") or row.get("instance_id")
                if not instance_id or (expected_prefix and not str(instance_id).startswith(expected_prefix)):
                    continue
                pretax = row.get("PretaxAmount")
                try:
                    pretax_f = float(pretax) if pretax is not None else 0.0
                except:
                    pretax_f = 0.0
                if pretax_f > 0:
                    cost_map[instance_id] = float(cost_map.get(instance_id, 0.0) + pretax_f)
        cache_manager.set(resource_type=cache_key, account_name=account_config.name, data=cost_map)
        return cost_map
    except:
        return {}

def _get_cost_map(resource_type: str, account_config: CloudAccount) -> Dict[str, float]:
    cost_map = {}
    try:
        from resource_modules.cost_analyzer import CostAnalyzer
        cost_analyzer = CostAnalyzer(account_config.name, account_config.access_key_id, account_config.access_key_secret)
        billing_costs = _get_cost_map_from_billing(resource_type, account_config)
        for rid, mc in (billing_costs or {}).items():
            if rid and mc and mc > 0: cost_map[rid] = float(mc)
        
        costs = cost_analyzer.get_cost_from_discount_analyzer(resource_type)
        for c in costs:
            rid, mc = c.get("instance_id"), c.get("monthly_cost", 0)
            if rid and mc > 0 and rid not in cost_map: cost_map[rid] = float(mc)
            
        db_costs = cost_analyzer.get_cost_from_database(resource_type)
        for c in db_costs:
            rid, mc = c.get("instance_id"), c.get("monthly_cost", 0)
            if rid and mc > 0 and rid not in cost_map: cost_map[rid] = float(mc)
    except: pass
    return cost_map

def _estimate_monthly_cost_from_spec(spec: str, resource_type: str = "ecs") -> float:
    cost_map = {
        "ecs.t5-lc1m1.small": 50, "ecs.t5-lc1m2.small": 80, "ecs.g6.large": 400,
        "ecs.g6.xlarge": 800, "rds.mysql.s1.small": 200, "rds.mysql.s2.large": 500,
        "redis.master.small.default": 150, "redis.master.mid.default": 300,
    }
    if spec in cost_map: return cost_map[spec]
    if resource_type == "ecs" and isinstance(spec, str) and spec.startswith("ecs."):
        parts = spec.split(".")
        if len(parts) >= 3:
            size = parts[-1].lower()
            size_mul = 1.0
            if size == "small": size_mul = 0.25
            elif size == "medium": size_mul = 0.5
            elif size == "large": size_mul = 1.0
            elif size == "xlarge": size_mul = 2.0
            else:
                import re
                m = re.match(r"^(\d+)xlarge$", size)
                if m: size_mul = max(1.0, float(m.group(1)) * 2.0)
            return round(320.0 * size_mul, 2)
    return 300 if resource_type == "ecs" else (400 if resource_type == "rds" else 200)

def _estimate_monthly_cost(resource) -> float:
    spec = getattr(resource, "spec", None) or ""
    resource_type = "ecs"
    if hasattr(resource, "resource_type"):
        rt = resource.resource_type.value if hasattr(resource.resource_type, 'value') else str(resource.resource_type)
        if "rds" in rt.lower(): resource_type = "rds"
        elif "redis" in rt.lower(): resource_type = "redis"
    return _estimate_monthly_cost_from_spec(spec, resource_type)

def _fetch_resources_for_region(account_config: CloudAccount, region: str, resource_type: str) -> List[Any]:
    """在新地区中获取特定类型的资源"""
    from providers.aliyun.provider import AliyunProvider
    try:
        region_provider = AliyunProvider(account_config.name, account_config.access_key_id, account_config.access_key_secret, region)
        
        if resource_type == "ecs":
            if region_provider.check_instances_count() > 0:
                return region_provider.list_instances()
        elif resource_type == "rds":
            return region_provider.list_rds()
        elif resource_type == "redis":
            return region_provider.list_redis()
        elif resource_type == "slb":
            return region_provider.list_slb() if hasattr(region_provider, "list_slb") else []
        elif resource_type == "nat":
            return region_provider.list_nat_gateways() if hasattr(region_provider, "list_nat_gateways") else []
        elif resource_type == "eip":
            return region_provider.list_eip() if hasattr(region_provider, "list_eip") else []
        elif resource_type == "vpc":
            vpcs = region_provider.list_vpcs()
            unified_vpcs = []
            for vpc in vpcs:
                vid = vpc.get("id") or vpc.get("VpcId")
                if vid:
                    unified_vpcs.append(UnifiedResource(
                        id=vid, 
                        name=vpc.get("name") or vid, 
                        resource_type=ResourceType.VPC, 
                        status=ResourceStatus.RUNNING, 
                        provider="aliyun", 
                        region=vpc.get("region") or vpc.get("RegionId", region)
                    ))
            return unified_vpcs
        elif resource_type == "oss":
            return region_provider.list_oss() if hasattr(region_provider, "list_oss") else []
        elif resource_type == "disk":
            return region_provider.list_disks() if hasattr(region_provider, "list_disks") else []
        elif resource_type == "snapshot":
            return region_provider.list_snapshots() if hasattr(region_provider, "list_snapshots") else []
            
    except Exception as e:
        logger.warning(f"Failed to fetch {resource_type} in region {region}: {e}")
    return []

@router.get("/resources")
def list_resources(
    type: str = Query("ecs"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    account: Optional[str] = None,
    sortBy: Optional[str] = None,
    sortOrder: Optional[str] = Query("asc", regex="^(asc|desc)$"),
    filter: Optional[str] = None,
    force_refresh: bool = Query(False),
):
    provider, account_name = _get_provider_for_account(account)
    cache_manager = CacheManager(ttl_seconds=86400)
    
    if not force_refresh:
        cached = cache_manager.get(resource_type=type, account_name=account_name)
        if cached:
            total_count = len(cached)
            total_pages = (total_count + pageSize - 1) // pageSize
            return {
                "success": True,
                "data": cached[(page-1)*pageSize : page*pageSize],
                "pagination": {
                    "total": total_count,
                    "page": page,
                    "pageSize": pageSize,
                    "totalPages": total_pages
                },
                "cached": True
            }
    
    cm = ConfigManager()
    account_config = cm.get_account(account_name)
    
    # 获取所有区域
    from core.services.analysis_service import AnalysisService
    all_regions = AnalysisService._get_all_regions(account_config.access_key_id, account_config.access_key_secret)
    
    all_resources = []
    
    # 并发查询（加速）
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_resources_for_region, account_config, region, type): region for region in all_regions}
        for future in concurrent.futures.as_completed(futures):
            all_resources.extend(future.result())

    cost_map = _get_cost_map(type, account_config) if type != "vpc" else {}
    result = []
    
    for r in all_resources:
        if isinstance(r, dict):
            rid = r.get("id") or r.get("ResourceId") or r.get("name")
            if not rid: continue
            cost = cost_map.get(rid, 0.0)
            result.append({
                "id": rid, "name": r.get("name") or rid, "type": type, 
                "status": str(r.get("status") or "Running"),
                "region": str(r.get("region") or r.get("RegionId") or ""), 
                "spec": str(r.get("spec") or "-"),
                "cost": float(cost), "tags": {}, "created_time": None, 
                "public_ips": [r.get("ip_address")] if r.get("ip_address") else [], 
                "private_ips": [], "vpc_id": r.get("vpc_id")
            })
        else:
            cost = cost_map.get(r.id) or _estimate_monthly_cost(r)
            result.append({
                "id": r.id, "name": r.name or r.id, "type": type, 
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "region": r.region, "spec": r.spec or "-", "cost": float(cost), 
                "tags": r.tags if hasattr(r, "tags") else {},
                "created_time": r.created_time.isoformat() if hasattr(r, "created_time") and r.created_time else None,
                "public_ips": r.public_ips if hasattr(r, "public_ips") else [],
                "private_ips": r.private_ips if hasattr(r, "private_ips") else [],
                "vpc_id": r.vpc_id if hasattr(r, "vpc_id") else None
            })

    if sortBy:
        reverse = sortOrder == "desc"
        result.sort(key=lambda x: x.get(sortBy, ""), reverse=reverse)
    
    cache_manager.set(resource_type=type, account_name=account_name, data=result)
    
    start = (page - 1) * pageSize
    end = start + pageSize
    total_count = len(result)
    total_pages = (total_count + pageSize - 1) // pageSize
    
    return {
        "success": True,
        "data": result[start:end],
        "pagination": {
            "total": total_count,
            "page": page,
            "pageSize": pageSize,
            "totalPages": total_pages
        }
    }

@router.get("/resources/{resource_id}")
def get_resource_detail(resource_id: str):
    return {"success": True, "data": {"id": resource_id}}

@router.get("/resources/{resource_id}/metrics")
def get_resource_metrics(resource_id: str):
    return {"success": True, "data": {}}
