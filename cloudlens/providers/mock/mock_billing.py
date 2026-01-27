# -*- coding: utf-8 -*-
"""
Mock Billing Data - 模拟中型互联网公司的账单和成本数据

规模设定：
- 月均云支出：约500万人民币
- 平均折扣：3折左右（25%-35%）
- 历史数据：3年（36个月）
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 使用固定种子确保数据一致性
random.seed(42)

# 产品代码和名称映射
PRODUCT_MAP = {
    "ecs": "云服务器 ECS",
    "rds": "云数据库RDS版",
    "kvstore": "云数据库Redis版",
    "slb": "负载均衡",
    "eip": "弹性公网IP",
    "oss": "对象存储OSS",
    "vpc": "专有网络VPC",
    "nat": "NAT网关",
    "cdn": "CDN",
    "mongodb": "MongoDB",
    "polardb": "云数据库PolarDB",
    "ecs_disk": "云盘",
}


class MockBillingService:
    """模拟账单服务"""

    @staticmethod
    def generate_billing_overview(billing_cycle: str, account_name: str) -> Dict[str, Any]:
        """生成账单概览数据"""
        # 解析年月
        year, month = map(int, billing_cycle.split("-"))
        
        # 基础月成本约500万，有波动
        base_total = 5000000
        variation = random.uniform(-0.15, 0.15)  # ±15%波动
        total_pretax = base_total * (1 + variation)
        
        # 按产品分配成本
        product_distribution = {
            "ecs": 0.35,      # 35% ECS
            "rds": 0.20,      # 20% RDS
            "kvstore": 0.08,  # 8% Redis
            "slb": 0.05,      # 5% SLB
            "eip": 0.04,      # 4% EIP
            "oss": 0.10,      # 10% OSS
            "vpc": 0.03,      # 3% VPC
            "nat": 0.05,      # 5% NAT
            "cdn": 0.06,      # 6% CDN
            "mongodb": 0.02,  # 2% MongoDB
            "polardb": 0.02,  # 2% PolarDB
        }
        
        by_product = {}
        by_product_name = {}
        for product_code, ratio in product_distribution.items():
            amount = total_pretax * ratio
            by_product[product_code] = amount
            by_product_name[product_code] = PRODUCT_MAP.get(product_code, product_code)
        
        # 应用折扣（3折左右）
        avg_discount = random.uniform(0.25, 0.35)
        total_discount = total_pretax * avg_discount
        total_paid = total_pretax - total_discount
        
        return {
            "billing_cycle": billing_cycle,
            "total_pretax": total_pretax,
            "total_discount": total_discount,
            "total_paid": total_paid,
            "avg_discount_rate": avg_discount,
            "by_product": by_product,
            "by_product_name": by_product_name,
        }

    @staticmethod
    def generate_instance_bills(
        product_code: str, 
        billing_cycle: str, 
        subscription_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """生成实例账单数据"""
        items = []
        
        # 根据产品类型生成不同数量的实例账单
        instance_counts = {
            "ecs": 800,
            "rds": 120,
            "kvstore": 80,
            "slb": 50,
            "eip": 100,
            "oss": 200,
            "vpc": 30,
            "nat": 20,
            "cdn": 150,
            "mongodb": 40,
            "polardb": 30,
        }
        
        count = instance_counts.get(product_code, 50)
        
        for i in range(count):
            # 基础价格
            base_price = random.uniform(100, 10000)
            
            # 应用折扣（不同实例折扣略有差异）
            discount_rate = random.uniform(0.20, 0.40)  # 2折到4折
            discount_amount = base_price * discount_rate
            payment_amount = base_price - discount_amount
            
            # 订阅类型
            sub_type = subscription_type or random.choice(["Subscription", "PayAsYouGo"])
            
            items.append({
                "ProductCode": product_code,
                "ProductName": PRODUCT_MAP.get(product_code, product_code),
                "SubscriptionType": sub_type,
                "PretaxAmount": base_price,
                "DiscountAmount": discount_amount,
                "PaymentAmount": payment_amount,
                "InstanceID": f"{product_code}-mock-{i+1:06d}",
                "BillingCycle": billing_cycle,
            })
        
        return items

    @staticmethod
    def generate_historical_bills(months: int = 36) -> List[Dict[str, Any]]:
        """生成历史账单数据（3年）"""
        bills = []
        today = datetime.now()
        
        for i in range(months):
            date = today - timedelta(days=30 * (months - i))
            billing_cycle = date.strftime("%Y-%m")
            
            bill = MockBillingService.generate_billing_overview(billing_cycle, "mock-prod")
            bills.append(bill)
        
        return bills
