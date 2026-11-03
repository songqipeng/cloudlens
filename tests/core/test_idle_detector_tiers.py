"""ECS 闲置分级判定单元测试（规则参考阿里云 alibabacloud-finops-inspect）"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cloudlens.core.idle_detector import (
    LEVEL_CRITICAL_IDLE,
    LEVEL_EXEMPT,
    LEVEL_LOW_UTILIZATION,
    LEVEL_NO_DATA,
    LEVEL_NORMAL,
    LEVEL_OBSERVING,
    LEVEL_STOPPED_PREPAID,
    IdleDetector,
)
from cloudlens.core.monitor import CloudMonitor
from cloudlens.core.rules_manager import RulesManager

NOW = datetime(2026, 10, 8, 12, 0)
OLD = NOW - timedelta(days=90)


def _metrics(cpu=None, memory=None, network=None):
    return {
        "avg_cpu": cpu,
        "avg_memory": memory,
        "avg_intranet_in": network,
        "avg_intranet_out": network,
        "avg_internet_in": None,
        "avg_internet_out": None,
    }


@pytest.fixture
def detector():
    return IdleDetector(RulesManager.DEFAULT_RULES)


def _classify(detector, metrics, **kwargs):
    kwargs.setdefault("status", "Running")
    kwargs.setdefault("charge_type", "PrePaid")
    kwargs.setdefault("created_time", OLD)
    return detector.classify_ecs(metrics, now=NOW, **kwargs)


class TestTiers:
    def test_critical_idle_when_all_low(self, detector):
        result = _classify(detector, _metrics(cpu=2, memory=5, network=10_000))
        assert result.level == LEVEL_CRITICAL_IDLE
        assert result.priority == "P1"
        assert result.is_idle

    def test_low_utilization_when_cpu_low_only(self, detector):
        result = _classify(detector, _metrics(cpu=8, memory=30, network=100_000))
        assert result.level == LEVEL_LOW_UTILIZATION
        assert result.priority == "P2"
        assert any("CPU" in r for r in result.reasons)

    def test_low_utilization_when_memory_low_only(self, detector):
        result = _classify(detector, _metrics(cpu=40, memory=15, network=100_000))
        assert result.level == LEVEL_LOW_UTILIZATION
        assert any("内存" in r for r in result.reasons)

    def test_normal_when_usage_healthy(self, detector):
        result = _classify(detector, _metrics(cpu=25, memory=40, network=500_000))
        assert result.level == LEVEL_NORMAL
        assert not result.is_idle

    def test_high_network_blocks_critical(self, detector):
        result = _classify(detector, _metrics(cpu=2, memory=5, network=200_000))
        assert result.level == LEVEL_LOW_UTILIZATION

    def test_no_memory_agent_judges_on_cpu_and_network(self, detector):
        result = _classify(detector, _metrics(cpu=2, memory=None, network=10_000))
        assert result.level == LEVEL_CRITICAL_IDLE
        assert any("未安装云监控插件" in r for r in result.reasons)

    def test_no_memory_agent_cpu_healthy_is_normal(self, detector):
        result = _classify(detector, _metrics(cpu=30, memory=None, network=10_000))
        assert result.level == LEVEL_NORMAL

    def test_missing_cpu_is_not_idle(self, detector):
        """无监控数据时不能误判为闲置（旧逻辑会把缺失值当 0）"""
        result = _classify(detector, {})
        assert result.level == LEVEL_NO_DATA
        assert not result.is_idle

    def test_missing_network_cannot_be_critical(self, detector):
        result = _classify(detector, _metrics(cpu=1, memory=5, network=None))
        assert result.level == LEVEL_LOW_UTILIZATION


class TestBillingAndLifecycle:
    def test_stopped_prepaid_is_p1(self, detector):
        result = _classify(detector, {}, status="Stopped", charge_type="PrePaid")
        assert result.level == LEVEL_STOPPED_PREPAID
        assert result.priority == "P1"
        assert result.is_idle

    def test_stopped_postpaid_is_skipped(self, detector):
        result = _classify(detector, {}, status="Stopped", charge_type="PostPaid")
        assert result.level == LEVEL_NORMAL
        assert not result.is_idle

    def test_new_instance_in_observation_window(self, detector):
        result = _classify(
            detector, _metrics(cpu=1, memory=1, network=0), created_time=NOW - timedelta(days=3)
        )
        assert result.level == LEVEL_OBSERVING
        assert not result.is_idle

    def test_long_running_postpaid_gets_billing_advice(self, detector):
        result = _classify(detector, _metrics(cpu=8, memory=30, network=100_000), charge_type="PostPaid")
        assert result.is_idle
        assert result.billing_advice and "包年包月" in result.billing_advice

    def test_prepaid_has_no_billing_advice(self, detector):
        result = _classify(detector, _metrics(cpu=8, memory=30, network=100_000))
        assert result.billing_advice is None

    def test_exclude_tag_exempts(self, detector):
        result = _classify(
            detector, _metrics(cpu=1, memory=1, network=0), instance_tags=[{"Key": "k8s.io", "Value": "x"}]
        )
        assert result.level == LEVEL_EXEMPT
        assert not result.is_idle


class TestConfig:
    def test_custom_thresholds(self):
        rules = {"idle_rules": {"ecs": {"low_cpu_percent": 30, "low_memory_percent": 5}}}
        result = IdleDetector(rules).classify_ecs(_metrics(cpu=25, memory=40, network=500_000), now=NOW)
        assert result.level == LEVEL_LOW_UTILIZATION

    def test_legacy_network_bytes_rule_converted_to_bits(self):
        rules = {"idle_rules": {"ecs": {"network_threshold_bytes_sec": 1000}}}
        assert IdleDetector(rules).thresholds["critical_network_bps"] == 8000

    def test_new_network_rule_takes_precedence(self):
        rules = {"idle_rules": {"ecs": {"network_threshold_bytes_sec": 1000, "critical_network_bps": 70000}}}
        assert IdleDetector(rules).thresholds["critical_network_bps"] == 70000


class TestMetrics:
    def test_summarize_datapoints(self):
        points = [{"Maximum": 10, "Average": 2}, {"Maximum": 30, "Average": 4}]
        assert CloudMonitor.summarize_datapoints(points) == (30.0, 3.0)

    def test_summarize_empty_returns_none_avg(self):
        assert CloudMonitor.summarize_datapoints([]) == (0.0, None)

    def test_fetch_ecs_metrics_keeps_legacy_keys(self):
        provider = MagicMock()
        provider.get_monitor_client.return_value.get_ecs_metrics.return_value = {
            "avg_cpu": 3.0,
            "avg_memory": None,
            "avg_internet_in": 100.0,
            "avg_internet_out": 200.0,
            "max_cpu": 50.0,
        }
        metrics = IdleDetector.fetch_ecs_metrics(provider, "i-1", 7)
        assert metrics["max_cpu"] == 50.0
        assert metrics["CPU利用率"] == 3.0
        assert metrics["内存利用率"] is None

    def test_fetch_ecs_metrics_handles_errors(self):
        provider = MagicMock()
        provider.get_monitor_client.side_effect = ConnectionError("boom")
        assert IdleDetector.fetch_ecs_metrics(provider, "i-1", 7) == {}

    def test_legacy_chinese_keys_still_work(self, detector):
        is_idle, reasons = detector.is_ecs_idle({"CPU利用率": 1.0, "内存利用率": 5.0, "公网入流量": 100, "公网出流量": 100})
        assert is_idle
        assert any("CPU" in r for r in reasons)


class TestEcsAnalyzer:
    def test_is_idle_uses_instance_attributes(self):
        from cloudlens.models.resource import ResourceStatus
        from cloudlens.resource_modules.ecs_analyzer import ECSAnalyzer

        with patch("cloudlens.resource_modules.ecs_analyzer.AliyunProvider"):
            analyzer = ECSAnalyzer("acc", "ak", "sk", "cn-hangzhou")
        instance = MagicMock()
        instance.status = ResourceStatus.STOPPED
        instance.tags = {}
        instance.charge_type = "PrePaid"
        instance.created_time = OLD
        is_idle, reasons = analyzer.is_idle(instance, {})
        assert is_idle
        assert "停机" in reasons[0]
