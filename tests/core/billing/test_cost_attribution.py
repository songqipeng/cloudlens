#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成本归因引擎单元测试。"""

from cloudlens.core.cost_attribution import (
    ProductPeriodStats,
    aggregate_product_stats,
    attribute_product_changes,
    build_attribution_report,
    generate_recommendations,
    shift_billing_cycle,
)


def _stats(
    code: str,
    pretax: float,
    discount: float = 0.0,
    usage: float = 0.0,
    instance_count: int = 1,
    name: str = "",
) -> ProductPeriodStats:
    return ProductPeriodStats(
        product_code=code,
        product_name=name or code.upper(),
        pretax=pretax,
        discount=discount,
        usage=usage,
        instance_count=instance_count,
    )


class TestShiftBillingCycle:
    def test_shift_backward(self) -> None:
        assert shift_billing_cycle("2026-01", -1) == "2025-12"

    def test_shift_year(self) -> None:
        assert shift_billing_cycle("2026-08", -12) == "2025-08"


class TestAggregateProductStats:
    def test_aggregate_rows(self) -> None:
        rows = [
            {"product_code": "ecs", "product_name": "ECS", "pretax": 100, "discount": 10, "usage": 0, "instance_count": 2},
            {"product_code": "ecs", "product_name": "ECS", "pretax": 50, "discount": 5, "usage": 0, "instance_count": 1},
            {"product_code": "oss", "product_name": "OSS", "pretax": 20, "discount": 0, "usage": 100, "instance_count": 1},
        ]
        result = aggregate_product_stats(rows)
        assert result["ecs"].pretax == 150
        assert result["ecs"].instance_count == 3
        assert result["oss"].usage == 100


class TestAttributeProductChanges:
    def test_quantity_increase(self) -> None:
        previous = {"ecs": _stats("ecs", pretax=100, instance_count=2)}
        current = {"ecs": _stats("ecs", pretax=150, instance_count=3)}
        deltas = attribute_product_changes(current, previous)
        assert len(deltas) == 1
        item = deltas[0]
        assert item.status == "existing"
        assert item.quantity_effect > 0
        assert abs(item.delta - (item.quantity_effect + item.price_effect + item.discount_effect + item.residual)) < 0.05

    def test_discount_drop_increases_cost(self) -> None:
        # 上期：应付 80，折扣 20，折扣率 20%
        previous = {"ecs": _stats("ecs", pretax=80, discount=20, instance_count=1)}
        # 本期：应付 90，折扣 10，折扣率约 10%，数量不变
        current = {"ecs": _stats("ecs", pretax=90, discount=10, instance_count=1)}
        item = attribute_product_changes(current, previous)[0]
        assert item.discount_effect > 0
        assert abs(item.quantity_effect) < 0.01

    def test_new_product_goes_to_mix(self) -> None:
        previous = {"ecs": _stats("ecs", pretax=100)}
        current = {"ecs": _stats("ecs", pretax=100), "rds": _stats("rds", pretax=40)}
        deltas = {row.product_code: row for row in attribute_product_changes(current, previous)}
        assert deltas["rds"].status == "new"
        assert deltas["rds"].mix_effect == 40

    def test_removed_product_goes_to_mix(self) -> None:
        previous = {"ecs": _stats("ecs", pretax=100), "cdn": _stats("cdn", pretax=30)}
        current = {"ecs": _stats("ecs", pretax=100)}
        deltas = {row.product_code: row for row in attribute_product_changes(current, previous)}
        assert deltas["cdn"].status == "removed"
        assert deltas["cdn"].mix_effect == -30

    def test_usage_based_quantity(self) -> None:
        previous = {"oss": _stats("oss", pretax=100, usage=100, instance_count=1)}
        current = {"oss": _stats("oss", pretax=150, usage=150, instance_count=1)}
        item = attribute_product_changes(current, previous)[0]
        assert item.quantity_effect > 40
        assert abs(item.price_effect) < 5


class TestBuildAttributionReport:
    def test_report_totals_and_categories(self) -> None:
        previous = {
            "ecs": _stats("ecs", pretax=100, discount=20, instance_count=2, name="ECS"),
        }
        current = {
            "ecs": _stats("ecs", pretax=130, discount=10, instance_count=3, name="ECS"),
            "rds": _stats("rds", pretax=40, instance_count=1, name="RDS"),
        }
        report = build_attribution_report(current, previous, "2026-08", "2026-07")
        assert report["current_total"] == 170
        assert report["compare_total"] == 100
        assert report["delta"] == 70
        categories = {item["category"] for item in report["attributions"]}
        assert "product_mix" in categories
        assert report["recommendations"]

    def test_flat_cost_recommendation(self) -> None:
        stats = {"ecs": _stats("ecs", pretax=100, instance_count=1)}
        report = build_attribution_report(stats, stats, "2026-08", "2026-07")
        assert report["delta"] == 0
        assert report["recommendations"][0]["category"] == "other"


class TestRecommendations:
    def test_discount_high_priority(self) -> None:
        recs = generate_recommendations(
            [
                {
                    "category": "discount",
                    "impact": 3200,
                    "details": [{"product_name": "ECS", "product_code": "ecs"}],
                }
            ],
            total_delta=3200,
        )
        assert recs[0]["priority"] == "high"
        assert recs[0]["category"] == "discount"
