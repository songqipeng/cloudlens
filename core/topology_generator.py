"""
Network Topology Generator
Generates Mermaid diagrams from cloud resources
"""

import logging
from typing import Dict, List

from models.resource import UnifiedResource

logger = logging.getLogger("TopologyGenerator")


class TopologyGenerator:

    @staticmethod
    def generate_mermaid(
        instances: List[UnifiedResource],
        vpcs: List[Dict],
        rds_instances: List[UnifiedResource] = None,
    ) -> str:
        """
        生成Mermaid格式的网络拓扑图

        Args:
            instances: ECS实例列表
            vpcs: VPC列表
            rds_instances: RDS实例列表(可选)

        Returns:
            Mermaid markdown string
        """
        lines = ["```mermaid", "graph TB"]

        # Group instances by VPC and AZ
        vpc_az_instances = {}
        for inst in instances:
            vpc_id = inst.vpc_id or "no-vpc"
            az = inst.zone or "unknown"
            key = (vpc_id, az)
            if key not in vpc_az_instances:
                vpc_az_instances[key] = []
            vpc_az_instances[key].append(inst)

        # Group RDS by VPC and AZ
        vpc_az_rds = {}
        if rds_instances:
            for rds in rds_instances:
                vpc_id = rds.vpc_id or "no-vpc"
                az = rds.zone or "unknown"
                key = (vpc_id, az)
                if key not in vpc_az_rds:
                    vpc_az_rds[key] = []
                vpc_az_rds[key].append(rds)

        # Create VPC subgraphs with AZ grouping
        for vpc in vpcs:
            vpc_id = vpc["id"]
            vpc_name = vpc["name"]

            lines.append(f"  subgraph {vpc_id}[\"{vpc_name}<br/>{vpc['cidr']}\"]")

            # Get all AZs in this VPC
            azs_in_vpc = set()
            for (v_id, az), _ in vpc_az_instances.items():
                if v_id == vpc_id:
                    azs_in_vpc.add(az)
            for (v_id, az), _ in vpc_az_rds.items():
                if v_id == vpc_id:
                    azs_in_vpc.add(az)

            # Group by AZ
            for az in sorted(azs_in_vpc):
                lines.append(f"    subgraph {vpc_id}_{az.replace('-', '_')}[\"AZ: {az}\"]")

                # Add ECS instances in this AZ
                key = (vpc_id, az)
                if key in vpc_az_instances:
                    for inst in vpc_az_instances[key]:
                        ip = (
                            inst.public_ips[0]
                            if inst.public_ips
                            else (inst.private_ips[0] if inst.private_ips else "N/A")
                        )
                        status_emoji = "🟢" if inst.status.value == "Running" else "🔴"
                        lines.append(
                            f'      {inst.id}["{status_emoji} {inst.name}<br/>{ip}<br/>{inst.spec}"]'
                        )

                # Add RDS instances in this AZ
                if key in vpc_az_rds:
                    for rds in vpc_az_rds[key]:
                        lines.append(f'      {rds.id}[("💾 {rds.name}<br/>{rds.spec}")]')

                lines.append("    end")

            lines.append("  end")

        lines.append("```")
        return "\n".join(lines)

    @staticmethod
    def generate_markdown_report(
        account_name: str,
        instances: List[UnifiedResource],
        vpcs: List[Dict],
        rds_instances: List[UnifiedResource] = None,
        redis_instances: List[UnifiedResource] = None,
        eips: List[Dict] = None,
    ) -> str:
        """
        生成完整的Markdown报告

        Returns:
            Markdown formatted report
        """
        lines = [f"# {account_name} 网络拓扑与资源清单", ""]

        # Summary
        lines.append("## 资源概览")
        lines.append(f"- **ECS实例**: {len(instances)}")
        lines.append(f"- **VPC**: {len(vpcs)}")
        if rds_instances:
            lines.append(f"- **RDS实例**: {len(rds_instances)}")
        if redis_instances:
            lines.append(f"- **Redis实例**: {len(redis_instances)}")
        if eips:
            lines.append(f"- **弹性公网IP**: {len(eips)}")
        lines.append("")

        # Network topology
        lines.append("## 网络拓扑")
        lines.append(TopologyGenerator.generate_mermaid(instances, vpcs, rds_instances))
        lines.append("")

        # Resource details
        lines.append("## 资源详情")

        # ECS Table
        if instances:
            lines.append("### ECS 实例")
            lines.append("| ID | 名称 | 状态 | 公网IP | 私网IP | 规格 | VPC |")
            lines.append("|---|---|---|---|---|---|---|")
            for inst in instances:
                pub_ip = inst.public_ips[0] if inst.public_ips else "-"
                priv_ip = inst.private_ips[0] if inst.private_ips else "-"
                lines.append(
                    f"| {inst.id} | {inst.name} | {inst.status.value} | {pub_ip} | {priv_ip} | {inst.spec} | {inst.vpc_id or '-'} |"
                )
            lines.append("")

        # RDS Table
        if rds_instances:
            lines.append("### RDS 实例")
            lines.append("| ID | 名称 | 状态 | 规格 | VPC |")
            lines.append("|---|---|---|---|---|")
            for rds in rds_instances:
                lines.append(
                    f"| {rds.id} | {rds.name} | {rds.status.value} | {rds.spec} | {rds.vpc_id or '-'} |"
                )
            lines.append("")

        return "\n".join(lines)
