#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VPN网关资源分析模块
分析VPN网关的使用情况,提供优化建议
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkvpc.request.v20160428 import (
    DescribeVpnGatewaysRequest,
    DescribeVpnConnectionsRequest,
)

from cloudlens.core.analyzer_registry import AnalyzerRegistry
from cloudlens.core.base_analyzer import BaseResourceAnalyzer
from cloudlens.utils.concurrent_helper import process_concurrently
from cloudlens.utils.error_handler import ErrorHandler
from cloudlens.utils.logger import get_logger


@AnalyzerRegistry.register("vpn", "VPN网关", "🔒")
class VPNAnalyzer(BaseResourceAnalyzer):
    """VPN网关资源分析器"""

    def __init__(self, access_key_id, access_key_secret, tenant_name=None):
        super().__init__(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            tenant_name=tenant_name or "default",
        )
        self.db_name = "vpn_monitoring_data.db"
        self.logger = get_logger("vpn_analyzer")
        self.init_database()

    def get_resource_type(self) -> str:
        return "vpn"

    def init_database(self):
        """初始化VPN数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS vpn_gateways (
            vpn_gateway_id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT,
            business_status TEXT,
            vpc_id TEXT,
            spec TEXT,
            region TEXT,
            creation_time TEXT,
            connection_count INTEGER DEFAULT 0,
            ssl_connection_count INTEGER DEFAULT 0
        )
        """
        )

        conn.commit()
        conn.close()
        self.logger.info("VPN网关数据库初始化完成")

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

        return [region["RegionId"] for region in data["Regions"]["Region"]]

    def get_instances(self, region: str) -> List[Dict]:
        """获取指定区域的VPN网关"""
        return self.get_vpn_gateways(region)

    def get_vpn_gateways(self, region_id):
        """获取指定区域的VPN网关"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeVpnGatewaysRequest.DescribeVpnGatewaysRequest()
            request.set_PageSize(50)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            vpn_gateways = []
            if "VpnGateways" in data and "VpnGateway" in data["VpnGateways"]:
                for vpn in data["VpnGateways"]["VpnGateway"]:
                    vpn_gateways.append(
                        {
                            "VpnGatewayId": vpn["VpnGatewayId"],
                            "Name": vpn.get("Name", ""),
                            "Status": vpn.get("Status", ""),
                            "BusinessStatus": vpn.get("BusinessStatus", ""),
                            "VpcId": vpn.get("VpcId", ""),
                            "Spec": vpn.get("Spec", ""),
                            "CreationTime": vpn.get("CreateTime", ""),
                            "SslConnections": vpn.get("SslMaxConnections", 0),
                            "Region": region_id,
                        }
                    )

            return vpn_gateways
        except Exception as e:
            self.logger.info(f"获取VPN网关失败 {region_id}: {str(e)}")
            return []

    def get_vpn_connections(self, region_id, vpn_gateway_id):
        """获取VPN连接数"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeVpnConnectionsRequest.DescribeVpnConnectionsRequest()
            request.set_VpnGatewayId(vpn_gateway_id)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            if "VpnConnections" in data and "VpnConnection" in data["VpnConnections"]:
                connections = data["VpnConnections"]["VpnConnection"]
                active_count = sum(1 for conn in connections if conn.get("Status") == "ipsec_sa_established")
                return {"total": len(connections), "active": active_count}
            
            return {"total": 0, "active": 0}
        except Exception as e:
            self.logger.debug(f"获取VPN连接失败: {e}")
            return {"total": 0, "active": 0}

    def get_metrics(self, region: str, instance_id: str, days: int = 14) -> Dict:
        """获取VPN网关监控数据"""
        client = AcsClient(self.access_key_id, self.access_key_secret, region)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        metrics_config = {
            "net_rx.rate": "入流量速率",
            "net_tx.rate": "出流量速率",
        }

        result = {}

        for metric_name, display_name in metrics_config.items():
            try:
                request = CommonRequest()
                request.set_domain(f"cms.{region}.aliyuncs.com")
                request.set_method("POST")
                request.set_version("2019-01-01")
                request.set_action_name("DescribeMetricData")
                request.add_query_param("RegionId", region)
                request.add_query_param("Namespace", "acs_vpn")
                request.add_query_param("MetricName", metric_name)
                request.add_query_param("StartTime", start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
                request.add_query_param("EndTime", end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
                request.add_query_param("Period", "86400")
                request.add_query_param(
                    "Dimensions", f'[{{"instanceId":"{instance_id}"}}]'
                )

                response = client.do_action_with_exception(request)
                data = json.loads(response)

                if "Datapoints" in data and data["Datapoints"]:
                    dps = json.loads(data["Datapoints"]) if isinstance(data["Datapoints"], str) else data["Datapoints"]
                    values = [float(dp.get("Average", 0)) for dp in dps if dp.get("Average") is not None]
                    result[display_name] = sum(values) / len(values) if values else 0
                else:
                    result[display_name] = 0
            except Exception as e:
                self.logger.debug(f"指标 {metric_name} 获取失败: {e}")
                result[display_name] = 0

        # 计算总流量
        rx_rate = result.get("入流量速率", 0)
        tx_rate = result.get("出流量速率", 0)
        total_traffic_bytes = (rx_rate + tx_rate) * 86400 * days
        result["总流量(GB)"] = total_traffic_bytes / (1024 * 1024 * 1024)

        # 获取连接信息
        conn_info = self.get_vpn_connections(region, instance_id)
        result["连接总数"] = conn_info["total"]
        result["活跃连接数"] = conn_info["active"]

        return result

    def is_idle(self, instance: Dict, metrics: Dict, thresholds: Dict = None) -> tuple:
        """判断VPN网关是否闲置"""
        if thresholds is None:
            thresholds = {
                "no_connections": True,
                "traffic_gb_total": 1,
                "active_connections": 1,
            }

        idle_conditions = []

        # 无IPsec连接
        total_conn = metrics.get("连接总数", 0)
        if total_conn == 0 and thresholds["no_connections"]:
            idle_conditions.append("无IPsec连接")

        # 无活跃连接
        active_conn = metrics.get("活跃连接数", 0)
        if active_conn < thresholds["active_connections"]:
            idle_conditions.append(f"活跃连接数({active_conn}) < {thresholds['active_connections']}")

        # 流量极低
        total_traffic = metrics.get("总流量(GB)", 0)
        if total_traffic < thresholds["traffic_gb_total"]:
            idle_conditions.append(f"14天流量({total_traffic:.2f}GB) < {thresholds['traffic_gb_total']}GB")

        # 业务状态异常
        business_status = instance.get("BusinessStatus", "")
        if business_status in ["FinancialLocked", "SecurityLocked"]:
            idle_conditions.append(f"业务状态异常: {business_status}")

        return len(idle_conditions) > 0, idle_conditions

    def get_optimization_suggestions(self, instance: Dict, metrics: Dict) -> str:
        """获取优化建议"""
        suggestions = []

        total_conn = metrics.get("连接总数", 0)
        active_conn = metrics.get("活跃连接数", 0)
        total_traffic = metrics.get("总流量(GB)", 0)
        spec = instance.get("Spec", "")

        if total_conn == 0:
            suggestions.append("建议删除无连接的VPN网关")
        
        if active_conn == 0 and total_conn > 0:
            suggestions.append("建议检查VPN连接状态,所有连接均未建立")

        if total_traffic < 0.1:
            suggestions.append("流量极低,建议评估是否需要保留")

        if not suggestions:
            suggestions.append("VPN使用正常")

        return "; ".join(suggestions)

    def analyze(self, regions=None, days=14):
        """分析资源"""
        self.analyze_vpn_gateways()
        return []

    def generate_report(self, idle_instances):
        """生成报告"""
        pass

    def analyze_vpn_gateways(self):
        """分析VPN网关"""
        self.logger.info("开始VPN网关分析...")

        regions = self.get_all_regions()

        def get_region_vpns(region_item):
            region = region_item
            try:
                vpns = self.get_vpn_gateways(region)
                return {"region": region, "vpns": vpns}
            except Exception as e:
                self.logger.warning(f"区域 {region} 获取VPN失败: {e}")
                return {"region": region, "vpns": []}

        region_results = process_concurrently(
            regions, get_region_vpns, max_workers=10, description="获取VPN网关"
        )

        all_vpns = []
        for result in region_results:
            if result and result.get("vpns"):
                all_vpns.extend(result["vpns"])
                self.logger.info(f"{result['region']}: {len(result['vpns'])} 个VPN网关")

        if not all_vpns:
            self.logger.warning("未发现任何VPN网关")
            return

        self.logger.info(f"总共获取到 {len(all_vpns)} 个VPN网关")

        def process_single_vpn(vpn_item):
            vpn = vpn_item
            vpn_id = vpn["VpnGatewayId"]
            region = vpn["Region"]

            try:
                metrics = self.get_metrics(region, vpn_id)
                is_idle_result, conditions = self.is_idle(vpn, metrics)
                optimization = self.get_optimization_suggestions(vpn, metrics)

                vpn["metrics"] = metrics
                vpn["is_idle"] = is_idle_result
                vpn["idle_conditions"] = conditions
                vpn["optimization"] = optimization

                return {"success": True, "vpn": vpn}
            except Exception as e:
                ErrorHandler.handle_instance_error(e, vpn_id, region, "VPN", continue_on_error=True)
                return {"success": False, "vpn": vpn, "error": str(e)}

        def progress_callback(completed, total):
            sys.stdout.write(f"\r📊 处理进度: {completed}/{total} ({completed/total*100:.1f}%)")
            sys.stdout.flush()

        processing_results = process_concurrently(
            all_vpns, process_single_vpn, max_workers=10, description="VPN分析", progress_callback=progress_callback
        )

        analyzed_vpns = [r["vpn"] for r in processing_results if r and r.get("success")]
        
        self.logger.info(f"\n处理完成: 成功 {len(analyzed_vpns)} 个")
        self.generate_vpn_report(analyzed_vpns)
        self.logger.info("VPN分析完成")

    def generate_vpn_report(self, vpns):
        """生成VPN报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        idle_vpns = [vpn for vpn in vpns if vpn.get("is_idle", False)]

        self.logger.info(f"分析结果: 共 {len(vpns)} 个VPN网关，其中 {len(idle_vpns)} 个闲置")

        if not idle_vpns:
            self.logger.info("没有发现闲置的VPN网关")
            return

        # 生成报告
        html_file = f"vpn_idle_report_{timestamp}.html"
        excel_file = f"vpn_idle_report_{timestamp}.xlsx"
        
        self.generate_html_report(idle_vpns, html_file)
        self.generate_excel_report(idle_vpns, excel_file)

        self.logger.info(f"📄 报告已生成: {html_file}, {excel_file}")

    def generate_html_report(self, idle_vpns, filename):
        """生成HTML报告"""
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>VPN网关闲置报告</title>
<style>body{{font-family:'Microsoft YaHei',Arial;margin:20px;background:#f5f5f5}}
.container{{max-width:1400px;margin:0 auto;background:white;padding:20px;border-radius:10px}}
h1{{color:#2c3e50;text-align:center;border-bottom:3px solid #e74c3c;padding-bottom:20px}}
table{{width:100%;border-collapse:collapse;margin:20px 0;font-size:14px}}
th,td{{border:1px solid #ddd;padding:10px;text-align:left}}
th{{background:#3498db;color:white}}tr:hover{{background:#e8f4f8}}</style>
</head><body><div class="container"><h1>🔒 VPN网关闲置实例报告</h1>
<p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p><strong>闲置VPN网关:</strong> {len(idle_vpns)} 个</p>
<table><thead><tr><th>VPN网关ID</th><th>名称</th><th>区域</th><th>状态</th><th>连接数</th><th>活跃连接</th><th>流量(GB)</th><th>闲置原因</th><th>优化建议</th></tr></thead><tbody>"""
        
        for vpn in idle_vpns:
            m = vpn.get("metrics", {})
            html += f"""<tr><td>{vpn['VpnGatewayId']}</td><td>{vpn.get('Name','未命名')}</td><td>{vpn.get('Region','')}</td>
<td>{vpn.get('Status','')}</td><td>{m.get('连接总数',0)}</td><td>{m.get('活跃连接数',0)}</td><td>{m.get('总流量(GB)',0):.2f}</td>
<td>{'; '.join(vpn.get('idle_conditions',[]))}</td><td>{vpn.get('optimization','')}</td></tr>"""
        
        html += "</tbody></table></div></body></html>"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

    def generate_excel_report(self, idle_vpns, filename):
        """生成Excel报告"""
        try:
            data = []
            for vpn in idle_vpns:
                m = vpn.get("metrics", {})
                data.append({
                    "VPN网关ID": vpn["VpnGatewayId"],
                    "名称": vpn.get("Name", "未命名"),
                    "区域": vpn.get("Region", ""),
                    "状态": vpn.get("Status", ""),
                    "VPC": vpn.get("VpcId", ""),
                    "规格": vpn.get("Spec", ""),
                    "连接总数": m.get("连接总数", 0),
                    "活跃连接数": m.get("活跃连接数", 0),
                    "14天流量(GB)": round(m.get("总流量(GB)", 0), 2),
                    "闲置原因": "; ".join(vpn.get("idle_conditions", [])),
                    "优化建议": vpn.get("optimization", ""),
                })
            
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine="openpyxl")
        except ImportError:
            self.logger.warning("pandas未安装")


if __name__ == "__main__":
    pass
