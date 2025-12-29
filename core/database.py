#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库抽象层
提供统一的MySQL数据库操作接口
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    import mysql.connector
    from mysql.connector import pooling, Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    logger.warning("mysql-connector-python未安装，MySQL功能不可用")


class DatabaseAdapter(ABC):
    """数据库适配器抽象基类"""
    
    @abstractmethod
    def connect(self):
        """建立数据库连接"""
        pass
    
    @abstractmethod
    def close(self):
        """关闭数据库连接"""
        pass
    
    @abstractmethod
    def execute(self, sql: str, params: Optional[Tuple] = None) -> Any:
        """执行SQL语句（INSERT, UPDATE, DELETE）"""
        pass
    
    def executemany(self, sql: str, params_list: List[Tuple]) -> int:
        """
        批量执行SQL语句（优化性能）
        
        Args:
            sql: SQL语句
            params_list: 参数列表
            
        Returns:
            影响的行数
        """
        # 默认实现：循环执行（子类可以重写以优化）
        total_rows = 0
        for params in params_list:
            cursor = self.execute(sql, params)
            if hasattr(cursor, 'rowcount'):
                total_rows += cursor.rowcount
        return total_rows
    
    @abstractmethod
    def query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict]:
        """查询并返回字典列表"""
        pass
    
    @abstractmethod
    def query_one(self, sql: str, params: Optional[Tuple] = None) -> Optional[Dict]:
        """查询单条记录"""
        pass
    
    @abstractmethod
    def begin_transaction(self):
        """开始事务"""
        pass
    
    @abstractmethod
    def commit(self):
        """提交事务"""
        pass
    
    @abstractmethod
    def rollback(self):
        """回滚事务"""
        pass
    
    def normalize_sql(self, sql: str) -> str:
        """标准化SQL语句"""
        return sql


