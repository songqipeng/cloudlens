#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECI资源分析模块
分析阿里云ECI弹性容器实例的闲置情况
"""

import json
import time
import sys
from datetime import datetime
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from utils.concurrent_helper import process_concurrently
from utils.logger import get_logger
from utils.error_handler import ErrorHandler
from core.report_generator import ReportGenerator
from core.db_manager import DatabaseManager


class ECIAnalyzer:
    """ECI资源分析器"""
    
    def __init__(self, access_key_id, access_key_secret, tenant_name=None):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.tenant_name = tenant_name or "default"
        self.db_name = 'eci_monitoring_data.db'
        self.logger = get_logger('eci_analyzer')
        self.db_manager = DatabaseManager(self.db_name)
        
    def init_database(self):
        """初始化ECI数据库"""
        extra_columns = {
            'cpu': 'REAL',
            'memory': 'REAL',
            'instance_type': 'TEXT'
        }
        self.db_manager.create_resource_table("eci", extra_columns)
        self.db_manager.create_monitoring_table("eci")
        self.logger.info("ECI数据库初始化完成")
    
    def get_all_regions(self):
        """获取所有可用区域"""
        client = AcsClient(self.access_key_id, self.access_key_secret, 'cn-hangzhou')
        request = CommonRequest()
        request.set_domain('ecs.cn-hangzhou.aliyuncs.com')
        request.set_method('POST')
        request.set_version('2014-05-26')
        request.set_action_name('DescribeRegions')
        response = client.do_action_with_exception(request)
        data = json.loads(response)
        return [region['RegionId'] for region in data['Regions']['Region']]
    
    def get_eci_container_groups(self, region_id):
        """获取指定区域的ECI容器组"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = CommonRequest()
            request.set_domain(f'eci.{region_id}.aliyuncs.com')
            request.set_method('POST')
            request.set_version('2018-08-28')
            request.set_action_name('DescribeContainerGroups')
            request.add_query_param('PageSize', 50)
            request.add_query_param('PageNumber', 1)
            
            all_groups = []
            page_number = 1
            
            while True:
                request.add_query_param('PageNumber', page_number)
                response = client.do_action_with_exception(request)
                data = json.loads(response)
                
                if 'ContainerGroups' in data and 'ContainerGroup' in data['ContainerGroups']:
                    groups = data['ContainerGroups']['ContainerGroup']
                    if not isinstance(groups, list):
                        groups = [groups]
                    
                    if len(groups) == 0:
                        break
                    
                    for group in groups:
                        all_groups.append({
                            'ContainerGroupId': group.get('ContainerGroupId', ''),
                            'ContainerGroupName': group.get('ContainerGroupName', ''),
                            'RegionId': group.get('RegionId', region_id),
                            'Status': group.get('Status', ''),
                            'Cpu': group.get('Cpu', 0),
                            'Memory': group.get('Memory', 0),
                            'InstanceType': group.get('InstanceType', ''),
                            'CreationTime': group.get('CreationTime', '')
                        })
                    
                    page_number += 1
                    if len(groups) < 50:
                        break
                else:
                    break
            
            return all_groups
        except Exception as e:
            error = ErrorHandler.handle_api_error(e, "ECI", region_id)
            ErrorHandler.handle_region_error(e, region_id, "ECI")
            return []
    
    def get_eci_metrics(self, region_id, container_group_id):
        """获取ECI容器组的监控数据"""
        client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
        end_time = int(round(time.time() * 1000))
        start_time = end_time - 14 * 24 * 60 * 60 * 1000
        
        metrics = {
            'CpuTotal': 'CPU总量',
            'MemoryTotal': '内存总量',
            'NetworkRxRate': '网络入流量',
            'NetworkTxRate': '网络出流量'
        }
        
        result = {}
        
        for metric_name, display_name in metrics.items():
            try:
                request = CommonRequest()
                request.set_domain(f'cms.{region_id}.aliyuncs.com')
                request.set_method('POST')
                request.set_version('2019-01-01')
                request.set_action_name('DescribeMetricData')
                request.add_query_param('RegionId', region_id)
                request.add_query_param('Namespace', 'acs_eci_dashboard')
                request.add_query_param('MetricName', metric_name)
                request.add_query_param('StartTime', start_time)
                request.add_query_param('EndTime', end_time)
                request.add_query_param('Period', '86400')
                request.add_query_param('Dimensions', f'[{{"containerGroupId":"{container_group_id}"}}]')
                
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
                            result[display_name] = sum(values) / len(values)
                        else:
                            result[display_name] = 0
                    else:
                        result[display_name] = 0
                else:
                    result[display_name] = 0
                    
                time.sleep(0.1)
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "ECI", region_id, container_group_id)
                result[display_name] = 0
        
        return result
    
    def save_eci_data(self, groups_data, monitoring_data):
        """保存ECI数据到数据库"""
        for group in groups_data:
            instance_dict = {
                'InstanceId': group.get('ContainerGroupId', ''),
                'InstanceName': group.get('ContainerGroupName', ''),
                'InstanceType': group.get('InstanceType', ''),
                'Region': group.get('RegionId', ''),
                'Status': group.get('Status', ''),
                'CreationTime': group.get('CreationTime', ''),
                'cpu': group.get('Cpu', 0),
                'memory': group.get('Memory', 0),
                'instance_type': group.get('InstanceType', '')
            }
            self.db_manager.save_instance("eci", instance_dict)
        
        for group_id, metrics in monitoring_data.items():
            self.db_manager.save_metrics_batch("eci", group_id, metrics)
        
        self.logger.info(f"ECI数据保存完成: {len(groups_data)}个容器组")
    
    def is_eci_idle(self, metrics):
        """判断ECI容器组是否闲置"""
        cpu_total = metrics.get('CPU总量', 0)
        memory_total = metrics.get('内存总量', 0)
        network_rx = metrics.get('网络入流量', 0)
        network_tx = metrics.get('网络出流量', 0)
        
        # ECI闲置判断标准
        if cpu_total < 0.1 and memory_total < 256:
            return True
        if network_rx < 1 and network_tx < 1:
            return True
        
        return False
    
    def get_idle_reason(self, metrics):
        """获取闲置原因"""
        reasons = []
        cpu_total = metrics.get('CPU总量', 0)
        memory_total = metrics.get('内存总量', 0)
        network_rx = metrics.get('网络入流量', 0)
        
        if cpu_total < 0.1:
            reasons.append(f"CPU总量 {cpu_total:.2f}核 < 0.1核")
        if memory_total < 256:
            reasons.append(f"内存总量 {memory_total:.0f}MB < 256MB")
        if network_rx < 1:
            reasons.append(f"网络流量极低")
        
        return ", ".join(reasons) if reasons else "未满足闲置条件"
    
    def get_optimization_suggestion(self, metrics, instance_type):
        """获取优化建议"""
        cpu_total = metrics.get('CPU总量', 0)
        
        if cpu_total < 0.1:
            return "考虑删除容器组（资源使用极低）"
        else:
            return "持续监控，考虑降配资源规格"
    
    def get_monthly_cost(self, container_group_id, cpu, memory, region):
        """获取月度成本估算"""
        # 简化实现，按CPU和内存估算
        return (cpu * 100 + memory / 1024 * 50)  # 粗略估算
    
    def analyze_eci_resources(self):
        """分析ECI资源"""
        self.init_database()
        self.logger.info("开始ECI资源分析...")
        
        all_regions = self.get_all_regions()
        all_groups = []
        
        def get_region_groups(region_item):
            region_id = region_item
            try:
                groups = self.get_eci_container_groups(region_id)
                return {'success': True, 'region': region_id, 'groups': groups}
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "ECI", region_id)
                return {'success': False, 'region': region_id, 'groups': []}
        
        results = process_concurrently(
            all_regions,
            get_region_groups,
            max_workers=10,
            description="ECI容器组采集"
        )
        
        for result in results:
            if result and result.get('success'):
                all_groups.extend(result['groups'])
        
        self.logger.info(f"总共获取到 {len(all_groups)} 个ECI容器组")
        
        def process_single_group(group_item):
            group = group_item
            group_id = group['ContainerGroupId']
            region = group['RegionId']
            
            try:
                metrics = self.get_eci_metrics(region, group_id)
                return {
                    'success': True,
                    'group_id': group_id,
                    'metrics': metrics
                }
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "ECI", region, group_id)
                return {
                    'success': False,
                    'group_id': group_id,
                    'metrics': {},
                    'error': str(e)
                }
        
        self.logger.info("并发获取监控数据...")
        monitoring_results = process_concurrently(
            all_groups,
            process_single_group,
            max_workers=10,
            description="ECI监控数据采集"
        )
        
        all_monitoring_data = {}
        for result in monitoring_results:
            if result and result.get('success'):
                all_monitoring_data[result['group_id']] = result['metrics']
        
        self.save_eci_data(all_groups, all_monitoring_data)
        
        idle_groups = []
        for group in all_groups:
            group_id = group['ContainerGroupId']
            metrics = all_monitoring_data.get(group_id, {})
            
            if self.is_eci_idle(metrics):
                idle_reason = self.get_idle_reason(metrics)
                optimization = self.get_optimization_suggestion(metrics, group.get('InstanceType', ''))
                monthly_cost = self.get_monthly_cost(group_id, group.get('Cpu', 0), group.get('Memory', 0), group['RegionId'])
                
                idle_groups.append({
                    '容器组ID': group_id,
                    '容器组名称': group.get('ContainerGroupName', ''),
                    '实例类型': group.get('InstanceType', ''),
                    'CPU(核)': group.get('Cpu', 0),
                    '内存(GB)': group.get('Memory', 0) / 1024,
                    '区域': group['RegionId'],
                    '状态': group.get('Status', ''),
                    'CPU总量(核)': metrics.get('CPU总量', 0),
                    '内存总量(MB)': metrics.get('内存总量', 0),
                    '网络入流量(KB/s)': metrics.get('网络入流量', 0),
                    '网络出流量(KB/s)': metrics.get('网络出流量', 0),
                    '闲置原因': idle_reason,
                    '优化建议': optimization,
                    '月成本(¥)': monthly_cost
                })
        
        self.logger.info(f"ECI分析完成: 发现 {len(idle_groups)} 个闲置容器组")
        return idle_groups
    
    def generate_eci_report(self, idle_groups):
        """生成ECI报告"""
        if not idle_groups:
            self.logger.info("没有发现闲置的ECI容器组")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports = ReportGenerator.generate_combined_report(
            resource_type="ECI",
            idle_instances=idle_groups,
            output_dir=".",
            tenant_name=self.tenant_name,
            timestamp=timestamp
        )
        
        self.logger.info(f"Excel报告已生成: {reports['excel']}")
        self.logger.info(f"HTML报告已生成: {reports['html']}")


def main():
    """ECI分析主函数"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        access_key_id = config['access_key_id']
        access_key_secret = config['access_key_secret']
    except FileNotFoundError:
        import logging
        logging.error("配置文件 config.json 不存在")
        return
    
    analyzer = ECIAnalyzer(access_key_id, access_key_secret)
    idle_groups = analyzer.analyze_eci_resources()
    analyzer.generate_eci_report(idle_groups)


if __name__ == "__main__":
    main()

