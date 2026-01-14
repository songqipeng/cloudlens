#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VPC网络资源分析模块
分析VPC、子网、路由表、安全组的使用情况,提供优化建议
"""

import json
import sqlite3
import sys
from datetime import datetime
from typing import Dict, List

import pandas as pd
from aliyunsdkcore.client import AcsClient
from aliyunsdkvpc.request.v20160428 import (
    DescribeVpcsRequest,
    DescribeVSwitchesRequest,
    DescribeRouteTablesRequest,
)
from aliyunsdkecs.request.v20140526 import (
    DescribeInstancesRequest,
    DescribeSecurityGroupsRequest,
)

from cloudlens.core.analyzer_registry import AnalyzerRegistry
from cloudlens.core.base_analyzer import BaseResourceAnalyzer
from cloudlens.utils.concurrent_helper import process_concurrently
from cloudlens.utils.error_handler import ErrorHandler
from cloudlens.utils.logger import get_logger


@AnalyzerRegistry.register("vpc", "VPC网络", "🌐")
class VPCAnalyzer(BaseResourceAnalyzer):
    """VPC网络资源分析器"""

    def __init__(self, access_key_id, access_key_secret, tenant_name=None):
        super().__init__(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            tenant_name=tenant_name or "default",
        )
        self.db_name = "vpc_monitoring_data.db"
        self.logger = get_logger("vpc_analyzer")
        self.init_database()

    def get_resource_type(self) -> str:
        return "vpc"

    def init_database(self):
        """初始化VPC数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # 创建VPC表
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS vpcs (
            vpc_id TEXT PRIMARY KEY,
            vpc_name TEXT,
            cidr_block TEXT,
            status TEXT,
            region TEXT,
            creation_time TEXT,
            vswitch_count INTEGER DEFAULT 0,
            route_table_count INTEGER DEFAULT 0,
            security_group_count INTEGER DEFAULT 0,
            resource_count INTEGER DEFAULT 0
        )
        """
        )

        conn.commit()
        conn.close()
        self.logger.info("VPC数据库初始化完成")

    def get_all_regions(self):
        """获取所有可用区域"""
        client = AcsClient(self.access_key_id, self.access_key_secret, "cn-hangzhou")
        from aliyunsdkcore.request import CommonRequest
        
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
        """获取指定区域的VPC实例"""
        return self.get_vpcs(region)

    def get_vpcs(self, region_id):
        """获取指定区域的VPC"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeVpcsRequest.DescribeVpcsRequest()
            request.set_PageSize(50)
            request.set_PageNumber(1)

            all_vpcs = []
            page_number = 1

            while True:
                request.set_PageNumber(page_number)
                response = client.do_action_with_exception(request)
                data = json.loads(response)

                if "Vpcs" in data and "Vpc" in data["Vpcs"]:
                    vpcs = data["Vpcs"]["Vpc"]

                    if not vpcs:
                        break

                    for vpc in vpcs:
                        all_vpcs.append(
                            {
                                "VpcId": vpc["VpcId"],
                                "VpcName": vpc.get("VpcName", ""),
                                "CidrBlock": vpc.get("CidrBlock", ""),
                                "Status": vpc.get("Status", ""),
                                "CreationTime": vpc.get("CreationTime", ""),
                                "Region": region_id,
                            }
                        )

                    total_count = data.get("TotalCount", 0)
                    if len(all_vpcs) >= total_count:
                        break

                    page_number += 1
                else:
                    break

            return all_vpcs
        except Exception as e:
            self.logger.info(f"获取VPC失败 {region_id}: {str(e)}")
            return []

    def get_vswitch_count(self, region_id, vpc_id):
        """获取VPC中的交换机数量和IP使用情况"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeVSwitchesRequest.DescribeVSwitchesRequest()
            request.set_VpcId(vpc_id)
            request.set_PageSize(50)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            if "VSwitches" in data and "VSwitch" in data["VSwitches"]:
                vswitches = data["VSwitches"]["VSwitch"]
                
                total_ips = 0
                available_ips = 0
                
                for vs in vswitches:
                    total_ips += vs.get("TotalIpAddressCount", 0)
                    available_ips += vs.get("AvailableIpAddressCount", 0)
                
                used_ips = total_ips - available_ips
                ip_usage_rate = (used_ips / total_ips * 100) if total_ips > 0 else 0
                
                return {
                    "count": len(vswitches),
                    "total_ips": total_ips,
                    "used_ips": used_ips,
                    "ip_usage_rate": ip_usage_rate
                }
            return {"count": 0, "total_ips": 0, "used_ips": 0, "ip_usage_rate": 0}
        except Exception as e:
            self.logger.debug(f"获取VSwitch失败: {e}")
            return {"count": 0, "total_ips": 0, "used_ips": 0, "ip_usage_rate": 0}

    def get_route_table_count(self, region_id, vpc_id):
        """获取路由表数量和规则统计"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeRouteTablesRequest.DescribeRouteTablesRequest()
            request.set_VpcId(vpc_id)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            if "RouteTables" in data and "RouteTable" in data["RouteTables"]:
                tables = data["RouteTables"]["RouteTable"]
                
                total_rules = 0
                for table in tables:
                    route_entrys = table.get("RouteEntrys", {}).get("RouteEntry", [])
                    total_rules += len(route_entrys)
                
                return {"count": len(tables), "total_rules": total_rules}
            return {"count": 0, "total_rules": 0}
        except Exception as e:
            self.logger.debug(f"获取路由表失败: {e}")
            return {"count": 0, "total_rules": 0}

    def get_security_group_count(self, region_id, vpc_id):
        """获取安全组数量和规则统计"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeSecurityGroupsRequest.DescribeSecurityGroupsRequest()
            request.set_VpcId(vpc_id)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            if "SecurityGroups" in data and "SecurityGroup" in data["SecurityGroups"]:
                return {"count": len(data["SecurityGroups"]["SecurityGroup"])}
            return {"count": 0}
        except Exception as e:
            self.logger.debug(f"获取安全组失败: {e}")
            return {"count": 0}

    def get_resource_count_in_vpc(self, region_id, vpc_id):
        """获取VPC中的资源数量(ECS等)"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region_id)
            request = DescribeInstancesRequest.DescribeInstancesRequest()
            request.set_VpcId(vpc_id)
            request.set_PageSize(1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            return data.get("TotalCount", 0)
        except Exception as e:
            self.logger.debug(f"获取VPC资源数失败: {e}")
            return 0

    def get_metrics(self, region: str, instance_id: str, days: int = 14) -> Dict:
        """获取VPC的详细信息"""
        vpc_id = instance_id
        
        # 获取子网信息
        vswitch_info = self.get_vswitch_count(region, vpc_id)
        
        # 获取路由表信息
        route_info = self.get_route_table_count(region, vpc_id)
        
        # 获取安全组信息
        sg_info = self.get_security_group_count(region, vpc_id)
        
        # 获取资源数量
        resource_count = self.get_resource_count_in_vpc(region, vpc_id)
        
        return {
            "vswitch_count": vswitch_info["count"],
            "total_ips": vswitch_info["total_ips"],
            "used_ips": vswitch_info["used_ips"],
            "ip_usage_rate": vswitch_info["ip_usage_rate"],
            "route_table_count": route_info["count"],
            "route_rule_count": route_info["total_rules"],
            "security_group_count": sg_info["count"],
            "resource_count": resource_count,
        }

    def is_idle(self, instance: Dict, metrics: Dict, thresholds: Dict = None) -> tuple:
        """判断VPC是否闲置或需要优化"""
        if thresholds is None:
            thresholds = {
                "no_resources": True,
                "ip_usage_low": 10,  # IP使用率 < 10%
                "route_rules_too_many": 50,  # 路由规则 > 50条
            }

        issues = []

        # 1. VPC内无资源
        resource_count = metrics.get("resource_count", 0)
        if resource_count == 0 and thresholds["no_resources"]:
            issues.append(f"VPC内无任何资源(空VPC)")

        # 2. IP使用率极低
        ip_usage = metrics.get("ip_usage_rate", 0)
        if ip_usage > 0 and ip_usage < thresholds["ip_usage_low"]:
            issues.append(f"IP使用率过低({ip_usage:.1f}% < {thresholds['ip_usage_low']}%)")

        # 3. 路由规则过多
        route_rules = metrics.get("route_rule_count", 0)
        if route_rules > thresholds["route_rules_too_many"]:
            issues.append(f"路由规则过多({route_rules} > {thresholds['route_rules_too_many']}条)")

        return len(issues) > 0, issues

    def get_optimization_suggestions(self, instance: Dict, metrics: Dict) -> str:
        """获取优化建议"""
        suggestions = []

        resource_count = metrics.get("resource_count", 0)
        ip_usage = metrics.get("ip_usage_rate", 0)
        route_rules = metrics.get("route_rule_count", 0)
        vswitch_count = metrics.get("vswitch_count", 0)

        # 空VPC
        if resource_count == 0:
            suggestions.append("建议删除空VPC或迁移资源")

        # IP使用率低
        if ip_usage < 10 and ip_usage > 0:
            suggestions.append(f"IP使用率仅{ip_usage:.1f}%,建议减少子网数量或调整CIDR")

        # 路由规则多
        if route_rules > 50:
            suggestions.append(f"路由规则较多({route_rules}条),建议清理无用规则")

        # 子网建议
        if vswitch_count > 20:
            suggestions.append(f"子网数量较多({vswitch_count}个),建议评估是否合理")

        if not suggestions:
            suggestions.append("VPC配置合理")

        return "; ".join(suggestions)

    def analyze(self, regions=None, days=14):
        """分析资源"""
        self.analyze_vpcs()
        return []

    def generate_report(self, idle_instances):
        """生成报告"""
        pass

    def analyze_vpcs(self):
        """分析VPC资源"""
        self.logger.info("开始VPC资源分析...")

        regions = self.get_all_regions()

        # 并发获取所有区域的VPC
        self.logger.info("🔍 并发获取所有区域的VPC...")

        def get_region_vpcs(region_item):
            region = region_item
            try:
                vpcs = self.get_vpcs(region)
                return {"region": region, "vpcs": vpcs}
            except Exception as e:
                self.logger.warning(f"区域 {region} 获取VPC失败: {e}")
                return {"region": region, "vpcs": []}

        region_results = process_concurrently(
            regions, get_region_vpcs, max_workers=10, description="获取VPC"
        )

        # 整理所有VPC
        all_vpcs = []
        for result in region_results:
            if result and result.get("vpcs"):
                all_vpcs.extend(result["vpcs"])
                self.logger.info(f"{result['region']}: {len(result['vpcs'])} 个VPC")

        if not all_vpcs:
            self.logger.warning("未发现任何VPC")
            return

        self.logger.info(f"总共获取到 {len(all_vpcs)} 个VPC")

        # 处理每个VPC
        def process_single_vpc(vpc_item):
            vpc = vpc_item
            vpc_id = vpc["VpcId"]
            region = vpc["Region"]

            try:
                metrics = self.get_metrics(region, vpc_id)

                has_issues, issues = self.is_idle(vpc, metrics)
                optimization = self.get_optimization_suggestions(vpc, metrics)

                vpc["metrics"] = metrics
                vpc["has_issues"] = has_issues
                vpc["issues"] = issues
                vpc["optimization"] = optimization

                return {"success": True, "vpc": vpc}
            except Exception as e:
                ErrorHandler.handle_instance_error(
                    e, vpc_id, region, "VPC", continue_on_error=True
                )
                return {"success": False, "vpc": vpc, "error": str(e)}

        # 并发处理
        self.logger.info("并发分析VPC详情...")

        def progress_callback(completed, total):
            progress_pct = completed / total * 100
            sys.stdout.write(f"\r📊 处理进度: {completed}/{total} ({progress_pct:.1f}%)")
            sys.stdout.flush()

        processing_results = process_concurrently(
            all_vpcs,
            process_single_vpc,
            max_workers=10,
            description="VPC分析",
            progress_callback=progress_callback,
        )

        # 整理结果
        analyzed_vpcs = []
        success_count = 0
        fail_count = 0

        for result in processing_results:
            if result and result.get("success"):
                vpc = result["vpc"]
                analyzed_vpcs.append(vpc)
                success_count += 1
            else:
                fail_count += 1

        self.logger.info(f"\n处理完成: 成功 {success_count} 个, 失败 {fail_count} 个")

        # 生成报告
        self.generate_vpc_report(analyzed_vpcs)

        self.logger.info("VPC分析完成")

    def generate_vpc_report(self, vpcs):
        """生成VPC报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 筛选有问题的VPC
        problem_vpcs = [vpc for vpc in vpcs if vpc.get("has_issues", False)]

        self.logger.info(
            f"分析结果: 共 {len(vpcs)} 个VPC，其中 {len(problem_vpcs)} 个需要优化"
        )

        # 生成HTML报告
        html_file = f"vpc_analysis_report_{timestamp}.html"
        self.generate_html_report(vpcs, problem_vpcs, html_file)

        # 生成Excel报告
        excel_file = f"vpc_analysis_report_{timestamp}.xlsx"
        self.generate_excel_report(vpcs, excel_file)

        self.logger.info(f"📄 报告已生成:")
        self.logger.info(f"  HTML: {html_file}")
        self.logger.info(f"  Excel: {excel_file}")

    def generate_html_report(self, all_vpcs, problem_vpcs, filename):
        """生成HTML报告"""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>VPC网络分析报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 20px; }}
        .summary {{ background: #ecf0f1; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background-color: #3498db; color: white; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #e8f4f8; }}
        .issue {{ color: #e74c3c; font-weight: bold; }}
        .optimization {{ color: #27ae60; font-style: italic; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 VPC网络资源分析报告</h1>
        
        <div class="summary">
            <h3>📋 报告摘要</h3>
            <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>VPC总数:</strong> {len(all_vpcs)} 个</p>
            <p><strong>需要优化的VPC:</strong> {len(problem_vpcs)} 个</p>
        </div>
        
        <h2>需要优化的VPC</h2>
        <table>
            <thead>
                <tr>
                    <th>VPC ID</th>
                    <th>名称</th>
                    <th>区域</th>
                    <th>CIDR</th>
                    <th>资源数</th>
                    <th>子网数</th>
                    <th>IP使用率</th>
                    <th>路由规则</th>
                    <th>问题</th>
                    <th>优化建议</th>
                </tr>
            </thead>
            <tbody>
"""

        for vpc in problem_vpcs:
            metrics = vpc.get("metrics", {})
            issues = vpc.get("issues", [])
            
            html_content += f"""
                <tr>
                    <td>{vpc['VpcId']}</td>
                    <td>{vpc.get('VpcName', '未命名')}</td>
                    <td>{vpc.get('Region', '')}</td>
                    <td>{vpc.get('CidrBlock', '')}</td>
                    <td>{metrics.get('resource_count', 0)}</td>
                    <td>{metrics.get('vswitch_count', 0)}</td>
                    <td>{metrics.get('ip_usage_rate', 0):.1f}%</td>
                    <td>{metrics.get('route_rule_count', 0)}</td>
                    <td class="issue">{"; ".join(issues)}</td>
                    <td class="optimization">{vpc.get('optimization', '')}</td>
                </tr>
"""

        html_content += """
            </tbody>
        </table>
        
        <div class="footer" style="text-align: center; margin-top: 30px; color: #7f8c8d; font-size: 0.9em;">
            <p>本报告由阿里云资源分析工具自动生成 | VPC网络分析</p>
        </div>
    </div>
</body>
</html>
"""

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)

    def generate_excel_report(self, vpcs, filename):
        """生成Excel报告"""
        try:
            data = []
            for vpc in vpcs:
                metrics = vpc.get("metrics", {})

                data.append(
                    {
                        "VPC ID": vpc["VpcId"],
                        "名称": vpc.get("VpcName", "未命名"),
                        "区域": vpc.get("Region", ""),
                        "CIDR": vpc.get("CidrBlock", ""),
                        "状态": vpc.get("Status", ""),
                        "资源数量": metrics.get("resource_count", 0),
                        "子网数量": metrics.get("vswitch_count", 0),
                        "总IP数": metrics.get("total_ips", 0),
                        "已用IP": metrics.get("used_ips", 0),
                        "IP使用率(%)": round(metrics.get("ip_usage_rate", 0), 1),
                        "路由表数": metrics.get("route_table_count", 0),
                        "路由规则数": metrics.get("route_rule_count", 0),
                        "安全组数": metrics.get("security_group_count", 0),
                        "问题": "; ".join(vpc.get("issues", [])),
                        "优化建议": vpc.get("optimization", ""),
                    }
                )

            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine="openpyxl")

        except ImportError:
            self.logger.warning("pandas未安装，跳过Excel报告生成")


if __name__ == "__main__":
    import sys
    sys.path.append("..")
    
    try:
        with open("../config.json", "r") as f:
            config = json.load(f)
            access_key_id = config.get("access_key_id")
            access_key_secret = config.get("access_key_secret")
            
        analyzer = VPCAnalyzer(access_key_id, access_key_secret)
        analyzer.analyze_vpcs()
    except Exception as e:
        print(f"错误: {e}")
