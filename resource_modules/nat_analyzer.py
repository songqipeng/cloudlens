#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NAT网关资源分析模块
分析NAT网关的闲置情况,提供优化建议
"""

import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkvpc.request.v20160428 import DescribeNatGatewaysRequest

from core.analyzer_registry import AnalyzerRegistry
from core.base_analyzer import BaseResourceAnalyzer
from utils.concurrent_helper import process_concurrently
from utils.error_handler import ErrorHandler
from utils.logger import get_logger


@AnalyzerRegistry.register("nat", "NAT网关", "🌉")
class NATAnalyzer(BaseResourceAnalyzer):
    """NAT网关资源分析器"""

    def __init__(self, access_key_id, access_key_secret, tenant_name=None):
        super().__init__(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            tenant_name=tenant_name or "default",
        )
        self.db_name = "nat_monitoring_data.db"
        self.logger = get_logger("nat_analyzer")
        self.init_database()

    def get_resource_type(self) -> str:
        return "nat"

    def init_database(self):
        """初始化NAT网关数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # 创建NAT网关实例表
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS nat_gateways (
            nat_gateway_id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT,
            business_status TEXT,
            vpc_id TEXT,
            spec TEXT,
            region TEXT,
            creation_time TEXT,
            ip_count INTEGER DEFAULT 0,
            snat_count INTEGER DEFAULT 0,
            bandwidth_package_count INTEGER DEFAULT 0,
            monthly_cost REAL DEFAULT 0
        )
        """
        )

        # 创建NAT网关监控数据表
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS nat_monitoring_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nat_gateway_id TEXT,
            metric_name TEXT,
            metric_value REAL,
            timestamp INTEGER,
            FOREIGN KEY (nat_gateway_id) REFERENCES nat_gateways (nat_gateway_id)
        )
        """
        )

        conn.commit()
        conn.close()
        self.logger.info("NAT网关数据库初始化完成")

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

    def get_instances(self, region: str) -> List[Dict]:
        """获取指定区域的NAT网关实例"""
        return self.get_nat_gateways(region)

    def get_nat_gateways(self, region_id):
        """获取指定区域的NAT网关实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeNatGatewaysRequest.DescribeNatGatewaysRequest()
            request.set_PageSize(50)
            request.set_PageNumber(1)

            all_nats = []
            page_number = 1

            while True:
                request.set_PageNumber(page_number)
                response = client.do_action_with_exception(request)
                data = json.loads(response)

                if "NatGateways" in data and "NatGateway" in data["NatGateways"]:
                    nats = data["NatGateways"]["NatGateway"]

                    if not nats:
                        break

                    for nat in nats:
                        # 获取绑定的EIP信息
                        ip_list = nat.get("IpLists", {}).get("IpList", [])
                        
                        # 获取SNAT条目信息
                        snat_table = nat.get("SnatTableIds", {}).get("SnatTableId", [])
                        
                        # 获取带宽包信息
                        bandwidth_packages = nat.get("BandwidthPackageIds", {}).get("BandwidthPackageId", [])

                        all_nats.append(
                            {
                                "NatGatewayId": nat["NatGatewayId"],
                                "Name": nat.get("Name", ""),
                                "Status": nat.get("Status", ""),
                                "BusinessStatus": nat.get("BusinessStatus", ""),
                                "VpcId": nat.get("VpcId", ""),
                                "Spec": nat.get("Spec", ""),
                                "CreationTime": nat.get("CreationTime", ""),
                                "IpCount": len(ip_list),
                                "IpList": ip_list,
                                "SnatCount": len(snat_table),
                                "BandwidthPackageCount": len(bandwidth_packages),
                                "Region": region_id,
                            }
                        )

                    # 检查是否还有更多页面
                    total_count = data.get("TotalCount", 0)
                    if len(all_nats) >= total_count:
                        break

                    page_number += 1
                else:
                    break

            return all_nats
        except Exception as e:
            self.logger.info(f"获取NAT网关失败 {region_id}: {str(e)}")
            return []

    def get_metrics(self, region: str, instance_id: str, days: int = 14) -> Dict:
        """获取NAT网关的监控数据"""
        return self.get_nat_metrics(region, instance_id, days)

    def get_nat_metrics(self, region_id, nat_gateway_id, days=14):
        """获取NAT网关的监控指标"""
        client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        # NAT网关监控指标
        metrics_config = {
            "net_rx.rate": "入流量速率",
            "net_tx.rate": "出流量速率",
            "SnatConnection": "SNAT连接数",
        }

        result = {}

        for metric_name, display_name in metrics_config.items():
            try:
                request = CommonRequest()
                request.set_domain(f"cms.{region_id}.aliyuncs.com")
                request.set_method("POST")
                request.set_version("2019-01-01")
                request.set_action_name("DescribeMetricData")
                request.add_query_param("RegionId", region_id)
                request.add_query_param("Namespace", "acs_nat_gateway")
                request.add_query_param("MetricName", metric_name)
                request.add_query_param("StartTime", start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
                request.add_query_param("EndTime", end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
                request.add_query_param("Period", "86400")  # 1天聚合
                request.add_query_param(
                    "Dimensions", f'[{{"instanceId":"{nat_gateway_id}"}}]'
                )
                request.add_query_param("Statistics", "Average")

                response = client.do_action_with_exception(request)
                data = json.loads(response)

                if "Datapoints" in data and data["Datapoints"]:
                    if isinstance(data["Datapoints"], str):
                        dps = json.loads(data["Datapoints"])
                    else:
                        dps = data["Datapoints"]

                    if dps and len(dps) > 0:
                        # 计算平均值和最大值
                        values = [
                            float(dp.get("Average", 0))
                            for dp in dps
                            if dp.get("Average") is not None
                        ]
                        if values:
                            result[display_name] = sum(values) / len(values)
                            result[f"{display_name}_max"] = max(values)
                        else:
                            result[display_name] = 0
                            result[f"{display_name}_max"] = 0
                    else:
                        result[display_name] = 0
                        result[f"{display_name}_max"] = 0
                else:
                    result[display_name] = 0
                    result[f"{display_name}_max"] = 0

            except Exception as e:
                self.logger.debug(f"指标 {metric_name} 获取失败: {e}")
                result[display_name] = 0
                result[f"{display_name}_max"] = 0

        # 计算总流量(MB)
        rx_rate = result.get("入流量速率", 0)  # bytes/s
        tx_rate = result.get("出流量速率", 0)  # bytes/s
        total_traffic_bytes = (rx_rate + tx_rate) * 86400 * days  # 转换为days天总流量
        result["总流量(MB)"] = total_traffic_bytes / (1024 * 1024)

        return result

    def is_idle(self, instance: Dict, metrics: Dict, thresholds: Dict = None) -> tuple:
        """判断NAT网关是否闲置"""
        if thresholds is None:
            thresholds = {
                "no_eip": True,  # 未绑定EIP
                "no_snat": True,  # 无SNAT条目
                "traffic_mb_total": 100,  # 总流量阈值(MB)
                "snat_connection": 10,  # SNAT连接数阈值
            }

        idle_conditions = []

        # 1. 未绑定EIP
        ip_count = instance.get("IpCount", 0)
        if ip_count == 0 and thresholds["no_eip"]:
            idle_conditions.append("未绑定EIP")

        # 2. 无SNAT条目
        snat_count = instance.get("SnatCount", 0)
        if snat_count == 0 and thresholds["no_snat"]:
            idle_conditions.append("无SNAT条目")

        # 3. 流量极低
        total_traffic_mb = metrics.get("总流量(MB)", 0)
        if total_traffic_mb < thresholds["traffic_mb_total"]:
            idle_conditions.append(
                f"14天总流量({total_traffic_mb:.2f}MB) < {thresholds['traffic_mb_total']}MB"
            )

        # 4. SNAT连接数极低
        snat_connections = metrics.get("SNAT连接数", 0)
        if snat_connections < thresholds["snat_connection"]:
            idle_conditions.append(
                f"SNAT连接数({snat_connections:.0f}) < {thresholds['snat_connection']}"
            )

        # 5. 业务状态异常
        business_status = instance.get("BusinessStatus", "")
        if business_status in ["FinancialLocked", "SecurityLocked"]:
            idle_conditions.append(f"业务状态异常: {business_status}")

        return len(idle_conditions) > 0, idle_conditions

    def get_optimization_suggestions(self, instance: Dict, metrics: Dict) -> str:
        """获取优化建议"""
        suggestions = []

        ip_count = instance.get("IpCount", 0)
        snat_count = instance.get("SnatCount", 0)
        total_traffic_mb = metrics.get("总流量(MB)", 0)
        spec = instance.get("Spec", "")

        # 未绑定EIP
        if ip_count == 0:
            suggestions.append("建议绑定EIP或删除未使用的NAT网关")

        # 无SNAT条目
        if snat_count == 0:
            suggestions.append("建议配置SNAT规则或删除闲置NAT网关")

        # 流量极低
        if total_traffic_mb < 10:
            suggestions.append("流量极低,建议评估是否需要保留")

        # 规格优化
        if spec and "Large" in spec and total_traffic_mb < 100:
            suggestions.append(f"当前规格({spec})过高,建议降低规格")

        # 无优化建议
        if not suggestions:
            suggestions.append("资源使用正常,无需优化")

        return "; ".join(suggestions)

    def analyze(self, regions=None, days=14):
        """分析资源"""
        self.analyze_nat_gateways()
        return []

    def generate_report(self, idle_instances):
        """生成报告"""
        # 已在analyze中生成
        pass

    def analyze_nat_gateways(self):
        """分析NAT网关实例"""
        self.logger.info("开始NAT网关资源分析...")

        regions = self.get_all_regions()

        # 并发获取所有区域的实例
        self.logger.info("🔍 并发获取所有区域的NAT网关...")

        def get_region_instances(region_item):
            region = region_item
            try:
                instances = self.get_nat_gateways(region)
                return {"region": region, "instances": instances}
            except Exception as e:
                self.logger.warning(f"区域 {region} 获取实例失败: {e}")
                return {"region": region, "instances": []}

        region_results = process_concurrently(
            regions, get_region_instances, max_workers=10, description="获取NAT网关"
        )

        # 整理所有实例
        all_instances_raw = []
        for result in region_results:
            if result and result.get("instances"):
                all_instances_raw.extend(result["instances"])
                self.logger.info(f"{result['region']}: {len(result['instances'])} 个NAT网关")

        if not all_instances_raw:
            self.logger.warning("未发现任何NAT网关")
            return

        self.logger.info(f"总共获取到 {len(all_instances_raw)} 个NAT网关")

        # 定义单个实例处理函数
        def process_single_instance(instance_item):
            instance = instance_item
            nat_id = instance["NatGatewayId"]
            region = instance["Region"]

            try:
                metrics = self.get_nat_metrics(region, nat_id)

                is_idle_result, conditions = self.is_idle(instance, metrics)
                optimization = self.get_optimization_suggestions(instance, metrics)

                instance["metrics"] = metrics
                instance["is_idle"] = is_idle_result
                instance["idle_conditions"] = conditions
                instance["optimization"] = optimization

                return {"success": True, "instance": instance}
            except Exception as e:
                error = ErrorHandler.handle_api_error(e, "NAT", region, nat_id)
                ErrorHandler.handle_instance_error(
                    e, nat_id, region, "NAT", continue_on_error=True
                )
                return {"success": False, "instance": instance, "error": str(e)}

        # 并发处理所有实例
        self.logger.info("并发获取监控数据并分析...")

        def progress_callback(completed, total):
            progress_pct = completed / total * 100
            sys.stdout.write(f"\r📊 处理进度: {completed}/{total} ({progress_pct:.1f}%)")
            sys.stdout.flush()

        processing_results = process_concurrently(
            all_instances_raw,
            process_single_instance,
            max_workers=10,
            description="NAT网关分析",
            progress_callback=progress_callback,
        )

        # 整理结果
        all_instances = []
        success_count = 0
        fail_count = 0

        for result in processing_results:
            if result and result.get("success"):
                instance = result["instance"]
                all_instances.append(instance)
                success_count += 1
            else:
                fail_count += 1

        self.logger.info(f"\n处理完成: 成功 {success_count} 个, 失败 {fail_count} 个")

        # 生成报告
        self.generate_nat_report(all_instances)

        self.logger.info("NAT网关分析完成")

    def generate_nat_report(self, instances):
        """生成NAT网关报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        idle_instances = [inst for inst in instances if inst.get("is_idle", False)]

        self.logger.info(
            f"分析结果: 共 {len(instances)} 个NAT网关，其中 {len(idle_instances)} 个闲置"
        )

        if not idle_instances:
            self.logger.info("没有发现闲置的NAT网关")
            return

        # 生成HTML报告
        html_file = f"nat_idle_report_{timestamp}.html"
        self.generate_html_report(idle_instances, html_file)

        # 生成Excel报告
        excel_file = f"nat_idle_report_{timestamp}.xlsx"
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
    <title>NAT网关闲置实例报告</title>
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
        <h1>🌉 NAT网关闲置实例分析报告</h1>
        
        <div class="summary">
            <h3>📋 报告摘要</h3>
            <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>闲置NAT网关数量:</strong> {len(idle_instances)} 个</p>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>NAT网关ID</th>
                    <th>名称</th>
                    <th>区域</th>
                    <th>状态</th>
                    <th>VPC</th>
                    <th>规格</th>
                    <th>绑定EIP数</th>
                    <th>SNAT条目</th>
                    <th>14天流量(MB)</th>
                    <th>闲置原因</th>
                    <th>优化建议</th>
                </tr>
            </thead>
            <tbody>
