#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动测试 Dashboard API
用于验证 dashboard/summary 端点是否正常工作
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ.setdefault("DB_TYPE", "mysql")

def test_dashboard_summary():
    """测试 dashboard summary API"""
    from web.backend.api import get_summary
    from core.config import ConfigManager
    
    # 获取第一个可用账号
    cm = ConfigManager()
    accounts = cm.list_accounts()
    
    if not accounts:
        print("❌ 没有找到可用账号，请先配置账号")
        return False
    
    # 使用第一个账号
    test_account = accounts[0].name if hasattr(accounts[0], 'name') else str(accounts[0])
    print(f"📋 测试账号: {test_account}")
    
    try:
        # 测试获取 summary
        print("\n🔍 测试 /api/dashboard/summary...")
        result = get_summary(account=test_account, force_refresh=False)
        
        print(f"✅ 成功获取数据!")
        print(f"   - account: {result.get('account')}")
        print(f"   - total_cost: {result.get('total_cost')}")
        print(f"   - idle_count: {result.get('idle_count')}")
        print(f"   - cost_trend: {result.get('cost_trend')}")
        print(f"   - trend_pct: {result.get('trend_pct')}")
        print(f"   - total_resources: {result.get('total_resources')}")
        print(f"   - resource_breakdown: {result.get('resource_breakdown')}")
        print(f"   - tag_coverage: {result.get('tag_coverage')}")
        print(f"   - savings_potential: {result.get('savings_potential')}")
        print(f"   - cached: {result.get('cached')}")
        
        # 验证数据结构
        required_fields = [
            "account", "total_cost", "idle_count", "cost_trend", 
            "trend_pct", "total_resources", "resource_breakdown",
            "alert_count", "tag_coverage", "savings_potential", "cached"
        ]
        
        missing_fields = [field for field in required_fields if field not in result]
        if missing_fields:
            print(f"❌ 缺少字段: {missing_fields}")
            return False
        
        # 验证数据类型
        assert isinstance(result["account"], str), "account 应该是字符串"
        assert isinstance(result["total_cost"], (int, float)), "total_cost 应该是数字"
        assert isinstance(result["idle_count"], int), "idle_count 应该是整数"
        assert isinstance(result["cost_trend"], str), "cost_trend 应该是字符串"
        assert isinstance(result["trend_pct"], (int, float)), "trend_pct 应该是数字"
        assert isinstance(result["total_resources"], int), "total_resources 应该是整数"
        assert isinstance(result["resource_breakdown"], dict), "resource_breakdown 应该是字典"
        assert isinstance(result["cached"], bool), "cached 应该是布尔值"
        
        print("\n✅ 所有测试通过！数据结构正确！")
        return True
        
    except Exception as e:
        import traceback
        print(f"\n❌ 测试失败: {str(e)}")
        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = test_dashboard_summary()
    sys.exit(0 if success else 1)

