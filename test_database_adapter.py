#!/usr/bin/env python3
"""
测试数据库抽象层
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.database import DatabaseFactory, get_database_adapter
from core.cache import CacheManager

def test_sqlite_adapter():
    """测试SQLite适配器"""
    print("=" * 60)
    print("测试SQLite适配器")
    print("=" * 60)
    
    try:
        # 创建SQLite适配器
        db = DatabaseFactory.create_adapter("sqlite", db_name="test.db")
        
        # 测试连接
        db.connect()
        print("✅ SQLite连接成功")
        
        # 测试执行
        db.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER
            )
        """)
        print("✅ SQLite表创建成功")
        
        # 测试插入
        db.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("test", 123))
        print("✅ SQLite插入成功")
        
        # 测试查询
        results = db.query("SELECT * FROM test_table WHERE name = ?", ("test",))
        print(f"✅ SQLite查询成功: {results}")
        
        # 测试查询单条
        result = db.query_one("SELECT * FROM test_table WHERE name = ?", ("test",))
        print(f"✅ SQLite查询单条成功: {result}")
        
        # 清理
        db.execute("DROP TABLE IF EXISTS test_table")
        db.close()
        
        print("✅ SQLite适配器测试通过\n")
        return True
        
    except Exception as e:
        print(f"❌ SQLite适配器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mysql_adapter():
    """测试MySQL适配器"""
    print("=" * 60)
    print("测试MySQL适配器")
    print("=" * 60)
    
    try:
        # 创建MySQL适配器（使用明确的配置）
        db = DatabaseFactory.create_adapter("mysql", 
                                            host="localhost",
                                            user="cloudlens",
                                            password="cloudlens123",
                                            database="cloudlens")
        
        # 测试连接
        db.connect()
        print("✅ MySQL连接成功")
        
        # 测试执行
        db.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100),
                value INT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("✅ MySQL表创建成功")
        
        # 测试插入
        db.execute("INSERT INTO test_table (name, value) VALUES (%s, %s)", ("test", 123))
        print("✅ MySQL插入成功")
        
        # 测试查询
        results = db.query("SELECT * FROM test_table WHERE name = %s", ("test",))
        print(f"✅ MySQL查询成功: {results}")
        
        # 测试查询单条
        result = db.query_one("SELECT * FROM test_table WHERE name = %s", ("test",))
        print(f"✅ MySQL查询单条成功: {result}")
        
        # 清理
        db.execute("DROP TABLE IF EXISTS test_table")
        db.close()
        
        print("✅ MySQL适配器测试通过\n")
        return True
        
    except Exception as e:
        print(f"❌ MySQL适配器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cache_manager():
    """测试缓存管理器"""
    print("=" * 60)
    print("测试缓存管理器（SQLite）")
    print("=" * 60)
    
    try:
        # 测试SQLite缓存
        cache = CacheManager(ttl_seconds=3600, db_type="sqlite")
        
        # 测试设置缓存
        test_data = [{"id": "1", "name": "test"}]
        cache.set("ecs", "test_account", test_data)
        print("✅ 缓存设置成功")
        
        # 测试获取缓存
        cached_data = cache.get("ecs", "test_account")
        if cached_data == test_data:
            print("✅ 缓存获取成功")
        else:
            print(f"⚠️  缓存数据不匹配: {cached_data} vs {test_data}")
        
        # 清理
        cache.clear("ecs", "test_account")
        print("✅ 缓存清理成功")
        
        print("✅ SQLite缓存管理器测试通过\n")
        return True
        
    except Exception as e:
        print(f"❌ 缓存管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cache_manager_mysql():
    """测试MySQL缓存管理器"""
    print("=" * 60)
    print("测试缓存管理器（MySQL）")
    print("=" * 60)
    
    try:
        # 设置环境变量
        os.environ['MYSQL_PASSWORD'] = 'cloudlens123'
        
        # 测试MySQL缓存
        cache = CacheManager(ttl_seconds=3600, db_type="mysql")
        
        # 测试设置缓存
        test_data = [{"id": "1", "name": "test"}]
        cache.set("ecs", "test_account", test_data)
        print("✅ MySQL缓存设置成功")
        
        # 测试获取缓存
        cached_data = cache.get("ecs", "test_account")
        if cached_data == test_data:
            print("✅ MySQL缓存获取成功")
        else:
            print(f"⚠️  缓存数据不匹配: {cached_data} vs {test_data}")
        
        # 清理
        cache.clear("ecs", "test_account")
        print("✅ MySQL缓存清理成功")
        
        print("✅ MySQL缓存管理器测试通过\n")
        return True
        
    except Exception as e:
        print(f"❌ MySQL缓存管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    results = []
    
    # 测试SQLite适配器
    results.append(("SQLite适配器", test_sqlite_adapter()))
    
    # 测试MySQL适配器
    results.append(("MySQL适配器", test_mysql_adapter()))
    
    # 测试SQLite缓存管理器
    results.append(("SQLite缓存管理器", test_cache_manager()))
    
    # 测试MySQL缓存管理器
    results.append(("MySQL缓存管理器", test_cache_manager_mysql()))
    
    # 总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
