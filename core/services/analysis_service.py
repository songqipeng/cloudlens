import logging
from typing import List, Dict, Any, Tuple
from core.idle_detector import IdleDetector
from providers.aliyun.provider import AliyunProvider
from core.rules_manager import RulesManager
from core.cache import CacheManager
from core.config import ConfigManager

logger = logging.getLogger(__name__)

class AnalysisService:
    @staticmethod
    def analyze_idle_resources(account_name: str, days: int = 7, force_refresh: bool = False) -> Tuple[List[Dict], bool]:
        """
        Analyze idle resources for the given account.
        
        Args:
            account_name: Cloud account name
            days: Number of days to analyze
            force_refresh: Whether to force refresh cache
            
        Returns:
            (idle_instances, is_from_cache)
        """
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        if not account_config:
            raise ValueError(f"Account '{account_name}' not found")

        # 1. Check Cache
        cache = CacheManager(ttl_seconds=86400)
        cache_key = "idle_result"
        
        if not force_refresh:
            cached_data = cache.get(cache_key, account_name)
            if cached_data:
                return cached_data, True

        # 2. Load Rules
        rm = RulesManager()
        rules = rm.get_rules()

        # 3. Initialize Provider
        provider = AliyunProvider(
            account_name=account_config.name,
            access_key=account_config.access_key_id,
            secret_key=account_config.access_key_secret,
            region=account_config.region,
        )

        # 4. Fetch Resources
        try:
            instances = provider.list_instances()
        except Exception as e:
            logger.error(f"获取实例列表失败: {str(e)}")
            raise
        
        if not instances:
            # 即使没有实例，也保存空结果到缓存，避免重复查询
            cache.set(cache_key, account_name, [])
            return [], False

        # 5. Analyze
        idle_instances = []
        for inst in instances:
            try:
                # Metrics
                metrics = IdleDetector.fetch_ecs_metrics(provider, inst.id, days)
                
                # Detection
                detector = IdleDetector(rules)
                is_idle, reasons = detector.is_ecs_idle(metrics, inst.tags)
                
                if is_idle:
                    idle_instances.append({
                        "instance_id": inst.id,
                        "name": inst.name or "-",
                        "region": inst.region,
                        "spec": inst.spec,
                        "reasons": reasons,
                    })
            except Exception as e:
                logger.warning(f"分析实例 {inst.id if hasattr(inst, 'id') else 'unknown'} 失败: {str(e)}")
                # 继续处理下一个实例，不中断整个分析过程
                continue

        # 6. Save to Cache (即使为空也保存，避免重复分析)
        try:
            cache.set(cache_key, account_name, idle_instances)
        except Exception as e:
            logger.warning(f"保存缓存失败: {str(e)}")
            # 缓存失败不影响返回结果
            
        return idle_instances, False
