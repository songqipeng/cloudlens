#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudLens高级功能示例

演示自动修复、权限审计等高级功能
"""

from cloudlens.core.config import ConfigManager
from cloudlens.core.remediation import RemediationEngine, RemediationPlan, RemediationAction
from cloudlens.core.security import PermissionGuard


def example_1_remediation_dry_run():
    """示例1: 使用Dry-run模式测试修复计划"""
    print("=" * 60)
    print("示例1: 修复计划Dry-Run测试")
    print("=" * 60)
    
    # 创建dry-run引擎（安全模式，不会真正执行）
    engine = RemediationEngine(dry_run=True)
    
    # 创建修复计划列表
    plans = [
        RemediationPlan(
            action=RemediationAction.STOP_INSTANCE,
            resource_id="i-test001",
            resource_type="ECS",
            reason="实例闲置超过14天",
            metadata={
                "region": "cn-hangzhou",
                "instance_name": "test-server-001"
            }
        ),
        RemediationPlan(
            action=RemediationAction.DELETE_SNAPSHOT,
            resource_id="s-snapshot001",
            resource_type="Snapshot",
            reason="快照保留超过90天",
            metadata={
                "region": "cn-hangzhou",
                "snapshot_name": "auto-snapshot-001"
            }
        ),
        RemediationPlan(
            action=RemediationAction.DELETE_IDLE_DISK,
            resource_id="d-disk001",
            resource_type="Disk",
            reason="云盘未挂载超过30天",
            metadata={
                "region": "cn-shanghai",
                "disk_status": "Available"  # 未挂载状态
            }
        )
    ]
    
    # 执行批量修复（Dry-run）
    print("\n执行Dry-Run测试...\n")
    results = engine.execute_batch(plans)
    
    # 查看结果
    print(f"\n执行结果:")
    print(f"  总计: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")
    print(f"  Dry-run模式: {results['dry_run']}")


def example_2_permission_audit():
    """示例2: 审计RAM Policy"""
    print("\n" + "=" * 60)
    print("示例2: 审计RAM权限策略")
    print("=" * 60)
    
    # 示例策略文档1: 正常的只读策略
    readonly_policy = {
        "Version": "1",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "ecs:Describe*",
                "ecs:List*",
                "rds:Describe*",
                "vpc:Describe*"
            ],
            "Resource": ["*"]
        }]
    }
    
    print("\n检查策略1: 只读策略")
    risks = PermissionGuard.audit_policy(readonly_policy)
    
    if risks:
        print("⚠️  发现风险:")
        for risk in risks:
            print(f"  - {risk}")
    else:
        print("✅ 未发现明显风险")
    
    # 示例策略文档2: 含有高危权限
    dangerous_policy = {
        "Version": "1",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["*"],  # 完全权限！
                "Resource": ["*"]
            }
        ]
    }
    
    print("\n检查策略2: 完全权限策略")
    risks = PermissionGuard.audit_policy(dangerous_policy)
    
    if risks:
        print("⚠️  发现风险:")
        for risk in risks:
            print(f"  - {risk}")
    
    # 示例策略文档3: 含有危险操作
    mixed_policy = {
        "Version": "1",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "ecs:DescribeInstances",
                "ecs:DeleteInstance",  # 危险操作
                "ecs:StopInstance",    # 危险操作
                "rds:DescribeDBInstances"
            ],
            "Resource": ["acs:ecs:*:*:instance/*"]
        }]
    }
    
    print("\n检查策略3: 混合权限策略")
    risks = PermissionGuard.audit_policy(mixed_policy)
    
    if risks:
        print("⚠️  发现风险:")
        for risk in risks:
            print(f"  - {risk}")


def example_3_safe_action_check():
    """示例3: 检查API操作是否安全"""
    print("\n" + "=" * 60)
    print("示例3: 检查API操作安全性")
    print("=" * 60)
    
    # 测试一系列API操作
    api_actions = [
        "ecs:DescribeInstances",
        "ecs:ListInstances",
        "ecs:DeleteInstance",
        "ecs:StopInstance",
        "rds:DescribeDBInstances",
        "vpc:DescribeVpcs",
        "ecs:CreateInstance",
        "ecs:ModifyInstanceAttribute"
    ]
    
    print("\nAPI操作安全检查:\n")
    
    for action in api_actions:
        is_safe = PermissionGuard.is_action_safe(action)
        status = "✅ 安全" if is_safe else "❌ 危险"
        print(f"  {status} - {action}")


def example_4_create_remediation_plan():
    """示例4: 创建和导出修复计划"""
    print("\n" + "=" * 60)
    print("示例4: 创建修复计划")
    print("=" * 60)
    
    # 假设我们分析出了一些闲置资源
    idle_resources = [
        {"type": "ECS", "id": "i-001", "name": "idle-server-1", "reason": "CPU<5%, 14天"},
        {"type": "ECS", "id": "i-002", "name": "idle-server-2", "reason": "CPU<5%, 20天"},
        {"type": "Disk", "id": "d-001", "name": "unmounted-disk", "reason": "未挂载30天"}
    ]
    
    # 生成修复计划
    plans = []
    for resource in idle_resources:
        if resource["type"] == "ECS":
            plans.append(RemediationPlan(
                action=RemediationAction.STOP_INSTANCE,
                resource_id=resource["id"],
                resource_type=resource["type"],
                reason=resource["reason"],
                metadata={"resource_name": resource["name"]}
            ))
        elif resource["type"] == "Disk":
            plans.append(RemediationPlan(
                action=RemediationAction.DELETE_IDLE_DISK,
                resource_id=resource["id"],
                resource_type=resource["type"],
                reason=resource["reason"],
                metadata={
                    "resource_name": resource["name"],
                    "disk_status": "Available"
                }
            ))
    
    print(f"\n生成了 {len(plans)} 个修复计划:\n")
    for i, plan in enumerate(plans, 1):
        print(f"{i}. {plan.action.value}")
        print(f"   资源: {plan.resource_id}")
        print(f"   原因: {plan.reason}")
        print()
    
    # 在实际使用中，可以将这些计划保存到文件
    # 或提交给用户审批后再执行


def main():
    """主函数"""
    print("\n🚀 CloudLens 高级功能示例\n")
    
    try:
        example_1_remediation_dry_run()
        example_2_permission_audit()
        example_3_safe_action_check()
        example_4_create_remediation_plan()
        
        print("\n" + "=" * 60)
        print("✅ 所有示例执行完成")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
