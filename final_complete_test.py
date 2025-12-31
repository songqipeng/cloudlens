#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终完整测试 - CLI 和 Web
"""
import requests
import sys
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
ACCOUNT = "ydzn"

def test_web_apis():
    """测试所有 Web API"""
    print("=" * 80)
    print("Web API 完整测试")
    print("=" * 80)
    
    results = {}
    
    # 1. 资源列表（ECS）
    print("\n1. 资源列表 (ECS) - 强制刷新...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/resources",
            params={"account": ACCOUNT, "type": "ecs", "page": 1, "pageSize": 10, "force_refresh": True},
            timeout=180
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
                if isinstance(data['data'], dict):
                    items = data['data'].get('items', [])
                    total = data['data'].get('pagination', {}).get('total', 0)
                else:
                    items = data['data'] if isinstance(data['data'], list) else []
                    total = len(items)
            else:
                items = data if isinstance(data, list) else []
                total = len(items)
            
            results['resources'] = {"total": total, "items": len(items)}
            if total > 0:
                print(f"   ✅ 成功: {total} 个资源")
            else:
                print(f"   ⚠️  资源数为 0")
        else:
            print(f"   ❌ 失败: {response.status_code}")
            results['resources'] = {"error": response.status_code}
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        results['resources'] = {"error": str(e)}
    
    # 2. Dashboard Summary
    print("\n2. Dashboard Summary - 强制刷新...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/dashboard/summary",
            params={"account": ACCOUNT, "force_refresh": True},
            timeout=180
        )
        if response.status_code == 200:
            data = response.json()
            results['summary'] = {
                "total_resources": data.get('total_resources'),
                "total_cost": data.get('total_cost'),
                "resource_breakdown": data.get('resource_breakdown', {}),
                "cached": data.get('cached', False)
            }
            if data.get('total_resources', 0) > 0:
                print(f"   ✅ 成功: {data.get('total_resources')} 个资源")
            else:
                print(f"   ⚠️  资源总数为 0（后台任务可能还在运行）")
        else:
            print(f"   ❌ 失败: {response.status_code}")
            results['summary'] = {"error": response.status_code}
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        results['summary'] = {"error": str(e)}
    
    # 3. Billing Overview
    print("\n3. Billing Overview...")
    try:
        billing_cycle = datetime.now().strftime('%Y-%m')
        response = requests.get(
            f"{BASE_URL}/api/billing/overview",
            params={"account": ACCOUNT, "billing_cycle": billing_cycle},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                bill_data = data.get('data', {})
                items = bill_data.get('Data', {}).get('Items', {}).get('Item', [])
                if not isinstance(items, list):
                    items = [items] if items else []
                results['billing'] = {"items": len(items)}
                if len(items) > 0:
                    total = sum(float(item.get('PretaxAmount', 0) or 0) for item in items)
                    print(f"   ✅ 成功: {len(items)} 条账单，总金额 ¥{total:,.2f}")
                else:
                    print(f"   ⚠️  账单数据为空（可能是当月无消费）")
            else:
                print(f"   ⚠️  响应异常")
                results['billing'] = {"error": "response_error"}
        else:
            print(f"   ❌ 失败: {response.status_code}")
            results['billing'] = {"error": response.status_code}
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        results['billing'] = {"error": str(e)}
    
    # 4. 折扣分析
    print("\n4. 折扣分析...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/discounts/trend",
            params={"account": ACCOUNT, "months": 6},
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            has_data = bool(data.get('data') if isinstance(data, dict) else data)
            results['discount'] = {"has_data": has_data}
            if has_data:
                print(f"   ✅ 成功: 有折扣数据")
            else:
                print(f"   ⚠️  折扣数据为空（需要账单数据支持）")
        else:
            print(f"   ❌ 失败: {response.status_code}")
            results['discount'] = {"error": response.status_code}
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        results['discount'] = {"error": str(e)}
    
    # 5. 安全合规
    print("\n5. 安全合规...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/security/overview",
            params={"account": ACCOUNT},
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            score = data.get('score', 0) if isinstance(data, dict) else 0
            results['security'] = {"score": score}
            if score > 0:
                print(f"   ✅ 成功: 安全评分 {score}")
            else:
                print(f"   ⚠️  安全评分为 0（需要资源数据支持）")
        else:
            print(f"   ❌ 失败: {response.status_code}")
            results['security'] = {"error": response.status_code}
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        results['security'] = {"error": str(e)}
    
    # 6. 优化建议
    print("\n6. 优化建议...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/optimization/suggestions",
            params={"account": ACCOUNT},
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            suggestions = data.get('suggestions', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            results['optimization'] = {"count": len(suggestions)}
            if len(suggestions) > 0:
                print(f"   ✅ 成功: {len(suggestions)} 条优化建议")
            else:
                print(f"   ⚠️  优化建议为空（需要资源数据支持）")
        else:
            print(f"   ❌ 失败: {response.status_code}")
            results['optimization'] = {"error": response.status_code}
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        results['optimization'] = {"error": str(e)}
    
    return results

def test_cli():
    """测试 CLI 功能"""
    print("\n" + "=" * 80)
    print("CLI 功能测试")
    print("=" * 80)
    
    results = {}
    
    # 测试模块导入
    print("\n1. CLI 模块导入...")
    try:
        from cli.main import cli
        print("   ✅ CLI 主模块导入成功")
        results['cli_import'] = True
    except Exception as e:
        print(f"   ❌ CLI 主模块导入失败: {e}")
        results['cli_import'] = False
        return results
    
    # 测试命令模块
    commands = [
        ("config", "配置管理"),
        ("query", "资源查询"),
        ("analyze", "资源分析"),
        ("cache", "缓存管理"),
        ("bill", "账单管理"),
        ("remediate", "修复建议"),
    ]
    
    print("\n2. 命令模块导入...")
    for cmd_name, desc in commands:
        try:
            module = __import__(f"cli.commands.{cmd_name}_cmd", fromlist=[cmd_name])
            cmd_func = getattr(module, cmd_name, None)
            if cmd_func:
                print(f"   ✅ {desc} ({cmd_name}) 可用")
                results[f'cmd_{cmd_name}'] = True
            else:
                print(f"   ⚠️  {desc} ({cmd_name}) 缺少函数")
                results[f'cmd_{cmd_name}'] = False
        except Exception as e:
            print(f"   ⚠️  {desc} ({cmd_name}) 导入失败: {e}")
            results[f'cmd_{cmd_name}'] = False
    
    # 测试核心功能
    print("\n3. 核心功能...")
    try:
        from core.config import ConfigManager
        cm = ConfigManager()
        accounts = cm.list_accounts()
        print(f"   ✅ 配置管理: {len(accounts)} 个账号")
        results['config'] = len(accounts)
    except Exception as e:
        print(f"   ❌ 配置管理失败: {e}")
        results['config'] = False
    
    try:
        from core.cache import CacheManager
        cache = CacheManager()
        print("   ✅ 缓存管理: 正常")
        results['cache'] = True
    except Exception as e:
        print(f"   ❌ 缓存管理失败: {e}")
        results['cache'] = False
    
    try:
        from core.services.analysis_service import AnalysisService
        print("   ✅ 分析服务: 正常")
        results['analysis'] = True
    except Exception as e:
        print(f"   ❌ 分析服务失败: {e}")
        results['analysis'] = False
    
    try:
        from providers.aliyun.provider import AliyunProvider
        print("   ✅ 阿里云 Provider: 正常")
        results['provider'] = True
    except Exception as e:
        print(f"   ❌ 阿里云 Provider 失败: {e}")
        results['provider'] = False
    
    return results

def main():
    print("\n" + "=" * 80)
    print("CloudLens 完整功能测试（CLI + Web）")
    print("=" * 80)
    
    # 测试 Web API
    web_results = test_web_apis()
    
    # 测试 CLI
    cli_results = test_cli()
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    print("\nWeb API 测试结果:")
    for key, value in web_results.items():
        if "error" in value:
            print(f"  ❌ {key}: {value['error']}")
        else:
            print(f"  ✅ {key}: {value}")
    
    print("\nCLI 测试结果:")
    for key, value in cli_results.items():
        if value:
            print(f"  ✅ {key}: {value}")
        else:
            print(f"  ❌ {key}: 失败")
    
    # 检查关键功能
    print("\n关键功能状态:")
    if web_results.get('resources', {}).get('total', 0) > 0:
        print("  ✅ 资源查询: 正常")
    else:
        print("  ⚠️  资源查询: 需要等待后台任务完成或检查代码")
    
    if web_results.get('billing', {}).get('items', 0) > 0:
        print("  ✅ 账单数据: 正常")
    else:
        print("  ⚠️  账单数据: 可能当月无消费或需要权限")
    
    if cli_results.get('cli_import'):
        print("  ✅ CLI 功能: 正常")
    else:
        print("  ❌ CLI 功能: 异常")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()



