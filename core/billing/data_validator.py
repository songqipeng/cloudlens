#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单数据校验模块
提供BSS API数据校验、数据源一致性检查等功能
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from .cost_calculator import BillItem, CostCalculator

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """校验级别"""
    ERROR = "error"  # 错误，必须修复
    WARNING = "warning"  # 警告，建议修复
    INFO = "info"  # 信息，供参考


@dataclass
class ValidationIssue:
    """校验问题"""
    level: ValidationLevel
    code: str  # 问题代码（如 MISSING_FIELD, NEGATIVE_AMOUNT等）
    message: str  # 问题描述
    field: Optional[str] = None  # 相关字段
    value: Optional[str] = None  # 问题值
    suggestion: Optional[str] = None  # 修复建议

    def __str__(self):
        parts = [f"[{self.level.value.upper()}] {self.code}: {self.message}"]
        if self.field:
            parts.append(f"  Field: {self.field}")
        if self.value:
            parts.append(f"  Value: {self.value}")
        if self.suggestion:
            parts.append(f"  Suggestion: {self.suggestion}")
        return "\n".join(parts)


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool  # 是否通过校验（无ERROR级别问题）
    issues: List[ValidationIssue]  # 问题列表
    validated_count: int  # 已校验的记录数
    error_count: int = 0  # 错误数量
    warning_count: int = 0  # 警告数量
    info_count: int = 0  # 信息数量

    def add_issue(self, issue: ValidationIssue):
        """添加校验问题"""
        self.issues.append(issue)
        if issue.level == ValidationLevel.ERROR:
            self.error_count += 1
            self.is_valid = False
        elif issue.level == ValidationLevel.WARNING:
            self.warning_count += 1
        elif issue.level == ValidationLevel.INFO:
            self.info_count += 1

    def get_summary(self) -> str:
        """获取校验摘要"""
        return (
            f"Validation Result: {'PASSED' if self.is_valid else 'FAILED'}\n"
            f"Validated: {self.validated_count} records\n"
            f"Errors: {self.error_count}, Warnings: {self.warning_count}, Info: {self.info_count}"
        )

    def get_issues_by_level(self, level: ValidationLevel) -> List[ValidationIssue]:
        """获取指定级别的问题"""
        return [issue for issue in self.issues if issue.level == level]


