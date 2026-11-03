#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成本归因分析引擎。

对比两个完整账期的账单明细，将成本变化拆成：
- resource_count: 实例数量 / 使用量变化
- discount: 折扣率变化
- price: 单价变化
- product_mix: 新增或消失的产品
- other: 舍入残差

数据只读 bill_items，不绑定某一家云厂商 API，便于后续接入多云账单。
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CATEGORY_LABELS = {
    "resource_count": "资源数量/用量变化",
    "discount": "折扣率变化",
    "price": "单价变化",
    "product_mix": "产品结构变化",
    "other": "其他/舍入",
}

CATEGORY_ORDER = ["resource_count", "discount", "price", "product_mix", "other"]


@dataclass
class ProductPeriodStats:
    """单个产品在一个账期内的聚合指标。"""

    product_code: str
    product_name: str
    pretax: float
    discount: float
    usage: float
    instance_count: int

    @property
    def gross(self) -> float:
        """税前应付 + 发票折扣，近似未折前金额。"""
        return max(self.pretax, 0.0) + max(self.discount, 0.0)

    @property
    def discount_rate(self) -> float:
        gross = self.gross
        if gross <= 0:
            return 0.0
        return max(self.discount, 0.0) / gross

    @property
    def quantity(self) -> float:
        """优先用量，其次实例数；都没有则视为 1，避免除零。"""
        if self.usage > 0:
            return float(self.usage)
        if self.instance_count > 0:
            return float(self.instance_count)
        return 1.0 if self.pretax != 0 else 0.0


@dataclass
class ProductDelta:
    """单个产品的归因拆解。"""

    product_code: str
    product_name: str
    current_pretax: float
    compare_pretax: float
    delta: float
    current_count: int
    compare_count: int
    current_usage: float
    compare_usage: float
    current_discount_rate: float
    compare_discount_rate: float
    quantity_effect: float = 0.0
    discount_effect: float = 0.0
    price_effect: float = 0.0
    mix_effect: float = 0.0
    residual: float = 0.0
    status: str = "existing"  # existing / new / removed


@dataclass
class AttributionCategory:
    """按原因聚合后的归因桶。"""

    category: str
    label: str
    impact: float
    impact_pct: float
    details: List[Dict[str, Any]] = field(default_factory=list)


def shift_billing_cycle(cycle: str, months: int) -> str:
    """将 YYYY-MM 账期平移指定月数。"""
    year, month = _parse_cycle(cycle)
    total = year * 12 + (month - 1) + months
    new_year, new_month_index = divmod(total, 12)
    return f"{new_year:04d}-{new_month_index + 1:02d}"


def _parse_cycle(cycle: str) -> Tuple[int, int]:
    parts = (cycle or "").split("-")
    if len(parts) != 2:
        raise ValueError(f"账期格式无效: {cycle}")
    year = int(parts[0])
    month = int(parts[1])
    if month < 1 or month > 12:
        raise ValueError(f"账期月份无效: {cycle}")
    return year, month


def aggregate_product_stats(rows: List[Dict[str, Any]]) -> Dict[str, ProductPeriodStats]:
    """把账单查询行聚合成 product_code -> ProductPeriodStats。"""
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        code = str(row.get("product_code") or "unknown")
        name = str(row.get("product_name") or code)
        pretax = float(row.get("pretax") or 0)
        discount = float(row.get("discount") or 0)
        usage = float(row.get("usage") or 0)
        instance_count = int(row.get("instance_count") or 0)
        bucket = grouped.setdefault(
            code,
            {
                "product_code": code,
                "product_name": name,
                "pretax": 0.0,
                "discount": 0.0,
                "usage": 0.0,
                "instance_count": 0,
            },
        )
        if name and name != code:
            bucket["product_name"] = name
        bucket["pretax"] += pretax
        bucket["discount"] += discount
        bucket["usage"] += usage
        bucket["instance_count"] += instance_count

    return {
        code: ProductPeriodStats(
            product_code=item["product_code"],
            product_name=item["product_name"],
            pretax=round(item["pretax"], 4),
            discount=round(item["discount"], 4),
            usage=round(item["usage"], 4),
            instance_count=int(item["instance_count"]),
        )
        for code, item in grouped.items()
    }


