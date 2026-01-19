#!/usr/bin/env python3
"""
完整的前端功能测试脚本
使用Selenium自动化测试前端各个功能
"""
import time
import subprocess
import sys

def test_with_selenium():
    """使用Selenium测试前端"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, WebDriverException
        
        print("启动Chrome浏览器...")
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        
        print("✅ Chrome浏览器已启动")
        print("")
        
        # 测试首页
        print("1. 测试首页...")
        driver.get("http://localhost:3000")
        time.sleep(5)
        
        # 检查页面标题
        try:
            title = driver.title
            print(f"   页面标题: {title}")
        except:
            print("   ⚠️  无法获取页面标题")
        
        # 检查控制台错误
        print("   检查浏览器控制台错误...")
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE']
        if errors:
            print(f"   ❌ 发现 {len(errors)} 个错误:")
            for error in errors[:5]:
                print(f"      - {error['message']}")
        else:
            print("   ✅ 没有控制台错误")
        
        print("")
        
        # 测试各个功能页面
        pages = [
            ("成本分析", "/cost"),
            ("资源管理", "/resources"),
            ("折扣分析", "/discounts"),
            ("预算管理", "/budgets"),
        ]
        
        print("2. 测试各个功能页面...")
        for name, path in pages:
            try:
                print(f"   测试 {name} ({path})...")
                driver.get(f"http://localhost:3000{path}")
                time.sleep(3)
                
                # 检查页面是否加载
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    print(f"   ✅ {name} 页面加载成功")
                except TimeoutException:
                    print(f"   ❌ {name} 页面加载超时")
                
                # 检查错误
                logs = driver.get_log('browser')
                errors = [log for log in logs if log['level'] == 'SEVERE']
                if errors:
                    print(f"   ⚠️  发现 {len(errors)} 个错误")
                
            except Exception as e:
                print(f"   ❌ {name} 测试失败: {e}")
        
        print("")
        print("✅ 测试完成")
        print("")
        print("浏览器将保持打开状态，请手动检查：")
        print("1. 各个功能是否正常")
        print("2. 数据是否正确加载")
        print("3. 是否有错误提示")
        
        input("按Enter键关闭浏览器...")
        driver.quit()
        
    except ImportError:
        print("❌ Selenium未安装")
        print("安装: pip install selenium")
        print("")
        print("使用简化测试...")
        test_simple()
    except WebDriverException as e:
        print(f"❌ Chrome驱动问题: {e}")
        print("")
        print("使用简化测试...")
        test_simple()

def test_simple():
    """简化测试（不使用Selenium）"""
    print("在Chrome中打开前端页面...")
    subprocess.Popen(['open', '-a', 'Google Chrome', 'http://localhost:3000'])
    time.sleep(2)
    
    pages = [
        ("成本分析", "/cost"),
        ("资源管理", "/resources"),
        ("折扣分析", "/discounts"),
        ("预算管理", "/budgets"),
    ]
    
    for name, path in pages:
        subprocess.Popen(['open', '-a', 'Google Chrome', f'http://localhost:3000{path}'])
        time.sleep(1)
    
    print("✅ 已在Chrome中打开所有测试页面")
    print("")
    print("请手动检查：")
    print("1. 按F12打开开发者工具")
    print("2. 查看Console标签中的错误")
    print("3. 查看Network标签中的API请求")
    print("4. 检查各个功能是否正常")

if __name__ == '__main__':
    test_with_selenium()
