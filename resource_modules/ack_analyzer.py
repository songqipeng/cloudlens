#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACK资源分析模块
分析阿里云ACK容器服务Kubernetes版的闲置情况
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


class ACKAnalyzer:
    """ACK资源分析器"""
    
    def __init__(self, access_key_id, access_key_secret, tenant_name=None):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.tenant_name = tenant_name or "default"
        self.db_name = 'ack_monitoring_data.db'
        self.logger = get_logger('ack_analyzer')
        self.db_manager = DatabaseManager(self.db_name)
        
    def init_database(self):
        """初始化ACK数据库"""
        extra_columns = {
            'cluster_type': 'TEXT',
            'kubernetes_version': 'TEXT',
            'node_count': 'INTEGER'
        }
        self.db_manager.create_resource_table("ack", extra_columns)
        self.db_manager.create_monitoring_table("ack")
        self.logger.info("ACK数据库初始化完成")
    
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
    
    def get_ack_clusters(self, region_id):
        """获取指定区域的ACK集群"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = CommonRequest()
            request.set_domain(f'cs.{region_id}.aliyuncs.com')
            request.set_method('POST')
            request.set_version('2015-12-15')
            request.set_action_name('DescribeClusters')
            
            response = client.do_action_with_exception(request)
            data = json.loads(response)
            
            clusters = []
            if 'clusters' in data:
                cluster_list = data['clusters']
                if not isinstance(cluster_list, list):
                    cluster_list = [cluster_list]
                
                for cluster in cluster_list:
                    clusters.append({
                        'ClusterId': cluster.get('cluster_id', ''),
                        'Name': cluster.get('name', ''),
                        'ClusterType': cluster.get('cluster_type', ''),
                        'State': cluster.get('state', ''),
                        'RegionId': cluster.get('region_id', region_id),
                        'KubernetesVersion': cluster.get('current_version', ''),
                        'NodeCount': cluster.get('size', 0)
                    })
            
            return clusters
        except Exception as e:
            error = ErrorHandler.handle_api_error(e, "ACK", region_id)
            ErrorHandler.handle_region_error(e, region_id, "ACK")
            return []
    
    def get_ack_metrics(self, region_id, cluster_id):
        """获取ACK集群的监控数据"""
        client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
        end_time = int(round(time.time() * 1000))
        start_time = end_time - 14 * 24 * 60 * 60 * 1000
        
        metrics = {
            'cpu_total': 'CPU总量',
            'cpu_request': 'CPU请求量',
            'memory_total': '内存总量',
            'memory_request': '内存请求量',
            'pod_count': 'Pod数量'
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
                request.add_query_param('Namespace', 'acs_cs')
                request.add_query_param('MetricName', metric_name)
                request.add_query_param('StartTime', start_time)
                request.add_query_param('EndTime', end_time)
                request.add_query_param('Period', '86400')
                request.add_query_param('Dimensions', f'[{{"clusterId":"{cluster_id}"}}]')
                
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
                error = ErrorHandler.handle_api_error(e, "ACK", region_id, cluster_id)
                result[display_name] = 0
        
        return result
    
    def save_ack_data(self, clusters_data, monitoring_data):
        """保存ACK数据到数据库"""
        for cluster in clusters_data:
            instance_dict = {
                'InstanceId': cluster.get('ClusterId', ''),
                'InstanceName': cluster.get('Name', ''),
                'InstanceType': cluster.get('ClusterType', ''),
                'Region': cluster.get('RegionId', ''),
                'Status': cluster.get('State', ''),
                'cluster_type': cluster.get('ClusterType', ''),
                'kubernetes_version': cluster.get('KubernetesVersion', ''),
                'node_count': cluster.get('NodeCount', 0)
            }
            self.db_manager.save_instance("ack", instance_dict)
        
        for cluster_id, metrics in monitoring_data.items():
            self.db_manager.save_metrics_batch("ack", cluster_id, metrics)
        
        self.logger.info(f"ACK数据保存完成: {len(clusters_data)}个集群")
    
    def is_ack_idle(self, metrics):
        """判断ACK集群是否闲置"""
        cpu_request = metrics.get('CPU请求量', 0)
        memory_request = metrics.get('内存请求量', 0)
        pod_count = metrics.get('Pod数量', 0)
        
        # ACK闲置判断标准（或关系）
        if cpu_request < 0.1:  # CPU请求小于0.1核
            return True
        if memory_request < 256:  # 内存请求小于256MB
            return True
        if pod_count < 1:  # Pod数量小于1
            return True
        
        return False
    
    def get_idle_reason(self, metrics):
        """获取闲置原因"""
        reasons = []
        cpu_request = metrics.get('CPU请求量', 0)
        memory_request = metrics.get('内存请求量', 0)
        pod_count = metrics.get('Pod数量', 0)
        
        if cpu_request < 0.1:
            reasons.append(f"CPU请求量 {cpu_request:.2f}核 < 0.1核")
        if memory_request < 256:
            reasons.append(f"内存请求量 {memory_request:.0f}MB < 256MB")
        if pod_count < 1:
            reasons.append(f"Pod数量 {pod_count:.0f} < 1")
        
        return ", ".join(reasons) if reasons else "未满足闲置条件"
    
    def get_optimization_suggestion(self, metrics, cluster_type):
        """获取优化建议"""
        pod_count = metrics.get('Pod数量', 0)
        
        if pod_count == 0:
            return "考虑删除集群（无运行Pod）"
        elif pod_count < 3:
            return "考虑合并小集群"
        else:
            return "持续监控，考虑节点缩容"
    
    def get_monthly_cost(self, cluster_id, node_count, region):
        """获取月度成本估算"""
        # 简化实现，按节点数估算
        return node_count * 300.0  # 默认每节点300元/月
    
    def analyze_ack_resources(self):
        """分析ACK资源"""
        self.init_database()
        self.logger.info("开始ACK资源分析...")
        
        all_regions = self.get_all_regions()
        all_clusters = []
        
        def get_region_clusters(region_item):
            region_id = region_item
            try:
                clusters = self.get_ack_clusters(region_id)
                return {'success': True, 'region': region_id, 'clusters': clusters}
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "ACK", region_id)
                return {'success': False, 'region': region_id, 'clusters': []}
        
        results = process_concurrently(
            all_regions,
            get_region_clusters,
            max_workers=10,
            description="ACK集群采集"
        )
        
        for result in results:
            if result and result.get('success'):
                all_clusters.extend(result['clusters'])
        
        self.logger.info(f"总共获取到 {len(all_clusters)} 个ACK集群")
        
        def process_single_cluster(cluster_item):
            cluster = cluster_item
            cluster_id = cluster['ClusterId']
            region = cluster['RegionId']
            
            try:
                metrics = self.get_ack_metrics(region, cluster_id)
                return {
                    'success': True,
                    'cluster_id': cluster_id,
                    'metrics': metrics
                }
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "ACK", region, cluster_id)
                return {
                    'success': False,
                    'cluster_id': cluster_id,
                    'metrics': {},
                    'error': str(e)
                }
        
        self.logger.info("并发获取监控数据...")
        monitoring_results = process_concurrently(
            all_clusters,
            process_single_cluster,
            max_workers=10,
            description="ACK监控数据采集"
        )
        
        all_monitoring_data = {}
        for result in monitoring_results:
            if result and result.get('success'):
                all_monitoring_data[result['cluster_id']] = result['metrics']
        
        self.save_ack_data(all_clusters, all_monitoring_data)
        
        idle_clusters = []
        for cluster in all_clusters:
            cluster_id = cluster['ClusterId']
            metrics = all_monitoring_data.get(cluster_id, {})
            
            if self.is_ack_idle(metrics):
                idle_reason = self.get_idle_reason(metrics)
                optimization = self.get_optimization_suggestion(metrics, cluster.get('ClusterType', ''))
                monthly_cost = self.get_monthly_cost(cluster_id, cluster.get('NodeCount', 0), cluster['RegionId'])
                
                idle_clusters.append({
                    '集群ID': cluster_id,
                    '集群名称': cluster.get('Name', ''),
                    '集群类型': cluster.get('ClusterType', ''),
                    'Kubernetes版本': cluster.get('KubernetesVersion', ''),
                    '节点数': cluster.get('NodeCount', 0),
                    '区域': cluster['RegionId'],
                    '状态': cluster.get('State', ''),
                    'CPU请求量(核)': metrics.get('CPU请求量', 0),
                    '内存请求量(MB)': metrics.get('内存请求量', 0),
                    'Pod数量': metrics.get('Pod数量', 0),
                    '闲置原因': idle_reason,
                    '优化建议': optimization,
                    '月成本(¥)': monthly_cost
                })
        
        self.logger.info(f"ACK分析完成: 发现 {len(idle_clusters)} 个闲置集群")
        return idle_clusters
    
    def generate_ack_report(self, idle_clusters):
        """生成ACK报告"""
        if not idle_clusters:
            self.logger.info("没有发现闲置的ACK集群")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports = ReportGenerator.generate_combined_report(
            resource_type="ACK",
            idle_instances=idle_clusters,
            output_dir=".",
            tenant_name=self.tenant_name,
            timestamp=timestamp
        )
        
        self.logger.info(f"Excel报告已生成: {reports['excel']}")
        self.logger.info(f"HTML报告已生成: {reports['html']}")


def main():
    """ACK分析主函数"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        access_key_id = config['access_key_id']
        access_key_secret = config['access_key_secret']
    except FileNotFoundError:
        import logging
        logging.error("配置文件 config.json 不存在")
        return
    
    analyzer = ACKAnalyzer(access_key_id, access_key_secret)
    idle_clusters = analyzer.analyze_ack_resources()
    analyzer.generate_ack_report(idle_clusters)


if __name__ == "__main__":
    main()

