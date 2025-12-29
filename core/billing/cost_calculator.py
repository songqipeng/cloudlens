#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的费用计算模块
解决账单计算逻辑不一致的问题，提供标准化的费用计算接口

主要功能：
1. 统一处理Subscription（包年包月）和PayAsYouGo（按量付费）的费用计算
2. 按服务期间分摊费用
3. 计算每日费用
4. 处理折扣和优惠
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SubscriptionType(str, Enum):
    """订阅类型"""
    SUBSCRIPTION = "Subscription"  # 包年包月
    PAY_AS_YOU_GO = "PayAsYouGo"  # 按量付费


@dataclass
class BillItem:
    """账单明细项（统一数据模型）"""
    # 基础信息
    billing_date: str  # 账单日期 YYYY-MM-DD
    billing_cycle: str  # 账期 YYYY-MM
    account_id: str
    instance_id: str

    # 产品信息
    product_name: str
    product_code: str
    subscription_type: str  # Subscription or PayAsYouGo

    # 价格信息（使用Decimal保证精度）
    pretax_gross_amount: Decimal  # 税前原价（未折扣）
    pretax_amount: Decimal  # 税前应付（折扣后）
    payment_amount: Decimal  # 实付金额
    outstanding_amount: Decimal  # 未付金额
    invoice_discount: Decimal  # 发票折扣

    # 抵扣信息
    deducted_by_coupons: Decimal  # 优惠券抵扣
    deducted_by_cash_coupons: Decimal  # 代金券抵扣
    deducted_by_prepaid_card: Decimal  # 预付卡抵扣

    # 服务期间（用于包年包月分摊）
    service_period: Optional[str] = None  # 服务期间（如 "1" 表示1个月）
    service_period_unit: Optional[str] = None  # 单位（Month、Day等）

    # 区域和标签
    region: Optional[str] = None
    zone: Optional[str] = None
    tag: Optional[str] = None

    @classmethod
    def from_bss_api(cls, item: Dict) -> 'BillItem':
        """从BSS API响应构建BillItem"""
        return cls(
            billing_date=item.get('BillingDate', ''),
            billing_cycle=item.get('BillingCycle', ''),
            account_id=item.get('OwnerID', ''),
            instance_id=item.get('InstanceID', ''),
            product_name=item.get('ProductName', ''),
            product_code=item.get('ProductCode', ''),
            subscription_type=item.get('SubscriptionType', ''),
            pretax_gross_amount=Decimal(str(item.get('PretaxGrossAmount', 0))),
            pretax_amount=Decimal(str(item.get('PretaxAmount', 0))),
            payment_amount=Decimal(str(item.get('PaymentAmount', 0))),
            outstanding_amount=Decimal(str(item.get('OutstandingAmount', 0))),
            invoice_discount=Decimal(str(item.get('InvoiceDiscount', 0))),
            deducted_by_coupons=Decimal(str(item.get('DeductedByCoupons', 0))),
            deducted_by_cash_coupons=Decimal(str(item.get('DeductedByCashCoupons', 0))),
            deducted_by_prepaid_card=Decimal(str(item.get('DeductedByPrepaidCard', 0))),
            service_period=item.get('ServicePeriod'),
            service_period_unit=item.get('ServicePeriodUnit'),
            region=item.get('Region'),
            zone=item.get('Zone'),
            tag=item.get('Tag'),
        )

    @classmethod
    def from_mysql(cls, row: Dict) -> 'BillItem':
        """从MySQL查询结果构建BillItem"""
        return cls(
            billing_date=row.get('billing_date', ''),
            billing_cycle=row.get('billing_cycle', ''),
            account_id=row.get('account_id', ''),
            instance_id=row.get('instance_id', ''),
            product_name=row.get('product_name', ''),
            product_code=row.get('product_code', ''),
            subscription_type=row.get('subscription_type', ''),
            pretax_gross_amount=Decimal(str(row.get('pretax_gross_amount', 0) or 0)),
            pretax_amount=Decimal(str(row.get('pretax_amount', 0) or 0)),
            payment_amount=Decimal(str(row.get('payment_amount', 0) or 0)),
            outstanding_amount=Decimal(str(row.get('outstanding_amount', 0) or 0)),
            invoice_discount=Decimal(str(row.get('invoice_discount', 0) or 0)),
            deducted_by_coupons=Decimal(str(row.get('deducted_by_coupons', 0) or 0)),
            deducted_by_cash_coupons=Decimal(str(row.get('deducted_by_cash_coupons', 0) or 0)),
            deducted_by_prepaid_card=Decimal(str(row.get('deducted_by_prepaid_card', 0) or 0)),
            service_period=row.get('service_period'),
            service_period_unit=row.get('service_period_unit'),
            region=row.get('region'),
            zone=row.get('zone'),
            tag=row.get('tag'),
        )


