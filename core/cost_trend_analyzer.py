"""
成本趋势分析器
用于分析云资源历史成本,计算趋势和预测未来
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class CostTrendAnalyzer:
    """成本趋势分析器"""

    def __init__(self, data_dir: str = "./data/cost"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cost_history_file = self.data_dir / "cost_history.json"

    def record_cost_snapshot(
        self, account_name: str, resources: List, timestamp: Optional[datetime] = None
    ):
        """
        记录成本快照
        
        Args:
            account_name: 账号名称
            resources: 资源列表(UnifiedResource)
            timestamp: 时间戳,默认当前时间
        """
        if timestamp is None:
            timestamp = datetime.now()

        # 计算当前成本
        total_cost = 0
        cost_by_type = defaultdict(float)
        cost_by_region = defaultdict(float)

        for resource in resources:
            # 估算成本(基于规格和计费类型)
            monthly_cost = self._estimate_resource_cost(resource)
            total_cost += monthly_cost

            # 按类型统计
            cost_by_type[resource.resource_type.value] += monthly_cost

            # 按区域统计
            cost_by_region[resource.region] += monthly_cost

        # 构建快照数据
        snapshot = {
            "timestamp": timestamp.isoformat(),
            "account": account_name,
            "total_cost": round(total_cost, 2),
            "cost_by_type": {k: round(v, 2) for k, v in cost_by_type.items()},
            "cost_by_region": {k: round(v, 2) for k, v in cost_by_region.items()},
            "resource_count": len(resources),
        }

        # 保存到历史记录
        self._append_snapshot(snapshot)

        return snapshot

    def _estimate_resource_cost(self, resource) -> float:
        """
        估算单个资源的月成本
        
        这是简化版本,实际应该:
        1. 查询云厂商API获取实际账单
        2. 使用详细价格表计算
        3. 考虑折扣和优惠
        """
        # 简化估算规则（尽量避免不同 ECS 规格落到同一个默认值）
        cost_map = {
            # ECS按规格估算(CNY/月)
            "ecs.t5-lc1m1.small": 50,
            "ecs.t5-lc1m2.small": 80,
            "ecs.g6.large": 400,
            "ecs.g6.xlarge": 800,
            "ecs.r6.xlarge": 900,
            # RDS
            "rds.mysql.s1.small": 200,
            "rds.mysql.s2.large": 500,
            # Redis
            "redis.master.small.default": 150,
            "redis.master.mid.default": 300,
        }

        spec = getattr(resource, "spec", None) or ""
        rt = ""
        if hasattr(resource, "resource_type"):
            rt = resource.resource_type.value.lower()

        if spec and spec in cost_map:
            base_cost = cost_map[spec]
        elif spec.startswith("ecs."):
            # ecs.{family}.{size}
            parts = spec.split(".")
            if len(parts) >= 3:
                family = parts[-2] or ""
                size = parts[-1] or ""

                # size multiplier（large=1, xlarge=2, 2xlarge=4, ...）
                s = size.lower()
                size_mul = 1.0
                if s == "small":
                    size_mul = 0.25
                elif s == "medium":
                    size_mul = 0.5
                elif s == "large":
                    size_mul = 1.0
                elif s == "xlarge":
                    size_mul = 2.0
                else:
                    import re
                    m = re.match(r"^(\d+)xlarge$", s)
                    if m:
                        n = int(m.group(1))
                        size_mul = max(1.0, float(n) * 2.0)

                # family multiplier（粗略：r>g>c>t）
                fam = (family or "").lower()
                prefix = fam[:1]
                fam_mul = 1.1
                if prefix == "t":
                    fam_mul = 0.55
                elif prefix == "c":
                    fam_mul = 1.0
                elif prefix == "g":
                    fam_mul = 1.15
                elif prefix == "r":
                    fam_mul = 1.45
                elif prefix == "h":
                    fam_mul = 1.35

                # generation multiplier（6代基线）
                m2 = re.search(r"(\d+)", fam)
                gen_mul = 1.0
                if m2:
                    gen = int(m2.group(1))
                    if gen > 6:
                        gen_mul = min(1.30, 1.0 + (gen - 6) * 0.05)

                base_large = 320.0
                base_cost = round(base_large * size_mul * fam_mul * gen_mul, 2)
            else:
                base_cost = 300
        else:
            # 默认估算
            if "ecs" in rt:
                base_cost = 300
            elif "rds" in rt:
                base_cost = 400
            elif "redis" in rt:
                base_cost = 200
            else:
                base_cost = 100

        # 考虑计费类型
        charge_type = getattr(resource, "charge_type", "PostPaid")
        if charge_type == "PrePaid":
            # 预付费折扣10%
            base_cost *= 0.9

        return base_cost

    def _append_snapshot(self, snapshot: Dict):
        """追加快照到历史文件"""
        history = []

        # 读取现有历史
        if self.cost_history_file.exists():
            try:
                with open(self.cost_history_file, "r") as f:
                    history = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cost history: {e}")
                history = []

        # 追加新快照
        history.append(snapshot)

        # 保留最近365天数据
        cutoff_date = datetime.now() - timedelta(days=365)
        history = [
            s
            for s in history
            if datetime.fromisoformat(s["timestamp"]) > cutoff_date
        ]

        # 保存
        with open(self.cost_history_file, "w") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def get_cost_trend(
        self, account_name: str, days: int = 30
    ) -> Tuple[List[Dict], Dict]:
        """
        获取成本趋势
        
        Returns:
            (history_data, analysis)
        """
        # 读取历史数据
        if not self.cost_history_file.exists():
            return [], {"error": "No cost history available"}

        with open(self.cost_history_file, "r") as f:
            all_history = json.load(f)

        # 筛选账号和时间范围
        cutoff_date = datetime.now() - timedelta(days=days)
        history = [
            s
            for s in all_history
            if s["account"] == account_name
            and datetime.fromisoformat(s["timestamp"]) > cutoff_date
        ]

        if len(history) < 2:
            return history, {"error": "Insufficient data for trend analysis"}

        # 按时间排序
        history.sort(key=lambda x: x["timestamp"])

        # 分析趋势
        analysis = self._analyze_trend(history)

        return history, analysis

    def _analyze_trend(self, history: List[Dict]) -> Dict:
        """分析成本趋势"""
        if len(history) < 2:
            return {}

        latest = history[-1]
        oldest = history[0]

        # 计算总增长
        total_change = latest["total_cost"] - oldest["total_cost"]
        total_change_pct = (
            (total_change / oldest["total_cost"] * 100) if oldest["total_cost"] > 0 else 0
        )

        # 计算平均成本
        avg_cost = sum(s["total_cost"] for s in history) / len(history)

        # 计算最大/最小
        max_cost = max(s["total_cost"] for s in history)
        min_cost = min(s["total_cost"] for s in history)

        # 环比增长(最近2个数据点)
        if len(history) >= 2:
            prev = history[-2]
            mom_change = latest["total_cost"] - prev["total_cost"]
            mom_change_pct = (
                (mom_change / prev["total_cost"] * 100) if prev["total_cost"] > 0 else 0
            )
        else:
            mom_change = 0
            mom_change_pct = 0

        # 同比增长(如果有去年同期数据)
        yoy_change = None
        yoy_change_pct = None
        if len(history) > 30:  # 假设每天一个快照
            last_year = history[min(30, len(history) - 1)]
            yoy_change = latest["total_cost"] - last_year["total_cost"]
            yoy_change_pct = (
                (yoy_change / last_year["total_cost"] * 100)
                if last_year["total_cost"] > 0
                else 0
            )

        return {
            "period_days": (
                datetime.fromisoformat(latest["timestamp"])
                - datetime.fromisoformat(oldest["timestamp"])
            ).days,
            "latest_cost": round(latest["total_cost"], 2),
            "oldest_cost": round(oldest["total_cost"], 2),
            "total_change": round(total_change, 2),
            "total_change_pct": round(total_change_pct, 2),
            "avg_cost": round(avg_cost, 2),
            "max_cost": round(max_cost, 2),
            "min_cost": round(min_cost, 2),
            "mom_change": round(mom_change, 2),
            "mom_change_pct": round(mom_change_pct, 2),
            "yoy_change": round(yoy_change, 2) if yoy_change else None,
            "yoy_change_pct": round(yoy_change_pct, 2) if yoy_change_pct else None,
            "trend": "上升" if total_change > 0 else "下降" if total_change < 0 else "平稳",
        }

    def generate_trend_report(self, account_name: str, days: int = 30) -> Dict:
        """
        生成趋势报告
        
        Returns:
            包含图表数据和分析的报告
        """
        history, analysis = self.get_cost_trend(account_name, days)

        if "error" in analysis:
            return {"error": analysis["error"]}

        # 准备图表数据
        chart_data = {
            "dates": [datetime.fromisoformat(s["timestamp"]).strftime("%Y-%m-%d") for s in history],
            "costs": [s["total_cost"] for s in history],
            "resource_counts": [s["resource_count"] for s in history],
        }

        # 按类型汇总
        type_summary = defaultdict(float)
        for snapshot in history:
            for type_name, cost in snapshot.get("cost_by_type", {}).items():
                type_summary[type_name] += cost

        # 按区域汇总
        region_summary = defaultdict(float)
        for snapshot in history:
            for region, cost in snapshot.get("cost_by_region", {}).items():
                region_summary[region] += cost

        return {
            "account": account_name,
            "period_days": days,
            "analysis": analysis,
            "chart_data": chart_data,
            "cost_by_type": dict(type_summary),
            "cost_by_region": dict(region_summary),
            "snapshots_count": len(history),
        }
