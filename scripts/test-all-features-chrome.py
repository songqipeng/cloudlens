#!/usr/bin/env python3
"""
使用Selenium Chrome自动化测试所有前端功能
"""
import time
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

BASE_URL = "http://localhost:3000"

def setup_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # 启用日志
    chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL', 'performance': 'ALL'})
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        return driver
    except Exception as e:
        print(f"❌ Chrome驱动启动失败: {e}")
        print("请确保已安装Chrome和ChromeDriver")
        sys.exit(1)

def test_page(driver, name, url, wait_time=10):
    """测试单个页面"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        driver.get(url)
        time.sleep(3)
        
        # 等待页面加载
        try:
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("✅ 页面加载成功")
        except TimeoutException:
            print("❌ 页面加载超时")
            return False
        
        # 检查控制台错误
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE']
        warnings = [log for log in logs if log['level'] == 'WARNING']
        
        if errors:
            print(f"❌ 发现 {len(errors)} 个严重错误:")
            for error in errors[:5]:
                print(f"   - {error['message']}")
        elif warnings:
            print(f"⚠️  发现 {len(warnings)} 个警告")
        else:
            print("✅ 没有控制台错误")
        
        # 检查页面内容
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "404" in body_text or "Not Found" in body_text:
                print("❌ 页面显示404错误")
                return False
            if "Error" in body_text and "加载" in body_text:
                print("⚠️  页面显示加载错误")
        except:
            pass
        
        # 截图
        screenshot_name = f"/tmp/cloudlens_test_{name.replace(' ', '_').lower()}.png"
        driver.save_screenshot(screenshot_name)
        print(f"📸 截图已保存: {screenshot_name}")
        
        return len(errors) == 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主测试流程"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     CloudLens 完整功能测试（Chrome自动化）                  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print("")
    
    driver = setup_driver()
    print("✅ Chrome浏览器已启动")
    
    # 测试页面列表
    test_pages = [
        ("首页", "/"),
        ("仪表盘", "/dashboard"),
        ("成本分析", "/cost"),
        ("成本趋势", "/cost-trend"),
        ("资源管理", "/resources"),
        ("折扣分析", "/discounts"),
        ("预算管理", "/budgets"),
        ("优化建议", "/optimization"),
        ("报告", "/reports"),
        ("设置", "/settings"),
        ("账号设置", "/settings/accounts"),
    ]
    
    results = {}
    
    for name, path in test_pages:
        url = f"{BASE_URL}{path}"
        success = test_page(driver, name, url)
        results[name] = success
        time.sleep(2)
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    print("\n按Enter键关闭浏览器...")
    input()
    driver.quit()

if __name__ == '__main__':
    main()
