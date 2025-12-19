#!/usr/bin/env python3
"""
最终验证：确保MySQL迁移完成，程序正常工作
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def verify_mysql_migration():
    """验证MySQL迁移完成"""
    print("=" * 60)
    print("MySQL迁移最终验证")
    print("=" * 60)
    
    # 设置环境变量
    os.environ['MYSQL_PASSWORD'] = 'cloudlens123'
    os.environ['DB_TYPE'] = 'mysql'
    
    results = []
    
    # 1. 验证数据库连接
    print("\n1. 验证数据库连接...")
    try:
        from core.database import DatabaseFactory
        db = DatabaseFactory.create_adapter("mysql")
        result = db.query_one("SELECT VERSION() as version")
        print(f"   ✅ MySQL连接成功，版本: {result['version']}")
        results.append(True)
    except Exception as e:
        print(f"   ❌ MySQL连接失败: {e}")
        results.append(False)
    
    # 2. 验证数据迁移
    print("\n2. 验证数据迁移...")
    try:
        cache_count = db.query_one("SELECT COUNT(*) as count FROM resource_cache")['count']
        bill_count = db.query_one("SELECT COUNT(*) as count FROM bill_items")['count']
        
        if cache_count > 0 and bill_count > 0:
            print(f"   ✅ 缓存数据: {cache_count:,} 条")
            print(f"   ✅ 账单数据: {bill_count:,} 条")
            results.append(True)
        else:
            print(f"   ⚠️  数据可能未完全迁移")
            results.append(False)
    except Exception as e:
        print(f"   ❌ 数据验证失败: {e}")
        results.append(False)
    
    # 3. 验证CacheManager
    print("\n3. 验证CacheManager...")
    try:
        from core.cache import CacheManager
        cache = CacheManager()
        if cache.db_type == "mysql":
            print(f"   ✅ CacheManager 使用 MySQL")
            # 测试读写
            cache.set("test", "test_account", [{"id": "test1"}])
            data = cache.get("test", "test_account")
            if data and data[0]["id"] == "test1":
                print(f"   ✅ 缓存读写测试成功")
                cache.clear("test", "test_account")
                results.append(True)
            else:
                print(f"   ⚠️  缓存读写测试失败")
                results.append(False)
        else:
            print(f"   ❌ CacheManager 使用 {cache.db_type}，不是MySQL")
            results.append(False)
    except Exception as e:
        print(f"   ❌ CacheManager验证失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(False)
    
    # 4. 验证BillStorageManager
    print("\n4. 验证BillStorageManager...")
    try:
        from core.bill_storage import BillStorageManager
        storage = BillStorageManager()
        if storage.db_type == "mysql":
            print(f"   ✅ BillStorageManager 使用 MySQL")
            stats = storage.get_storage_stats()
            print(f"   ✅ 账单统计: {stats['total_records']:,} 条记录")
            results.append(True)
        else:
            print(f"   ❌ BillStorageManager 使用 {storage.db_type}")
            results.append(False)
    except Exception as e:
        print(f"   ❌ BillStorageManager验证失败: {e}")
        results.append(False)
    
    # 5. 验证API端点
    print("\n5. 验证API端点...")
    try:
        import requests
        response = requests.get("http://127.0.0.1:8000/api/resources?type=vpc&page=1&pageSize=1&force_refresh=true", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and len(data.get("data", [])) > 0:
                vpc = data["data"][0]
                if vpc.get("vpc_id"):
                    print(f"   ✅ API正常，VPC ID: {vpc.get('vpc_id')}")
                    results.append(True)
                else:
                    print(f"   ⚠️  API返回数据但vpc_id为空")
                    results.append(False)
            else:
                print(f"   ⚠️  API返回但数据为空")
                results.append(False)
        else:
            print(f"   ❌ API返回状态码: {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"   ⚠️  API验证失败（可能服务未启动）: {e}")
        results.append(False)
    
    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    checks = [
        "数据库连接",
        "数据迁移",
        "CacheManager",
        "BillStorageManager",
        "API端点"
    ]
    
    for i, (check, result) in enumerate(zip(checks, results)):
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{check}: {status}")
    
    print(f"\n总计: {passed}/{total} 检查通过")
    
    if passed == total:
        print("\n🎉 所有验证通过！MySQL迁移完成，程序正常工作！")
        return True
    else:
        print(f"\n⚠️  有 {total - passed} 项检查未通过，请检查上述问题")
        return False

if __name__ == "__main__":
    success = verify_mysql_migration()
    sys.exit(0 if success else 1)

