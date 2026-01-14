"""
自动修复引擎
支持批量修复资源问题,带干运行模式
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class RemediationEngine:
    """自动修复引擎"""

    def __init__(self, audit_dir: str = "./data/remediation"):
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_file = self.audit_dir / "audit.log"

    def remediate_tags(
        self,
        resources: List,
        default_tags: Dict[str, str],
        dry_run: bool = True,
        provider=None,
    ) -> Dict:
        """
        自动为资源打标签
        
        Args:
            resources: 资源列表
            default_tags: 默认标签
            dry_run: 是否干运行
            provider: Provider实例
            
        Returns:
            修复结果统计
        """
        untagged_resources = []
        incomplete_tags = []

        # 识别需要打标签的资源
        for resource in resources:
            if not hasattr(resource, "tags") or not resource.tags:
                untagged_resources.append(resource)
            elif not all(k in resource.tags for k in ["env", "owner"]):
                incomplete_tags.append(resource)

        total_to_fix = len(untagged_resources) + len(incomplete_tags)

        if total_to_fix == 0:
            return {
                "dry_run": dry_run,
                "action": "tag",
                "total": 0,
                "success": 0,
                "skipped": 0,
                "message": "所有资源标签完整",
            }

        if dry_run:
            # 干运行: 仅预览
            preview = []
            
            for resource in untagged_resources[:10]:  # 只显示前10个
                preview.append({
                    "resource_id": resource.id,
                    "resource_type": resource.resource_type.value if hasattr(resource, 'resource_type') else "unknown",
                    "action": "add_tags",
                    "tags": default_tags,
                })

            return {
                "dry_run": True,
                "action": "tag",
                "total": total_to_fix,
                "preview": preview,
                "message": f"将为{total_to_fix}个资源添加标签 (干运行模式,未实际执行)",
            }

        # 实际执行
        success_count = 0
        failed = []

        for resource in untagged_resources + incomplete_tags:
            try:
                # 调用Provider API添加标签
                if provider and hasattr(provider, "add_tags"):
                    # 合并现有标签和默认标签
                    new_tags = {**default_tags}
                    if hasattr(resource, "tags") and resource.tags:
                        new_tags = {**resource.tags, **default_tags}

                    provider.add_tags(resource.id, new_tags)
                    success_count += 1
                    
                    # 记录审计日志
                    self._log_remediation(
                        action="add_tags",
                        resource_id=resource.id,
                        resource_type=getattr(resource, 'resource_type', 'unknown'),
                        details={"tags": new_tags},
                        status="success",
                    )
                else:
                    # Provider不支持
                    failed.append({
                        "resource_id": resource.id,
                        "error": "Provider不支持add_tags方法",
                    })

            except Exception as e:
                logger.error(f"Failed to tag {resource.id}: {e}")
                failed.append({"resource_id": resource.id, "error": str(e)})
                
                self._log_remediation(
                    action="add_tags",
                    resource_id=resource.id,
                    resource_type=getattr(resource, 'resource_type', 'unknown'),
                    details={"error": str(e)},
                    status="failed",
                )

        return {
            "dry_run": False,
            "action": "tag",
            "total": total_to_fix,
            "success": success_count,
            "failed": len(failed),
            "failed_details": failed[:10],  # 只返回前10个失败
        }

    def remediate_security_groups(
        self,
        resources: List,
        allowed_cidrs: List[str],
        dry_run: bool = True,
        provider=None,
    ) -> Dict:
        """
        修复不安全的安全组规则
        
        Args:
            resources: 资源列表
            allowed_cidrs: 允许的CIDR列表
            dry_run: 是否干运行
            provider: Provider实例
        """
        # 简化实现
        risky_resources = []

        # 检测风险资源 (实际需要查询安全组规则)
        for resource in resources:
            if hasattr(resource, "public_ips") and resource.public_ips:
                risky_resources.append(resource)

        if dry_run:
            return {
                "dry_run": True,
                "action": "security_group",
                "total": len(risky_resources),
                "message": f"发现{len(risky_resources)}个可能的风险资源 (干运行模式)",
            }

        # 实际修复需要实现具体逻辑
        return {
            "dry_run": False,
            "action": "security_group",
            "total": 0,
            "success": 0,
            "message": "安全组修复功能开发中",
        }

    def remediate_encryption(
        self,
        resources: List,
        dry_run: bool = True,
        provider=None,
    ) -> Dict:
        """
        启用磁盘加密
        
        注意: 现有磁盘无法直接启用加密,只能针对新磁盘
        """
        unencrypted = []

        for resource in resources:
            if hasattr(resource, 'raw_data'):
                encrypted = resource.raw_data.get('Encrypted', False)
                if not encrypted:
                    unencrypted.append(resource)

        if dry_run:
            return {
                "dry_run": True,
                "action": "encryption",
                "total": len(unencrypted),
                "message": f"发现{len(unencrypted)}个未加密资源 (现有磁盘无法直接启用加密)",
            }

        return {
            "dry_run": False,
            "action": "encryption",
            "total": 0,
            "message": "加密修复功能开发中",
        }

    def _log_remediation(
        self,
        action: str,
        resource_id: str,
        resource_type: str,
        details: Dict,
        status: str,
    ):
        """记录修复审计日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "resource_id": resource_id,
            "resource_type": str(resource_type),
            "details": details,
            "status": status,
        }

        try:
            with open(self.audit_log_file, "a") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def get_audit_history(self, limit: int = 50) -> List[Dict]:
        """获取审计历史"""
        if not self.audit_log_file.exists():
            return []

        history = []
        try:
            with open(self.audit_log_file, "r") as f:
                lines = f.readlines()
                # 取最后N条
                for line in lines[-limit:]:
                    history.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to read audit log: {e}")

        return history


class RemediationPolicy:
    """修复策略定义"""

    def __init__(self, name: str, resource_type: str, condition: str, action: Dict):
        self.name = name
        self.resource_type = resource_type
        self.condition = condition
        self.action = action

    def matches(self, resource) -> bool:
        """检查资源是否匹配策略条件"""
        # 简化实现: 实际应支持更复杂的条件表达式
        if self.resource_type != "*" and hasattr(resource, "resource_type"):
            if resource.resource_type.value != self.resource_type:
                return False

        # 评估条件
        # 这里需要一个表达式解析器
        return True

    @classmethod
    def from_yaml(cls, config: Dict):
        """从YAML配置创建策略"""
        return cls(
            name=config["name"],
            resource_type=config.get("resource", "*"),
            condition=config.get("condition", "true"),
            action=config.get("action", {}),
        )
