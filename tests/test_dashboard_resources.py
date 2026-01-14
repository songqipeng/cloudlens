#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard资源统计专项测试
使用Selenium自动化测试，重点验证资源统计数据是否正确显示
"""
import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 配置
BASE_URL = "http://localhost:3000"
ACCOUNT = "ydzn"
# Dashboard页面实际上是 /a/[account]/page.tsx，也就是首页
DASHBOARD_URLS = [
    f"{BASE_URL}/a/{ACCOUNT}?force_refresh=true",
    f"{BASE_URL}/a/{ACCOUNT}",
]
SCREENSHOT_DIR = "/tmp/cloudlens_test_screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def test_dashboard_resources():
    """测试Dashboard页面的资源统计"""
    print("=" * 80)
    print("🔍 Dashboard资源统计专项测试")
    print("=" * 80)
    
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    
    driver = None
    try:
        # 启动浏览器
        print("\n✅ 启动Chrome浏览器...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        
        # 访问Dashboard页面（尝试多个URL）
        dashboard_url = None
        for url in DASHBOARD_URLS:
            print(f"\n📄 尝试访问: {url}")
            driver.get(url)
            time.sleep(2)
            if "404" not in driver.page_source and "not found" not in driver.page_source.lower():
                dashboard_url = url
                print(f"✅ 成功访问: {url}")
                break
            else:
                print(f"❌ 404错误，尝试下一个URL...")
        
        if not dashboard_url:
            print("❌ 所有URL都返回404，使用第一个URL继续测试")
            dashboard_url = DASHBOARD_URLS[0]
            driver.get(dashboard_url)
        
        # 等待页面加载
        print("⏳ 等待页面加载（10秒）...")
        time.sleep(10)  # 给足够时间让数据加载
        
        # 检查页面标题
        page_title = driver.title
        print(f"📄 页面标题: {page_title}")
        
        # 获取页面源码，检查资源统计
        print("\n🔍 检查资源统计数据...")
        page_source = driver.page_source
        
        # 检查资源总数
        resource_checks = {
            "资源总数": "资源总数" in page_source or "Total Resources" in page_source,
            "ECS统计": "ECS:" in page_source or "ecs" in page_source.lower(),
            "RDS统计": "RDS:" in page_source or "rds" in page_source.lower(),
            "Redis统计": "Redis:" in page_source or "redis" in page_source.lower(),
        }
        
        for check_name, found in resource_checks.items():
            status = "✅" if found else "❌"
            print(f"   {status} {check_name}: {'找到' if found else '未找到'}")
        
        # 使用JavaScript提取资源统计数字
        print("\n📊 提取资源统计数字...")
        try:
            resource_data = driver.execute_script("""
                const results = {
                    totalResources: null,
                    ecsCount: null,
                    rdsCount: null,
                    redisCount: null,
                    allText: ''
                };
                
                // 获取页面所有文本
                const bodyText = document.body.innerText || document.body.textContent || '';
                results.allText = bodyText.substring(0, 5000); // 前5000字符
                
                // 查找资源总数（多种可能的格式）
                const totalMatch = bodyText.match(/资源总数[^\\d]*(\\d+)|Total Resources[^\\d]*(\\d+)/i);
                if (totalMatch) {
                    results.totalResources = totalMatch[1] || totalMatch[2];
                }
                
                // 查找ECS数量
                const ecsMatch = bodyText.match(/ECS[^\\d]*(\\d+)|ecs[^\\d]*(\\d+)/i);
                if (ecsMatch) {
                    results.ecsCount = ecsMatch[1] || ecsMatch[2];
                }
                
                // 查找RDS数量
                const rdsMatch = bodyText.match(/RDS[^\\d]*(\\d+)|rds[^\\d]*(\\d+)/i);
                if (rdsMatch) {
                    results.rdsCount = rdsMatch[1] || rdsMatch[2];
                }
                
                // 查找Redis数量
                const redisMatch = bodyText.match(/Redis[^\\d]*(\\d+)|redis[^\\d]*(\\d+)/i);
                if (redisMatch) {
                    results.redisCount = redisMatch[1] || redisMatch[2];
                }
                
                // 尝试查找包含"ECS:"、"RDS:"、"Redis:"的文本
                const breakdownMatch = bodyText.match(/ECS:\\s*(\\d+).*RDS:\\s*(\\d+).*Redis:\\s*(\\d+)/i);
                if (breakdownMatch) {
                    results.ecsCount = breakdownMatch[1];
                    results.rdsCount = breakdownMatch[2];
                    results.redisCount = breakdownMatch[3];
                }
                
                return results;
            """)
            
            print(f"   📊 资源总数: {resource_data.get('totalResources', '未找到')}")
            print(f"   📊 ECS数量: {resource_data.get('ecsCount', '未找到')}")
            print(f"   📊 RDS数量: {resource_data.get('rdsCount', '未找到')}")
            print(f"   📊 Redis数量: {resource_data.get('redisCount', '未找到')}")
            
            # 显示部分页面文本（用于调试）
            all_text = resource_data.get('allText', '')
            if all_text:
                print(f"\n📝 页面文本片段（前500字符）:")
                print(f"   {all_text[:500]}")
            
            # 检查是否有0值
            issues = []
            if resource_data.get('totalResources') == '0':
                issues.append("⚠️  资源总数为0")
            elif resource_data.get('totalResources') is None:
                issues.append("⚠️  未找到资源总数")
            if resource_data.get('ecsCount') == '0':
                issues.append("⚠️  ECS数量为0")
            if resource_data.get('rdsCount') == '0':
                issues.append("⚠️  RDS数量为0")
            if resource_data.get('redisCount') == '0':
                issues.append("⚠️  Redis数量为0")
            
            if issues:
                print("\n❌ 发现问题:")
                for issue in issues:
                    print(f"   {issue}")
            else:
                print("\n✅ 资源统计数据正常")
                
        except Exception as e:
            print(f"   ⚠️  提取资源统计失败: {e}")
        
        # 检查浏览器控制台错误
        print("\n🔍 检查浏览器控制台错误...")
        try:
            logs = driver.get_log('browser')
            errors = [log for log in logs if log['level'] == 'SEVERE']
            if errors:
                print(f"   ❌ 发现 {len(errors)} 个控制台错误:")
                for error in errors[:5]:  # 只显示前5个
                    print(f"      - {error['message'][:200]}")
            else:
                print("   ✅ 无控制台错误")
        except Exception as e:
            print(f"   ⚠️  无法获取控制台日志: {e}")
        
        # 滚动页面，确保所有内容加载
        print("\n📜 滚动页面...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        # 截图
        screenshot_path = os.path.join(SCREENSHOT_DIR, f"dashboard_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        driver.save_screenshot(screenshot_path)
        print(f"\n📸 截图已保存: {screenshot_path}")
        
        # 再次检查资源统计（滚动后）
        print("\n🔍 滚动后再次检查资源统计...")
        time.sleep(3)
        page_source_after = driver.page_source
        
        # 检查API调用
        print("\n🔍 检查网络请求...")
        try:
            # 获取网络日志（需要启用性能日志）
            performance_log = driver.get_log('performance')
            api_calls = [
                log for log in performance_log 
                if 'api' in log.get('message', '').lower() and 'dashboard' in log.get('message', '').lower()
            ]
            if api_calls:
                print(f"   ✅ 发现 {len(api_calls)} 个Dashboard相关API调用")
            else:
                print("   ⚠️  未发现Dashboard API调用")
        except Exception as e:
            print(f"   ⚠️  无法获取网络日志: {e}")
        
        print("\n" + "=" * 80)
        print("✅ 测试完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            print("\n🔒 关闭浏览器...")
            driver.quit()

if __name__ == "__main__":
    test_dashboard_resources()