"""

        for instance in idle_instances:
            metrics = instance.get("metrics", {})
            conditions = instance.get("idle_conditions", [])
            optimization = instance.get("optimization", "")

            html_content += f"""
                <tr>
                    <td>{instance['NatGatewayId']}</td>
                    <td>{instance.get('Name', '未命名')}</td>
                    <td>{instance.get('Region', '')}</td>
                    <td>{instance.get('Status', '')}</td>
                    <td>{instance.get('VpcId', '')}</td>
                    <td>{instance.get('Spec', '')}</td>
                    <td>{instance.get('IpCount', 0)}</td>
                    <td>{instance.get('SnatCount', 0)}</td>
                    <td>{metrics.get('总流量(MB)', 0):.2f}</td>
                    <td class="idle-reason">{"; ".join(conditions)}</td>
                    <td class="optimization">{optimization}</td>
                </tr>
"""

        html_content += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>本报告由阿里云资源分析工具自动生成 | NAT网关闲置实例分析</p>
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

                data.append(
                    {
                        "NAT网关ID": instance["NatGatewayId"],
                        "名称": instance.get("Name", "未命名"),
                        "区域": instance.get("Region", ""),
                        "状态": instance.get("Status", ""),
                        "业务状态": instance.get("BusinessStatus", ""),
                        "VPC": instance.get("VpcId", ""),
                        "规格": instance.get("Spec", ""),
                        "绑定EIP数": instance.get("IpCount", 0),
                        "SNAT条目数": instance.get("SnatCount", 0),
                        "带宽包数": instance.get("BandwidthPackageCount", 0),
                        "14天流量(MB)": round(metrics.get("总流量(MB)", 0), 2),
                        "SNAT连接数": round(metrics.get("SNAT连接数", 0), 0),
                        "闲置原因": "; ".join(instance.get("idle_conditions", [])),
                        "优化建议": instance.get("optimization", ""),
                    }
                )

            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine="openpyxl")

        except ImportError:
            self.logger.warning("pandas未安装，跳过Excel报告生成")


if __name__ == "__main__":
    # 测试代码
    import sys
    sys.path.append("..")
    
    try:
        with open("../config.json", "r") as f:
            config = json.load(f)
            access_key_id = config.get("access_key_id")
            access_key_secret = config.get("access_key_secret")
            
        analyzer = NATAnalyzer(access_key_id, access_key_secret)
        analyzer.analyze_nat_gateways()
    except Exception as e:
        print(f"错误: {e}")
