import logging
import time
from typing import Dict, List, Tuple

logger = logging.getLogger("IdleDetector")


class IdleDetector:
    """
    闲置资源检测器
    基于监控指标判断资源是否闲置
    """

    def __init__(self, rules: Dict = None):
        self.rules = rules or {}
        self.ecs_rules = self.rules.get("idle_rules", {}).get("ecs", {})
        
        # 兼容旧代码，如果没有配置规则，使用默认阈值作为回退
        self.thresholds = {
            "cpu_utilization": self.ecs_rules.get("cpu_threshold_percent", 5),
            "memory_utilization": 20, # 当前规则未配置内存，保留默认
            "internet_in_rate": self.ecs_rules.get("network_threshold_bytes_sec", 1000),
            "internet_out_rate": self.ecs_rules.get("network_threshold_bytes_sec", 1000),
            "disk_read_iops": 100,
            "disk_write_iops": 100,
        }

    def is_ecs_idle(self, metrics: Dict[str, float], instance_tags: List[Dict] = None) -> Tuple[bool, List[str]]:
        """
        判断ECS实例是否闲置

        Args:
            metrics: 监控指标字典
            instance_tags: 实例标签列表 [{"Key": "k", "Value": "v"}]
        
        Returns:
            (is_idle, reasons) - 是否闲置及原因列表
        """
        # 1. 检查白名单标签
        exclude_tags = self.ecs_rules.get("exclude_tags", [])
        if instance_tags and exclude_tags:
            for tag in instance_tags:
                tag_str = f"{tag.get('Key')}={tag.get('Value')}"
                tag_key = tag.get('Key')
                # 检查 key=value 或 key
                if tag_str in exclude_tags or tag_key in exclude_tags:
                    return False, [f"白名单标签豁免: {tag_str}"]

        conditions = []
        thresholds = self.thresholds

        # CPU利用率
        cpu_util = metrics.get("CPU利用率", 0)
        if cpu_util < thresholds.get("cpu_utilization", 5):
            conditions.append(
                f"CPU利用率 {cpu_util:.2f}% < {thresholds.get('cpu_utilization', 5)}%"
            )

        # 内存利用率
        memory_util = metrics.get("内存利用率", 0)
        if memory_util < thresholds.get("memory_utilization", 20):
            conditions.append(
                f"内存利用率 {memory_util:.2f}% < {thresholds.get('memory_utilization', 20)}%"
            )

        # 公网流量
        internet_in = metrics.get("公网入流量", 0)
        internet_out = metrics.get("公网出流量", 0)
        threshold_net = thresholds.get("internet_in_rate", 1000)
        if internet_in < threshold_net and internet_out < threshold_net:
            conditions.append("公网流量极低")

        # 磁盘IOPS
        disk_read_iops = metrics.get("磁盘读IOPS", 0)
        disk_write_iops = metrics.get("磁盘写IOPS", 0)
        if disk_read_iops < thresholds.get("disk_read_iops", 100) and disk_write_iops < thresholds.get("disk_write_iops", 100):
            conditions.append("磁盘IOPS极低")

        # 判断是否闲置: 至少需要2个指标满足才判定为闲置
        is_idle = len(conditions) >= 2
        return is_idle, conditions

    @staticmethod
    def fetch_ecs_metrics(provider, instance_id: str, days: int = 14) -> Dict[str, float]:
        """
        获取ECS实例的监控指标 (使用 CloudMonitor)
        
        Args:
            provider: AliyunProvider实例
            instance_id: 实例ID
            days: 查询天数
            
        Returns:
            监控指标字典 (Max值)
        """
        metrics_result = {}
        try:
            # 尝试使用 get_monitor_client (如果 provider 支持)
            if hasattr(provider, 'get_monitor_client'):
                monitor = provider.get_monitor_client()
                # CloudMonitor.get_ecs_metrics 返回的是 Max 值
                raw_metrics = monitor.get_ecs_metrics(instance_id, days)
                
                # 映射到 IdleDetector 使用的中文键
                metrics_result["CPU利用率"] = raw_metrics.get("max_cpu", 0)
                metrics_result["公网入流量"] = raw_metrics.get("max_internet_in", 0)
                metrics_result["公网出流量"] = raw_metrics.get("max_internet_out", 0)
                # 内存和磁盘暂时没有在 CloudMonitor.get_ecs_metrics 中实现，置为安全值(100)避免误判，或者保留0
                metrics_result["内存利用率"] = 100 # 暂不作为判断依据
                metrics_result["磁盘读IOPS"] = 100
                metrics_result["磁盘写IOPS"] = 100
            else:
                # Fallback to old logic or return empty
                logger.warning("Provider does not support get_monitor_client, skipping metrics.")
        except Exception as e:
            logger.warning(f"Failed to fetch metrics via CloudMonitor for {instance_id}: {e}")
            
        return metrics_result
