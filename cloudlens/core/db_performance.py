#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库性能分析工具
用于慢查询分析和性能优化
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from cloudlens.core.database import DatabaseFactory

logger = logging.getLogger(__name__)


class DatabasePerformanceAnalyzer:
    """数据库性能分析器"""
    
    def __init__(self):
        """初始化性能分析器"""
        self.db = DatabaseFactory.create_adapter("mysql")
    
    def enable_slow_query_log(self, slow_query_time: float = 1.0, log_file: Optional[str] = None) -> bool:
        """
        启用MySQL慢查询日志
        
        Args:
            slow_query_time: 慢查询阈值（秒），默认1.0秒
            log_file: 慢查询日志文件路径（可选，默认使用MySQL配置）
            
        Returns:
            是否成功启用
        """
        try:
            # 设置慢查询阈值
            self.db.execute(f"SET GLOBAL slow_query_log = 'ON'")
            self.db.execute(f"SET GLOBAL long_query_time = {slow_query_time}")
            
            if log_file:
                self.db.execute(f"SET GLOBAL slow_query_log_file = '{log_file}'")
            
            # 记录慢查询（不使用索引的查询）
            self.db.execute("SET GLOBAL log_queries_not_using_indexes = 'ON'")
            
            logger.info(f"✅ 慢查询日志已启用，阈值: {slow_query_time}秒")
            return True
        except Exception as e:
            logger.error(f"启用慢查询日志失败: {e}")
            return False
    
    def disable_slow_query_log(self) -> bool:
        """禁用慢查询日志"""
        try:
            self.db.execute("SET GLOBAL slow_query_log = 'OFF'")
            logger.info("✅ 慢查询日志已禁用")
            return True
        except Exception as e:
            logger.error(f"禁用慢查询日志失败: {e}")
            return False
    
    def get_slow_query_status(self) -> Dict[str, Any]:
        """获取慢查询日志状态"""
        try:
            status = {}
            
            # 检查慢查询日志是否启用
            result = self.db.query_one("SHOW VARIABLES LIKE 'slow_query_log'")
            status['enabled'] = result.get('Value', 'OFF') == 'ON' if result else False
            
            # 获取慢查询阈值
            result = self.db.query_one("SHOW VARIABLES LIKE 'long_query_time'")
            status['threshold'] = float(result.get('Value', 10.0)) if result else 10.0
            
            # 获取慢查询日志文件路径
            result = self.db.query_one("SHOW VARIABLES LIKE 'slow_query_log_file'")
            status['log_file'] = result.get('Value', '') if result else ''
            
            # 获取慢查询数量
            result = self.db.query_one("SHOW STATUS LIKE 'Slow_queries'")
            status['slow_query_count'] = int(result.get('Value', 0)) if result else 0
            
            return status
        except Exception as e:
            logger.error(f"获取慢查询状态失败: {e}")
            return {}
    
    def analyze_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        分析慢查询（从performance_schema或慢查询日志）
        
        Args:
            limit: 返回的慢查询数量限制
            
        Returns:
            慢查询列表
        """
        try:
            # 检查是否支持performance_schema
            result = self.db.query_one("SHOW VARIABLES LIKE 'performance_schema'")
            if result and result.get('Value') == 'ON':
                # 使用performance_schema查询慢查询
                slow_queries = self.db.query(f"""
                    SELECT 
                        sql_text,
                        timer_wait / 1000000000000 as query_time_sec,
                        lock_time / 1000000000000 as lock_time_sec,
                        rows_examined,
                        rows_sent,
                        digest_text
                    FROM performance_schema.events_statements_history_long
                    WHERE timer_wait > 1000000000000  -- 大于1秒
                    ORDER BY timer_wait DESC
                    LIMIT {limit}
                """)
                return slow_queries
            
            # 如果不支持performance_schema，返回空列表
            logger.warning("performance_schema未启用，无法分析慢查询")
            return []
        except Exception as e:
            logger.error(f"分析慢查询失败: {e}")
            return []
    
    def explain_query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        使用EXPLAIN分析查询执行计划
        
        Args:
            sql: SQL查询语句
            params: 查询参数
            
        Returns:
            EXPLAIN结果
        """
        try:
            explain_sql = f"EXPLAIN {sql}"
            result = self.db.query(explain_sql, params)
            return result
        except Exception as e:
            logger.error(f"EXPLAIN查询失败: {e}")
            return []
    
    def analyze_table_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """
        分析表的索引使用情况
        
        Args:
            table_name: 表名
            
        Returns:
            索引信息列表
        """
        try:
            indexes = self.db.query(f"""
                SELECT 
                    INDEX_NAME as index_name,
                    COLUMN_NAME as column_name,
                    SEQ_IN_INDEX as seq_in_index,
                    CARDINALITY as cardinality,
                    INDEX_TYPE as index_type,
                    NON_UNIQUE as non_unique
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = %s
                ORDER BY INDEX_NAME, SEQ_IN_INDEX
            """, (table_name,))
            return indexes
        except Exception as e:
            logger.error(f"分析表索引失败: {e}")
            return []
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """
        获取表的统计信息
        
        Args:
            table_name: 表名
            
        Returns:
            表统计信息
        """
        try:
            # 获取表行数
            result = self.db.query_one(f"SELECT COUNT(*) as row_count FROM {table_name}")
            row_count = result.get('row_count', 0) if result else 0
            
            # 获取表大小
            result = self.db.query_one(f"""
                SELECT 
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = %s
            """, (table_name,))
            size_mb = result.get('size_mb', 0) if result else 0
            
            return {
                'table_name': table_name,
                'row_count': row_count,
                'size_mb': size_mb
            }
        except Exception as e:
            logger.error(f"获取表统计信息失败: {e}")
            return {}
    
    def identify_performance_bottlenecks(self) -> Dict[str, Any]:
        """
        识别性能瓶颈
        
        Returns:
            性能瓶颈分析报告
        """
        bottlenecks = {
            'missing_indexes': [],
            'unused_indexes': [],
            'large_tables': [],
            'slow_queries': []
        }
        
        try:
            # 分析主要表的索引
            main_tables = ['bill_items', 'resource_cache', 'alerts', 'budgets']
            
            for table in main_tables:
                try:
                    stats = self.get_table_stats(table)
                    if stats.get('row_count', 0) > 100000:
                        bottlenecks['large_tables'].append(stats)
                    
                    indexes = self.analyze_table_indexes(table)
                    # TODO: 分析缺失的索引（需要根据查询模式）
                except Exception as e:
                    logger.warning(f"分析表 {table} 失败: {e}")
            
            # 获取慢查询
            slow_queries = self.analyze_slow_queries(limit=20)
            bottlenecks['slow_queries'] = slow_queries
            
            return bottlenecks
        except Exception as e:
            logger.error(f"识别性能瓶颈失败: {e}")
            return bottlenecks
