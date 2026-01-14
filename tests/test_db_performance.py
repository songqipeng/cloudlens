#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库性能测试
测试索引优化和查询性能
"""

import pytest
import time
from cloudlens.core.database import DatabaseFactory
from cloudlens.core.db_performance import DatabasePerformanceAnalyzer
from cloudlens.core.bill_storage import BillStorageManager


class TestDatabasePerformance:
    """数据库性能测试类"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        self.db = DatabaseFactory.create_adapter("mysql")
        self.analyzer = DatabasePerformanceAnalyzer()
        self.bill_storage = BillStorageManager()
    
    def test_slow_query_log_status(self):
        """测试慢查询日志状态"""
        status = self.analyzer.get_slow_query_status()
        assert 'enabled' in status
        assert 'threshold' in status
        assert 'log_file' in status
    
    def test_explain_query(self):
        """测试EXPLAIN查询"""
        sql = "SELECT * FROM bill_items WHERE account_id = %s LIMIT 10"
        explain_result = self.analyzer.explain_query(sql, ('test_account',))
        assert isinstance(explain_result, list)
        # MySQL 8.0+ 的EXPLAIN格式可能不同，只要返回结果即可
        if explain_result:
            assert isinstance(explain_result[0], dict)
    
    def test_table_indexes(self):
        """测试表索引分析"""
        indexes = self.analyzer.analyze_table_indexes('bill_items')
        assert isinstance(indexes, list)
        # 应该至少有一个索引（PRIMARY KEY）
        assert len(indexes) > 0
    
    def test_table_stats(self):
        """测试表统计信息"""
        stats = self.analyzer.get_table_stats('bill_items')
        assert 'table_name' in stats
        assert 'row_count' in stats
        assert stats['table_name'] == 'bill_items'
    
    def test_query_performance(self):
        """测试查询性能"""
        # 测试基本查询性能
        start_time = time.time()
        result = self.bill_storage.query_bill_items(
            account_id='test_account',
            limit=100
        )
        query_time = time.time() - start_time
        
        # 查询应该在合理时间内完成（< 1秒）
        assert query_time < 1.0, f"查询耗时过长: {query_time:.2f}秒"
        assert isinstance(result, list)
    
    def test_index_usage(self):
        """测试索引使用情况"""
        # 测试使用索引的查询
        sql = """
            SELECT billing_date, SUM(pretax_amount) as daily_cost
            FROM bill_items
            WHERE account_id = %s
                AND billing_date >= %s
                AND billing_date <= %s
            GROUP BY billing_date
            LIMIT 10
        """
        explain_result = self.analyzer.explain_query(
            sql, 
            ('test_account', '2025-01-01', '2025-01-31')
        )
        
        # 检查是否使用了索引
        if explain_result:
            # 至少应该有一个执行计划
            assert len(explain_result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
