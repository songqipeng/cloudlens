#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite到MySQL数据迁移脚本
将现有的SQLite数据库数据迁移到MySQL
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    print("❌ 错误: mysql-connector-python未安装")
    print("请运行: pip install mysql-connector-python")
    sys.exit(1)

from core.database import MySQLAdapter, DatabaseFactory


class SQLiteToMySQLMigrator:
    """SQLite到MySQL迁移器"""
    
    def __init__(self, mysql_config: Dict):
        """
        初始化迁移器
        
        Args:
            mysql_config: MySQL配置字典
        """
        self.mysql_config = mysql_config
        self.mysql_adapter = MySQLAdapter(mysql_config)
        self.cloudlens_dir = Path.home() / ".cloudlens"
        
    def migrate_cache(self) -> int:
        """迁移缓存数据"""
        print("📦 迁移缓存数据...")
        
        sqlite_db = self.cloudlens_dir / "cache.db"
        if not sqlite_db.exists():
            print("  ⚠️  cache.db不存在，跳过")
            return 0
        
        sqlite_conn = sqlite3.connect(str(sqlite_db))
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        try:
            # 读取SQLite数据
            sqlite_cursor.execute("SELECT * FROM resource_cache")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print("  ✅ 没有缓存数据需要迁移")
                return 0
            
            # 迁移到MySQL
            migrated = 0
            for row in rows:
                try:
                    # SQLite Row对象支持字典式访问（使用keys()方法）
                    row_keys = list(row.keys())
                    cache_key = row['cache_key'] if 'cache_key' in row_keys else row[0]
                    resource_type = row['resource_type'] if 'resource_type' in row_keys else row[1]
                    account_name = row['account_name'] if 'account_name' in row_keys else row[2]
                    region = row['region'] if 'region' in row_keys else (row[3] if len(row) > 3 else None)
                    data = row['data'] if 'data' in row_keys else row[4]
                    created_at = row['created_at'] if 'created_at' in row_keys else (row[5] if len(row) > 5 else None)
                    expires_at = row['expires_at'] if 'expires_at' in row_keys else (row[6] if len(row) > 6 else None)
                    
                    if isinstance(data, str):
                        # 验证是否为有效JSON
                        try:
                            json.loads(data)
                        except:
                            # 如果不是JSON，跳过
                            continue
                    
                    # MySQL使用ON DUPLICATE KEY UPDATE
                    sql = """
                        INSERT INTO resource_cache 
                        (cache_key, resource_type, account_name, region, data, created_at, expires_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            resource_type = VALUES(resource_type),
                            account_name = VALUES(account_name),
                            region = VALUES(region),
                            data = VALUES(data),
                            created_at = VALUES(created_at),
                            expires_at = VALUES(expires_at)
                    """
                    
                    params = (
                        cache_key,
                        resource_type,
                        account_name,
                        region,
                        data,
                        created_at,
                        expires_at
                    )
                    
                    self.mysql_adapter.execute(sql, params)
                    migrated += 1
                except Exception as e:
                    print(f"  ⚠️  迁移缓存记录失败: {e}")
                    continue
            
            print(f"  ✅ 成功迁移 {migrated}/{len(rows)} 条缓存记录")
            return migrated
            
        finally:
            sqlite_cursor.close()
            sqlite_conn.close()
    
    def migrate_bills(self) -> int:
        """迁移账单数据"""
        print("💰 迁移账单数据...")
        
        sqlite_db = self.cloudlens_dir / "bills.db"
        if not sqlite_db.exists():
            print("  ⚠️  bills.db不存在，跳过")
            return 0
        
        sqlite_conn = sqlite3.connect(str(sqlite_db))
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        try:
            # 检查表是否存在
            sqlite_cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='bill_items'
            """)
            if not sqlite_cursor.fetchone():
                print("  ⚠️  bill_items表不存在，跳过")
                return 0
            
            # 读取SQLite数据
            sqlite_cursor.execute("SELECT * FROM bill_items")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print("  ✅ 没有账单数据需要迁移")
                return 0
            
            # 获取列名
            columns = [desc[0] for desc in sqlite_cursor.description]
            
            # 迁移到MySQL
            migrated = 0
            batch_size = 100
            batch = []
            
            for row in rows:
                try:
                    # 构建INSERT语句（排除id，让MySQL自动生成）
                    row_dict = dict(row)
                    row_dict.pop('id', None)  # 移除id，使用AUTO_INCREMENT
                    
                    # 处理JSON字段
                    if 'raw_data' in row_dict and row_dict['raw_data']:
                        try:
                            if isinstance(row_dict['raw_data'], str):
                                json.loads(row_dict['raw_data'])  # 验证JSON
                        except:
                            row_dict['raw_data'] = None
                    
                    if 'tag' in row_dict and row_dict['tag']:
                        try:
                            if isinstance(row_dict['tag'], str):
                                json.loads(row_dict['tag'])  # 验证JSON
                        except:
                            row_dict['tag'] = None
                    
                    batch.append(row_dict)
                    
                    if len(batch) >= batch_size:
                        self._insert_bills_batch(batch)
                        migrated += len(batch)
                        batch = []
                        
                except Exception as e:
                    print(f"  ⚠️  迁移账单记录失败: {e}")
                    continue
            
            # 插入剩余批次
            if batch:
                self._insert_bills_batch(batch)
                migrated += len(batch)
            
            print(f"  ✅ 成功迁移 {migrated}/{len(rows)} 条账单记录")
            return migrated
            
        finally:
            sqlite_cursor.close()
            sqlite_conn.close()
    
    def _insert_bills_batch(self, batch: List[Dict]):
        """批量插入账单数据"""
        if not batch:
            return
        
        # 构建INSERT语句（处理MySQL保留关键字）
        columns = [k for k in batch[0].keys() if k != 'id']
        # 对保留关键字添加反引号
        reserved_keywords = ['usage', 'key', 'order', 'group', 'select', 'table']
        columns_quoted = [f"`{col}`" if col.lower() in reserved_keywords else col for col in columns]
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns_quoted)
        
        # 构建ON DUPLICATE KEY UPDATE部分
        update_parts = [f"`{col}` = VALUES(`{col}`)" if col.lower() in reserved_keywords else f"{col} = VALUES({col})" for col in columns]
        update_clause = ', '.join(update_parts)
        
        sql = f"""
            INSERT INTO bill_items ({columns_str})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE
                {update_clause}
        """
        
        values_list = []
        for row in batch:
            values = tuple(row.get(col) for col in columns)
            values_list.append(values)
        
        # 执行批量插入
        conn = self.mysql_adapter.connect()
        cursor = conn.cursor()
        try:
            cursor.executemany(sql, values_list)
            conn.commit()
        finally:
            cursor.close()
    
    def migrate_dashboards(self) -> int:
        """迁移仪表盘数据"""
        print("📊 迁移仪表盘数据...")
        
        sqlite_db = self.cloudlens_dir / "dashboards.db"
        if not sqlite_db.exists():
            print("  ⚠️  dashboards.db不存在，跳过")
            return 0
        
        sqlite_conn = sqlite3.connect(str(sqlite_db))
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        try:
            sqlite_cursor.execute("SELECT * FROM dashboards")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print("  ✅ 没有仪表盘数据需要迁移")
                return 0
            
            migrated = 0
            for row in rows:
                try:
                    # 处理widgets字段（JSON）
                    widgets = row['widgets']
                    if isinstance(widgets, str):
                        try:
                            json.loads(widgets)  # 验证JSON
                        except:
                            widgets = '[]'
                    
                    sql = """
                        INSERT INTO dashboards 
                        (id, name, description, layout, widgets, account_id, is_shared, created_by, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            name = VALUES(name),
                            description = VALUES(description),
                            layout = VALUES(layout),
                            widgets = VALUES(widgets),
                            account_id = VALUES(account_id),
                            is_shared = VALUES(is_shared),
                            created_by = VALUES(created_by),
                            updated_at = VALUES(updated_at)
                    """
                    
                    params = (
                        row['id'],
                        row['name'],
                        row.get('description'),
                        row.get('layout', 'grid'),
                        widgets,
                        row.get('account_id'),
                        row.get('is_shared', 0),
                        row.get('created_by'),
                        row.get('created_at'),
                        row.get('updated_at')
                    )
                    
                    self.mysql_adapter.execute(sql, params)
                    migrated += 1
                except Exception as e:
                    print(f"  ⚠️  迁移仪表盘记录失败: {e}")
                    continue
            
            print(f"  ✅ 成功迁移 {migrated}/{len(rows)} 条仪表盘记录")
            return migrated
            
        finally:
            sqlite_cursor.close()
            sqlite_conn.close()
    
    def migrate_all(self) -> Dict[str, int]:
        """迁移所有数据"""
        print("=" * 60)
        print("开始SQLite到MySQL数据迁移")
        print("=" * 60)
        
        results = {}
        
        try:
            results['cache'] = self.migrate_cache()
            results['bills'] = self.migrate_bills()
            results['dashboards'] = self.migrate_dashboards()
            
            print("\n" + "=" * 60)
            print("迁移完成!")
            print("=" * 60)
            print(f"缓存: {results['cache']} 条")
            print(f"账单: {results['bills']} 条")
            print(f"仪表盘: {results['dashboards']} 条")
            
        except Exception as e:
            print(f"\n❌ 迁移失败: {e}")
            raise
        
        return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SQLite到MySQL数据迁移工具')
    parser.add_argument('--host', default='localhost', help='MySQL主机地址')
    parser.add_argument('--port', type=int, default=3306, help='MySQL端口')
    parser.add_argument('--user', default='cloudlens', help='MySQL用户名')
    parser.add_argument('--password', default='cloudlens123', help='MySQL密码')
    parser.add_argument('--database', default='cloudlens', help='MySQL数据库名')
    
    args = parser.parse_args()
    
    mysql_config = {
        'host': args.host,
        'port': args.port,
        'user': args.user,
        'password': args.password,
        'database': args.database,
    }
    
    # 从环境变量覆盖
    mysql_config['host'] = os.getenv('MYSQL_HOST', mysql_config['host'])
    mysql_config['port'] = int(os.getenv('MYSQL_PORT', mysql_config['port']))
    mysql_config['user'] = os.getenv('MYSQL_USER', mysql_config['user'])
    mysql_config['password'] = os.getenv('MYSQL_PASSWORD', mysql_config['password'])
    mysql_config['database'] = os.getenv('MYSQL_DATABASE', mysql_config['database'])
    
    try:
        migrator = SQLiteToMySQLMigrator(mysql_config)
        results = migrator.migrate_all()
        
        print("\n✅ 迁移成功完成!")
        return 0
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
