#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据校验器单元测试
"""

import pytest
from decimal import Decimal

from core.billing.data_validator import (
    BillingDataValidator,
    ValidationLevel,
    ValidationIssue,
    ValidationResult
)
from core.billing.cost_calculator import BillItem, SubscriptionType


class TestBillingDataValidator:
    """测试BillingDataValidator"""

    def test_validate_bss_data_success(self):
        """测试校验BSS数据（成功情况）"""
        validator = BillingDataValidator()

        items = [
            {
                'BillingDate': '2024-01-15',
                'BillingCycle': '2024-01',
                'InstanceID': 'i-abc123',
                'ProductCode': 'ecs',
                'SubscriptionType': 'PayAsYouGo',
                'PretaxGrossAmount': '100.50',
                'PretaxAmount': '90.45',
                'PaymentAmount': '0',
                'OutstandingAmount': '90.45',
                'InvoiceDiscount': '10.05',
                'DeductedByCoupons': '0',
                'DeductedByCashCoupons': '0',
                'DeductedByPrepaidCard': '0',
            }
        ]

        result = validator.validate_bss_data(items)

        assert result.is_valid
        assert result.validated_count == 1
        assert result.error_count == 0

    def test_validate_bss_data_missing_field(self):
        """测试校验BSS数据（缺失必填字段）"""
        validator = BillingDataValidator()

        items = [
            {
                'BillingDate': '2024-01-15',
                # 缺失 BillingCycle
                'InstanceID': 'i-abc123',
                'ProductCode': 'ecs',
                'SubscriptionType': 'PayAsYouGo',
                'PretaxAmount': '90.45',
            }
        ]

        result = validator.validate_bss_data(items)

        assert not result.is_valid
        assert result.error_count > 0
        errors = result.get_issues_by_level(ValidationLevel.ERROR)
        assert any('MISSING_REQUIRED_FIELD' in issue.code for issue in errors)

    def test_validate_bss_data_negative_amount(self):
        """测试校验BSS数据（负金额）"""
        validator = BillingDataValidator()

        items = [
            {
                'BillingDate': '2024-01-15',
                'BillingCycle': '2024-01',
                'InstanceID': 'i-abc123',
                'ProductCode': 'ecs',
                'SubscriptionType': 'PayAsYouGo',
                'PretaxGrossAmount': '-100',  # 负数
                'PretaxAmount': '90',
            }
        ]

        result = validator.validate_bss_data(items)

        assert not result.is_valid
        errors = result.get_issues_by_level(ValidationLevel.ERROR)
        assert any('NEGATIVE_AMOUNT' in issue.code for issue in errors)

    def test_validate_bss_data_invalid_numeric(self):
        """测试校验BSS数据（无效数值）"""
        validator = BillingDataValidator()

        items = [
            {
                'BillingDate': '2024-01-15',
                'BillingCycle': '2024-01',
                'InstanceID': 'i-abc123',
                'ProductCode': 'ecs',
                'SubscriptionType': 'PayAsYouGo',
                'PretaxAmount': 'invalid_number',  # 无效数值
            }
        ]

        result = validator.validate_bss_data(items)

        assert not result.is_valid
        errors = result.get_issues_by_level(ValidationLevel.ERROR)
        assert any('INVALID_NUMERIC_VALUE' in issue.code for issue in errors)

    def test_validate_bss_data_inconsistent_amount(self):
        """测试校验BSS数据（金额不一致）"""
        validator = BillingDataValidator()

        items = [
            {
                'BillingDate': '2024-01-15',
                'BillingCycle': '2024-01',
                'InstanceID': 'i-abc123',
                'ProductCode': 'ecs',
                'SubscriptionType': 'PayAsYouGo',
                'PretaxGrossAmount': '80',  # 原价更小
                'PretaxAmount': '100',  # 折扣价更大（异常）
            }
        ]

        result = validator.validate_bss_data(items)

        warnings = result.get_issues_by_level(ValidationLevel.WARNING)
        assert any('INCONSISTENT_AMOUNT' in issue.code for issue in warnings)

    def test_validate_subscription_missing_service_period(self):
        """测试校验Subscription缺失服务期间"""
        validator = BillingDataValidator()

        items = [
            {
                'BillingDate': '2024-01-15',
                'BillingCycle': '2024-01',
                'InstanceID': 'i-abc123',
                'ProductCode': 'ecs',
                'SubscriptionType': 'Subscription',  # 包年包月
                'PretaxAmount': '3000',
                # 缺失 ServicePeriod 和 ServicePeriodUnit
            }
        ]

        result = validator.validate_bss_data(items)

        warnings = result.get_issues_by_level(ValidationLevel.WARNING)
        assert any('MISSING_SERVICE_PERIOD' in issue.code for issue in warnings)

    def test_compare_data_sources_consistent(self):
        """测试数据源对比（一致）"""
        validator = BillingDataValidator()

        bss_items = [
            BillItem(
                billing_date='2024-01-01',
                billing_cycle='2024-01',
                account_id='test',
                instance_id='i-001',
                product_name='ECS',
                product_code='ecs',
                subscription_type=SubscriptionType.PAY_AS_YOU_GO,
                pretax_gross_amount=Decimal('100'),
                pretax_amount=Decimal('90'),
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('90'),
                invoice_discount=Decimal('10'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
            )
        ]

        mysql_items = [
            BillItem(
                billing_date='2024-01-01',
                billing_cycle='2024-01',
                account_id='test',
                instance_id='i-001',
                product_name='ECS',
                product_code='ecs',
                subscription_type=SubscriptionType.PAY_AS_YOU_GO,
                pretax_gross_amount=Decimal('100'),
                pretax_amount=Decimal('90'),  # 相同
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('90'),
                invoice_discount=Decimal('10'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
            )
        ]

        result = validator.compare_data_sources(bss_items, mysql_items)

        assert result.is_valid
        assert result.error_count == 0

    def test_compare_data_sources_missing_in_mysql(self):
        """测试数据源对比（MySQL中缺失）"""
        validator = BillingDataValidator()

        bss_items = [
            BillItem(
                billing_date='2024-01-01',
                billing_cycle='2024-01',
                account_id='test',
                instance_id='i-001',
                product_name='ECS',
                product_code='ecs',
                subscription_type=SubscriptionType.PAY_AS_YOU_GO,
                pretax_gross_amount=Decimal('100'),
                pretax_amount=Decimal('90'),
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('90'),
                invoice_discount=Decimal('10'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
            )
        ]

        mysql_items = []  # MySQL中无数据

        result = validator.compare_data_sources(bss_items, mysql_items)

        warnings = result.get_issues_by_level(ValidationLevel.WARNING)
        assert any('MISSING_IN_MYSQL' in issue.code for issue in warnings)

    def test_compare_data_sources_amount_mismatch(self):
        """测试数据源对比（金额不一致）"""
        validator = BillingDataValidator(tolerance=Decimal('0.01'))

        bss_items = [
            BillItem(
                billing_date='2024-01-01',
                billing_cycle='2024-01',
                account_id='test',
                instance_id='i-001',
                product_name='ECS',
                product_code='ecs',
                subscription_type=SubscriptionType.PAY_AS_YOU_GO,
                pretax_gross_amount=Decimal('100'),
                pretax_amount=Decimal('90'),  # BSS: 90元
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('90'),
                invoice_discount=Decimal('10'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
            )
        ]

        mysql_items = [
            BillItem(
                billing_date='2024-01-01',
                billing_cycle='2024-01',
                account_id='test',
                instance_id='i-001',
                product_name='ECS',
                product_code='ecs',
                subscription_type=SubscriptionType.PAY_AS_YOU_GO,
                pretax_gross_amount=Decimal('100'),
                pretax_amount=Decimal('85'),  # MySQL: 85元（不一致）
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('85'),
                invoice_discount=Decimal('15'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
            )
        ]

        result = validator.compare_data_sources(bss_items, mysql_items)

        warnings = result.get_issues_by_level(ValidationLevel.WARNING)
        assert any('AMOUNT_MISMATCH' in issue.code for issue in warnings)

    def test_validate_calculation_results(self):
        """测试校验计算结果"""
        validator = BillingDataValidator()

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
                pretax_amount=Decimal('90'),
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('90'),
                invoice_discount=Decimal('10'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
            )
        ]

        result = validator.validate_calculation_results(items, expected_total=Decimal('90'))

        assert result.is_valid
        assert result.error_count == 0

    def test_validate_calculation_results_negative_cost(self):
        """测试校验计算结果（负费用）"""
        validator = BillingDataValidator()

        items = [
            BillItem(
                billing_date='2024-01-01',
                billing_cycle='2024-01',
                account_id='test',
                instance_id='i-bad',
                product_name='ECS',
                product_code='ecs',
                subscription_type=SubscriptionType.PAY_AS_YOU_GO,
                pretax_gross_amount=Decimal('-100'),  # 负数
                pretax_amount=Decimal('-90'),
                payment_amount=Decimal('0'),
                outstanding_amount=Decimal('-90'),
                invoice_discount=Decimal('-10'),
                deducted_by_coupons=Decimal('0'),
                deducted_by_cash_coupons=Decimal('0'),
                deducted_by_prepaid_card=Decimal('0'),
            )
        ]

        result = validator.validate_calculation_results(items)

        assert not result.is_valid
        errors = result.get_issues_by_level(ValidationLevel.ERROR)
        assert any('NEGATIVE_DAILY_COST' in issue.code for issue in errors)

    def test_validation_issue_str(self):
        """测试ValidationIssue字符串表示"""
        issue = ValidationIssue(
            level=ValidationLevel.ERROR,
            code='TEST_ERROR',
            message='This is a test error',
            field='test_field',
            value='test_value',
            suggestion='Fix it'
        )

        issue_str = str(issue)
        assert 'ERROR' in issue_str
        assert 'TEST_ERROR' in issue_str
        assert 'test_field' in issue_str
        assert 'Fix it' in issue_str


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
