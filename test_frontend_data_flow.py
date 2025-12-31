#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前端数据流 - 模拟前端如何解析后端数据
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"
ACCOUNT = "ydzn"

def test_api_responses():
    """测试 API 实际返回的数据格式"""
    print("=" * 80)
    print("测试后端 API 返回的数据格式")
    print("=" * 80)
    
    # 1. 测试 Idle API
    print("\n1. 测试 /api/dashboard/idle")
    try:
        response = requests.get(f"{BASE_URL}/dashboard/idle", params={"account": ACCOUNT}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 状态码: {response.status_code}")
            print(f"返回类型: {type(data)}")
            
            # 模拟前端解析逻辑
            idle_data = []
            if data and isinstance(data, dict):
                if "success" in data and "data" in data:
                    if isinstance(data["data"], list):
                        idle_data = data["data"]
                        print(f"✅ 格式: {{success: true, data: [...]}}")
                        print(f"✅ 数据长度: {len(idle_data)}")
                    else:
                        print(f"⚠️  data 不是数组: {type(data['data'])}")
                elif "data" in data and isinstance(data["data"], list):
                    idle_data = data["data"]
                    print(f"✅ 格式: {{data: [...]}}")
                    print(f"✅ 数据长度: {len(idle_data)}")
                elif isinstance(data, list):
                    idle_data = data
                    print(f"✅ 格式: 直接数组")
                    print(f"✅ 数据长度: {len(idle_data)}")
                else:
                    print(f"⚠️  未知格式: {list(data.keys())}")
            elif isinstance(data, list):
                idle_data = data
                print(f"✅ 格式: 直接数组")
                print(f"✅ 数据长度: {len(idle_data)}")
            
            if len(idle_data) > 0:
                print(f"✅ 第一条数据: {json.dumps(idle_data[0], ensure_ascii=False, default=str)[:150]}")
                return idle_data
            else:
                print("⚠️  数据为空")
                return []
        else:
            print(f"❌ 状态码: {response.status_code}")
            print(response.text[:200])
            return []
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return []
    
    # 2. 测试 Summary API
    print("\n2. 测试 /api/dashboard/summary")
    try:
        response = requests.get(f"{BASE_URL}/dashboard/summary", params={"account": ACCOUNT}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 状态码: {response.status_code}")
            print(f"返回类型: {type(data)}")
            
            # 模拟前端解析逻辑
            summary_data = None
            if data and isinstance(data, dict):
                if "success" in data and "data" in data:
                    summary_data = data["data"]
                    print(f"✅ 格式: {{success: true, data: {{...}}}}")
                else:
                    summary_data = data
                    print(f"✅ 格式: 直接对象")
                
                print(f"idle_count: {summary_data.get('idle_count', 'N/A')}")
                print(f"total_resources: {summary_data.get('total_resources', 'N/A')}")
                print(f"total_cost: {summary_data.get('total_cost', 'N/A')}")
                return summary_data
            else:
                print(f"⚠️  未知格式: {type(data)}")
                return None
        else:
            print(f"❌ 状态码: {response.status_code}")
            print(response.text[:200])
            return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

def main():
    idle_data = test_api_responses()
    summary_data = test_api_responses()
    
    print("\n" + "=" * 80)
    print("数据流测试结果")
    print("=" * 80)
    
    if idle_data and len(idle_data) > 0:
        print(f"✅ Idle 数据: {len(idle_data)} 条")
    else:
        print("❌ Idle 数据: 无数据")
    
    if summary_data:
        print(f"✅ Summary 数据: idle_count={summary_data.get('idle_count', 'N/A')}")
    else:
        print("❌ Summary 数据: 无数据")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()



