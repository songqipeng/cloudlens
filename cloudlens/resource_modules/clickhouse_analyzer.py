#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClickHouse资源分析模块
分析阿里云ClickHouse实例的闲置情况，提供优化建议
"""

import json
import sqlite3
import sys
import time
from datetime import datetime

import pandas as pd
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from cloudlens.core.analyzer_registry import AnalyzerRegistry
from cloudlens.core.base_analyzer import BaseResourceAnalyzer
from cloudlens.core.report_generator import ReportGenerator
from cloudlens.utils.concurrent_helper import process_concurrently
from cloudlens.utils.error_handler import ErrorHandler
from cloudlens.utils.logger import get_logger


@AnalyzerRegistry.register("clickhouse", "ClickHouse数据仓库", "📊")
class ClickHouseAnalyzer(BaseResourceAnalyzer):
    """ClickHouse资源分析器"""

    def __init__(self, access_key_id, access_key_secret, tenant_name=None):
        super().__init__(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            tenant_name=tenant_name or "default",
        )
        self.db_name = "clickhouse_monitoring_data.db"
        self.logger = get_logger("clickhouse_analyzer")

    def get_resource_type(self) -> str:
        return "clickhouse"

    def init_database(self):
        """初始化ClickHouse数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # 创建ClickHouse实例表
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS clickhouse_instances (
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
        """
        )

        # 创建ClickHouse监控数据表
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS clickhouse_monitoring_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id TEXT,
            metric_name TEXT,
            metric_value REAL,
            timestamp INTEGER,
            FOREIGN KEY (instance_id) REFERENCES clickhouse_instances (instance_id)
        )
        """
        )

        conn.commit()
        conn.close()
        self.logger.info("ClickHouse数据库初始化完成")

    def get_all_regions(self):
        """获取所有可用区域"""
        client = AcsClient(self.access_key_id, self.access_key_secret, "cn-hangzhou")
        request = CommonRequest()
        request.set_domain("ecs.cn-hangzhou.aliyuncs.com")
        request.set_method("POST")
        request.set_version("2014-05-26")
        request.set_action_name("DescribeRegions")

        response = client.do_action_with_exception(request)
        data = json.loads(response)

        regions = []
        for region in data["Regions"]["Region"]:
            regions.append(region["RegionId"])

        return regions

    def get_instances(self, region: str):
        """获取指定区域的ClickHouse实例 (BaseResourceAnalyzer接口)"""
        return self.get_clickhouse_instances(region)

    def get_clickhouse_instances(self, region_id):
        """获取指定区域的ClickHouse实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = CommonRequest()
            request.set_domain("clickhouse.{}.aliyuncs.com".format(region_id))
            request.set_method("POST")
            request.set_version("2019-11-11")
            request.set_action_name("DescribeDBInstances")
            request.add_query_param("PageSize", 100)
            request.add_query_param("PageNumber", 1)

            # 尝试获取所有页
            all_instances = []
            page_number = 1

            while True:
                request.add_query_param("PageNumber", page_number)
                response = client.do_action_with_exception(request)
                data = json.loads(response)

                if "Items" in data and "DBInstance" in data["Items"]:
                    instances = data["Items"]["DBInstance"]
                    if not isinstance(instances, list):
                        instances = [instances]

                    if len(instances) == 0:
                        break

                    for instance in instances:
                        all_instances.append(
                            {
                                "InstanceId": instance.get("DBInstanceId", ""),
                                "DBInstanceDescription": instance.get("DBInstanceDescription", ""),
                                "DBInstanceType": instance.get("DBInstanceType", ""),
                                "EngineVersion": instance.get("EngineVersion", ""),
                                "DBInstanceClass": instance.get("DBInstanceClass", ""),
                                "DBInstanceStatus": instance.get("DBInstanceStatus", ""),
                                "CreateTime": instance.get("CreateTime", ""),
                                "ExpireTime": instance.get("ExpireTime", ""),
                                "Region": region_id,
                            }
                        )

                    total_count = data.get("TotalCount", 0)
                    if len(all_instances) >= total_count or len(instances) < 100:
                        break

                    page_number += 1
                else:
                    break

            return all_instances
        except Exception as e:
            # ClickHouse可能在某些区域不可用，静默失败
            return []

    def get_metrics(self, region: str, instance_id: str, days: int = 14):
        """获取ClickHouse实例的监控数据 (BaseResourceAnalyzer接口)"""
        return self.get_clickhouse_metrics(region, instance_id)

    def get_clickhouse_metrics(self, region_id, instance_id):
        """获取ClickHouse实例的监控数据"""
        client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
        end_time = int(round(time.time() * 1000))
        start_time = end_time - 14 * 24 * 60 * 60 * 1000  # 14天前

        # ClickHouse监控指标（使用CMS云监控）
        metrics = {
            "CpuUsage": "CPU利用率",
            "MemoryUsage": "内存利用率",
            "DiskUsage": "磁盘利用率",
            "ConnectionCount": "连接数",
            "QueryCount": "查询数",
            "InsertCount": "插入数",
            "NetworkIn": "网络入流量",
            "NetworkOut": "网络出流量",
            "DiskReadIOPS": "磁盘读IOPS",
            "DiskWriteIOPS": "磁盘写IOPS",
        }

        result = {}

        for metric_name, display_name in metrics.items():
            try:
                request = CommonRequest()
                request.set_domain(f"cms.{region_id}.aliyuncs.com")
                request.set_method("POST")
                request.set_version("2019-01-01")
                request.set_action_name("DescribeMetricData")
                request.add_query_param("RegionId", region_id)
                request.add_query_param("Namespace", "acs_clickhouse_dashboard")
                request.add_query_param("MetricName", metric_name)
                request.add_query_param("StartTime", start_time)
                request.add_query_param("EndTime", end_time)
                request.add_query_param("Period", "86400")  # 1天聚合
                request.add_query_param("Dimensions", f'[{{"instanceId":"{instance_id}"}}]')

                response = client.do_action_with_exception(request)
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
                            result[display_name] = total / count
                        else:
                            result[display_name] = 0
                    else:
                        result[display_name] = 0
                else:
                    result[display_name] = 0
            except Exception as e:
                # 某些指标可能不可用，设置为0
                result[display_name] = 0

            time.sleep(0.1)  # 避免API限流

        return result

    def save_clickhouse_data(self, instances_data, monitoring_data):
        """保存ClickHouse数据到数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # 保存实例数据
        for instance in instances_data:
            cursor.execute(
                """
            INSERT OR REPLACE INTO clickhouse_instances 
            (instance_id, instance_name, instance_type, engine_version, 
             instance_class, region, status, creation_time, expire_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    instance["InstanceId"],
                    instance["DBInstanceDescription"],
                    instance["DBInstanceType"],
                    instance["EngineVersion"],
                    instance["DBInstanceClass"],
                    instance["Region"],
                    instance["DBInstanceStatus"],
                    instance["CreateTime"],
                    instance["ExpireTime"],
                ),
            )

        # 保存监控数据
        for instance_id, metrics in monitoring_data.items():
            for metric_name, metric_value in metrics.items():
                cursor.execute(
                    """
                INSERT INTO clickhouse_monitoring_data 
                (instance_id, metric_name, metric_value, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                    (instance_id, metric_name, metric_value, int(time.time())),
                )

        conn.commit()
        conn.close()
        self.logger.info(f"ClickHouse数据保存完成: {len(instances_data)}个实例")

    def is_idle(self, instance, metrics, thresholds=None):
        """判断ClickHouse实例是否闲置 (BaseResourceAnalyzer接口)"""
        is_idle = self.is_clickhouse_idle(metrics)
        conditions = []
        if is_idle:
            conditions = [self.get_idle_reason(metrics)]
        return is_idle, conditions

    def get_optimization_suggestions(self, instance, metrics):
        """获取优化建议 (BaseResourceAnalyzer接口)"""
        return self.get_optimization_suggestion(metrics, instance.get("DBInstanceClass", ""))

    def is_clickhouse_idle(self, metrics):
        """判断ClickHouse实例是否闲置"""
        # ClickHouse闲置判断标准（或关系）
        cpu_util = metrics.get("CPU利用率", 0)
        memory_util = metrics.get("内存利用率", 0)
        disk_util = metrics.get("磁盘利用率", 0)
        connection_count = metrics.get("连接数", 0)
        query_count = metrics.get("查询数", 0)
        insert_count = metrics.get("插入数", 0)
        network_in = metrics.get("网络入流量", 0)
        network_out = metrics.get("网络出流量", 0)
        disk_read_iops = metrics.get("磁盘读IOPS", 0)
        disk_write_iops = metrics.get("磁盘写IOPS", 0)

        # 闲置条件（满足任一即判定为闲置）
        idle_conditions = [
            cpu_util < 10,  # CPU利用率低于10%
            memory_util < 20,  # 内存利用率低于20%
            disk_util < 20,  # 磁盘利用率低于20%
            connection_count < 10,  # 连接数低于10
            query_count < 100,  # 查询数低于100
            insert_count < 50,  # 插入数低于50
            network_in < 1,  # 网络入流量低于1KB/s
            network_out < 1,  # 网络出流量低于1KB/s
            disk_read_iops < 100,  # 磁盘读IOPS低于100
            disk_write_iops < 100,  # 磁盘写IOPS低于100
        ]

        return any(idle_conditions)

    def get_idle_reason(self, metrics):
        """获取闲置原因"""
        reasons = []

        cpu_util = metrics.get("CPU利用率", 0)
        memory_util = metrics.get("内存利用率", 0)
        disk_util = metrics.get("磁盘利用率", 0)
        connection_count = metrics.get("连接数", 0)
        query_count = metrics.get("查询数", 0)
        insert_count = metrics.get("插入数", 0)
        network_in = metrics.get("网络入流量", 0)
        network_out = metrics.get("网络出流量", 0)
        disk_read_iops = metrics.get("磁盘读IOPS", 0)
        disk_write_iops = metrics.get("磁盘写IOPS", 0)

        if cpu_util < 10:
            reasons.append(f"CPU利用率({cpu_util:.1f}%) < 10%")
        if memory_util < 20:
            reasons.append(f"内存利用率({memory_util:.1f}%) < 20%")
        if disk_util < 20:
            reasons.append(f"磁盘利用率({disk_util:.1f}%) < 20%")
        if connection_count < 10:
            reasons.append(f"连接数({connection_count:.0f}) < 10")
        if query_count < 100:
            reasons.append(f"查询数({query_count:.0f}) < 100")
        if insert_count < 50:
            reasons.append(f"插入数({insert_count:.0f}) < 50")
        if network_in < 1:
            reasons.append(f"网络入流量({network_in:.2f}KB/s) < 1KB/s")
        if network_out < 1:
            reasons.append(f"网络出流量({network_out:.2f}KB/s) < 1KB/s")
        if disk_read_iops < 100:
            reasons.append(f"磁盘读IOPS({disk_read_iops:.0f}) < 100")
        if disk_write_iops < 100:
            reasons.append(f"磁盘写IOPS({disk_write_iops:.0f}) < 100")

        return "; ".join(reasons)

    def get_optimization_suggestion(self, metrics, instance_class):
        """获取优化建议"""
        suggestions = []

        cpu_util = metrics.get("CPU利用率", 0)
        memory_util = metrics.get("内存利用率", 0)
        disk_util = metrics.get("磁盘利用率", 0)
        connection_count = metrics.get("连接数", 0)
        query_count = metrics.get("查询数", 0)
        insert_count = metrics.get("插入数", 0)

        if cpu_util < 10 and memory_util < 20:
            suggestions.append("建议降配实例规格")
        elif cpu_util < 10:
            suggestions.append("建议降配CPU规格")
        elif memory_util < 20:
            suggestions.append("建议降配内存规格")

        if disk_util < 20:
            suggestions.append("建议减少存储容量")

        if connection_count < 10:
            suggestions.append("建议使用更小的实例类型")

        if query_count < 100 and insert_count < 50:
            suggestions.append("建议合并到其他实例或删除")

        return "; ".join(suggestions) if suggestions else "建议保持当前配置"

    def get_monthly_cost(self, instance_id, instance_class, region):
        """获取ClickHouse实例月成本（简化版本，实际需要调用BSS API）"""
        # 这里简化处理，实际应该调用DescribeRenewalPrice API
        # 根据实例类型和区域返回估算成本
        cost_map = {
            "clickhouse.c1.small": 300,
            "clickhouse.c1.medium": 500,
            "clickhouse.c1.large": 800,
            "clickhouse.c1.xlarge": 1200,
            "clickhouse.c2.small": 400,
            "clickhouse.c2.medium": 600,
            "clickhouse.c2.large": 1000,
            "clickhouse.c2.xlarge": 1500,
        }

        return cost_map.get(instance_class, 500)  # 默认500元

    def analyze(self, regions=None, days=14):
        """分析资源 (BaseResourceAnalyzer接口)"""
        # ClickHouseAnalyzer的analyze_clickhouse_resources逻辑比较复杂
        return self.analyze_clickhouse_resources()

    def generate_report(self, idle_instances):
        """生成报告 (BaseResourceAnalyzer接口)"""
        self.generate_clickhouse_report(idle_instances, self.tenant_name)

    def analyze_clickhouse_resources(self):
        """分析ClickHouse资源"""
        self.logger.info("开始ClickHouse资源分析...")

        # 初始化数据库
        self.init_database()

        # 获取所有区域
        regions = self.get_all_regions()
        self.logger.info(f"获取到 {len(regions)} 个区域")

        # 并发获取所有区域的实例
        self.logger.info("🔍 并发获取所有区域的ClickHouse实例...")

        def get_region_instances(region_item):
            """获取单个区域的实例（用于并发）"""
            region = region_item
            try:
                instances = self.get_clickhouse_instances(region)
                return {"region": region, "instances": instances}
            except Exception as e:
                return {"region": region, "instances": []}

        # 并发获取所有区域的实例
        region_results = process_concurrently(
            regions, get_region_instances, max_workers=10, description="获取ClickHouse实例"
        )

        # 整理所有实例
        all_instances = []
        for result in region_results:
            if result and result.get("instances"):
                all_instances.extend(result["instances"])
                self.logger.info(f"{result['region']}: {len(result['instances'])} 个实例")

        if not all_instances:
            self.logger.warning("未发现任何ClickHouse实例")
            return []

        self.logger.info(f"总共获取到 {len(all_instances)} 个ClickHouse实例")

        # 定义单个实例处理函数（用于并发）
        def process_single_instance(instance_item):
            """处理单个实例（用于并发）"""
            instance = instance_item
            instance_id = instance["InstanceId"]
            region = instance["Region"]

            try:
                metrics = self.get_clickhouse_metrics(region, instance_id)
                return {"success": True, "instance_id": instance_id, "metrics": metrics}
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "ClickHouse", region, instance_id)
                ErrorHandler.handle_instance_error(
                    e, instance_id, region, "ClickHouse", continue_on_error=True
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
            all_instances,
            process_single_instance,
            max_workers=10,
            description="ClickHouse监控数据采集",
            progress_callback=progress_callback,
        )

        # 换行

        # 整理监控数据
        all_monitoring_data = {}
        success_count = 0
        fail_count = 0

        for result in monitoring_results:
            if result and result.get("success"):
                all_monitoring_data[result["instance_id"]] = result["metrics"]
                success_count += 1
            else:
                if result:
                    instance_id = result.get("instance_id", "unknown")
                    all_monitoring_data[instance_id] = {}
                    fail_count += 1

        self.logger.info(f"监控数据获取完成: 成功 {success_count} 个, 失败 {fail_count} 个")

        # 保存数据
        self.save_clickhouse_data(all_instances, all_monitoring_data)

        # 分析闲置实例
        idle_instances = []
        for instance in all_instances:
            instance_id = instance["InstanceId"]
            metrics = all_monitoring_data.get(instance_id, {})

            if self.is_clickhouse_idle(metrics):
                idle_reason = self.get_idle_reason(metrics)
                optimization = self.get_optimization_suggestion(
                    metrics, instance.get("DBInstanceClass", "")
                )
                monthly_cost = self.get_monthly_cost(
                    instance_id, instance.get("DBInstanceClass", ""), instance["Region"]
                )

                idle_instances.append(
                    {
                        "实例ID": instance_id,
                        "实例名称": instance["DBInstanceDescription"],
                        "实例类型": instance.get("DBInstanceClass", ""),
                        "版本": instance.get("EngineVersion", ""),
                        "区域": instance["Region"],
                        "状态": instance["DBInstanceStatus"],
                        "CPU利用率(%)": metrics.get("CPU利用率", 0),
                        "内存利用率(%)": metrics.get("内存利用率", 0),
                        "磁盘利用率(%)": metrics.get("磁盘利用率", 0),
                        "连接数": metrics.get("连接数", 0),
                        "查询数": metrics.get("查询数", 0),
                        "插入数": metrics.get("插入数", 0),
                        "网络入流量(KB/s)": metrics.get("网络入流量", 0),
                        "网络出流量(KB/s)": metrics.get("网络出流量", 0),
                        "磁盘读IOPS": metrics.get("磁盘读IOPS", 0),
                        "磁盘写IOPS": metrics.get("磁盘写IOPS", 0),
                        "闲置原因": idle_reason,
                        "优化建议": optimization,
                        "月成本(¥)": monthly_cost,
                    }
                )

        self.logger.info(f"ClickHouse分析完成: 发现 {len(idle_instances)} 个闲置实例")
        return idle_instances

    def generate_clickhouse_report(self, idle_instances, tenant_name=None, output_base_dir="."):
        """生成ClickHouse报告"""
        if not idle_instances:
            self.logger.warning("没有发现闲置的ClickHouse实例")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tenant_prefix = f"{tenant_name}_" if tenant_name else ""

        # 生成Excel报告
        df = pd.DataFrame(idle_instances)
        excel_file = f"{output_base_dir}/{tenant_prefix}clickhouse_idle_report_{timestamp}.xlsx"
        df.to_excel(excel_file, index=False)
        self.logger.info(f"Excel报告已生成: {excel_file}")

        # 生成HTML报告
        html_file = f"{output_base_dir}/{tenant_prefix}clickhouse_idle_report_{timestamp}.html"
        self.generate_html_report(idle_instances, html_file, tenant_name)
        self.logger.info(f"HTML报告已生成: {html_file}")

        # 统计信息
        total_cost = sum(instance["月成本(¥)"] for instance in idle_instances)
        self.logger.info("ClickHouse闲置实例统计:")
        self.logger.info(f"  总数量: {len(idle_instances)} 个")
        self.logger.info(f"  总月成本: {total_cost:,.2f} 元")
        self.logger.info(f"  预计年节省: {total_cost * 12:,.2f} 元")

    def generate_html_report(self, idle_instances, filename, tenant_name=None):
        """生成HTML报告"""
        tenant_str = f" - {tenant_name}" if tenant_name else ""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ClickHouse闲置实例分析报告{tenant_str}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}
        .summary {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #3498db; color: white; position: sticky; top: 0; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .metric {{ font-weight: bold; color: #e74c3c; }}
        .low-utilization {{ background-color: #fff3cd; }}
        .footer {{ margin-top: 30px; padding: 15px; background: #34495e; color: white; text-align: center; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 ClickHouse闲置实例分析报告{tenant_str}</h1>
        
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
                    <th>版本</th>
                    <th>区域</th>
                    <th>状态</th>
                    <th>CPU利用率(%)</th>
                    <th>内存利用率(%)</th>
                    <th>磁盘利用率(%)</th>
                    <th>连接数</th>
                    <th>查询数</th>
                    <th>插入数</th>
                    <th>网络入流量(KB/s)</th>
                    <th>网络出流量(KB/s)</th>
                    <th>磁盘读IOPS</th>
                    <th>磁盘写IOPS</th>
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
                    <td>{instance['版本']}</td>
                    <td>{instance['区域']}</td>
                    <td>{instance['状态']}</td>
                    <td><span class="metric">{instance['CPU利用率(%)']:.1f}%</span></td>
                    <td><span class="metric">{instance['内存利用率(%)']:.1f}%</span></td>
                    <td><span class="metric">{instance['磁盘利用率(%)']:.1f}%</span></td>
                    <td>{instance['连接数']:.0f}</td>
                    <td>{instance['查询数']:.0f}</td>
                    <td>{instance['插入数']:.0f}</td>
                    <td>{instance['网络入流量(KB/s)']:.2f}</td>
                    <td>{instance['网络出流量(KB/s)']:.2f}</td>
                    <td>{instance['磁盘读IOPS']:.0f}</td>
                    <td>{instance['磁盘写IOPS']:.0f}</td>
                    <td>{instance['闲置原因']}</td>
                    <td>{instance['优化建议']}</td>
                    <td>{instance['月成本(¥)']:.2f}</td>
                </tr>
"""

        html_content += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>报告由阿里云资源分析工具自动生成</p>
        </div>
    </div>
</body>
</html>
"""

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)


def main():
    """主函数"""
    import sys

    if len(sys.argv) < 3:
        self.logger.info("用法: python clickhouse_analyzer.py <access_key_id> <access_key_secret>")
        sys.exit(1)

    access_key_id = sys.argv[1]
    access_key_secret = sys.argv[2]

    analyzer = ClickHouseAnalyzer(access_key_id, access_key_secret)
    idle_instances = analyzer.analyze_clickhouse_resources()
    analyzer.generate_clickhouse_report(idle_instances)


if __name__ == "__main__":
    main()
