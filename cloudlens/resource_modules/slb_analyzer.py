#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLB（负载均衡）资源分析模块
分析SLB实例的闲置情况，提供优化建议
"""

import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkslb.request.v20140515 import (
    DescribeLoadBalancerAttributeRequest,
    DescribeLoadBalancersRequest,
)

from cloudlens.core.analyzer_registry import AnalyzerRegistry
from cloudlens.core.base_analyzer import BaseResourceAnalyzer
from cloudlens.core.report_generator import ReportGenerator
from cloudlens.utils.concurrent_helper import process_concurrently
from cloudlens.utils.error_handler import ErrorHandler
from cloudlens.utils.logger import get_logger


@AnalyzerRegistry.register("slb", "SLB负载均衡", "⚖️")
class SLBAnalyzer(BaseResourceAnalyzer):
    """SLB资源分析器"""

    def __init__(self, access_key_id, access_key_secret, tenant_name=None):
        super().__init__(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            tenant_name=tenant_name or "default",
        )
        self.db_name = "slb_monitoring_data.db"
        self.logger = get_logger("slb_analyzer")
        self.init_database()

    def get_resource_type(self) -> str:
        return "slb"

    def init_database(self):
        """初始化SLB数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # 创建SLB实例表
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS slb_instances (
            instance_id TEXT PRIMARY KEY,
            instance_name TEXT,
            instance_type TEXT,
            address_type TEXT,
            region TEXT,
            status TEXT,
            bandwidth INTEGER,
            creation_time TEXT,
            monthly_cost REAL DEFAULT 0
        )
        """
        )

        # 创建SLB监控数据表
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS slb_monitoring_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id TEXT,
            metric_name TEXT,
            metric_value REAL,
            timestamp INTEGER,
            FOREIGN KEY (instance_id) REFERENCES slb_instances (instance_id)
        )
        """
        )

        conn.commit()
        conn.close()
        self.logger.info("SLB数据库初始化完成")

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
        """获取指定区域的SLB实例 (BaseResourceAnalyzer接口)"""
        return self.get_slb_instances(region)

    def get_slb_instances(self, region_id):
        """获取指定区域的所有SLB实例（包括CLB、NLB、ALB）"""
        all_instances = []

        # 1. 获取CLB（传统型负载均衡）实例
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeLoadBalancersRequest.DescribeLoadBalancersRequest()
            request.set_PageSize(100)

            page_number = 1
            while True:
                request.set_PageNumber(page_number)
                try:
                    response = client.do_action_with_exception(request)
                    data = json.loads(response)

                    if "LoadBalancers" in data and "LoadBalancer" in data["LoadBalancers"]:
                        instances = data["LoadBalancers"]["LoadBalancer"]
                        if not isinstance(instances, list):
                            instances = [instances]

                        if len(instances) == 0:
                            break

                        for instance in instances:
                            instance_id = instance.get("LoadBalancerId", "")
                            if not instance_id:
                                continue

                            detail = self.get_slb_detail(region_id, instance_id, "clb")

                            all_instances.append(
                                {
                                    "InstanceId": instance_id,
                                    "InstanceName": instance.get("LoadBalancerName", ""),
                                    "LoadBalancerType": "clb",
                                    "LoadBalancerTypeName": "CLB",
                                    "LoadBalancerTypeDesc": "传统型负载均衡",
                                    "InstanceType": instance.get("LoadBalancerSpec", ""),
                                    "AddressType": instance.get("AddressType", ""),
                                    "InstanceStatus": instance.get("LoadBalancerStatus", ""),
                                    "Region": region_id,
                                    "Bandwidth": detail.get("Bandwidth", 0),
                                    "BackendServerCount": detail.get("BackendServerCount", 0),
                                    "ListenerCount": detail.get("ListenerCount", 0),
                                    "CreateTime": instance.get("CreateTime", ""),
                                }
                            )

                        total_count = data.get("TotalCount", 0)
                        if len(all_instances) >= total_count or len(instances) < 100:
                            break

                        page_number += 1
                    else:
                        break
                except Exception as e:
                    self.logger.info(f"获取CLB实例失败 {region_id}: {str(e)}")
                    break
        except Exception as e:
            self.logger.info(f"获取CLB实例失败 {region_id}: {str(e)}")

        # 2. 获取ALB（应用型负载均衡）实例
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = CommonRequest()
            request.set_domain(f"alb.{region_id}.aliyuncs.com")
            request.set_version("2020-06-16")
            request.set_method("POST")
            request.set_action_name("ListLoadBalancers")
            request.add_query_param("PageSize", 100)
            request.add_query_param("PageNumber", 1)

            page_number = 1
            while True:
                request.add_query_param("PageNumber", page_number)
                try:
                    response = client.do_action_with_exception(request)
                    data = json.loads(response)

                    if "LoadBalancers" in data:
                        instances = data["LoadBalancers"]
                        if not isinstance(instances, list):
                            instances = [instances] if instances else []

                        if len(instances) == 0:
                            break

                        for instance in instances:
                            instance_id = instance.get("LoadBalancerId", "") or instance.get(
                                "Id", ""
                            )
                            if not instance_id:
                                continue

                            detail = self.get_slb_detail(region_id, instance_id, "alb")

                            all_instances.append(
                                {
                                    "InstanceId": instance_id,
                                    "InstanceName": instance.get("LoadBalancerName", "")
                                    or instance.get("Name", ""),
                                    "LoadBalancerType": "alb",
                                    "LoadBalancerTypeName": "ALB",
                                    "LoadBalancerTypeDesc": "应用型负载均衡",
                                    "InstanceType": instance.get("LoadBalancerSpec", "")
                                    or instance.get("SpecType", ""),
                                    "AddressType": instance.get("AddressType", "")
                                    or instance.get("AddressAllocatedMode", ""),
                                    "InstanceStatus": instance.get("LoadBalancerStatus", "")
                                    or instance.get("Status", ""),
                                    "Region": region_id,
                                    "Bandwidth": detail.get("Bandwidth", 0),
                                    "BackendServerCount": detail.get("BackendServerCount", 0),
                                    "ListenerCount": detail.get("ListenerCount", 0),
                                    "CreateTime": instance.get("CreateTime", "")
                                    or instance.get("CreateTime", ""),
                                }
                            )

                        total_count = data.get("TotalCount", 0)
                        if len(instances) < 100:
                            break

                        page_number += 1
                    else:
                        break
                except Exception as e:
                    self.logger.info(f"获取ALB实例失败 {region_id}: {str(e)}")
                    break
        except Exception as e:
            self.logger.info(f"获取ALB实例失败 {region_id}: {str(e)}")

        # 3. 获取NLB（网络型负载均衡）实例
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = CommonRequest()
            request.set_domain(f"nlb.{region_id}.aliyuncs.com")
            request.set_version("2022-04-30")
            request.set_method("POST")
            request.set_action_name("ListLoadBalancers")
            request.add_query_param("PageSize", 100)
            request.add_query_param("PageNumber", 1)

            page_number = 1
            while True:
                request.add_query_param("PageNumber", page_number)
                try:
                    response = client.do_action_with_exception(request)
                    data = json.loads(response)

                    if "LoadBalancers" in data:
                        instances = data["LoadBalancers"]
                        if not isinstance(instances, list):
                            instances = [instances] if instances else []

                        if len(instances) == 0:
                            break

                        for instance in instances:
                            instance_id = instance.get("LoadBalancerId", "") or instance.get(
                                "Id", ""
                            )
                            if not instance_id:
                                continue

                            detail = self.get_slb_detail(region_id, instance_id, "nlb")

                            all_instances.append(
                                {
                                    "InstanceId": instance_id,
                                    "InstanceName": instance.get("LoadBalancerName", "")
                                    or instance.get("Name", ""),
                                    "LoadBalancerType": "nlb",
                                    "LoadBalancerTypeName": "NLB",
                                    "LoadBalancerTypeDesc": "网络型负载均衡",
                                    "InstanceType": instance.get("LoadBalancerSpec", "")
                                    or instance.get("SpecType", ""),
                                    "AddressType": instance.get("AddressType", "")
                                    or instance.get("AddressAllocatedMode", ""),
                                    "InstanceStatus": instance.get("LoadBalancerStatus", "")
                                    or instance.get("Status", ""),
                                    "Region": region_id,
                                    "Bandwidth": detail.get("Bandwidth", 0),
                                    "BackendServerCount": detail.get("BackendServerCount", 0),
                                    "ListenerCount": detail.get("ListenerCount", 0),
                                    "CreateTime": instance.get("CreateTime", "")
                                    or instance.get("CreateTime", ""),
                                }
                            )

                        total_count = data.get("TotalCount", 0)
                        if len(instances) < 100:
                            break

                        page_number += 1
                    else:
                        break
                except Exception as e:
                    self.logger.info(f"获取NLB实例失败 {region_id}: {str(e)}")
                    break
        except Exception as e:
            self.logger.info(f"获取NLB实例失败 {region_id}: {str(e)}")

        return all_instances

    def get_slb_detail(self, region_id, instance_id, lb_type="clb"):
        """获取SLB实例详细信息"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)

            # 根据负载均衡类型使用不同的API
            if lb_type == "clb":
                # CLB使用传统SLB API
                request = (
                    DescribeLoadBalancerAttributeRequest.DescribeLoadBalancerAttributeRequest()
                )
                request.set_LoadBalancerId(instance_id)
                response = client.do_action_with_exception(request)
                data = json.loads(response)

                backend_servers = data.get("BackendServers", {})
                backend_server_list = backend_servers.get("BackendServer", [])
                if not isinstance(backend_server_list, list):
                    backend_server_list = [backend_server_list] if backend_server_list else []

                listener_ports = data.get("ListenerPortsAndProtocols", {})
                listener_list = listener_ports.get("ListenerPortAndProtocol", [])
                if not isinstance(listener_list, list):
                    listener_list = [listener_list] if listener_list else []

                return {
                    "Bandwidth": data.get("Bandwidth", 0),
                    "BackendServerCount": len(backend_server_list),
                    "ListenerCount": len(listener_list),
                    "BackendServers": backend_servers,
                    "ListenerPortsAndProtocols": listener_ports,
                }
            elif lb_type == "nlb":
                # NLB需要分别获取后端服务器组和监听器
                backend_count = 0
                listener_count = 0

                # 1. 获取后端服务器组
                try:
                    request = CommonRequest()
                    request.set_domain(f"nlb.{region_id}.aliyuncs.com")
                    request.set_version("2022-04-30")
                    request.set_method("POST")
                    request.set_action_name("ListServerGroups")
                    request.add_query_param("LoadBalancerId", instance_id)
                    request.add_query_param("PageSize", 50)

                    response = client.do_action_with_exception(request)
                    data = json.loads(response)

                    if "ServerGroups" in data:
                        groups = data["ServerGroups"]
                        if not isinstance(groups, list):
                            groups = [groups] if groups else []

                        # 统计属于当前实例的服务器组的ServerCount
                        for group in groups:
                            related_lb_ids = group.get("RelatedLoadBalancerIds", [])
                            if not isinstance(related_lb_ids, list):
                                related_lb_ids = [related_lb_ids] if related_lb_ids else []

                            if instance_id in related_lb_ids:
                                server_count = group.get("ServerCount", 0)
                                if isinstance(server_count, (int, float)):
                                    backend_count += int(server_count)
                except Exception as e:
                    self.logger.info(f"获取NLB后端服务器组失败 {instance_id}: {e}")

                # 2. 获取监听器
                try:
                    request = CommonRequest()
                    request.set_domain(f"nlb.{region_id}.aliyuncs.com")
                    request.set_version("2022-04-30")
                    request.set_method("POST")
                    request.set_action_name("ListListeners")
                    request.add_query_param("LoadBalancerId", instance_id)
                    request.add_query_param("PageSize", 50)

                    response = client.do_action_with_exception(request)
                    data = json.loads(response)

                    if "Listeners" in data:
                        listeners = data["Listeners"]
                        if not isinstance(listeners, list):
                            listeners = [listeners] if listeners else []

                        listener_count = len(listeners)
                except Exception as e:
                    self.logger.info(f"获取NLB监听器失败 {instance_id}: {e}")

                # 3. 获取带宽信息
                bandwidth = 0
                try:
                    request = CommonRequest()
                    request.set_domain(f"nlb.{region_id}.aliyuncs.com")
                    request.set_version("2022-04-30")
                    request.set_method("POST")
                    request.set_action_name("GetLoadBalancerAttribute")
                    request.add_query_param("LoadBalancerId", instance_id)

                    response = client.do_action_with_exception(request)
                    data = json.loads(response)

                    # NLB的带宽可能在LoadBalancerBillingConfig中
                    billing_config = data.get("LoadBalancerBillingConfig", {})
                    bandwidth = billing_config.get("InternetBandwidth", 0)
                except Exception as e:
                    self.logger.info(f"获取NLB带宽信息失败 {instance_id}: {e}")

                return {
                    "Bandwidth": bandwidth,
                    "BackendServerCount": backend_count,
                    "ListenerCount": listener_count,
                    "BackendServers": {},
                    "ListenerPortsAndProtocols": {},
                }
            elif lb_type == "alb":
                # ALB类似处理
                backend_count = 0
                listener_count = 0
                bandwidth = 0

                # 获取服务器组和监听器（类似NLB的逻辑）
                try:
                    # ALB获取服务器组
                    request = CommonRequest()
                    request.set_domain(f"alb.{region_id}.aliyuncs.com")
                    request.set_version("2020-06-16")
                    request.set_method("POST")
                    request.set_action_name("ListServerGroups")
                    request.add_query_param("LoadBalancerId", instance_id)
                    request.add_query_param("PageSize", 50)

                    response = client.do_action_with_exception(request)
                    data = json.loads(response)

                    if "ServerGroups" in data:
                        groups = data["ServerGroups"]
                        if not isinstance(groups, list):
                            groups = [groups] if groups else []

                        for group in groups:
                            related_lb_ids = group.get("RelatedLoadBalancerIds", []) or group.get(
                                "LoadBalancerIds", []
                            )
                            if not isinstance(related_lb_ids, list):
                                related_lb_ids = [related_lb_ids] if related_lb_ids else []

                            if instance_id in related_lb_ids or not related_lb_ids:
                                # 如果没有RelatedLoadBalancerIds，需要获取服务器组详情
                                server_count = group.get("ServerCount", 0) or len(
                                    group.get("Servers", [])
                                )
                                if isinstance(server_count, (int, float)):
                                    backend_count += int(server_count)
                except Exception as e:
                    self.logger.info(f"获取ALB后端服务器组失败 {instance_id}: {e}")

                # 获取监听器
                try:
                    request = CommonRequest()
                    request.set_domain(f"alb.{region_id}.aliyuncs.com")
                    request.set_version("2020-06-16")
                    request.set_method("POST")
                    request.set_action_name("ListListeners")
                    request.add_query_param("LoadBalancerId", instance_id)
                    request.add_query_param("PageSize", 50)

                    response = client.do_action_with_exception(request)
                    data = json.loads(response)

                    if "Listeners" in data:
                        listeners = data["Listeners"]
                        if not isinstance(listeners, list):
                            listeners = [listeners] if listeners else []

                        listener_count = len(listeners)
                except Exception as e:
                    self.logger.info(f"获取ALB监听器失败 {instance_id}: {e}")

                return {
                    "Bandwidth": bandwidth,
                    "BackendServerCount": backend_count,
                    "ListenerCount": listener_count,
                    "BackendServers": {},
                    "ListenerPortsAndProtocols": {},
                }
            else:
                # 其他类型，尝试通用方法
                request = CommonRequest()
                request.set_domain(f"slb.{region_id}.aliyuncs.com")
                request.set_version("2014-05-15")
                request.set_method("POST")
                request.set_action_name("GetLoadBalancerAttribute")
                request.add_query_param("LoadBalancerId", instance_id)

                response = client.do_action_with_exception(request)
                data = json.loads(response)

                backend_count = data.get("BackendServerCount", 0) or len(
                    data.get("BackendServers", [])
                )
                listener_count = data.get("ListenerCount", 0) or len(data.get("Listeners", []))

                return {
                    "Bandwidth": data.get("Bandwidth", 0) or data.get("BandwidthMbps", 0),
                    "BackendServerCount": backend_count,
                    "ListenerCount": listener_count,
                    "BackendServers": data.get("BackendServers", {}),
                    "ListenerPortsAndProtocols": data.get("Listeners", {}),
                }

        except Exception as e:
            # 如果获取详细信息失败，返回基本结构
            self.logger.info(f"获取SLB详情失败 {instance_id} ({lb_type}): {str(e)}")
            return {
                "Bandwidth": 0,
                "BackendServerCount": 0,
                "ListenerCount": 0,
                "BackendServers": {},
                "ListenerPortsAndProtocols": {},
            }

    def get_metrics(self, region: str, instance_id: str, days: int = 14):
        """获取SLB实例的监控数据 (BaseResourceAnalyzer接口)"""
        # 这里需要注意，get_slb_metrics需要lb_type参数
        # BaseResourceAnalyzer接口没有这个参数，我们需要想办法获取
        # 可以在get_instances中把lb_type存入instance信息，然后在analyze中传递
        # 或者在这里尝试获取（比较耗时）或者默认clb
        # 由于BaseResourceAnalyzer.analyze会先调用get_instances，我们可以假设instance信息里有
        # 但get_metrics只接收instance_id
        # 这是一个接口设计问题。
        # 暂时我们默认clb，或者在analyze中重写逻辑
        # 实际上，SLBAnalyzer的analyze_slb_instances已经处理了这个问题
        return self.get_slb_metrics(
            region, instance_id, "clb"
        )  # 默认clb，实际在analyze中会被正确调用

    def get_slb_metrics(self, region_id, instance_id, lb_type="clb"):
        """获取SLB实例的监控数据（支持CLB、NLB、ALB）"""
        client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=14)

        # 根据负载均衡类型选择命名空间和指标
        if lb_type == "clb":
            namespace = "acs_slb_dashboard"
            metrics = {
                "ActiveConnection": "活跃连接数",
                "NewConnection": "新建连接数",
                "TrafficRXNew": "入流量",
                "TrafficTXNew": "出流量",
                "Qps": "每秒查询数",
                "Rt": "响应时间",
            }
        elif lb_type == "alb":
            namespace = "acs_alb_dashboard"
            metrics = {
                "ActiveConnection": "活跃连接数",
                "NewConnection": "新建连接数",
                "TrafficRXNew": "入流量",
                "TrafficTXNew": "出流量",
                "Qps": "每秒查询数",
                "Rt": "响应时间",
            }
        elif lb_type == "nlb":
            namespace = "acs_nlb_dashboard"
            metrics = {
                "ActiveConnection": "活跃连接数",
                "NewConnection": "新建连接数",
                "TrafficRXNew": "入流量",
                "TrafficTXNew": "出流量",
                "Qps": "每秒查询数",
                "Rt": "响应时间",
            }
        else:
            namespace = "acs_slb_dashboard"
            metrics = {
                "ActiveConnection": "活跃连接数",
                "NewConnection": "新建连接数",
                "TrafficRXNew": "入流量",
                "TrafficTXNew": "出流量",
                "Qps": "每秒查询数",
                "Rt": "响应时间",
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
                request.add_query_param("Namespace", namespace)
                request.add_query_param("MetricName", metric_name)
                request.add_query_param("StartTime", start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
                request.add_query_param("EndTime", end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
                request.add_query_param("Period", "86400")  # 1天聚合
                request.add_query_param("Dimensions", f'[{{"instanceId":"{instance_id}"}}]')
                request.add_query_param("Statistics", "Average")

                response = client.do_action_with_exception(request)
                data = json.loads(response)

                if "Datapoints" in data and data["Datapoints"]:
                    if isinstance(data["Datapoints"], str):
                        dps = json.loads(data["Datapoints"])
                    else:
                        dps = data["Datapoints"]

                    if dps and len(dps) > 0:
                        # 计算平均值
                        values = [
                            float(dp.get("Average", 0))
                            for dp in dps
                            if dp.get("Average") is not None
                        ]
                        if values:
                            result[display_name] = sum(values) / len(values)
                        else:
                            result[display_name] = 0
                    else:
                        result[display_name] = 0
                else:
                    result[display_name] = 0

            except Exception as e:
                self.logger.info(f"    ⚠️  指标 {metric_name} 获取失败 ({lb_type}): {e}")
                result[display_name] = 0

        # 计算流量总和（MB）
        traffic_in = result.get("入流量", 0)
        traffic_out = result.get("出流量", 0)
        total_traffic_mb = (traffic_in + traffic_out) / (1024 * 1024)  # 转换为MB
        result["总流量(MB)"] = total_traffic_mb

        return result

    def is_idle(self, instance, metrics, thresholds=None):
        """判断SLB实例是否闲置 (BaseResourceAnalyzer接口)"""
        return self.is_slb_idle(instance, metrics, thresholds)

    def get_optimization_suggestions(self, instance, metrics):
        """获取优化建议 (BaseResourceAnalyzer接口)"""
        return self.get_optimization_suggestion(instance, metrics)

    def is_slb_idle(self, instance, metrics, thresholds=None):
        """判断SLB实例是否闲置"""
        if thresholds is None:
            thresholds = {
                "backend_server_count": 0,
                "traffic_mb_per_day": 10,
                "active_connections": 10,
                "new_connections_per_day": 100,
            }

        backend_count = instance.get("BackendServerCount", 0)
        active_conn = metrics.get("活跃连接数", 0)
        new_conn = metrics.get("新建连接数", 0)
        total_traffic = metrics.get("总流量(MB)", 0)

        # 计算14天平均每日流量
        daily_traffic = total_traffic / 14
        daily_new_conn = new_conn / 14

        idle_conditions = []

        # 判断条件（或关系）
        if backend_count <= thresholds["backend_server_count"]:
            idle_conditions.append(
                f"后端服务器数({backend_count}) <= {thresholds['backend_server_count']}"
            )

        if daily_traffic < thresholds["traffic_mb_per_day"]:
            idle_conditions.append(
                f"日均流量({daily_traffic:.2f}MB) < {thresholds['traffic_mb_per_day']}MB"
            )

        if active_conn < thresholds["active_connections"]:
            idle_conditions.append(
                f"活跃连接数({active_conn:.0f}) < {thresholds['active_connections']}"
            )

        if daily_new_conn < thresholds["new_connections_per_day"]:
            idle_conditions.append(
                f"日均新建连接({daily_new_conn:.0f}) < {thresholds['new_connections_per_day']}"
            )

        return len(idle_conditions) > 0, idle_conditions

    def get_optimization_suggestion(self, instance, metrics):
        """获取优化建议"""
        suggestions = []

        backend_count = instance.get("BackendServerCount", 0)
        listener_count = instance.get("ListenerCount", 0)
        active_conn = metrics.get("活跃连接数", 0)
        daily_traffic = metrics.get("总流量(MB)", 0) / 14

        # 无后端服务器
        if backend_count == 0:
            suggestions.append("建议删除未配置后端服务器的SLB实例")

        # 无监听器
        if listener_count == 0:
            suggestions.append("建议删除未配置监听器的SLB实例")

        # 流量极低
        if daily_traffic < 1:
            suggestions.append("建议评估是否有必要保留此SLB实例")

        # 连接数极低
        if active_conn < 1:
            suggestions.append("建议检查应用是否需要负载均衡")

        # 带宽优化
        bandwidth = instance.get("Bandwidth", 0)
        if bandwidth > 0 and daily_traffic < 10:
            suggestions.append(f"建议降低带宽（当前{bandwidth}Mbps，使用率极低）")

        if not suggestions:
            suggestions.append("资源使用正常，无需优化")

        return "; ".join(suggestions)

    def save_to_database(self, instances, metrics_data):
        """保存数据到数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        for instance in instances:
            cursor.execute(
                """
                INSERT OR REPLACE INTO slb_instances 
                (instance_id, instance_name, instance_type, address_type, region, status, bandwidth, creation_time, monthly_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    instance["InstanceId"],
                    instance.get("InstanceName", ""),
                    instance.get("InstanceType", ""),
                    instance.get("AddressType", ""),
                    instance.get("Region", ""),
                    instance.get("InstanceStatus", ""),
                    instance.get("Bandwidth", 0),
                    instance.get("CreateTime", ""),
                    0,
                ),
            )

            instance_id = instance["InstanceId"]
            if instance_id in metrics_data:
                metrics = metrics_data[instance_id]
                for metric_name, metric_value in metrics.items():
                    cursor.execute(
                        """
                        INSERT INTO slb_monitoring_data (instance_id, metric_name, metric_value, timestamp)
                        VALUES (?, ?, ?, ?)
                    """,
                        (instance_id, metric_name, metric_value, int(time.time())),
                    )

        conn.commit()
        conn.close()

    def analyze(self, regions=None, days=14):
        """分析资源 (BaseResourceAnalyzer接口)"""
        # SLBAnalyzer的analyze_slb_instances逻辑比较复杂
        self.analyze_slb_instances()
        return []

    def generate_report(self, idle_instances):
        """生成报告 (BaseResourceAnalyzer接口)"""
        # 已经在analyze中生成了
        pass

    def analyze_slb_instances(self):
        """分析SLB实例"""
        self.logger.info("开始SLB资源分析...")

        regions = self.get_all_regions()

        # 并发获取所有区域的实例
        self.logger.info("🔍 并发获取所有区域的SLB实例...")

        def get_region_instances(region_item):
            """获取单个区域的实例（用于并发）"""
            region = region_item
            try:
                instances = self.get_slb_instances(region)
                return {"region": region, "instances": instances}
            except Exception as e:
                self.logger.warning(f"区域 {region} 获取实例失败: {e}")
                return {"region": region, "instances": []}

        # 并发获取所有区域的实例
        region_results = process_concurrently(
            regions, get_region_instances, max_workers=10, description="获取SLB实例"
        )

        # 整理所有实例
        all_instances_raw = []
        for result in region_results:
            if result and result.get("instances"):
                all_instances_raw.extend(result["instances"])
                self.logger.info(f"{result['region']}: {len(result['instances'])} 个实例")

        if not all_instances_raw:
            self.logger.warning("未发现任何SLB实例")
            return

        self.logger.info(f"总共获取到 {len(all_instances_raw)} 个SLB实例")

        # 定义单个实例处理函数（用于并发）
        def process_single_instance(instance_item):
            """处理单个实例（用于并发）"""
            instance = instance_item
            instance_id = instance["InstanceId"]
            region = instance["Region"]

            try:
                lb_type = instance.get("LoadBalancerType", "clb")
                metrics = self.get_slb_metrics(region, instance_id, lb_type)

                is_idle, conditions = self.is_slb_idle(instance, metrics)
                optimization = self.get_optimization_suggestion(instance, metrics)

                instance["metrics"] = metrics
                instance["is_idle"] = is_idle
                instance["idle_conditions"] = conditions
                instance["optimization"] = optimization

                return {"success": True, "instance": instance}
            except Exception as e:
                ErrorHandler.handle_instance_error(
                    e, instance_id, region, "SLB", continue_on_error=True
                )
                return {"success": False, "instance": instance, "error": str(e)}

        # 并发处理所有实例
        self.logger.info("并发获取监控数据并分析（最多10个并发线程）...")

        def progress_callback(completed, total):
            progress_pct = completed / total * 100
            sys.stdout.write(f"\r📊 处理进度: {completed}/{total} ({progress_pct:.1f}%)")
            sys.stdout.flush()

        processing_results = process_concurrently(
            all_instances_raw,
            process_single_instance,
            max_workers=10,
            description="SLB实例分析",
            progress_callback=progress_callback,
        )

        print()  # 换行

        # 整理结果
        all_instances = []
        metrics_data = {}
        success_count = 0
        fail_count = 0

        for result in processing_results:
            if result and result.get("success"):
                instance = result["instance"]
                all_instances.append(instance)
                metrics_data[instance["InstanceId"]] = instance.get("metrics", {})
                success_count += 1
            else:
                fail_count += 1

        self.logger.info(f"处理完成: 成功 {success_count} 个, 失败 {fail_count} 个")

        # 保存数据
        self.save_to_database(all_instances, metrics_data)

        # 生成报告
        self.generate_slb_report(all_instances)

        self.logger.info("SLB分析完成")

    def generate_slb_report(self, instances):
        """生成SLB报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        idle_instances = [inst for inst in instances if inst.get("is_idle", False)]

        self.logger.info(
            f"分析结果: 共 {len(instances)} 个SLB实例，其中 {len(idle_instances)} 个闲置"
        )

        if not idle_instances:
            self.logger.info("没有发现闲置的SLB实例")
            return

        # 生成HTML报告
        html_file = f"slb_idle_report_{timestamp}.html"
        self.generate_html_report(idle_instances, html_file)

        # 生成Excel报告
        excel_file = f"slb_idle_report_{timestamp}.xlsx"
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
    <title>SLB闲置实例报告</title>
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
        <h1>⚖️ SLB闲置实例分析报告</h1>
        
        <div class="summary">
            <h3>📋 报告摘要</h3>
            <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>闲置实例数量:</strong> {len(idle_instances)} 个</p>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>实例ID</th>
                    <th>实例名称</th>
                    <th>负载均衡类型</th>
                    <th>区域</th>
                    <th>地址类型</th>
                    <th>规格</th>
                    <th>带宽(Mbps)</th>
                    <th>后端服务器数</th>
                    <th>监听器数</th>
                    <th>活跃连接数</th>
                    <th>日均新建连接</th>
                    <th>日均流量(MB)</th>
                    <th>闲置原因</th>
                    <th>优化建议</th>
                </tr>
            </thead>
            <tbody>
"""

        for instance in idle_instances:
            metrics = instance.get("metrics", {})
            daily_traffic = metrics.get("总流量(MB)", 0) / 14
            daily_new_conn = metrics.get("新建连接数", 0) / 14
            conditions = instance.get("idle_conditions", [])
            optimization = instance.get("optimization", "")

            html_content += f"""
                <tr>
                    <td>{instance['InstanceId']}</td>
                    <td>{instance.get('InstanceName', '')}</td>
                    <td>{instance.get('LoadBalancerTypeName', 'CLB')}</td>
                    <td>{instance.get('Region', '')}</td>
                    <td>{instance.get('AddressType', '')}</td>
                    <td>{instance.get('InstanceType', '')}</td>
                    <td>{instance.get('Bandwidth', 0)}</td>
                    <td>{instance.get('BackendServerCount', 0)}</td>
                    <td>{instance.get('ListenerCount', 0)}</td>
                    <td>{metrics.get('活跃连接数', 0):.0f}</td>
                    <td>{daily_new_conn:.0f}</td>
                    <td>{daily_traffic:.2f}</td>
                    <td class="idle-reason">{"; ".join(conditions)}</td>
                    <td class="optimization">{optimization}</td>
                </tr>
"""

        html_content += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>本报告由阿里云资源分析工具自动生成 | SLB闲置实例分析</p>
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
            data = []
            for instance in idle_instances:
                metrics = instance.get("metrics", {})
                daily_traffic = metrics.get("总流量(MB)", 0) / 14
                daily_new_conn = metrics.get("新建连接数", 0) / 14

                data.append(
                    {
                        "实例ID": instance["InstanceId"],
                        "实例名称": instance.get("InstanceName", ""),
                        "负载均衡类型": instance.get("LoadBalancerTypeName", "CLB"),
                        "区域": instance.get("Region", ""),
                        "地址类型": instance.get("AddressType", ""),
                        "规格": instance.get("InstanceType", ""),
                        "带宽(Mbps)": instance.get("Bandwidth", 0),
                        "后端服务器数": instance.get("BackendServerCount", 0),
                        "监听器数": instance.get("ListenerCount", 0),
                        "活跃连接数": round(metrics.get("活跃连接数", 0), 0),
                        "日均新建连接": round(daily_new_conn, 0),
                        "日均流量(MB)": round(daily_traffic, 2),
                        "闲置原因": "; ".join(instance.get("idle_conditions", [])),
                        "优化建议": instance.get("optimization", ""),
                    }
                )

            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine="openpyxl")

        except ImportError:
            self.logger.warning(" pandas未安装，跳过Excel报告生成")


def main(access_key_id=None, access_key_secret=None):
    """主函数"""
    # 如果没有传入参数，尝试从配置文件读取
    if access_key_id is None or access_key_secret is None:
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                access_key_id = access_key_id or config.get("access_key_id")
                access_key_secret = access_key_secret or config.get("access_key_secret")
        except FileNotFoundError:
            raise ValueError("必须提供access_key_id和access_key_secret，或配置文件config.json")

    analyzer = SLBAnalyzer(access_key_id, access_key_secret)
    analyzer.analyze_slb_instances()


if __name__ == "__main__":
    main()
