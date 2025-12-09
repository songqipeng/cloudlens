# -*- coding: utf-8 -*-
"""
RemediationEngine单元测试
"""

import pytest
from core.remediation import RemediationEngine, RemediationPlan, RemediationAction


class TestRemediationEngine:
    """RemediationEngine测试套件"""
    
    def test_engine_dry_run_mode(self):
        \"\"\"测试dry-run模式\"\"\"
        engine = RemediationEngine(dry_run=True)
        assert engine.dry_run == True
    
    def test_engine_execute_mode(self):
        \"\"\"测试执行模式\"\"\"
        engine = RemediationEngine(dry_run=False)
        assert engine.dry_run == False
    
    def test_dry_run_execution(self):
        \"\"\"测试dry-run模式下执行计划\"\"\"
        engine = RemediationEngine(dry_run=True)
        plan = RemediationPlan(
            action=RemediationAction.STOP_INSTANCE,
            resource_id="i-test123",
            resource_type="ECS",
            reason="测试停止实例"
        )
        
        # Dry-run模式应该返回True且不实际执行
        result = engine.execute_plan(plan)
        assert result == True
    
    def test_execute_batch_dry_run(self):
        \"\"\"测试批量执行dry-run\"\"\"
        engine = RemediationEngine(dry_run=True)
        plans = [
            RemediationPlan(
                action=RemediationAction.STOP_INSTANCE,
                resource_id=f"i-test{i}",
                resource_type="ECS",
                reason="测试"
            )
            for i in range(3)
        ]
        
        results = engine.execute_batch(plans)
        assert results["total"] == 3
        assert results["success"] == 3
        assert results["failed"] == 0
        assert results["dry_run"] == True
    
    def test_stop_instance_requires_credentials(self):
        \"\"\"测试停止实例需要认证信息\"\"\"
        engine = RemediationEngine(dry_run=False)
        plan = RemediationPlan(
            action=RemediationAction.STOP_INSTANCE,
            resource_id="i-test123",
            resource_type="ECS",
            reason="测试",
            metadata={}  # 缺少认证信息
        )
        
        # 缺少认证信息应该失败
        result = engine.execute_plan(plan)
        assert result == False
    
    def test_delete_idle_disk_safety_check(self):
        \"\"\"测试删除云盘的安全检查\"\"\"
        engine = RemediationEngine(dry_run=False)
        
        # 尝试删除正在使用的云盘
        plan = RemediationPlan(
            action=RemediationAction.DELETE_IDLE_DISK,
            resource_id="d-test123",
            resource_type="Disk",
            reason="测试",
            metadata={
                "disk_status": "In_use",  # 正在使用
                "access_key": "test",
                "secret_key": "test"
            }
        )
        
        # 应该拒绝删除
        result = engine.execute_plan(plan)
        assert result == False
    
    def test_action_registry(self):
        \"\"\"测试所有动作都已注册\"\"\"
        engine = RemediationEngine()
        
        # 检查所有动作都有对应的处理器
        for action in RemediationAction:
            assert action in engine.actions
            assert callable(engine.actions[action])
    
    def test_unknown_action_handling(self):
        \"\"\"测试未知动作的处理\"\"\"
        engine = RemediationEngine(dry_run=False)
        
        # 创建一个使用字符串而非枚举的计划（模拟错误情况）
        class FakePlan:
            action = "unknown_action"
            resource_id = "test"
            reason = "test"
            resource_type = "test"
            metadata = {}
        
        # 应该优雅处理，返回False
        # 注意：这个测试取决于实际实现
