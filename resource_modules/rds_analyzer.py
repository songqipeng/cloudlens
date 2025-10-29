#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDS资源分析模块
分析RDS实例的闲置情况，提供优化建议
"""

import json
import time
import sqlite3
import pandas as pd
from datetime import datetime
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkrds.request.v20140815 import DescribeDBInstancesRequest
from aliyunsdkcms.request.v20190101 import DescribeMetricDataRequest


class RDSAnalyzer:
    """RDS资源分析器"""
    
    def __init__(self, access_key_id, access_key_secret):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.db_name = 'rds_monitoring_data.db'
        
    def init_database(self):
        """初始化RDS数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # 创建RDS实例表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS rds_instances (
            instance_id TEXT PRIMARY KEY,
            instance_name TEXT,
            instance_type TEXT,
            engine TEXT,
            engine_version TEXT,
            instance_class TEXT,
            region TEXT,
            status TEXT,
            creation_time TEXT,
            expire_time TEXT,
            monthly_cost REAL DEFAULT 0
        )
        ''')
        
        # 创建RDS监控数据表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS rds_monitoring_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id TEXT,
            metric_name TEXT,
            metric_value REAL,
            timestamp INTEGER,
            FOREIGN KEY (instance_id) REFERENCES rds_instances (instance_id)
        )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ RDS数据库初始化完成")
    
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
    
    def get_rds_instances(self, region_id):
        """获取指定区域的RDS实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeDBInstancesRequest.DescribeDBInstancesRequest()
            request.set_PageSize(100)
            
            response = client.do_action_with_exception(request)
            data = json.loads(response)
            
            instances = []
            if 'Items' in data and 'DBInstance' in data['Items']:
                for instance in data['Items']['DBInstance']:
                    instances.append({
                        'InstanceId': instance['DBInstanceId'],
                        'DBInstanceDescription': instance.get('DBInstanceDescription', ''),
                        'DBInstanceType': instance.get('DBInstanceType', ''),
                        'Engine': instance.get('Engine', ''),
                        'EngineVersion': instance.get('EngineVersion', ''),
                        'DBInstanceClass': instance.get('DBInstanceClass', ''),
                        'DBInstanceStatus': instance.get('DBInstanceStatus', ''),
                        'CreateTime': instance.get('CreateTime', ''),
                        'ExpireTime': instance.get('ExpireTime', ''),
                        'Region': region_id
                    })
            
            return instances
        except Exception as e:
            print(f"获取RDS实例失败 {region_id}: {str(e)}")
            return []
    
    def get_rds_metrics(self, region_id, instance_id):
        """获取RDS实例的监控数据"""
        client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
        end_time = int(round(time.time() * 1000))
        start_time = end_time - 14 * 24 * 60 * 60 * 1000  # 14天前
        
        # RDS监控指标（使用正确的指标名称）
        metrics = {
            'CpuUsage': 'CPU利用率',
            'MemoryUsage': '内存利用率',
            'ConnectionUsage': '连接数使用率',
            'MySQL_QPS': '每秒查询数',
            'MySQL_TPS': '每秒事务数',
            'MySQL_ComSelect': 'SELECT查询数',
            'MySQL_ComInsert': 'INSERT操作数',
            'MySQL_ComUpdate': 'UPDATE操作数',
            'MySQL_ComDelete': 'DELETE操作数',
            'MySQL_ThreadsConnected': '连接线程数',
            'MySQL_ThreadsRunning': '运行线程数',
            'MySQL_SlowQueries': '慢查询数',
            'MySQL_OpenFiles': '打开文件数',
            'MySQL_OpenTables': '打开表数',
            'MySQL_SelectScan': '扫描查询数'
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
                request.add_query_param('Namespace', 'acs_rds_dashboard')
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
    
    def save_rds_data(self, instances_data, monitoring_data):
        """保存RDS数据到数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # 保存实例数据
        for instance in instances_data:
            cursor.execute('''
            INSERT OR REPLACE INTO rds_instances 
            (instance_id, instance_name, instance_type, engine, engine_version, 
             instance_class, region, status, creation_time, expire_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                instance['InstanceId'],
                instance['DBInstanceDescription'],
                instance['DBInstanceType'],
                instance['Engine'],
                instance['EngineVersion'],
                instance['DBInstanceClass'],
                instance['Region'],
                instance['DBInstanceStatus'],
                instance['CreateTime'],
                instance['ExpireTime']
            ))
        
        # 保存监控数据
        for instance_id, metrics in monitoring_data.items():
            for metric_name, metric_value in metrics.items():
                cursor.execute('''
                INSERT INTO rds_monitoring_data 
                (instance_id, metric_name, metric_value, timestamp)
                VALUES (?, ?, ?, ?)
                ''', (instance_id, metric_name, metric_value, int(time.time())))
        
        conn.commit()
        conn.close()
        print(f"✅ RDS数据保存完成: {len(instances_data)}个实例")
    
    def is_rds_idle(self, metrics):
        """判断RDS实例是否闲置"""
        # RDS闲置判断标准（或关系）
        cpu_util = metrics.get('CPU利用率', 0)
        memory_util = metrics.get('内存利用率', 0)
        connection_usage = metrics.get('连接数使用率', 0)
        qps = metrics.get('每秒查询数', 0)
        tps = metrics.get('每秒事务数', 0)
        threads_connected = metrics.get('连接线程数', 0)
        threads_running = metrics.get('运行线程数', 0)
        
        # 闲置条件（满足任一即判定为闲置）
        idle_conditions = [
            cpu_util < 10,  # CPU利用率低于10%
            memory_util < 20,  # 内存利用率低于20%
            connection_usage < 20,  # 连接数使用率低于20%
            qps < 100,  # QPS低于100
            tps < 10,  # TPS低于10
            threads_connected < 10,  # 连接线程数低于10
            threads_running < 5  # 运行线程数低于5
        ]
        
        return any(idle_conditions)
    
    def get_idle_reason(self, metrics):
        """获取闲置原因"""
        reasons = []
        
        cpu_util = metrics.get('CPU利用率', 0)
        memory_util = metrics.get('内存利用率', 0)
        connection_usage = metrics.get('连接数使用率', 0)
        qps = metrics.get('每秒查询数', 0)
        tps = metrics.get('每秒事务数', 0)
        threads_connected = metrics.get('连接线程数', 0)
        threads_running = metrics.get('运行线程数', 0)
        
        if cpu_util < 10:
            reasons.append(f"CPU利用率({cpu_util:.1f}%) < 10%")
        if memory_util < 20:
            reasons.append(f"内存利用率({memory_util:.1f}%) < 20%")
        if connection_usage < 20:
            reasons.append(f"连接数使用率({connection_usage:.1f}%) < 20%")
        if qps < 100:
            reasons.append(f"QPS({qps:.0f}) < 100")
        if tps < 10:
            reasons.append(f"TPS({tps:.0f}) < 10")
        if threads_connected < 10:
            reasons.append(f"连接线程数({threads_connected:.0f}) < 10")
        if threads_running < 5:
            reasons.append(f"运行线程数({threads_running:.0f}) < 5")
        
        return "; ".join(reasons)
    
    def get_optimization_suggestion(self, metrics, instance_class):
        """获取优化建议"""
        suggestions = []
        
        cpu_util = metrics.get('CPU利用率', 0)
        memory_util = metrics.get('内存利用率', 0)
        connection_usage = metrics.get('连接数使用率', 0)
        qps = metrics.get('每秒查询数', 0)
        tps = metrics.get('每秒事务数', 0)
        
        if cpu_util < 10 and memory_util < 20:
            suggestions.append("建议降配实例规格")
        elif cpu_util < 10:
            suggestions.append("建议降配CPU规格")
        elif memory_util < 20:
            suggestions.append("建议降配内存规格")
        
        if connection_usage < 20:
            suggestions.append("建议减少最大连接数")
        
        if qps < 100 and tps < 10:
            suggestions.append("建议使用更小的实例类型")
        
        return "; ".join(suggestions) if suggestions else "建议保持当前配置"
    
    def get_monthly_cost(self, instance_id, instance_class, region):
        """获取RDS实例月成本（简化版本，实际需要调用BSS API）"""
        # 这里简化处理，实际应该调用DescribeRenewalPrice API
        # 根据实例类型和区域返回估算成本
        cost_map = {
            'rds.mysql.s1.small': 200,
            'rds.mysql.s2.small': 300,
            'rds.mysql.s1.medium': 400,
            'rds.mysql.s2.medium': 600,
            'rds.mysql.s1.large': 800,
            'rds.mysql.s2.large': 1200,
            'rds.mysql.s1.xlarge': 1600,
            'rds.mysql.s2.xlarge': 2400,
        }
        
        return cost_map.get(instance_class, 500)  # 默认500元
    
    def analyze_rds_resources(self):
        """分析RDS资源"""
        print("🚀 开始RDS资源分析...")
        
        # 初始化数据库
        self.init_database()
        
        # 获取所有区域
        regions = self.get_all_regions()
        print(f"✅ 获取到 {len(regions)} 个区域")
        
        # 收集RDS实例和监控数据
        all_instances = []
        all_monitoring_data = {}
        
        for region in regions:
            print(f"🔍 检查区域: {region}")
            instances = self.get_rds_instances(region)
            
            if instances:
                print(f"  发现 {len(instances)} 个RDS实例")
                all_instances.extend(instances)
                
                # 获取监控数据
                for instance in instances:
                    instance_id = instance['InstanceId']
                    print(f"  获取监控数据: {instance_id}")
                    metrics = self.get_rds_metrics(region, instance_id)
                    all_monitoring_data[instance_id] = metrics
        
        # 保存数据
        self.save_rds_data(all_instances, all_monitoring_data)
        
        # 分析闲置实例
        idle_instances = []
        for instance in all_instances:
            instance_id = instance['InstanceId']
            metrics = all_monitoring_data.get(instance_id, {})
            
            if self.is_rds_idle(metrics):
                idle_reason = self.get_idle_reason(metrics)
                optimization = self.get_optimization_suggestion(metrics, instance['DBInstanceClass'])
                monthly_cost = self.get_monthly_cost(instance_id, instance['DBInstanceClass'], instance['Region'])
                
                idle_instances.append({
                    '实例ID': instance_id,
                    '实例名称': instance['DBInstanceDescription'],
                    '实例类型': instance['DBInstanceClass'],
                    '引擎': instance['Engine'],
                    '版本': instance['EngineVersion'],
                    '区域': instance['Region'],
                    '状态': instance['DBInstanceStatus'],
                    'CPU利用率(%)': metrics.get('CPU利用率', 0),
                    '内存利用率(%)': metrics.get('内存利用率', 0),
                    '连接数使用率(%)': metrics.get('连接数使用率', 0),
                    'QPS': metrics.get('每秒查询数', 0),
                    'TPS': metrics.get('每秒事务数', 0),
                    '连接线程数': metrics.get('连接线程数', 0),
                    '运行线程数': metrics.get('运行线程数', 0),
                    '慢查询数': metrics.get('慢查询数', 0),
                    '打开文件数': metrics.get('打开文件数', 0),
                    '打开表数': metrics.get('打开表数', 0),
                    'SELECT查询数': metrics.get('SELECT查询数', 0),
                    'INSERT操作数': metrics.get('INSERT操作数', 0),
                    'UPDATE操作数': metrics.get('UPDATE操作数', 0),
                    'DELETE操作数': metrics.get('DELETE操作数', 0),
                    '闲置原因': idle_reason,
                    '优化建议': optimization,
                    '月成本(¥)': monthly_cost
                })
        
        print(f"✅ RDS分析完成: 发现 {len(idle_instances)} 个闲置实例")
        return idle_instances
    
    def generate_rds_report(self, idle_instances):
        """生成RDS报告"""
        if not idle_instances:
            print("⚠️ 没有发现闲置的RDS实例")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成Excel报告
        df = pd.DataFrame(idle_instances)
        excel_file = f'rds_idle_report_{timestamp}.xlsx'
        df.to_excel(excel_file, index=False)
        print(f"✅ Excel报告已生成: {excel_file}")
        
        # 生成HTML报告
        html_file = f'rds_idle_report_{timestamp}.html'
        self.generate_html_report(idle_instances, html_file)
        print(f"✅ HTML报告已生成: {html_file}")
        
        # 统计信息
        total_cost = sum(instance['月成本(¥)'] for instance in idle_instances)
        print(f"📊 RDS闲置实例统计:")
        print(f"  总数量: {len(idle_instances)} 个")
        print(f"  总月成本: {total_cost:,.2f} 元")
        print(f"  预计年节省: {total_cost * 12:,.2f} 元")
    
    def generate_html_report(self, idle_instances, filename):
        """生成HTML报告"""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RDS闲置实例分析报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}
        .summary {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .metric {{ font-weight: bold; color: #e74c3c; }}
        .low-utilization {{ background-color: #fff3cd; }}
        .footer {{ margin-top: 30px; padding: 15px; background: #34495e; color: white; text-align: center; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🗄️ RDS闲置实例分析报告</h1>
        
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
                    <th>引擎</th>
                    <th>区域</th>
                    <th>状态</th>
                    <th>CPU利用率(%)</th>
                    <th>内存利用率(%)</th>
                    <th>连接数使用率(%)</th>
                    <th>QPS</th>
                    <th>TPS</th>
                    <th>连接线程数</th>
                    <th>运行线程数</th>
                    <th>慢查询数</th>
                    <th>打开文件数</th>
                    <th>打开表数</th>
                    <th>SELECT查询数</th>
                    <th>INSERT操作数</th>
                    <th>UPDATE操作数</th>
                    <th>DELETE操作数</th>
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
                    <td>{instance['引擎']}</td>
                    <td>{instance['区域']}</td>
                    <td>{instance['状态']}</td>
                    <td><span class="metric">{instance['CPU利用率(%)']:.1f}%</span></td>
                    <td><span class="metric">{instance['内存利用率(%)']:.1f}%</span></td>
                    <td><span class="metric">{instance['连接数使用率(%)']:.1f}%</span></td>
                    <td><span class="metric">{instance['QPS']:.0f}</span></td>
                    <td><span class="metric">{instance['TPS']:.0f}</span></td>
                    <td><span class="metric">{instance['连接线程数']:.0f}</span></td>
                    <td><span class="metric">{instance['运行线程数']:.0f}</span></td>
                    <td><span class="metric">{instance['慢查询数']:.0f}</span></td>
                    <td><span class="metric">{instance['打开文件数']:.0f}</span></td>
                    <td><span class="metric">{instance['打开表数']:.0f}</span></td>
                    <td><span class="metric">{instance['SELECT查询数']:.0f}</span></td>
                    <td><span class="metric">{instance['INSERT操作数']:.0f}</span></td>
                    <td><span class="metric">{instance['UPDATE操作数']:.0f}</span></td>
                    <td><span class="metric">{instance['DELETE操作数']:.0f}</span></td>
                    <td>{instance['闲置原因']}</td>
                    <td>{instance['优化建议']}</td>
                    <td>{instance['月成本(¥)']:,.2f}</td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>📋 闲置判断标准: CPU利用率 < 10% 或 内存利用率 < 20% 或 连接数使用率 < 20% 或 QPS < 100 或 TPS < 10 或 连接线程数 < 10 或 运行线程数 < 5</p>
            <p>💡 建议: 根据优化建议进行资源配置调整，预计可节省成本30-50%</p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)


def main():
    """RDS分析主函数"""
    # 读取配置文件
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        access_key_id = config['access_key_id']
        access_key_secret = config['access_key_secret']
    except FileNotFoundError:
        print("❌ 配置文件 config.json 不存在")
        return
    
    # 创建RDS分析器
    analyzer = RDSAnalyzer(access_key_id, access_key_secret)
    
    # 分析RDS资源
    idle_instances = analyzer.analyze_rds_resources()
    
    # 生成报告
    analyzer.generate_rds_report(idle_instances)


if __name__ == "__main__":
    main()
