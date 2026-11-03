#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""折扣分析器：优化建议参数与空缓存策略。"""

from cloudlens.core.cache.decorators import _should_cache_response
from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer


def test_optimization_suggestions_does_not_raise_on_months():
    """get_optimization_suggestions 必须自带 months，不能 NameError。"""
    analyzer = AdvancedDiscountAnalyzer.__new__(AdvancedDiscountAnalyzer)
    analyzer.db_type = "mysql"
    analyzer._get_placeholder = lambda: "%s"
    analyzer._get_date_filter_params = lambda months: (" AND billing_cycle >= %s", "2025-01")
    analyzer._query_db = lambda sql, params: []
    analyzer._get_region_name = lambda region: region or ""

    result = analyzer.get_optimization_suggestions("LTAI5t5nqy-cf")

    assert result["success"] is True
    assert result["total_suggestions"] == 0
    assert result["suggestions"] == []


def test_should_not_cache_empty_quarterly_payload():
    """空季度结果不能写入缓存。"""
    empty = {"success": True, "data": {"success": True, "quarters": [], "total_quarters": 0}}
    filled = {"success": True, "data": {"success": True, "quarters": [{"period": "2026-Q3"}], "total_quarters": 1}}

    assert _should_cache_response(empty) is False
    assert _should_cache_response(filled) is True
