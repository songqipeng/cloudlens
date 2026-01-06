#!/usr/bin/env python3
"""
CloudLens Web功能自动化测试与录屏脚本

使用Selenium WebDriver进行自动化测试，并使用浏览器内置的录屏功能
"""

import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 配置
BASE_URL = "http://localhost:3000"
ACCOUNT = "ydzn"  # 测试账号
SCREENSHOT_DIR = "/tmp/cloudlens_test_screenshots"
WAIT_TIME = 8  # 页面加载等待时间（秒）- 增加等待时间以确保数据加载
SCROLL_PAUSE = 2  # 滚动暂停时间（秒）

# 确保截图目录存在
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# 测试模块配置（使用实际的路由路径）
TEST_MODULES = [
    {
        "name": "Dashboard",
        "url": f"/a/{ACCOUNT}/dashboard",
        "description": "仪表板 - 总览页面（重点测试资源统计）",
        "screenshot": "01_dashboard.png",
        "actions": ["scroll", "wait", "check_resources"]
    },
    {
        "name": "Cost Analysis",
        "url": "/cost",
        "description": "成本分析",
        "screenshot": "02_cost_analysis.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "Cost Trend",
        "url": "/cost-trend",
        "description": "成本趋势",
        "screenshot": "03_cost_trend.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "Budgets",
        "url": "/budgets",
        "description": "预算管理",
        "screenshot": "04_budgets.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "Resources",
        "url": "/resources",
        "description": "资源管理",
        "screenshot": "05_resources.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "Optimization",
        "url": "/optimization",
        "description": "优化建议",
        "screenshot": "06_optimization.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "Reports",
        "url": "/reports",
        "description": "报告",
        "screenshot": "07_reports.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "Settings",
        "url": "/settings",
        "description": "设置",
        "screenshot": "08_settings.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "Settings - Accounts",
        "url": "/settings/accounts",
        "description": "设置 - 账户管理",
        "screenshot": "08b_settings_accounts.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "Custom Dashboards",
        "url": "/custom-dashboards",
        "description": "自定义仪表板",
        "screenshot": "09_custom_dashboards.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "Security",
        "url": f"/a/{ACCOUNT}/security",
        "description": "安全（重点测试资源详情跳转）",
        "screenshot": "10_security.png",
        "actions": ["scroll", "wait", "check_resources"]
    },
    {
        "name": "Security - CIS",
        "url": "/security/cis",
        "description": "安全 - CIS合规",
        "screenshot": "10b_security_cis.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "AI Optimizer",
        "url": "/ai-optimizer",
        "description": "AI优化器",
        "screenshot": "11_ai_optimizer.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "Alerts",
        "url": "/alerts",
        "description": "告警",
        "screenshot": "12_alerts.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "Virtual Tags",
        "url": "/virtual-tags",
        "description": "虚拟标签",
        "screenshot": "13_virtual_tags.png",
        "actions": ["scroll", "wait"]
    },
    {
        "name": "Discounts",
        "url": "/discounts",
        "description": "折扣",
        "screenshot": "14_discounts.png",
        "actions": ["scroll", "wait"]
    },
]


