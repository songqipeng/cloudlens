import logging
from typing import Dict, List

logger = logging.getLogger("PermissionGuard")


class PermissionGuard:
    """
    权限卫士
    负责审计云账号权限，确保只读原则
    """

    # 危险动词黑名单 (各云厂商通用)
    DANGEROUS_ACTIONS = [
        "Delete",
        "Update",
        "Create",
        "Modify",
        "Reboot",
        "Stop",
        "Start",
        "Terminate",
        "Release",
        "Authorize",
        "Revoke",
    ]

    # 允许的动词白名单
    ALLOWED_ACTIONS = ["Describe", "List", "Get", "Query", "Check", "Lookup"]

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
        支持阿里云RAM Policy格式
        """
        risks = []

        try:
            # 解析 Policy Document
            if "Statement" not in policy_document:
                return ["无效的Policy格式：缺少Statement字段"]

            statements = policy_document["Statement"]
            if not isinstance(statements, list):
                statements = [statements]

            for idx, statement in enumerate(statements):
                effect = statement.get("Effect", "")
                action = statement.get("Action", [])

                # 确保action是列表
                if isinstance(action, str):
                    action = [action]

                # 只检查Allow类型的Statement
                if effect != "Allow":
                    continue

                # 检查每个Action
                for act in action:
                    # 检查通配符 (最高危险)
                    if act == "*" or act == "*:*":
                        risks.append(f"Statement[{idx}]: 发现完全权限 '*' - 极度危险！")
                        continue

                    # 检查服务级通配符
                    if act.endswith(":*"):
                        service = act.split(":")[0]
                        risks.append(f"Statement[{idx}]: 发现服务完全权限 '{act}' - 高风险")
                        continue

                    # 检查危险动作
                    for dangerous in PermissionGuard.DANGEROUS_ACTIONS:
                        if dangerous in act:
                            risks.append(f"Statement[{idx}]: 发现危险操作 '{act}' - 中风险")
                            break

            # 检查Resource字段
            for idx, statement in enumerate(statements):
                resource = statement.get("Resource", [])
                if isinstance(resource, str):
                    resource = [resource]

                for res in resource:
                    if res == "*":
                        risks.append(f"Statement[{idx}]: Resource为'*'（所有资源） - 风险提升")

        except Exception as e:
            logger.error(f"解析Policy失败: {e}")
            risks.append(f"Policy解析错误: {str(e)}")

        return risks
