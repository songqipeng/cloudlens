from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging
from web.backend.api_base import handle_api_error
from cloudlens.core.config import ConfigManager
from cloudlens.core.cache import CacheManager
from web.backend.i18n import get_locale_from_request, get_translation, Locale
from web.backend.api_resources import _get_cost_map, _estimate_monthly_cost_from_spec
from web.backend.api_dashboards import _get_provider_for_account

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

def _fetch_all_instances(account_config) -> List[Any]:
    """并发获取所有区域的实例"""
    from cloudlens.core.services.analysis_service import AnalysisService
    from cloudlens.providers.aliyun.provider import AliyunProvider
    import concurrent.futures

    instances = []
    try:
        all_regions = AnalysisService._get_all_regions(account_config.access_key_id, account_config.access_key_secret)
        
        def fetch_region_instances(region):
            try:
                rp = AliyunProvider(account_config.name, account_config.access_key_id, account_config.access_key_secret, region)
                if rp.check_instances_count() > 0:
                    return rp.list_instances()
            except: pass
            return []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_region_instances, r) for r in all_regions]
            for f in concurrent.futures.as_completed(futures):
                instances.extend(f.result())
                
    except Exception as e:
        logger.warning(f"获取实例列表失败: {e}")
        
    return instances

def _analyze_idle_with_metrics(instances, account_config) -> List[Dict]:
    """使用 CloudMonitor 分析闲置实例 (CPU < 5%)"""
    from cloudlens.providers.aliyun.provider import AliyunProvider
    import concurrent.futures
    
    idle_instances = []
    
    # 过滤出运行中的实例
    running_instances = [
        inst for inst in instances 
        if (hasattr(inst, 'status') and str(inst.status).upper() == 'RUNNING') or 
           (isinstance(inst, dict) and str(inst.get('status', '')).upper() == 'RUNNING')
    ]
    
    if not running_instances:
        return []
        
    # 定义单个分析任务
    def check_instance_metrics(inst):
        try:
            # 兼容对象和字典
            inst_id = inst.id if hasattr(inst, 'id') else inst.get('id')
            region = inst.region if hasattr(inst, 'region') else inst.get('region')
            inst_name = inst.name if hasattr(inst, 'name') else inst.get('name')
            spec = inst.spec if hasattr(inst, 'spec') else inst.get('spec')
            
            # 使用 AliyunProvider 获取 Monitor Client
            rp = AliyunProvider(account_config.name, account_config.access_key_id, account_config.access_key_secret, region)
            monitor = rp.get_monitor_client()
            
            # 获取过去 7 天指标
            metrics = monitor.get_ecs_metrics(inst_id, days=7)
            max_cpu = metrics.get('max_cpu', 0)
            
            # 闲置判定: Max CPU < 5% (可配置)
            if max_cpu < 5.0:
                cost = _get_cost_map("ecs", account_config).get(inst_id)
                if cost is None:
                    cost = _estimate_monthly_cost_from_spec(spec, "ecs")
                
                return {
                    "id": inst_id,
                    "name": inst_name,
                    "region": region,
                    "spec": spec,
                    "reason": f"Low CPU Usage (Max {round(max_cpu, 2)}% in 7 days)",
                    "savings": cost,
                    "metrics": metrics
                }
        except Exception as e:
            # logger.warning(f"Failed to check metrics for {inst_id}: {e}")
            pass
        return None

    # 并发执行检查 (CloudMonitor API 并发限制要注意，但 10-20 个线程通常 OK)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(check_instance_metrics, inst) for inst in running_instances]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                idle_instances.append(res)
                
    return idle_instances

