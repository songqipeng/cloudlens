#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NAS资源分析模块
分析阿里云NAS文件存储的闲置情况，提供优化建议
"""

import json
import time
import sqlite3
import sys
from datetime import datetime
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from utils.concurrent_helper import process_concurrently
from utils.logger import get_logger
from utils.error_handler import ErrorHandler
from core.report_generator import ReportGenerator
from core.db_manager import DatabaseManager


class NASAnalyzer:
    """NAS资源分析器"""
    
    def __init__(self, access_key_id, access_key_secret, tenant_name=None):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.tenant_name = tenant_name or "default"
        self.db_name = 'nas_monitoring_data.db'
        self.logger = get_logger('nas_analyzer')
        self.db_manager = DatabaseManager(self.db_name)
        
    def init_database(self):
        """初始化NAS数据库"""
        extra_columns = {
            'storage_type': 'TEXT',
            'protocol_type': 'TEXT',
            'capacity': 'REAL'
        }
        self.db_manager.create_resource_table("nas", extra_columns)
        self.db_manager.create_monitoring_table("nas")
        self.logger.info("NAS数据库初始化完成")
    
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
        
        regions = []
        for region in data['Regions']['Region']:
            regions.append(region['RegionId'])
        
        return regions
    
    def get_nas_file_systems(self, region_id):
        """获取指定区域的NAS文件系统"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = CommonRequest()
            request.set_domain(f'nas.{region_id}.aliyuncs.com')
            request.set_method('POST')
            request.set_version('2017-06-26')
            request.set_action_name('DescribeFileSystems')
            request.add_query_param('PageSize', 100)
            request.add_query_param('PageNumber', 1)
            
            all_file_systems = []
            page_number = 1
            
            while True:
                request.add_query_param('PageNumber', page_number)
                response = client.do_action_with_exception(request)
                data = json.loads(response)
                
                if 'FileSystems' in data and 'FileSystem' in data['FileSystems']:
                    file_systems = data['FileSystems']['FileSystem']
                    if not isinstance(file_systems, list):
                        file_systems = [file_systems]
                    
                    if len(file_systems) == 0:
                        break
                    
                    for fs in file_systems:
                        all_file_systems.append({
                            'FileSystemId': fs.get('FileSystemId', ''),
                            'Description': fs.get('Description', ''),
                            'StorageType': fs.get('StorageType', ''),
                            'ProtocolType': fs.get('ProtocolType', ''),
                            'Capacity': fs.get('Capacity', 0),
                            'MeteredSize': fs.get('MeteredSize', 0),
                            'RegionId': fs.get('RegionId', region_id),
                            'ZoneId': fs.get('ZoneId', ''),
                            'Status': fs.get('Status', ''),
                            'CreateTime': fs.get('CreateTime', '')
                        })
                    
                    page_number += 1
                    
                    if len(file_systems) < 100:
                        break
                else:
                    break
            
            return all_file_systems
        except Exception as e:
            error = ErrorHandler.handle_api_error(e, "NAS", region_id)
            ErrorHandler.handle_region_error(e, region_id, "NAS")
            return []
    
    def get_nas_metrics(self, region_id, file_system_id):
        """获取NAS文件系统的监控数据"""
        client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
        end_time = int(round(time.time() * 1000))
        start_time = end_time - 14 * 24 * 60 * 60 * 1000  # 14天前
        
        metrics = {
            'DiskSize': '存储容量',
            'DiskUsed': '已用容量',
            'DiskUtilization': '容量使用率',
            'FilesystemInodesFree': '可用inode数',
            'FilesystemInodesTotal': '总inode数',
            'FilesystemInodesUtilization': 'inode使用率'
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
                request.add_query_param('Namespace', 'acs_nas')
                request.add_query_param('MetricName', metric_name)
                request.add_query_param('StartTime', start_time)
                request.add_query_param('EndTime', end_time)
                request.add_query_param('Period', '86400')
                request.add_query_param('Dimensions', f'[{{"filesystemId":"{file_system_id}"}}]')
                
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
                error = ErrorHandler.handle_api_error(e, "NAS", region_id, file_system_id)
                result[display_name] = 0
        
        return result
    
    def save_nas_data(self, file_systems_data, monitoring_data):
        """保存NAS数据到数据库"""
        for fs in file_systems_data:
            instance_dict = {
                'InstanceId': fs.get('FileSystemId', ''),
                'InstanceName': fs.get('Description', ''),
                'InstanceType': fs.get('StorageType', ''),
                'Region': fs.get('RegionId', ''),
                'Status': fs.get('Status', ''),
                'CreationTime': fs.get('CreateTime', ''),
                'storage_type': fs.get('StorageType', ''),
                'protocol_type': fs.get('ProtocolType', ''),
                'capacity': fs.get('Capacity', 0)
            }
            self.db_manager.save_instance("nas", instance_dict)
        
        for fs_id, metrics in monitoring_data.items():
            self.db_manager.save_metrics_batch("nas", fs_id, metrics)
        
        self.logger.info(f"NAS数据保存完成: {len(file_systems_data)}个文件系统")
    
    def is_nas_idle(self, metrics):
        """判断NAS文件系统是否闲置"""
        capacity_util = metrics.get('容量使用率', 0)
        inode_util = metrics.get('inode使用率', 0)
        
        # NAS闲置判断标准（或关系）
        if capacity_util < 10:
            return True
        if inode_util < 10:
            return True
        
        return False
    
    def get_idle_reason(self, metrics):
        """获取闲置原因"""
        reasons = []
        capacity_util = metrics.get('容量使用率', 0)
        inode_util = metrics.get('inode使用率', 0)
        
        if capacity_util < 10:
            reasons.append(f"容量使用率 {capacity_util:.2f}% < 10%")
        if inode_util < 10:
            reasons.append(f"inode使用率 {inode_util:.2f}% < 10%")
        
        return ", ".join(reasons) if reasons else "未满足闲置条件"
    
    def get_optimization_suggestion(self, metrics, storage_type):
        """获取优化建议"""
        capacity_util = metrics.get('容量使用率', 0)
        
        if capacity_util < 5:
            return "考虑删除文件系统（使用率极低）"
        elif capacity_util < 20:
            return "考虑降配存储类型或容量"
        else:
            return "持续监控，考虑合并小文件系统"
    
    def get_monthly_cost(self, file_system_id, storage_type, region):
        """获取月度成本估算"""
        # 简化实现，实际应从Billing API获取
        return 200.0  # 默认200元/月
    
    def analyze_nas_resources(self):
        """分析NAS资源"""
        self.init_database()
        self.logger.info("开始NAS资源分析...")
        
        all_regions = self.get_all_regions()
        self.logger.info(f"获取到 {len(all_regions)} 个区域")
        
        all_file_systems = []
        
        def get_region_file_systems(region_item):
            region_id = region_item
            try:
                file_systems = self.get_nas_file_systems(region_id)
                return {'success': True, 'region': region_id, 'file_systems': file_systems}
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "NAS", region_id)
                return {'success': False, 'region': region_id, 'file_systems': []}
        
        results = process_concurrently(
            all_regions,
            get_region_file_systems,
            max_workers=10,
            description="NAS文件系统采集"
        )
        
        for result in results:
            if result and result.get('success'):
                all_file_systems.extend(result['file_systems'])
        
        self.logger.info(f"总共获取到 {len(all_file_systems)} 个NAS文件系统")
        
        def process_single_file_system(fs_item):
            fs = fs_item
            file_system_id = fs['FileSystemId']
            region = fs['RegionId']
            
            try:
                metrics = self.get_nas_metrics(region, file_system_id)
                return {
                    'success': True,
                    'file_system_id': file_system_id,
                    'metrics': metrics
                }
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "NAS", region, file_system_id)
                return {
                    'success': False,
                    'file_system_id': file_system_id,
                    'metrics': {},
                    'error': str(e)
                }
        
        self.logger.info("并发获取监控数据（最多10个并发线程）...")
        
        monitoring_results = process_concurrently(
            all_file_systems,
            process_single_file_system,
            max_workers=10,
            description="NAS监控数据采集"
        )
        
        all_monitoring_data = {}
        success_count = 0
        fail_count = 0
        
        for result in monitoring_results:
            if result and result.get('success'):
                all_monitoring_data[result['file_system_id']] = result['metrics']
                success_count += 1
            else:
                if result:
                    file_system_id = result.get('file_system_id', 'unknown')
                    all_monitoring_data[file_system_id] = {}
                    fail_count += 1
        
        self.logger.info(f"监控数据获取完成: 成功 {success_count} 个, 失败 {fail_count} 个")
        
        self.save_nas_data(all_file_systems, all_monitoring_data)
        
        idle_file_systems = []
        
        for fs in all_file_systems:
            file_system_id = fs['FileSystemId']
            metrics = all_monitoring_data.get(file_system_id, {})
            
            if self.is_nas_idle(metrics):
                idle_reason = self.get_idle_reason(metrics)
                optimization = self.get_optimization_suggestion(metrics, fs.get('StorageType', ''))
                monthly_cost = self.get_monthly_cost(file_system_id, fs.get('StorageType', ''), fs['RegionId'])
                
                idle_file_systems.append({
                    '文件系统ID': file_system_id,
                    '文件系统名称': fs.get('Description', ''),
                    '存储类型': fs.get('StorageType', ''),
                    '协议类型': fs.get('ProtocolType', ''),
                    '区域': fs['RegionId'],
                    '状态': fs.get('Status', ''),
                    '容量使用率(%)': metrics.get('容量使用率', 0),
                    'inode使用率(%)': metrics.get('inode使用率', 0),
                    '已用容量(GB)': metrics.get('已用容量', 0) / 1024 / 1024 / 1024 if metrics.get('已用容量', 0) > 0 else 0,
                    '闲置原因': idle_reason,
                    '优化建议': optimization,
                    '月成本(¥)': monthly_cost
                })
        
        self.logger.info(f"NAS分析完成: 发现 {len(idle_file_systems)} 个闲置文件系统")
        return idle_file_systems
    
    def generate_nas_report(self, idle_file_systems):
        """生成NAS报告"""
        if not idle_file_systems:
            self.logger.info("没有发现闲置的NAS文件系统")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        reports = ReportGenerator.generate_combined_report(
            resource_type="NAS",
            idle_instances=idle_file_systems,
            output_dir=".",
            tenant_name=self.tenant_name,
            timestamp=timestamp
        )
        
        self.logger.info(f"Excel报告已生成: {reports['excel']}")
        self.logger.info(f"HTML报告已生成: {reports['html']}")
        
        total_cost = sum(fs.get('月成本(¥)', 0) for fs in idle_file_systems)
        self.logger.info(f"NAS闲置文件系统统计: 总数量={len(idle_file_systems)}个, 总月成本={total_cost:,.2f}元, 预计年节省={total_cost * 12:,.2f}元")


def main():
    """NAS分析主函数"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        access_key_id = config['access_key_id']
        access_key_secret = config['access_key_secret']
    except FileNotFoundError:
        import logging
        logging.error("配置文件 config.json 不存在")
        return
    
    analyzer = NASAnalyzer(access_key_id, access_key_secret)
    idle_file_systems = analyzer.analyze_nas_resources()
    analyzer.generate_nas_report(idle_file_systems)


if __name__ == "__main__":
    main()