class MySQLAdapter(DatabaseAdapter):
    """MySQL适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化MySQL适配器
        
        Args:
            config: MySQL配置字典
                - host: 主机地址
                - port: 端口（默认3306）
                - user: 用户名
                - password: 密码
                - database: 数据库名
                - charset: 字符集（默认utf8mb4）
                - pool_size: 连接池大小（默认10）
        """
        if not MYSQL_AVAILABLE:
            raise ImportError("mysql-connector-python未安装，请运行: pip install mysql-connector-python")
        
        self.config = {
            'host': config.get('host', 'localhost'),
            'port': config.get('port', 3306),
            'user': config.get('user', 'cloudlens'),
            'password': config.get('password', ''),
            'database': config.get('database', 'cloudlens'),
            'charset': config.get('charset', 'utf8mb4'),
            'collation': config.get('collation', 'utf8mb4_unicode_ci'),
            'autocommit': False,
        }
        
        # 创建连接池（增加连接池大小，避免连接耗尽）
        pool_size = config.get('pool_size', 20)  # 从10增加到20
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name="cloudlens_pool",
                pool_size=pool_size,
                pool_reset_session=True,
                **self.config
            )
        except MySQLError as e:
            logger.error(f"创建MySQL连接池失败: {e}")
            raise
        
        self.conn = None
    
    def connect(self):
        """从连接池获取连接（用于事务操作）"""
        if not self.conn:
            try:
                self.conn = self.pool.get_connection()
                self.conn.autocommit = False
            except MySQLError as e:
                logger.error(f"获取MySQL连接失败: {e}")
                raise
        return self.conn
    
    def close(self):
        """关闭连接（归还到连接池）"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def execute(self, sql: str, params: Optional[Tuple] = None) -> Any:
        """执行SQL"""
        # 每次操作都获取新连接，操作完成后立即归还
        conn = self.pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # 转换占位符：? -> %s
            sql = self.normalize_sql(sql)
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            conn.commit()
            return cursor
        except MySQLError as e:
            conn.rollback()
            logger.error(f"MySQL执行错误: {sql[:100]}, 错误: {e}")
            raise
        finally:
            cursor.close()
            conn.close()  # 归还连接到连接池
    
    def executemany(self, sql: str, params_list: List[Tuple]) -> int:
        """批量执行SQL（MySQL优化版本）"""
        # 每次操作都获取新连接，操作完成后立即归还
        conn = self.pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # 转换占位符：? -> %s
            sql = self.normalize_sql(sql)
            
            cursor.executemany(sql, params_list)
            conn.commit()
            return cursor.rowcount
        except MySQLError as e:
            conn.rollback()
            logger.error(f"MySQL批量执行错误: {sql[:100]}, 错误: {e}")
            raise
        finally:
            cursor.close()
            conn.close()  # 归还连接到连接池
    
    def query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict]:
        """查询并返回字典列表"""
        # 每次操作都获取新连接，操作完成后立即归还
        conn = self.pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # 转换占位符：? -> %s
            sql = self.normalize_sql(sql)
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            return cursor.fetchall()
        except MySQLError as e:
            logger.error(f"MySQL查询错误: {sql[:100]}, 错误: {e}")
            raise
        finally:
            cursor.close()
            conn.close()  # 归还连接到连接池
    
    def query_one(self, sql: str, params: Optional[Tuple] = None) -> Optional[Dict]:
        """查询单条记录"""
        results = self.query(sql, params)
        return results[0] if results else None
    
    def begin_transaction(self):
        """开始事务"""
        conn = self.connect()
        conn.start_transaction()
    
    def commit(self):
        """提交事务"""
        if self.conn:
            self.conn.commit()
    
    def rollback(self):
        """回滚事务"""
        if self.conn:
            self.conn.rollback()
    
    def normalize_sql(self, sql: str) -> str:
        """标准化SQL语句（将?转换为%s）"""
        # MySQL使用%s作为占位符
        return sql.replace('?', '%s')
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        self.close()


class DatabaseFactory:
    """数据库工厂类"""
    
    @staticmethod
    def create_adapter(db_type: Optional[str] = None, **kwargs) -> DatabaseAdapter:
        """
        根据配置创建MySQL数据库适配器

        Args:
            db_type: 数据库类型（仅支持'mysql'），如果为None则从环境变量读取
            **kwargs: MySQL数据库配置参数
                - host: 主机地址
                - port: 端口
                - user: 用户名
                - password: 密码
                - database: 数据库名
                - charset: 字符集
                - pool_size: 连接池大小

        Returns:
            MySQLAdapter实例
        """
        # 从环境变量或参数获取数据库类型（默认使用MySQL）
        db_type = db_type or os.getenv("DB_TYPE", "mysql").lower()

        if db_type != "mysql":
            raise ValueError(f"不支持的数据库类型: {db_type}，仅支持MySQL")

        if not MYSQL_AVAILABLE:
            raise ImportError(
                "mysql-connector-python未安装，请运行: pip install mysql-connector-python"
            )

        # 从环境变量或kwargs获取MySQL配置
        mysql_config = {
            'host': kwargs.get('host') or os.getenv("MYSQL_HOST", "localhost"),
            'port': int(kwargs.get('port') or os.getenv("MYSQL_PORT", 3306)),
            'user': kwargs.get('user') or os.getenv("MYSQL_USER", "cloudlens"),
            'password': kwargs.get('password') or os.getenv("MYSQL_PASSWORD", ""),
            'database': kwargs.get('database') or os.getenv("MYSQL_DATABASE", "cloudlens"),
            'charset': kwargs.get('charset') or os.getenv("MYSQL_CHARSET", "utf8mb4"),
            'pool_size': int(kwargs.get('pool_size') or os.getenv("MYSQL_POOL_SIZE", 20)),
        }

        return MySQLAdapter(mysql_config)


def get_database_adapter(db_type: Optional[str] = None, **kwargs) -> DatabaseAdapter:
    """
    便捷函数：获取数据库适配器
    
    Args:
        db_type: 数据库类型
        **kwargs: 数据库配置参数
    
    Returns:
        DatabaseAdapter实例
    """
    return DatabaseFactory.create_adapter(db_type, **kwargs)





