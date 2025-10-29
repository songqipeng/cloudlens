#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EIP（弹性公网IP）资源分析模块
分析EIP实例的闲置情况，提供优化建议
"""

import json
import time
import sqlite3
import pandas as pd
import sys
from datetime import datetime, timedelta
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkvpc.request.v20160428 import DescribeEipAddressesRequest
from utils.concurrent_helper import process_concurrently


class EIPAnalyzer:
    """EIP资源分析器"""
    
    def __init__(self, access_key_id, access_key_secret):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.db_name = 'eip_monitoring_data.db'
        self.init_database()
        
    def init_database(self):
        """初始化EIP数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # 创建EIP实例表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS eip_instances (
            allocation_id TEXT PRIMARY KEY,
            eip_address TEXT,
            instance_id TEXT,
            instance_type TEXT,
            instance_status TEXT,
            region TEXT,
            bandwidth INTEGER,
            charge_type TEXT,
            internet_charge_type TEXT,
            creation_time TEXT,
            monthly_cost REAL DEFAULT 0
        )
        ''')
        
        # 创建EIP监控数据表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS eip_monitoring_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            allocation_id TEXT,
            metric_name TEXT,
            metric_value REAL,
            timestamp INTEGER,
            FOREIGN KEY (allocation_id) REFERENCES eip_instances (allocation_id)
        )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ EIP数据库初始化完成")
    
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
    
    def get_eip_instances(self, region_id):
        """获取指定区域的EIP实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeEipAddressesRequest.DescribeEipAddressesRequest()
            request.set_PageSize(100)
            request.set_PageNumber(1)
            
            all_eips = []
            page_number = 1
            
            while True:
                request.set_PageNumber(page_number)
                response = client.do_action_with_exception(request)
                data = json.loads(response)
                
                if 'EipAddresses' in data and 'EipAddress' in data['EipAddresses']:
                    eips = data['EipAddresses']['EipAddress']
                    
                    if not eips:
                        break
                    
                    for eip in eips:
                        all_eips.append({
                            'AllocationId': eip['AllocationId'],
                            'IpAddress': eip.get('IpAddress', ''),
                            'InstanceId': eip.get('InstanceId', ''),
                            'InstanceType': eip.get('InstanceType', ''),
                            'Status': eip.get('Status', ''),
                            'Bandwidth': int(eip.get('Bandwidth', 0)),
                            'InternetChargeType': eip.get('InternetChargeType', ''),
                            'ChargeType': eip.get('ChargeType', ''),
                            'AllocationTime': eip.get('AllocationTime', ''),
                            'Region': region_id
                        })
                    
                    # 检查是否还有更多页面
                    total_count = data.get('TotalCount', 0)
                    if len(all_eips) >= total_count:
                        break
                    
                    page_number += 1
                else:
                    break
            
            return all_eips
        except Exception as e:
            print(f"获取EIP实例失败 {region_id}: {str(e)}")
            return []
    
    def get_eip_metrics(self, region_id, allocation_id, ip_address):
        """获取EIP实例的监控数据"""
        client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=14)
        
        # EIP监控指标
        metrics = {
            'InternetInRate': '入流量',
            'InternetOutRate': '出流量',
            'InternetInBandwidth': '入带宽',
            'InternetOutBandwidth': '出带宽',
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
                request.add_query_param('Namespace', 'acs_vpc_eip')
                request.add_query_param('MetricName', metric_name)
                request.add_query_param('StartTime', start_time.strftime('%Y-%m-%dT%H:%M:%SZ'))
                request.add_query_param('EndTime', end_time.strftime('%Y-%m-%dT%H:%M:%SZ'))
                request.add_query_param('Period', '86400')  # 1天聚合
                request.add_query_param('Dimensions', f'[{{"ip":"{ip_address}"}}]')
                request.add_query_param('Statistics', 'Average')
                
                response = client.do_action_with_exception(request)
                data = json.loads(response)
                
                if 'Datapoints' in data and data['Datapoints']:
                    if isinstance(data['Datapoints'], str):
                        dps = json.loads(data['Datapoints'])
                    else:
                        dps = data['Datapoints']
                    
                    if dps and len(dps) > 0:
                        # 计算平均值
                        values = [float(dp.get('Average', 0)) for dp in dps if dp.get('Average') is not None]
                        if values:
                            result[display_name] = sum(values) / len(values)
                        else:
                            result[display_name] = 0
                    else:
                        result[display_name] = 0
                else:
                    result[display_name] = 0
                    
            except Exception as e:
                print(f"    ⚠️  指标 {metric_name} 获取失败: {e}")
                result[display_name] = 0
        
        # 计算总流量（字节）
        traffic_in = result.get('入流量', 0)
        traffic_out = result.get('出流量', 0)
        total_traffic_bytes = (traffic_in + traffic_out) * 86400 * 14  # 转换为14天总流量（字节）
        result['总流量(MB)'] = total_traffic_bytes / (1024 * 1024)  # 转换为MB
        
        # 计算带宽使用率（在analyze_eip_instances中计算，因为需要实例的带宽信息）
        
        return result
    
    def is_eip_idle(self, instance, metrics, thresholds=None):
        """判断EIP实例是否闲置"""
        if thresholds is None:
            thresholds = {
                'unbound': True,
                'traffic_mb_total': 1,  # 14天总流量小于1MB
                'bandwidth_usage': 5,  # 带宽使用率小于5%
                'instance_stopped': True
            }
        
        idle_conditions = []
        
        # 1. 未绑定任何实例
        instance_id = instance.get('InstanceId', '')
        if not instance_id and thresholds['unbound']:
            idle_conditions.append("未绑定任何实例")
        
        # 2. 绑定实例已停止或删除
        instance_status = instance.get('InstanceStatus', '')
        if instance_status in ['Stopped', 'Deleted', 'Stopping'] and thresholds['instance_stopped']:
            idle_conditions.append(f"绑定实例状态: {instance_status}")
        
        # 3. 流量极低
        total_traffic_mb = metrics.get('总流量(MB)', 0)
        if total_traffic_mb < thresholds['traffic_mb_total']:
            idle_conditions.append(f"14天总流量({total_traffic_mb:.2f}MB) < {thresholds['traffic_mb_total']}MB")
        
        # 4. 带宽使用率低
        bandwidth_usage = metrics.get('带宽使用率', 0)
        if bandwidth_usage > 0 and bandwidth_usage < thresholds['bandwidth_usage']:
            idle_conditions.append(f"带宽使用率({bandwidth_usage:.1f}%) < {thresholds['bandwidth_usage']}%")
        
        # 5. 出带宽极低（如果没有出流量）
        out_bandwidth = metrics.get('出带宽', 0)
        if out_bandwidth < 1 and total_traffic_mb < 0.1:  # 几乎没有流量
            idle_conditions.append("几乎无流量")
        
        return len(idle_conditions) > 0, idle_conditions
    
    def get_optimization_suggestion(self, instance, metrics):
        """获取优化建议"""
        suggestions = []
        
        instance_id = instance.get('InstanceId', '')
        bandwidth = instance.get('Bandwidth', 0)
        charge_type = instance.get('InternetChargeType', '')
        total_traffic_mb = metrics.get('总流量(MB)', 0)
        bandwidth_usage = metrics.get('带宽使用率', 0)
        
        # 未绑定实例
        if not instance_id:
            suggestions.append("建议释放未绑定的EIP")
        
        # 绑定实例已停止
        if instance.get('InstanceStatus') in ['Stopped', 'Deleted']:
            suggestions.append("建议释放已停止实例的EIP")
        
        # 流量极低
        if total_traffic_mb < 0.1:
            suggestions.append("建议评估是否有必要保留此EIP")
        
        # 计费方式优化
        if charge_type == 'PayByBandwidth':
            if bandwidth_usage < 20 and total_traffic_mb > 10:
                suggestions.append("建议改为按流量计费")
        elif charge_type == 'PayByTraffic':
            if total_traffic_mb > 1000:  # 流量较大
                suggestions.append("建议评估是否改为按带宽计费")
        
        # 带宽优化
        if bandwidth > 0:
            if bandwidth_usage < 10:
                suggestions.append(f"建议降低带宽（当前{bandwidth}Mbps，使用率仅{bandwidth_usage:.1f}%）")
        
        if not suggestions:
            suggestions.append("资源使用正常，无需优化")
        
        return "; ".join(suggestions)
    
    def save_to_database(self, instances, metrics_data):
        """保存数据到数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        for instance in instances:
            cursor.execute('''
                INSERT OR REPLACE INTO eip_instances 
                (allocation_id, eip_address, instance_id, instance_type, instance_status, region, 
                 bandwidth, charge_type, internet_charge_type, creation_time, monthly_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                instance['AllocationId'],
                instance.get('IpAddress', ''),
                instance.get('InstanceId', ''),
                instance.get('InstanceType', ''),
                instance.get('Status', ''),
                instance.get('Region', ''),
                instance.get('Bandwidth', 0),
                instance.get('ChargeType', ''),
                instance.get('InternetChargeType', ''),
                instance.get('AllocationTime', ''),
                0
            ))
            
            allocation_id = instance['AllocationId']
            if allocation_id in metrics_data:
                metrics = metrics_data[allocation_id]
                for metric_name, metric_value in metrics.items():
                    cursor.execute('''
                        INSERT INTO eip_monitoring_data (allocation_id, metric_name, metric_value, timestamp)
                        VALUES (?, ?, ?, ?)
                    ''', (allocation_id, metric_name, metric_value, int(time.time())))
        
        conn.commit()
        conn.close()
    
    def analyze_eip_instances(self):
        """分析EIP实例"""
        print("🚀 开始EIP资源分析...")
        
        regions = self.get_all_regions()
        
        # 并发获取所有区域的实例
        print("🔍 并发获取所有区域的EIP实例...")
        
        def get_region_instances(region_item):
            """获取单个区域的实例（用于并发）"""
            region = region_item
            try:
                instances = self.get_eip_instances(region)
                return {'region': region, 'instances': instances}
            except Exception as e:
                print(f"  ❌ 区域 {region} 获取实例失败: {e}")
                return {'region': region, 'instances': []}
        
        # 并发获取所有区域的实例
        region_results = process_concurrently(
            regions,
            get_region_instances,
            max_workers=10,
            description="获取EIP实例"
        )
        
        # 整理所有实例
        all_instances_raw = []
        for result in region_results:
            if result and result.get('instances'):
                all_instances_raw.extend(result['instances'])
                print(f"  ✅ {result['region']}: {len(result['instances'])} 个实例")
        
        if not all_instances_raw:
            print("⚠️ 未发现任何EIP实例")
            return
        
        print(f"✅ 总共获取到 {len(all_instances_raw)} 个EIP实例")
        
        # 定义单个实例处理函数（用于并发）
        def process_single_instance(instance_item):
            """处理单个实例（用于并发）"""
            instance = instance_item
            allocation_id = instance['AllocationId']
            ip_address = instance['IpAddress']
            region = instance['Region']
            
            try:
                metrics = self.get_eip_metrics(region, allocation_id, ip_address)
                
                # 计算带宽使用率
                max_bandwidth = instance.get('Bandwidth', 0)
                if max_bandwidth > 0:
                    out_bandwidth = metrics.get('出带宽', 0)
                    metrics['带宽使用率'] = (out_bandwidth / max_bandwidth) * 100
                else:
                    metrics['带宽使用率'] = 0
                
                is_idle, conditions = self.is_eip_idle(instance, metrics)
                optimization = self.get_optimization_suggestion(instance, metrics)
                
                instance['metrics'] = metrics
                instance['is_idle'] = is_idle
                instance['idle_conditions'] = conditions
                instance['optimization'] = optimization
                
                return {
                    'success': True,
                    'instance': instance
                }
            except Exception as e:
                return {
                    'success': False,
                    'instance': instance,
                    'error': str(e)
                }
        
        # 并发处理所有实例
        print(f"🚀 并发获取监控数据并分析（最多10个并发线程）...")
        
        def progress_callback(completed, total):
            progress_pct = completed / total * 100
            sys.stdout.write(f'\r📊 处理进度: {completed}/{total} ({progress_pct:.1f}%)')
            sys.stdout.flush()
        
        processing_results = process_concurrently(
            all_instances_raw,
            process_single_instance,
            max_workers=10,
            description="EIP实例分析",
            progress_callback=progress_callback
        )
        
        print()  # 换行
        
        # 整理结果
        all_instances = []
        metrics_data = {}
        success_count = 0
        fail_count = 0
        
        for result in processing_results:
            if result and result.get('success'):
                instance = result['instance']
                all_instances.append(instance)
                metrics_data[instance['AllocationId']] = instance.get('metrics', {})
                success_count += 1
            else:
                fail_count += 1
        
        print(f"✅ 处理完成: 成功 {success_count} 个, 失败 {fail_count} 个")
        
        # 保存数据
        self.save_to_database(all_instances, metrics_data)
        
        # 生成报告
        self.generate_eip_report(all_instances)
        
        print("✅ EIP分析完成")
    
    def generate_eip_report(self, instances):
        """生成EIP报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        idle_instances = [inst for inst in instances if inst.get('is_idle', False)]
        
        print(f"📊 分析结果: 共 {len(instances)} 个EIP实例，其中 {len(idle_instances)} 个闲置")
        
        if not idle_instances:
            print("✅ 没有发现闲置的EIP实例")
            return
        
        # 生成HTML报告
        html_file = f'eip_idle_report_{timestamp}.html'
        self.generate_html_report(idle_instances, html_file)
        
        # 生成Excel报告
        excel_file = f'eip_idle_report_{timestamp}.xlsx'
        self.generate_excel_report(idle_instances, excel_file)
        
        print(f"📄 报告已生成:")
        print(f"  HTML: {html_file}")
        print(f"  Excel: {excel_file}")
    
    def generate_html_report(self, idle_instances, filename):
        """生成HTML报告"""
        html_content = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EIP闲置实例报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; border-bottom: 3px solid #e74c3c; padding-bottom: 20px; }}
        .summary {{ background: #ecf0f1; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background-color: #3498db; color: white; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #e8f4f8; }}
        .idle-reason {{ color: #e74c3c; font-weight: bold; }}
        .optimization {{ color: #27ae60; font-style: italic; }}
        .footer {{ text-align: center; margin-top: 30px; color: #7f8c8d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 EIP闲置实例分析报告</h1>
        
        <div class="summary">
            <h3>📋 报告摘要</h3>
            <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>闲置实例数量:</strong> {len(idle_instances)} 个</p>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>分配ID</th>
                    <th>IP地址</th>
                    <th>区域</th>
                    <th>绑定实例ID</th>
                    <th>实例类型</th>
                    <th>实例状态</th>
                    <th>带宽(Mbps)</th>
                    <th>计费类型</th>
                    <th>14天总流量(MB)</th>
                    <th>带宽使用率(%)</th>
                    <th>闲置原因</th>
                    <th>优化建议</th>
                </tr>
            </thead>
            <tbody>
'''
        
        for instance in idle_instances:
            metrics = instance.get('metrics', {})
            conditions = instance.get('idle_conditions', [])
            optimization = instance.get('optimization', '')
            
            html_content += f'''
                <tr>
                    <td>{instance['AllocationId']}</td>
                    <td>{instance.get('IpAddress', '')}</td>
                    <td>{instance.get('Region', '')}</td>
                    <td>{instance.get('InstanceId', '未绑定')}</td>
                    <td>{instance.get('InstanceType', '')}</td>
                    <td>{instance.get('Status', '')}</td>
                    <td>{instance.get('Bandwidth', 0)}</td>
                    <td>{instance.get('InternetChargeType', '')}</td>
                    <td>{metrics.get('总流量(MB)', 0):.2f}</td>
                    <td>{metrics.get('带宽使用率', 0):.1f}</td>
                    <td class="idle-reason">{"; ".join(conditions)}</td>
                    <td class="optimization">{optimization}</td>
                </tr>
'''
        
        html_content += '''
            </tbody>
        </table>
        
        <div class="footer">
            <p>本报告由阿里云资源分析工具自动生成 | EIP闲置实例分析</p>
        </div>
    </div>
</body>
</html>
'''
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def generate_excel_report(self, idle_instances, filename):
        """生成Excel报告"""
        try:
            data = []
            for instance in idle_instances:
                metrics = instance.get('metrics', {})
                
                data.append({
                    '分配ID': instance['AllocationId'],
                    'IP地址': instance.get('IpAddress', ''),
                    '区域': instance.get('Region', ''),
                    '绑定实例ID': instance.get('InstanceId', '未绑定'),
                    '实例类型': instance.get('InstanceType', ''),
                    '实例状态': instance.get('Status', ''),
                    '带宽(Mbps)': instance.get('Bandwidth', 0),
                    '计费类型': instance.get('InternetChargeType', ''),
                    '14天总流量(MB)': round(metrics.get('总流量(MB)', 0), 2),
                    '带宽使用率(%)': round(metrics.get('带宽使用率', 0), 1),
                    '闲置原因': "; ".join(instance.get('idle_conditions', [])),
                    '优化建议': instance.get('optimization', '')
                })
            
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine='openpyxl')
            
        except ImportError:
            print("⚠️  pandas未安装，跳过Excel报告生成")


def main(access_key_id=None, access_key_secret=None):
    """主函数"""
    # 如果没有传入参数，尝试从配置文件读取
    if access_key_id is None or access_key_secret is None:
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                access_key_id = access_key_id or config.get('access_key_id')
                access_key_secret = access_key_secret or config.get('access_key_secret')
        except FileNotFoundError:
            raise ValueError("必须提供access_key_id和access_key_secret，或配置文件config.json")
    
    analyzer = EIPAnalyzer(access_key_id, access_key_secret)
    analyzer.analyze_eip_instances()


if __name__ == "__main__":
    main()

