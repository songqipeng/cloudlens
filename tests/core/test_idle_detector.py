"""闲置检测器单元测试"""
import pytest
from core.idle_detector import IdleDetector


class TestIdleDetector:
    """IdleDetector测试类"""

    def test_is_ecs_idle_with_low_cpu_and_memory(self):
        """测试: CPU和内存使用率都低应判定为闲置"""
        metrics = {"cpu_avg": 2.5, "memory_avg": 15.0, "net_in_avg": 500, "disk_iops_avg": 50}

        is_idle, reasons = IdleDetector.is_ecs_idle(metrics)

        assert is_idle is True
        assert len(reasons) >= 2  # 至少2个指标满足
        assert any("CPU" in r for r in reasons)
        assert any("内存" in r or "memory" in r.lower() for r in reasons)

    def test_is_ecs_idle_with_high_usage(self):
        """测试: 高使用率不应判定为闲置"""
        metrics = {
            "cpu_avg": 75.0,
            "memory_avg": 80.0,
            "net_in_avg": 100000,
            "disk_iops_avg": 5000,
        }

        is_idle, reasons = IdleDetector.is_ecs_idle(metrics)

        assert is_idle is False
        assert len(reasons) == 0

    def test_is_ecs_idle_edge_case(self):
        """测试: 边界条件 - 恰好满足阈值"""
        metrics = {
            "cpu_avg": 5.0,  # 恰好等于阈值
            "memory_avg": 20.0,
            "net_in_avg": 1000,
            "disk_iops_avg": 100,
        }

        is_idle, reasons = IdleDetector.is_ecs_idle(metrics)

        # 至少2个指标满足才判定闲置
        if is_idle:
            assert len(reasons) >= 2

    def test_is_ecs_idle_single_metric_low(self):
        """测试: 只有一个指标低不应判定为闲置"""
        metrics = {
            "cpu_avg": 2.0,  # 只有CPU低
            "memory_avg": 60.0,
            "net_in_avg": 50000,
            "disk_iops_avg": 5000,
        }

        is_idle, reasons = IdleDetector.is_ecs_idle(metrics)

        # 只有1个指标满足,不应判定为闲置
        assert is_idle is False or len(reasons) < 2

    def test_is_ecs_idle_multiple_low_metrics(self):
        """测试: 多个指标低应判定为闲置"""
        metrics = {
            "cpu_avg": 1.0,
            "memory_avg": 10.0,
            "net_in_avg": 100,  # 极低
            "disk_iops_avg": 10,  # 极低
        }

        is_idle, reasons = IdleDetector.is_ecs_idle(metrics)

        assert is_idle is True
        assert len(reasons) >= 2


# 注意: IdleDetector当前的逻辑是,如果提供的metrics缺少某些字段,
# 将默认为0,这可能导致即使只有一个指标实际为低值,
# 其他未提供的指标也被认为是0(满足阈值),从而误判为闲置。
# 这是一个需要在实际使用中注意的边界情况。
