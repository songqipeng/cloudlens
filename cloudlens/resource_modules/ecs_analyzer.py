from typing import List, Dict, Tuple

from cloudlens.core.analyzer_registry import AnalyzerRegistry
from cloudlens.core.base_analyzer import BaseResourceAnalyzer
from cloudlens.core.idle_detector import IdleDetector
from cloudlens.providers.aliyun.provider import AliyunProvider


@AnalyzerRegistry.register("ecs", "ECS云服务器", "🖥️")
class ECSAnalyzer(BaseResourceAnalyzer):
    """基于 AliyunProvider 的 ECS 闲置分析"""

    def __init__(self, account_name: str, access_key_id: str, access_key_secret: str, region: str):
        super().__init__(access_key_id, access_key_secret, account_name)
        self.provider = AliyunProvider(account_name, access_key_id, access_key_secret, region)
        self.region = region

    def get_resource_type(self) -> str:
        return "ecs"

    def get_all_regions(self) -> List[str]:
        # 当前 Analyzer 仅使用账号默认 region
        return [self.region]

    def get_instances(self, region: str) -> List:
        return self.provider.list_instances()

    def get_metrics(self, region: str, instance_id: str, days: int = 14) -> Dict[str, float]:
        return IdleDetector.fetch_ecs_metrics(self.provider, instance_id, days)

    def is_idle(self, instance, metrics: Dict, thresholds: Dict = None) -> Tuple[bool, List[str]]:
        return IdleDetector.is_ecs_idle(metrics, thresholds)

    def get_optimization_suggestions(self, instance, metrics: Dict) -> str:
        return "考虑下线或降配以节省成本"

    def analyze(self, regions: List[str] = None, days: int = 14) -> List[Dict]:
        # 覆盖基类以适配 UnifiedResource 对象
        idle_resources = []
        instances = self.get_instances(self.region)
        for inst in instances:
            metrics = self.get_metrics(self.region, inst.id, days)
            is_idle, reasons = self.is_idle(inst, metrics)
            if is_idle:
                idle_resources.append(
                    {
                        "instance": inst,
                        "metrics": metrics,
                        "idle_conditions": reasons,
                        "optimization": self.get_optimization_suggestions(inst, metrics),
                        "region": inst.region,
                    }
                )
        return idle_resources
