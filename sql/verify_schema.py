#!/usr/bin/env python3
"""
验证MySQL数据库表结构
"""
import mysql.connector
from mysql.connector import Error

def verify_schema():
    """验证数据库表结构"""
    try:
        config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'cloudlens',
            'password': 'cloudlens123',
            'database': 'cloudlens'
        }
        
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor(dictionary=True)
        
        print("=" * 60)
        print("验证MySQL数据库表结构")
        print("=" * 60)
        
        # 获取所有表
        cursor.execute("""
            SELECT table_name, table_rows, 
                   ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
            FROM information_schema.tables 
            WHERE table_schema = 'cloudlens'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        
        print(f"\n✅ 找到 {len(tables)} 个表:\n")
        
        expected_tables = [
            'resource_cache',
            'bill_items',
            'dashboards',
            'budgets',
            'budget_records',
            'budget_alerts',
            'alert_rules',
            'alerts',
            'virtual_tags',
            'tag_rules',
            'tag_matches',
            'resource_monitoring_data',
            'cost_allocation'
        ]
        
        # MySQL返回的键名可能是大写
        found_tables = [t.get('TABLE_NAME') or t.get('table_name') for t in tables]
        
        print(f"{'表名':<30} {'行数':<15} {'大小(MB)':<15}")
        print("-" * 60)
        
        for table in tables:
            name = table.get('TABLE_NAME') or table.get('table_name') or 'unknown'
            rows = table.get('TABLE_ROWS') or table.get('table_rows') or 0
            size = table.get('size_mb') or table.get('SIZE_MB') or 0
            print(f"{name:<30} {rows:<15} {size:<15}")
        
        # 验证所有必需的表都存在
        print("\n" + "=" * 60)
        print("验证必需的表:")
        print("=" * 60)
        
        missing_tables = []
        for expected in expected_tables:
            if expected in found_tables:
                print(f"✅ {expected}")
            else:
                print(f"❌ {expected} - 缺失!")
                missing_tables.append(expected)
        
        if missing_tables:
            print(f"\n⚠️  缺失 {len(missing_tables)} 个表")
            return False
        else:
            print(f"\n✅ 所有 {len(expected_tables)} 个必需表都存在!")
        
        # 验证表结构（检查几个关键表）
        print("\n" + "=" * 60)
        print("验证关键表结构:")
        print("=" * 60)
        
        key_tables = ['resource_cache', 'bill_items', 'dashboards', 'budgets']
        for table_name in key_tables:
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            print(f"\n{table_name} ({len(columns)} 列):")
            for col in columns[:5]:  # 只显示前5列
                field = col.get('Field') or col.get('FIELD')
                col_type = col.get('Type') or col.get('TYPE')
                null = col.get('Null') or col.get('NULL')
                key = col.get('Key') or col.get('KEY')
                print(f"  - {field:<20} {col_type:<20} {null:<5} {key}")
            if len(columns) > 5:
                print(f"  ... 还有 {len(columns) - 5} 列")
        
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 60)
        print("✅ 数据库表结构验证完成!")
        print("=" * 60)
        
        return True
        
    except Error as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    verify_schema()