class BillingDataValidator:
    """
    账单数据校验器

    主要功能：
    1. BSS API数据校验（必填字段、数据类型、逻辑一致性）
    2. 数据源一致性检查（BSS API vs MySQL）
    3. 费用计算结果验证
    """

    # 必填字段
    REQUIRED_FIELDS = {
        'BillingDate', 'BillingCycle', 'InstanceID',
        'ProductCode', 'SubscriptionType', 'PretaxAmount'
    }

    # 数值字段
    NUMERIC_FIELDS = {
        'PretaxGrossAmount', 'PretaxAmount', 'PaymentAmount',
        'OutstandingAmount', 'InvoiceDiscount', 'DeductedByCoupons',
        'DeductedByCashCoupons', 'DeductedByPrepaidCard'
    }

    def __init__(self, tolerance: Decimal = Decimal('0.01')):
        """
        初始化校验器

        Args:
            tolerance: 金额比较的容差（默认0.01元，即1分）
        """
        self.tolerance = tolerance

    def validate_bss_data(self, items: List[Dict]) -> ValidationResult:
        """
        校验BSS API返回的数据

        Args:
            items: BSS API返回的账单明细列表

        Returns:
            ValidationResult: 校验结果
        """
        result = ValidationResult(
            is_valid=True,
            issues=[],
            validated_count=len(items)
        )

        for idx, item in enumerate(items):
            item_id = f"Item #{idx + 1} ({item.get('InstanceID', 'unknown')})"

            # 1. 检查必填字段
            self._check_required_fields(item, item_id, result)

            # 2. 检查数值字段
            self._check_numeric_fields(item, item_id, result)

            # 3. 检查逻辑一致性
            self._check_logical_consistency(item, item_id, result)

            # 4. 检查日期格式
            self._check_date_format(item, item_id, result)

            # 5. 检查Subscription特定字段
            if item.get('SubscriptionType') == 'Subscription':
                self._check_subscription_fields(item, item_id, result)

        return result

    def _check_required_fields(self, item: Dict, item_id: str, result: ValidationResult):
        """检查必填字段"""
        for field in self.REQUIRED_FIELDS:
            if not item.get(field):
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code='MISSING_REQUIRED_FIELD',
                    message=f'{item_id}: Missing required field',
                    field=field,
                    suggestion='Ensure BSS API returns complete data'
                ))

    def _check_numeric_fields(self, item: Dict, item_id: str, result: ValidationResult):
        """检查数值字段"""
        for field in self.NUMERIC_FIELDS:
            value = item.get(field)
            if value is not None:
                try:
                    decimal_value = Decimal(str(value))
                    # 检查是否为负数（某些字段不应为负）
                    if field in ['PretaxGrossAmount', 'PretaxAmount'] and decimal_value < 0:
                        result.add_issue(ValidationIssue(
                            level=ValidationLevel.ERROR,
                            code='NEGATIVE_AMOUNT',
                            message=f'{item_id}: Amount should not be negative',
                            field=field,
                            value=str(value),
                            suggestion='Check data source or calculation logic'
                        ))
                except (ValueError, TypeError):
                    result.add_issue(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code='INVALID_NUMERIC_VALUE',
                        message=f'{item_id}: Invalid numeric value',
                        field=field,
                        value=str(value),
                        suggestion='Ensure field contains valid number'
                    ))

    def _check_logical_consistency(self, item: Dict, item_id: str, result: ValidationResult):
        """检查逻辑一致性"""
        try:
            pretax_gross = Decimal(str(item.get('PretaxGrossAmount', 0)))
            pretax_amount = Decimal(str(item.get('PretaxAmount', 0)))
            invoice_discount = Decimal(str(item.get('InvoiceDiscount', 0)))

            # 检查：PretaxGrossAmount >= PretaxAmount
            if pretax_gross > 0 and pretax_amount > pretax_gross:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code='INCONSISTENT_AMOUNT',
                    message=f'{item_id}: PretaxAmount exceeds PretaxGrossAmount',
                    field='PretaxAmount',
                    value=f'PretaxAmount={pretax_amount}, PretaxGrossAmount={pretax_gross}',
                    suggestion='Verify discount calculation'
                ))

            # 检查：折扣金额的合理性
            expected_discount = pretax_gross - pretax_amount
            if abs(expected_discount - invoice_discount) > self.tolerance:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code='DISCOUNT_MISMATCH',
                    message=f'{item_id}: InvoiceDiscount does not match calculated discount',
                    field='InvoiceDiscount',
                    value=f'InvoiceDiscount={invoice_discount}, Expected={expected_discount}',
                    suggestion='Check if other discounts/coupons are included'
                ))

        except (ValueError, TypeError) as e:
            logger.warning(f"Error checking logical consistency for {item_id}: {e}")

    def _check_date_format(self, item: Dict, item_id: str, result: ValidationResult):
        """检查日期格式"""
        billing_date = item.get('BillingDate')
        if billing_date:
            # 简单检查格式 YYYY-MM-DD
            if not (isinstance(billing_date, str) and len(billing_date) == 10 and billing_date.count('-') == 2):
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code='INVALID_DATE_FORMAT',
                    message=f'{item_id}: Invalid date format',
                    field='BillingDate',
                    value=billing_date,
                    suggestion='Expected format: YYYY-MM-DD'
                ))

    def _check_subscription_fields(self, item: Dict, item_id: str, result: ValidationResult):
        """检查Subscription特定字段"""
        service_period = item.get('ServicePeriod')
        service_period_unit = item.get('ServicePeriodUnit')

        if not service_period or not service_period_unit:
            result.add_issue(ValidationIssue(
                level=ValidationLevel.WARNING,
                code='MISSING_SERVICE_PERIOD',
                message=f'{item_id}: Subscription item missing service period information',
                field='ServicePeriod/ServicePeriodUnit',
                suggestion='Cost amortization may use default values (30 days)'
            ))

    def compare_data_sources(
        self,
        bss_items: List[BillItem],
        mysql_items: List[BillItem],
        group_by: str = 'instance_id'
    ) -> ValidationResult:
        """
        比较BSS API和MySQL两个数据源的一致性

        Args:
            bss_items: BSS API获取的数据
            mysql_items: MySQL查询的数据
            group_by: 分组字段（用于匹配记录）

        Returns:
            ValidationResult: 比较结果
        """
        result = ValidationResult(
            is_valid=True,
            issues=[],
            validated_count=len(bss_items)
        )

        # 按group_by字段分组
        bss_groups = self._group_items(bss_items, group_by)
        mysql_groups = self._group_items(mysql_items, group_by)

        # 检查缺失的记录
        bss_keys = set(bss_groups.keys())
        mysql_keys = set(mysql_groups.keys())

        missing_in_mysql = bss_keys - mysql_keys
        missing_in_bss = mysql_keys - bss_keys

        for key in missing_in_mysql:
            result.add_issue(ValidationIssue(
                level=ValidationLevel.WARNING,
                code='MISSING_IN_MYSQL',
                message=f'Record exists in BSS but not in MySQL',
                field=group_by,
                value=key,
                suggestion='MySQL cache may be outdated, consider refresh'
            ))

        for key in missing_in_bss:
            result.add_issue(ValidationIssue(
                level=ValidationLevel.INFO,
                code='MISSING_IN_BSS',
                message=f'Record exists in MySQL but not in current BSS query',
                field=group_by,
                value=key,
                suggestion='May be historical data or different query scope'
            ))

        # 比较金额
        common_keys = bss_keys & mysql_keys
        for key in common_keys:
            bss_total = sum(item.pretax_amount for item in bss_groups[key])
            mysql_total = sum(item.pretax_amount for item in mysql_groups[key])

            diff = abs(bss_total - mysql_total)
            if diff > self.tolerance:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code='AMOUNT_MISMATCH',
                    message=f'Amount mismatch between BSS and MySQL',
                    field=f'{group_by}={key}',
                    value=f'BSS={float(bss_total)}, MySQL={float(mysql_total)}, Diff={float(diff)}',
                    suggestion='MySQL data may be stale or calculation logic differs'
                ))

        return result

    def _group_items(self, items: List[BillItem], group_by: str) -> Dict[str, List[BillItem]]:
        """将账单明细按指定字段分组"""
        from collections import defaultdict
        groups = defaultdict(list)
        for item in items:
            key = getattr(item, group_by, 'unknown')
            groups[key].append(item)
        return dict(groups)

    def validate_calculation_results(
        self,
        items: List[BillItem],
        expected_total: Optional[Decimal] = None
    ) -> ValidationResult:
        """
        验证费用计算结果

        Args:
            items: 账单明细列表
            expected_total: 预期的总金额（可选）

        Returns:
            ValidationResult: 校验结果
        """
        result = ValidationResult(
            is_valid=True,
            issues=[],
            validated_count=len(items)
        )

        calculated_total = Decimal('0')

        for item in items:
            try:
                calc_result = CostCalculator.calculate_daily_cost(item)
                calculated_total += calc_result.daily_cost

                # 检查计算结果的合理性
                if calc_result.daily_cost < 0:
                    result.add_issue(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code='NEGATIVE_DAILY_COST',
                        message=f'Negative daily cost calculated',
                        field='instance_id',
                        value=item.instance_id,
                        suggestion='Check input data and calculation logic'
                    ))

                # 检查折扣率的合理性（通常不应超过100%）
                if calc_result.discount_rate > 100:
                    result.add_issue(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        code='EXCESSIVE_DISCOUNT',
                        message=f'Discount rate exceeds 100%',
                        field='instance_id',
                        value=f'{item.instance_id}, discount_rate={float(calc_result.discount_rate)}%',
                        suggestion='Verify discount calculation'
                    ))

            except Exception as e:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code='CALCULATION_ERROR',
                    message=f'Error calculating cost',
                    field='instance_id',
                    value=item.instance_id,
                    suggestion=f'Exception: {str(e)}'
                ))

        # 如果提供了预期总金额，进行比较
        if expected_total is not None:
            diff = abs(calculated_total - expected_total)
            if diff > self.tolerance:
                result.add_issue(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code='TOTAL_MISMATCH',
                    message=f'Calculated total does not match expected total',
                    value=f'Calculated={float(calculated_total)}, Expected={float(expected_total)}, Diff={float(diff)}',
                    suggestion='Review calculation logic or input data'
                ))

        return result
