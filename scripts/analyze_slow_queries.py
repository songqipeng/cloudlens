#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
慢查询分析脚本
用于分析MySQL慢查询并生成报告
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from core.db_performance import DatabasePerformanceAnalyzer
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    print("=" * 60)
    print("数据库慢查询分析工具")
    print("=" * 60)
    print()
    
    analyzer = DatabasePerformanceAnalyzer()
    
    # 1. 检查慢查询日志状态
    print("📊 检查慢查询日志状态...")
    status = analyzer.get_slow_query_status()
    print(f"  慢查询日志: {'✅ 已启用' if status.get('enabled') else '❌ 未启用'}")
    print(f"  慢查询阈值: {status.get('threshold', 0)}秒")
    print(f"  慢查询数量: {status.get('slow_query_count', 0)}")
    print(f"  日志文件: {status.get('log_file', 'N/A')}")
    print()
    
    # 2. 如果未启用，询问是否启用
    if not status.get('enabled'):
        print("⚠️  慢查询日志未启用")
        response = input("是否启用慢查询日志？(y/n): ")
        if response.lower() == 'y':
            threshold = input("请输入慢查询阈值（秒，默认1.0）: ")
            threshold = float(threshold) if threshold else 1.0
            if analyzer.enable_slow_query_log(slow_query_time=threshold):
                print("✅ 慢查询日志已启用")
            else:
                print("❌ 启用失败")
                return
        else:
            print("跳过慢查询日志启用")
            print()
    
    # 3. 分析慢查询
    print("🔍 分析慢查询...")
    slow_queries = analyzer.analyze_slow_queries(limit=20)
    if slow_queries:
        print(f"  发现 {len(slow_queries)} 个慢查询:")
        for i, query in enumerate(slow_queries, 1):
            print(f"  {i}. 查询时间: {query.get('query_time_sec', 0):.2f}秒")
            print(f"     检查行数: {query.get('rows_examined', 0)}")
            print(f"     返回行数: {query.get('rows_sent', 0)}")
            sql = query.get('sql_text', query.get('digest_text', ''))
            if sql:
                print(f"     SQL: {sql[:100]}...")
            print()
    else:
        print("  ✅ 未发现慢查询（或performance_schema未启用）")
    print()
    
    # 4. 识别性能瓶颈
    print("🔍 识别性能瓶颈...")
    bottlenecks = analyzer.identify_performance_bottlenecks()
    
    if bottlenecks.get('large_tables'):
        print("  📊 大表:")
        for table in bottlenecks['large_tables']:
            print(f"    - {table['table_name']}: {table['row_count']:,} 行, {table['size_mb']:.2f} MB")
    
    if bottlenecks.get('slow_queries'):
        print(f"  ⚠️  发现 {len(bottlenecks['slow_queries'])} 个慢查询")
    
    print()
    print("=" * 60)
    print("分析完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
