#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReportGenerator 单元测试
"""

import pytest
import os
import tempfile
from pathlib import Path
from core.report_generator import ReportGenerator


class TestReportGenerator:
    """报告生成器测试类"""

    def test_escape_html(self):
        """测试HTML转义"""
        assert ReportGenerator.escape_html("test") == "test"
        assert ReportGenerator.escape_html("<script>") == "&lt;script&gt;"
        assert ReportGenerator.escape_html("a & b") == "a &amp; b"
        assert ReportGenerator.escape_html('"quote"') == "&quot;quote&quot;"
        assert ReportGenerator.escape_html(None) == ""

    def test_generate_html_report_empty(self):
        """测试生成空报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "test_empty.html")
            result = ReportGenerator.generate_html_report(
                "RDS", [], filename, tenant_name="test"
            )
            
            assert result == filename
            assert os.path.exists(filename)
            
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "RDS闲置实例分析报告" in content
                assert "闲置实例数量: 0 个" in content

    def test_generate_html_report_with_data(self):
        """测试生成有数据的报告"""
        instances = [
            {
                '实例名称': 'test-rds-001',
                '实例ID': 'rds-001',
                '区域': 'cn-hangzhou',
                'CPU利用率(%)': 5.0,
                '月成本(¥)': 500.0,
                '闲置原因': 'CPU利用率低',
                '优化建议': '考虑降配或删除'
            }
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "test_report.html")
            result = ReportGenerator.generate_html_report(
                "RDS", instances, filename, tenant_name="test"
            )
            
            assert result == filename
            assert os.path.exists(filename)
            
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "test-rds-001" in content
                assert "总月成本" in content
                assert "预计年节省" in content

    def test_generate_excel_report(self):
        """测试生成Excel报告"""
        instances = [
            {
                '实例名称': 'test-rds-001',
                '实例ID': 'rds-001',
                '区域': 'cn-hangzhou',
                '月成本(¥)': 500.0
            }
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "test_report.xlsx")
            result = ReportGenerator.generate_excel_report(instances, filename)
            
            assert result == filename
            assert os.path.exists(filename)

    def test_generate_combined_report(self):
        """测试生成组合报告（HTML+Excel）"""
        instances = [
            {
                '实例名称': 'test-rds-001',
                '实例ID': 'rds-001',
                '月成本(¥)': 500.0
            }
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            results = ReportGenerator.generate_combined_report(
                "RDS", instances, tmpdir, tenant_name="test"
            )
            
            assert 'html' in results
            assert 'excel' in results
            assert os.path.exists(results['html'])
            assert os.path.exists(results['excel'])

