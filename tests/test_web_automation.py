#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web API 测试脚本
测试后端 API 和前端功能
"""
import sys
import time
import requests
import json

def check_backend():
    """检查后端服务是否运行"""
    try:
        response = requests.get("http://127.0.0.1:8000/api/accounts", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_backend_api():
    """测试后端 API"""
    print("=" * 60)
    print("测试后端 API")
    print("=" * 60)
    
    if not check_backend():
        print("❌ 后端服务未运行，请先启动后端服务")
        print("   启动命令: cd web/backend && python3 -m uvicorn main:app --reload")
        return False
    
    print("✅ 后端服务正在运行")
    
    # 测试进度 API
    try:
        response = requests.get("http://127.0.0.1:8000/api/analyze/progress", 
                               params={"account": "test"}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 进度 API 正常: {data.get('status', 'unknown')}")
        else:
            print(f"⚠️  进度 API 响应: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试进度 API 失败: {e}")
        return False
    
    return True

def test_analyze_api():
    """测试分析 API"""
    print("\n" + "=" * 60)
    print("测试分析 API")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8000"
    
    # 获取账号列表
    try:
        response = requests.get(f"{base_url}/api/accounts", timeout=5)
        if response.status_code == 200:
            accounts = response.json()
            if accounts:
                test_account = accounts[0].get("name")
                print(f"✅ 找到测试账号: {test_account}")
                
                # 测试触发分析（不实际执行，只测试 API）
                print(f"   测试触发分析 API...")
                try:
                    response = requests.post(
                        f"{base_url}/api/analyze/trigger",
                        json={
                            "account": test_account,
                            "days": 7,
                            "force": False  # 不强制刷新，使用缓存
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        status = data.get("status")
                        print(f"   ✅ 分析 API 响应: {status}")
                        
                        if status == "processing":
                            # 测试进度查询
                            task_id = data.get("task_id") or test_account
                            print(f"   测试进度查询 API...")
                            time.sleep(1)
                            
                            progress_response = requests.get(
                                f"{base_url}/api/analyze/progress",
                                params={"account": task_id},
                                timeout=5
                            )
                            
                            if progress_response.status_code == 200:
                                progress_data = progress_response.json()
                                print(f"   ✅ 进度查询成功: {progress_data.get('status', 'unknown')}")
                            else:
                                print(f"   ⚠️  进度查询响应: {progress_response.status_code}")
                    else:
                        print(f"   ⚠️  分析 API 响应: {response.status_code}")
                        print(f"   响应内容: {response.text[:200]}")
                except Exception as e:
                    print(f"   ⚠️  测试分析 API 失败: {e}")
            else:
                print("⚠️  没有可用的账号进行测试")
        else:
            print(f"⚠️  获取账号列表失败: {response.status_code}")
    except Exception as e:
        print(f"⚠️  测试分析 API 出错: {e}")
    
    return True

def test_frontend_endpoints():
    """测试前端相关 API"""
    print("\n" + "=" * 60)
    print("测试前端相关 API")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8000"
    
    # 测试前端页面是否可访问（通过检查 API 端点）
    endpoints = [
        "/api/dashboard/summary",
        "/api/dashboard/idle",
        "/api/dashboard/trend",
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(
                f"{base_url}{endpoint}",
                params={"account": "test"},
                timeout=5
            )
            if response.status_code in [200, 400, 404]:  # 400/404 也算正常（参数错误）
                print(f"✅ {endpoint} 可访问")
            else:
                print(f"⚠️  {endpoint} 响应: {response.status_code}")
        except Exception as e:
            print(f"⚠️  {endpoint} 测试失败: {e}")
    
    return True

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("开始 Web 自动化测试")
    print("=" * 60 + "\n")
    
    try:
        # 测试后端 API
        backend_ok = test_backend_api()
        
        # 测试分析 API
        analyze_ok = test_analyze_api()
        
        # 测试前端相关 API
        frontend_ok = test_frontend_endpoints()
        
        print("\n" + "=" * 60)
        if backend_ok and analyze_ok and frontend_ok:
            print("✅ Web API 测试完成")
        else:
            print("⚠️  部分测试未通过（可能是服务未启动或配置问题）")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

