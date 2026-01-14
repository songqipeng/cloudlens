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
from cloudlens.core.config import ConfigManager, CloudAccount
from cloudlens.core.context import ContextManager
from cloudlens.core.cache import CacheManager
from cloudlens.models.resource import UnifiedResource, ResourceType, ResourceStatus

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
    
    from cloudlens.cli.utils import get_provider
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
        from cloudlens.resource_modules.cost_analyzer import CostAnalyzer
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
    from cloudlens.providers.aliyun.provider import AliyunProvider
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
            # OSS is a global service, but list_buckets returns all buckets regardless of region endpoint.
            # To avoid N times duplication (where N is number of regions), we only fetch when region is "cn-hangzhou".
            if region == "cn-hangzhou":
                 return region_provider.list_buckets() if hasattr(region_provider, "list_buckets") else []
            return []
        elif resource_type == "disk":
            return region_provider.list_disks() if hasattr(region_provider, "list_disks") else []
        elif resource_type == "snapshot":
            return region_provider.list_snapshots() if hasattr(region_provider, "list_snapshots") else []
        elif resource_type == "mongodb":
            return region_provider.list_mongodb() if hasattr(region_provider, "list_mongodb") else []
        elif resource_type == "ack":
            # ACK 集群查询需要特殊处理（直接调用 API，不依赖数据库）
            try:
                from aliyunsdkcore.client import AcsClient
                from aliyunsdkcore.request import CommonRequest
                import json

                # 直接调用阿里云 API，不依赖 ACKAnalyzer（避免数据库初始化问题）
                client = AcsClient(account_config.access_key_id, account_config.access_key_secret, region)
                request = CommonRequest()
                request.set_domain(f"cs.{region}.aliyuncs.com")
                request.set_method("GET")  # 修复：使用 GET 方法
                request.set_version("2015-12-15")
                request.set_uri_pattern("/clusters")  # 修复：使用 URI 路径而不是 Action

                response = client.do_action_with_exception(request)
                data = json.loads(response)

                # 修复：API 返回的是直接的列表，不是包含 "clusters" 键的字典
                clusters = []
                if isinstance(data, list):
                    cluster_list = data
                elif isinstance(data, dict) and "clusters" in data:
                    cluster_list = data["clusters"]
                    if not isinstance(cluster_list, list):
                        cluster_list = [cluster_list]
                else:
                    cluster_list = []

                for cluster in cluster_list:
                    # 获取集群的实际区域（从 cluster.region_id 获取，如果没有则使用查询的区域）
                    cluster_region = cluster.get("region_id") or region
                    
                    # 只添加属于当前查询区域的集群（避免重复）
                    if cluster_region == region:
                        clusters.append({
                            "ClusterId": cluster.get("cluster_id", ""),
                            "Name": cluster.get("name", ""),
                            "ClusterType": cluster.get("cluster_type", ""),
                            "State": cluster.get("state", ""),
                            "RegionId": cluster_region,
                            "KubernetesVersion": cluster.get("current_version", ""),
                            "InitVersion": cluster.get("init_version", ""),
                            "NodeCount": cluster.get("size", 0),
                            "Created": cluster.get("created", ""),
                            "Updated": cluster.get("updated", ""),
                            "VpcId": cluster.get("vpc_id", ""),
                            "VSwitchId": cluster.get("vswitch_id", ""),
                            "SecurityGroupId": cluster.get("security_group_id", ""),
                            "ServiceDomainName": cluster.get("service_domain_name", ""),
                            "ExternalLoadBalancerId": cluster.get("external_loadbalancer_id", ""),
                            "ResourceGroupId": cluster.get("resource_group_id", ""),
                            "MasterUrl": cluster.get("master_url", ""),
                            "Tags": cluster.get("tags", []),
                            "Profile": cluster.get("profile", ""),
                            "MetaData": cluster.get("meta_data", ""),  # 包含插件、网络配置等详细信息
                            "RawData": cluster,  # 保存完整原始数据
                        })

                # 转换为 UnifiedResource
                # 转换为 UnifiedResource
                unified_clusters = []
                for cluster in clusters:
                    if isinstance(cluster, dict):
                        # ACKAnalyzer 返回的键是大写的：ClusterId, Name, State, ClusterType
                        cluster_id = cluster.get("ClusterId") or cluster.get("cluster_id") or cluster.get("id", "")
                        cluster_name = cluster.get("Name") or cluster.get("name") or cluster_id
                        cluster_state = cluster.get("State") or cluster.get("state", "")
                        cluster_type = cluster.get("ClusterType") or cluster.get("cluster_type", "-")

                        if cluster_id:  # 只有有效的 cluster_id 才添加
                            # 保存完整的 ACK 集群数据到 raw_data
                            raw_data = cluster.get("RawData", cluster)
                            unified_clusters.append(UnifiedResource(
                                id=cluster_id,
                                name=cluster_name,
                                resource_type=ResourceType.K8S,
                                status=ResourceStatus.RUNNING if cluster_state.lower() == "running" else ResourceStatus.STOPPED,
                                provider="aliyun",
                                region=region,
                                spec=cluster_type,
                                raw_data=raw_data,  # 保存完整原始数据
                                tags={tag.get("key", ""): tag.get("value", "") for tag in cluster.get("Tags", []) if isinstance(tag, dict)} if cluster.get("Tags") else {}
                            ))
                return unified_clusters
            except Exception as e:
                logger.warning(f"Failed to fetch ACK clusters in region {region}: {e}")
                import traceback
                logger.debug(f"ACK query error details: {traceback.format_exc()}")
                return []
            
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
    sortOrder: Optional[str] = Query("asc", pattern="^(asc|desc)$"),
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
    from cloudlens.core.services.analysis_service import AnalysisService
    all_regions = AnalysisService._get_all_regions(account_config.access_key_id, account_config.access_key_secret)
    
    all_resources = []
    
    # 并发查询（加速）
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_resources_for_region, account_config, region, type): region for region in all_regions}
        for future in concurrent.futures.as_completed(futures):
            try:
                region_resources = future.result()
                if region_resources:
                    logger.info(f"区域 {futures[future]} 找到 {len(region_resources)} 个 {type} 资源")
                all_resources.extend(region_resources)
            except Exception as e:
                region = futures.get(future, "unknown")
                logger.warning(f"查询区域 {region} 的 {type} 资源失败: {e}")
    
    logger.info(f"总共获取到 {len(all_resources)} 个 {type} 资源")

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
            # 处理 created_time：可能是 datetime 对象或字符串
            created_time = None
            if hasattr(r, "created_time") and r.created_time:
                if isinstance(r.created_time, str):
                    created_time = r.created_time
                elif hasattr(r.created_time, "isoformat"):
                    created_time = r.created_time.isoformat()
                else:
                    created_time = str(r.created_time)
            
            result.append({
                "id": r.id, "name": r.name or r.id, "type": type, 
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "region": r.region, "spec": r.spec or "-", "cost": float(cost), 
                "tags": r.tags if hasattr(r, "tags") else {},
                "created_time": created_time,
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
def get_resource_detail(
    resource_id: str,
    account: Optional[str] = None,
    resource_type: Optional[str] = Query(None, alias="type"),  # 同时支持 type 和 resource_type
    type: Optional[str] = None  # 兼容前端传递的 type 参数
):
    """获取资源详情"""
    # 优先使用 resource_type，如果没有则使用 type
    final_type = resource_type or type
    logger.info(f"[api_resources] 收到请求: resource_id={resource_id}, type={final_type}, account={account}")

    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)

        # 如果提供了 resource_type，直接查询该类型
        if final_type:
            from cloudlens.core.services.analysis_service import AnalysisService
            all_regions = AnalysisService._get_all_regions(
                account_config.access_key_id,
                account_config.access_key_secret
            )
            
            # 在所有区域中查找资源
            resource = None
            found_region = None
            for region in all_regions:
                resources = _fetch_resources_for_region(account_config, region, final_type)
                found = next((r for r in resources if (r.id if hasattr(r, 'id') else r.get('id', '')) == resource_id), None)
                if found:
                    resource = found
                    found_region = region
                    logger.info(f"找到资源 {resource_id} 在区域 {region}, 类型: {final_type}, has raw_data: {hasattr(resource, 'raw_data')}")
                    break

            if resource:
                # 转换为字典格式
                if hasattr(resource, 'id'):
                    cost_map = _get_cost_map(final_type, account_config) if final_type != "vpc" else {}
                    cost = cost_map.get(resource.id) or _estimate_monthly_cost(resource)

                    # 基础数据
                    result_data = {
                        "id": resource.id,
                        "name": resource.name or resource.id,
                        "type": final_type,
                        "status": resource.status.value if hasattr(resource.status, "value") else str(resource.status),
                        "region": resource.region,
                        "spec": resource.spec or "-",
                        "cost": float(cost or 0),
                        "tags": resource.tags if hasattr(resource, "tags") else {},
                        "created_time": resource.created_time.isoformat() if hasattr(resource, "created_time") and resource.created_time else None,
                        "public_ips": resource.public_ips if hasattr(resource, "public_ips") else [],
                        "private_ips": resource.private_ips if hasattr(resource, "private_ips") else [],
                        "vpc_id": resource.vpc_id if hasattr(resource, "vpc_id") else None
                    }
                    
                    # 如果是 ACK 资源，添加详细信息
                    if final_type == "ack":
                        logger.info(f"处理 ACK 资源详情: {resource.id}, has raw_data: {hasattr(resource, 'raw_data')}")
                        if hasattr(resource, "raw_data") and resource.raw_data:
                            raw_data = resource.raw_data
                            # 注意：不能使用 type() 因为参数名为 type，会覆盖内置函数
                            logger.info(f"raw_data 类型: {raw_data.__class__.__name__}, 是字典: {isinstance(raw_data, dict)}")

                            # 如果 raw_data 是字符串，尝试解析为 JSON
                            if isinstance(raw_data, str):
                                logger.warning(f"raw_data 是字符串类型，尝试解析为 JSON")
                                try:
                                    import json as json_lib
                                    raw_data = json_lib.loads(raw_data)
                                    logger.info(f"成功解析 raw_data 为字典")
                                except Exception as parse_error:
                                    logger.error(f"解析 raw_data 失败: {parse_error}")
                                    raw_data = None
                        else:
                            logger.warning(f"ACK 资源 {resource.id} 没有 raw_data 或 raw_data 为空")
                            raw_data = None

                        if raw_data:
                            import json as json_lib
                            
                            # 解析 meta_data（包含插件、网络配置等）
                            meta_data = {}
                            if isinstance(raw_data.get("meta_data"), str):
                                try:
                                    meta_data = json_lib.loads(raw_data.get("meta_data", "{}"))
                                except:
                                    pass
                            elif isinstance(raw_data.get("meta_data"), dict):
                                meta_data = raw_data.get("meta_data", {})
                            
                            # 解析 master_url
                            master_url = {}
                            if isinstance(raw_data.get("master_url"), str):
                                try:
                                    master_url = json_lib.loads(raw_data.get("master_url", "{}"))
                                except:
                                    pass
                            elif isinstance(raw_data.get("master_url"), dict):
                                master_url = raw_data.get("master_url", {})
                            
                            # 提取插件信息
                            addons = []
                            if "Addons" in meta_data:
                                addons = meta_data.get("Addons", [])
                            
                            # 提取网络配置
                            network_info = {}
                            if "Capabilities" in meta_data:
                                caps = meta_data.get("Capabilities", {})
                                network_info = {
                                    "network": caps.get("Network", ""),
                                    "proxy_mode": caps.get("ProxyMode", ""),
                                    "node_cidr_mask": caps.get("NodeCIDRMask", ""),
                                }
                            
                            # 添加 ACK 特定信息
                            result_data.update({
                                "ack_details": {
                                    "cluster_id": raw_data.get("cluster_id", ""),
                                    "cluster_type": raw_data.get("cluster_type", ""),
                                    "cluster_spec": raw_data.get("cluster_spec", ""),
                                    "kubernetes_version": raw_data.get("current_version", ""),
                                    "init_version": raw_data.get("init_version", ""),
                                    "node_count": raw_data.get("size", 0),
                                    "created": raw_data.get("created", ""),
                                    "updated": raw_data.get("updated", ""),
                                    "cluster_domain": raw_data.get("cluster_domain", ""),
                                    "timezone": raw_data.get("timezone", ""),
                                    "deletion_protection": raw_data.get("deletion_protection", False),
                                    "network_mode": raw_data.get("network_mode", ""),
                                    "proxy_mode": raw_data.get("proxy_mode", ""),
                                    "vpc_id": raw_data.get("vpc_id", ""),
                                    "vswitch_id": raw_data.get("vswitch_id", ""),
                                    "vswitch_ids": raw_data.get("vswitch_ids", []),
                                    "security_group_id": raw_data.get("security_group_id", ""),
                                    "external_loadbalancer_id": raw_data.get("external_loadbalancer_id", ""),
                                    "service_domain_name": raw_data.get("service_domain_name", ""),
                                    "service_cidr": raw_data.get("service_cidr", ""),
                                    "master_url": master_url,
                                    "resource_group_id": raw_data.get("resource_group_id", ""),
                                    "profile": raw_data.get("profile", ""),
                                    "addons": addons,
                                    "network_info": network_info,
                                }
                            })
                    
                    return {
                        "success": True,
                        "data": result_data
                    }
        
        # 如果没有提供 resource_type，尝试从所有类型中查找
        resource_types = ["ecs", "rds", "redis", "slb", "nat", "eip", "oss", "disk", "snapshot", "vpc", "mongodb", "ack"]
        for rt in resource_types:
            try:
                from cloudlens.core.services.analysis_service import AnalysisService
                all_regions = AnalysisService._get_all_regions(
                    account_config.access_key_id,
                    account_config.access_key_secret
                )
                for region in all_regions:
                    resources = _fetch_resources_for_region(account_config, region, rt)
                    resource = next((r for r in resources if (r.id if hasattr(r, 'id') else r.get('id', '')) == resource_id), None)
                    if resource:
                        if hasattr(resource, 'id'):
                            cost_map = _get_cost_map(rt, account_config) if rt != "vpc" else {}
                            cost = cost_map.get(resource.id) or _estimate_monthly_cost(resource)
                            return {
                                "success": True,
                                "data": {
                                    "id": resource.id,
                                    "name": resource.name or resource.id,
                                    "type": rt,
                                    "status": resource.status.value if hasattr(resource.status, "value") else str(resource.status),
                                    "region": resource.region,
                                    "spec": resource.spec or "-",
                                    "cost": float(cost or 0),
                                    "tags": resource.tags if hasattr(resource, "tags") else {},
                                    "created_time": resource.created_time.isoformat() if hasattr(resource, "created_time") and resource.created_time else None,
                                    "public_ips": resource.public_ips if hasattr(resource, "public_ips") else [],
                                    "private_ips": resource.private_ips if hasattr(resource, "private_ips") else [],
                                    "vpc_id": resource.vpc_id if hasattr(resource, "vpc_id") else None
                                }
                            }
            except Exception as e:
                logger.debug(f"查询 {rt} 类型资源失败: {e}")
                continue
        
        # 如果找不到资源，返回基本信息
        return {
            "success": True,
            "data": {
                "id": resource_id,
                "name": resource_id,
                "type": resource_type or "unknown",
                "status": "Unknown",
                "region": "",
                "spec": "-",
                "cost": 0.0,
                "tags": {},
                "created_time": None,
                "public_ips": [],
                "private_ips": [],
                "vpc_id": None
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"获取资源详情失败: {e}")
        logger.error(f"完整错误堆栈:\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "id": resource_id,
                "name": resource_id,
                "type": resource_type or "unknown",
                "status": "Unknown",
                "region": "",
                "spec": "-",
                "cost": 0.0,
                "tags": {},
                "created_time": None,
                "public_ips": [],
                "private_ips": [],
                "vpc_id": None
            }
        }

@router.get("/resources/{resource_id}/metrics")
def get_resource_metrics(
    resource_id: str,
    resource_type: str = Query("ecs"),
    days: int = Query(7, ge=1, le=30),
    account: Optional[str] = None
):
    """获取资源的监控指标"""
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        from cloudlens.core.monitor import CloudMonitor
        monitor = CloudMonitor(account_config)
        
        if resource_type == "ecs":
            metrics = monitor.get_ecs_metrics(resource_id, days)
        elif resource_type == "rds":
            metrics = monitor.get_rds_metrics(resource_id, days)
        elif resource_type == "slb":
            metrics = monitor.get_slb_metrics(resource_id, days)
        else:
            return {"success": False, "error": f"不支持的资源类型: {resource_type}"}
        
        return {"success": True, "data": metrics}
    except Exception as e:
        logger.error(f"获取资源 {resource_id} 的监控指标失败: {e}")
        return {"success": False, "error": str(e)}

@router.get("/resources/export")
def export_resources(
    type: str = Query("ecs"),
    format: str = Query("csv", pattern="^(csv|excel)$"),
    account: Optional[str] = None,
    filter: Optional[str] = None,
):
    """导出资源列表"""
    try:
        provider, account_name = _get_provider_for_account(account)
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        # 获取所有资源（不分页）
        from cloudlens.core.services.analysis_service import AnalysisService
        all_regions = AnalysisService._get_all_regions(account_config.access_key_id, account_config.access_key_secret)
        
        all_resources = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_fetch_resources_for_region, account_config, region, type): region for region in all_regions}
            for future in concurrent.futures.as_completed(futures):
                all_resources.extend(future.result())
        
        # 应用筛选
        if filter:
            # 简单的筛选逻辑，可以根据需要扩展
            filtered = []
            for r in all_resources:
                if isinstance(r, dict):
                    if filter.lower() in str(r.get("name", "")).lower() or filter.lower() in str(r.get("id", "")).lower():
                        filtered.append(r)
                else:
                    if filter.lower() in str(r.name or "").lower() or filter.lower() in str(r.id or "").lower():
                        filtered.append(r)
            all_resources = filtered
        
        # 转换为导出格式
        cost_map = _get_cost_map(type, account_config) if type != "vpc" else {}
        export_data = []
        
        for r in all_resources:
            if isinstance(r, dict):
                rid = r.get("id") or r.get("ResourceId") or r.get("name")
                if not rid:
                    continue
                cost = cost_map.get(rid, 0.0)
                export_data.append({
                    "ID": rid,
                    "名称": r.get("name") or rid,
                    "类型": type.upper(),
                    "状态": str(r.get("status") or "Running"),
                    "区域": str(r.get("region") or r.get("RegionId") or ""),
                    "规格": str(r.get("spec") or "-"),
                    "月成本(¥)": float(cost),
                    "创建时间": r.get("created_time") or "-",
                })
            else:
                cost = cost_map.get(r.id) or _estimate_monthly_cost(r)
                export_data.append({
                    "ID": r.id,
                    "名称": r.name or r.id,
                    "类型": type.upper(),
                    "状态": r.status.value if hasattr(r.status, "value") else str(r.status),
                    "区域": r.region,
                    "规格": r.spec or "-",
                    "月成本(¥)": float(cost),
                    "创建时间": r.created_time.isoformat() if hasattr(r, "created_time") and r.created_time else "-",
                })
        
        # 生成导出文件
        if format == "csv":
            import csv
            import io
            from fastapi.responses import StreamingResponse
            
            output = io.StringIO()
            if export_data:
                writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
                writer.writeheader()
                writer.writerows(export_data)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=resources_{type}_{datetime.now().strftime('%Y%m%d')}.csv"}
            )
        elif format == "excel":
            try:
                import pandas as pd
                import io
                from fastapi.responses import StreamingResponse
                
                df = pd.DataFrame(export_data)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='资源列表')
                
                output.seek(0)
                return StreamingResponse(
                    iter([output.read()]),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=resources_{type}_{datetime.now().strftime('%Y%m%d')}.xlsx"}
                )
            except ImportError:
                logger.error("pandas 或 openpyxl 未安装，无法导出 Excel")
                raise HTTPException(status_code=500, detail="Excel 导出功能需要安装 pandas 和 openpyxl")
        
    except Exception as e:
        logger.error(f"导出资源列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")
