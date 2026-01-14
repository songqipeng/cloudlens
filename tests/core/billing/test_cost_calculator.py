#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
费用计算器单元测试
测试CostCalculator的各种计算逻辑
"""

import pytest
from datetime import datetime
from decimal import Decimal

from cloudlens.core.billing.cost_calculator import (
    CostCalculator,
    BillItem,
    SubscriptionType,
    CostCalculationResult
)


class TestBillItem:
    """测试BillItem数据模型"""

    def test_from_bss_api(self):
        """测试从BSS API响应构建BillItem"""
        api_response = {
            'BillingDate': '2024-01-15',
            'BillingCycle': '2024-01',
            'OwnerID': 'account123',
            'InstanceID': 'i-abc123',
            'ProductName': 'ECS',
            'ProductCode': 'ecs',
            'SubscriptionType': 'Subscription',
            'PretaxGrossAmount': '100.50',
            'PretaxAmount': '90.45',
            'PaymentAmount': '90.45',
            'OutstandingAmount': '0',
            'InvoiceDiscount': '10.05',
            'DeductedByCoupons': '0',
            'DeductedByCashCoupons': '0',
            'DeductedByPrepaidCard': '0',
            'ServicePeriod': '1',
            'ServicePeriodUnit': 'Month',
            'Region': 'cn-hangzhou',
        }

        item = BillItem.from_bss_api(api_response)

        assert item.billing_date == '2024-01-15'
        assert item.instance_id == 'i-abc123'
        assert item.subscription_type == 'Subscription'
        assert item.pretax_gross_amount == Decimal('100.50')
        assert item.pretax_amount == Decimal('90.45')
        assert item.service_period == '1'
        assert item.service_period_unit == 'Month'

    def test_from_mysql(self):
        """测试从MySQL查询结果构建BillItem"""
        mysql_row = {
            'billing_date': '2024-01-15',
            'billing_cycle': '2024-01',
            'account_id': 'account123',
            'instance_id': 'i-abc123',
            'product_name': 'ECS',
            'product_code': 'ecs',
            'subscription_type': 'PayAsYouGo',
            'pretax_gross_amount': 50.00,
            'pretax_amount': 45.00,
            'payment_amount': 0,
            'outstanding_amount': 45.00,
            'invoice_discount': 5.00,
            'deducted_by_coupons': 0,
            'deducted_by_cash_coupons': 0,
            'deducted_by_prepaid_card': 0,
            'region': 'cn-beijing',
        }

        item = BillItem.from_mysql(mysql_row)

        assert item.billing_date == '2024-01-15'
        assert item.subscription_type == 'PayAsYouGo'
        assert item.pretax_amount == Decimal('45.00')


class TestCostCalculator:
    """测试CostCalculator费用计算逻辑"""

    def test_subscription_daily_cost_with_service_period(self):
        """测试包年包月费用计算（有服务期间）"""
        # 场景：包年包月ECS，1个月，税前原价3000元
        item = BillItem(
            billing_date='2024-01-01',
            billing_cycle='2024-01',
            account_id='test_account',
            instance_id='i-test001',
            product_name='ECS',
            product_code='ecs',
            subscription_type=SubscriptionType.SUBSCRIPTION,
            pretax_gross_amount=Decimal('3000.00'),  # 原价3000元
            pretax_amount=Decimal('2700.00'),  # 折扣后2700元
            payment_amount=Decimal('2700.00'),
            outstanding_amount=Decimal('0'),
            invoice_discount=Decimal('300.00'),
            deducted_by_coupons=Decimal('0'),
            deducted_by_cash_coupons=Decimal('0'),
            deducted_by_prepaid_card=Decimal('0'),
            service_period='1',  # 1个月
            service_period_unit='Month',
        )

        result = CostCalculator.calculate_daily_cost(item)

        # 断言：3000元 / 30天 = 100元/天
        assert result.daily_cost == Decimal('100.00')
        assert result.total_cost == Decimal('3000.00')
        assert result.discount_amount == Decimal('300.00')
        assert result.discount_rate == Decimal('10.00')  # 10%折扣
        assert result.calculation_method == 'subscription_amortized'
        assert result.service_days == 30

    def test_subscription_daily_cost_without_service_period(self):
        """测试包年包月费用计算（无服务期间，使用默认值）"""
        item = BillItem(
            billing_date='2024-01-01',
            billing_cycle='2024-01',
            account_id='test_account',
            instance_id='i-test002',
            product_name='RDS',
            product_code='rds',
            subscription_type=SubscriptionType.SUBSCRIPTION,
            pretax_gross_amount=Decimal('1500.00'),
            pretax_amount=Decimal('1500.00'),
            payment_amount=Decimal('1500.00'),
            outstanding_amount=Decimal('0'),
            invoice_discount=Decimal('0'),
            deducted_by_coupons=Decimal('0'),
            deducted_by_cash_coupons=Decimal('0'),
            deducted_by_prepaid_card=Decimal('0'),
            service_period=None,  # 缺失服务期间
            service_period_unit=None,
        )

        result = CostCalculator.calculate_daily_cost(item)

        # 断言：使用默认30天，1500元 / 30天 = 50元/天
        assert result.daily_cost == Decimal('50.00')
        assert result.service_days is None

    def test_subscription_yearly_cost(self):
        """测试包年包月费用计算（年付）"""
        item = BillItem(
            billing_date='2024-01-01',
            billing_cycle='2024-01',
            account_id='test_account',
            instance_id='i-test003',
            product_name='ECS',
            product_code='ecs',
            subscription_type=SubscriptionType.SUBSCRIPTION,
            pretax_gross_amount=Decimal('36500.00'),  # 1年
            pretax_amount=Decimal('32850.00'),  # 10%折扣
            payment_amount=Decimal('32850.00'),
            outstanding_amount=Decimal('0'),
            invoice_discount=Decimal('3650.00'),
            deducted_by_coupons=Decimal('0'),
            deducted_by_cash_coupons=Decimal('0'),
            deducted_by_prepaid_card=Decimal('0'),
            service_period='1',
            service_period_unit='Year',
        )

        result = CostCalculator.calculate_daily_cost(item)

        # 断言：36500元 / 365天 = 100元/天
        assert result.daily_cost == Decimal('100.00')
        assert result.service_days == 365

    def test_payg_daily_cost(self):
        """测试按量付费费用计算"""
        # 场景：按量付费ECS，当天费用100元
        item = BillItem(
            billing_date='2024-01-15',
            billing_cycle='2024-01',
            account_id='test_account',
            instance_id='i-test004',
            product_name='ECS',
            product_code='ecs',
            subscription_type=SubscriptionType.PAY_AS_YOU_GO,
            pretax_gross_amount=Decimal('120.00'),  # 原价
            pretax_amount=Decimal('100.00'),  # 折扣后
            payment_amount=Decimal('0'),  # 按量付费通常未结算
            outstanding_amount=Decimal('100.00'),  # 未付金额
            invoice_discount=Decimal('20.00'),
            deducted_by_coupons=Decimal('0'),
            deducted_by_cash_coupons=Decimal('0'),
            deducted_by_prepaid_card=Decimal('0'),
        )

        result = CostCalculator.calculate_daily_cost(item)

        # 断言：按量付费直接使用当天费用，不分摊
        assert result.daily_cost == Decimal('100.00')
        assert result.total_cost == Decimal('100.00')
        assert result.discount_amount == Decimal('20.00')
        assert result.discount_rate == Decimal('16.67')  # 约16.67%
        assert result.calculation_method == 'payg_direct'
        assert result.service_days is None

    def test_calculate_service_days_month(self):
        """测试服务天数计算（月）"""
        days = CostCalculator._calculate_service_days('3', 'Month')
        assert days == 90  # 3个月 * 30天

    def test_calculate_service_days_day(self):
        """测试服务天数计算（天）"""
        days = CostCalculator._calculate_service_days('15', 'Day')
        assert days == 15

    def test_calculate_service_days_year(self):
        """测试服务天数计算（年）"""
        days = CostCalculator._calculate_service_days('1', 'Year')
        assert days == 365

    def test_calculate_service_days_invalid(self):
        """测试服务天数计算（无效输入）"""
        days = CostCalculator._calculate_service_days(None, None)
        assert days == 0

        days = CostCalculator._calculate_service_days('abc', 'Month')
        assert days == 0

    def test_calculate_period_cost(self):
        """测试时间段费用计算"""
        items = [
            BillItem(
                billing_date='2024-01-01',
                billing_cycle='2024-01',
                account_id='test',
                instance_id='i-001',
                product_name='ECS',
                product_code='ecs',
                subscription_type=SubscriptionType.PAY_AS_YOU_GO,
                pretax_gross_amount=Decimal('100'),
                pretax_amount=Decimal('100'),
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('100'),
                invoice_discount=Decimal('0'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
            ),
            BillItem(
                billing_date='2024-01-02',
                billing_cycle='2024-01',
                account_id='test',
                instance_id='i-001',
                product_name='ECS',
                product_code='ecs',
                subscription_type=SubscriptionType.PAY_AS_YOU_GO,
                pretax_gross_amount=Decimal('150'),
                pretax_amount=Decimal('150'),
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('150'),
                invoice_discount=Decimal('0'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
            ),
        ]

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)

        result = CostCalculator.calculate_period_cost(items, start_date, end_date)

        assert result['total_cost'] == 250.0  # 100 + 150
        assert result['days'] == 2

    def test_calculate_period_cost_with_grouping(self):
        """测试时间段费用计算（分组）"""
        items = [
            BillItem(
                billing_date='2024-01-01',
                billing_cycle='2024-01',
                account_id='test',
                instance_id='i-001',
                product_name='ECS',
                product_code='ecs',
                subscription_type=SubscriptionType.PAY_AS_YOU_GO,
                pretax_gross_amount=Decimal('100'),
                pretax_amount=Decimal('100'),
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('100'),
                invoice_discount=Decimal('0'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
                region='cn-hangzhou',
            ),
            BillItem(
                billing_date='2024-01-01',
                billing_cycle='2024-01',
                account_id='test',
                instance_id='i-002',
                product_name='RDS',
                product_code='rds',
                subscription_type=SubscriptionType.PAY_AS_YOU_GO,
                pretax_gross_amount=Decimal('200'),
                pretax_amount=Decimal('200'),
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('200'),
                invoice_discount=Decimal('0'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
                region='cn-beijing',
            ),
        ]

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)

        result = CostCalculator.calculate_period_cost(items, start_date, end_date, group_by='region')

        assert result['group_by'] == 'region'
        assert result['grouped_cost']['cn-hangzhou'] == 100.0
        assert result['grouped_cost']['cn-beijing'] == 200.0
        assert result['total_cost'] == 300.0

    def test_calculate_discount_summary(self):
        """测试折扣汇总计算"""
        items = [
            BillItem(
                billing_date='2024-01-01',
                billing_cycle='2024-01',
                account_id='test',
                instance_id='i-001',
                product_name='ECS',
                product_code='ecs',
                subscription_type=SubscriptionType.PAY_AS_YOU_GO,
                pretax_gross_amount=Decimal('1000'),
                pretax_amount=Decimal('900'),  # 10%折扣
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('900'),
                invoice_discount=Decimal('100'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
            ),
            BillItem(
                billing_date='2024-01-01',
                billing_cycle='2024-01',
                account_id='test',
                instance_id='i-002',
                product_name='RDS',
                product_code='rds',
                subscription_type=SubscriptionType.PAY_AS_YOU_GO,
                pretax_gross_amount=Decimal('2000'),
                pretax_amount=Decimal('1600'),  # 20%折扣
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('1600'),
                invoice_discount=Decimal('400'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
            ),
        ]

        result = CostCalculator.calculate_discount_summary(items)

        assert result['total_gross_amount'] == 3000.0
        assert result['total_pretax_amount'] == 2500.0
        assert result['total_discount_amount'] == 500.0
        assert result['average_discount_rate'] == 16.67  # (500/3000)*100
        assert result['item_count'] == 2

    def test_zero_cost_item(self):
        """测试零费用项"""
        item = BillItem(
            billing_date='2024-01-01',
            billing_cycle='2024-01',
            account_id='test',
            instance_id='i-zero',
            product_name='ECS',
            product_code='ecs',
            subscription_type=SubscriptionType.PAY_AS_YOU_GO,
            pretax_gross_amount=Decimal('0'),
            pretax_amount=Decimal('0'),
            payment_amount=Decimal('0'),
            outstanding_amount=Decimal('0'),
            invoice_discount=Decimal('0'),
            deducted_by_coupons=Decimal('0'),
            deducted_by_cash_coupons=Decimal('0'),
            deducted_by_prepaid_card=Decimal('0'),
        )

        result = CostCalculator.calculate_daily_cost(item)

        assert result.daily_cost == Decimal('0')
        assert result.discount_rate == Decimal('0')

    def test_decimal_precision(self):
        """测试Decimal精度（避免浮点数误差）"""
        item = BillItem(
            billing_date='2024-01-01',
            billing_cycle='2024-01',
            account_id='test',
            instance_id='i-precision',
            product_name='ECS',
            product_code='ecs',
            subscription_type=SubscriptionType.SUBSCRIPTION,
            pretax_gross_amount=Decimal('100.333'),
            pretax_amount=Decimal('90.299'),
            payment_amount=Decimal('90.299'),
            outstanding_amount=Decimal('0'),
            invoice_discount=Decimal('10.034'),
            deducted_by_coupons=Decimal('0'),
            deducted_by_cash_coupons=Decimal('0'),
            deducted_by_prepaid_card=Decimal('0'),
            service_period='1',
            service_period_unit='Month',
        )

        result = CostCalculator.calculate_daily_cost(item)

        # 断言：100.333 / 30 = 3.34（四舍五入到2位小数）
        assert result.daily_cost == Decimal('3.34')
        assert isinstance(result.daily_cost, Decimal)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
