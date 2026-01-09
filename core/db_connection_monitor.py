#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接池监控工具
用于监控连接池状态和性能
"""

import logging
from typing import Dict, Any, Optional
from core.database import DatabaseFactory

logger = logging.getLogger(__name__)


class ConnectionPoolMonitor:
    """连接池监控器"""
    
    def __init__(self):
        """初始化监控器"""
        self.db = DatabaseFactory.create_adapter("mysql")
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        获取连接池状态
        
        Returns:
            连接池状态信息
        """
        try:
            status = {}
            
            # 获取连接数统计
            result = self.db.query_one("SHOW STATUS LIKE 'Threads_connected'")
            status['threads_connected'] = int(result.get('Value', 0)) if result else 0
            
            result = self.db.query_one("SHOW STATUS LIKE 'Threads_running'")
            status['threads_running'] = int(result.get('Value', 0)) if result else 0
            
            result = self.db.query_one("SHOW STATUS LIKE 'Max_used_connections'")
            status['max_used_connections'] = int(result.get('Value', 0)) if result else 0
            
            # 获取最大连接数
            result = self.db.query_one("SHOW VARIABLES LIKE 'max_connections'")
            status['max_connections'] = int(result.get('Value', 0)) if result else 0
            
            # 计算连接池使用率
            if status.get('max_connections', 0) > 0:
                status['connection_usage_rate'] = (
                    status['threads_connected'] / status['max_connections'] * 100
                )
            else:
                status['connection_usage_rate'] = 0
            
            return status
        except Exception as e:
            logger.error(f"获取连接池状态失败: {e}")
            return {}
    
    def get_slow_queries_count(self) -> int:
        """获取慢查询数量"""
        try:
            result = self.db.query_one("SHOW STATUS LIKE 'Slow_queries'")
            return int(result.get('Value', 0)) if result else 0
        except Exception as e:
            logger.error(f"获取慢查询数量失败: {e}")
            return 0
    
    def get_query_cache_status(self) -> Dict[str, Any]:
        """获取查询缓存状态"""
        try:
            status = {}
            
            # 检查查询缓存是否启用
            result = self.db.query_one("SHOW VARIABLES LIKE 'query_cache_type'")
            status['query_cache_type'] = result.get('Value', 'OFF') if result else 'OFF'
            
            if status['query_cache_type'] != 'OFF':
                result = self.db.query_one("SHOW STATUS LIKE 'Qcache_hits'")
                status['cache_hits'] = int(result.get('Value', 0)) if result else 0
                
                result = self.db.query_one("SHOW STATUS LIKE 'Qcache_inserts'")
                status['cache_inserts'] = int(result.get('Value', 0)) if result else 0
                
                # 计算缓存命中率
                total = status['cache_hits'] + status['cache_inserts']
                if total > 0:
                    status['cache_hit_rate'] = (status['cache_hits'] / total) * 100
                else:
                    status['cache_hit_rate'] = 0
            else:
                status['cache_hits'] = 0
                status['cache_inserts'] = 0
                status['cache_hit_rate'] = 0
            
            return status
        except Exception as e:
            logger.error(f"获取查询缓存状态失败: {e}")
            return {}
