#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import msgpack
import datetime
import sqlite3
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
import pandas as pd

# 导入新的工具模块
try:
    from utils.logger import setup_logger
    from utils.concurrent_helper import process_concurrently
    from utils.retry_helper import retry_api_call
    USE_NEW_UTILS = True
except ImportError:
    # 如果工具模块不存在，使用兼容模式
    USE_NEW_UTILS = False
    print("⚠️  工具模块未找到，使用兼容模式（无并发和重试）")

# 配置信息 - 将从main函数参数传入
access_key_id = None
access_key_secret = None

# 日志记录器（延迟初始化）
logger = None

def set_credentials(key_id, key_secret):
    """设置访问凭证"""
    global access_key_id, access_key_secret
    access_key_id = key_id
    access_key_secret = key_secret

# 数据库/缓存配置（默认全局，运行时按租户重写）
DB_FILE = "ecs_monitoring_data_fixed.db"
CACHE_FILE = "ecs_data_cache_fixed.pkl"
CACHE_EXPIRE_HOURS = 24

def set_storage_paths(tenant_name: str = None, base_dir: str = "."):
    """按租户设置数据库与缓存文件路径"""
    global DB_FILE, CACHE_FILE
    if tenant_name:
        tenant_data_dir = os.path.join(base_dir, "data", tenant_name, "ecs")
    else:
        tenant_data_dir = os.path.join(base_dir, "data", "default", "ecs")
    os.makedirs(tenant_data_dir, exist_ok=True)
    DB_FILE = os.path.join(tenant_data_dir, "ecs_monitoring_data_fixed.db")
    CACHE_FILE = os.path.join(tenant_data_dir, "ecs_data_cache_fixed.pkl")

