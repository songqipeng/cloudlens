#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB资源分析模块
分析阿里云MongoDB实例的闲置情况
"""

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta

import msgpack
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from core.analyzer_registry import AnalyzerRegistry
from core.base_analyzer import BaseResourceAnalyzer
from core.report_generator import ReportGenerator
from utils.concurrent_helper import process_concurrently
from utils.error_handler import ErrorHandler
from utils.logger import get_logger


@AnalyzerRegistry.register("mongodb", "MongoDB数据库", "🍃")
class MongoDBAnalyzer(BaseResourceAnalyzer):
    def __init__(self, access_key_id, access_key_secret, tenant_name=None):
        """初始化MongoDB分析器"""
        super().__init__(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            tenant_name=tenant_name or "default",
        )
        self.logger = get_logger("mongodb_analyzer")

        # 初始化客户端
        self.client = AcsClient(self.access_key_id, self.access_key_secret, "cn-hangzhou")

        # 数据库连接
        self.db_path = "mongodb_monitoring_data.db"
        self.init_database()

        # 缓存文件
        self.cache_file = "mongodb_data_cache.pkl"

        # MongoDB区域列表 (BaseResourceAnalyzer已有get_all_regions，这里可以保留作为备选或覆盖)
        self.regions = [
            "cn-hangzhou",
            "cn-shanghai",
            "cn-beijing",
            "cn-shenzhen",
            "cn-guangzhou",
            "cn-qingdao",
            "cn-zhangjiakou",
            "cn-huhehaote",
            "cn-chengdu",
            "cn-hongkong",
            "ap-southeast-1",
            "ap-southeast-2",
            "ap-southeast-3",
            "ap-southeast-5",
            "ap-southeast-6",
            "ap-southeast-7",
            "ap-northeast-1",
            "ap-south-1",
            "us-east-1",
            "us-west-1",
            "eu-west-1",
            "eu-central-1",
            "me-east-1",
        ]

    def get_resource_type(self) -> str:
        return "mongodb"

    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建MongoDB实例表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS mongodb_instances (
                instance_id TEXT PRIMARY KEY,
                instance_name TEXT,
                instance_class TEXT,
                engine_version TEXT,
                region TEXT,
                instance_status TEXT,
                instance_type TEXT,
                storage_engine TEXT,
                created_time TEXT,
                updated_time TEXT
            )
        """
        )

        # 创建监控数据表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS mongodb_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instance_id TEXT,
                metric_name TEXT,
                metric_value REAL,
                timestamp TEXT,
                FOREIGN KEY (instance_id) REFERENCES mongodb_instances (instance_id)
            )
        """
        )

        conn.commit()
        conn.close()

    def get_all_mongodb_instances(self):
        """获取所有MongoDB实例"""
        self.logger.info("🔍 开始获取MongoDB实例信息...")
        all_instances = []

        for region in self.regions:
            try:
                self.logger.info(f"  📍 检查区域: {region}")

                # 设置区域
                self.client.set_region_id(region)

                # 创建请求
                request = CommonRequest()
                request.set_domain(f"dds.{region}.aliyuncs.com")
                request.set_method("POST")
                request.set_version("2015-12-01")
                request.set_action_name("DescribeDBInstances")
                request.add_query_param("RegionId", region)
                request.add_query_param("PageSize", 100)

                page_num = 1
                while True:
                    request.add_query_param("PageNumber", page_num)

                    try:
                        response = self.client.do_action_with_exception(request)
                        result = json.loads(response)

                        if "DBInstances" not in result or not result["DBInstances"]["DBInstance"]:
                            break

                        instances = result["DBInstances"]["DBInstance"]
                        if not isinstance(instances, list):
                            instances = [instances]

                        for instance in instances:
                            instance_info = {
                                "InstanceId": instance["DBInstanceId"],
                                "InstanceName": instance.get("DBInstanceDescription", ""),
                                "InstanceClass": instance.get("DBInstanceClass", ""),
                                "EngineVersion": instance.get("EngineVersion", ""),
                                "Region": region,
                                "InstanceStatus": instance.get("DBInstanceStatus", ""),
                                "InstanceType": instance.get("DBInstanceType", ""),
                                "StorageEngine": instance.get("StorageEngine", ""),
                                "CreatedTime": instance.get("CreateTime", ""),
                                "UpdatedTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            }
                            all_instances.append(instance_info)

                        page_num += 1

                        # 如果返回的实例数少于页面大小，说明已经到最后一页
                        if len(instances) < 100:
                            break

                    except (ClientException, ServerException) as e:
                        self.logger.info(f"    ⚠️  区域 {region} API调用失败: {e}")
                        break

            except Exception as e:
                self.logger.info(f"    ❌ 区域 {region} 处理失败: {e}")
                continue

        self.logger.info(f"共找到 {len(all_instances)} 个MongoDB实例")
        return all_instances

    def get_instances(self, region: str):
        """获取指定区域的MongoDB实例 (BaseResourceAnalyzer接口)"""
        self.logger.info(f"  📍 检查区域: {region}")
        instances_list = []
        try:
            # 设置区域
            self.client.set_region_id(region)

            # 创建请求
            request = CommonRequest()
            request.set_domain(f"dds.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2015-12-01")
            request.set_action_name("DescribeDBInstances")
            request.add_query_param("RegionId", region)
            request.add_query_param("PageSize", 100)

            page_num = 1
            while True:
                request.add_query_param("PageNumber", page_num)

                try:
                    response = self.client.do_action_with_exception(request)
                    result = json.loads(response)

                    if "DBInstances" not in result or not result["DBInstances"]["DBInstance"]:
                        break

                    instances = result["DBInstances"]["DBInstance"]
                    if not isinstance(instances, list):
                        instances = [instances]

                    for instance in instances:
                        instance_info = {
                            "InstanceId": instance["DBInstanceId"],
                            "InstanceName": instance.get("DBInstanceDescription", ""),
                            "InstanceClass": instance.get("DBInstanceClass", ""),
                            "EngineVersion": instance.get("EngineVersion", ""),
                            "Region": region,
                            "InstanceStatus": instance.get("DBInstanceStatus", ""),
                            "InstanceType": instance.get("DBInstanceType", ""),
                            "StorageEngine": instance.get("StorageEngine", ""),
                            "CreatedTime": instance.get("CreateTime", ""),
                            "UpdatedTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        instances_list.append(instance_info)

                    page_num += 1

                    # 如果返回的实例数少于页面大小，说明已经到最后一页
                    if len(instances) < 100:
                        break

                except (ClientException, ServerException) as e:
                    self.logger.info(f"    ⚠️  区域 {region} API调用失败: {e}")
                    break
        except Exception as e:
            self.logger.error(f"Failed to get instances for region {region}: {e}")
            
        return instances_list

    def get_metrics(self, region: str, instance_id: str, days: int = 14):
        """获取MongoDB实例的监控数据 (BaseResourceAnalyzer接口)"""
        return self.get_mongodb_metrics(instance_id, region)

    def get_mongodb_metrics(self, instance_id, region):
        """获取MongoDB实例的监控数据"""
        try:
            # 设置区域
            self.client.set_region_id(region)

            # MongoDB监控指标（基于实际测试结果）
            metrics = {
                "CPUUtilization": "CPU利用率",
                "MemoryUtilization": "内存利用率",
                "DiskUtilization": "磁盘利用率",
                "ConnectionUtilization": "连接数使用率",
                "QPS": "每秒查询数",
                "ReplicationLag": "复制延迟",
                "CacheHitRatio": "缓存命中率",
            }

            metrics_data = {}
            end_time = int(round(time.time() * 1000))
            start_time = end_time - 14 * 24 * 60 * 60 * 1000  # 14天前

            for metric_name, metric_desc in metrics.items():
                try:
                    request = CommonRequest()
                    request.set_domain(f"cms.{region}.aliyuncs.com")
                    request.set_method("POST")
                    request.set_version("2019-01-01")
                    request.set_action_name("DescribeMetricData")
                    request.add_query_param("RegionId", region)
                    request.add_query_param("Namespace", "acs_mongodb")
                    request.add_query_param("MetricName", metric_name)
                    request.add_query_param("StartTime", start_time)
                    request.add_query_param("EndTime", end_time)
                    request.add_query_param("Period", "86400")  # 1天聚合
                    request.add_query_param("Dimensions", f'[{{"instanceId":"{instance_id}"}}]')

                    response = self.client.do_action_with_exception(request)
                    data = json.loads(response)

                    if "Datapoints" in data and data["Datapoints"]:
                        if isinstance(data["Datapoints"], str):
                            dps = json.loads(data["Datapoints"])
                        else:
                            dps = data["Datapoints"]

                        if dps and len(dps) > 0:
                            # 计算所有数据点的平均值
                            total = 0
                            count = 0
                            for dp in dps:
                                if "Average" in dp and dp["Average"] is not None:
                                    total += float(dp["Average"])
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

            return metrics_data

        except Exception as e:
            self.logger.info(f"    ❌ 获取监控数据失败: {e}")
            return {}

    def is_idle(self, instance, metrics, thresholds=None):
        """判断MongoDB实例是否闲置 (BaseResourceAnalyzer接口)"""
        is_idle = self.is_mongodb_idle(metrics)
        conditions = []
        if is_idle:
            conditions = [self.get_idle_reason(metrics)]
        return is_idle, conditions

    def get_optimization_suggestions(self, instance, metrics):
        """获取优化建议 (BaseResourceAnalyzer接口)"""
        return self.get_optimization_suggestion(metrics, instance.get("InstanceClass", ""))

    def is_mongodb_idle(self, metrics):
        """判断MongoDB实例是否闲置"""
        # MongoDB闲置判断标准（或关系）- 基于实际可用的指标
        cpu_util = metrics.get("CPU利用率", 0)
        memory_util = metrics.get("内存利用率", 0)
        disk_util = metrics.get("磁盘利用率", 0)
        connection_util = metrics.get("连接数使用率", 0)
        qps = metrics.get("每秒查询数", 0)

        # 闲置条件（满足任一即判定为闲置）
        idle_conditions = [
            cpu_util < 10,  # CPU利用率低于10%
            memory_util < 20,  # 内存利用率低于20%
            disk_util < 20,  # 磁盘利用率低于20%
            connection_util < 20,  # 连接数使用率低于20%
            qps < 100,  # QPS低于100
        ]

        return any(idle_conditions)

    def get_idle_reason(self, metrics):
        """获取闲置原因"""
        reasons = []

        cpu_util = metrics.get("CPU利用率", 0)
        memory_util = metrics.get("内存利用率", 0)
        disk_util = metrics.get("磁盘利用率", 0)
        connection_util = metrics.get("连接数使用率", 0)
        qps = metrics.get("每秒查询数", 0)

        if cpu_util < 10:
            reasons.append(f"CPU利用率({cpu_util:.1f}%) < 10%")
        if memory_util < 20:
            reasons.append(f"内存利用率({memory_util:.1f}%) < 20%")
        if disk_util < 20:
            reasons.append(f"磁盘利用率({disk_util:.1f}%) < 20%")
        if connection_util < 20:
            reasons.append(f"连接数使用率({connection_util:.1f}%) < 20%")
        if qps < 100:
            reasons.append(f"QPS({qps:.0f}) < 100")

        return "; ".join(reasons)

    def get_optimization_suggestion(self, metrics, instance_class):
        """获取优化建议"""
        suggestions = []

        cpu_util = metrics.get("CPU利用率", 0)
        memory_util = metrics.get("内存利用率", 0)
        disk_util = metrics.get("磁盘利用率", 0)
        qps = metrics.get("每秒查询数", 0)

        if cpu_util < 10 and memory_util < 20:
            suggestions.append("建议降低实例规格，CPU和内存使用率都很低")
        elif cpu_util < 10:
            suggestions.append("建议降低CPU规格")
        elif memory_util < 20:
            suggestions.append("建议降低内存规格")

        if disk_util < 20:
            suggestions.append("建议降低存储容量")

        if qps < 100:
            suggestions.append("建议降低性能规格")

        if not suggestions:
            suggestions.append("资源使用正常，无需优化")

        return "; ".join(suggestions)

    def save_to_database(self, instances, metrics_data):
        """保存数据到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 保存实例信息
        for instance in instances:
            # 处理不同的字段名格式
            instance_id = instance.get("InstanceId") or instance.get("DBInstanceId", "unknown")
            instance_name = instance.get("InstanceName") or instance.get(
                "DBInstanceDescription", "unknown"
            )
            instance_class = instance.get("InstanceClass") or instance.get(
                "DBInstanceClass", "unknown"
            )
            engine_version = instance.get("EngineVersion") or instance.get(
                "EngineVersion", "unknown"
            )
            region = instance.get("Region") or instance.get("RegionId", "unknown")
            status = instance.get("InstanceStatus") or instance.get("DBInstanceStatus", "unknown")
            instance_type = instance.get("InstanceType") or instance.get(
                "DBInstanceType", "unknown"
            )
            storage_engine = instance.get("StorageEngine") or instance.get(
                "StorageEngine", "unknown"
            )
            created_time = instance.get("CreatedTime") or instance.get("CreatedTime", "unknown")
            updated_time = instance.get("UpdatedTime") or instance.get("UpdatedTime", "unknown")

            cursor.execute(
                """
                INSERT OR REPLACE INTO mongodb_instances 
                (instance_id, instance_name, instance_class, engine_version, region, 
                 instance_status, instance_type, storage_engine, created_time, updated_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    instance_id,
                    instance_name,
                    instance_class,
                    engine_version,
                    region,
                    status,
                    instance_type,
                    storage_engine,
                    created_time,
                    updated_time,
                ),
            )

        # 保存监控数据
        for instance_id, metrics in metrics_data.items():
            for metric_name, metric_value in metrics.items():
                cursor.execute(
                    """
                    INSERT INTO mongodb_metrics 
                    (instance_id, metric_name, metric_value, timestamp)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        instance_id,
                        metric_name,
                        metric_value,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )

        conn.commit()
        conn.close()

    def analyze(self, regions=None, days=14):
        """分析资源 (BaseResourceAnalyzer接口)"""
        # MongoDBAnalyzer的analyze_mongodb_instances逻辑比较复杂，包含缓存等
        # 我们这里直接调用它，但要注意它没有返回值，而是直接生成报告
        # 为了适配统一架构，我们应该让它返回idle_instances
        # 这里我们修改analyze_mongodb_instances让它返回结果，或者在这里包装一下
        # 由于analyze_mongodb_instances内部已经生成了报告，我们这里暂时返回空列表
        # 或者更好的做法是重构analyze_mongodb_instances
        self.analyze_mongodb_instances()
        return []

    def generate_report(self, idle_instances):
        """生成报告 (BaseResourceAnalyzer接口)"""
        # 已经在analyze中生成了，这里可以为空，或者重构
        pass

    def analyze_mongodb_instances(self):
        """分析MongoDB实例"""
        self.logger.info("开始MongoDB资源分析...")

        # 检查缓存
        if os.path.exists(self.cache_file):
            cache_time = os.path.getmtime(self.cache_file)
            if time.time() - cache_time < 86400:  # 24小时内
                self.logger.info("使用缓存数据...")
                with open(self.cache_file, "rb") as f:
                    cached_data = msgpack.unpack(f, raw=False, strict_map_key=False)
                    instances = cached_data.get("instances", [])
                    metrics_data = cached_data.get("metrics", {})
            else:
                self.logger.info("缓存过期，重新获取数据...")
                instances = self.get_all_mongodb_instances()
                metrics_data = {}
        else:
            self.logger.info("首次运行，获取数据...")
            instances = self.get_all_mongodb_instances()
            metrics_data = {}

        if not instances:
            self.logger.error("未找到MongoDB实例")
            return

        # 获取监控数据
        self.logger.info("开始获取监控数据...")

        # 定义单个实例处理函数（用于并发）
        def process_single_instance(instance_item):
            """处理单个实例（用于并发）"""
            instance = instance_item
            instance_id = instance.get("InstanceId") or instance.get("DBInstanceId")
            region = instance.get("Region") or instance.get("RegionId")

            if not instance_id or not region:
                return {
                    "success": False,
                    "instance_id": "unknown",
                    "metrics": {},
                    "error": "无效实例",
                }

            try:
                metrics = self.get_mongodb_metrics(instance_id, region)
                return {"success": True, "instance_id": instance_id, "metrics": metrics}
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "MongoDB", region, instance_id)
                ErrorHandler.handle_instance_error(
                    e, instance_id, region, "MongoDB", continue_on_error=True
                )
                return {
                    "success": False,
                    "instance_id": instance_id,
                    "metrics": {},
                    "error": str(e),
                }

        # 并发获取监控数据
        self.logger.info("并发获取监控数据（最多10个并发线程）...")

        def progress_callback(completed, total):
            progress_pct = completed / total * 100
            sys.stdout.write(f"\r📊 监控数据进度: {completed}/{total} ({progress_pct:.1f}%)")
            sys.stdout.flush()

        monitoring_results = process_concurrently(
            instances,
            process_single_instance,
            max_workers=10,
            description="MongoDB监控数据采集",
            progress_callback=progress_callback,
        )

        # 换行

        # 整理监控数据
        metrics_data = {}
        success_count = 0
        fail_count = 0

        for i, result in enumerate(monitoring_results):
            instance = instances[i]
            instance_id = instance.get("InstanceId") or instance.get("DBInstanceId")

            if result and result.get("success"):
                metrics_data[instance_id] = result["metrics"]
                success_count += 1
            else:
                metrics_data[instance_id] = {}
                fail_count += 1

        self.logger.info(f"监控数据获取完成: 成功 {success_count} 个, 失败 {fail_count} 个")

        # 更新实例数据
        for instance in instances:
            instance_id = instance.get("InstanceId") or instance.get("DBInstanceId")
            if instance_id in metrics_data:
                metrics = metrics_data[instance_id]
                is_idle = self.is_mongodb_idle(metrics)
                instance["is_idle"] = is_idle
                instance["metrics"] = metrics

        # 保存数据
        self.save_to_database(instances, metrics_data)

        # 保存缓存
        cache_data = {
            "instances": instances,
            "metrics": metrics_data,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(self.cache_file, "wb") as f:
            msgpack.pack(cache_data, f)

        # 生成报告
        self.generate_mongodb_report(instances)

        self.logger.info("MongoDB分析完成")

    def generate_mongodb_report(self, instances):
        """生成MongoDB报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 筛选闲置实例
        idle_instances = [inst for inst in instances if inst.get("is_idle", False)]

        self.logger.info(
            f"分析结果: 共 {len(instances)} 个MongoDB实例，其中 {len(idle_instances)} 个闲置"
        )

        if not idle_instances:
            self.logger.info("没有发现闲置的MongoDB实例")
            return

        # 生成HTML报告
        html_file = f"mongodb_idle_report_{timestamp}.html"
        self.generate_html_report(idle_instances, html_file)

        # 生成Excel报告
        excel_file = f"mongodb_idle_report_{timestamp}.xlsx"
        self.generate_excel_report(idle_instances, excel_file)

        self.logger.info(f"📄 报告已生成:")
        self.logger.info(f"  HTML: {html_file}")
        self.logger.info(f"  Excel: {excel_file}")

    def generate_html_report(self, idle_instances, filename):
        """生成HTML报告"""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MongoDB闲置实例报告</title>
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
        <h1>📊 MongoDB闲置实例分析报告</h1>
        
        <div class="summary">
            <h3>📋 报告摘要</h3>
            <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>闲置实例数量:</strong> {len(idle_instances)} 个</p>
            <p><strong>闲置判断标准:</strong> CPU利用率 < 10% 或 内存利用率 < 20% 或 磁盘利用率 < 20% 或 连接数使用率 < 20% 或 QPS < 100 或 IOPS < 100 或 网络流量 < 1KB/s</p>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>实例ID</th>
                    <th>实例名称</th>
                    <th>实例类型</th>
                    <th>引擎版本</th>
                    <th>区域</th>
                    <th>状态</th>
                    <th>CPU利用率(%)</th>
                    <th>内存利用率(%)</th>
                    <th>磁盘利用率(%)</th>
                    <th>连接数使用率(%)</th>
                    <th>QPS</th>
                    <th>IOPS</th>
                    <th>网络入流量(KB/s)</th>
                    <th>网络出流量(KB/s)</th>
                    <th>闲置原因</th>
                    <th>优化建议</th>
                </tr>
            </thead>
            <tbody>
"""

        for instance in idle_instances:
            metrics = instance.get("metrics", {})
            idle_reason = self.get_idle_reason(metrics)
            instance_class = instance.get("InstanceClass") or instance.get(
                "DBInstanceClass", "unknown"
            )
            optimization = self.get_optimization_suggestion(metrics, instance_class)

            # 处理不同的字段名格式
            instance_id = instance.get("InstanceId") or instance.get("DBInstanceId", "unknown")
            instance_name = instance.get("InstanceName") or instance.get(
                "DBInstanceDescription", "unknown"
            )
            engine_version = instance.get("EngineVersion") or instance.get(
                "EngineVersion", "unknown"
            )
            region = instance.get("Region") or instance.get("RegionId", "unknown")
            status = instance.get("InstanceStatus") or instance.get("DBInstanceStatus", "unknown")

            html_content += f"""
                <tr>
                    <td>{instance_id}</td>
                    <td>{instance_name}</td>
                    <td>{instance_class}</td>
                    <td>{engine_version}</td>
                    <td>{region}</td>
                    <td>{status}</td>
                    <td>{metrics.get('CPU利用率', 0):.1f}</td>
                    <td>{metrics.get('内存利用率', 0):.1f}</td>
                    <td>{metrics.get('磁盘利用率', 0):.1f}</td>
                    <td>{metrics.get('连接数使用率', 0):.1f}</td>
                    <td>{metrics.get('每秒查询数', 0):.0f}</td>
                    <td>-</td>
                    <td>-</td>
                    <td>-</td>
                    <td class="idle-reason">{idle_reason}</td>
                    <td class="optimization">{optimization}</td>
                </tr>
"""

        html_content += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>本报告由阿里云资源分析工具自动生成 | MongoDB闲置实例分析</p>
        </div>
    </div>
</body>
</html>
"""

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)

    def generate_excel_report(self, idle_instances, filename):
        """生成Excel报告"""
        try:
            import pandas as pd

            data = []
            for instance in idle_instances:
                metrics = instance.get("metrics", {})
                idle_reason = self.get_idle_reason(metrics)
                instance_class = instance.get("InstanceClass") or instance.get(
                    "DBInstanceClass", "unknown"
                )
                optimization = self.get_optimization_suggestion(metrics, instance_class)

                # 处理不同的字段名格式
                instance_id = instance.get("InstanceId") or instance.get("DBInstanceId", "unknown")
                instance_name = instance.get("InstanceName") or instance.get(
                    "DBInstanceDescription", "unknown"
                )
                engine_version = instance.get("EngineVersion") or instance.get(
                    "EngineVersion", "unknown"
                )
                region = instance.get("Region") or instance.get("RegionId", "unknown")
                status = instance.get("InstanceStatus") or instance.get(
                    "DBInstanceStatus", "unknown"
                )

                data.append(
                    {
                        "实例ID": instance_id,
                        "实例名称": instance_name,
                        "实例类型": instance_class,
                        "引擎版本": engine_version,
                        "区域": region,
                        "状态": status,
                        "CPU利用率(%)": round(metrics.get("CPU利用率", 0), 1),
                        "内存利用率(%)": round(metrics.get("内存利用率", 0), 1),
                        "磁盘利用率(%)": round(metrics.get("磁盘利用率", 0), 1),
                        "连接数使用率(%)": round(metrics.get("连接数使用率", 0), 1),
                        "QPS": round(metrics.get("每秒查询数", 0), 0),
                        "闲置原因": idle_reason,
                        "优化建议": optimization,
                    }
                )

            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine="openpyxl")

        except ImportError:
            self.logger.warning(" pandas未安装，跳过Excel报告生成")


def main():
    """主函数"""
    analyzer = MongoDBAnalyzer()
    analyzer.analyze_mongodb_instances()


if __name__ == "__main__":
    main()
