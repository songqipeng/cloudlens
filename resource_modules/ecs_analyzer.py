#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECS资源分析模块（基于BaseResourceAnalyzer重构）
分析ECS实例的闲置情况，提供优化建议
"""

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException

from core.base_analyzer import BaseResourceAnalyzer
from core.report_generator import ReportGenerator
from core.threshold_manager import ThresholdManager
from utils.logger import get_logger
from utils.error_handler import ErrorHandler
from utils.concurrent_helper import process_concurrently
from utils.retry_helper import retry_api_call


class ECSAnalyzer(BaseResourceAnalyzer):
    """ECS资源分析器（基于BaseResourceAnalyzer）"""
    
    def __init__(self, access_key_id: str, access_key_secret: str, 
                 tenant_name: str = "default"):
        """初始化ECS分析器"""
        threshold_manager = ThresholdManager()
        super().__init__(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            tenant_name=tenant_name,
            threshold_manager=threshold_manager
        )
        self.logger = get_logger('ecs_analyzer')
        self.client = AcsClient(access_key_id, access_key_secret, 'cn-hangzhou')
    
    def get_resource_type(self) -> str:
        """获取资源类型"""
        return "ecs"
    
    def get_all_regions(self) -> List[str]:
        """获取所有可用区域"""
        try:
            request = CommonRequest()
            request.set_domain('ecs.cn-hangzhou.aliyuncs.com')
            request.set_method('POST')
            request.set_version('2014-05-26')
            request.set_action_name('DescribeRegions')
            
            response = self.client.do_action_with_exception(request)
            data = json.loads(response)
            
            regions = []
            for region in data['Regions']['Region']:
                regions.append(region['RegionId'])
            
            return regions
        except Exception as e:
            error = ErrorHandler.handle_api_error(e, "ECS")
            self.logger.error(f"获取区域列表失败: {e}")
            return []
    
    def get_instances(self, region: str) -> List[Dict]:
        """获取指定区域的ECS实例列表"""
        instances = []
        page_number = 1
        page_size = 100
        
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            
            while True:
                request = CommonRequest()
                request.set_domain(f'ecs.{region}.aliyuncs.com')
                request.set_method('POST')
                request.set_version('2014-05-26')
                request.set_action_name('DescribeInstances')
                request.add_query_param('PageSize', page_size)
                request.add_query_param('PageNumber', page_number)
                
                response = client.do_action_with_exception(request)
                data = json.loads(response)
                
                if 'Instances' in data and 'Instance' in data['Instances']:
                    page_instances = data['Instances']['Instance']
                    if not isinstance(page_instances, list):
                        page_instances = [page_instances]
                    
                    if len(page_instances) == 0:
                        break
                    
                    instances.extend(page_instances)
                    page_number += 1
                    
                    if len(page_instances) < page_size:
                        break
                else:
                    break
            
            return instances
        except Exception as e:
            error = ErrorHandler.handle_api_error(e, "ECS", region)
            ErrorHandler.handle_region_error(e, region, "ECS")
            return []
    
    def get_metrics(self, region: str, instance_id: str, days: int = 14) -> Dict[str, float]:
        """获取ECS实例的监控数据"""
        metrics = {}
        end_time = int(round(time.time() * 1000))
        start_time = end_time - (days * 24 * 60 * 60 * 1000)
        
        # ECS关键监控指标
        metric_names = {
            'CPUUtilization': 'CPU利用率',
            'memory_usedutilization': '内存利用率',
            'InternetInRate': '公网入流量',
            'InternetOutRate': '公网出流量',
            'IntranetInRate': '内网入流量',
            'IntranetOutRate': '内网出流量',
            'disk_readbytes': '磁盘读流量',
            'disk_writebytes': '磁盘写流量',
            'disk_readiops': '磁盘读IOPS',
            'disk_writeiops': '磁盘写IOPS'
        }
        
        client = AcsClient(self.access_key_id, self.access_key_secret, region)
        
        for metric_key, metric_display in metric_names.items():
            try:
                request = CommonRequest()
                request.set_domain(f'cms.{region}.aliyuncs.com')
                request.set_method('POST')
                request.set_version('2019-01-01')
                request.set_action_name('DescribeMetricData')
                request.add_query_param('Namespace', 'acs_ecs_dashboard')
                request.add_query_param('MetricName', metric_key)
                request.add_query_param('StartTime', start_time)
                request.add_query_param('EndTime', end_time)
                request.add_query_param('Period', '86400')
                request.add_query_param('Dimensions', f'[{{"instanceId":"{instance_id}"}}]')
                
                response = client.do_action_with_exception(request)
                data = json.loads(response)
                
                if 'Datapoints' in data and data['Datapoints']:
                    if isinstance(data['Datapoints'], str):
                        dps = json.loads(data['Datapoints'])
                    else:
                        dps = data['Datapoints']
                    
                    if dps:
                        values = [float(dp.get('Average', 0)) for dp in dps if 'Average' in dp]
                        if values:
                            metrics[metric_display] = sum(values) / len(values)
                        else:
                            metrics[metric_display] = 0
                    else:
                        metrics[metric_display] = 0
                else:
                    metrics[metric_display] = 0
                    
                time.sleep(0.1)  # 避免API限流
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "ECS", region, instance_id)
                metrics[metric_display] = 0
        
        return metrics
    
    def is_idle(self, instance: Dict, metrics: Dict, thresholds: Dict = None) -> Tuple[bool, List[str]]:
        """判断ECS实例是否闲置"""
        conditions = []
        
        # 获取阈值（从threshold_manager或传入）
        if thresholds is None:
            thresholds = self.threshold_manager.get_thresholds("ecs", "with_agent")
        
        cpu_util = metrics.get('CPU利用率', 0)
        memory_util = metrics.get('内存利用率', 0)
        
        # CPU利用率
        if cpu_util < thresholds.get('cpu_utilization', 5):
            conditions.append(f"CPU利用率 {cpu_util:.2f}% < {thresholds.get('cpu_utilization', 5)}%")
        
        # 内存利用率
        if memory_util < thresholds.get('memory_utilization', 20):
            conditions.append(f"内存利用率 {memory_util:.2f}% < {thresholds.get('memory_utilization', 20)}%")
        
        # 网络流量（公网）
        internet_in = metrics.get('公网入流量', 0)
        internet_out = metrics.get('公网出流量', 0)
        if internet_in < thresholds.get('internet_in_rate', 1000) and \
           internet_out < thresholds.get('internet_out_rate', 1000):
            conditions.append("公网流量极低")
        
        # 磁盘IOPS
        disk_read_iops = metrics.get('磁盘读IOPS', 0)
        disk_write_iops = metrics.get('磁盘写IOPS', 0)
        if disk_read_iops < thresholds.get('disk_read_iops', 100) and \
           disk_write_iops < thresholds.get('disk_write_iops', 100):
            conditions.append("磁盘IOPS极低")
        
        # 判断是否闲置（满足任一条件即可）
        is_idle = len(conditions) > 0
        return is_idle, conditions
    
    def get_optimization_suggestions(self, instance: Dict, metrics: Dict) -> str:
        """获取优化建议"""
        cpu_util = metrics.get('CPU利用率', 0)
        memory_util = metrics.get('内存利用率', 0)
        
        suggestions = []
        
        if cpu_util < 5 and memory_util < 20:
            suggestions.append("考虑删除实例（资源利用率极低）")
        elif cpu_util < 10:
            suggestions.append("考虑降配CPU规格")
        elif memory_util < 30:
            suggestions.append("考虑降配内存规格")
        
        if not suggestions:
            suggestions.append("持续监控，考虑合并小实例")
        
        return "; ".join(suggestions)
    
    def get_cost(self, region: str, instance_id: str) -> float:
        """获取实例成本（简化实现）"""
        # 实际实现可以从Billing API获取
        return 500.0  # 默认500元/月
    
    def analyze_ecs_resources(self) -> List[Dict]:
        """分析ECS资源（使用基类的analyze方法）"""
        self.logger.info("开始ECS资源分析...")
        
        idle_resources = self.analyze()
        
        # 转换为报告格式
        idle_instances = []
        for resource in idle_resources:
            instance = resource['instance']
            metrics = resource['metrics']
            
            idle_instances.append({
                '实例名称': instance.get('InstanceName', ''),
                '实例ID': instance.get('InstanceId', ''),
                '实例类型': instance.get('InstanceType', ''),
                '区域': resource['region'],
                '状态': instance.get('Status', ''),
                'CPU利用率(%)': metrics.get('CPU利用率', 0),
                '内存利用率(%)': metrics.get('内存利用率', 0),
                '闲置原因': ", ".join(resource['idle_conditions']),
                '优化建议': resource['optimization'],
                '月成本(¥)': resource['cost']
            })
        
        return idle_instances
    
    def generate_ecs_report(self, idle_instances: List[Dict], output_dir: str = "."):
        """生成ECS报告（使用统一ReportGenerator）"""
        if not idle_instances:
            self.logger.info("没有发现闲置的ECS实例")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        reports = ReportGenerator.generate_combined_report(
            resource_type="ECS",
            idle_instances=idle_instances,
            output_dir=output_dir,
            tenant_name=self.tenant_name,
            timestamp=timestamp
        )
        
        self.logger.info(f"Excel报告已生成: {reports['excel']}")
        self.logger.info(f"HTML报告已生成: {reports['html']}")


def main():
    """ECS分析主函数（新版本）"""
    import sys
    
    # 从配置文件或参数获取凭证
    tenant_name = sys.argv[1] if len(sys.argv) > 1 else "default"
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        tenant_config = config.get('tenants', {}).get(tenant_name, {})
        access_key_id = tenant_config.get('access_key_id')
        access_key_secret = tenant_config.get('access_key_secret')
        
        if not access_key_id or not access_key_secret:
            print("❌ 缺少访问凭证")
            return
        
        analyzer = ECSAnalyzer(access_key_id, access_key_secret, tenant_name)
        idle_instances = analyzer.analyze_ecs_resources()
        analyzer.generate_ecs_report(idle_instances)
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

