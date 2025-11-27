#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDS资源分析模块
分析RDS实例的闲置情况，提供优化建议
"""

import json
import sqlite3
import sys
import time
from datetime import datetime

import pandas as pd
from aliyunsdkcms.request.v20190101 import DescribeMetricDataRequest
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkrds.request.v20140815 import DescribeDBInstancesRequest

from core.analyzer_registry import AnalyzerRegistry
from core.base_analyzer import BaseResourceAnalyzer
from core.db_manager import DatabaseManager
from core.report_generator import ReportGenerator
from utils.concurrent_helper import process_concurrently
from utils.error_handler import ErrorHandler
from utils.logger import get_logger


@AnalyzerRegistry.register("rds", "RDS数据库", "🗄️")
class RDSAnalyzer(BaseResourceAnalyzer):
    """RDS资源分析器"""

    def __init__(self, access_key_id, access_key_secret, tenant_name=None):
        super().__init__(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            tenant_name=tenant_name or "default",
        )
        self.db_name = "rds_monitoring_data.db"
        self.logger = get_logger("rds_analyzer")
        # 使用统一数据库管理器
        self.db_manager = DatabaseManager(self.db_name)

    def get_resource_type(self) -> str:
        return "rds"

    def init_database(self):
        """初始化RDS数据库（使用统一DatabaseManager）"""
        # 定义额外列
        extra_columns = {"engine": "TEXT", "engine_version": "TEXT", "instance_class": "TEXT"}

        self.db_manager.create_resource_table("rds", extra_columns)
        self.db_manager.create_monitoring_table("rds")
        self.logger.info("RDS数据库初始化完成")

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
        """获取指定区域的RDS实例 (BaseResourceAnalyzer接口)"""
        return self.get_rds_instances(region)

    def get_rds_instances(self, region_id):
        """获取指定区域的RDS实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeDBInstancesRequest.DescribeDBInstancesRequest()
            request.set_PageSize(100)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            instances = []
            if "Items" in data and "DBInstance" in data["Items"]:
                for instance in data["Items"]["DBInstance"]:
                    instances.append(
                        {
                            "InstanceId": instance["DBInstanceId"],
                            "DBInstanceDescription": instance.get("DBInstanceDescription", ""),
                            "DBInstanceType": instance.get("DBInstanceType", ""),
                            "Engine": instance.get("Engine", ""),
                            "EngineVersion": instance.get("EngineVersion", ""),
                            "DBInstanceClass": instance.get("DBInstanceClass", ""),
                            "DBInstanceStatus": instance.get("DBInstanceStatus", ""),
                            "CreateTime": instance.get("CreateTime", ""),
                            "ExpireTime": instance.get("ExpireTime", ""),
                            "Region": region_id,
                        }
                    )

            return instances
        except Exception as e:
            error = ErrorHandler.handle_api_error(e, "RDS", region_id)
            ErrorHandler.handle_region_error(e, region_id, "RDS")
            return []

    def get_metrics(self, region: str, instance_id: str, days: int = 14):
        """获取RDS实例的监控数据 (BaseResourceAnalyzer接口)"""
        return self.get_rds_metrics(region, instance_id)

    def get_rds_metrics(self, region_id, instance_id):
        """获取RDS实例的监控数据"""
        client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
        end_time = int(round(time.time() * 1000))
        start_time = end_time - 14 * 24 * 60 * 60 * 1000  # 14天前

        # RDS监控指标（使用正确的指标名称）
        metrics = {
            "CpuUsage": "CPU利用率",
            "MemoryUsage": "内存利用率",
            "ConnectionUsage": "连接数使用率",
            "MySQL_QPS": "每秒查询数",
            "MySQL_TPS": "每秒事务数",
            "MySQL_ComSelect": "SELECT查询数",
            "MySQL_ComInsert": "INSERT操作数",
            "MySQL_ComUpdate": "UPDATE操作数",
            "MySQL_ComDelete": "DELETE操作数",
            "MySQL_ThreadsConnected": "连接线程数",
            "MySQL_ThreadsRunning": "运行线程数",
            "MySQL_SlowQueries": "慢查询数",
            "MySQL_OpenFiles": "打开文件数",
            "MySQL_OpenTables": "打开表数",
            "MySQL_SelectScan": "扫描查询数",
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
                request.add_query_param("Namespace", "acs_rds_dashboard")
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
                result[display_name] = 0

            time.sleep(0.1)  # 避免API限流

        return result

    def save_rds_data(self, instances_data, monitoring_data):
        """保存RDS数据到数据库（使用统一DatabaseManager）"""
        # 转换实例数据格式
        for instance in instances_data:
            instance_dict = {
                "InstanceId": instance["InstanceId"],
                "InstanceName": instance.get("DBInstanceDescription", ""),
                "InstanceType": instance.get("DBInstanceType", ""),
                "Region": instance.get("Region", ""),
                "Status": instance.get("DBInstanceStatus", ""),
                "CreationTime": instance.get("CreateTime", ""),
                "ExpireTime": instance.get("ExpireTime", ""),
                "engine": instance.get("Engine", ""),
                "engine_version": instance.get("EngineVersion", ""),
                "instance_class": instance.get("DBInstanceClass", ""),
            }
            self.db_manager.save_instance("rds", instance_dict)

        # 保存监控数据
        for instance_id, metrics in monitoring_data.items():
            self.db_manager.save_metrics_batch("rds", instance_id, metrics)

        self.logger.info(f"RDS数据保存完成: {len(instances_data)}个实例")

    def is_idle(self, instance, metrics, thresholds=None):
        """判断RDS实例是否闲置 (BaseResourceAnalyzer接口)"""
        is_idle = self.is_rds_idle(metrics)
        conditions = []
        if is_idle:
            conditions = [self.get_idle_reason(metrics)]
        return is_idle, conditions

    def get_optimization_suggestions(self, instance, metrics):
        """获取优化建议 (BaseResourceAnalyzer接口)"""
        return self.get_optimization_suggestion(metrics, instance.get("DBInstanceClass", ""))

    def is_rds_idle(self, metrics):
        """判断RDS实例是否闲置"""
        # RDS闲置判断标准（或关系）
        cpu_util = metrics.get("CPU利用率", 0)
        memory_util = metrics.get("内存利用率", 0)
        connection_usage = metrics.get("连接数使用率", 0)
        qps = metrics.get("每秒查询数", 0)
        tps = metrics.get("每秒事务数", 0)
        threads_connected = metrics.get("连接线程数", 0)
        threads_running = metrics.get("运行线程数", 0)

        # 闲置条件（满足任一即判定为闲置）
        idle_conditions = [
            cpu_util < 10,  # CPU利用率低于10%
            memory_util < 20,  # 内存利用率低于20%
            connection_usage < 20,  # 连接数使用率低于20%
            qps < 100,  # QPS低于100
            tps < 10,  # TPS低于10
            threads_connected < 10,  # 连接线程数低于10
            threads_running < 5,  # 运行线程数低于5
        ]

        return any(idle_conditions)

    def get_idle_reason(self, metrics):
        """获取闲置原因"""
        reasons = []

        cpu_util = metrics.get("CPU利用率", 0)
        memory_util = metrics.get("内存利用率", 0)
        connection_usage = metrics.get("连接数使用率", 0)
        qps = metrics.get("每秒查询数", 0)
        tps = metrics.get("每秒事务数", 0)
        threads_connected = metrics.get("连接线程数", 0)
        threads_running = metrics.get("运行线程数", 0)

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

        cpu_util = metrics.get("CPU利用率", 0)
        memory_util = metrics.get("内存利用率", 0)
        connection_usage = metrics.get("连接数使用率", 0)
        qps = metrics.get("每秒查询数", 0)
        tps = metrics.get("每秒事务数", 0)

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
            "rds.mysql.s1.small": 200,
            "rds.mysql.s2.small": 300,
            "rds.mysql.s1.medium": 400,
            "rds.mysql.s2.medium": 600,
            "rds.mysql.s1.large": 800,
            "rds.mysql.s2.large": 1200,
            "rds.mysql.s1.xlarge": 1600,
            "rds.mysql.s2.xlarge": 2400,
        }

        return cost_map.get(instance_class, 500)  # 默认500元

    def analyze(self, regions=None, days=14):
        """分析资源 (BaseResourceAnalyzer接口)"""
        # 复用现有的analyze_rds_resources逻辑，但需要适配返回格式
        # 这里简单起见，直接调用analyze_rds_resources，它返回的是idle_instances列表
        # 但BaseResourceAnalyzer.analyze通常返回包含metrics等的详细字典列表
        # 由于RDSAnalyzer的analyze_rds_resources已经做了很多工作，我们这里暂时保留它的逻辑
        # 并让analyze返回它返回的结果（虽然类型可能不太匹配BaseResourceAnalyzer的签名，但在动态语言中是可以的）
        return self.analyze_rds_resources()

    def generate_report(self, idle_instances):
        """生成报告 (BaseResourceAnalyzer接口)"""
        self.generate_rds_report(idle_instances)

    def analyze_rds_resources(self):
        """分析RDS资源"""
        self.logger.info("开始RDS资源分析...")

        # 初始化数据库
        self.init_database()

        # 获取所有区域
        regions = self.get_all_regions()
        self.logger.info(f"获取到 {len(regions)} 个区域")

        # 并发获取所有区域的实例
        self.logger.info("并发获取所有区域的RDS实例...")

        def get_region_instances(region_item):
            """获取单个区域的实例（用于并发）"""
            region = region_item
            try:
                instances = self.get_rds_instances(region)
                return {"region": region, "instances": instances}
            except Exception as e:
                self.logger.warning(f"区域 {region} 获取实例失败: {e}")
                return {"region": region, "instances": []}

        # 并发获取所有区域的实例
        region_results = process_concurrently(
            regions, get_region_instances, max_workers=10, description="获取RDS实例"
        )

        # 整理所有实例
        all_instances = []
        for result in region_results:
            if result and result.get("instances"):
                all_instances.extend(result["instances"])
                self.logger.info(f"{result['region']}: {len(result['instances'])} 个实例")

        if not all_instances:
            self.logger.warning("未发现任何RDS实例")
            return []

        self.logger.info(f"总共获取到 {len(all_instances)} 个RDS实例")

        # 定义单个实例处理函数（用于并发）
        def process_single_instance(instance_item):
            """处理单个实例（用于并发）"""
            instance = instance_item
            instance_id = instance["InstanceId"]
            region = instance["Region"]

            try:
                metrics = self.get_rds_metrics(region, instance_id)
                return {"success": True, "instance_id": instance_id, "metrics": metrics}
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "RDS", region, instance_id)
                ErrorHandler.handle_instance_error(
                    e, instance_id, region, "RDS", continue_on_error=True
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
            description="RDS监控数据采集",
            progress_callback=progress_callback,
        )

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
        self.save_rds_data(all_instances, all_monitoring_data)

        # 分析闲置实例
        idle_instances = []
        for instance in all_instances:
            instance_id = instance["InstanceId"]
            metrics = all_monitoring_data.get(instance_id, {})

            if self.is_rds_idle(metrics):
                idle_reason = self.get_idle_reason(metrics)
                optimization = self.get_optimization_suggestion(
                    metrics, instance["DBInstanceClass"]
                )
                monthly_cost = self.get_monthly_cost(
                    instance_id, instance["DBInstanceClass"], instance["Region"]
                )

                idle_instances.append(
                    {
                        "实例ID": instance_id,
                        "实例名称": instance["DBInstanceDescription"],
                        "实例类型": instance["DBInstanceClass"],
                        "引擎": instance["Engine"],
                        "版本": instance["EngineVersion"],
                        "区域": instance["Region"],
                        "状态": instance["DBInstanceStatus"],
                        "CPU利用率(%)": metrics.get("CPU利用率", 0),
                        "内存利用率(%)": metrics.get("内存利用率", 0),
                        "连接数使用率(%)": metrics.get("连接数使用率", 0),
                        "QPS": metrics.get("每秒查询数", 0),
                        "TPS": metrics.get("每秒事务数", 0),
                        "连接线程数": metrics.get("连接线程数", 0),
                        "运行线程数": metrics.get("运行线程数", 0),
                        "慢查询数": metrics.get("慢查询数", 0),
                        "打开文件数": metrics.get("打开文件数", 0),
                        "打开表数": metrics.get("打开表数", 0),
                        "SELECT查询数": metrics.get("SELECT查询数", 0),
                        "INSERT操作数": metrics.get("INSERT操作数", 0),
                        "UPDATE操作数": metrics.get("UPDATE操作数", 0),
                        "DELETE操作数": metrics.get("DELETE操作数", 0),
                        "闲置原因": idle_reason,
                        "优化建议": optimization,
                        "月成本(¥)": monthly_cost,
                    }
                )

        self.logger.info(f"RDS分析完成: 发现 {len(idle_instances)} 个闲置实例")
        return idle_instances

    def generate_rds_report(self, idle_instances):
        """生成RDS报告（使用统一ReportGenerator）"""
        if not idle_instances:
            self.logger.info("没有发现闲置的RDS实例")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 使用统一报告生成器
        reports = ReportGenerator.generate_combined_report(
            resource_type="RDS",
            idle_instances=idle_instances,
            output_dir=".",
            tenant_name=self.tenant_name,
            timestamp=timestamp,
        )

        self.logger.info(f"Excel报告已生成: {reports['excel']}")
        self.logger.info(f"HTML报告已生成: {reports['html']}")

        # 统计信息
        total_cost = sum(instance.get("月成本(¥)", 0) for instance in idle_instances)
        self.logger.info(
            f"RDS闲置实例统计: 总数量={len(idle_instances)}个, 总月成本={total_cost:,.2f}元, 预计年节省={total_cost * 12:,.2f}元"
        )

    # generate_html_report方法已移除，改用ReportGenerator.generate_combined_report


def main():
    """RDS分析主函数"""
    # 读取配置文件
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        access_key_id = config["access_key_id"]
        access_key_secret = config["access_key_secret"]
    except FileNotFoundError:
        import logging

        logging.error("配置文件 config.json 不存在")
        return

    # 创建RDS分析器
    analyzer = RDSAnalyzer(access_key_id, access_key_secret)

    # 分析RDS资源
    idle_instances = analyzer.analyze_rds_resources()

    # 生成报告
    analyzer.generate_rds_report(idle_instances)


if __name__ == "__main__":
    main()
