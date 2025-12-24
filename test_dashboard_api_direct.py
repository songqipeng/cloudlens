#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试 Dashboard API
不依赖外部模块，直接调用函数
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ.setdefault("DB_TYPE", "mysql")

def test_api_direct():
    """直接测试 API 函数"""
    print("=" * 60)
    print("Dashboard API 直接测试")
    print("=" * 60)
    
    try:
        # 导入必要的模块
        from core.config import ConfigManager
        
        # 获取账号列表
        cm = ConfigManager()
        accounts = cm.list_accounts()
        
        if not accounts:
            print("❌ 没有找到可用账号")
            return False
        
        # 使用第一个账号
        test_account = accounts[0].name if hasattr(accounts[0], 'name') else str(accounts[0])
        print(f"\n📋 测试账号: {test_account}")
        
        # 直接导入并调用函数（绕过 FastAPI）
        print("\n🔍 测试 get_summary 函数...")
        
        # 由于 get_summary 是 async 函数，我们需要用同步方式测试
        # 或者创建一个同步包装器
        import asyncio
        from web.backend.api import get_summary
        
        # 运行异步函数
        try:
            result = asyncio.run(get_summary(account=test_account, force_refresh=False))
        except RuntimeError:
            # 如果已经在事件循环中，使用不同的方法
            import nest_asyncio
            nest_asyncio.apply()
            result = asyncio.run(get_summary(account=test_account, force_refresh=False))
        
        print(f"\n✅ API 调用成功!")
        print(f"\n返回数据结构:")
        print(f"  - account: {result.get('account')} (type: {type(result.get('account'))})")
        print(f"  - total_cost: {result.get('total_cost')} (type: {type(result.get('total_cost'))})")
        print(f"  - idle_count: {result.get('idle_count')} (type: {type(result.get('idle_count'))})")
        print(f"  - cost_trend: {result.get('cost_trend')} (type: {type(result.get('cost_trend'))})")
        print(f"  - trend_pct: {result.get('trend_pct')} (type: {type(result.get('trend_pct'))})")
        print(f"  - total_resources: {result.get('total_resources')} (type: {type(result.get('total_resources'))})")
        print(f"  - resource_breakdown: {result.get('resource_breakdown')} (type: {type(result.get('resource_breakdown'))})")
        print(f"  - alert_count: {result.get('alert_count')} (type: {type(result.get('alert_count'))})")
        print(f"  - tag_coverage: {result.get('tag_coverage')} (type: {type(result.get('tag_coverage'))})")
        print(f"  - savings_potential: {result.get('savings_potential')} (type: {type(result.get('savings_potential'))})")
        print(f"  - cached: {result.get('cached')} (type: {type(result.get('cached'))})")
        
        # 验证必需字段
        required_fields = [
            "account", "total_cost", "idle_count", "cost_trend", 
            "trend_pct", "total_resources", "resource_breakdown",
            "alert_count", "tag_coverage", "savings_potential", "cached"
        ]
        
        missing_fields = [field for field in required_fields if field not in result]
        if missing_fields:
            print(f"\n❌ 缺少字段: {missing_fields}")
            return False
        
        # 验证数据类型
        checks = [
            (result["account"], str, "account"),
            (result["total_cost"], (int, float), "total_cost"),
            (result["idle_count"], int, "idle_count"),
            (result["cost_trend"], str, "cost_trend"),
            (result["trend_pct"], (int, float), "trend_pct"),
            (result["total_resources"], int, "total_resources"),
            (result["resource_breakdown"], dict, "resource_breakdown"),
            (result["alert_count"], int, "alert_count"),
            (result["tag_coverage"], (int, float), "tag_coverage"),
            (result["savings_potential"], (int, float), "savings_potential"),
            (result["cached"], bool, "cached"),
        ]
        
        print(f"\n🔍 验证数据类型...")
        all_valid = True
        for value, expected_type, field_name in checks:
            if not isinstance(value, expected_type):
                print(f"  ❌ {field_name}: 期望 {expected_type}, 实际 {type(value)}")
                all_valid = False
            else:
                print(f"  ✅ {field_name}: {type(value).__name__}")
        
        if not all_valid:
            return False
        
        # 验证 resource_breakdown 结构
        breakdown = result["resource_breakdown"]
        if not isinstance(breakdown, dict):
            print(f"\n❌ resource_breakdown 不是字典")
            return False
        
        expected_keys = ["ecs", "rds", "redis"]
        for key in expected_keys:
            if key not in breakdown:
                print(f"  ⚠️  resource_breakdown 缺少键: {key}")
        
        print(f"\n✅ 所有验证通过！数据格式正确！")
        return True
        
    except Exception as e:
        import traceback
        print(f"\n❌ 测试失败: {str(e)}")
        print("\n详细错误:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_api_direct()
    sys.exit(0 if success else 1)

