from typing import List, Dict
import logging

logger = logging.getLogger("PermissionGuard")

class PermissionGuard:
    """
    权限卫士
    负责审计云账号权限，确保只读原则
    """
    
    # 危险动词黑名单 (各云厂商通用)
    DANGEROUS_ACTIONS = [
        "Delete", "Update", "Create", "Modify", "Reboot", "Stop", "Start", 
        "Terminate", "Release", "Authorize", "Revoke"
    ]
    
    # 允许的动词白名单
    ALLOWED_ACTIONS = [
        "Describe", "List", "Get", "Query", "Check", "Lookup"
    ]

    @staticmethod
    def is_action_safe(action_name: str) -> bool:
        """
        检查API Action是否安全
        :param action_name: e.g., "ecs:DescribeInstances" or "ec2:DescribeInstances"
        """
        # 1. 检查白名单
        for allowed in PermissionGuard.ALLOWED_ACTIONS:
            if allowed in action_name:
                return True
                
        # 2. 检查黑名单 (Double Check)
        for dangerous in PermissionGuard.DANGEROUS_ACTIONS:
            if dangerous in action_name:
                logger.warning(f"⚠️ Detected dangerous action: {action_name}")
                return False
                
        # 默认策略: 未知即拒绝 (Strict Mode)
        # 但为了兼容性，暂时对未在黑名单且含 Get/List 的放行
        return False

    @staticmethod
    def audit_policy(policy_document: Dict) -> List[str]:
        """
        审计RAM/IAM Policy文档，返回风险项列表
        (具体实现需根据各云厂商Policy结构适配)
        """
        risks = []
        # TODO: 解析 JSON Policy 并匹配 Action
        return risks
