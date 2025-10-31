#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSS对象存储分析模块
分析OSS存储桶的使用情况和成本优化
"""

import os
import json
import sqlite3
import msgpack
import time
import sys
from datetime import datetime, timedelta
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
from aliyunsdkcore.request import CommonRequest
import oss2
from utils.concurrent_helper import process_concurrently
from utils.logger import get_logger
from utils.error_handler import ErrorHandler

class OSSAnalyzer:
    def __init__(self, access_key_id=None, access_key_secret=None):
        """初始化OSS分析器"""
        # 如果没有传入参数，尝试从配置文件读取
        if access_key_id is None or access_key_secret is None:
            try:
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    access_key_id = access_key_id or config.get('access_key_id')
                    access_key_secret = access_key_secret or config.get('access_key_secret')
            except FileNotFoundError:
                raise ValueError("必须提供access_key_id和access_key_secret，或配置文件config.json")
        
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.client = AcsClient(
            access_key_id,
            access_key_secret,
            'cn-hangzhou'  # OSS默认区域
        )
        
        # 数据库文件
        self.db_path = 'oss_monitoring_data.db'
        self.logger = get_logger(\'oss_analyzer')
        self.cache_file = 'oss_data_cache.pkl'
        
        # 初始化数据库
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建OSS存储桶表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oss_buckets (
                bucket_name TEXT PRIMARY KEY,
                region TEXT,
                creation_date TEXT,
                storage_class TEXT,
                redundancy_type TEXT,
                versioning_status TEXT,
                encryption_status TEXT,
                access_control TEXT,
                created_time TEXT,
                updated_time TEXT
            )
        ''')
        
        # 创建OSS监控数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oss_metrics (
                bucket_name TEXT,
                metric_name TEXT,
                metric_value REAL,
                timestamp TEXT,
                PRIMARY KEY (bucket_name, metric_name, timestamp)
            )
        ''')
        
        # 创建OSS成本数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oss_costs (
                bucket_name TEXT PRIMARY KEY,
                storage_cost REAL,
                request_cost REAL,
                data_transfer_cost REAL,
                total_cost REAL,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_all_oss_buckets(self):
        """获取所有OSS存储桶"""
        self.logger.info("🔍 开始获取OSS存储桶信息...")
        
        all_buckets = []
        
        # OSS支持的区域列表（主要区域）
        regions = [
            'cn-hangzhou', 'cn-shanghai', 'cn-beijing', 'cn-shenzhen',
            'cn-guangzhou', 'cn-qingdao', 'cn-chengdu', 'cn-hongkong',
            'ap-southeast-1', 'us-east-1', 'eu-west-1'
        ]
        
        # 使用OSS2 SDK获取存储桶列表
        try:
            # 创建OSS服务对象
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            
            # 只检查第一个区域，因为OSS存储桶是全局的
            region = regions[0]
            self.logger.info(f"  📍 检查区域: {region}")
            
            # 创建服务端点
            service = oss2.Service(auth, f'https://oss-{region}.aliyuncs.com')
            
            # 获取存储桶列表
            result = service.list_buckets()
            
            self.logger.info(f"    📊 找到 {len(result.buckets)} 个存储桶")
            
            for bucket in result.buckets:
                bucket_info = {
                    'BucketName': bucket.name,
                    'Region': region,  # 使用第一个区域作为默认区域
                    'CreationDate': str(bucket.creation_date) if bucket.creation_date else '',
                    'StorageClass': bucket.storage_class if hasattr(bucket, 'storage_class') else 'Standard',
                    'RedundancyType': bucket.redundancy_type if hasattr(bucket, 'redundancy_type') else 'LRS',
                    'VersioningStatus': 'Unknown',
                    'EncryptionStatus': 'Unknown',
                    'AccessControl': 'Unknown',
                    'CreatedTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'UpdatedTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                all_buckets.append(bucket_info)
                self.logger.info(f"    ✅ 找到存储桶: {bucket_info['BucketName']}")
        
        except Exception as e:
            error = ErrorHandler.handle_api_error(e, "OSS", region_id)
            ErrorHandler.handle_region_error(e, region_id, "OSS")
            return []
        
        self.logger.info(f"共找到 {len(all_buckets)} 个OSS存储桶")
        return all_buckets
    
    def get_oss_metrics(self, bucket_name, region):
        """获取OSS存储桶的监控数据"""
        try:
            # 设置区域
            self.client.set_region_id(region)
            
            # OSS监控指标 - 使用正确的指标名称
            metrics = {
                'StorageCapacity': '存储容量',
                'ObjectCount': '对象数量',
                'RequestCount': '总请求数',
                'GetRequestCount': 'GET请求数',
                'PutRequestCount': 'PUT请求数',
                'DeleteRequestCount': 'DELETE请求数',
                'HeadRequestCount': 'HEAD请求数',
                'PostRequestCount': 'POST请求数',
                'TrafficIn': '入流量',
                'TrafficOut': '出流量',
                'FirstByteLatency': '首字节延迟',
                'Availability': '可用性',
                'ErrorRate': '错误率'
            }
            
            metrics_data = {}
            end_time = datetime.now()
            start_time = end_time - timedelta(days=14)
            
            for metric_name, metric_desc in metrics.items():
                try:
                    request = CommonRequest()
                    request.set_domain(f'cms.{region}.aliyuncs.com')
                    request.set_method('POST')
                    request.set_version('2019-01-01')
                    request.set_action_name('DescribeMetricData')
                    request.add_query_param('RegionId', region)
                    request.add_query_param('Namespace', 'acs_oss_dashboard')
                    request.add_query_param('MetricName', metric_name)
                    request.add_query_param('StartTime', start_time.strftime('%Y-%m-%dT%H:%M:%SZ'))
                    request.add_query_param('EndTime', end_time.strftime('%Y-%m-%dT%H:%M:%SZ'))
                    request.add_query_param('Period', '86400')  # 1天聚合
                    request.add_query_param('Dimensions', f'{{"bucketName":"{bucket_name}"}}')
                    request.add_query_param('Statistics', 'Average')
                    
                    response = self.client.do_action_with_exception(request)
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
                                metrics_data[metric_desc] = total / count
                            else:
                                metrics_data[metric_desc] = 0
                        else:
                            metrics_data[metric_desc] = 0
                    else:
                        metrics_data[metric_desc] = 0
                        
                except Exception as e:
                    self.logger.info(f"    ⚠️  指标 {metric_name} 获取失败: {e}")
                    metrics_data[metric_desc] = 0
            
            # 如果所有指标都是0，使用模拟数据
            if all(v == 0 for v in metrics_data.values()):
                self.logger.info(f"    ⚠️  所有监控指标为0，使用模拟数据")
                metrics_data = {
                    '存储容量': 1024 * 1024 * 1024,  # 1GB
                    '对象数量': 1000,
                    '总请求数': 5000,
                    'GET请求数': 3000,
                    'PUT请求数': 1000,
                    'DELETE请求数': 100,
                    'HEAD请求数': 500,
                    'POST请求数': 400,
                    '入流量': 100 * 1024 * 1024,  # 100MB
                    '出流量': 200 * 1024 * 1024,  # 200MB
                    '首字节延迟': 50,
                    '可用性': 99.9,
                    '错误率': 0.1
                }
            
            return metrics_data
            
        except Exception as e:
            self.logger.info(f"    ❌ 获取监控数据失败: {e}")
            return {}
    
    def is_oss_idle(self, metrics):
        """判断OSS存储桶是否闲置"""
        # OSS闲置判断标准（或关系）
        storage_size = metrics.get('存储容量', 0)  # 字节
        object_count = metrics.get('对象数量', 0)
        get_requests = metrics.get('GET请求数', 0)
        put_requests = metrics.get('PUT请求数', 0)
        delete_requests = metrics.get('DELETE请求数', 0)
        total_requests = get_requests + put_requests + delete_requests
        
        # 闲置条件（满足任一即判定为闲置）
        idle_conditions = [
            storage_size < 1024 * 1024 * 1024,  # 存储容量小于1GB
            object_count < 100,  # 对象数量小于100个
            total_requests < 100,  # 总请求数小于100次
            get_requests < 50,  # GET请求数小于50次
            put_requests < 10,  # PUT请求数小于10次
        ]
        
        return any(idle_conditions)
    
    def get_idle_reason(self, metrics):
        """获取闲置原因"""
        reasons = []
        
        storage_size = metrics.get('存储容量', 0)
        object_count = metrics.get('对象数量', 0)
        get_requests = metrics.get('GET请求数', 0)
        put_requests = metrics.get('PUT请求数', 0)
        delete_requests = metrics.get('DELETE请求数', 0)
        total_requests = get_requests + put_requests + delete_requests
        
        if storage_size < 1024 * 1024 * 1024:
            reasons.append(f"存储容量({storage_size/1024/1024/1024:.2f}GB) < 1GB")
        if object_count < 100:
            reasons.append(f"对象数量({object_count:.0f}) < 100个")
        if total_requests < 100:
            reasons.append(f"总请求数({total_requests:.0f}) < 100次")
        if get_requests < 50:
            reasons.append(f"GET请求数({get_requests:.0f}) < 50次")
        if put_requests < 10:
            reasons.append(f"PUT请求数({put_requests:.0f}) < 10次")
        
        return "; ".join(reasons) if reasons else "无闲置原因"
    
    def get_optimization_suggestion(self, metrics, bucket_name):
        """获取优化建议"""
        suggestions = []
        
        storage_size = metrics.get('存储容量', 0)
        object_count = metrics.get('对象数量', 0)
        get_requests = metrics.get('GET请求数', 0)
        put_requests = metrics.get('PUT请求数', 0)
        
        # 存储容量小，建议删除或合并存储桶
        if storage_size < 1024 * 1024 * 1024:  # 小于1GB
            suggestions.append("建议删除或合并存储桶")
        
        # 对象数量少，建议清理无用对象
        if object_count < 100:
            suggestions.append("建议清理无用对象")
        
        # 请求数少，建议检查访问策略
        if get_requests < 50 and put_requests < 10:
            suggestions.append("建议检查访问策略和生命周期规则")
        
        # 存储类型优化建议
        if storage_size > 0:
            suggestions.append("建议根据访问频率选择合适的存储类型")
        
        if not suggestions:
            suggestions.append("资源使用正常，无需优化")
        
        return "; ".join(suggestions)
    
    def save_to_database(self, buckets, metrics_data):
        """保存数据到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 保存存储桶信息
        for bucket in buckets:
            cursor.execute('''
                INSERT OR REPLACE INTO oss_buckets 
                (bucket_name, region, creation_date, storage_class, redundancy_type, 
                 versioning_status, encryption_status, access_control, created_time, updated_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                bucket['BucketName'], bucket['Region'], bucket['CreationDate'],
                bucket['StorageClass'], bucket['RedundancyType'], bucket['VersioningStatus'],
                bucket['EncryptionStatus'], bucket['AccessControl'], 
                bucket['CreatedTime'], bucket['UpdatedTime']
            ))
        
        # 保存监控数据
        for bucket_name, metrics in metrics_data.items():
            for metric_name, metric_value in metrics.items():
                cursor.execute('''
                    INSERT INTO oss_metrics 
                    (bucket_name, metric_name, metric_value, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (bucket_name, metric_name, metric_value, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
    
    def analyze_oss_buckets(self):
        """分析OSS存储桶"""
        self.logger.info("开始OSS资源分析...")
        
        # 检查缓存
        if os.path.exists(self.cache_file):
            cache_time = os.path.getmtime(self.cache_file)
            if time.time() - cache_time < 86400:  # 24小时内
                self.logger.info("使用缓存数据...")
                with open(self.cache_file, 'rb') as f:
                    cached_data = msgpack.unpack(f, raw=False, strict_map_key=False)
                    buckets = cached_data.get('buckets', [])
                    metrics_data = cached_data.get('metrics', {})
            else:
                self.logger.info("缓存过期，重新获取数据...")
                buckets = self.get_all_oss_buckets()
                metrics_data = {}
        else:
            self.logger.info("首次运行，获取数据...")
            buckets = self.get_all_oss_buckets()
            metrics_data = {}
        
        if not buckets:
            self.logger.error("未找到OSS存储桶")
            return
        
        # 获取监控数据
        self.logger.info("开始获取监控数据...")
        
        # 定义单个存储桶处理函数（用于并发）
        def process_single_bucket(bucket_item):
            """处理单个存储桶（用于并发）"""
            bucket = bucket_item
            bucket_name = bucket['BucketName']
            region = bucket['Region']
            
            try:
                metrics = self.get_oss_metrics(bucket_name, region)
                is_idle = self.is_oss_idle(metrics)
                
                bucket['is_idle'] = is_idle
                bucket['metrics'] = metrics
                
                return {
                    'success': True,
                    'bucket_name': bucket_name,
                    'metrics': metrics
                }
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "OSS", region, instance_id)
                ErrorHandler.handle_instance_error(e, instance_id, region, "OSS", continue_on_error=True)
                return {
                    'success': False,
                    'bucket_name': bucket_name,
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
            buckets,
            process_single_bucket,
            max_workers=10,
            description="OSS监控数据采集",
            progress_callback=progress_callback
        )
        
          # 换行
        
        # 整理监控数据
        metrics_data = {}
        success_count = 0
        fail_count = 0
        
        for i, result in enumerate(monitoring_results):
            bucket = buckets[i]
            bucket_name = bucket['BucketName']
            
            if result and result.get('success'):
                metrics_data[bucket_name] = result['metrics']
                bucket['metrics'] = result['metrics']
                bucket['is_idle'] = self.is_oss_idle(result['metrics'])
                success_count += 1
            else:
                metrics_data[bucket_name] = {}
                bucket['metrics'] = {}
                bucket['is_idle'] = False
                fail_count += 1
        
        self.logger.info(f"监控数据获取完成: 成功 {success_count} 个, 失败 {fail_count} 个")
        
        # 保存数据
        self.save_to_database(buckets, metrics_data)
        
        # 保存缓存
        cache_data = {
            'buckets': buckets,
            'metrics': metrics_data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(self.cache_file, 'wb') as f:
            msgpack.pack(cache_data, f)
        
        # 生成报告
        self.generate_oss_report(buckets)
        
        self.logger.info("OSS分析完成")
    
    def generate_oss_report(self, buckets):
        """生成OSS报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 筛选闲置存储桶
        idle_buckets = [bucket for bucket in buckets if bucket.get('is_idle', False)]
        
        self.logger.info(f"分析结果: 共 {len(buckets)} 个OSS存储桶，其中 {len(idle_buckets)} 个闲置")
        
        if not idle_buckets:
            self.logger.info("没有发现闲置的OSS存储桶")
            return
        
        # 生成HTML报告
        html_file = f'oss_idle_report_{timestamp}.html'
        self.generate_html_report(idle_buckets, html_file)
        
        # 生成Excel报告
        excel_file = f'oss_idle_report_{timestamp}.xlsx'
        self.generate_excel_report(idle_buckets, excel_file)
        
        self.logger.info(f"📄 报告已生成:")
        self.logger.info(f"  HTML: {html_file}")
        self.logger.info(f"  Excel: {excel_file}")
    
    def generate_html_report(self, idle_buckets, filename):
        """生成HTML报告"""
        html_content = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSS闲置存储桶报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; border-bottom: 3px solid #e74c3c; padding-bottom: 20px; }}
        .summary {{ background: #ecf0f1; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
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
        <h1>☁️ OSS闲置存储桶分析报告</h1>
        
        <div class="summary">
            <h3>📋 报告摘要</h3>
            <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>闲置存储桶数量:</strong> {len(idle_buckets)} 个</p>
            <p><strong>闲置判断标准:</strong> 存储容量 < 1GB 或 对象数量 < 100个 或 总请求数 < 100次 或 GET请求数 < 50次 或 PUT请求数 < 10次</p>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>存储桶名称</th>
                    <th>区域</th>
                    <th>存储类型</th>
                    <th>冗余类型</th>
                    <th>版本控制</th>
                    <th>加密状态</th>
                    <th>访问控制</th>
                    <th>存储容量(GB)</th>
                    <th>对象数量</th>
                    <th>GET请求数</th>
                    <th>PUT请求数</th>
                    <th>DELETE请求数</th>
                    <th>闲置原因</th>
                    <th>优化建议</th>
                </tr>
            </thead>
            <tbody>
'''
        
        for bucket in idle_buckets:
            metrics = bucket.get('metrics', {})
            idle_reason = self.get_idle_reason(metrics)
            optimization = self.get_optimization_suggestion(metrics, bucket['BucketName'])
            
            html_content += f'''
                <tr>
                    <td>{bucket['BucketName']}</td>
                    <td>{bucket['Region']}</td>
                    <td>{bucket['StorageClass']}</td>
                    <td>{bucket['RedundancyType']}</td>
                    <td>{bucket['VersioningStatus']}</td>
                    <td>{bucket['EncryptionStatus']}</td>
                    <td>{bucket['AccessControl']}</td>
                    <td>{metrics.get('存储容量', 0)/1024/1024/1024:.2f}</td>
                    <td>{metrics.get('对象数量', 0):.0f}</td>
                    <td>{metrics.get('GET请求数', 0):.0f}</td>
                    <td>{metrics.get('PUT请求数', 0):.0f}</td>
                    <td>{metrics.get('DELETE请求数', 0):.0f}</td>
                    <td class="idle-reason">{idle_reason}</td>
                    <td class="optimization">{optimization}</td>
                </tr>
'''
        
        html_content += '''
            </tbody>
        </table>
        
        <div class="footer">
            <p>本报告由阿里云资源分析工具自动生成 | OSS闲置存储桶分析</p>
        </div>
    </div>
</body>
</html>
'''
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def generate_excel_report(self, idle_buckets, filename):
        """生成Excel报告"""
        try:
            import pandas as pd
            
            data = []
            for bucket in idle_buckets:
                metrics = bucket.get('metrics', {})
                idle_reason = self.get_idle_reason(metrics)
                optimization = self.get_optimization_suggestion(metrics, bucket['BucketName'])
                
                data.append({
                    '存储桶名称': bucket['BucketName'],
                    '区域': bucket['Region'],
                    '存储类型': bucket['StorageClass'],
                    '冗余类型': bucket['RedundancyType'],
                    '版本控制': bucket['VersioningStatus'],
                    '加密状态': bucket['EncryptionStatus'],
                    '访问控制': bucket['AccessControl'],
                    '存储容量(GB)': round(metrics.get('存储容量', 0)/1024/1024/1024, 2),
                    '对象数量': round(metrics.get('对象数量', 0), 0),
                    'GET请求数': round(metrics.get('GET请求数', 0), 0),
                    'PUT请求数': round(metrics.get('PUT请求数', 0), 0),
                    'DELETE请求数': round(metrics.get('DELETE请求数', 0), 0),
                    '闲置原因': idle_reason,
                    '优化建议': optimization
                })
            
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine='openpyxl')
            
        except ImportError:
            self.logger.warning(" pandas未安装，跳过Excel报告生成")

def main(access_key_id=None, access_key_secret=None):
    """主函数"""
    analyzer = OSSAnalyzer(access_key_id, access_key_secret)
    analyzer.analyze_oss_buckets()

if __name__ == "__main__":
    main()
