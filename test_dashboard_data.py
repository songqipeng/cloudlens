#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试 Dashboard 数据获取
"""
import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_backend_connection():
    """测试后端连接"""
    print("=" * 60)
    print("测试 1: 后端服务连接")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/accounts", timeout=5)
        if response.status_code == 200:
            print("✅ 后端服务连接成功")
            return True
        else:
            print(f"⚠️  后端服务响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 后端服务未运行")
        print("   请启动后端服务: cd web/backend && python3 -m uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_accounts():
    """测试账号列表"""
    print("\n" + "=" * 60)
    print("测试 2: 获取账号列表")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/accounts", timeout=5)
        if response.status_code == 200:
            accounts = response.json()
            print(f"✅ 找到 {len(accounts)} 个账号")
            for acc in accounts:
                print(f"   - {acc.get('name', 'unknown')} ({acc.get('region', 'unknown')})")
            return accounts[0].get('name') if accounts else None
        else:
            print(f"❌ 获取账号列表失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None

def test_dashboard_summary(account):
    """测试 Dashboard Summary"""
    print("\n" + "=" * 60)
    print(f"测试 3: Dashboard Summary (账号: {account})")
    print("=" * 60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/dashboard/summary",
            params={"account": account},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Summary API 响应成功")
            print(f"   总成本: {data.get('total_cost', 'N/A')}")
            print(f"   闲置资源数: {data.get('idle_count', 'N/A')}")
            print(f"   资源总数: {data.get('total_resources', 'N/A')}")
            print(f"   告警数量: {data.get('alert_count', 'N/A')}")
            print(f"   标签覆盖率: {data.get('tag_coverage', 'N/A')}%")
            print(f"   节省潜力: {data.get('savings_potential', 'N/A')}")
            print(f"   是否缓存: {data.get('cached', False)}")
            return data
        else:
            print(f"❌ Summary API 失败: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_dashboard_idle(account):
    """测试 Dashboard Idle Resources"""
    print("\n" + "=" * 60)
    print(f"测试 4: Dashboard Idle Resources (账号: {account})")
    print("=" * 60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/dashboard/idle",
            params={"account": account},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Idle API 响应成功")
            print(f"   返回格式: {type(data)}")
            
            if isinstance(data, dict):
                print(f"   数据键: {list(data.keys())}")
                if 'data' in data:
                    idle_list = data['data']
                    print(f"   闲置资源数量: {len(idle_list) if isinstance(idle_list, list) else 'N/A'}")
                    if isinstance(idle_list, list) and len(idle_list) > 0:
                        print(f"   示例资源:")
                        for i, item in enumerate(idle_list[:3]):
                            print(f"     {i+1}. {item.get('name', 'N/A')} ({item.get('instance_id', 'N/A')})")
                else:
                    print(f"   ⚠️  没有 'data' 键")
            elif isinstance(data, list):
                print(f"   闲置资源数量: {len(data)}")
                if len(data) > 0:
                    print(f"   示例资源:")
                    for i, item in enumerate(data[:3]):
                        print(f"     {i+1}. {item.get('name', 'N/A')} ({item.get('instance_id', 'N/A')})")
            else:
                print(f"   ⚠️  未知数据格式: {type(data)}")
            
            return data
        else:
            print(f"❌ Idle API 失败: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_dashboard_trend(account):
    """测试 Dashboard Trend"""
    print("\n" + "=" * 60)
    print(f"测试 5: Dashboard Trend (账号: {account})")
    print("=" * 60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/dashboard/trend",
            params={"account": account, "days": 30},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Trend API 响应成功")
            if isinstance(data, dict) and 'chart_data' in data:
                chart_data = data['chart_data']
                if isinstance(chart_data, dict) and 'dates' in chart_data:
                    print(f"   数据点数量: {len(chart_data.get('dates', []))}")
                    print(f"   成本数据: {len(chart_data.get('costs', []))}")
            return data
        else:
            print(f"❌ Trend API 失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None

def test_trigger_scan(account):
    """测试触发扫描"""
    print("\n" + "=" * 60)
    print(f"测试 6: 触发扫描 (账号: {account})")
    print("=" * 60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/analyze/trigger",
            json={
                "account": account,
                "days": 7,
                "force": False  # 不强制刷新，使用缓存
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 扫描触发成功")
            print(f"   状态: {data.get('status', 'N/A')}")
            if 'count' in data:
                print(f"   闲置资源数: {data.get('count', 'N/A')}")
            return data
        else:
            print(f"❌ 扫描触发失败: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None

def main():
    print("\n" + "=" * 60)
    print("CloudLens Dashboard 完整数据测试")
    print("=" * 60 + "\n")
    
    # 测试后端连接
    if not test_backend_connection():
        print("\n❌ 后端服务未运行，无法继续测试")
        sys.exit(1)
    
    # 获取账号
    account = test_accounts()
    if not account:
        print("\n❌ 没有可用账号，无法继续测试")
        sys.exit(1)
    
    # 测试各个 API
    summary = test_dashboard_summary(account)
    idle = test_dashboard_idle(account)
    trend = test_dashboard_trend(account)
    
    # 如果数据为空，尝试触发扫描
    if (not idle or (isinstance(idle, dict) and len(idle.get('data', [])) == 0) or 
        (isinstance(idle, list) and len(idle) == 0)):
        print("\n⚠️  闲置资源数据为空，尝试触发扫描...")
        scan_result = test_trigger_scan(account)
        
        if scan_result and scan_result.get('status') == 'processing':
            print("\n⏳ 扫描任务已启动，请等待完成后重新测试")
        elif scan_result and scan_result.get('status') == 'success':
            print("\n✅ 扫描完成，重新获取数据...")
            idle = test_dashboard_idle(account)
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"✅ 后端服务: 运行中")
    print(f"✅ 账号: {account}")
    print(f"{'✅' if summary else '❌'} Summary API: {'正常' if summary else '失败'}")
    print(f"{'✅' if idle else '❌'} Idle API: {'正常' if idle else '失败'}")
    print(f"{'✅' if trend else '❌'} Trend API: {'正常' if trend else '失败'}")
    
    # 检查数据量
    if idle:
        if isinstance(idle, dict) and 'data' in idle:
            idle_count = len(idle['data']) if isinstance(idle['data'], list) else 0
        elif isinstance(idle, list):
            idle_count = len(idle)
        else:
            idle_count = 0
        
        if idle_count == 0:
            print("\n⚠️  警告: 闲置资源数据为空")
            print("   可能原因:")
            print("   1. 账号下确实没有闲置资源")
            print("   2. 缓存数据为空，需要触发扫描")
            print("   3. 扫描任务还在进行中")
        else:
            print(f"\n✅ 找到 {idle_count} 个闲置资源")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()


