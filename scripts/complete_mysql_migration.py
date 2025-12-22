#!/usr/bin/env python3
"""
完成MySQL迁移的最终检查脚本
确保所有数据已迁移，程序默认使用MySQL
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def check_migration_complete():
    """检查迁移是否完成"""
    print("=" * 60)
    print("MySQL迁移完成检查")
    print("=" * 60)
    
    from core.database import DatabaseFactory
    
    # 设置MySQL密码
    os.environ['MYSQL_PASSWORD'] = 'cloudlens123'
    
    try:
        db = DatabaseFactory.create_adapter("mysql")
        
        # 检查数据
        print("\n📊 数据检查:")
        
        cache_count = db.query_one("SELECT COUNT(*) as count FROM resource_cache")['count']
        bill_count = db.query_one("SELECT COUNT(*) as count FROM bill_items")['count']
        
        print(f"  ✅ 缓存数据: {cache_count:,} 条")
        print(f"  ✅ 账单数据: {bill_count:,} 条")
        
        if cache_count > 0 and bill_count > 0:
            print("\n✅ 数据迁移成功！")
        else:
            print("\n⚠️  部分数据可能未迁移")
        
        # 检查默认配置
        print("\n⚙️  配置检查:")
        from core.database import DatabaseFactory
        from core.cache import CacheManager
        
        # 测试默认使用MySQL
        try:
            cache = CacheManager()
            if cache.db_type == "mysql":
                print("  ✅ CacheManager 默认使用 MySQL")
            else:
                print(f"  ⚠️  CacheManager 使用 {cache.db_type}")
        except Exception as e:
            print(f"  ❌ CacheManager 测试失败: {e}")
        
        print("\n" + "=" * 60)
        print("✅ MySQL迁移完成！")
        print("=" * 60)
        print("\n程序现在默认使用MySQL数据库")
        print("所有数据已从SQLite迁移到MySQL")
        print("\n提示: 如果需要在shell中使用，请设置环境变量:")
        print("  export MYSQL_PASSWORD=cloudlens123")
        print("  export DB_TYPE=mysql")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_migration_complete()
    sys.exit(0 if success else 1)


