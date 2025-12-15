
from typing import List, Dict, Any, Tuple
from core.idle_detector import IdleDetector
from providers.aliyun.provider import AliyunProvider
from core.rules_manager import RulesManager
from core.cache import CacheManager
from core.config import ConfigManager

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
        instances = provider.list_instances()
        if not instances:
            return [], False

        # 5. Analyze
        idle_instances = []
        for inst in instances:
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

        # 6. Save to Cache
        if idle_instances:
            cache.set(cache_key, account_name, idle_instances)
            
        return idle_instances, False