def _decompose_existing(current: ProductPeriodStats, previous: ProductPeriodStats) -> ProductDelta:
    """对两期都存在的产品做数量/折扣/单价拆解。"""
    delta = current.pretax - previous.pretax
    q_a = previous.quantity
    q_b = current.quantity
    g_a = previous.gross
    g_b = current.gross
    d_a = previous.discount_rate
    d_b = current.discount_rate

    if q_a <= 0 and q_b <= 0:
        quantity_effect = 0.0
        price_effect = 0.0
        discount_effect = 0.0
    elif q_a <= 0:
        quantity_effect = current.pretax
        price_effect = 0.0
        discount_effect = 0.0
    elif q_b <= 0:
        quantity_effect = -previous.pretax
        price_effect = 0.0
        discount_effect = 0.0
    else:
        unit_g_a = g_a / q_a
        unit_g_b = g_b / q_b
        net_unit_a = unit_g_a * (1.0 - d_a)
        quantity_effect = (q_b - q_a) * net_unit_a
        price_effect = q_b * (unit_g_b - unit_g_a) * (1.0 - d_a)
        discount_effect = q_b * unit_g_b * (d_a - d_b)

    residual = delta - (quantity_effect + price_effect + discount_effect)
    return ProductDelta(
        product_code=current.product_code,
        product_name=current.product_name or previous.product_name,
        current_pretax=current.pretax,
        compare_pretax=previous.pretax,
        delta=delta,
        current_count=current.instance_count,
        compare_count=previous.instance_count,
        current_usage=current.usage,
        compare_usage=previous.usage,
        current_discount_rate=d_b,
        compare_discount_rate=d_a,
        quantity_effect=quantity_effect,
        discount_effect=discount_effect,
        price_effect=price_effect,
        residual=residual,
        status="existing",
    )


def attribute_product_changes(
    current: Dict[str, ProductPeriodStats],
    previous: Dict[str, ProductPeriodStats],
) -> List[ProductDelta]:
    """对比两期产品聚合结果，返回每个产品的拆解。"""
    codes = sorted(set(current.keys()) | set(previous.keys()))
    results: List[ProductDelta] = []
    for code in codes:
        cur = current.get(code)
        prev = previous.get(code)
        if cur and not prev:
            results.append(
                ProductDelta(
                    product_code=code,
                    product_name=cur.product_name,
                    current_pretax=cur.pretax,
                    compare_pretax=0.0,
                    delta=cur.pretax,
                    current_count=cur.instance_count,
                    compare_count=0,
                    current_usage=cur.usage,
                    compare_usage=0.0,
                    current_discount_rate=cur.discount_rate,
                    compare_discount_rate=0.0,
                    mix_effect=cur.pretax,
                    status="new",
                )
            )
            continue
        if prev and not cur:
            results.append(
                ProductDelta(
                    product_code=code,
                    product_name=prev.product_name,
                    current_pretax=0.0,
                    compare_pretax=prev.pretax,
                    delta=-prev.pretax,
                    current_count=0,
                    compare_count=prev.instance_count,
                    current_usage=0.0,
                    compare_usage=prev.usage,
                    current_discount_rate=0.0,
                    compare_discount_rate=prev.discount_rate,
                    mix_effect=-prev.pretax,
                    status="removed",
                )
            )
            continue
        if cur and prev:
            results.append(_decompose_existing(cur, prev))
    return results


def _round_money(value: float) -> float:
    return round(float(value or 0.0), 2)


