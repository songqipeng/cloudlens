
import json
import logging
import datetime
from typing import List, Dict, Any, Optional

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from cloudlens.core.config import CloudAccount

logger = logging.getLogger(__name__)

class CloudMonitor:
    """阿里云云监控 (CMS) 客户端封装"""

    def __init__(self, account_config: CloudAccount):
        self.client = AcsClient(
            account_config.access_key_id,
            account_config.access_key_secret,
            "cn-hangzhou"  # CMS API 通常使用 cn-hangzhou 或与资源同地域，这里默认杭州即可
        )
        self.account_name = account_config.name

    def get_metric_statistics(
        self, 
        namespace: str, 
        metric_name: str, 
        dimensions: str, 
        start_time: datetime.datetime, 
        end_time: datetime.datetime,
        period: int = 3600  # 默认 1 小时精度
    ) -> List[Dict[str, Any]]:
        """
        获取监控数据统计值 (DescribeMetricList)
        
        Args:
            namespace: 命名空间 (e.g., acs_ecs_dashboard)
            metric_name: 指标名称 (e.g., CPUUtilization)
            dimensions: 维度 (JSON string, e.g., [{"instanceId": "i-xxx"}])
            start_time: 开始时间
            end_time: 结束时间
            period: 聚合周期(秒)
            
        Returns:
            指标数据列表
        """
        try:
            request = CommonRequest()
            request.set_domain("metrics.aliyuncs.com")
            request.set_version("2019-01-01")
            request.set_action_name("DescribeMetricList")
            request.set_protocol_type("https")
            
            request.add_query_param("Namespace", namespace)
            request.add_query_param("MetricName", metric_name)
            request.add_query_param("Dimensions", dimensions)
            request.add_query_param("StartTime", int(start_time.timestamp() * 1000))
            request.add_query_param("EndTime", int(end_time.timestamp() * 1000))
            request.add_query_param("Period", str(period))
            
            response = self.client.do_action_with_exception(request)
            data = json.loads(response)
            
            # CMS 返回的 Datapoints 是 JSON 字符串，需要二次解析
            if "Datapoints" in data and data["Datapoints"]:
                return json.loads(data["Datapoints"])
            return []
            
        except Exception as e:
            logger.error(f"Failed to fetch metrics for {dimensions}: {e}")
            return []

    def get_ecs_metrics(self, instance_id: str, days: int = 7) -> Dict[str, float]:
        """
        获取 ECS 实例过去 N 天的关键性能指标 (Max)
        
        Args:
            instance_id: ECS 实例 ID
            days: 查询天数，默认 7 天
            
        Returns:
            Dict: { "max_cpu": 12.5, "max_memory": 45.2, "max_traffic_in": 1024, ... }
        """
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=days)
        dimensions = json.dumps([{"instanceId": instance_id}])
        
        # 1. CPU Utilization (Percent)
        cpu_data = self.get_metric_statistics(
            "acs_ecs_dashboard", "CPUUtilization", dimensions, start_time, end_time
        )
        max_cpu = max([p.get("Maximum", 0) for p in cpu_data]) if cpu_data else 0.0
        
        # 2. Memory Utilization (Percent)
        memory_data = self.get_metric_statistics(
            "acs_ecs_dashboard", "memory_usedutilization", dimensions, start_time, end_time
        )
        max_memory = max([p.get("Maximum", 0) for p in memory_data]) if memory_data else 0.0
        
        # 3. Internet In Rate (bits/s)
        net_in_data = self.get_metric_statistics(
            "acs_ecs_dashboard", "InternetInRate", dimensions, start_time, end_time
        )
        max_net_in = max([p.get("Maximum", 0) for p in net_in_data]) if net_in_data else 0.0

        # 4. Internet Out Rate (bits/s)
        net_out_data = self.get_metric_statistics(
            "acs_ecs_dashboard", "InternetOutRate", dimensions, start_time, end_time
        )
        max_net_out = max([p.get("Maximum", 0) for p in net_out_data]) if net_out_data else 0.0

        # 5. Disk Read IOPS
        disk_read_data = self.get_metric_statistics(
            "acs_ecs_dashboard", "DiskReadIOPS", dimensions, start_time, end_time
        )
        max_disk_read = max([p.get("Maximum", 0) for p in disk_read_data]) if disk_read_data else 0.0

        # 6. Disk Write IOPS
        disk_write_data = self.get_metric_statistics(
            "acs_ecs_dashboard", "DiskWriteIOPS", dimensions, start_time, end_time
        )
        max_disk_write = max([p.get("Maximum", 0) for p in disk_write_data]) if disk_write_data else 0.0

        return {
            "max_cpu": max_cpu,
            "max_memory": max_memory,
            "max_internet_in": max_net_in,
            "max_internet_out": max_net_out,
            "max_disk_read_iops": max_disk_read,
            "max_disk_write_iops": max_disk_write,
            "period_days": days
        }

    def get_rds_metrics(self, instance_id: str, days: int = 7) -> Dict[str, float]:
        """
        获取 RDS 实例过去 N 天的关键性能指标
        
        Args:
            instance_id: RDS 实例 ID
            days: 查询天数，默认 7 天
            
        Returns:
            Dict: { "max_cpu": 15.3, "max_memory": 60.5, "max_connections": 120, ... }
        """
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=days)
        dimensions = json.dumps([{"instanceId": instance_id}])
        
        # 1. CPU Utilization
        cpu_data = self.get_metric_statistics(
            "acs_rds_dashboard", "CPUUtilization", dimensions, start_time, end_time
        )
        max_cpu = max([p.get("Maximum", 0) for p in cpu_data]) if cpu_data else 0.0
        
        # 2. Memory Utilization
        memory_data = self.get_metric_statistics(
            "acs_rds_dashboard", "MemoryUsage", dimensions, start_time, end_time
        )
        max_memory = max([p.get("Maximum", 0) for p in memory_data]) if memory_data else 0.0
        
        # 3. Connection Count
        conn_data = self.get_metric_statistics(
            "acs_rds_dashboard", "ConnectionUsage", dimensions, start_time, end_time
        )
        max_connections = max([p.get("Maximum", 0) for p in conn_data]) if conn_data else 0.0
        
        # 4. IOPS Utilization
        iops_data = self.get_metric_statistics(
            "acs_rds_dashboard", "IOPSUsage", dimensions, start_time, end_time
        )
        max_iops = max([p.get("Maximum", 0) for p in iops_data]) if iops_data else 0.0
        
        return {
            "max_cpu": max_cpu,
            "max_memory": max_memory,
            "max_connections": max_connections,
            "max_iops": max_iops,
            "period_days": days
        }

    def get_slb_metrics(self, load_balancer_id: str, days: int = 7) -> Dict[str, float]:
        """
        获取 SLB 实例过去 N 天的关键性能指标
        
        Args:
            load_balancer_id: SLB 实例 ID
            days: 查询天数，默认 7 天
            
        Returns:
            Dict: { "max_qps": 1000, "max_connections": 5000, ... }
        """
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=days)
        dimensions = json.dumps([{"instanceId": load_balancer_id}])
        
        # 1. QPS (Queries Per Second)
        qps_data = self.get_metric_statistics(
            "acs_slb_dashboard", "Qps", dimensions, start_time, end_time
        )
        max_qps = max([p.get("Maximum", 0) for p in qps_data]) if qps_data else 0.0
        
        # 2. Connection Count
        conn_data = self.get_metric_statistics(
            "acs_slb_dashboard", "ConnectionUsage", dimensions, start_time, end_time
        )
        max_connections = max([p.get("Maximum", 0) for p in conn_data]) if conn_data else 0.0
        
        # 3. Incoming Traffic (bits/s)
        traffic_in_data = self.get_metric_statistics(
            "acs_slb_dashboard", "TrafficRXNew", dimensions, start_time, end_time
        )
        max_traffic_in = max([p.get("Maximum", 0) for p in traffic_in_data]) if traffic_in_data else 0.0
        
        # 4. Outgoing Traffic (bits/s)
        traffic_out_data = self.get_metric_statistics(
            "acs_slb_dashboard", "TrafficTXNew", dimensions, start_time, end_time
        )
        max_traffic_out = max([p.get("Maximum", 0) for p in traffic_out_data]) if traffic_out_data else 0.0
        
        return {
            "max_qps": max_qps,
            "max_connections": max_connections,
            "max_traffic_in": max_traffic_in,
            "max_traffic_out": max_traffic_out,
            "period_days": days
        }

    def batch_get_metrics(
        self,
        resource_type: str,
        resource_ids: List[str],
        days: int = 7
    ) -> Dict[str, Dict[str, float]]:
        """
        批量获取多个资源的监控指标
        
        Args:
            resource_type: 资源类型 ("ecs", "rds", "slb")
            resource_ids: 资源 ID 列表
            days: 查询天数，默认 7 天
            
        Returns:
            Dict: { "resource_id": { "max_cpu": 12.5, ... }, ... }
        """
        results = {}
        
        for resource_id in resource_ids:
            try:
                if resource_type == "ecs":
                    metrics = self.get_ecs_metrics(resource_id, days)
                elif resource_type == "rds":
                    metrics = self.get_rds_metrics(resource_id, days)
                elif resource_type == "slb":
                    metrics = self.get_slb_metrics(resource_id, days)
                else:
                    logger.warning(f"不支持的资源类型: {resource_type}")
                    continue
                    
                results[resource_id] = metrics
            except Exception as e:
                logger.error(f"获取资源 {resource_id} 的监控指标失败: {e}")
                results[resource_id] = {}
        
        return results
