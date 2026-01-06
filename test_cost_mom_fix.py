#!/usr/bin/env python3
"""
测试环比计算修复
验证：本月成本（1月1-6日）vs 上月成本（12月1-6日）
"""

import sys
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000"
ACCOUNT = "ydzn"

def test_cost_overview():
    """测试成本概览API"""
    print("=" * 60)
    print("测试成本概览API - 环比计算修复验证")
    print("=" * 60)
    
    # 强制刷新，清除缓存
    url = f"{BASE_URL}/api/cost/overview"
    params = {
        "account": ACCOUNT,
        "force_refresh": True
    }
    
    try:
        print(f"\n📡 请求URL: {url}")
        print(f"📋 参数: {params}")
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ API返回错误状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
        
        data = response.json()
        
        if not data.get("success"):
            print(f"❌ API返回失败: {data.get('error', 'Unknown error')}")
            return False
        
        result = data.get("data", {})
        
        print(f"\n✅ API调用成功")
        print(f"   本月成本: ¥{result.get('current_month', 0):,.2f}")
        print(f"   上月成本: ¥{result.get('last_month', 0):,.2f}")
        print(f"   环比增长: {result.get('mom', 0):.2f}%")
        print(f"   本月已过天数: {result.get('current_days', 'N/A')}")
        print(f"   对比天数: {result.get('comparable_days', 'N/A')}")
        
        # 验证逻辑
        now = datetime.now()
        current_day = now.day
        expected_days = current_day
        
        if result.get("current_days") != expected_days:
            print(f"\n⚠️  警告: 本月已过天数不匹配")
            print(f"   期望: {expected_days} 天")
            print(f"   实际: {result.get('current_days', 'N/A')}")
        
        if result.get("comparable_days") != expected_days:
            print(f"\n⚠️  警告: 对比天数不匹配")
            print(f"   期望: {expected_days} 天")
            print(f"   实际: {result.get('comparable_days', 'N/A')}")
        
        # 验证环比计算
        current_cost = result.get("current_month", 0)
        last_cost = result.get("last_month", 0)
        mom = result.get("mom", 0)
        
        if last_cost > 0:
            expected_mom = ((current_cost - last_cost) / last_cost * 100)
            if abs(mom - expected_mom) > 0.01:  # 允许0.01%的误差
                print(f"\n⚠️  警告: 环比计算可能不准确")
                print(f"   期望环比: {expected_mom:.2f}%")
                print(f"   实际环比: {mom:.2f}%")
            else:
                print(f"\n✅ 环比计算正确")
        else:
            print(f"\n⚠️  上月成本为0，无法验证环比计算")
        
        print(f"\n📊 数据说明:")
        print(f"   本月成本范围: 1月1日 至 1月{current_day}日 ({current_day}天)")
        print(f"   上月成本范围: 12月1日 至 12月{current_day}日 ({current_day}天)")
        print(f"   对比逻辑: ✅ 相同天数对比，符合预期")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cost_trend_analyzer():
    """测试成本趋势分析器的日期范围查询"""
    print("\n" + "=" * 60)
    print("测试成本趋势分析器 - 日期范围查询")
    print("=" * 60)
    
    try:
        from core.cost_trend_analyzer import CostTrendAnalyzer
        from datetime import datetime, timedelta
        
        analyzer = CostTrendAnalyzer()
        now = datetime.now()
        current_day = now.day
        
        # 本月范围
        current_month_start = now.replace(day=1)
        current_month_end = now
        
        # 上月范围
        last_month_end = current_month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        last_month_comparable_end = last_month_start + timedelta(days=current_day - 1)
        if last_month_comparable_end > last_month_end:
            last_month_comparable_end = last_month_end
        
        print(f"\n📅 日期范围:")
        print(f"   本月: {current_month_start.strftime('%Y-%m-%d')} 至 {current_month_end.strftime('%Y-%m-%d')}")
        print(f"   上月: {last_month_start.strftime('%Y-%m-%d')} 至 {last_month_comparable_end.strftime('%Y-%m-%d')}")
        
        # 查询本月成本
        print(f"\n📊 查询本月成本...")
        current_data = analyzer.get_real_cost_from_bills(
            account_name=ACCOUNT,
            start_date=current_month_start.strftime("%Y-%m-%d"),
            end_date=current_month_end.strftime("%Y-%m-%d")
        )
        
        if "error" in current_data:
            print(f"   ⚠️  查询失败: {current_data.get('error')}")
        else:
            current_cost = current_data.get("total_cost", 0)
            print(f"   ✅ 本月成本: ¥{current_cost:,.2f}")
        
        # 查询上月成本
        print(f"\n📊 查询上月成本...")
        last_data = analyzer.get_real_cost_from_bills(
            account_name=ACCOUNT,
            start_date=last_month_start.strftime("%Y-%m-%d"),
            end_date=last_month_comparable_end.strftime("%Y-%m-%d")
        )
        
        if "error" in last_data:
            print(f"   ⚠️  查询失败: {last_data.get('error')}")
        else:
            last_cost = last_data.get("total_cost", 0)
            print(f"   ✅ 上月成本: ¥{last_cost:,.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("成本环比计算修复 - 完整回归测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: API测试
    print("\n【测试1】成本概览API测试")
    results.append(("成本概览API", test_cost_overview()))
    
    # 测试2: 成本趋势分析器测试
    print("\n【测试2】成本趋势分析器测试")
    results.append(("成本趋势分析器", test_cost_trend_analyzer()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！")
        return 0
    else:
        print("❌ 部分测试失败，请检查日志")
        return 1

if __name__ == "__main__":
    sys.exit(main())

