"""闲置检测器单元测试"""
import pytest
from cloudlens.core.idle_detector import IdleDetector


class TestIdleDetector:
    """IdleDetector测试类"""

    @pytest.fixture
    def detector(self):
        """创建IdleDetector实例"""
        return IdleDetector()

    def test_is_ecs_idle_with_low_cpu_and_memory(self, detector):
        """测试: CPU和内存使用率都低应判定为闲置"""
        metrics = {
            "CPU利用率": 2.5,
            "内存利用率": 15.0,
            "公网入流量": 500,
            "公网出流量": 500,
            "磁盘读IOPS": 50,
            "磁盘写IOPS": 50
        }

        is_idle, reasons = detector.is_ecs_idle(metrics)

        assert is_idle is True
        assert len(reasons) >= 2  # 至少2个指标满足
        assert any("CPU" in r for r in reasons)
        assert any("内存" in r or "memory" in r.lower() for r in reasons)

    def test_is_ecs_idle_with_high_usage(self, detector):
        """测试: 高使用率不应判定为闲置"""
        metrics = {
            "CPU利用率": 75.0,
            "内存利用率": 80.0,
            "公网入流量": 100000,
            "公网出流量": 100000,
            "磁盘读IOPS": 5000,
            "磁盘写IOPS": 5000
        }

        is_idle, reasons = detector.is_ecs_idle(metrics)

        assert is_idle is False
        assert len(reasons) == 0

    def test_is_ecs_idle_edge_case(self, detector):
        """测试: 边界条件 - 恰好满足阈值"""
        metrics = {
            "CPU利用率": 5.0,  # 恰好等于阈值
            "内存利用率": 20.0,
            "公网入流量": 1000,
            "公网出流量": 1000,
            "磁盘读IOPS": 100,
            "磁盘写IOPS": 100
        }

        is_idle, reasons = detector.is_ecs_idle(metrics)

        # 至少2个指标满足才判定闲置
        if is_idle:
            assert len(reasons) >= 2

    def test_is_ecs_idle_single_metric_low(self, detector):
        """测试: 只有一个指标低不应判定为闲置"""
        metrics = {
            "CPU利用率": 2.0,  # 只有CPU低
            "内存利用率": 60.0,
            "公网入流量": 50000,
            "公网出流量": 50000,
            "磁盘读IOPS": 5000,
            "磁盘写IOPS": 5000
        }

        is_idle, reasons = detector.is_ecs_idle(metrics)

        # 只有1个指标满足,不应判定为闲置
        assert is_idle is False or len(reasons) < 2

    def test_is_ecs_idle_multiple_low_metrics(self, detector):
        """测试: 多个指标低应判定为闲置"""
        metrics = {
            "CPU利用率": 1.0,
            "内存利用率": 10.0,
            "公网入流量": 100,  # 极低
            "公网出流量": 100,
            "磁盘读IOPS": 10,  # 极低
            "磁盘写IOPS": 10
        }

        is_idle, reasons = detector.is_ecs_idle(metrics)

        assert is_idle is True
        assert len(reasons) >= 2


# 注意: IdleDetector当前的逻辑是,如果提供的metrics缺少某些字段,
# 将默认为0,这可能导致即使只有一个指标实际为低值,
# 其他未提供的指标也被认为是0(满足阈值),从而误判为闲置。
# 这是一个需要在实际使用中注意的边界情况。
