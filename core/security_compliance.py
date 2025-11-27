"""
Security Compliance Analyzer
安全合规检查
"""
import logging
from typing import List, Dict
from models.resource import UnifiedResource

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
    def suggest_security_improvements(exposed_count: int, unbound_eip_count: int) -> List[str]:
        """
        安全改进建议
        
        Returns:
            建议列表
        """
        suggestions = []
        
        if exposed_count > 0:
            suggestions.append(f"⚠️ 发现{exposed_count}个实例绑定了公网IP，建议:")
            suggestions.append("  • 评估是否真的需要公网访问")
            suggestions.append("  • 对必须暴露的服务，配置安全组白名单")
            suggestions.append("  • 考虑使用NAT网关或SLB替代直接绑定EIP")
        
        if unbound_eip_count > 0:
            suggestions.append(f"⚠️ 发现{unbound_eip_count}个未绑定的EIP，建议释放以节省成本")
        
        if not suggestions:
            suggestions.append("✅ 未发现明显的安全风险")
        
        return suggestions
    
    @staticmethod
    def check_encryption_status(resources: List[UnifiedResource]) -> Dict:
        """
        检查资源加密状态（简化版）
        
        Returns:
            加密统计
        """
        # TODO: 实际实现需要查询具体的加密配置
        # 这里只是示例框架
        return {
            "total": len(resources),
            "encrypted": 0,
            "unencrypted": len(resources),
            "note": "实际加密状态需要查询具体API"
        }
