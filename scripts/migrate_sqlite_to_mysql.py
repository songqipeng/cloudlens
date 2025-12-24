#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite到MySQL数据迁移脚本
将SQLite数据库中的所有数据迁移到MySQL
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseFactory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_table(sqlite_db, mysql_db, table_name, batch_size=1000):
    """
    迁移单个表的数据
    
    Args:
        sqlite_db: SQLite数据库适配器
        mysql_db: MySQL数据库适配器
        table_name: 表名
        batch_size: 批量插入大小
    """
    logger.info(f"开始迁移表: {table_name}")
    
    # 检查表是否存在
    try:
        sqlite_db.query(f"SELECT 1 FROM {table_name} LIMIT 1")
    except Exception as e:
        logger.warning(f"SQLite表 {table_name} 不存在或为空: {e}")
        return 0
    
    # 获取SQLite中的所有数据
    rows = sqlite_db.query(f"SELECT * FROM {table_name}")
    if not rows:
        logger.info(f"表 {table_name} 没有数据，跳过")
        return 0
    
    total_count = len(rows)
    logger.info(f"表 {table_name} 共有 {total_count} 条记录")
    
    # 获取表结构（列名）
    if not rows:
        return 0
    
    columns = list(rows[0].keys())
    columns_str = ', '.join([f"`{col}`" for col in columns])
    placeholders = ', '.join(['%s' for _ in columns])
    
    # 检查MySQL表是否存在，如果不存在则创建（这里假设表已存在）
    # 实际迁移时，表结构应该已经通过schema创建
    
    # 批量插入数据
    inserted = 0
    skipped = 0
    
    for i in range(0, total_count, batch_size):
        batch = rows[i:i + batch_size]
        values_list = []
        
        for row in batch:
            values = [row.get(col) for col in columns]
            values_list.append(tuple(values))
        
        try:
            # 使用REPLACE INTO避免重复（如果有唯一约束）
            sql = f"REPLACE INTO {table_name} ({columns_str}) VALUES ({placeholders})"
            mysql_db.executemany(sql, values_list)
            inserted += len(batch)
            logger.info(f"已插入 {inserted}/{total_count} 条记录")
        except Exception as e:
            logger.error(f"插入数据失败: {e}")
            # 尝试逐条插入，跳过重复的
            for values in values_list:
                try:
                    mysql_db.execute(f"REPLACE INTO {table_name} ({columns_str}) VALUES ({placeholders})", values)
                    inserted += 1
                except Exception as e2:
                    logger.warning(f"跳过重复记录: {e2}")
                    skipped += 1
    
    logger.info(f"表 {table_name} 迁移完成: 插入 {inserted} 条，跳过 {skipped} 条")
    return inserted


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始SQLite到MySQL数据迁移")
    logger.info("=" * 60)
    
    # SQLite数据库路径
    sqlite_path = os.path.expanduser("~/.cloudlens/bills.db")
    
    if not os.path.exists(sqlite_path):
        logger.error(f"SQLite数据库不存在: {sqlite_path}")
        return 1
    
    logger.info(f"SQLite数据库路径: {sqlite_path}")
    logger.info(f"数据库大小: {os.path.getsize(sqlite_path) / 1024 / 1024:.2f} MB")
    
    # 连接SQLite
    try:
        sqlite_db = DatabaseFactory.create_adapter("sqlite", db_path=sqlite_path)
        logger.info("SQLite连接成功")
    except Exception as e:
        logger.error(f"SQLite连接失败: {e}")
        return 1
    
    # 连接MySQL
    try:
        mysql_db = DatabaseFactory.create_adapter("mysql")
        logger.info("MySQL连接成功")
    except Exception as e:
        logger.error(f"MySQL连接失败: {e}")
        logger.error("请确保MySQL配置正确（环境变量或配置文件）")
        return 1
    
    # 需要迁移的表列表
    tables_to_migrate = [
        'bill_items',
        'budgets',
        'budget_records',
        'alerts',
        'virtual_tags',
        'cost_allocation_rules',
        'cost_allocation_results',
        'resource_cache',
        'dashboards',
    ]
    
    total_inserted = 0
    
    for table_name in tables_to_migrate:
        try:
            count = migrate_table(sqlite_db, mysql_db, table_name)
            total_inserted += count
        except Exception as e:
            logger.error(f"迁移表 {table_name} 失败: {e}")
            continue
    
    logger.info("=" * 60)
    logger.info(f"迁移完成！总共插入 {total_inserted} 条记录")
    logger.info("=" * 60)
    
    # 验证迁移结果
    logger.info("\n验证迁移结果:")
    for table_name in tables_to_migrate:
        try:
            sqlite_count = len(sqlite_db.query(f"SELECT 1 FROM {table_name}"))
            mysql_count = len(mysql_db.query(f"SELECT 1 FROM {table_name}"))
            logger.info(f"  {table_name}: SQLite={sqlite_count}, MySQL={mysql_count}")
        except Exception as e:
            logger.warning(f"  {table_name}: 验证失败 - {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

