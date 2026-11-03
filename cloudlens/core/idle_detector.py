"""ECS 闲置检测

分级规则参考阿里云官方 FinOps 巡检 Skill（alibabacloud-finops-inspect），基于观察期内的平均值：
- P1 严重闲置：CPU < 5% 且 内存 < 10% 且 网络 < 50 Kbps
- P2 低利用率：CPU < 10% 或 内存 < 20%
- 无内存数据（未安装云监控插件）时仅按 CPU 与网络判断
- 已停机的包年包月实例仍在计费，直接判定为 P1
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("IdleDetector")

LEVEL_CRITICAL_IDLE = "critical_idle"
LEVEL_LOW_UTILIZATION = "low_utilization"
LEVEL_STOPPED_PREPAID = "stopped_prepaid"
LEVEL_NORMAL = "normal"
LEVEL_OBSERVING = "observing"
LEVEL_NO_DATA = "no_data"
LEVEL_EXEMPT = "exempt"

IDLE_LEVELS = (LEVEL_CRITICAL_IDLE, LEVEL_STOPPED_PREPAID, LEVEL_LOW_UTILIZATION)

LEVEL_PRIORITY = {
    LEVEL_CRITICAL_IDLE: "P1",
    LEVEL_STOPPED_PREPAID: "P1",
    LEVEL_LOW_UTILIZATION: "P2",
}

LEVEL_LABELS = {
    LEVEL_CRITICAL_IDLE: "严重闲置",
    LEVEL_STOPPED_PREPAID: "停机仍计费",
    LEVEL_LOW_UTILIZATION: "低利用率",
    LEVEL_NORMAL: "正常",
    LEVEL_OBSERVING: "观察期",
    LEVEL_NO_DATA: "无监控数据",
    LEVEL_EXEMPT: "白名单豁免",
}

# 按量付费运行超过该天数时建议转包年包月
POSTPAID_LONG_RUNNING_DAYS = 30

# 旧版指标键（中文）到新版键的映射，兼容历史调用方
_LEGACY_METRIC_KEYS = {
    "CPU利用率": "avg_cpu",
    "内存利用率": "avg_memory",
}


@dataclass
class EcsIdleAssessment:
    """ECS 闲置判定结果"""

    level: str
    reasons: List[str] = field(default_factory=list)
    suggestion: str = ""
    billing_advice: Optional[str] = None
    metrics: Dict[str, Optional[float]] = field(default_factory=dict)

    @property
    def is_idle(self) -> bool:
        return self.level in IDLE_LEVELS

    @property
    def priority(self) -> Optional[str]:
        return LEVEL_PRIORITY.get(self.level)

    @property
    def label(self) -> str:
        return LEVEL_LABELS.get(self.level, self.level)


def _round(value: Optional[float]) -> Optional[float]:
    return round(value, 2) if value is not None else None


def _fmt_bps(bps: float) -> str:
    return f"{bps / 1000:.1f} Kbps"


class IdleDetector:
    """
    闲置资源检测器
    基于监控指标平均值对 ECS 实例进行分级判定
    """

    def __init__(self, rules: Optional[Dict] = None):
        self.rules = rules or {}
        self.ecs_rules = self.rules.get("idle_rules", {}).get("ecs", {})

        # 旧配置 network_threshold_bytes_sec 单位为字节/秒，换算为 bits/s 作为回退
        legacy_net = self.ecs_rules.get("network_threshold_bytes_sec")
        default_net_bps = legacy_net * 8 if legacy_net is not None else 50_000

        self.thresholds = {
            "critical_cpu_percent": self.ecs_rules.get("cpu_threshold_percent", 5),
            "critical_memory_percent": self.ecs_rules.get("critical_memory_percent", 10),
            "critical_network_bps": self.ecs_rules.get("critical_network_bps", default_net_bps),
            "low_cpu_percent": self.ecs_rules.get("low_cpu_percent", 10),
            "low_memory_percent": self.ecs_rules.get("low_memory_percent", 20),
        }

    def _is_exempt(self, instance_tags: Optional[List[Dict]]) -> Optional[str]:
        """检查白名单标签，命中时返回标签描述"""
        exclude_tags = self.ecs_rules.get("exclude_tags", [])
        if not instance_tags or not exclude_tags:
            return None
        for tag in instance_tags:
            tag_key = tag.get("Key")
            tag_str = f"{tag_key}={tag.get('Value')}"
            if tag_str in exclude_tags or tag_key in exclude_tags:
                return tag_str
        return None

    @staticmethod
    def _normalize_metrics(metrics: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """统一指标键：兼容旧版中文键，并计算网络平均值（取内外网、出入方向的最大者）"""
        normalized: Dict[str, Optional[float]] = dict(metrics)
        for legacy_key, new_key in _LEGACY_METRIC_KEYS.items():
            if new_key not in normalized and legacy_key in metrics:
                normalized[new_key] = metrics[legacy_key]

        if "avg_network_bps" not in normalized:
            network_values = [
                metrics.get(k)
                for k in ("avg_intranet_in", "avg_intranet_out", "avg_internet_in", "avg_internet_out")
                if metrics.get(k) is not None
            ]
            if not network_values:
                network_values = [
                    metrics.get(k) for k in ("公网入流量", "公网出流量") if metrics.get(k) is not None
                ]
            normalized["avg_network_bps"] = max(network_values) if network_values else None
        return normalized

    @staticmethod
    def _postpaid_advice(charge_type: Optional[str], created_time: Optional[datetime], now: datetime) -> Optional[str]:
        """长期运行的按量付费实例，建议转包年包月"""
        if charge_type != "PostPaid" or not created_time:
            return None
        age_days = (now - created_time).days
        if age_days > POSTPAID_LONG_RUNNING_DAYS:
            return f"按量付费已运行 {age_days} 天，转包年包月通常可节省 30%~50%"
        return None

    def classify_ecs(
        self,
        metrics: Dict[str, Any],
        instance_tags: Optional[List[Dict]] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
        created_time: Optional[datetime] = None,
        observation_days: int = 7,
        now: Optional[datetime] = None,
    ) -> EcsIdleAssessment:
        """对 ECS 实例做分级闲置判定

        Args:
            metrics: 监控指标，键为 avg_cpu / avg_memory / avg_intranet_in 等（值为 None 表示无数据），
                兼容旧版中文键（CPU利用率、内存利用率、公网入流量、公网出流量）
            instance_tags: 实例标签列表 [{"Key": "k", "Value": "v"}]
            status: 实例状态（Running / Stopped ...），为 None 时视为运行中
            charge_type: 计费方式（PrePaid / PostPaid）
            created_time: 创建时间（UTC，naive datetime）
            observation_days: 观察期天数，创建时间不足该天数的实例不做判定
            now: 当前时间（UTC），便于测试注入

        Returns:
            判定结果
        """
        now = now or datetime.now(timezone.utc).replace(tzinfo=None)

        exempt_tag = self._is_exempt(instance_tags)
        if exempt_tag:
            return EcsIdleAssessment(LEVEL_EXEMPT, [f"白名单标签豁免: {exempt_tag}"])

        if status == "Stopped" and charge_type == "PrePaid":
            return EcsIdleAssessment(
                LEVEL_STOPPED_PREPAID,
                ["包年包月实例已停机，仍在持续计费"],
                suggestion="确认不再使用后释放实例，或在到期前取消续费",
            )

        if status is not None and status != "Running":
            return EcsIdleAssessment(LEVEL_NORMAL, [f"实例状态为 {status}，不做利用率判定"])

        if created_time and (now - created_time).days < observation_days:
            return EcsIdleAssessment(LEVEL_OBSERVING, [f"创建不足 {observation_days} 天，处于观察期"])

        m = self._normalize_metrics(metrics)
        cpu = m.get("avg_cpu")
        memory = m.get("avg_memory")
        network = m.get("avg_network_bps")
        t = self.thresholds
        billing_advice = self._postpaid_advice(charge_type, created_time, now)
        summary = {
            "avg_cpu": _round(cpu),
            "avg_memory": _round(memory),
            "avg_network_bps": _round(network),
        }

        if cpu is None:
            return EcsIdleAssessment(
                LEVEL_NO_DATA, ["未获取到 CPU 监控数据，无法判定"], billing_advice=billing_advice, metrics=summary
            )

        # 无网络数据时不作为严重闲置的否定条件，但也不能作为肯定条件
        network_low = network is not None and network < t["critical_network_bps"]
        cpu_reason = f"CPU 平均 {cpu:.2f}%"
        memory_reason = f"内存平均 {memory:.2f}%" if memory is not None else "内存无数据（未安装云监控插件）"
        network_reason = f"网络平均 {_fmt_bps(network)}" if network is not None else "网络无数据"

        if memory is not None:
            is_critical = cpu < t["critical_cpu_percent"] and memory < t["critical_memory_percent"] and network_low
            is_low = cpu < t["low_cpu_percent"] or memory < t["low_memory_percent"]
        else:
            is_critical = cpu < t["critical_cpu_percent"] and network_low
            is_low = cpu < t["low_cpu_percent"]

        if is_critical:
            return EcsIdleAssessment(
                LEVEL_CRITICAL_IDLE,
                [cpu_reason, memory_reason, network_reason],
                suggestion="考虑释放实例或大幅降配",
                billing_advice=billing_advice,
                metrics=summary,
            )
        if is_low:
            reasons = []
            if cpu < t["low_cpu_percent"]:
                reasons.append(f"{cpu_reason} < {t['low_cpu_percent']}%")
            if memory is not None and memory < t["low_memory_percent"]:
                reasons.append(f"{memory_reason} < {t['low_memory_percent']}%")
            return EcsIdleAssessment(
                LEVEL_LOW_UTILIZATION,
                reasons,
                suggestion="考虑降配到更小规格",
                billing_advice=billing_advice,
                metrics=summary,
            )
        return EcsIdleAssessment(LEVEL_NORMAL, [], billing_advice=billing_advice, metrics=summary)

    def is_ecs_idle(self, metrics: Dict[str, Any], instance_tags: Optional[List[Dict]] = None) -> Tuple[bool, List[str]]:
        """
        判断ECS实例是否闲置（兼容旧接口，内部使用分级判定）

        Args:
            metrics: 监控指标字典
            instance_tags: 实例标签列表 [{"Key": "k", "Value": "v"}]

        Returns:
            (is_idle, reasons) - 是否闲置及原因列表
        """
        assessment = self.classify_ecs(metrics, instance_tags)
        return assessment.is_idle, assessment.reasons

    @staticmethod
    def fetch_ecs_metrics(provider, instance_id: str, days: int = 14) -> Dict[str, Optional[float]]:
        """
        获取ECS实例的监控指标 (使用 CloudMonitor)

        Args:
            provider: AliyunProvider实例
            instance_id: 实例ID
            days: 查询天数

        Returns:
            监控指标字典，包含 avg_* 平均值（None 表示无数据）与 max_* 最大值；
            同时保留旧版中文键（CPU利用率等，取平均值）供历史调用方使用
        """
        metrics_result: Dict[str, Optional[float]] = {}
        if not hasattr(provider, "get_monitor_client"):
            logger.warning("Provider does not support get_monitor_client, skipping metrics.")
            return metrics_result
        try:
            monitor = provider.get_monitor_client()
            metrics_result = dict(monitor.get_ecs_metrics(instance_id, days))
        except Exception as e:
            logger.warning(f"Failed to fetch metrics via CloudMonitor for {instance_id}: {e}")
            return metrics_result

        metrics_result["CPU利用率"] = metrics_result.get("avg_cpu")
        metrics_result["内存利用率"] = metrics_result.get("avg_memory")
        metrics_result["公网入流量"] = metrics_result.get("avg_internet_in")
        metrics_result["公网出流量"] = metrics_result.get("avg_internet_out")
        return metrics_result
