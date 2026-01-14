#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化优化引擎
分析闲置资源并生成优化建议和执行脚本
"""

import json
import os
from datetime import datetime
from typing import Dict, List

from cloudlens.core.database import DatabaseFactory
from cloudlens.utils.logger import get_logger


class OptimizationEngine:
    """优化引擎"""

    def __init__(self):
        self.logger = get_logger("optimization_engine")
        self.optimization_actions = []

    def analyze_optimization_opportunities(self, tenant_name: str) -> List[Dict]:
        """分析优化机会"""
        self.logger.info(f"分析 {tenant_name} 的优化机会...")

        opportunities = []

        # 只分析确实存在的资源
        opportunities.extend(self._analyze_idle_eip(tenant_name))

        # 尝试分析其他资源,忽略错误
        try:
            opportunities.extend(self._analyze_idle_ecs(tenant_name))
        except Exception as e:
            self.logger.debug(f"ECS分析跳过: {e}")

        try:
            opportunities.extend(self._analyze_idle_rds(tenant_name))
        except Exception as e:
            self.logger.debug(f"RDS分析跳过: {e}")

        return opportunities

    def _analyze_idle_ecs(self, tenant_name: str) -> List[Dict]:
        """分析闲置ECS实例"""
        opportunities = []

        try:
            # 使用数据库抽象层读取监控数据
            db = DatabaseFactory.create_adapter("sqlite", db_path="ecs_monitoring_data_fixed.db")

            # 查找闲置ECS (CPU和内存都很低)
            instances = db.query(
                """
                SELECT DISTINCT e.instance_id, e.instance_name, e.instance_type,
                       e.region, e.monthly_cost
                FROM ecs_instances e
                WHERE e.tenant_name = ? AND e.monthly_cost > 0
            """,
                (tenant_name,),
            )

            for inst in instances:
                instance_id = inst.get("instance_id") if isinstance(inst, dict) else inst[0]
                name = inst.get("instance_name") if isinstance(inst, dict) else inst[1]
                instance_type = inst.get("instance_type") if isinstance(inst, dict) else inst[2]
                region = inst.get("region") if isinstance(inst, dict) else inst[3]
                cost = inst.get("monthly_cost") if isinstance(inst, dict) else inst[4]

                # 获取监控数据
                metrics_rows = db.query(
                    """
                    SELECT AVG(metric_value) as avg_val, metric_name
                    FROM ecs_monitoring_data
                    WHERE instance_id = ? AND metric_name IN ('cpu_utilization', 'memory_utilization')
                    GROUP BY metric_name
                """,
                    (instance_id,),
                )

                metrics = {}
                for row in metrics_rows:
                    metric_name = row.get("metric_name") if isinstance(row, dict) else row[1]
                    avg_val = row.get("avg_val") if isinstance(row, dict) else row[0]
                    metrics[metric_name] = avg_val

                cpu_util = metrics.get("cpu_utilization", 0)
                mem_util = metrics.get("memory_utilization", 0)

                # 判断是否闲置或可降配
                if cpu_util < 5 and mem_util < 10:
                    opportunities.append(
                        {
                            "resource_type": "ECS",
                            "resource_id": instance_id,
                            "resource_name": name,
                            "region": region,
                            "action": "release",
                            "reason": f"CPU利用率{cpu_util:.1f}%,内存{mem_util:.1f}%,几乎闲置",
                            "estimated_savings": cost,
                            "current_spec": instance_type,
                            "priority": "high",
                        }
                    )
                elif cpu_util < 20 and "-" in instance_type:
                    # 建议降配
                    downgraded_spec = self._suggest_downgrade_spec(instance_type)
                    if downgraded_spec:
                        opportunities.append(
                            {
                                "resource_type": "ECS",
                                "resource_id": instance_id,
                                "resource_name": name,
                                "region": region,
                                "action": "downgrade",
                                "reason": f"CPU利用率{cpu_util:.1f}%,可降配",
                                "estimated_savings": cost * 0.3,  # 估计节省30%
                                "current_spec": instance_type,
                                "suggested_spec": downgraded_spec,
                                "priority": "medium",
                            }
                        )

            db.close()

        except Exception as e:
            self.logger.error(f"分析ECS失败: {e}")

        return opportunities

    def _suggest_downgrade_spec(self, current_spec: str) -> str:
        """建议降配规格"""
        # 简化逻辑:从xlarge降到large,从large降到medium等
        if "xlarge" in current_spec or "2xlarge" in current_spec:
            return current_spec.replace("2xlarge", "xlarge").replace("xlarge", "large")
        elif "large" in current_spec:
            return current_spec.replace("large", "medium")
        return ""

    def _analyze_idle_rds(self, tenant_name: str) -> List[Dict]:
        """分析闲置RDS数据库"""
        opportunities = []

        try:
            db = DatabaseFactory.create_adapter("sqlite", db_path="rds_monitoring_data.db")

            instances = db.query(
                """
                SELECT DISTINCT db_instance_id, description, db_instance_class,
                       region_id
                FROM rds_instances
            """
            )

            for inst in instances:
                db_id = inst.get("db_instance_id") if isinstance(inst, dict) else inst[0]
                description = inst.get("description") if isinstance(inst, dict) else inst[1]
                instance_class = inst.get("db_instance_class") if isinstance(inst, dict) else inst[2]
                region = inst.get("region_id") if isinstance(inst, dict) else inst[3]

                # 获取连接数
                result = db.query_one(
                    """
                    SELECT AVG(metric_value) as avg_conn
                    FROM rds_monitoring_data
                    WHERE db_instance_id = ? AND metric_name = 'active_connections'
                """,
                    (db_id,),
                )

                avg_conn = result.get("avg_conn", 0) if result else 0

                if avg_conn < 1:
                    opportunities.append(
                        {
                            "resource_type": "RDS",
                            "resource_id": db_id,
                            "resource_name": description or db_id,
                            "region": region,
                            "action": "release",
                            "reason": f"平均连接数{avg_conn:.1f},几乎无连接",
                            "estimated_savings": 200,  # 估算值
                            "current_spec": instance_class,
                            "priority": "high",
                        }
                    )

            db.close()

        except Exception as e:
            self.logger.error(f"分析RDS失败: {e}")

        return opportunities

    def _analyze_idle_eip(self, tenant_name: str) -> List[Dict]:
        """分析闲置EIP"""
        opportunities = []

        try:
            db = DatabaseFactory.create_adapter("sqlite", db_path="eip_monitoring_data.db")

            eips = db.query(
                """
                SELECT allocation_id, eip_address, region, monthly_cost
                FROM eip_instances
                WHERE (instance_id IS NULL OR instance_id = '')
            """
            )

            for eip in eips:
                allocation_id = eip.get("allocation_id") if isinstance(eip, dict) else eip[0]
                ip = eip.get("eip_address") if isinstance(eip, dict) else eip[1]
                region = eip.get("region") if isinstance(eip, dict) else eip[2]
                cost = eip.get("monthly_cost") if isinstance(eip, dict) else eip[3]

                opportunities.append(
                    {
                        "resource_type": "EIP",
                        "resource_id": allocation_id,
                        "resource_name": ip,
                        "region": region,
                        "action": "release",
                        "reason": "未绑定任何实例",
                        "estimated_savings": cost or 50,  # 默认估计50元/月
                        "priority": "high",
                    }
                )

            db.close()

        except Exception as e:
            self.logger.error(f"分析EIP失败: {e}")

        return opportunities

    def _analyze_idle_nat(self, tenant_name: str) -> List[Dict]:
        """分析闲置NAT网关"""
        opportunities = []

        try:
            db = DatabaseFactory.create_adapter("sqlite", db_path="nat_monitoring_data.db")

            nats = db.query(
                """
                SELECT nat_gateway_id, name, region
                FROM nat_gateways
                WHERE ip_count = 0 OR snat_count = 0
            """
            )

            for nat in nats:
                nat_id = nat.get("nat_gateway_id") if isinstance(nat, dict) else nat[0]
                name = nat.get("name") if isinstance(nat, dict) else nat[1]
                region = nat.get("region") if isinstance(nat, dict) else nat[2]

                opportunities.append(
                    {
                        "resource_type": "NAT",
                        "resource_id": nat_id,
                        "resource_name": name or nat_id,
                        "region": region,
                        "action": "release",
                        "reason": "未绑定EIP或无SNAT条目",
                        "estimated_savings": 150,  # NAT网关约150元/月
                        "priority": "high",
                    }
                )

            db.close()

        except Exception as e:
            self.logger.error(f"分析NAT失败: {e}")

        return opportunities

    def _analyze_idle_nas(self, tenant_name: str) -> List[Dict]:
        """分析闲置NAS文件系统"""
        opportunities = []

        try:
            db = DatabaseFactory.create_adapter("sqlite", db_path="nas_monitoring_data.db")

            nas_list = db.query(
                """
                SELECT file_system_id, description, region, monthly_cost
                FROM nas_file_systems
                WHERE mount_target_count = 0
            """
            )

            for nas in nas_list:
                fs_id = nas.get("file_system_id") if isinstance(nas, dict) else nas[0]
                description = nas.get("description") if isinstance(nas, dict) else nas[1]
                region = nas.get("region") if isinstance(nas, dict) else nas[2]
                cost = nas.get("monthly_cost") if isinstance(nas, dict) else nas[3]

                opportunities.append(
                    {
                        "resource_type": "NAS",
                        "resource_id": fs_id,
                        "resource_name": description or fs_id,
                        "region": region,
                        "action": "release",
                        "reason": "无挂载点",
                        "estimated_savings": cost or 30,
                        "priority": "medium",
                    }
                )

            db.close()

        except Exception as e:
            self.logger.error(f"分析NAS失败: {e}")

        return opportunities

    def _analyze_idle_disk(self, tenant_name: str) -> List[Dict]:
        """分析未挂载云盘"""
        opportunities = []

        try:
            db = DatabaseFactory.create_adapter("sqlite", db_path="disk_monitoring_data.db")

            disks = db.query(
                """
                SELECT disk_id, disk_name, region, monthly_cost
                FROM disk_instances
                WHERE status = 'Available'
            """
            )

            for disk in disks:
                disk_id = disk.get("disk_id") if isinstance(disk, dict) else disk[0]
                name = disk.get("disk_name") if isinstance(disk, dict) else disk[1]
                region = disk.get("region") if isinstance(disk, dict) else disk[2]
                cost = disk.get("monthly_cost") if isinstance(disk, dict) else disk[3]

                opportunities.append(
                    {
                        "resource_type": "Disk",
                        "resource_id": disk_id,
                        "resource_name": name or disk_id,
                        "region": region,
                        "action": "release",
                        "reason": "未挂载到任何实例",
                        "estimated_savings": cost or 20,
                        "priority": "medium",
                    }
                )

            db.close()

        except Exception as e:
            self.logger.error(f"分析Disk失败: {e}")

        return opportunities

    def calculate_roi(self, opportunities: List[Dict]) -> Dict:
        """计算ROI"""
        total_savings = sum(opp.get("estimated_savings", 0) for opp in opportunities)

        return {
            "total_opportunities": len(opportunities),
            "monthly_savings": round(total_savings, 2),
            "yearly_savings": round(total_savings * 12, 2),
            "by_action": self._group_by_action(opportunities),
            "by_resource_type": self._group_by_resource_type(opportunities),
            "by_priority": self._group_by_priority(opportunities),
        }

    def _group_by_action(self, opportunities: List[Dict]) -> Dict:
        """按操作类型分组"""
        grouped = {}
        for opp in opportunities:
            action = opp.get("action", "unknown")
            if action not in grouped:
                grouped[action] = {"count": 0, "savings": 0}
            grouped[action]["count"] += 1
            grouped[action]["savings"] += opp.get("estimated_savings", 0)
        return grouped

    def _group_by_resource_type(self, opportunities: List[Dict]) -> Dict:
        """按资源类型分组"""
        grouped = {}
        for opp in opportunities:
            resource_type = opp.get("resource_type", "unknown")
            if resource_type not in grouped:
                grouped[resource_type] = {"count": 0, "savings": 0}
            grouped[resource_type]["count"] += 1
            grouped[resource_type]["savings"] += opp.get("estimated_savings", 0)
        return grouped

    def _group_by_priority(self, opportunities: List[Dict]) -> Dict:
        """按优先级分组"""
        grouped = {"high": [], "medium": [], "low": []}
        for opp in opportunities:
            priority = opp.get("priority", "low")
            grouped[priority].append(opp)
        return {k: len(v) for k, v in grouped.items()}

    def generate_aliyun_cli_scripts(
        self, opportunities: List[Dict], output_file: str = "optimization_scripts.sh"
    ):
        """生成阿里云CLI脚本"""
        script_lines = [
            "#!/bin/bash",
            "# 阿里云资源优化脚本",
            f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "# 警告: 执行前请仔细检查,确保不会误删重要资源!",
            "",
            "set -e  # 遇到错误立即退出",
            "",
        ]

        for opp in opportunities:
            resource_type = opp.get("resource_type")
            resource_id = opp.get("resource_id")
            action = opp.get("action")
            region = opp.get("region", "cn-hangzhou")

            script_lines.append(f"# {resource_type}: {opp.get('resource_name')}")
            script_lines.append(f"# 原因: {opp.get('reason')}")
            script_lines.append(f"# 预计节省: ¥{opp.get('estimated_savings', 0):.2f}/月")

            if action == "release":
                if resource_type == "ECS":
                    script_lines.append(
                        f"# aliyun ecs DeleteInstance --RegionId {region} --InstanceId {resource_id} --Force true"
                    )
                elif resource_type == "RDS":
                    script_lines.append(
                        f"# aliyun rds DeleteDBInstance --RegionId {region} --DBInstanceId {resource_id}"
                    )
                elif resource_type == "EIP":
                    script_lines.append(
                        f"# aliyun vpc ReleaseEipAddress --RegionId {region} --AllocationId {resource_id}"
                    )
                elif resource_type == "NAT":
                    script_lines.append(
                        f"# aliyun vpc DeleteNatGateway --RegionId {region} --NatGatewayId {resource_id}"
                    )
                elif resource_type == "Disk":
                    script_lines.append(
                        f"# aliyun ecs DeleteDisk --RegionId {region} --DiskId {resource_id}"
                    )

            elif action == "downgrade":
                if resource_type == "ECS":
                    new_spec = opp.get("suggested_spec", "")
                    script_lines.append(
                        f"# aliyun ecs ModifyInstanceSpec --RegionId {region} --InstanceId {resource_id} --InstanceType {new_spec}"
                    )

            script_lines.append("")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(script_lines))

        self.logger.info(f"脚本已生成: {output_file}")

    def generate_optimization_report(
        self, tenant_name: str, opportunities: List[Dict], output_file: str
    ):
        """生成优化报告"""
        try:
            import pandas as pd

            # 计算ROI
            roi = self.calculate_roi(opportunities)

            # 生成DataFrame
            df = pd.DataFrame(opportunities)

            # 生成Excel
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                # 优化机会列表
                if not df.empty:
                    df.to_excel(writer, sheet_name="优化机会", index=False)

                # ROI总结
                roi_summary = pd.DataFrame(
                    [
                        {"指标": "优化机会总数", "值": roi["total_opportunities"]},
                        {"指标": "月度节省(元)", "值": roi["monthly_savings"]},
                        {"指标": "年度节省(元)", "值": roi["yearly_savings"]},
                    ]
                )
                roi_summary.to_excel(writer, sheet_name="ROI总结", index=False)

                # 按资源类型分组
                if roi["by_resource_type"]:
                    resource_df = pd.DataFrame(
                        [
                            {
                                "资源类型": k,
                                "数量": v["count"],
                                "月度节省(元)": round(v["savings"], 2),
                            }
                            for k, v in roi["by_resource_type"].items()
                        ]
                    )
                    resource_df.to_excel(writer, sheet_name="按资源类型", index=False)

            self.logger.info(f"优化报告已生成: {output_file}")

        except ImportError:
            self.logger.warning("pandas未安装")
        except Exception as e:
            self.logger.error(f"生成报告失败: {e}")


if __name__ == "__main__":
    # 测试
    engine = OptimizationEngine()
    print("优化引擎初始化完成")
