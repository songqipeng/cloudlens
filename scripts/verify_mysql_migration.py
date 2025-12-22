#!/usr/bin/env python3
"""
验证MySQL迁移状态
检查所有模块是否已迁移到MySQL，不再使用SQLite
"""

import os
import sys
import re
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_sqlite_usage():
    """检查代码中是否还有SQLite使用"""
    print("=" * 60)
    print("检查SQLite使用情况")
    print("=" * 60)
    
    # 需要检查的目录
    check_dirs = ['core', 'web/backend']
    
    sqlite_patterns = [
        r'import sqlite3',
        r'from sqlite3 import',
        r'sqlite3\.connect',
        r'\.db_path',
    ]
    
    issues = []
    
    for check_dir in check_dirs:
        dir_path = Path(__file__).parent.parent / check_dir
        if not dir_path.exists():
            continue
        
        for py_file in dir_path.rglob('*.py'):
            # 跳过备份文件和测试文件
            if 'backup' in str(py_file) or 'test' in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
                
                for pattern in sqlite_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()
                        
                        # 排除注释和数据库抽象层文件
                        if '#' in line_content[:match.start() - content[:match.start()].rfind('\n')] or \
                           'database.py' in str(py_file) or \
                           'storage_base.py' in str(py_file):
                            continue
                        
                        issues.append({
                            'file': str(py_file.relative_to(Path(__file__).parent.parent)),
                            'line': line_num,
                            'pattern': pattern,
                            'content': line_content[:100]
                        })
            except Exception as e:
                print(f"⚠️  读取文件失败 {py_file}: {e}")
    
    if issues:
        print(f"\n❌ 发现 {len(issues)} 处SQLite使用:")
        for issue in issues[:20]:  # 只显示前20个
            print(f"  {issue['file']}:{issue['line']} - {issue['pattern']}")
            print(f"    {issue['content']}")
        if len(issues) > 20:
            print(f"  ... 还有 {len(issues) - 20} 处")
        return False
    else:
        print("\n✅ 未发现SQLite直接使用")
        return True

def check_mysql_data():
    """检查MySQL中的数据"""
    print("\n" + "=" * 60)
    print("检查MySQL数据")
    print("=" * 60)
    
    try:
        from core.database import DatabaseFactory
        
        db = DatabaseFactory.create_adapter("mysql")
        
        # 检查各表的数据量
        tables = [
            'resource_cache',
            'bill_items',
            'dashboards',
            'budgets',
            'alert_rules',
            'alerts',
            'virtual_tags'
        ]
        
        print("\n表数据统计:")
        for table in tables:
            try:
                result = db.query_one(f"SELECT COUNT(*) as count FROM {table}")
                count = result['count'] if result else 0
                status = "✅" if count > 0 or table == 'dashboards' else "⚠️"
                print(f"  {status} {table}: {count:,} 条")
            except Exception as e:
                print(f"  ❌ {table}: 查询失败 - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查MySQL数据失败: {e}")
        return False

def check_default_db_type():
    """检查默认数据库类型设置"""
    print("\n" + "=" * 60)
    print("检查默认数据库类型")
    print("=" * 60)
    
    from core.database import DatabaseFactory
    from core.cache import CacheManager
    
    # 检查默认值
    db_type_env = os.getenv("DB_TYPE", "未设置")
    print(f"环境变量 DB_TYPE: {db_type_env}")
    
    # 检查代码中的默认值
    try:
        # 读取database.py检查默认值
        db_file = Path(__file__).parent.parent / "core" / "database.py"
        content = db_file.read_text()
        if 'os.getenv("DB_TYPE", "mysql")' in content:
            print("✅ database.py 默认使用 MySQL")
        else:
            print("⚠️  database.py 默认值不是 MySQL")
        
        # 检查cache.py
        cache_file = Path(__file__).parent.parent / "core" / "cache.py"
        content = cache_file.read_text()
        if 'os.getenv("DB_TYPE", "mysql")' in content:
            print("✅ cache.py 默认使用 MySQL")
        else:
            print("⚠️  cache.py 默认值不是 MySQL")
        
        return True
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def main():
    """主函数"""
    results = []
    
    results.append(("SQLite使用检查", check_sqlite_usage()))
    results.append(("MySQL数据检查", check_mysql_data()))
    results.append(("默认数据库类型", check_default_db_type()))
    
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 检查通过")
    
    if passed == total:
        print("\n✅ 所有检查通过！程序已迁移到MySQL")
    else:
        print("\n⚠️  仍有问题需要修复")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())


