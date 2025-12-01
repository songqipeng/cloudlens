"""
Security Compliance Analyzer
安全合规检查
"""
import logging
from typing import List, Dict, Tuple
from models.resource import UnifiedResource, ResourceStatus

logger = logging.getLogger("SecurityAnalyzer")

class SecurityComplianceAnalyzer:
    """安全合规分析器"""
    
    @staticmethod
    def detect_public_exposure(instances: List[UnifiedResource]) -> List[Dict]:
        """
        检测公网暴露的资源
        
        Returns:
            暴露资源列表
        """
        exposed = []
        
        for inst in instances:
            if inst.public_ips:
                exposed.append({
                    "id": inst.id,
                    "name": inst.name,
                    "type": inst.resource_type.value,
                    "public_ips": inst.public_ips,
                    "region": inst.region,
                    "risk_level": "HIGH" if len(inst.public_ips) > 1 else "MEDIUM"
                })
        
        return exposed
    
    @staticmethod
    def analyze_eip_usage(eips: List[Dict]) -> Dict:
        """
        分析EIP使用情况
        
        Returns:
            EIP统计
        """
        total = len(eips)
        bound = sum(1 for eip in eips if eip.get('instance_id'))
        unbound = total - bound
        
        unbound_eips = [eip for eip in eips if not eip.get('instance_id')]
        
        return {
            "total": total,
            "bound": bound,
            "unbound": unbound,
            "unbound_rate": round(unbound / total * 100, 2) if total > 0 else 0,
            "unbound_eips": unbound_eips
        }
    
    @staticmethod
    def check_stopped_instances(instances: List[UnifiedResource]) -> List[Dict]:
        """检查长期停止的实例（仍产生磁盘费用）"""
        stopped = []
        for inst in instances:
            if inst.status == ResourceStatus.STOPPED:
                stopped.append({
                    "id": inst.id,
                    "name": inst.name,
                    "region": inst.region,
                    "status": inst.status.value
                })
        return stopped
    
    @staticmethod
    def check_missing_tags(instances: List[UnifiedResource]) -> Tuple[int, List[Dict]]:
        """检查缺失标签的资源（影响成本分摊和管理）"""
        total = len(instances)
        no_tags = []
        
        for inst in instances:
            # 假设 raw_data 中有 Tags 字段
            tags = inst.raw_data.get('Tags', {}).get('Tag', []) if inst.raw_data else []
            if not tags or len(tags) == 0:
                no_tags.append({
                    "id": inst.id,
                    "name": inst.name,
                    "region": inst.region
                })
        
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
                encrypted = inst.raw_data.get('SystemDisk', {}).get('Encrypted', False)
                if encrypted:
                    encrypted_count += 1
                else:
                    unencrypted.append({
                        "id": inst.id,
                        "name": inst.name,
                        "region": inst.region
                    })
        
        return {
            "total": total,
            "encrypted": encrypted_count,
            "unencrypted_count": len(unencrypted),
            "encryption_rate": round(encrypted_count / total * 100, 2) if total > 0 else 0,
            "unencrypted_instances": unencrypted[:5]  # 只返回前5个
        }
    
    @staticmethod
    def check_preemptible_instances(instances: List[UnifiedResource]) -> List[Dict]:
        """检查抢占式实例（生产环境不建议使用）"""
        preemptible = []
        for inst in instances:
            if inst.raw_data:
                instance_charge_type = inst.raw_data.get('InstanceChargeType', '')
                if instance_charge_type == 'PreemptibleInstance':
                    preemptible.append({
                        "id": inst.id,
                        "name": inst.name,
                        "region": inst.region,
                        "type": instance_charge_type
                    })
        return preemptible
    
    @staticmethod
    def suggest_security_improvements(security_summary: Dict) -> List[str]:
        """
        综合安全改进建议
        
        Returns:
            建议列表
        """
        suggestions = []
        
        exposed_count = security_summary.get('exposed_count', 0)
        if exposed_count > 0:
            suggestions.append(f"⚠️ 公网暴露: 发现 {exposed_count} 个实例暴露在公网")
            suggestions.append("  • 评估是否真的需要公网访问")
            suggestions.append("  • 配置安全组白名单限制访问源")
            suggestions.append("  • 考虑使用 NAT 网关或 SLB")
        
        unbound_eip = security_summary.get('unbound_eip', 0)
        if unbound_eip > 0:
            suggestions.append(f"💰 未绑定EIP: {unbound_eip} 个 EIP 未使用，建议释放")
        
        stopped_count = security_summary.get('stopped_count', 0)
        if stopped_count > 0:
            suggestions.append(f"⏸️ 停止实例: {stopped_count} 个实例长期停止，仍产生磁盘费用")
        
        tag_coverage = security_summary.get('tag_coverage_rate', 100)
        if tag_coverage < 80:
            suggestions.append(f"🏷️ 标签覆盖率: 仅 {tag_coverage}%，建议完善资源标签")
        
        encryption_rate = security_summary.get('encryption_rate', 100)
        if encryption_rate < 50:
            suggestions.append(f"🔒 磁盘加密: 仅 {encryption_rate}% 实例启用加密")
        
        preemptible_count = security_summary.get('preemptible_count', 0)
        if preemptible_count > 0:
            suggestions.append(f"⚡ 抢占式实例: {preemptible_count} 个，生产环境不建议使用")
        
        if not suggestions:
            suggestions.append("✅ 未发现明显的安全和合规风险")
        
        return suggestions

