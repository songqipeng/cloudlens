import logging
from typing import Dict, List, Tuple
import time

logger = logging.getLogger("IdleDetector")

class IdleDetector:
    """
    闲置资源检测器
    基于监控指标判断资源是否闲置
    """
    
    # 默认阈值
    DEFAULT_THRESHOLDS = {
        "ecs": {
            "cpu_utilization": 5,      # CPU < 5%
            "memory_utilization": 20,  # 内存 < 20%
            "internet_in_rate": 1000,  # 公网入流量 < 1KB/s
            "internet_out_rate": 1000, # 公网出流量 < 1KB/s
            "disk_read_iops": 100,     # 磁盘读IOPS < 100
            "disk_write_iops": 100     # 磁盘写IOPS < 100
        },
        "rds": {
            "cpu_utilization": 10,
            "memory_utilization": 20,
            "connections_utilization": 20,
            "qps": 100,
            "tps": 10
        }
    }
    
    @staticmethod
    def is_ecs_idle(metrics: Dict[str, float], thresholds: Dict = None) -> Tuple[bool, List[str]]:
        """
        判断ECS实例是否闲置
        
        Args:
            metrics: 监控指标字典
            thresholds: 自定义阈值（可选）
        
        Returns:
            (is_idle, reasons) - 是否闲置及原因列表
        """
        if thresholds is None:
            thresholds = IdleDetector.DEFAULT_THRESHOLDS["ecs"]
        
        conditions = []
        
        # CPU利用率
        cpu_util = metrics.get("CPU利用率", 0)
        if cpu_util < thresholds.get("cpu_utilization", 5):
            conditions.append(f"CPU利用率 {cpu_util:.2f}% < {thresholds.get('cpu_utilization', 5)}%")
        
        # 内存利用率
        memory_util = metrics.get("内存利用率", 0)
        if memory_util < thresholds.get("memory_utilization", 20):
            conditions.append(f"内存利用率 {memory_util:.2f}% < {thresholds.get('memory_utilization', 20)}%")
        
        # 公网流量
        internet_in = metrics.get("公网入流量", 0)
        internet_out = metrics.get("公网出流量", 0)
        if internet_in < thresholds.get("internet_in_rate", 1000) and internet_out < thresholds.get("internet_out_rate", 1000):
            conditions.append("公网流量极低")
        
        # 磁盘IOPS
        disk_read_iops = metrics.get("磁盘读IOPS", 0)
        disk_write_iops = metrics.get("磁盘写IOPS", 0)
        if disk_read_iops < thresholds.get("disk_read_iops", 100) and disk_write_iops < thresholds.get("disk_write_iops", 100):
            conditions.append("磁盘IOPS极低")
        
        # 判断是否闲置（满足任一条件即可）
        is_idle = len(conditions) > 0
        return is_idle, conditions
    
    @staticmethod
    def fetch_ecs_metrics(provider, instance_id: str, days: int = 14) -> Dict[str, float]:
        """
        获取ECS实例的监控指标平均值
        
        Args:
            provider: AliyunProvider实例
            instance_id: 实例ID
            days: 查询天数
        
        Returns:
            监控指标平均值字典
        """
        metrics_result = {}
        end_time = int(round(time.time() * 1000))
        start_time = end_time - (days * 24 * 60 * 60 * 1000)
        
        # ECS关键监控指标
        metric_names = {
            "CPUUtilization": "CPU利用率",
            "memory_usedutilization": "内存利用率",
            "InternetInRate": "公网入流量",
            "InternetOutRate": "公网出流量",
            "disk_readiops": "磁盘读IOPS",
            "disk_writeiops": "磁盘写IOPS"
        }
        
        for metric_key, metric_display in metric_names.items():
            try:
                datapoints = provider.get_metric(instance_id, metric_key, start_time, end_time)
                
                if datapoints:
                    values = [float(dp.get("Average", 0)) for dp in datapoints if "Average" in dp]
                    if values:
                        metrics_result[metric_display] = sum(values) / len(values)
                    else:
                        metrics_result[metric_display] = 0
                else:
                    metrics_result[metric_display] = 0
                
                time.sleep(0.1)  # 避免API限流
            except Exception as e:
                logger.warning(f"Failed to fetch metric {metric_key} for {instance_id}: {e}")
                metrics_result[metric_display] = 0
        
        return metrics_result