@router.get("/optimization/suggestions")
def get_optimization_suggestions(
    account: Optional[str] = None, 
    force_refresh: bool = Query(False, description="强制刷新缓存"),
    locale: Optional[str] = Query("zh", description="语言设置: zh 或 en")
):
    """获取优化建议（带24小时缓存）"""
    try:
        # 获取语言设置
        lang: Locale = get_locale_from_request(
            request_headers=None,
            query_params={"locale": locale}
        )
        
        provider, account_name = _get_provider_for_account(account)
        
        # 初始化缓存管理器，TTL设置为24小时（86400秒）
        cache_manager = CacheManager(ttl_seconds=86400)
        
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
        
        from cloudlens.core.security_compliance import SecurityComplianceAnalyzer
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        
        suggestions = []
        
        # 0. 统一获取实例列表 (如果缓存中没有，则实时获取)
        instances = []
        instances_cache = cache_manager.get(resource_type="ecs_instances", account_name=account_name)
        if instances_cache and not force_refresh:
             instances = instances_cache
        else:
             instances_obj = _fetch_all_instances(account_config)
             # Convert to dict for caching
             instances = [inst.to_dict() if hasattr(inst, "to_dict") else inst for inst in instances_obj]
             if instances:
                 cm_hour = CacheManager(ttl_seconds=3600)
                 cm_hour.set(resource_type="ecs_instances", account_name=account_name, data=instances)

        # 1. 闲置资源建议 (基于 CloudMonitor 真实指标)
        # 优先使用特定的 idle_result 缓存，如果没有且 force_refresh=True 或者没有缓存，则计算
        idle_data = cache_manager.get(resource_type="idle_result", account_name=account_name)
        if (not idle_data) or force_refresh:
            # 实时分析
            logger.info("开始执行基于监控指标的闲置资源分析...")
            idle_data = _analyze_idle_with_metrics(instances, account_config)
            # 存入缓存
            if idle_data:
                cache_manager.set(resource_type="idle_result", account_name=account_name, data=idle_data)
            
        if idle_data:
            total_savings = sum(item.get("savings", 0) for item in idle_data)
            suggestions.append({
                "type": "idle_resources",
                "category": get_translation("optimization.idle_resources.category", lang),
                "priority": "high",
                "title": get_translation("optimization.idle_resources.title", lang),
                "description": f"发现 {len(idle_data)} 个低负载实例 (CPU < 5%)",
                "savings_potential": round(total_savings, 2),
                "resource_count": len(idle_data),
                "resources": idle_data[:10],
                "action": "release_or_downgrade",
                "recommendation": "建议释放或降配。实例过去7天CPU最高利用率低于5%。",
            })
        
        # 2. 停止实例建议 (复用 instances 列表)
        analyzer = SecurityComplianceAnalyzer()
        stopped = analyzer.check_stopped_instances(instances or [])
        if stopped:
            stopped_savings = 0.0
            if account_config:
                cost_map = _get_cost_map("ecs", account_config)
                for stop_item in stopped:
                    instance_id = stop_item.get("id")
                    if instance_id:
                        cost = cost_map.get(instance_id) or 300
                        stopped_savings += cost * 0.7
            
            suggestions.append({
                "type": "stopped_instances",
                "category": get_translation("optimization.stopped_instances.category", lang),
                "priority": "medium",
                "title": get_translation("optimization.stopped_instances.title", lang),
                "description": get_translation("optimization.stopped_instances.description", lang, count=len(stopped)),
                "savings_potential": round(stopped_savings, 2),
                "resource_count": len(stopped),
                "resources": stopped[:10],
                "action": "release",
                "recommendation": get_translation("optimization.stopped_instances.recommendation", lang),
            })
        
        # 3. 未绑定EIP建议
        try:
            eips_cache = cache_manager.get(resource_type="eip_list", account_name=account_name)
            if eips_cache:
                eips = eips_cache
            else:
                from cloudlens.core.services.analysis_service import AnalysisService
                all_regions = AnalysisService._get_all_regions(account_config.access_key_id, account_config.access_key_secret)
                
                from cloudlens.providers.aliyun.provider import AliyunProvider
                import concurrent.futures
                
                def fetch_region_eips(region):
                    try:
                        rp = AliyunProvider(account_config.name, account_config.access_key_id, account_config.access_key_secret, region)
                        return rp.list_eip()
                    except: pass
                    return []
                
                eips = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(fetch_region_eips, r) for r in all_regions]
                    for f in concurrent.futures.as_completed(futures):
                        eips.extend(f.result())
                
                if eips:
                    eips_dict = [e.to_dict() if hasattr(e, "to_dict") else e for e in eips]
                    # Create a new CacheManager with 1 hour TTL for this data
                    cm_hour = CacheManager(ttl_seconds=3600)
                    cm_hour.set(resource_type="eip_list", account_name=account_name, data=eips_dict)
                    eips = eips_dict
            
            if eips:
                eip_info = analyzer.analyze_eip_usage(eips)
                unbound_eips = eip_info.get("unbound_eips", [])
                if unbound_eips:
                    suggestions.append({
                        "type": "unbound_eips",
                        "category": get_translation("optimization.unbound_eips.category", lang),
                        "priority": "high",
                        "title": get_translation("optimization.unbound_eips.title", lang),
                        "description": get_translation("optimization.unbound_eips.description", lang, count=len(unbound_eips)),
                        "savings_potential": len(unbound_eips) * 20,
                        "resource_count": len(unbound_eips),
                        "resources": unbound_eips[:10],
                        "action": "release",
                        "recommendation": get_translation("optimization.unbound_eips.recommendation", lang),
                    })
        except Exception as e:
            logger.warning(f"EIP分析失败: {e}")
        
        # 按优先级排序
        suggestions.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "low"), 2))
        
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
        
        cache_manager.set(resource_type="optimization_suggestions", account_name=account_name, data=result)
        
        return {
            "success": True,
            "data": result,
            "cached": False,
        }
    except Exception as e:
        raise handle_api_error(e, "get_optimization_suggestions")
