"""
Cost Analyzer
简化版成本分析器，提供续费价格查询和折扣建议
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

from cloudlens.models.resource import UnifiedResource

logger = logging.getLogger("CostAnalyzer")


class CostAnalyzer:
    """成本分析器"""

    @staticmethod
    def analyze_renewal_costs(instances: List[UnifiedResource]) -> Dict:
        """
        分析续费成本

        Args:
            instances: 资源实例列表

        Returns:
            分析结果字典
        """
        results = {
            "total_prepaid": 0,
            "expiring_soon": [],  # 30天内到期
            "high_value": [],  # 高价值实例（建议续费）
            "recommendations": [],
        }

        now = datetime.now()
        threshold = now + timedelta(days=30)

        for inst in instances:
            if inst.charge_type == "PrePaid" and inst.expired_time:
                results["total_prepaid"] += 1

                # 30天内到期
                if inst.expired_time <= threshold:
                    results["expiring_soon"].append(
                        {
                            "id": inst.id,
                            "name": inst.name,
                            "spec": inst.spec,
                            "expire_date": inst.expired_time.strftime("%Y-%m-%d"),
                            "days_left": (inst.expired_time - now).days,
                        }
                    )

                    # 生成续费建议
                    if (inst.expired_time - now).days <= 7:
                        urgency = "🔴 紧急"
                    elif (inst.expired_time - now).days <= 14:
                        urgency = "🟠 重要"
                    else:
                        urgency = "🟡 关注"

                    results["recommendations"].append(
                        {
                            "urgency": urgency,
                            "resource": f"{inst.name} ({inst.id})",
                            "action": f"建议在 {inst.expired_time.strftime('%Y-%m-%d')} 之前续费",
                            "days_left": (inst.expired_time - now).days,
                        }
                    )

        # 按紧急程度排序
        results["recommendations"].sort(key=lambda x: x["days_left"])

        return results

    @staticmethod
    def suggest_discount_optimization(instances: List[UnifiedResource]) -> List[Dict]:
        """
        折扣优化建议

        Returns:
            优化建议列表
        """
        suggestions = []

        # 统计按量付费实例
        postpaid_count = sum(1 for inst in instances if inst.charge_type == "PostPaid")

        if postpaid_count > 5:
            suggestions.append(
                {
                    "type": "包年包月转换",
                    "description": f"发现 {postpaid_count} 个按量付费实例，建议转换为包年包月以获得折扣",
                    "potential_saving": "约15-30%",
                    "action": "评估长期运行的实例并转换为包年包月",
                }
            )

        # 统计即将到期的预付费实例
        expiring = [
            inst
            for inst in instances
            if inst.charge_type == "PrePaid"
            and inst.expired_time
            and inst.expired_time <= datetime.now() + timedelta(days=30)
        ]

        if expiring:
            suggestions.append(
                {
                    "type": "批量续费折扣",
                    "description": f"有 {len(expiring)} 个实例即将到期，建议批量续费获取折扣",
                    "potential_saving": "约5-10%",
                    "action": "联系阿里云商务申请批量续费折扣",
                }
            )

        return suggestions

    @staticmethod
    def calculate_monthly_estimate(instances: List[UnifiedResource]) -> Dict:
        """
        估算月度成本（简化版，基于实例规格）

        Returns:
            成本估算
        """
        # 这里只是示例，实际价格需要调用阿里云询价API
        spec_price_map = {
            "ecs.g": 0.5,  # 通用型 约0.5元/小时
            "ecs.c": 0.4,  # 计算型
            "ecs.r": 0.6,  # 内存型
            "ecs.hf": 0.8,  # 高频型
        }

        total_estimate = 0
        breakdown = []

        for inst in instances:
            if inst.charge_type == "PostPaid":
                # 根据规格估算
                hourly_price = 0.5  # 默认价格
                for prefix, price in spec_price_map.items():
                    if inst.spec and inst.spec.startswith(prefix):
                        hourly_price = price
                        break

                monthly_cost = hourly_price * 24 * 30
                total_estimate += monthly_cost

                breakdown.append(
                    {
                        "id": inst.id,
                        "name": inst.name,
                        "spec": inst.spec,
                        "estimated_monthly": round(monthly_cost, 2),
                    }
                )

        return {
            "total_monthly_estimate": round(total_estimate, 2),
            "currency": "CNY",
            "note": "仅为估算，实际价格以阿里云账单为准",
            "breakdown": breakdown,
        }
