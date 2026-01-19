#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Selenium检查AI Chatbot是否在浏览器中显示
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def check_chatbot():
    """检查AI Chatbot是否显示"""
    print("=" * 60)
    print("检查AI Chatbot是否在浏览器中显示")
    print("=" * 60)
    
    # 配置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--headless")  # 如果想无头模式，取消注释
    
    try:
        # 启动浏览器
        print("正在启动Chrome浏览器...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        
        # 访问首页
        print("访问 http://localhost:3000 ...")
        driver.get("http://localhost:3000")
        
        # 等待页面加载
        print("等待页面加载...")
        time.sleep(5)  # 给React组件足够时间渲染
        
        # 检查AI Chatbot按钮
        print("\n检查AI Chatbot按钮...")
        try:
            # 方法1: 通过aria-label查找
            button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button[aria-label="打开AI助手"]'))
            )
            
            # 检查是否可见
            if button.is_displayed():
                print("✅ AI Chatbot按钮已找到并可见！")
                
                # 获取按钮位置和样式
                location = button.location
                size = button.size
                print(f"   位置: x={location['x']}, y={location['y']}")
                print(f"   大小: width={size['width']}, height={size['height']}")
                
                # 获取窗口大小
                window_size = driver.get_window_size()
                print(f"   窗口大小: {window_size['width']}x{window_size['height']}")
                
                # 检查是否在右下角
                viewport_width = window_size['width']
                viewport_height = window_size['height']
                button_x = location['x']
                button_y = location['y']
                
                # 右下角判断（允许一些误差）
                is_bottom_right = (
                    button_x > viewport_width * 0.7 and  # 在右侧70%区域
                    button_y > viewport_height * 0.7  # 在下侧70%区域
                )
                
                if is_bottom_right:
                    print("   ✅ 按钮位置正确（右下角）")
                else:
                    print(f"   ⚠️  按钮位置可能不在右下角: x={button_x}, y={button_y}")
                
                # 截图
                screenshot_path = "/tmp/chatbot_button_screenshot.png"
                driver.save_screenshot(screenshot_path)
                print(f"   📸 截图已保存: {screenshot_path}")
                
                # 点击按钮测试
                print("\n测试点击按钮...")
                button.click()
                time.sleep(2)
                
                # 检查聊天窗口是否打开
                try:
                    chat_window = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'CloudLens AI 助手')]"))
                    )
                    if chat_window.is_displayed():
                        print("✅ 聊天窗口已打开！")
                    else:
                        print("⚠️  聊天窗口存在但不可见")
                except TimeoutException:
                    print("⚠️  点击后聊天窗口未打开")
                
                # 再次截图
                screenshot_path2 = "/tmp/chatbot_window_screenshot.png"
                driver.save_screenshot(screenshot_path2)
                print(f"   📸 窗口截图已保存: {screenshot_path2}")
                
            else:
                print("❌ AI Chatbot按钮存在但不可见（可能被遮挡）")
                
        except TimeoutException:
            print("❌ AI Chatbot按钮未找到")
            print("\n检查页面源码...")
            
            # 检查页面中是否有相关元素
            page_source = driver.page_source
            if "AIChatbot" in page_source or "ai-chatbot" in page_source:
                print("   ⚠️  页面源码中包含AIChatbot，但按钮未渲染")
            else:
                print("   ❌ 页面源码中未找到AIChatbot相关代码")
            
            # 检查控制台错误
            print("\n检查浏览器控制台日志...")
            logs = driver.get_log('browser')
            if logs:
                print(f"   找到 {len(logs)} 条日志:")
                for log in logs[:10]:
                    if log['level'] in ['SEVERE', 'ERROR']:
                        print(f"   ❌ {log['level']}: {log['message']}")
            else:
                print("   未找到控制台错误")
            
            # 截图
            screenshot_path = "/tmp/chatbot_not_found_screenshot.png"
            driver.save_screenshot(screenshot_path)
            print(f"   📸 截图已保存: {screenshot_path}")
        
        # 等待一下以便观察
        print("\n等待5秒以便观察...")
        time.sleep(5)
        
        driver.quit()
        print("\n✅ 检查完成")
        
    except Exception as e:
        print(f"\n❌ 检查失败: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    check_chatbot()
