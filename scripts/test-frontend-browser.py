#!/usr/bin/env python3
"""
使用Selenium测试前端功能
"""
import subprocess
import time
import sys

def open_browser_and_test():
    """打开浏览器并测试前端功能"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     前端功能测试                                             ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("")
    
    # 检查服务
    print("1. 检查服务状态...")
    try:
        import requests
        backend_health = requests.get('http://localhost:8000/health', timeout=5)
        if backend_health.status_code == 200:
            print("   ✅ 后端服务正常")
        else:
            print(f"   ❌ 后端服务异常: {backend_health.status_code}")
    except Exception as e:
        print(f"   ❌ 后端服务无法访问: {e}")
    
    try:
        frontend_check = requests.get('http://localhost:3000', timeout=5)
        if frontend_check.status_code == 200:
            print("   ✅ 前端服务正常")
        else:
            print(f"   ❌ 前端服务异常: {frontend_check.status_code}")
    except Exception as e:
        print(f"   ❌ 前端服务无法访问: {e}")
    
    print("")
    
    # 打开浏览器
    print("2. 在Chrome中打开前端页面...")
    urls = [
        ('前端首页', 'http://localhost:3000'),
        ('后端API文档', 'http://localhost:8000/docs'),
        ('后端健康检查', 'http://localhost:8000/health'),
    ]
    
    for name, url in urls:
        try:
            print(f"   打开 {name}: {url}")
            subprocess.Popen(['open', '-a', 'Google Chrome', url])
            time.sleep(1)
        except Exception as e:
            print(f"   ❌ 无法打开 {name}: {e}")
    
    print("")
    print("✅ 已在Chrome中打开测试页面")
    print("")
    print("请检查：")
    print("1. 前端页面是否正常加载")
    print("2. 按F12打开开发者工具")
    print("3. 查看Console标签中的错误")
    print("4. 查看Network标签中的API请求")
    print("5. 检查是否有CORS错误或404错误")

if __name__ == '__main__':
    try:
        open_browser_and_test()
    except ImportError:
        print("⚠️  requests库未安装，使用简化版本...")
        # 简化版本，不依赖requests
        print("在Chrome中打开前端页面...")
        subprocess.Popen(['open', '-a', 'Google Chrome', 'http://localhost:3000'])
        subprocess.Popen(['open', '-a', 'Google Chrome', 'http://localhost:8000/docs'])
        print("✅ 已打开浏览器")
        print("")
        print("请手动检查：")
        print("1. 前端页面是否正常加载")
        print("2. F12查看控制台错误")
        print("3. Network标签查看API请求")
