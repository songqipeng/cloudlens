#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PolarDB资源分析模块
分析阿里云PolarDB云原生数据库的闲置情况
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


class PolarDBAnalyzer:
    """PolarDB资源分析器"""
    
    def __init__(self, access_key_id, access_key_secret, tenant_name=None):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.tenant_name = tenant_name or "default"
        self.db_name = 'polardb_monitoring_data.db'
        self.logger = get_logger('polardb_analyzer')
        self.db_manager = DatabaseManager(self.db_name)
        
    def init_database(self):
        """初始化PolarDB数据库"""
        extra_columns = {
            'engine': 'TEXT',
            'engine_version': 'TEXT',
            'db_node_class': 'TEXT'
        }
        self.db_manager.create_resource_table("polardb", extra_columns)
        self.db_manager.create_monitoring_table("polardb")
        self.logger.info("PolarDB数据库初始化完成")
    
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
    
    def get_polardb_clusters(self, region_id):
        """获取指定区域的PolarDB集群"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = CommonRequest()
            request.set_domain(f'polardb.{region_id}.aliyuncs.com')
            request.set_method('POST')
            request.set_version('2017-08-01')
            request.set_action_name('DescribeDBClusters')
            request.add_query_param('PageSize', 100)
            request.add_query_param('PageNumber', 1)
            
            all_clusters = []
            page_number = 1
            
            while True:
                request.add_query_param('PageNumber', page_number)
                response = client.do_action_with_exception(request)
                data = json.loads(response)
                
                if 'Items' in data and 'DBCluster' in data['Items']:
                    clusters = data['Items']['DBCluster']
                    if not isinstance(clusters, list):
                        clusters = [clusters]
                    
                    if len(clusters) == 0:
                        break
                    
                    for cluster in clusters:
                        all_clusters.append({
                            'DBClusterId': cluster.get('DBClusterId', ''),
                            'DBClusterDescription': cluster.get('DBClusterDescription', ''),
                            'Engine': cluster.get('Engine', ''),
                            'DBVersion': cluster.get('DBVersion', ''),
                            'DBNodeClass': cluster.get('DBNodeClass', ''),
                            'RegionId': cluster.get('RegionId', region_id),
                            'DBClusterStatus': cluster.get('DBClusterStatus', ''),
                            'CreateTime': cluster.get('CreateTime', '')
                        })
                    
                    page_number += 1
                    if len(clusters) < 100:
                        break
                else:
                    break
            
            return all_clusters
        except Exception as e:
            error = ErrorHandler.handle_api_error(e, "PolarDB", region_id)
            ErrorHandler.handle_region_error(e, region_id, "PolarDB")
            return []
    
    def get_polardb_metrics(self, region_id, cluster_id):
        """获取PolarDB集群的监控数据"""
        client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
        end_time = int(round(time.time() * 1000))
        start_time = end_time - 14 * 24 * 60 * 60 * 1000
        
        metrics = {
            'CPUUtilization': 'CPU利用率',
            'MemoryUtilization': '内存利用率',
            'ConnectionUsage': '连接数使用率',
            'IOPSUsage': 'IOPS使用率',
            'DiskUsage': '磁盘使用率'
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
                request.add_query_param('Namespace', 'acs_polardb')
                request.add_query_param('MetricName', metric_name)
                request.add_query_param('StartTime', start_time)
                request.add_query_param('EndTime', end_time)
                request.add_query_param('Period', '86400')
                request.add_query_param('Dimensions', f'[{{"dbClusterId":"{cluster_id}"}}]')
                
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
                error = ErrorHandler.handle_api_error(e, "PolarDB", region_id, cluster_id)
                result[display_name] = 0
        
        return result
    
    def save_polardb_data(self, clusters_data, monitoring_data):
        """保存PolarDB数据到数据库"""
        for cluster in clusters_data:
            instance_dict = {
                'InstanceId': cluster.get('DBClusterId', ''),
                'InstanceName': cluster.get('DBClusterDescription', ''),
                'InstanceType': cluster.get('DBNodeClass', ''),
                'Region': cluster.get('RegionId', ''),
                'Status': cluster.get('DBClusterStatus', ''),
                'CreationTime': cluster.get('CreateTime', ''),
                'engine': cluster.get('Engine', ''),
                'engine_version': cluster.get('DBVersion', ''),
                'db_node_class': cluster.get('DBNodeClass', '')
            }
            self.db_manager.save_instance("polardb", instance_dict)
        
        for cluster_id, metrics in monitoring_data.items():
            self.db_manager.save_metrics_batch("polardb", cluster_id, metrics)
        
        self.logger.info(f"PolarDB数据保存完成: {len(clusters_data)}个集群")
    
    def is_polardb_idle(self, metrics):
        """判断PolarDB集群是否闲置"""
        cpu_util = metrics.get('CPU利用率', 0)
        memory_util = metrics.get('内存利用率', 0)
        connection_util = metrics.get('连接数使用率', 0)
        iops_util = metrics.get('IOPS使用率', 0)
        
        # PolarDB闲置判断标准（或关系）
        if cpu_util < 10:
            return True
        if memory_util < 20:
            return True
        if connection_util < 20:
            return True
        if iops_util < 10:
            return True
        
        return False
    
    def get_idle_reason(self, metrics):
        """获取闲置原因"""
        reasons = []
        cpu_util = metrics.get('CPU利用率', 0)
        memory_util = metrics.get('内存利用率', 0)
        connection_util = metrics.get('连接数使用率', 0)
        
        if cpu_util < 10:
            reasons.append(f"CPU利用率 {cpu_util:.2f}% < 10%")
        if memory_util < 20:
            reasons.append(f"内存利用率 {memory_util:.2f}% < 20%")
        if connection_util < 20:
            reasons.append(f"连接数使用率 {connection_util:.2f}% < 20%")
        
        return ", ".join(reasons) if reasons else "未满足闲置条件"
    
    def get_optimization_suggestion(self, metrics, db_node_class):
        """获取优化建议"""
        cpu_util = metrics.get('CPU利用率', 0)
        
        if cpu_util < 5:
            return "考虑删除集群（使用率极低）"
        elif cpu_util < 15:
            return "考虑降配节点规格"
        else:
            return "持续监控，考虑优化配置"
    
    def get_monthly_cost(self, cluster_id, db_node_class, region):
        """获取月度成本估算"""
        return 800.0  # 默认800元/月
    
    def analyze_polardb_resources(self):
        """分析PolarDB资源"""
        self.init_database()
        self.logger.info("开始PolarDB资源分析...")
        
        all_regions = self.get_all_regions()
        all_clusters = []
        
        def get_region_clusters(region_item):
            region_id = region_item
            try:
                clusters = self.get_polardb_clusters(region_id)
                return {'success': True, 'region': region_id, 'clusters': clusters}
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "PolarDB", region_id)
                return {'success': False, 'region': region_id, 'clusters': []}
        
        results = process_concurrently(
            all_regions,
            get_region_clusters,
            max_workers=10,
            description="PolarDB集群采集"
        )
        
        for result in results:
            if result and result.get('success'):
                all_clusters.extend(result['clusters'])
        
        self.logger.info(f"总共获取到 {len(all_clusters)} 个PolarDB集群")
        
        def process_single_cluster(cluster_item):
            cluster = cluster_item
            cluster_id = cluster['DBClusterId']
            region = cluster['RegionId']
            
            try:
                metrics = self.get_polardb_metrics(region, cluster_id)
                return {
                    'success': True,
                    'cluster_id': cluster_id,
                    'metrics': metrics
                }
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "PolarDB", region, cluster_id)
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
            description="PolarDB监控数据采集"
        )
        
        all_monitoring_data = {}
        for result in monitoring_results:
            if result and result.get('success'):
                all_monitoring_data[result['cluster_id']] = result['metrics']
        
        self.save_polardb_data(all_clusters, all_monitoring_data)
        
        idle_clusters = []
        for cluster in all_clusters:
            cluster_id = cluster['DBClusterId']
            metrics = all_monitoring_data.get(cluster_id, {})
            
            if self.is_polardb_idle(metrics):
                idle_reason = self.get_idle_reason(metrics)
                optimization = self.get_optimization_suggestion(metrics, cluster.get('DBNodeClass', ''))
                monthly_cost = self.get_monthly_cost(cluster_id, cluster.get('DBNodeClass', ''), cluster['RegionId'])
                
                idle_clusters.append({
                    '集群ID': cluster_id,
                    '集群名称': cluster.get('DBClusterDescription', ''),
                    '引擎': cluster.get('Engine', ''),
                    '版本': cluster.get('DBVersion', ''),
                    '节点规格': cluster.get('DBNodeClass', ''),
                    '区域': cluster['RegionId'],
                    '状态': cluster.get('DBClusterStatus', ''),
                    'CPU利用率(%)': metrics.get('CPU利用率', 0),
                    '内存利用率(%)': metrics.get('内存利用率', 0),
                    '连接数使用率(%)': metrics.get('连接数使用率', 0),
                    'IOPS使用率(%)': metrics.get('IOPS使用率', 0),
                    '闲置原因': idle_reason,
                    '优化建议': optimization,
                    '月成本(¥)': monthly_cost
                })
        
        self.logger.info(f"PolarDB分析完成: 发现 {len(idle_clusters)} 个闲置集群")
        return idle_clusters
    
    def generate_polardb_report(self, idle_clusters):
        """生成PolarDB报告"""
        if not idle_clusters:
            self.logger.info("没有发现闲置的PolarDB集群")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports = ReportGenerator.generate_combined_report(
            resource_type="PolarDB",
            idle_instances=idle_clusters,
            output_dir=".",
            tenant_name=self.tenant_name,
            timestamp=timestamp
        )
        
        self.logger.info(f"Excel报告已生成: {reports['excel']}")
        self.logger.info(f"HTML报告已生成: {reports['html']}")


def main():
    """PolarDB分析主函数"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        access_key_id = config['access_key_id']
        access_key_secret = config['access_key_secret']
    except FileNotFoundError:
        import logging
        logging.error("配置文件 config.json 不存在")
        return
    
    analyzer = PolarDBAnalyzer(access_key_id, access_key_secret)
    idle_clusters = analyzer.analyze_polardb_resources()
    analyzer.generate_polardb_report(idle_clusters)


if __name__ == "__main__":
    main()