@dataclass
class CostCalculationResult:
    """费用计算结果"""
    total_cost: Decimal  # 总费用
    daily_cost: Decimal  # 每日费用
    discount_amount: Decimal  # 折扣金额
    discount_rate: Decimal  # 折扣率（百分比）
    calculation_method: str  # 计算方法（subscription_amortized, payg_direct等）
    service_days: Optional[int] = None  # 服务天数（Subscription）
    notes: Optional[str] = None  # 备注

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'total_cost': float(self.total_cost),
            'daily_cost': float(self.daily_cost),
            'discount_amount': float(self.discount_amount),
            'discount_rate': float(self.discount_rate),
            'calculation_method': self.calculation_method,
            'service_days': self.service_days,
            'notes': self.notes,
        }


class CostCalculator:
    """
    统一的费用计算器

    设计原则：
    1. 单一数据源：优先使用BSS API数据，MySQL仅作缓存
    2. 精确计算：使用Decimal避免浮点数误差
    3. 类型区分：Subscription和PayAsYouGo使用不同的计算逻辑
    4. 可追溯：返回计算方法和备注，便于审计
    """

    # 每月平均天数（用于月度到日均的换算）
    DAYS_PER_MONTH = Decimal('30')

    @staticmethod
    def calculate_daily_cost(bill_item: BillItem, target_date: Optional[datetime] = None) -> CostCalculationResult:
        """
        计算每日费用（核心方法）

        Args:
            bill_item: 账单明细项
            target_date: 目标日期（用于判断是否在服务期内），默认使用billing_date

        Returns:
            CostCalculationResult: 费用计算结果

        逻辑说明：
        1. Subscription（包年包月）：
           - 使用PretaxGrossAmount（税前原价）
           - 按服务期间分摊到每天
           - 计算公式：daily_cost = PretaxGrossAmount / service_days

        2. PayAsYouGo（按量付费）：
           - 使用PretaxAmount（税前应付）
           - 直接使用当天的账单金额，不分摊
           - 计算公式：daily_cost = PretaxAmount
        """
        if target_date is None:
            target_date = datetime.strptime(bill_item.billing_date, '%Y-%m-%d')

        subscription_type = bill_item.subscription_type

        if subscription_type == SubscriptionType.SUBSCRIPTION:
            return CostCalculator._calculate_subscription_daily_cost(bill_item, target_date)
        elif subscription_type == SubscriptionType.PAY_AS_YOU_GO:
            return CostCalculator._calculate_payg_daily_cost(bill_item, target_date)
        else:
            # 未知类型，使用保守策略（直接使用PretaxAmount）
            logger.warning(f"Unknown subscription type: {subscription_type}, using conservative calculation")
            return CostCalculationResult(
                total_cost=bill_item.pretax_amount,
                daily_cost=bill_item.pretax_amount,
                discount_amount=Decimal('0'),
                discount_rate=Decimal('0'),
                calculation_method='unknown_direct',
                notes=f'Unknown subscription type: {subscription_type}'
            )

    @staticmethod
    def _calculate_subscription_daily_cost(bill_item: BillItem, target_date: datetime) -> CostCalculationResult:
        """
        计算包年包月的每日费用

        逻辑：
        1. 使用PretaxGrossAmount（税前原价，未打折前的金额）
        2. 计算服务天数（从service_period和service_period_unit）
        3. 按天分摊：daily_cost = PretaxGrossAmount / service_days
        4. 计算折扣：discount_amount = PretaxGrossAmount - PretaxAmount
        """
        # 获取服务天数
        service_days = CostCalculator._calculate_service_days(
            bill_item.service_period,
            bill_item.service_period_unit
        )

        # 使用PretaxGrossAmount（税前原价）进行分摊
        total_cost = bill_item.pretax_gross_amount

        # 按天分摊
        if service_days > 0:
            daily_cost = (total_cost / Decimal(str(service_days))).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        else:
            # 无法获取服务期间，使用月度平均
            daily_cost = (total_cost / CostCalculator.DAYS_PER_MONTH).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            logger.warning(
                f"No service period for Subscription item {bill_item.instance_id}, "
                f"using monthly average (30 days)"
            )

        # 计算折扣
        discount_amount = bill_item.pretax_gross_amount - bill_item.pretax_amount
        discount_rate = Decimal('0')
        if bill_item.pretax_gross_amount > 0:
            discount_rate = (discount_amount / bill_item.pretax_gross_amount * 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

        return CostCalculationResult(
            total_cost=total_cost,
            daily_cost=daily_cost,
            discount_amount=discount_amount,
            discount_rate=discount_rate,
            calculation_method='subscription_amortized',
            service_days=service_days if service_days > 0 else None,
            notes=f'Amortized over {service_days} days' if service_days > 0 else 'Amortized over 30 days (default)'
        )

    @staticmethod
    def _calculate_payg_daily_cost(bill_item: BillItem, target_date: datetime) -> CostCalculationResult:
        """
        计算按量付费的每日费用

        逻辑：
        1. 使用PretaxAmount（税前应付，已包含折扣）
        2. 直接使用当天的账单金额，不进行分摊
        3. daily_cost = PretaxAmount（就是当天的实际费用）
        """
        # 按量付费直接使用当天的费用，不分摊
        total_cost = bill_item.pretax_amount
        daily_cost = bill_item.pretax_amount

        # 计算折扣
        discount_amount = bill_item.pretax_gross_amount - bill_item.pretax_amount
        discount_rate = Decimal('0')
        if bill_item.pretax_gross_amount > 0:
            discount_rate = (discount_amount / bill_item.pretax_gross_amount * 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

        return CostCalculationResult(
            total_cost=total_cost,
            daily_cost=daily_cost,
            discount_amount=discount_amount,
            discount_rate=discount_rate,
            calculation_method='payg_direct',
            notes='PayAsYouGo: direct daily cost, no amortization'
        )

    @staticmethod
    def _calculate_service_days(service_period: Optional[str], service_period_unit: Optional[str]) -> int:
        """
        计算服务天数

        Args:
            service_period: 服务期间数值（如 "1", "3", "12"）
            service_period_unit: 服务期间单位（Month, Day, Year等）

        Returns:
            服务天数（整数）
        """
        if not service_period or not service_period_unit:
            return 0

        try:
            period_value = int(service_period)
        except (ValueError, TypeError):
            logger.warning(f"Invalid service_period: {service_period}")
            return 0

        unit = service_period_unit.lower()

        if unit in ['month', 'months']:
            return period_value * 30  # 简化：每月按30天
        elif unit in ['day', 'days']:
            return period_value
        elif unit in ['year', 'years']:
            return period_value * 365
        elif unit in ['hour', 'hours']:
            return max(1, period_value // 24)  # 小时转天，至少1天
        else:
            logger.warning(f"Unknown service_period_unit: {service_period_unit}")
            return 0

    @staticmethod
    def calculate_period_cost(
        bill_items: List[BillItem],
        start_date: datetime,
        end_date: datetime,
        group_by: Optional[str] = None
    ) -> Dict:
        """
        计算指定时间段的总费用

        Args:
            bill_items: 账单明细列表
            start_date: 开始日期
            end_date: 结束日期
            group_by: 分组字段（product_code, region, instance_id等）

        Returns:
            费用汇总结果
        """
        from collections import defaultdict

        # 按日期筛选
        date_range = set()
        current = start_date
        while current <= end_date:
            date_range.add(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

        # 计算费用
        if group_by:
            grouped_cost = defaultdict(Decimal)
            for item in bill_items:
                if item.billing_date in date_range:
                    result = CostCalculator.calculate_daily_cost(item)
                    key = getattr(item, group_by, 'unknown')
                    grouped_cost[key] += result.daily_cost

            return {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'days': len(date_range),
                'group_by': group_by,
                'grouped_cost': {k: float(v) for k, v in grouped_cost.items()},
                'total_cost': float(sum(grouped_cost.values()))
            }
        else:
            total_cost = Decimal('0')
            for item in bill_items:
                if item.billing_date in date_range:
                    result = CostCalculator.calculate_daily_cost(item)
                    total_cost += result.daily_cost

            return {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'days': len(date_range),
                'total_cost': float(total_cost)
            }

    @staticmethod
    def calculate_discount_summary(bill_items: List[BillItem]) -> Dict:
        """
        计算折扣汇总

        Args:
            bill_items: 账单明细列表

        Returns:
            折扣汇总结果
        """
        total_gross = Decimal('0')
        total_pretax = Decimal('0')
        total_discount = Decimal('0')

        for item in bill_items:
            total_gross += item.pretax_gross_amount
            total_pretax += item.pretax_amount
            result = CostCalculator.calculate_daily_cost(item)
            total_discount += result.discount_amount

        average_discount_rate = Decimal('0')
        if total_gross > 0:
            average_discount_rate = (total_discount / total_gross * 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

        return {
            'total_gross_amount': float(total_gross),
            'total_pretax_amount': float(total_pretax),
            'total_discount_amount': float(total_discount),
            'average_discount_rate': float(average_discount_rate),
            'item_count': len(bill_items)
        }
