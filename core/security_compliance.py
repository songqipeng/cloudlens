"""
Security Compliance Analyzer
安全合规检查
"""

import logging
from typing import Dict, List, Tuple

from models.resource import ResourceStatus, UnifiedResource

logger = logging.getLogger("SecurityAnalyzer")


class SecurityComplianceAnalyzer:
    """安全合规分析器"""

    @staticmethod
    def detect_public_exposure(instances: List[UnifiedResource]) -> List[Dict]:
        """
        检测公网暴露的资源（所有类型）

        Returns:
            暴露资源列表
        """
        exposed = []

        for inst in instances:
            if inst.public_ips:
                exposed.append(
                    {
                        "id": inst.id,
                        "name": inst.name,
                        "type": inst.resource_type.value,
                        "public_ips": inst.public_ips,
                        "region": inst.region,
                        "risk_level": "HIGH" if len(inst.public_ips) > 1 else "MEDIUM",
                    }
                )

        return exposed

    @staticmethod
    def analyze_eip_usage(eips: List[Dict]) -> Dict:
        """
        分析EIP使用情况

        Returns:
            EIP统计
        """
        total = len(eips)
        bound = sum(1 for eip in eips if eip.get("instance_id"))
        unbound = total - bound

        unbound_eips = [eip for eip in eips if not eip.get("instance_id")]

        return {
            "total": total,
            "bound": bound,
            "unbound": unbound,
            "unbound_rate": round(unbound / total * 100, 2) if total > 0 else 0,
            "unbound_eips": unbound_eips,
        }

    @staticmethod
    def check_stopped_instances(instances: List[UnifiedResource]) -> List[Dict]:
        """检查长期停止的实例（仍产生磁盘费用）"""
        stopped = []

        for inst in instances:
            # Handle both dict and object
            if isinstance(inst, dict):
                 status = inst.get("status")
                 inst_id = inst.get("id")
                 name = inst.get("name")
                 region = inst.get("region")
                 created_time = inst.get("created_time")
            else:
                 status = inst.status
                 inst_id = inst.id
                 name = inst.name
                 region = inst.region
                 created_time = inst.created_time

            # Check for stopped status (handle Enum or string)
            is_stopped = False
            if hasattr(status, "value"): # ResourceStatus enum
                is_stopped = (status == ResourceStatus.STOPPED)
            else:
                is_stopped = (str(status).lower() == "stopped")

            if is_stopped:
                # Format created_time
                created_time_str = "N/A"
                if created_time:
                    if isinstance(created_time, str):
                        created_time_str = created_time
                    elif hasattr(created_time, "strftime"):
                        created_time_str = created_time.strftime("%Y-%m-%d")

                stopped.append(
                    {
                        "id": inst_id,
                        "name": name,
                        "region": region,
                        "status": "Stopped",
                        "created_time": created_time_str,
                    }
                )    
        return stopped

    @staticmethod
    def check_missing_tags(instances: List[UnifiedResource]) -> Tuple[float, List[Dict]]:
        """检查缺失标签的资源（影响成本分摊和管理）"""
        total = len(instances)
        no_tags = []

        for inst in instances:
            # 假设 raw_data 中有 Tags 字段
            tags = inst.raw_data.get("Tags", {}).get("Tag", []) if inst.raw_data else []
            if not tags or len(tags) == 0:
                no_tags.append(
                    {
                        "id": inst.id,
                        "name": inst.name,
                        "type": inst.resource_type.value,
                        "region": inst.region,
                    }
                )

        coverage_rate = round((total - len(no_tags)) / total * 100, 2) if total > 0 else 0
        return coverage_rate, no_tags

    @staticmethod
    def check_disk_encryption(instances: List[UnifiedResource]) -> Dict:
        """检查磁盘加密状态"""
        total = len(instances)
        encrypted_count = 0
        unencrypted = []

        for inst in instances:
            # 检查系统盘加密（仅示例，需要实际 API 数据）
            if inst.raw_data:
                encrypted = inst.raw_data.get("SystemDisk", {}).get("Encrypted", False)
                if encrypted:
                    encrypted_count += 1
                else:
                    unencrypted.append({"id": inst.id, "name": inst.name, "region": inst.region})

        return {
            "total": total,
            "encrypted": encrypted_count,
            "unencrypted_count": len(unencrypted),
            "encryption_rate": round(encrypted_count / total * 100, 2) if total > 0 else 0,
            "unencrypted_instances": unencrypted[:5],  # 只返回前5个
        }

    @staticmethod
    def check_preemptible_instances(instances: List[UnifiedResource]) -> List[Dict]:
        """检查抢占式实例（生产环境不建议使用）"""
        preemptible = []
        for inst in instances:
            if inst.raw_data:
                instance_charge_type = inst.raw_data.get("InstanceChargeType", "")
                if instance_charge_type == "PreemptibleInstance":
                    preemptible.append(
                        {
                            "id": inst.id,
                            "name": inst.name,
                            "region": inst.region,
                            "type": instance_charge_type,
                        }
                    )
        return preemptible

    @staticmethod
    def suggest_security_improvements(security_summary: Dict, locale: str = "zh") -> List[str]:
        """
        综合安全改进建议

        Args:
            security_summary: 安全摘要数据
            locale: 语言代码 ("zh" 或 "en")

        Returns:
            建议列表
        """
        try:
            from web.backend.i18n import get_translation
        except ImportError:
            # 如果无法导入，使用默认中文
            locale = "zh"
            get_translation = lambda lang, key, **kwargs: key
        
        suggestions = []

        exposed_count = security_summary.get("exposed_count", 0)
        if exposed_count > 0:
            if locale == "en":
                suggestions.append(f"⚠️ Public Exposure: Found {exposed_count} instances exposed to the public network")
                suggestions.append("  • Evaluate if public network access is really needed")
                suggestions.append("  • Configure security group whitelist to limit access sources")
                suggestions.append("  • Consider using NAT gateway or SLB")
            else:
                suggestions.append(f"⚠️ 公网暴露: 发现 {exposed_count} 个实例暴露在公网")
                suggestions.append("  • 评估是否真的需要公网访问")
                suggestions.append("  • 配置安全组白名单限制访问源")
                suggestions.append("  • 考虑使用 NAT 网关或 SLB")

        unbound_eip = security_summary.get("unbound_eip", 0)
        if unbound_eip > 0:
            if locale == "en":
                suggestions.append(f"💰 Unbound EIP: {unbound_eip} EIPs unused, recommend releasing")
            else:
                suggestions.append(f"💰 未绑定EIP: {unbound_eip} 个 EIP 未使用，建议释放")

        stopped_count = security_summary.get("stopped_count", 0)
        if stopped_count > 0:
            if locale == "en":
                suggestions.append(f"⏸️ Stopped Instances: {stopped_count} instances long-term stopped, still incurring disk costs")
            else:
                suggestions.append(f"⏸️ 停止实例: {stopped_count} 个实例长期停止，仍产生磁盘费用")

        tag_coverage = security_summary.get("tag_coverage_rate", 100)
        if tag_coverage < 80:
            if locale == "en":
                suggestions.append(f"🏷️ Tag Coverage: Only {tag_coverage}%, recommend improving resource tags")
            else:
                suggestions.append(f"🏷️ 标签覆盖率: 仅 {tag_coverage}%，建议完善资源标签")

        encryption_rate = security_summary.get("encryption_rate", 100)
        if encryption_rate < 50:
            if locale == "en":
                suggestions.append(f"🔒 Disk Encryption: Only {encryption_rate}% instances have encryption enabled")
            else:
                suggestions.append(f"🔒 磁盘加密: 仅 {encryption_rate}% 实例启用加密")

        preemptible_count = security_summary.get("preemptible_count", 0)
        if preemptible_count > 0:
            if locale == "en":
                suggestions.append(f"⚡ Preemptible Instances: {preemptible_count} instances, not recommended for production")
            else:
                suggestions.append(f"⚡ 抢占式实例: {preemptible_count} 个，生产环境不建议使用")

        if not suggestions:
            if locale == "en":
                suggestions.append("✅ No obvious security and compliance risks found")
            else:
                suggestions.append("✅ 未发现明显的安全和合规风险")

        return suggestions
