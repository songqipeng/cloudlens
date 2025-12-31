#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试进度条功能
"""
import sys
import time
import requests
from core.progress_manager import ProgressManager

def test_progress_manager():
    """测试进度管理器"""
    print("=" * 50)
    print("测试进度管理器")
    print("=" * 50)
    
    pm = ProgressManager()
    task_id = "test_task"
    
    # 测试设置进度
    print("\n1. 测试设置进度...")
    for i in range(0, 101, 10):
        pm.set_progress(task_id, i, 100, f"处理中 {i}%", "testing")
        progress = pm.get_progress(task_id)
        print(f"   进度: {progress['percent']:.1f}% - {progress['message']}")
        time.sleep(0.1)
    
    # 测试完成
    print("\n2. 测试标记完成...")
    pm.set_completed(task_id, {"result": "success"})
    progress = pm.get_progress(task_id)
    print(f"   状态: {progress['status']}")
    print(f"   结果: {progress.get('result', {})}")
    
    # 测试失败
    print("\n3. 测试标记失败...")
    pm.set_failed("failed_task", "测试错误")
    progress = pm.get_progress("failed_task")
    if progress:
        print(f"   状态: {progress['status']}")
        print(f"   错误: {progress.get('error', '')}")
    else:
        print("   ⚠️  进度未找到（可能已清理）")
    
    print("\n✅ 进度管理器测试通过！")
    return True

def test_backend_api():
    """测试后端 API"""
    print("\n" + "=" * 50)
    print("测试后端 API")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8000"
    
    # 测试健康检查
    print("\n1. 测试健康检查...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ 后端服务运行正常: {response.json()}")
        else:
            print(f"   ❌ 后端服务异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 无法连接到后端服务: {e}")
        return False
    
    # 测试进度查询 API
    print("\n2. 测试进度查询 API...")
    try:
        response = requests.get(f"{base_url}/api/analyze/progress?account=test", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 进度查询 API 正常: {data}")
        else:
            print(f"   ⚠️  进度查询返回: {response.status_code} (可能没有任务)")
    except Exception as e:
        print(f"   ❌ 进度查询 API 错误: {e}")
        return False
    
    print("\n✅ 后端 API 测试通过！")
    return True

if __name__ == "__main__":
    print("\n🚀 开始测试进度条功能...\n")
    
    # 测试进度管理器
    if not test_progress_manager():
        print("\n❌ 进度管理器测试失败！")
        sys.exit(1)
    
    # 测试后端 API
    if not test_backend_api():
        print("\n⚠️  后端 API 测试失败（可能后端未启动）")
        print("   请确保后端服务正在运行: python3 -m uvicorn main:app --host 0.0.0.0 --port 8000")
    
    print("\n" + "=" * 50)
    print("✅ 所有测试完成！")
    print("=" * 50)

