#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis资源分析模块
分析Redis实例的闲置情况，提供优化建议
"""

import json
import time
import sqlite3
import pandas as pd
import sys
from datetime import datetime
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkr_kvstore.request.v20150101 import DescribeInstancesRequest
from utils.concurrent_helper import process_concurrently
from utils.logger import get_logger
from utils.error_handler import ErrorHandler


class RedisAnalyzer:
    """Redis资源分析器"""
    
    def __init__(self, access_key_id, access_key_secret):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.db_name = 'redis_monitoring_data.db'
        self.logger = get_logger('redis_analyzer')
        
    def init_database(self):
        """初始化Redis数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # 创建Redis实例表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS redis_instances (
            instance_id TEXT PRIMARY KEY,
            instance_name TEXT,
            instance_type TEXT,
            engine_version TEXT,
            instance_class TEXT,
            region TEXT,
            status TEXT,
            creation_time TEXT,
            expire_time TEXT,
            monthly_cost REAL DEFAULT 0
        )
        ''')
        
        # 创建Redis监控数据表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS redis_monitoring_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id TEXT,
            metric_name TEXT,
            metric_value REAL,
            timestamp INTEGER,
            FOREIGN KEY (instance_id) REFERENCES redis_instances (instance_id)
        )
        ''')
        
        conn.commit()
        conn.close()
        self.logger.info("Redis数据库初始化完成")
    
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
    
    def get_redis_instances(self, region_id):
        """获取指定区域的Redis实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeInstancesRequest.DescribeInstancesRequest()
            request.set_PageSize(100)
            
            response = client.do_action_with_exception(request)
            data = json.loads(response)
            
            instances = []
            if 'Instances' in data and 'KVStoreInstance' in data['Instances']:
                for instance in data['Instances']['KVStoreInstance']:
                    instances.append({
                        'InstanceId': instance['InstanceId'],
                        'InstanceName': instance.get('InstanceName', ''),
                        'InstanceType': instance.get('InstanceType', ''),
                        'EngineVersion': instance.get('EngineVersion', ''),
                        'InstanceClass': instance.get('InstanceClass', ''),
                        'InstanceStatus': instance.get('InstanceStatus', ''),
                        'CreateTime': instance.get('CreateTime', ''),
                        'EndTime': instance.get('EndTime', ''),
                        'Region': region_id
                    })
            
            return instances
        except Exception as e:
            error = ErrorHandler.handle_api_error(e, "Redis", region_id)
            ErrorHandler.handle_region_error(e, region_id, "Redis")
            return []
    
    def get_redis_metrics(self, region_id, instance_id):
        """获取Redis实例的监控数据"""
        client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
        end_time = int(round(time.time() * 1000))
        start_time = end_time - 14 * 24 * 60 * 60 * 1000  # 14天前
        
        # Redis监控指标（使用正确的指标名称）
        metrics = {
            'CpuUsage': 'CPU利用率',
            'MemoryUsage': '内存利用率',
            'ConnectionUsage': '连接数使用率',
            'IntranetIn': '内网入流量',
            'IntranetOut': '内网出流量',
            'UsedMemory': '已使用内存'
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
                request.add_query_param('Namespace', 'acs_kvstore')
                request.add_query_param('MetricName', metric_name)
                request.add_query_param('StartTime', start_time)
                request.add_query_param('EndTime', end_time)
                request.add_query_param('Period', '86400')  # 1天聚合
                request.add_query_param('Dimensions', f'[{{"instanceId":"{instance_id}"}}]')
                
                response = client.do_action_with_exception(request)
                data = json.loads(response)
                
                if 'Datapoints' in data and data['Datapoints']:
                    if isinstance(data['Datapoints'], str):
                        dps = json.loads(data['Datapoints'])
                    else:
                        dps = data['Datapoints']
                    
                    if dps and len(dps) > 0:
                        # 计算所有数据点的平均值
                        total = 0
                        count = 0
                        for dp in dps:
                            if 'Average' in dp and dp['Average'] is not None:
                                total += float(dp['Average'])
                                count += 1
                        
                        if count > 0:
                            result[display_name] = total / count
                        else:
                            result[display_name] = 0
                    else:
                        result[display_name] = 0
                else:
                    result[display_name] = 0
            except Exception as e:
                result[display_name] = 0
            
            time.sleep(0.1)  # 避免API限流
        
        return result
    
    def save_redis_data(self, instances_data, monitoring_data):
        """保存Redis数据到数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # 保存实例数据
        for instance in instances_data:
            cursor.execute('''
            INSERT OR REPLACE INTO redis_instances 
            (instance_id, instance_name, instance_type, engine_version, 
             instance_class, region, status, creation_time, expire_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                instance['InstanceId'],
                instance['InstanceName'],
                instance['InstanceType'],
                instance['EngineVersion'],
                instance['InstanceClass'],
                instance['Region'],
                instance['InstanceStatus'],
                instance['CreateTime'],
                instance['EndTime']
            ))
        
        # 保存监控数据
        for instance_id, metrics in monitoring_data.items():
            for metric_name, metric_value in metrics.items():
                cursor.execute('''
                INSERT INTO redis_monitoring_data 
                (instance_id, metric_name, metric_value, timestamp)
                VALUES (?, ?, ?, ?)
                ''', (instance_id, metric_name, metric_value, int(time.time())))
        
        conn.commit()
        conn.close()
        self.logger.info(f"Redis数据保存完成: {len(instances_data)}个实例")
    
    def is_redis_idle(self, metrics):
        """判断Redis实例是否闲置"""
        # Redis闲置判断标准（或关系）
        cpu_util = metrics.get('CPU利用率', 0)
        memory_util = metrics.get('内存利用率', 0)
        connection_usage = metrics.get('连接数使用率', 0)
        intranet_in = metrics.get('内网入流量', 0)
        intranet_out = metrics.get('内网出流量', 0)
        used_memory = metrics.get('已使用内存', 0)
        
        # 闲置条件（满足任一即判定为闲置）
        idle_conditions = [
            cpu_util < 10,  # CPU利用率低于10%
            memory_util < 20,  # 内存利用率低于20%
            connection_usage < 20,  # 连接数使用率低于20%
            intranet_in < 100,  # 内网入流量低于100KB/s
            intranet_out < 100,  # 内网出流量低于100KB/s
            used_memory < 10000000  # 已使用内存低于10MB
        ]
        
        return any(idle_conditions)
    
    def get_idle_reason(self, metrics):
        """获取闲置原因"""
        reasons = []
        
        cpu_util = metrics.get('CPU利用率', 0)
        memory_util = metrics.get('内存利用率', 0)
        connection_usage = metrics.get('连接数使用率', 0)
        intranet_in = metrics.get('内网入流量', 0)
        intranet_out = metrics.get('内网出流量', 0)
        used_memory = metrics.get('已使用内存', 0)
        
        if cpu_util < 10:
            reasons.append(f"CPU利用率({cpu_util:.1f}%) < 10%")
        if memory_util < 20:
            reasons.append(f"内存利用率({memory_util:.1f}%) < 20%")
        if connection_usage < 20:
            reasons.append(f"连接数使用率({connection_usage:.1f}%) < 20%")
        if intranet_in < 100:
            reasons.append(f"内网入流量({intranet_in:.0f}KB/s) < 100KB/s")
        if intranet_out < 100:
            reasons.append(f"内网出流量({intranet_out:.0f}KB/s) < 100KB/s")
        if used_memory < 10000000:
            reasons.append(f"已使用内存({used_memory/1024/1024:.1f}MB) < 10MB")
        
        return "; ".join(reasons)
    
    def get_optimization_suggestion(self, metrics, instance_class):
        """获取优化建议"""
        suggestions = []
        
        cpu_util = metrics.get('CPU利用率', 0)
        memory_util = metrics.get('内存利用率', 0)
        connection_usage = metrics.get('连接数使用率', 0)
        qps = metrics.get('每秒查询数', 0)
        hit_rate = metrics.get('命中率', 0)
        connected_clients = metrics.get('连接客户端数', 0)
        instantaneous_ops = metrics.get('瞬时每秒操作数', 0)
        
        if cpu_util < 10 and memory_util < 20:
            suggestions.append("建议降配实例规格")
        elif cpu_util < 10:
            suggestions.append("建议降配CPU规格")
        elif memory_util < 20:
            suggestions.append("建议降配内存规格")
        
        if connection_usage < 20:
            suggestions.append("建议减少最大连接数")
        
        if qps < 100 and instantaneous_ops < 50:
            suggestions.append("建议使用更小的实例类型")
        
        if hit_rate < 50:
            suggestions.append("建议优化缓存策略")
        
        if connected_clients < 10:
            suggestions.append("建议检查客户端连接")
        
        return "; ".join(suggestions) if suggestions else "建议保持当前配置"
    
    def get_monthly_cost(self, instance_id, instance_class, region):
        """获取Redis实例月成本（简化版本，实际需要调用BSS API）"""
        # 这里简化处理，实际应该调用DescribeRenewalPrice API
        # 根据实例类型和区域返回估算成本
        cost_map = {
            'redis.master.micro.default': 50,
            'redis.master.small.default': 100,
            'redis.master.mid.default': 200,
            'redis.master.large.default': 400,
            'redis.master.xlarge.default': 800,
            'redis.master.2xlarge.default': 1600,
            'redis.master.4xlarge.default': 3200,
            'redis.master.8xlarge.default': 6400,
            'redis.master.16xlarge.default': 12800,
            'redis.master.32xlarge.default': 25600,
        }
        
        return cost_map.get(instance_class, 200)  # 默认200元
    
    def analyze_redis_resources(self):
        """分析Redis资源"""
        self.logger.info("开始Redis资源分析...")
        
        # 初始化数据库
        self.init_database()
        
        # 获取所有区域
        regions = self.get_all_regions()
        self.logger.info(f"获取到 {len(regions)} 个区域")
        
        # 并发获取所有区域的实例
        self.logger.info("并发获取所有区域的Redis实例...")
        
        def get_region_instances(region_item):
            """获取单个区域的实例（用于并发）"""
            region = region_item
            try:
                instances = self.get_redis_instances(region)
                return {'region': region, 'instances': instances}
            except Exception as e:
                self.logger.warning(f"区域 {region} 获取实例失败: {e}")
                return {'region': region, 'instances': []}
        
        # 并发获取所有区域的实例
        region_results = process_concurrently(
            regions,
            get_region_instances,
            max_workers=10,
            description="获取Redis实例"
        )
        
        # 整理所有实例
        all_instances = []
        for result in region_results:
            if result and result.get('instances'):
                all_instances.extend(result['instances'])
                self.logger.info(f"{result['region']}: {len(result['instances'])} 个实例")
        
        if not all_instances:
            self.logger.warning("未发现任何Redis实例")
            return []
        
        self.logger.info(f"总共获取到 {len(all_instances)} 个Redis实例")
        
        # 定义单个实例处理函数（用于并发）
        def process_single_instance(instance_item):
            """处理单个实例（用于并发）"""
            instance = instance_item
            instance_id = instance['InstanceId']
            region = instance['Region']
            
            try:
                metrics = self.get_redis_metrics(region, instance_id)
                return {
                    'success': True,
                    'instance_id': instance_id,
                    'metrics': metrics
                }
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "Redis", region, instance_id)
                ErrorHandler.handle_instance_error(e, instance_id, region, "Redis", continue_on_error=True)
                return {
                    'success': False,
                    'instance_id': instance_id,
                    'metrics': {},
                    'error': str(e)
                }
        
        # 并发获取监控数据
        self.logger.info("并发获取监控数据（最多10个并发线程）...")
        
        def progress_callback(completed, total):
            progress_pct = completed / total * 100
            sys.stdout.write(f'\r📊 监控数据进度: {completed}/{total} ({progress_pct:.1f}%)')
            sys.stdout.flush()
        
        monitoring_results = process_concurrently(
            all_instances,
            process_single_instance,
            max_workers=10,
            description="Redis监控数据采集",
            progress_callback=progress_callback
        )
        
          # 换行
        
        # 整理监控数据
        all_monitoring_data = {}
        success_count = 0
        fail_count = 0
        
        for result in monitoring_results:
            if result and result.get('success'):
                all_monitoring_data[result['instance_id']] = result['metrics']
                success_count += 1
            else:
                if result:
                    instance_id = result.get('instance_id', 'unknown')
                    all_monitoring_data[instance_id] = {}
                    fail_count += 1
        
        self.logger.info(f"监控数据获取完成: 成功 {success_count} 个, 失败 {fail_count} 个")
        
        # 保存数据
        self.save_redis_data(all_instances, all_monitoring_data)
        
        # 分析闲置实例
        idle_instances = []
        for instance in all_instances:
            instance_id = instance['InstanceId']
            metrics = all_monitoring_data.get(instance_id, {})
            
            if self.is_redis_idle(metrics):
                idle_reason = self.get_idle_reason(metrics)
                optimization = self.get_optimization_suggestion(metrics, instance['InstanceClass'])
                monthly_cost = self.get_monthly_cost(instance_id, instance['InstanceClass'], instance['Region'])
                
                idle_instances.append({
                    '实例ID': instance_id,
                    '实例名称': instance['InstanceName'],
                    '实例类型': instance['InstanceClass'],
                    '引擎版本': instance['EngineVersion'],
                    '区域': instance['Region'],
                    '状态': instance['InstanceStatus'],
                    'CPU利用率(%)': metrics.get('CPU利用率', 0),
                    '内存利用率(%)': metrics.get('内存利用率', 0),
                    '连接数使用率(%)': metrics.get('连接数使用率', 0),
                    '内网入流量(KB/s)': metrics.get('内网入流量', 0),
                    '内网出流量(KB/s)': metrics.get('内网出流量', 0),
                    '已使用内存(MB)': metrics.get('已使用内存', 0) / 1024 / 1024,
                    '闲置原因': idle_reason,
                    '优化建议': optimization,
                    '月成本(¥)': monthly_cost
                })
        
        self.logger.info(f"Redis分析完成: 发现 {len(idle_instances)} 个闲置实例")
        return idle_instances
    
    def generate_redis_report(self, idle_instances):
        """生成Redis报告"""
        if not idle_instances:
            self.logger.warning("没有发现闲置的Redis实例")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成Excel报告
        df = pd.DataFrame(idle_instances)
        excel_file = f'redis_idle_report_{timestamp}.xlsx'
        df.to_excel(excel_file, index=False)
        self.logger.info(f"Excel报告已生成: {excel_file}")
        
        # 生成HTML报告
        html_file = f'redis_idle_report_{timestamp}.html'
        self.generate_html_report(idle_instances, html_file)
        self.logger.info(f"HTML报告已生成: {html_file}")
        
        # 统计信息
        total_cost = sum(instance['月成本(¥)'] for instance in idle_instances)
        self.logger.info(f"Redis闲置实例统计: 总数量={len(idle_instances)}个, 总月成本={total_cost:,.2f}元, 预计年节省={total_cost * 12:,.2f}元")
    
    def generate_html_report(self, idle_instances, filename):
        """生成HTML报告"""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Redis闲置实例分析报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}
        .summary {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #e74c3c; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .metric {{ font-weight: bold; color: #e74c3c; }}
        .low-utilization {{ background-color: #fff3cd; }}
        .footer {{ margin-top: 30px; padding: 15px; background: #34495e; color: white; text-align: center; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔴 Redis闲置实例分析报告</h1>
        
        <div class="summary">
            <h3>📊 报告摘要</h3>
            <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>闲置实例数量:</strong> {len(idle_instances)} 个</p>
            <p><strong>总月成本:</strong> {sum(instance['月成本(¥)'] for instance in idle_instances):,.2f} 元</p>
            <p><strong>预计年节省:</strong> {sum(instance['月成本(¥)'] for instance in idle_instances) * 12:,.2f} 元</p>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>实例名称</th>
                    <th>实例ID</th>
                    <th>实例类型</th>
                    <th>引擎版本</th>
                    <th>区域</th>
                    <th>状态</th>
                    <th>CPU利用率(%)</th>
                    <th>内存利用率(%)</th>
                    <th>连接数使用率(%)</th>
                    <th>内网入流量(KB/s)</th>
                    <th>内网出流量(KB/s)</th>
                    <th>已使用内存(MB)</th>
                    <th>闲置原因</th>
                    <th>优化建议</th>
                    <th>月成本(¥)</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for instance in idle_instances:
            html_content += f"""
                <tr>
                    <td>{instance['实例名称']}</td>
                    <td>{instance['实例ID']}</td>
                    <td>{instance['实例类型']}</td>
                    <td>{instance['引擎版本']}</td>
                    <td>{instance['区域']}</td>
                    <td>{instance['状态']}</td>
                    <td><span class="metric">{instance['CPU利用率(%)']:.1f}%</span></td>
                    <td><span class="metric">{instance['内存利用率(%)']:.1f}%</span></td>
                    <td><span class="metric">{instance['连接数使用率(%)']:.1f}%</span></td>
                    <td><span class="metric">{instance['内网入流量(KB/s)']:.1f}</span></td>
                    <td><span class="metric">{instance['内网出流量(KB/s)']:.1f}</span></td>
                    <td><span class="metric">{instance['已使用内存(MB)']:.1f}</span></td>
                    <td>{instance['闲置原因']}</td>
                    <td>{instance['优化建议']}</td>
                    <td>{instance['月成本(¥)']:,.2f}</td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>📋 闲置判断标准: CPU利用率 < 10% 或 内存利用率 < 20% 或 连接数使用率 < 20% 或 内网入流量 < 100KB/s 或 内网出流量 < 100KB/s 或 已使用内存 < 10MB</p>
            <p>💡 建议: 根据优化建议进行资源配置调整，预计可节省成本30-50%</p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)


def main():
    """Redis分析主函数"""
    # 读取配置文件
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        access_key_id = config['access_key_id']
        access_key_secret = config['access_key_secret']
    except FileNotFoundError:
        self.logger.error("配置文件 config.json 不存在")
        return
    
    # 创建Redis分析器
    analyzer = RedisAnalyzer(access_key_id, access_key_secret)
    
    # 分析Redis资源
    idle_instances = analyzer.analyze_redis_resources()
    
    # 生成报告
    analyzer.generate_redis_report(idle_instances)


if __name__ == "__main__":
    main()
