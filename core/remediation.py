# -*- coding: utf-8 -*-
"""
Auto-Remediation Framework
自动化治理框架，支持 dry-run 模式确保安全
"""

from enum import Enum
from typing import Any, Callable, Dict, List


class RemediationAction(Enum):
    """修复动作类型"""

    STOP_INSTANCE = "stop_instance"
    DELETE_SNAPSHOT = "delete_snapshot"
    MODIFY_SECURITY_GROUP = "modify_security_group"
    RELEASE_EIP = "release_eip"
    DELETE_IDLE_DISK = "delete_idle_disk"


class RemediationPlan:
    """修复计划"""

    def __init__(
        self,
        action: RemediationAction,
        resource_id: str,
        resource_type: str,
        reason: str,
        metadata: Dict[str, Any] = None,
    ):
        self.action = action
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.reason = reason
        self.metadata = metadata or {}


class RemediationEngine:
    """自动化修复引擎"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.actions: Dict[RemediationAction, Callable] = {}
        self._register_actions()

    def _register_actions(self):
        """注册修复动作处理器"""
        self.actions[RemediationAction.STOP_INSTANCE] = self._stop_instance
        self.actions[RemediationAction.DELETE_SNAPSHOT] = self._delete_snapshot
        self.actions[RemediationAction.MODIFY_SECURITY_GROUP] = self._modify_security_group
        self.actions[RemediationAction.RELEASE_EIP] = self._release_eip
        self.actions[RemediationAction.DELETE_IDLE_DISK] = self._delete_idle_disk

    def execute_plan(self, plan: RemediationPlan) -> bool:
        """
        执行修复计划

        Args:
            plan: 修复计划

        Returns:
            是否成功
        """
        if self.dry_run:
            print(f"[DRY-RUN] Would execute: {plan.action.value} on {plan.resource_id}")
            print(f"  Reason: {plan.reason}")
            return True

        handler = self.actions.get(plan.action)
        if not handler:
            print(f"❌ Unknown action: {plan.action}")
            return False

        try:
            result = handler(plan)
            print(f"✅ {plan.action.value} executed successfully on {plan.resource_id}")
            return result
        except Exception as e:
            print(f"❌ Failed to execute {plan.action.value}: {e}")
            return False

    def execute_batch(self, plans: List[RemediationPlan]) -> Dict[str, Any]:
        """
        批量执行修复计划

        Returns:
            执行结果统计
        """
        results = {"total": len(plans), "success": 0, "failed": 0, "dry_run": self.dry_run}

        print(
            f"{'[DRY-RUN]' if self.dry_run else '[EXECUTE]'} Running {len(plans)} remediation tasks..."
        )

        for plan in plans:
            if self.execute_plan(plan):
                results["success"] += 1
            else:
                results["failed"] += 1

        return results

    # Action Handlers (实际执行逻辑)

    def _stop_instance(self, plan: RemediationPlan) -> bool:
        """停止实例"""
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkecs.request.v20140526.StopInstanceRequest import StopInstanceRequest

            # 从 metadata 获取必要信息
            region = plan.metadata.get("region", "cn-hangzhou")
            access_key = plan.metadata.get("access_key")
            secret_key = plan.metadata.get("secret_key")

            if not access_key or not secret_key:
                print(f"❌ 缺少认证信息")
                return False

            client = AcsClient(access_key, secret_key, region)
            request = StopInstanceRequest()
            request.set_InstanceId(plan.resource_id)
            request.set_ForceStop(False)  # 安全停止

            response = client.do_action_with_exception(request)
            print(f"✅ 实例 {plan.resource_id} 停止请求已发送")
            return True
        except Exception as e:
            print(f"❌ 停止实例失败: {e}")
            return False

    def _delete_snapshot(self, plan: RemediationPlan) -> bool:
        """删除快照"""
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkecs.request.v20140526.DeleteSnapshotRequest import DeleteSnapshotRequest

            region = plan.metadata.get("region", "cn-hangzhou")
            access_key = plan.metadata.get("access_key")
            secret_key = plan.metadata.get("secret_key")

            if not access_key or not secret_key:
                print(f"❌ 缺少认证信息")
                return False

            client = AcsClient(access_key, secret_key, region)
            request = DeleteSnapshotRequest()
            request.set_SnapshotId(plan.resource_id)

            response = client.do_action_with_exception(request)
            print(f"✅ 快照 {plan.resource_id} 已删除")
            return True
        except Exception as e:
            print(f"❌ 删除快照失败: {e}")
            return False

    def _modify_security_group(self, plan: RemediationPlan) -> bool:
        """修改安全组规则"""
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkecs.request.v20140526.RevokeSecurityGroupRequest import (
                RevokeSecurityGroupRequest,
            )

            region = plan.metadata.get("region", "cn-hangzhou")
            access_key = plan.metadata.get("access_key")
            secret_key = plan.metadata.get("secret_key")
            security_group_id = plan.metadata.get("security_group_id")
            ip_protocol = plan.metadata.get("ip_protocol", "tcp")
            port_range = plan.metadata.get("port_range", "22/22")
            source_cidr = plan.metadata.get("source_cidr", "0.0.0.0/0")

            if not all([access_key, secret_key, security_group_id]):
                print(f"❌ 缺少必要信息")
                return False

            client = AcsClient(access_key, secret_key, region)
            request = RevokeSecurityGroupRequest()
            request.set_SecurityGroupId(security_group_id)
            request.set_IpProtocol(ip_protocol)
            request.set_PortRange(port_range)
            request.set_SourceCidrIp(source_cidr)

            response = client.do_action_with_exception(request)
            print(f"✅ 安全组 {security_group_id} 规则已修改")
            return True
        except Exception as e:
            print(f"❌ 修改安全组失败: {e}")
            return False

    def _release_eip(self, plan: RemediationPlan) -> bool:
        """释放弹性公网 IP"""
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkvpc.request.v20160428.ReleaseEipAddressRequest import (
                ReleaseEipAddressRequest,
            )

            region = plan.metadata.get("region", "cn-hangzhou")
            access_key = plan.metadata.get("access_key")
            secret_key = plan.metadata.get("secret_key")
            allocation_id = plan.metadata.get("allocation_id", plan.resource_id)

            if not access_key or not secret_key:
                print(f"❌ 缺少认证信息")
                return False

            client = AcsClient(access_key, secret_key, region)
            request = ReleaseEipAddressRequest()
            request.set_AllocationId(allocation_id)

            response = client.do_action_with_exception(request)
            print(f"✅ EIP {allocation_id} 已释放")
            return True
        except Exception as e:
            print(f"❌ 释放EIP失败: {e}")
            return False

    def _delete_idle_disk(self, plan: RemediationPlan) -> bool:
        """删除闲置云盘"""
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkecs.request.v20140526.DeleteDiskRequest import DeleteDiskRequest

            region = plan.metadata.get("region", "cn-hangzhou")
            access_key = plan.metadata.get("access_key")
            secret_key = plan.metadata.get("secret_key")

            if not access_key or not secret_key:
                print(f"❌ 缺少认证信息")
                return False

            # 安全检查：只删除未挂载的云盘
            if plan.metadata.get("disk_status") == "In_use":
                print(f"❌ 云盘 {plan.resource_id} 正在使用中，拒绝删除")
                return False

            client = AcsClient(access_key, secret_key, region)
            request = DeleteDiskRequest()
            request.set_DiskId(plan.resource_id)

            response = client.do_action_with_exception(request)
            print(f"✅ 云盘 {plan.resource_id} 已删除")
            return True
        except Exception as e:
            print(f"❌ 删除云盘失败: {e}")
            return False
