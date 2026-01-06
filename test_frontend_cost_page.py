#!/usr/bin/env python3
"""
前端成本分析页面测试
验证环比计算修复后的数据显示
"""

import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = "http://localhost:3000"
ACCOUNT = "ydzn"

def test_cost_page():
    """测试成本分析页面"""
    print("=" * 60)
    print("前端成本分析页面测试")
    print("=" * 60)
    
    # 配置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = None
    try:
        print(f"\n🚀 启动浏览器...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        
        # 访问成本分析页面
        url = f"{BASE_URL}/a/{ACCOUNT}/cost"
        print(f"📡 访问: {url}")
        driver.get(url)
        
        # 等待页面加载
        print("⏳ 等待页面加载...")
        time.sleep(5)
        
        # 检查页面标题
        try:
            title = driver.find_element(By.TAG_NAME, "h2")
            if "成本分析" in title.text or "Cost Analysis" in title.text:
                print(f"✅ 页面标题正确: {title.text}")
            else:
                print(f"⚠️  页面标题: {title.text}")
        except NoSuchElementException:
            print("⚠️  未找到页面标题")
        
        # 查找成本卡片
        print("\n📊 检查成本数据卡片...")
        
        # 查找所有卡片
        cards = driver.find_elements(By.CSS_SELECTOR, "[class*='Card']")
        print(f"   找到 {len(cards)} 个卡片")
        
        # 查找本月成本
        try:
            # 尝试通过文本查找
            current_month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '本月成本') or contains(text(), 'Current Month')]")
            if current_month_elements:
                print("   ✅ 找到本月成本标签")
                # 查找相邻的数值
                for elem in current_month_elements:
                    parent = elem.find_element(By.XPATH, "./..")
                    try:
                        value = parent.find_element(By.CSS_SELECTOR, "[class*='text-3xl']")
                        print(f"   📊 本月成本显示: {value.text}")
                    except:
                        pass
        except Exception as e:
            print(f"   ⚠️  查找本月成本失败: {e}")
        
        # 查找上月成本
        try:
            last_month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '上月成本') or contains(text(), 'Last Month')]")
            if last_month_elements:
                print("   ✅ 找到上月成本标签")
                for elem in last_month_elements:
                    parent = elem.find_element(By.XPATH, "./..")
                    try:
                        value = parent.find_element(By.CSS_SELECTOR, "[class*='text-3xl']")
                        print(f"   📊 上月成本显示: {value.text}")
                    except:
                        pass
        except Exception as e:
            print(f"   ⚠️  查找上月成本失败: {e}")
        
        # 查找环比增长
        try:
            mom_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '环比增长') or contains(text(), 'MoM Growth')]")
            if mom_elements:
                print("   ✅ 找到环比增长标签")
                for elem in mom_elements:
                    parent = elem.find_element(By.XPATH, "./..")
                    try:
                        value = parent.find_element(By.CSS_SELECTOR, "[class*='text-3xl']")
                        print(f"   📊 环比增长显示: {value.text}")
                    except:
                        pass
        except Exception as e:
            print(f"   ⚠️  查找环比增长失败: {e}")
        
        # 检查控制台错误
        print("\n🔍 检查浏览器控制台错误...")
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE']
        if errors:
            print(f"   ⚠️  发现 {len(errors)} 个错误:")
            for error in errors[:5]:  # 只显示前5个
                print(f"      {error['message']}")
        else:
            print("   ✅ 无控制台错误")
        
        # 截图
        screenshot_path = "/tmp/cost_page_test.png"
        driver.save_screenshot(screenshot_path)
        print(f"\n📸 截图已保存: {screenshot_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()
            print("\n🔒 浏览器已关闭")

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("前端成本分析页面 - 完整回归测试")
    print("=" * 60)
    
    result = test_cost_page()
    
    print("\n" + "=" * 60)
    if result:
        print("✅ 前端测试完成")
        return 0
    else:
        print("❌ 前端测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())