def build_attribution_report(
    current: Dict[str, ProductPeriodStats],
    previous: Dict[str, ProductPeriodStats],
    current_cycle: str,
    compare_cycle: str,
    compare_type: str = "mom",
) -> Dict[str, Any]:
    """把产品拆解汇总成可直接返回前端的归因报告。"""
    product_deltas = attribute_product_changes(current, previous)
    current_total = _round_money(sum(item.pretax for item in current.values()))
    compare_total = _round_money(sum(item.pretax for item in previous.values()))
    delta = _round_money(current_total - compare_total)
    delta_pct = _round_money((delta / compare_total) * 100) if compare_total else 0.0

    buckets: Dict[str, float] = {key: 0.0 for key in CATEGORY_ORDER}
    details: Dict[str, List[Dict[str, Any]]] = {key: [] for key in CATEGORY_ORDER}

    for item in product_deltas:
        mapped = [
            ("resource_count", item.quantity_effect, _quantity_description(item)),
            ("discount", item.discount_effect, _discount_description(item)),
            ("price", item.price_effect, _price_description(item)),
            ("product_mix", item.mix_effect, _mix_description(item)),
            ("other", item.residual, "舍入残差"),
        ]
        for category, impact, description in mapped:
            if abs(impact) < 0.005:
                continue
            buckets[category] += impact
            details[category].append(
                {
                    "product_code": item.product_code,
                    "product_name": item.product_name,
                    "status": item.status,
                    "current_count": item.current_count,
                    "compare_count": item.compare_count,
                    "current_usage": _round_money(item.current_usage),
                    "compare_usage": _round_money(item.compare_usage),
                    "current_discount_rate": round(item.current_discount_rate * 100, 2),
                    "compare_discount_rate": round(item.compare_discount_rate * 100, 2),
                    "current_pretax": _round_money(item.current_pretax),
                    "compare_pretax": _round_money(item.compare_pretax),
                    "cost_impact": _round_money(impact),
                    "description": description,
                }
            )

    attributions: List[Dict[str, Any]] = []
    denom = abs(delta) if abs(delta) > 0.01 else 1.0
    for category in CATEGORY_ORDER:
        impact = _round_money(buckets[category])
        if abs(impact) < 0.01 and category == "other":
            continue
        if abs(impact) < 0.01:
            continue
        product_details = sorted(details[category], key=lambda row: abs(row["cost_impact"]), reverse=True)
        attributions.append(
            asdict(
                AttributionCategory(
                    category=category,
                    label=CATEGORY_LABELS[category],
                    impact=impact,
                    impact_pct=_round_money((impact / denom) * 100) if delta != 0 else 0.0,
                    details=product_details[:12],
                )
            )
        )

    attributions.sort(key=lambda row: abs(row["impact"]), reverse=True)
    products = [
        {
            "product_code": item.product_code,
            "product_name": item.product_name,
            "status": item.status,
            "current_pretax": _round_money(item.current_pretax),
            "compare_pretax": _round_money(item.compare_pretax),
            "delta": _round_money(item.delta),
            "current_count": item.current_count,
            "compare_count": item.compare_count,
        }
        for item in sorted(product_deltas, key=lambda row: abs(row.delta), reverse=True)[:20]
        if abs(item.delta) >= 0.01
    ]
    recommendations = generate_recommendations(attributions, delta)

    return {
        "current_cycle": current_cycle,
        "compare_cycle": compare_cycle,
        "compare_type": compare_type,
        "current_total": current_total,
        "compare_total": compare_total,
        "delta": delta,
        "delta_pct": delta_pct,
        "attributions": attributions,
        "products": products,
        "recommendations": recommendations,
        "data_source": "bill_items",
    }


def generate_recommendations(attributions: List[Dict[str, Any]], total_delta: float) -> List[Dict[str, Any]]:
    """根据归因桶生成可执行建议（只读建议，不改云上资源）。"""
    by_category = {item["category"]: item for item in attributions}
    recommendations: List[Dict[str, Any]] = []

    discount = by_category.get("discount")
    if discount and discount["impact"] > 50:
        top = discount["details"][0] if discount["details"] else {}
        recommendations.append(
            {
                "priority": "high",
                "category": "discount",
                "title": "折扣率下降，评估续购预留/包年包月",
                "description": (
                    f"折扣变化使成本上升约 ¥{abs(discount['impact']):,.0f}。"
                    f"{'主要产品：' + str(top.get('product_name') or top.get('product_code') or '') if top else ''}"
                ),
                "estimated_savings": _round_money(abs(discount["impact"])),
                "effort": "low",
                "action": "查看即将到期的预留实例或包年包月，优先续购稳定负载。",
            }
        )

    quantity = by_category.get("resource_count")
    if quantity and quantity["impact"] >= 50:
        new_or_grown = [
            row
            for row in quantity.get("details", [])
            if row.get("cost_impact", 0) > 0
        ]
        recommendations.append(
            {
                "priority": "medium",
                "category": "resource_count",
                "title": "资源数量或用量上升，核对新增实例是否必要",
                "description": (
                    f"数量/用量变化使成本上升约 ¥{abs(quantity['impact']):,.0f}，"
                    f"涉及 {len(new_or_grown)} 个产品。"
                ),
                "estimated_savings": _round_money(abs(quantity["impact"]) * 0.5),
                "effort": "medium",
                "action": "对照闲置扫描结果，先停机观察低使用率实例，再决定释放。",
            }
        )

    mix = by_category.get("product_mix")
    if mix and mix["impact"] > 50:
        recommendations.append(
            {
                "priority": "medium",
                "category": "product_mix",
                "title": "本期出现新产品费用",
                "description": f"产品结构变化影响约 ¥{abs(mix['impact']):,.0f}，请确认是否为预期开通。",
                "estimated_savings": 0.0,
                "effort": "low",
                "action": "核对新产品开通人和业务用途，避免测试资源流入生产账单。",
            }
        )

    price = by_category.get("price")
    if price and price["impact"] > 50:
        recommendations.append(
            {
                "priority": "low",
                "category": "price",
                "title": "单价上升",
                "description": f"同等用量下单价变化约 ¥{abs(price['impact']):,.0f}，可能来自规格变更或目录价调整。",
                "estimated_savings": 0.0,
                "effort": "medium",
                "action": "检查是否发生了升配、计费项变更或区域迁移。",
            }
        )

    if not recommendations:
        if abs(total_delta) < 1:
            recommendations.append(
                {
                    "priority": "low",
                    "category": "other",
                    "title": "两期成本基本持平",
                    "description": "未发现需要立刻处理的成本驱动因素。",
                    "estimated_savings": 0.0,
                    "effort": "low",
                    "action": "保持现有巡检节奏即可。",
                }
            )
        elif attributions:
            top = max(attributions, key=lambda item: abs(float(item.get("impact") or 0)))
            recommendations.append(
                {
                    "priority": "medium",
                    "category": top.get("category") or "other",
                    "title": "关注本期最大成本驱动因素",
                    "description": (
                        f"{top.get('label') or top.get('category')} 影响约 "
                        f"¥{abs(float(top.get('impact') or 0)):,.0f}。"
                    ),
                    "estimated_savings": 0.0,
                    "effort": "medium",
                    "action": "先看该归因下的产品明细，确认是否为预期业务变化。",
                }
            )
    return recommendations


