#!/usr/bin/env python3
"""
使用浏览器测试后端服务
"""
import subprocess
import sys
import time
import requests

def test_backend_api():
    """测试后端API"""
    print("=== 测试后端API ===")
    print("")
    
    # 1. 测试健康检查端点
    print("1. 测试 /health 端点...")
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            print(f"   ✅ 健康检查成功: {response.json()}")
        else:
            print(f"   ❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 无法连接到后端服务: {e}")
        return False
    
    print("")
    
    # 2. 测试API文档
    print("2. 测试 /docs 端点...")
    try:
        response = requests.get('http://localhost:8000/docs', timeout=5)
        if response.status_code == 200:
            print(f"   ✅ API文档可访问")
        else:
            print(f"   ⚠️  API文档返回: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 无法访问API文档: {e}")
    
    print("")
    return True

def open_browser():
    """在浏览器中打开测试页面"""
    print("=== 在浏览器中打开测试页面 ===")
    print("")
    
    urls = [
        'http://localhost:8000/health',
        'http://localhost:8000/docs',
    ]
    
    for url in urls:
        try:
            print(f"打开: {url}")
            subprocess.Popen(['open', '-a', 'Google Chrome', url])
            time.sleep(1)
        except Exception as e:
            print(f"   ❌ 无法打开 {url}: {e}")
    
    print("")
    print("✅ 已在Chrome中打开测试页面")
    print("")
    print("请检查：")
    print("1. /health 端点是否显示JSON响应")
    print("2. /docs 端点是否显示Swagger UI")
    print("3. 浏览器控制台（F12）是否有错误")

if __name__ == '__main__':
    # 测试API
    if test_backend_api():
        # 打开浏览器
        open_browser()
        print("")
        print("✅ 测试完成！")
    else:
        print("")
        print("❌ 后端服务无法访问，请检查：")
        print("1. Docker容器是否运行: docker compose ps")
        print("2. 容器日志: docker compose logs backend")
        print("3. 端口是否被占用: lsof -i :8000")
        sys.exit(1)
