#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面测试所有页面数据获取
"""
import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"
ACCOUNT = "ydzn"

def test_api(endpoint, params=None, method="GET", data=None):
    """测试 API 端点"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=30)
        else:
            response = requests.post(f"{BASE_URL}{endpoint}", params=params, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return True, result
        else:
            return False, f"HTTP {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 80)
    print("CloudLens 全面功能测试")
    print("=" * 80)
    
    results = {}
    
    # 1. 仪表盘 Summary
    print("\n1. 测试仪表盘 Summary...")
    success, data = test_api("/api/dashboard/summary", {"account": ACCOUNT, "force_refresh": True})
    if success:
        results["summary"] = {
            "total_cost": data.get("total_cost"),
            "total_resources": data.get("total_resources"),
            "idle_count": data.get("idle_count"),
            "resource_breakdown": data.get("resource_breakdown", {}),
            "cached": data.get("cached", False)
        }
        print(f"   ✅ 总成本: {data.get('total_cost', 'N/A')}")
        print(f"   ✅ 资源总数: {data.get('total_resources', 'N/A')}")
        print(f"   ✅ 闲置资源: {data.get('idle_count', 'N/A')}")
        print(f"   ✅ 资源分布: {data.get('resource_breakdown', {})}")
    else:
        print(f"   ❌ 失败: {data}")
        results["summary"] = {"error": data}
    
    # 2. 仪表盘 Idle
    print("\n2. 测试仪表盘 Idle Resources...")
    success, data = test_api("/api/dashboard/idle", {"account": ACCOUNT, "force_refresh": True})
    if success:
        idle_list = data.get("data", []) if isinstance(data, dict) else data
        results["idle"] = {"count": len(idle_list) if isinstance(idle_list, list) else 0}
        print(f"   ✅ 闲置资源数: {len(idle_list) if isinstance(idle_list, list) else 0}")
    else:
        print(f"   ❌ 失败: {data}")
        results["idle"] = {"error": data}
    
    # 3. 仪表盘 Trend
    print("\n3. 测试仪表盘 Trend...")
    success, data = test_api("/api/dashboard/trend", {"account": ACCOUNT, "days": 30})
    if success:
        chart_data = data.get("chart_data", {}) if isinstance(data, dict) else {}
        dates_count = len(chart_data.get("dates", [])) if isinstance(chart_data, dict) else 0
        results["trend"] = {"data_points": dates_count}
        print(f"   ✅ 数据点: {dates_count}")
    else:
        print(f"   ❌ 失败: {data}")
        results["trend"] = {"error": data}
    
    # 4. 资源列表 (ECS)
    print("\n4. 测试资源列表 (ECS)...")
    success, data = test_api("/api/resources", {"account": ACCOUNT, "type": "ecs", "page": 1, "pageSize": 10})
    if success:
        if isinstance(data, dict) and "data" in data:
            items = data["data"].get("items", []) if isinstance(data["data"], dict) else data["data"]
            total = data["data"].get("pagination", {}).get("total", 0) if isinstance(data["data"], dict) else len(items)
        elif isinstance(data, list):
            items = data
            total = len(data)
        else:
            items = []
            total = 0
        results["resources_ecs"] = {"total": total, "items": len(items)}
        print(f"   ✅ 总资源数: {total}, 返回: {len(items)}")
    else:
        print(f"   ❌ 失败: {data}")
        results["resources_ecs"] = {"error": data}
    
    # 5. 成本分析 - 账单概览
    print("\n5. 测试成本分析 - 账单概览...")
    success, data = test_api("/api/billing/overview", {"account": ACCOUNT})
    if success:
        total_cost = data.get("total_pretax", 0) if isinstance(data, dict) else 0
        results["billing_overview"] = {"total_cost": total_cost}
        print(f"   ✅ 总成本: {total_cost}")
    else:
        print(f"   ❌ 失败: {data}")
        results["billing_overview"] = {"error": data}
    
    # 6. 折扣分析
    print("\n6. 测试折扣分析...")
    success, data = test_api("/api/discounts/trend", {"account": ACCOUNT, "months": 6})
    if success:
        discount_data = data.get("data", {}) if isinstance(data, dict) else data
        results["discount"] = {"has_data": bool(discount_data)}
        print(f"   ✅ 有数据: {bool(discount_data)}")
    else:
        print(f"   ❌ 失败: {data}")
        results["discount"] = {"error": data}
    
    # 7. 优化建议
    print("\n7. 测试优化建议...")
    success, data = test_api("/api/optimization/suggestions", {"account": ACCOUNT})
    if success:
        suggestions = data.get("suggestions", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        results["optimization"] = {"count": len(suggestions)}
        print(f"   ✅ 优化建议数: {len(suggestions)}")
    else:
        print(f"   ❌ 失败: {data}")
        results["optimization"] = {"error": data}
    
    # 8. 安全合规
    print("\n8. 测试安全合规...")
    success, data = test_api("/api/security/overview", {"account": ACCOUNT})
    if success:
        score = data.get("score", 0) if isinstance(data, dict) else 0
        results["security"] = {"score": score}
        print(f"   ✅ 安全评分: {score}")
    else:
        print(f"   ❌ 失败: {data}")
        results["security"] = {"error": data}
    
    # 9. 预算管理
    print("\n9. 测试预算管理...")
    success, data = test_api("/api/budgets", {"account": ACCOUNT})
    if success:
        budgets = data.get("data", []) if isinstance(data, dict) else data
        results["budgets"] = {"count": len(budgets) if isinstance(budgets, list) else 0}
        print(f"   ✅ 预算数: {len(budgets) if isinstance(budgets, list) else 0}")
    else:
        print(f"   ❌ 失败: {data}")
        results["budgets"] = {"error": data}
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    for key, value in results.items():
        if "error" in value:
            print(f"❌ {key}: {value['error']}")
        else:
            print(f"✅ {key}: {json.dumps(value, ensure_ascii=False)}")
    
    # 检查哪些功能没有数据
    print("\n" + "=" * 80)
    print("数据缺失分析")
    print("=" * 80)
    
    issues = []
    if results.get("summary", {}).get("total_resources", 0) == 0:
        issues.append("仪表盘 Summary: 资源总数为 0")
    if results.get("resources_ecs", {}).get("total", 0) == 0:
        issues.append("资源列表: ECS 资源数为 0")
    if results.get("idle", {}).get("count", 0) == 0 and "error" not in results.get("idle", {}):
        issues.append("闲置资源: 数量为 0（可能是正常的）")
    if "error" in results.get("billing_overview", {}):
        issues.append(f"成本分析: API 错误 - {results['billing_overview']['error']}")
    if "error" in results.get("discount", {}):
        issues.append(f"折扣分析: API 错误 - {results['discount']['error']}")
    if "error" in results.get("optimization", {}):
        issues.append(f"优化建议: API 错误 - {results['optimization']['error']}")
    if "error" in results.get("security", {}):
        issues.append(f"安全合规: API 错误 - {results['security']['error']}")
    if "error" in results.get("budgets", {}):
        issues.append(f"预算管理: API 错误 - {results['budgets']['error']}")
    
    if issues:
        print("发现以下问题:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("✅ 所有功能数据正常")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