def _quantity_description(item: ProductDelta) -> str:
    if item.current_usage or item.compare_usage:
        return f"用量 {item.compare_usage:.2f} → {item.current_usage:.2f}"
    return f"实例数 {item.compare_count} → {item.current_count}"


def _discount_description(item: ProductDelta) -> str:
    return (
        f"折扣率 {item.compare_discount_rate * 100:.1f}% → "
        f"{item.current_discount_rate * 100:.1f}%"
    )


def _price_description(item: ProductDelta) -> str:
    return f"应付 {item.compare_pretax:.2f} → {item.current_pretax:.2f} 中的单价部分"


def _mix_description(item: ProductDelta) -> str:
    if item.status == "new":
        return "本期新增产品"
    if item.status == "removed":
        return "上期有、本期无"
    return "产品结构变化"


class CostAttributionEngine:
    """从 MySQL bill_items 读取两期账单并输出归因报告。"""

    def __init__(self, db: Optional[Any] = None):
        self._db = db

    def _get_db(self) -> Any:
        if self._db is not None:
            return self._db
        from cloudlens.core.database import DatabaseFactory

        self._db = DatabaseFactory.create_adapter("mysql")
        return self._db

    def resolve_account_id(self, account_name: str, access_key_id: Optional[str] = None) -> Optional[str]:
        """解析 bill_items 中的 account_id。"""
        db = self._get_db()
        candidates: List[str] = []
        if access_key_id:
            candidates.append(f"{access_key_id[:10]}-{account_name}")
        candidates.append(account_name)

        for candidate in candidates:
            row = db.query_one(
                "SELECT DISTINCT account_id FROM bill_items WHERE account_id = %s LIMIT 1",
                (candidate,),
            )
            if row:
                return row.get("account_id") if isinstance(row, dict) else row[0]

        row = db.query_one(
            "SELECT DISTINCT account_id FROM bill_items WHERE account_id LIKE %s LIMIT 1",
            (f"%{account_name}%",),
        )
        if not row:
            return None
        return row.get("account_id") if isinstance(row, dict) else row[0]

    def list_cycles(self, account_id: str) -> List[str]:
        """列出账号已有账期，新到旧。"""
        db = self._get_db()
        rows = db.query(
            """
            SELECT DISTINCT billing_cycle
            FROM bill_items
            WHERE account_id = %s
            ORDER BY billing_cycle DESC
            """,
            (account_id,),
        )
        cycles: List[str] = []
        for row in rows or []:
            cycle = row.get("billing_cycle") if isinstance(row, dict) else row[0]
            if cycle:
                cycles.append(str(cycle))
        return cycles

    def _load_product_stats(self, account_id: str, billing_cycle: str) -> Dict[str, ProductPeriodStats]:
        db = self._get_db()
        rows = db.query(
            """
            SELECT
                COALESCE(product_code, 'unknown') AS product_code,
                MAX(COALESCE(product_name, product_code, 'unknown')) AS product_name,
                SUM(COALESCE(pretax_amount, 0)) AS pretax,
                SUM(COALESCE(invoice_discount, 0)) AS discount,
                SUM(COALESCE(`usage`, 0)) AS `usage`,
                COUNT(DISTINCT CASE
                    WHEN instance_id IS NOT NULL AND instance_id != '' THEN instance_id
                END) AS instance_count
            FROM bill_items
            WHERE account_id = %s
              AND billing_cycle = %s
            GROUP BY product_code
            """,
            (account_id, billing_cycle),
        )
        normalized: List[Dict[str, Any]] = []
        for row in rows or []:
            if isinstance(row, dict):
                normalized.append(row)
            else:
                normalized.append(
                    {
                        "product_code": row[0],
                        "product_name": row[1],
                        "pretax": row[2],
                        "discount": row[3],
                        "usage": row[4],
                        "instance_count": row[5],
                    }
                )
        return aggregate_product_stats(normalized)

    def analyze(
        self,
        account_name: str,
        current_cycle: Optional[str] = None,
        compare_cycle: Optional[str] = None,
        compare_type: str = "mom",
        access_key_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行归因分析。"""
        account_id = self.resolve_account_id(account_name, access_key_id=access_key_id)
        if not account_id:
            logger.warning("未找到账号 %s 的账单数据", account_name)
            return {
                "current_cycle": current_cycle,
                "compare_cycle": compare_cycle,
                "compare_type": compare_type,
                "current_total": 0.0,
                "compare_total": 0.0,
                "delta": 0.0,
                "delta_pct": 0.0,
                "attributions": [],
                "products": [],
                "recommendations": [],
                "data_source": "bill_items",
                "message": f"未找到账号 {account_name} 的账单数据，请先同步账单",
            }

        cycles = self.list_cycles(account_id)
        current_cycle, compare_cycle, compare_type = self._resolve_cycles(
            cycles, current_cycle, compare_cycle, compare_type
        )
        if not current_cycle or not compare_cycle:
            return {
                "current_cycle": current_cycle,
                "compare_cycle": compare_cycle,
                "compare_type": compare_type,
                "current_total": 0.0,
                "compare_total": 0.0,
                "delta": 0.0,
                "delta_pct": 0.0,
                "attributions": [],
                "products": [],
                "recommendations": [],
                "data_source": "bill_items",
                "message": "账单数据不足两个账期，无法做对比归因",
                "available_cycles": cycles,
            }

        current_stats = self._load_product_stats(account_id, current_cycle)
        previous_stats = self._load_product_stats(account_id, compare_cycle)
        report = build_attribution_report(
            current_stats,
            previous_stats,
            current_cycle=current_cycle,
            compare_cycle=compare_cycle,
            compare_type=compare_type,
        )
        report["account_id"] = account_id
        report["available_cycles"] = cycles
        logger.info(
            "成本归因完成: account=%s current=%s compare=%s delta=%s",
            account_name,
            current_cycle,
            compare_cycle,
            report["delta"],
        )
        return report

    def _resolve_cycles(
        self,
        available: List[str],
        current_cycle: Optional[str],
        compare_cycle: Optional[str],
        compare_type: str,
    ) -> Tuple[Optional[str], Optional[str], str]:
        compare_type = (compare_type or "mom").lower()
        if compare_type not in {"mom", "yoy", "custom"}:
            compare_type = "mom"

        if current_cycle and compare_cycle:
            return current_cycle, compare_cycle, "custom" if compare_type != "yoy" else compare_type

        calendar_last_month = shift_billing_cycle(datetime.now().strftime("%Y-%m"), -1)
        if not current_cycle:
            if calendar_last_month in available:
                current_cycle = calendar_last_month
            elif available:
                current_cycle = available[0]

        if current_cycle and not compare_cycle:
            offset = -12 if compare_type == "yoy" else -1
            candidate = shift_billing_cycle(current_cycle, offset)
            if candidate in available:
                compare_cycle = candidate
            elif len(available) >= 2:
                rest = [cycle for cycle in available if cycle != current_cycle]
                compare_cycle = rest[0] if rest else None
                if compare_type != "yoy":
                    compare_type = "custom" if compare_cycle != candidate else compare_type

        return current_cycle, compare_cycle, compare_type