def init_database():
    """初始化本地数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建实例信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS instances (
            instance_id TEXT PRIMARY KEY,
            instance_name TEXT,
            region TEXT,
            status TEXT,
            instance_type TEXT,
            creation_time TEXT,
            cpu_cores INTEGER,
            memory_gb INTEGER,
            eip_bandwidth INTEGER,
            eip_address TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建监控数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitoring_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id TEXT,
            metric_name TEXT,
            metric_value REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (instance_id) REFERENCES instances (instance_id)
        )
    ''')
    
    # 创建成本数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cost_data (
            instance_id TEXT PRIMARY KEY,
            monthly_cost REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (instance_id) REFERENCES instances (instance_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

def get_all_regions(client):
    """获取所有可用区域"""
    request = CommonRequest()
    request.set_domain('ecs.aliyuncs.com')
    request.set_method('POST')
    request.set_version('2014-05-26')
    request.set_action_name('DescribeRegions')
    
    response = client.do_action_with_exception(request)
    data = json.loads(response)
    
    regions = []
    for region in data['Regions']['Region']:
        regions.append(region['RegionId'])
    
    return regions

def get_all_instances(client, region_id):
    """获取指定区域的所有ECS实例"""
    request = CommonRequest()
    request.set_domain(f'ecs.{region_id}.aliyuncs.com')
    request.set_method('POST')
    request.set_version('2014-05-26')
    request.set_action_name('DescribeInstances')
    request.add_query_param('PageSize', 100)
    
    all_instances = []
    page_number = 1
    
    while True:
        request.add_query_param('PageNumber', page_number)
        response = client.do_action_with_exception(request)
        data = json.loads(response)
        
        if 'Instances' not in data or 'Instance' not in data['Instances']:
            break
            
        instances = data['Instances']['Instance']
        if not isinstance(instances, list):
            instances = [instances]
        
        for instance in instances:
            all_instances.append({
                'InstanceId': instance['InstanceId'],
                'InstanceName': instance.get('InstanceName', '未命名'),
                'Status': instance.get('Status', '未知'),
                'InstanceType': instance.get('InstanceType', '未知'),
                'CreationTime': instance.get('CreationTime', '未知'),
                'Cpu': instance.get('Cpu', 0),
                'Memory': instance.get('Memory', 0)
            })
        
        if len(instances) < 100:
            break
        page_number += 1
    
    return all_instances

def _get_instance_eip_info_internal(client, region_id, instance_id):
    """获取实例的EIP信息（内部实现）"""
    request = CommonRequest()
    request.set_domain(f'ecs.{region_id}.aliyuncs.com')
    request.set_method('POST')
    request.set_version('2014-05-26')
    request.set_action_name('DescribeEipAddresses')
    request.add_query_param('AssociatedInstanceId', instance_id)
    
    response = client.do_action_with_exception(request)
    data = json.loads(response)
    
    if 'EipAddresses' in data and 'EipAddress' in data['EipAddresses']:
        eip_list = data['EipAddresses']['EipAddress']
        if not isinstance(eip_list, list):
            eip_list = [eip_list]
        
        if eip_list:
            eip = eip_list[0]
            return {
                'Bandwidth': eip.get('Bandwidth', 0),
                'EipAddress': eip.get('IpAddress', '')
            }
    
    return None


def get_instance_eip_info(client, region_id, instance_id):
    """获取实例的EIP信息（带重试，仅对网络错误重试）"""
    def _call():
        return _get_instance_eip_info_internal(client, region_id, instance_id)
    
    if USE_NEW_UTILS:
        # 只对网络错误重试，业务错误（400/403等）直接返回None
        wrapped_call = retry_api_call(max_attempts=3, retry_exceptions=(ConnectionError, TimeoutError))(_call)
        try:
            return wrapped_call()
        except Exception as e:
            # 400/403等业务错误不重试，直接返回None
            error_str = str(e)
            if any(code in error_str for code in ['400', '403', 'Invalid', 'Forbidden']):
                if logger:
                    logger.debug(f"获取EIP信息业务错误（预期） {instance_id}: {error_str[:100]}")
            else:
                if logger:
                    logger.warning(f"获取EIP信息失败 {instance_id}: {e}")
            return None
    else:
        try:
            return _get_instance_eip_info_internal(client, region_id, instance_id)
        except Exception as e:
            return None

def get_comprehensive_metrics_from_db(instance_id):
    """从数据库获取实例的全面监控数据"""
    conn = sqlite3.connect('ecs_monitoring_data_fixed.db')
    
    # 定义需要获取的指标
    metrics_to_get = [
        'CPU利用率', '磁盘读BPS', '磁盘写BPS', '磁盘读IOPS', '磁盘写IOPS',
        '网络连接数', '入网流量', '出网流量', '内存利用率', '1分钟负载',
        '5分钟负载', '15分钟负载', 'Load Average', 'TCP连接数',
        '内网入带宽', '内网出带宽', '状态检查', '磁盘IO队列长度'
    ]
    
    result = {}
    
    for metric_name in metrics_to_get:
        try:
            query = '''
            SELECT AVG(metric_value) as avg_value
            FROM monitoring_data 
            WHERE instance_id = ? AND metric_name = ?
            '''
            cursor = conn.cursor()
            cursor.execute(query, (instance_id, metric_name))
            row = cursor.fetchone()
            
            if row and row[0] is not None:
                result[metric_name] = float(row[0])
            else:
                result[metric_name] = 0
        except Exception as e:
            result[metric_name] = 0
    
    conn.close()
    return result

def get_comprehensive_metrics(client, region_id, instance_id, show_progress=False, metric_index=0, total_metrics=18, days: int = 14):
    """获取实例的全面监控数据"""
    end_time = int(round(time.time() * 1000))
    # 支持可配置窗口（默认14天），按小时聚合后取平均
    start_time = end_time - days * 24 * 60 * 60 * 1000
    
    # 定义所有可能的监控指标 - 修复版本
    # 基础指标（acs_ecs_dashboard命名空间）
    base_metrics = {
        'CPUUtilization': ('CPU利用率', 'acs_ecs_dashboard'),
        'DiskReadBPS': ('磁盘读BPS', 'acs_ecs_dashboard'),
        'DiskWriteBPS': ('磁盘写BPS', 'acs_ecs_dashboard'),
        'DiskReadIOPS': ('磁盘读IOPS', 'acs_ecs_dashboard'),
        'DiskWriteIOPS': ('磁盘写IOPS', 'acs_ecs_dashboard'),
        'ConnectionUtilization': ('网络连接数', 'acs_ecs_dashboard'),
        # 改为默认采集内网带宽作为“入网流量/出网流量”
        'IntranetInRate': ('入网流量', 'acs_ecs_dashboard'),
        'IntranetOutRate': ('出网流量', 'acs_ecs_dashboard'),
        # 公网带宽保留，若需要可用于对照
        'InternetInRate': ('公网入带宽', 'acs_ecs_dashboard'),
        'InternetOutRate': ('公网出带宽', 'acs_ecs_dashboard'),
        'StatusCheck': ('状态检查', 'acs_ecs_dashboard'),
        'DiskIOQueueSize': ('磁盘IO队列长度', 'acs_ecs_dashboard')
    }
    
    # 云监控插件指标（这些指标在acs_ecs_dashboard命名空间中，使用Groupvm.前缀）
    agent_metrics_main = {
        'Groupvm.MemoryUtilization': ('内存利用率', 'acs_ecs_dashboard'),
        'load_1m': ('1分钟负载', 'acs_ecs_dashboard'),
        'load_5m': ('5分钟负载', 'acs_ecs_dashboard'),
        'load_15m': ('15分钟负载', 'acs_ecs_dashboard'),
        'Groupvm.LoadAverage': ('Load Average', 'acs_ecs_dashboard'),
        'Groupvm.TcpConnection': ('TCP连接数', 'acs_ecs_dashboard')
    }
    
    # 合并所有指标（基础指标 + 云监控插件指标）
    all_metrics = {**base_metrics, **agent_metrics_main}
    all_metrics_list = list(all_metrics.items())
    
    result = {}
    agent_metrics_found = []  # 记录哪些云监控插件指标成功获取到数据
    
    for idx, (metric_name, (display_name, namespace)) in enumerate(all_metrics_list):
        if show_progress and idx % 6 == 0:  # 每6个指标显示一次进度
            progress = (idx / len(all_metrics_list)) * 100
            sys.stdout.write(f'\r    📊 获取监控指标: {idx}/{len(all_metrics_list)} ({progress:.0f}%)')
            sys.stdout.flush()
        
        try:
            request = CommonRequest()
            request.set_domain(f'cms.{region_id}.aliyuncs.com')
            request.set_method('POST')
            request.set_version('2019-01-01')
            request.set_action_name('DescribeMetricData')
            request.add_query_param('RegionId', region_id)
            request.add_query_param('Namespace', namespace)
            request.add_query_param('MetricName', metric_name)
            request.add_query_param('StartTime', start_time)
            request.add_query_param('EndTime', end_time)
            # 使用每小时粒度，避免按天聚合导致无数据
            request.add_query_param('Period', '3600')
            request.add_query_param('Dimensions', f'[{{"instanceId":"{instance_id}"}}]')
            
            response = client.do_action_with_exception(request)
            data = json.loads(response)
            
            has_data_points = False
            has_data = False
            if 'Datapoints' in data and data['Datapoints']:
                has_data_points = True  # 有Datapoints字段，说明指标存在
                if isinstance(data['Datapoints'], str):
                    dps = json.loads(data['Datapoints'])
                else:
                    dps = data['Datapoints']
                
                if dps and len(dps) > 0:
                    # 计算所有数据点的平均值 - 确保14天平均值
                    total = 0
                    count = 0
                    for dp in dps:
                        if 'Average' in dp and dp['Average'] is not None:
                            total += float(dp['Average'])
                            count += 1
                    
                    if count > 0:
                        result[display_name] = total / count
                        has_data = True
                        # 记录云监控插件指标是否成功获取到数据（即使值为0也算成功）
                        # 检查是否是云监控插件指标（通过指标名称判断）
                        if metric_name.startswith('Groupvm.') or metric_name.startswith('load_'):
                            agent_metrics_found.append(display_name)
                    else:
                        result[display_name] = 0
                        # 即使count为0，如果has_data_points为True，也说明指标存在
                        if (metric_name.startswith('Groupvm.') or metric_name.startswith('load_')) and has_data_points:
                            agent_metrics_found.append(display_name)
                else:
                    result[display_name] = 0
                    # 空数组但有Datapoints字段，也说明指标存在
                    if (metric_name.startswith('Groupvm.') or metric_name.startswith('load_')) and has_data_points:
                        agent_metrics_found.append(display_name)
            else:
                result[display_name] = 0
        except Exception as e:
            # 如果API调用失败，认为该指标不存在
            result[display_name] = 0
            # 如果是云监控插件指标的异常，记录一下（但不影响判断）
            if namespace == 'acs_ecs_dashboard_agent' and show_progress:
                # 静默处理，不显示错误，因为可能是指标不存在
                pass
        
        time.sleep(0.1)  # 避免API限流
    
    if show_progress:
        sys.stdout.write('\r    ✅ 监控指标获取完成' + ' ' * 30 + '\n')
        sys.stdout.flush()
    
    # 标记是否有云监控插件（只要有一个云监控插件指标成功获取到数据就认为有插件）
    # 即使值可能为0，但能获取到数据就说明有插件
    result['_has_agent'] = len(agent_metrics_found) > 0
    
    return result

def _get_instance_monthly_cost_internal(client, region_id, instance_id):
    """获取实例的月度续费成本（内部实现）"""
    request = CommonRequest()
    request.set_domain(f'ecs.{region_id}.aliyuncs.com')
    request.set_method('POST')
    request.set_version('2014-05-26')
    request.set_action_name('DescribeRenewalPrice')
    request.add_query_param('ResourceId', instance_id)
    request.add_query_param('Period', 1)
    request.add_query_param('PriceUnit', 'Month')
    
    response = client.do_action_with_exception(request)
    data = json.loads(response)
    
    if 'PriceInfo' in data and 'Price' in data['PriceInfo']:
        price_info = data['PriceInfo']['Price']
        if 'TradePrice' in price_info:
            return float(price_info['TradePrice'])
    
    return 0


def get_instance_monthly_cost(client, region_id, instance_id):
    """获取实例的月度续费成本（带重试，仅对网络错误重试）"""
    def _call():
        return _get_instance_monthly_cost_internal(client, region_id, instance_id)
    
    if USE_NEW_UTILS:
        # 只对网络错误重试，业务错误（400/403等）直接返回0
        wrapped_call = retry_api_call(max_attempts=3, retry_exceptions=(ConnectionError, TimeoutError))(_call)
        try:
            return wrapped_call()
        except Exception as e:
            # 400/403等业务错误不重试，直接返回0（按量付费实例会返回错误，这是正常的）
            error_str = str(e)
            if any(code in error_str for code in ['400', '403', 'Invalid', 'Forbidden']):
                if logger:
                    logger.debug(f"获取成本信息业务错误（按量付费实例预期） {instance_id}: {error_str[:100]}")
            else:
                if logger:
                    logger.warning(f"获取成本信息失败 {instance_id}: {e}")
            return 0
    else:
        try:
            return _get_instance_monthly_cost_internal(client, region_id, instance_id)
        except Exception as e:
            return 0

def save_to_database(instance_data, metrics_data, cost_data):
    """保存数据到本地数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # 保存实例信息
        cursor.execute('''
            INSERT OR REPLACE INTO instances 
            (instance_id, instance_name, region, status, instance_type, 
             creation_time, cpu_cores, memory_gb, eip_bandwidth, eip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            instance_data['InstanceId'],
            instance_data['InstanceName'],
            instance_data['Region'],
            instance_data['Status'],
            instance_data['InstanceType'],
            instance_data['CreationTime'],
            instance_data['Cpu'],
            instance_data['Memory'],
            instance_data.get('EipBandwidth', 0),
            instance_data.get('EipAddress', '')
        ))
        
        # 保存监控数据
        for metric_name, metric_value in metrics_data.items():
            cursor.execute('''
                INSERT INTO monitoring_data (instance_id, metric_name, metric_value)
                VALUES (?, ?, ?)
            ''', (instance_data['InstanceId'], metric_name, metric_value))
        
        # 保存成本数据
        cursor.execute('''
            INSERT OR REPLACE INTO cost_data (instance_id, monthly_cost)
            VALUES (?, ?)
        ''', (instance_data['InstanceId'], cost_data))
        
        conn.commit()
    except Exception as e:
        print(f"❌ 数据库保存失败: {e}")
    finally:
        conn.close()

def is_cache_valid():
    """检查缓存是否有效"""
    if not os.path.exists(CACHE_FILE):
        return False
    
    cache_time = os.path.getmtime(CACHE_FILE)
    current_time = time.time()
    return (current_time - cache_time) < (CACHE_EXPIRE_HOURS * 3600)

def save_cache_data(data):
    """保存数据到缓存（使用msgpack，安全高效）"""
    cache_data = {
        'timestamp': time.time(),
        'data': data
    }
    with open(CACHE_FILE, 'wb') as f:
        msgpack.pack(cache_data, f)
    print(f"✅ 数据已缓存到 {CACHE_FILE}")

def load_cache_data():
    """从缓存加载数据（使用msgpack，安全高效）"""
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        with open(CACHE_FILE, 'rb') as f:
            cache_data = msgpack.unpack(f, raw=False, strict_map_key=False)
        print(f"✅ 从缓存加载数据 (缓存时间: {datetime.datetime.fromtimestamp(cache_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')})")
        return cache_data['data']
    except Exception as e:
        print(f"❌ 缓存加载失败: {e}")
        return None

def is_instance_idle_with_agent(instance, metrics, eip_info=None):
    """判断实例是否为闲置状态（有云监控插件）"""
    cpu_cores = instance.get('Cpu', 0)
    
    # 获取各项指标
    cpu_util = metrics.get('CPU利用率', 0)
    memory_util = metrics.get('内存利用率', 0)
    load_5m = metrics.get('5分钟负载', 0)
    disk_read_iops = metrics.get('磁盘读IOPS', 0)
    disk_write_iops = metrics.get('磁盘写IOPS', 0)
    
    # 计算总IOPS
    total_iops = disk_read_iops + disk_write_iops
    
    # 判断条件
    conditions = []
    
    # 1. Load Average平均低于vCPU数量的5%
    if cpu_cores > 0 and load_5m > 0:
        load_threshold = cpu_cores * 0.05
        if load_5m < load_threshold:
            conditions.append(f"Load Average({load_5m:.2f}) < vCPU*5%({load_threshold:.2f})")
    
    # 2. 内存平均利用率小于20%
    if memory_util > 0 and memory_util < 20:
        conditions.append(f"内存利用率({memory_util:.1f}%) < 20%")
    
    # 3. 磁盘平均IOPS小于100
    if total_iops < 100:
        conditions.append(f"磁盘IOPS({total_iops:.0f}) < 100")
    
    # 4. EIP带宽使用率检查（如果有EIP）
    if eip_info and eip_info.get('Bandwidth', 0) > 0:
        bandwidth_mbps = eip_info['Bandwidth']
        internet_in_rate = metrics.get('入网流量', 0)
        internet_out_rate = metrics.get('出网流量', 0)
        total_bandwidth_usage = internet_in_rate + internet_out_rate
        
        # 转换为Mbps进行比较
        bandwidth_usage_mbps = total_bandwidth_usage / 1024 / 1024 * 8  # bps转Mbps
        bandwidth_threshold = bandwidth_mbps * 0.1  # 10%阈值
        
        if bandwidth_usage_mbps < bandwidth_threshold:
            conditions.append(f"EIP带宽使用率({bandwidth_usage_mbps:.2f}Mbps) < 峰值*10%({bandwidth_threshold:.2f}Mbps)")
    
    return len(conditions) > 0, conditions

def is_instance_idle_without_agent(instance, metrics, eip_info=None):
    """判断实例是否为闲置状态（无云监控插件）"""
    # 获取各项指标
    cpu_util = metrics.get('CPU利用率', 0)
    disk_read_iops = metrics.get('磁盘读IOPS', 0)
    disk_write_iops = metrics.get('磁盘写IOPS', 0)
    
    # 计算总IOPS
    total_iops = disk_read_iops + disk_write_iops
    
    # 判断条件
    conditions = []
    
    # 1. CPU利用率低于5%
    if cpu_util < 5:
        conditions.append(f"CPU利用率({cpu_util:.1f}%) < 5%")
    
    # 2. 磁盘IOPS小于100
    if total_iops < 100:
        conditions.append(f"磁盘IOPS({total_iops:.0f}) < 100")
    
    # 3. EIP带宽使用率检查（如果有EIP）
    if eip_info and eip_info.get('Bandwidth', 0) > 0:
        bandwidth_mbps = eip_info['Bandwidth']
        internet_in_rate = metrics.get('入网流量', 0)
        internet_out_rate = metrics.get('出网流量', 0)
        total_bandwidth_usage = internet_in_rate + internet_out_rate
        
        # 转换为Mbps进行比较
        bandwidth_usage_mbps = total_bandwidth_usage / 1024 / 1024 * 8  # bps转Mbps
        bandwidth_threshold = bandwidth_mbps * 0.1  # 10%阈值
        
        if bandwidth_usage_mbps < bandwidth_threshold:
            conditions.append(f"EIP带宽使用率({bandwidth_usage_mbps:.2f}Mbps) < 峰值*10%({bandwidth_threshold:.2f}Mbps)")
    
    return len(conditions) > 0, conditions

def get_optimization_suggestion(instance, metrics, has_agent):
    """获取优化建议"""
    suggestions = []
    
    if has_agent:
        cpu_util = metrics.get('CPU利用率', 0)
        memory_util = metrics.get('内存利用率', 0)
        disk_read_iops = metrics.get('磁盘读IOPS', 0)
        disk_write_iops = metrics.get('磁盘写IOPS', 0)
        total_iops = disk_read_iops + disk_write_iops
        
        # CPU和内存使用率低，建议降配实例规格
        if cpu_util < 30 and memory_util < 30:
            suggestions.append("建议降配实例规格")
        
        # 磁盘IOPS低，建议降配磁盘规格
        if total_iops < 200:
            suggestions.append("建议降配磁盘规格")
    else:
        cpu_util = metrics.get('CPU利用率', 0)
        disk_read_iops = metrics.get('磁盘读IOPS', 0)
        disk_write_iops = metrics.get('磁盘写IOPS', 0)
        total_iops = disk_read_iops + disk_write_iops
        
        # CPU使用率低，建议降配实例规格
        if cpu_util < 30:
            suggestions.append("建议降配实例规格")
        
        # 磁盘IOPS低，建议降配磁盘规格
        if total_iops < 200:
            suggestions.append("建议降配磁盘规格")
    
    return "; ".join(suggestions) if suggestions else "无需优化"

def generate_excel_report(idle_instances, has_agent=True, output_dir="."):
    """生成Excel报告"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    agent_type = "with_agent" if has_agent else "without_agent"
    filename = os.path.join(output_dir, f"ecs_idle_report_{agent_type}_{timestamp}.xlsx")
    
    # 准备数据
    data = []
    for i, instance in enumerate(idle_instances, 1):
        metrics = instance['Metrics']
        eip_info = instance.get('EipInfo')
        
        # 修复内存单位显示 - 确保显示为GB
        memory_gb = instance['Memory'] / 1024 if instance['Memory'] > 1024 else instance['Memory']
        
        row = {
            '序号': i,
            '实例名称': instance['InstanceName'],
            '实例ID': instance['InstanceId'],
            '区域': instance['Region'],
            '状态': instance['Status'],
            '实例类型': instance['InstanceType'],
            '创建时间': instance['CreationTime'],
            'CPU核心数': instance['Cpu'],
            '内存(GB)': memory_gb,  # 修复：确保显示为GB
            'CPU利用率(%)': metrics.get('CPU利用率', 0),
            '磁盘读IOPS': metrics.get('磁盘读IOPS', 0),
            '磁盘写IOPS': metrics.get('磁盘写IOPS', 0),
            '总磁盘IOPS': metrics.get('磁盘读IOPS', 0) + metrics.get('磁盘写IOPS', 0),
            '入网流量(bps)': metrics.get('入网流量', 0),
            '出网流量(bps)': metrics.get('出网流量', 0),
            '网络连接数': metrics.get('网络连接数', 0),
            '闲置原因': '; '.join(instance.get('IdleConditions', [])),
            '优化建议': instance.get('Optimization', '无'),
            '续费月成本(¥)': instance.get('MonthlyCost', 0)
        }
        
        # 如果有云监控插件，添加更多指标
        if has_agent:
            row.update({
                '内存利用率(%)': metrics.get('内存利用率', 0),
                '5分钟负载': metrics.get('5分钟负载', 0),
                '1分钟负载': metrics.get('1分钟负载', 0),
                '15分钟负载': metrics.get('15分钟负载', 0),
                'Load Average': metrics.get('Load Average', 0),
                'TCP连接数': metrics.get('TCP连接数', 0),
                '内网入带宽(bps)': metrics.get('内网入带宽', 0),
                '内网出带宽(bps)': metrics.get('内网出带宽', 0),
                '磁盘IO队列长度': metrics.get('磁盘IO队列长度', 0)
                # 移除不准确的磁盘利用率指标
            })
        
        # EIP信息
        if eip_info:
            row.update({
                'EIP带宽(Mbps)': eip_info.get('Bandwidth', 0),
                'EIP地址': eip_info.get('EipAddress', '')
            })
        
        data.append(row)
    
    # 创建DataFrame并保存为Excel
    df = pd.DataFrame(data)
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='闲置实例详情', index=False)
        
        # 获取工作表对象以调整列宽
        worksheet = writer.sheets['闲置实例详情']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"✅ Excel报告已生成: {filename}")
    return filename

def generate_html_report(idle_instances, has_agent=True, output_dir="."):
    """生成HTML报告"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    agent_type = "with_agent" if has_agent else "without_agent"
    filename = os.path.join(output_dir, f"ecs_idle_report_{agent_type}_{timestamp}.html")
    
    agent_text = "有云监控插件" if has_agent else "无云监控插件"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>阿里云ECS闲置实例分析报告 - {agent_text}版本</title>
        <style>
            body {{
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
                color: #333;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5em;
                font-weight: 300;
            }}
            .header p {{
                margin: 10px 0 0 0;
                font-size: 1.2em;
                opacity: 0.9;
            }}
            .summary {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                padding: 30px;
                background: #f8f9fa;
            }}
            .summary-card {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .summary-card h3 {{
                margin: 0 0 10px 0;
                color: #667eea;
                font-size: 2em;
            }}
            .summary-card p {{
                margin: 0;
                color: #666;
                font-size: 1.1em;
            }}
            .table-container {{
                padding: 30px;
                overflow-x: auto;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            th {{
                background: #667eea;
                color: white;
                padding: 15px 10px;
                text-align: left;
                font-weight: 600;
                font-size: 0.9em;
            }}
            td {{
                padding: 12px 10px;
                border-bottom: 1px solid #eee;
                font-size: 0.85em;
            }}
            tr:hover {{
                background-color: #f8f9fa;
            }}
            .metric {{
                font-weight: 600;
                color: #667eea;
            }}
            .low-cpu {{ color: #e74c3c; }}
            .medium-cpu {{ color: #f39c12; }}
            .high-cpu {{ color: #27ae60; }}
            .running {{ color: #27ae60; }}
            .stopped {{ color: #e74c3c; }}
            .footer {{
                background: #2c3e50;
                color: white;
                padding: 20px;
                text-align: center;
                font-size: 0.9em;
            }}
            .footer p {{
                margin: 5px 0;
                opacity: 0.8;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>阿里云ECS闲置实例分析报告</h1>
                <p>{agent_text}版本 - 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <div class="summary-card">
                    <h3>{len(idle_instances)}</h3>
                    <p>闲置实例数量</p>
                </div>
                <div class="summary-card">
                    <h3>¥{sum(instance.get('MonthlyCost', 0) for instance in idle_instances):.2f}</h3>
                    <p>续费月成本总计</p>
                </div>
                <div class="summary-card">
                    <h3>{agent_text}</h3>
                    <p>监控插件状态</p>
                </div>
            </div>
            
            <div class="table-container">
                <h2>闲置实例详情</h2>
                <table>
                    <thead>
                        <tr>
                            <th>序号</th>
                            <th>实例名称</th>
                            <th>区域</th>
                            <th>状态</th>
                            <th>实例类型</th>
                            <th>CPU利用率</th>
    """
    
    if has_agent:
        html_content += """
                            <th>内存利用率</th>
                            <th>Load Average</th>
                            <th>磁盘IO队列长度</th>
        """
    
    html_content += """
                            <th>磁盘IOPS</th>
                            <th>闲置原因</th>
                            <th>优化建议</th>
                            <th>续费月成本</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for i, instance in enumerate(idle_instances, 1):
        metrics = instance['Metrics']
        cpu = metrics.get('CPU利用率', 0)
        total_disk_io = metrics.get('磁盘读IOPS', 0) + metrics.get('磁盘写IOPS', 0)
        
        # 状态样式
        status_class = "running" if instance['Status'] == 'Running' else "stopped"
        
        # CPU利用率样式
        if cpu < 5:
            cpu_class = "low-cpu"
        elif cpu < 20:
            cpu_class = "medium-cpu"
        else:
            cpu_class = "high-cpu"
        
        # 成本显示
        monthly_cost = instance.get('MonthlyCost', 0)
        cost_display = f"¥{monthly_cost:.2f}" if monthly_cost > 0 else "无数据"
        
        html_content += f"""
                        <tr>
                            <td>{i}</td>
                            <td>{instance['InstanceName']}</td>
                            <td>{instance['Region']}</td>
                            <td><span class="{status_class}">{instance['Status']}</span></td>
                            <td>{instance['InstanceType']}</td>
                            <td><span class="{cpu_class}">{cpu:.2f}%</span></td>
        """
        
        if has_agent:
            html_content += f"""
                            <td><span class="metric">{metrics.get('内存利用率', 0):.1f}%</span></td>
                            <td><span class="metric">{metrics.get('5分钟负载', 0):.2f}</span></td>
                            <td><span class="metric">{metrics.get('磁盘IO队列长度', 0):.2f}</span></td>
            """
        
        html_content += f"""
                            <td><span class="metric">{total_disk_io:.0f}</span></td>
                            <td><span class="metric">{'; '.join(instance.get('IdleConditions', [])[:2])}</span></td>
                            <td><span class="metric">{instance.get('Optimization', '无')}</span></td>
                            <td><span class="metric">{cost_display}</span></td>
                        </tr>
        """
    
    html_content += """
                    </tbody>
                </table>
            </div>
            
            <div class="footer">
                <p>报告说明：</p>
                <p>• 数据基于最近14天的平均值</p>
                <p>• 闲置实例判断标准：</p>
    """
    
    if has_agent:
        html_content += """
                <p>  - Load Average低于vCPU*5% 或 内存利用率低于20% 或 磁盘IOPS低于100 或 EIP带宽使用率低于峰值*10%</p>
        """
    else:
        html_content += """
                <p>  - CPU利用率低于5% 或 磁盘IOPS低于100 或 EIP带宽使用率低于峰值*10%</p>
        """
    
    html_content += f"""
                <p>• 监控插件状态: {agent_text}</p>
                <p>• 建议定期检查并优化这些实例的配置或考虑停止未使用的实例</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML报告已生成: {filename}")
    return filename


def main(tenant_name=None, output_base_dir=".", tenant_config=None):
    """主函数"""
    global logger
    
    # 初始化日志系统
    if USE_NEW_UTILS:
        log_dir = os.path.join(output_base_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'ecs_analysis.log')
        logger = setup_logger(
            name='aliyunidle',
            log_file=log_file,
            level='INFO',
            console=True
        )
        logger.info("=" * 60)
        logger.info("启动阿里云ECS闲置实例分析程序（优化版 - 支持并发和重试）")
        logger.info("=" * 60)
    
    print("🚀 启动阿里云ECS闲置实例分析程序（优化版 - 支持并发和重试）")
    print("=" * 60)
    
    # 从tenant_config或config.json获取凭证
    if tenant_config:
        set_credentials(tenant_config.get('access_key_id'), tenant_config.get('access_key_secret'))
    else:
        # 尝试从config.json读取
        try:
            import json
            with open('config.json', 'r') as f:
                config = json.load(f)
                if 'default_tenant' in config:
                    default_tenant = config['default_tenant']
                    tenant_config = config['tenants'].get(default_tenant)
                    if tenant_config:
                        set_credentials(tenant_config.get('access_key_id'), tenant_config.get('access_key_secret'))
                else:
                    # 兼容旧格式
                    set_credentials(config.get('access_key_id'), config.get('access_key_secret'))
        except Exception as e:
            print(f"⚠️ 无法读取配置: {e}")
            print("⚠️ 使用默认配置（如果已设置）")
    
    if not access_key_id or not access_key_secret:
        print("❌ 未设置访问凭证，请检查配置")
        return
    
    # 按租户设置存储路径（数据库/缓存）
    set_storage_paths(tenant_name, output_base_dir)

    # 创建输出目录结构
    if tenant_name:
        output_dir = os.path.join(output_base_dir, tenant_name, "cru")
    else:
        output_dir = os.path.join(output_base_dir, "cru")
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 输出目录: {output_dir}")
    
    # 初始化数据库
    print("📊 步骤1/8: 初始化数据库...")
    init_database()
    print("✅ 数据库初始化完成\n")
    
    # 检查缓存（支持通过环境变量强制禁用缓存）
    print("📦 步骤2/8: 检查缓存状态...")
    force_no_cache = os.getenv('ALIYUNIDLE_NO_CACHE') == '1'
    if not force_no_cache and is_cache_valid():
        print("📦 使用缓存数据...")
        cached_data = load_cache_data()
        if cached_data:
            regions_with_ecs = cached_data['regions_with_ecs']
            print(f"✅ 从缓存加载了 {len(regions_with_ecs)} 个区域的ECS实例数据")
        else:
            print("❌ 缓存数据损坏，重新获取数据...")
            cached_data = None
    else:
        if force_no_cache:
            print("🚫 已禁用缓存（ALIYUNIDLE_NO_CACHE=1），重新获取数据...")
        else:
            print("🔄 缓存已过期，重新获取数据...")
        cached_data = None
    print("✅ 缓存检查完成\n")
    
    # 如果没有有效缓存，重新获取数据
    if not cached_data:
        print("🌐 步骤3/8: 获取所有可用区域...")
        client = AcsClient(access_key_id, access_key_secret, 'cn-hangzhou')
        all_regions = get_all_regions(client)
        print(f"✅ 获取到 {len(all_regions)} 个可用Region")
        
        # 指定要检查的region列表，如果为空则检查所有region
        target_regions = []  # 空列表表示检查所有region
        
        if target_regions:
            valid_regions = [r for r in target_regions if r in all_regions]
            invalid_regions = [r for r in target_regions if r not in all_regions]
            if invalid_regions:
                print(f"警告：以下region无效，将被忽略: {invalid_regions}")
            regions = valid_regions
            print(f"指定检查 {len(regions)} 个Region: {regions}")
        else:
            regions = all_regions
            print(f"将检查所有 {len(regions)} 个Region")
        print("✅ 区域配置完成\n")
        
        regions_with_ecs = []
        
        # 第一遍：快速检查哪些region有ECS实例
        print("🔍 步骤4/8: 快速检查各Region是否有ECS实例...")
        print(f"正在检查 {len(regions)} 个Region...")
        for i, region in enumerate(regions, 1):
            try:
                print(f"[{i}/{len(regions)}] 检查Region: {region}", end=" ")
                region_client = AcsClient(access_key_id, access_key_secret, region)
                instances = get_all_instances(region_client, region)
                if len(instances) > 0:
                    regions_with_ecs.append((region, instances))
                    print(f"- 发现 {len(instances)} 台ECS实例")
                else:
                    print("- 无ECS实例，跳过")
            except Exception as e:
                print(f"- 检查失败: {str(e)}")
                continue
        
        print(f"✅ 区域检查完成，找到 {len(regions_with_ecs)} 个有ECS实例的Region\n")
        
        # 保存到缓存
        print("💾 保存数据到缓存...")
        cache_data = {
            'regions_with_ecs': regions_with_ecs,
            'timestamp': time.time()
        }
        save_cache_data(cache_data)
        print("✅ 缓存保存完成\n")
    else:
        regions_with_ecs = cached_data['regions_with_ecs']
        client = AcsClient(access_key_id, access_key_secret, 'cn-hangzhou')
        print("✅ 使用缓存数据，跳过区域检查\n")
    
    print(f"📋 步骤5/8: 开始详细检查 {len(regions_with_ecs)} 个Region的ECS实例...")
    
    # 采集时间窗口（天）支持通过环境变量配置，默认14天
    try:
        metrics_days = int(os.getenv('ALIYUNIDLE_DAYS', '14'))
        if metrics_days <= 0:
            metrics_days = 14
    except Exception:
        metrics_days = 14

    # 准备所有实例数据（用于并发处理）
    all_instances_to_process = []
    for region_idx, (region, instances) in enumerate(regions_with_ecs, 1):
        for instance in instances:
            all_instances_to_process.append({
                'region': region,
                'instance': instance,
                'region_idx': region_idx,
                'total_regions': len(regions_with_ecs)
            })
    
    total_instances = len(all_instances_to_process)
    print(f"📊 准备并发处理 {total_instances} 台ECS实例...")
    
    # 定义单个实例处理函数
    def process_single_instance(item):
        """处理单个实例（用于并发）"""
        region = item['region']
        instance = item['instance']
        iid = instance['InstanceId']
        instance_name = instance['InstanceName']
        
        # 为每个线程创建独立的客户端（线程安全）
        region_client = AcsClient(access_key_id, access_key_secret, region)
        
        try:
            # 获取全面监控数据（从API获取）
            metrics = get_comprehensive_metrics(region_client, region, iid, show_progress=False, days=metrics_days)
            
            # 获取EIP信息
            eip_info = get_instance_eip_info(region_client, region, iid)
            
            # 获取成本信息
            monthly_cost = get_instance_monthly_cost(region_client, region, iid)
            
            # 准备实例数据
            instance_data = {
                'InstanceId': iid,
                'InstanceName': instance_name,
                'Region': region,
                'Status': instance['Status'],
                'InstanceType': instance['InstanceType'],
                'CreationTime': instance['CreationTime'],
                'Cpu': instance['Cpu'],
                'Memory': instance['Memory'],
                'EipBandwidth': eip_info.get('Bandwidth', 0) if eip_info else 0,
                'EipAddress': eip_info.get('EipAddress', '') if eip_info else ''
            }
            
            # 保存到数据库
            save_to_database(instance_data, metrics, monthly_cost)
            
            # 返回结果
            return {
                'InstanceData': instance_data,
                'Metrics': metrics,
                'EipInfo': eip_info,
                'MonthlyCost': monthly_cost,
                'success': True,
                'instance_name': instance_name
            }
        except Exception as e:
            error_msg = str(e)
            if logger:
                logger.error(f"处理实例失败 {instance_name} ({iid}): {error_msg}")
            return {
                'success': False,
                'instance_name': instance_name,
                'error': error_msg
            }
    
    # 使用并发处理
    if USE_NEW_UTILS and total_instances > 1:
        print(f"🚀 使用并发处理（最多10个并发线程）...")
        if logger:
            logger.info(f"开始并发处理 {total_instances} 台实例")
        
        # 进度回调函数
        def progress_callback(completed, total):
            progress_pct = completed / total * 100
            sys.stdout.write(f'\r📊 总进度: {completed}/{total} ({progress_pct:.1f}%)')
            sys.stdout.flush()
        
        # 并发处理
        results = process_concurrently(
            all_instances_to_process,
            process_single_instance,
            max_workers=10,
            description="ECS实例分析",
            progress_callback=progress_callback
        )
        
        # 整理结果
        all_instances_data = []
        success_count = 0
        fail_count = 0
        
        for result in results:
            if result and result.get('success'):
                all_instances_data.append({
                    'InstanceData': result['InstanceData'],
                    'Metrics': result['Metrics'],
                    'EipInfo': result['EipInfo'],
                    'MonthlyCost': result['MonthlyCost']
                })
                success_count += 1
            else:
                fail_count += 1
        
        print(f"\n✅ 并发处理完成: 成功 {success_count} 台, 失败 {fail_count} 台")
        if logger:
            logger.info(f"并发处理完成: 成功 {success_count} 台, 失败 {fail_count} 台")
    else:
        # 兼容模式：串行处理
        if USE_NEW_UTILS:
            print("⚠️  并发工具可用，但实例数量为1，使用串行处理")
        
        all_instances_data = []
        processed_count = 0
        
        for region_idx, (region, instances) in enumerate(regions_with_ecs, 1):
            print(f"\n[{region_idx}/{len(regions_with_ecs)}] 正在检查Region: {region} ({len(instances)}台实例)")
            region_client = AcsClient(access_key_id, access_key_secret, region)
            
            for i, instance in enumerate(instances, 1):
                iid = instance['InstanceId']
                instance_name = instance['InstanceName']
                processed_count += 1
                
                # 显示进度信息
                progress_pct = processed_count / total_instances * 100
                print(f"  [{i}/{len(instances)}] 📊 总进度: {processed_count}/{total_instances} ({progress_pct:.1f}%) - {instance_name}")
                
                try:
                    # 获取全面监控数据（从API获取）
                    print(f"    📡 正在获取监控数据...", end="", flush=True)
                    metrics = get_comprehensive_metrics(region_client, region, iid, show_progress=True, days=metrics_days)
                    
                    # 获取EIP信息
                    print(f"    🔗 获取EIP信息...", end="", flush=True)
                    eip_info = get_instance_eip_info(region_client, region, iid)
                    print(" ✅")
                    
                    # 获取成本信息
                    print(f"    💰 获取成本信息...", end="", flush=True)
                    monthly_cost = get_instance_monthly_cost(region_client, region, iid)
                    print(" ✅")
                    
                    # 准备实例数据
                    instance_data = {
                        'InstanceId': iid,
                        'InstanceName': instance_name,
                        'Region': region,
                        'Status': instance['Status'],
                        'InstanceType': instance['InstanceType'],
                        'CreationTime': instance['CreationTime'],
                        'Cpu': instance['Cpu'],
                        'Memory': instance['Memory'],
                        'EipBandwidth': eip_info.get('Bandwidth', 0) if eip_info else 0,
                        'EipAddress': eip_info.get('EipAddress', '') if eip_info else ''
                    }
                    
                    # 保存到数据库
                    print(f"    💾 保存数据到数据库...", end="", flush=True)
                    save_to_database(instance_data, metrics, monthly_cost)
                    print(" ✅")
                    
                    # 添加到总数据
                    all_instances_data.append({
                        'InstanceData': instance_data,
                        'Metrics': metrics,
                        'EipInfo': eip_info,
                        'MonthlyCost': monthly_cost
                    })
                    
                    has_agent = "有插件" if metrics.get('_has_agent', False) else "无插件"
                    print(f"    ✅ 完成 ({has_agent})")
                    
                except Exception as e:
                    print(f"\n    ❌ 检查失败: {str(e)}")
                
                time.sleep(0.2)  # 避免API限流
    
    print(f"\n✅ 步骤5/8完成: 数据收集完成，共处理 {len(all_instances_data)} 台实例\n")
    
    # 分析闲置实例（有云监控插件版本）
    print("🔍 步骤6/8: 分析闲置实例（有云监控插件版本）...")
    idle_instances_with_agent = []
    
    for data in all_instances_data:
        instance = data['InstanceData']
        metrics = data['Metrics']
        eip_info = data['EipInfo']
        
        # 检查是否有云监控插件数据
        # 优先使用数据库标记，如果没有则通过值判断
        has_agent = metrics.get('_has_agent', False)
        if not has_agent:
            # 如果数据库中没有标记，检查是否有这些指标的数据（即使值为0）
            # 检查数据库中是否有这些指标的记录
            has_agent = (metrics.get('内存利用率') is not None or 
                        metrics.get('5分钟负载') is not None or 
                        metrics.get('TCP连接数') is not None)
        
        if has_agent:
            is_idle, conditions = is_instance_idle_with_agent(instance, metrics, eip_info)
            if is_idle:
                optimization = get_optimization_suggestion(instance, metrics, True)
                idle_instances_with_agent.append({
                    'InstanceId': instance['InstanceId'],
                    'InstanceName': instance['InstanceName'],
                    'Region': instance['Region'],
                    'Status': instance['Status'],
                    'InstanceType': instance['InstanceType'],
                    'CreationTime': instance['CreationTime'],
                    'Cpu': instance['Cpu'],
                    'Memory': instance['Memory'],
                    'Metrics': metrics,
                    'EipInfo': eip_info,
                    'IdleConditions': conditions,
                    'Optimization': optimization,
                    'MonthlyCost': data['MonthlyCost']
                })
    
    print(f"✅ 有云监控插件闲置实例: {len(idle_instances_with_agent)} 台")
    
    # 分析闲置实例（无云监控插件版本）
    print("🔍 步骤7/8: 分析闲置实例（无云监控插件版本）...")
    idle_instances_without_agent = []
    
    for data in all_instances_data:
        instance = data['InstanceData']
        metrics = data['Metrics']
        eip_info = data['EipInfo']
        
        # 检查是否有云监控插件数据
        # 优先使用数据库标记，如果没有则通过值判断
        has_agent = metrics.get('_has_agent', False)
        if not has_agent:
            # 如果数据库中没有标记，检查是否有这些指标的数据（即使值为0）
            has_agent = (metrics.get('内存利用率') is not None or 
                        metrics.get('5分钟负载') is not None or 
                        metrics.get('TCP连接数') is not None)
        
        if not has_agent:
            is_idle, conditions = is_instance_idle_without_agent(instance, metrics, eip_info)
            if is_idle:
                optimization = get_optimization_suggestion(instance, metrics, False)
                idle_instances_without_agent.append({
                    'InstanceId': instance['InstanceId'],
                    'InstanceName': instance['InstanceName'],
                    'Region': instance['Region'],
                    'Status': instance['Status'],
                    'InstanceType': instance['InstanceType'],
                    'CreationTime': instance['CreationTime'],
                    'Cpu': instance['Cpu'],
                    'Memory': instance['Memory'],
                    'Metrics': metrics,
                    'EipInfo': eip_info,
                    'IdleConditions': conditions,
                    'Optimization': optimization,
                    'MonthlyCost': data['MonthlyCost']
                })
    
    print(f"✅ 无云监控插件闲置实例: {len(idle_instances_without_agent)} 台")
    print("✅ 步骤6-7/8完成: 闲置实例分析完成\n")
    
    # 生成报告
    print("📋 步骤8/8: 生成报告文件...")
    print(f"📊 报告统计:")
    print(f"  - 有云监控插件闲置实例: {len(idle_instances_with_agent)} 台")
    print(f"  - 无云监控插件闲置实例: {len(idle_instances_without_agent)} 台")
    
    # 生成报告文件
    generated_files = []
    
    # 生成有云监控插件版本报告
    if idle_instances_with_agent:
        print(f"\n📊 生成有云监控插件版本报告...")
        print("  - 生成Excel报告...")
        excel_file_with_agent = generate_excel_report(idle_instances_with_agent, has_agent=True, output_dir=output_dir)
        print("  - 生成HTML报告...")
        html_file_with_agent = generate_html_report(idle_instances_with_agent, has_agent=True, output_dir=output_dir)
        
        generated_files.extend([
            f"✅ Excel报告: {excel_file_with_agent}",
            f"✅ HTML报告: {html_file_with_agent}"
        ])
        print("✅ 有云监控插件版本报告生成完成")
    else:
        print("⚠️ 没有找到有云监控插件的闲置实例，跳过报告生成")
    
    # 生成无云监控插件版本报告
    if idle_instances_without_agent:
        print(f"\n📊 生成无云监控插件版本报告...")
        print("  - 生成Excel报告...")
        excel_file_without_agent = generate_excel_report(idle_instances_without_agent, has_agent=False, output_dir=output_dir)
        print("  - 生成HTML报告...")
        html_file_without_agent = generate_html_report(idle_instances_without_agent, has_agent=False, output_dir=output_dir)
        
        generated_files.extend([
            f"✅ Excel报告: {excel_file_without_agent}",
            f"✅ HTML报告: {html_file_without_agent}"
        ])
        print("✅ 无云监控插件版本报告生成完成")
    else:
        print("⚠️ 没有找到无云监控插件的闲置实例，跳过报告生成")
    
    print("\n" + "=" * 60)
    print("🎉 程序执行完成！")
    print("=" * 60)
    print("📁 生成的文件:")
    print(f"  - 数据库文件: {DB_FILE}")
    print(f"  - 缓存文件: {CACHE_FILE}")
    for file_info in generated_files:
        print(f"  - {file_info}")
    print("=" * 60)

if __name__ == "__main__":
    main()