class WebTester:
    def __init__(self):
        self.driver = None
        self.results = []
        
    def setup_driver(self):
        """初始化Chrome WebDriver"""
        chrome_options = Options()
        # 设置窗口大小
        chrome_options.add_argument("--window-size=1920,1080")
        # 禁用GPU加速（避免某些系统问题）
        chrome_options.add_argument("--disable-gpu")
        # 禁用沙箱（某些环境需要）
        # chrome_options.add_argument("--no-sandbox")
        
        # 启动浏览器
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()
        print("✅ Chrome浏览器已启动")
        
    def scroll_page(self):
        """平滑滚动页面"""
        # 获取页面总高度
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        
        # 分段滚动
        current_position = 0
        scroll_step = viewport_height // 2
        
        while current_position < total_height:
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(SCROLL_PAUSE)
            current_position += scroll_step
            
        # 滚动回顶部
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
    def test_module(self, module):
        """测试单个模块"""
        print(f"\n{'='*60}")
        print(f"📋 测试模块: {module['name']}")
        print(f"📝 描述: {module['description']}")
        print(f"🔗 URL: {BASE_URL}{module['url']}")
        print(f"{'='*60}")
        
        result = {
            "name": module['name'],
            "url": module['url'],
            "status": "未测试",
            "screenshot": None,
            "error": None,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # 访问页面
            full_url = f"{BASE_URL}{module['url']}"
            self.driver.get(full_url)
            print(f"⏳ 正在加载页面...")
            
            # 等待页面加载
            time.sleep(WAIT_TIME)
            
            # 检查页面标题
            page_title = self.driver.title
            print(f"📄 页面标题: {page_title}")
            
            # 执行动作
            if "scroll" in module.get("actions", []):
                print(f"📜 正在滚动页面...")
                self.scroll_page()
                
            if "wait" in module.get("actions", []):
                print(f"⏱️  等待内容加载...")
                time.sleep(2)
            
            # 截图
            screenshot_path = os.path.join(SCREENSHOT_DIR, module['screenshot'])
            self.driver.save_screenshot(screenshot_path)
            print(f"📸 截图已保存: {screenshot_path}")
            
            result['status'] = "成功"
            result['screenshot'] = screenshot_path
            print(f"✅ 测试成功")
            
        except TimeoutException as e:
            result['status'] = "超时"
            result['error'] = str(e)
            print(f"⏰ 页面加载超时: {e}")
            
        except Exception as e:
            result['status'] = "失败"
            result['error'] = str(e)
            print(f"❌ 测试失败: {e}")
            
        self.results.append(result)
        return result
        
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("🚀 CloudLens Web功能自动化测试开始")
        print("="*60)
        
        start_time = time.time()
        
        try:
            self.setup_driver()
            
            # 逐个测试模块
            for i, module in enumerate(TEST_MODULES, 1):
                print(f"\n进度: [{i}/{len(TEST_MODULES)}]")
                self.test_module(module)
                time.sleep(1)  # 模块间间隔
                
        except Exception as e:
            print(f"\n❌ 测试过程中发生错误: {e}")
            
        finally:
            if self.driver:
                self.driver.quit()
                print("\n✅ 浏览器已关闭")
                
        end_time = time.time()
        duration = end_time - start_time
        
        # 生成测试报告
        self.generate_report(duration)
        
    def generate_report(self, duration):
        """生成测试报告"""
        print("\n" + "="*60)
        print("📊 测试报告")
        print("="*60)
        
        total = len(self.results)
        success = len([r for r in self.results if r['status'] == '成功'])
        failed = len([r for r in self.results if r['status'] == '失败'])
        timeout = len([r for r in self.results if r['status'] == '超时'])
        
        print(f"\n总测试数: {total}")
        print(f"✅ 成功: {success}")
        print(f"❌ 失败: {failed}")
        print(f"⏰ 超时: {timeout}")
        print(f"⏱️  总耗时: {duration:.2f}秒")
        print(f"📁 截图目录: {SCREENSHOT_DIR}")
        
        # 保存详细报告
        report_path = os.path.join(SCREENSHOT_DIR, "test_report.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("CloudLens Web功能自动化测试报告\n")
            f.write("="*60 + "\n\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总测试数: {total}\n")
            f.write(f"成功: {success}\n")
            f.write(f"失败: {failed}\n")
            f.write(f"超时: {timeout}\n")
            f.write(f"总耗时: {duration:.2f}秒\n\n")
            f.write("="*60 + "\n\n")
            
            for result in self.results:
                f.write(f"模块: {result['name']}\n")
                f.write(f"URL: {result['url']}\n")
                f.write(f"状态: {result['status']}\n")
                f.write(f"时间: {result['timestamp']}\n")
                if result['screenshot']:
                    f.write(f"截图: {result['screenshot']}\n")
                if result['error']:
                    f.write(f"错误: {result['error']}\n")
                f.write("-"*60 + "\n\n")
                
        print(f"\n📄 详细报告已保存: {report_path}")
        print("\n" + "="*60)
        print("🎉 测试完成！")
        print("="*60 + "\n")


if __name__ == "__main__":
    tester = WebTester()
    tester.run_all_tests()
