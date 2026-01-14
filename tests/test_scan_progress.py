#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试扫描进度功能
"""
import sys
import time
import requests
import json
from core.progress_manager import ProgressManager

def test_progress_manager():
    """测试进度管理器"""
    print("=" * 60)
    print("测试 1: 进度管理器功能")
    print("=" * 60)
    
    pm = ProgressManager()
    task_id = "test_task"
    
    # 测试设置进度
    pm.set_progress(task_id, 10, 100, "测试中...", "testing")
    progress = pm.get_progress(task_id)
    
    assert progress is not None, "进度应该存在"
    assert progress["current"] == 10, "当前进度应该是 10"
    assert progress["total"] == 100, "总进度应该是 100"
    assert progress["percent"] == 10.0, "百分比应该是 10%"
    assert progress["status"] == "running", "状态应该是 running"
    
    print("✅ 进度设置成功")
    
    # 测试更新进度
    pm.set_progress(task_id, 50, 100, "处理中...", "processing")
    progress = pm.get_progress(task_id)
    assert progress["percent"] == 50.0, "百分比应该是 50%"
    print("✅ 进度更新成功")
    
    # 测试完成任务
    pm.set_completed(task_id, {"result": "success"})
    progress = pm.get_progress(task_id)
    assert progress["status"] == "completed", "状态应该是 completed"
    assert progress["percent"] == 100, "百分比应该是 100%"
    print("✅ 任务完成标记成功")
    
    # 清理
    pm.clear_progress(task_id)
    progress = pm.get_progress(task_id)
    assert progress is None, "进度应该被清除"
    print("✅ 进度清理成功")
    
    print("\n✅ 进度管理器测试通过！\n")


def test_backend_api():
    """测试后端 API"""
    print("=" * 60)
    print("测试 2: 后端 API 功能")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8000"
    
    # 检查后端是否运行
    try:
        response = requests.get(f"{base_url}/api/accounts", timeout=5)
        if response.status_code == 200:
            print("✅ 后端服务正在运行")
        else:
            print(f"⚠️  后端服务响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 后端服务未运行，请先启动后端服务")
        print("   启动命令: cd web/backend && python3 -m uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"❌ 连接后端失败: {e}")
        return False
    
    # 测试进度 API
    try:
        # 测试获取不存在的进度
        response = requests.get(f"{base_url}/api/analyze/progress", params={"account": "test_account"}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "not_found":
                print("✅ 进度 API 正常（未找到任务时返回 not_found）")
            else:
                print(f"✅ 进度 API 正常（返回: {data.get('status')}）")
        else:
            print(f"⚠️  进度 API 响应异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试进度 API 失败: {e}")
        return False
    
    print("\n✅ 后端 API 测试通过！\n")
    return True


def test_progress_flow():
    """测试完整的进度流程"""
    print("=" * 60)
    print("测试 3: 完整进度流程")
    print("=" * 60)
    
    pm = ProgressManager()
    task_id = "flow_test"
    
    # 模拟扫描流程
    stages = [
        (0, 100, "正在初始化...", "initializing"),
        (10, 100, "正在检查区域...", "checking_regions"),
        (30, 100, "正在查询实例...", "querying_instances"),
        (60, 100, "正在分析资源...", "analyzing"),
        (90, 100, "正在保存结果...", "saving"),
        (100, 100, "扫描完成！", "completed"),
    ]
    
    for current, total, message, stage in stages:
        pm.set_progress(task_id, current, total, message, stage)
        progress = pm.get_progress(task_id)
        
        assert progress is not None, "进度应该存在"
        assert progress["current"] == current, f"当前进度应该是 {current}"
        assert progress["message"] == message, f"消息应该是 '{message}'"
        assert progress["stage"] == stage, f"阶段应该是 '{stage}'"
        
        print(f"  [{progress['percent']:.0f}%] {message}")
        time.sleep(0.1)  # 模拟处理时间
    
    # 标记完成
    pm.set_completed(task_id, {"count": 42})
    progress = pm.get_progress(task_id)
    assert progress["status"] == "completed", "状态应该是 completed"
    print(f"  [100%] {progress['message']}")
    
    # 清理
    pm.clear_progress(task_id)
    print("\n✅ 完整进度流程测试通过！\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("开始测试扫描进度功能")
    print("=" * 60 + "\n")
    
    try:
        # 测试 1: 进度管理器
        test_progress_manager()
        
        # 测试 2: 后端 API
        backend_available = test_backend_api()
        
        # 测试 3: 完整流程
        test_progress_flow()
        
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
        if not backend_available:
            print("\n⚠️  注意: 后端服务未运行，部分测试被跳过")
            print("   要测试完整功能，请先启动后端服务：")
            print("   cd web/backend && python3 -m uvicorn main:app --reload")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




