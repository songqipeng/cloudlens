#!/usr/bin/env python3
"""
CloudLens Web功能自动化测试与视频录制脚本

使用Selenium WebDriver进行自动化测试
使用pyautogui + opencv-python录制屏幕视频
"""

import time
import os
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import cv2
import numpy as np
import pyautogui

# 配置
BASE_URL = "http://localhost:3000"
VIDEO_DIR = "/Users/mac/.gemini/antigravity/brain/61182b5f-605b-4be1-993d-e968e2e2c113"
WAIT_TIME = 3  # 页面加载等待时间（秒）
SCROLL_PAUSE = 1.5  # 滚动暂停时间（秒）
FPS = 15  # 视频帧率

# 测试模块配置
TEST_MODULES = [
    {"name": "Dashboard", "url": "/", "description": "仪表板"},
    {"name": "Cost Analysis", "url": "/cost", "description": "成本分析"},
    {"name": "Cost Trend", "url": "/cost-trend", "description": "成本趋势"},
    {"name": "Budgets", "url": "/budgets", "description": "预算管理"},
    {"name": "Resources", "url": "/resources", "description": "资源管理"},
    {"name": "Optimization", "url": "/optimization", "description": "优化建议"},
    {"name": "Reports", "url": "/reports", "description": "报告"},
    {"name": "Settings", "url": "/settings", "description": "设置"},
    {"name": "Custom Dashboards", "url": "/custom-dashboards", "description": "自定义仪表板"},
    {"name": "Security", "url": "/security", "description": "安全"},
    {"name": "AI Optimizer", "url": "/ai-optimizer", "description": "AI优化器"},
    {"name": "Alerts", "url": "/alerts", "description": "告警"},
    {"name": "Virtual Tags", "url": "/virtual-tags", "description": "虚拟标签"},
    {"name": "Discounts", "url": "/discounts", "description": "折扣"},
]


class ScreenRecorder:
    """屏幕录制器"""
    
    def __init__(self, output_path, fps=15):
        self.output_path = output_path
        self.fps = fps
        self.recording = False
        self.thread = None
        self.frames = []
        
    def _record(self):
        """录制线程"""
        screen_size = pyautogui.size()
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(self.output_path, fourcc, self.fps, screen_size)
        
        while self.recording:
            # 截取屏幕
            img = pyautogui.screenshot()
            # 转换为numpy数组
            frame = np.array(img)
            # 转换颜色空间 RGB -> BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            # 写入视频
            out.write(frame)
            # 控制帧率
            time.sleep(1.0 / self.fps)
        
        out.release()
        
    def start(self):
        """开始录制"""
        self.recording = True
        self.thread = threading.Thread(target=self._record)
        self.thread.start()
        print(f"🎥 开始录制: {self.output_path}")
        
    def stop(self):
        """停止录制"""
        self.recording = False
        if self.thread:
            self.thread.join()
        print(f"✅ 录制完成: {self.output_path}")


class WebTester:
    def __init__(self):
        self.driver = None
        self.results = []
        
    def setup_driver(self):
        """初始化Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--window-position=0,0")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()
        print("✅ Chrome浏览器已启动")
        time.sleep(2)  # 等待浏览器完全启动
        
    def scroll_page_smoothly(self):
        """平滑滚动页面"""
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        
        # 滚动到底部
        current_position = 0
        scroll_step = viewport_height // 3
        
        while current_position < total_height:
            self.driver.execute_script(f"window.scrollTo({{top: {current_position}, behavior: 'smooth'}});")
            time.sleep(SCROLL_PAUSE)
            current_position += scroll_step
            # 重新获取高度（可能有动态加载的内容）
            total_height = self.driver.execute_script("return document.body.scrollHeight")
        
        # 滚动回顶部
        time.sleep(1)
        self.driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'});")
        time.sleep(2)
        
    def test_all_modules_single_video(self):
        """测试所有模块并录制为一个完整视频"""
        print("\n" + "="*60)
        print("🚀 CloudLens Web功能完整演示视频录制")
        print("="*60)
        
        start_time = time.time()
        
        try:
            self.setup_driver()
            
            # 开始录制完整视频
            video_path = os.path.join(VIDEO_DIR, "cloudlens_full_demo.mp4")
            recorder = ScreenRecorder(video_path, fps=FPS)
            recorder.start()
            
            # 等待录制启动
            time.sleep(2)
            
            # 逐个测试模块
            for i, module in enumerate(TEST_MODULES, 1):
                print(f"\n{'='*60}")
                print(f"进度: [{i}/{len(TEST_MODULES)}]")
                print(f"📋 {module['name']} - {module['description']}")
                print(f"🔗 {BASE_URL}{module['url']}")
                print(f"{'='*60}")
                
                try:
                    # 访问页面
                    full_url = f"{BASE_URL}{module['url']}"
                    self.driver.get(full_url)
                    time.sleep(WAIT_TIME)
                    
                    # 滚动页面展示内容
                    self.scroll_page_smoothly()
                    
                    # 在页面停留一会儿
                    time.sleep(2)
                    
                    print(f"✅ {module['name']} 录制完成")
                    
                except Exception as e:
                    print(f"❌ {module['name']} 测试失败: {e}")
                    
            # 停止录制
            print(f"\n{'='*60}")
            print("🎬 停止录制...")
            recorder.stop()
            
        except Exception as e:
            print(f"\n❌ 录制过程中发生错误: {e}")
            
        finally:
            if self.driver:
                self.driver.quit()
                print("✅ 浏览器已关闭")
                
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*60}")
        print("📊 录制完成")
        print(f"{'='*60}")
        print(f"⏱️  总耗时: {duration:.2f}秒 ({duration/60:.1f}分钟)")
        print(f"🎥 视频文件: {video_path}")
        print(f"📁 保存目录: {VIDEO_DIR}")
        print(f"\n🎉 完成！")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("CloudLens Web功能完整演示视频录制工具")
    print("="*60)
    print("\n📝 说明:")
    print("  - 将自动访问所有14个功能模块")
    print("  - 录制为一个完整的演示视频")
    print("  - 视频格式: MP4")
    print(f"  - 帧率: {FPS} FPS")
    print(f"  - 保存位置: {VIDEO_DIR}")
    print("\n⚠️  注意:")
    print("  - 请确保浏览器窗口可见（不要最小化）")
    print("  - 录制期间请勿移动鼠标或切换窗口")
    print("  - 预计录制时间: 5-8分钟")
    print("\n按 Ctrl+C 可随时停止录制")
    print("="*60 + "\n")
    
    input("按回车键开始录制...")
    
    tester = WebTester()
    tester.test_all_modules_single_video()
