#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudLens Web功能全面测试脚本
使用Chrome浏览器自动化测试所有Web功能
"""
import time
import sys
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

BASE_URL = "http://localhost:3000"
TEST_ACCOUNT = "ydzn"  # 测试账号

# 所有需要测试的功能模块
TEST_MODULES = [
    {
        "name": "首页仪表板",
        "url": f"/a/{TEST_ACCOUNT}",
        "description": "主仪表板页面，显示成本概览、资源统计、告警信息等",
        "test_points": [
            "检查页面加载",
            "检查成本卡片显示",
            "检查资源统计",
            "检查告警信息",
            "检查图表渲染",
        ],
        "wait_time": 10,
    },
    {
        "name": "资源管理",
        "url": f"/a/{TEST_ACCOUNT}/resources",
        "description": "云资源管理页面，显示所有云资源列表",
        "test_points": [
            "检查资源列表加载",
            "检查资源筛选功能",
            "检查资源详情",
        ],
        "wait_time": 8,
    },
    {
        "name": "成本分析",
        "url": f"/a/{TEST_ACCOUNT}/cost",
        "description": "成本分析页面，包含成本趋势图",
        "test_points": [
            "检查成本图表",
            "检查成本明细",
            "检查时间范围选择",
        ],
        "wait_time": 8,
    },
    {
        "name": "成本趋势",
        "url": f"/a/{TEST_ACCOUNT}/cost-trend",
        "description": "成本趋势分析页面",
        "test_points": [
            "检查趋势图表",
            "检查趋势数据",
        ],
        "wait_time": 8,
    },
    {
        "name": "预算管理",
        "url": f"/a/{TEST_ACCOUNT}/budgets",
        "description": "预算管理页面",
        "test_points": [
            "检查预算列表",
            "检查预算设置",
        ],
        "wait_time": 8,
    },
    {
        "name": "折扣分析",
        "url": f"/a/{TEST_ACCOUNT}/discounts",
        "description": "折扣趋势分析页面",
        "test_points": [
            "检查折扣数据",
            "检查折扣图表",
        ],
        "wait_time": 8,
    },
    {
        "name": "虚拟标签",
        "url": f"/a/{TEST_ACCOUNT}/virtual-tags",
        "description": "虚拟标签管理页面",
        "test_points": [
            "检查标签列表",
            "检查标签规则",
        ],
        "wait_time": 8,
    },
    {
        "name": "安全中心",
        "url": f"/a/{TEST_ACCOUNT}/security",
        "description": "安全检查页面",
        "test_points": [
            "检查安全检查结果",
            "检查安全建议",
        ],
        "wait_time": 8,
    },
    {
        "name": "优化建议",
        "url": f"/a/{TEST_ACCOUNT}/optimization",
        "description": "成本优化建议页面",
        "test_points": [
            "检查优化建议列表",
            "检查优化详情",
        ],
        "wait_time": 8,
    },
    {
        "name": "报告生成",
        "url": f"/a/{TEST_ACCOUNT}/reports",
        "description": "报告生成页面",
        "test_points": [
            "检查报告列表",
            "检查报告生成功能",
        ],
        "wait_time": 8,
    },
    {
        "name": "设置",
        "url": f"/a/{TEST_ACCOUNT}/settings",
        "description": "系统设置页面",
        "test_points": [
            "检查账号设置",
            "检查AI模型配置",
            "检查通知设置",
        ],
        "wait_time": 8,
    },
    {
        "name": "成本分配",
        "url": f"/a/{TEST_ACCOUNT}/cost-allocation",
        "description": "成本分配页面",
        "test_points": [
            "检查成本分配规则",
            "检查分配结果",
        ],
        "wait_time": 8,
    },
    {
        "name": "AI优化器",
        "url": f"/a/{TEST_ACCOUNT}/ai-optimizer",
        "description": "AI优化器页面",
        "test_points": [
            "检查AI优化建议",
            "检查优化分析",
        ],
        "wait_time": 8,
    },
    {
        "name": "告警管理",
        "url": f"/a/{TEST_ACCOUNT}/alerts",
        "description": "告警管理页面",
        "test_points": [
            "检查告警列表",
            "检查告警规则",
        ],
        "wait_time": 8,
    },
]

def setup_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.set_capability('goog:loggingPrefs', {
        'browser': 'ALL',
        'performance': 'ALL'
    })
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        return driver
    except Exception as e:
        print(f"❌ Chrome驱动启动失败: {e}")
        print("请确保已安装Chrome和ChromeDriver")
        sys.exit(1)

def get_console_errors(driver):
    """获取控制台错误"""
    errors = []
    try:
        logs = driver.get_log('browser')
        for log in logs:
            if log['level'] in ['SEVERE', 'ERROR']:
                errors.append({
                    'level': log['level'],
                    'message': log['message'][:200],
                    'timestamp': log['timestamp']
                })
    except:
        pass
    return errors

def test_page(driver, module):
    """测试单个页面"""
    result = {
        "name": module["name"],
        "url": module["url"],
        "status": "pending",
        "errors": [],
        "warnings": [],
        "test_points": {},
        "load_time": 0,
        "console_errors": [],
    }
    
    print(f"\n{'='*60}")
    print(f"📄 测试: {module['name']}")
    print(f"📍 URL: {module['url']}")
    print(f"📝 描述: {module['description']}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # 访问页面
        full_url = f"{BASE_URL}{module['url']}"
        print(f"🌐 访问: {full_url}")
        driver.get(full_url)
        
        # 等待页面加载
        wait_time = module.get("wait_time", 5)
        print(f"⏳ 等待页面加载 ({wait_time}秒)...")
        time.sleep(wait_time)
        
        # 检查页面标题
        try:
            title = driver.title
            print(f"✅ 页面标题: {title}")
            result["test_points"]["页面标题"] = "✅ 正常"
        except:
            print("⚠️  无法获取页面标题")
            result["test_points"]["页面标题"] = "⚠️  无法获取"
        
        # 检查页面是否加载完成
        try:
            # 等待主要内容加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("✅ 页面基本结构加载完成")
            result["test_points"]["页面加载"] = "✅ 正常"
        except TimeoutException:
            print("❌ 页面加载超时")
            result["status"] = "failed"
            result["errors"].append("页面加载超时")
            result["test_points"]["页面加载"] = "❌ 超时"
            return result
        
        # 检查控制台错误
        console_errors = get_console_errors(driver)
        if console_errors:
            print(f"⚠️  发现 {len(console_errors)} 个控制台错误:")
            for err in console_errors[:3]:  # 只显示前3个
                print(f"   - [{err['level']}] {err['message'][:100]}")
            result["console_errors"] = console_errors
            result["warnings"].append(f"发现 {len(console_errors)} 个控制台错误")
        else:
            print("✅ 没有控制台错误")
            result["test_points"]["控制台错误"] = "✅ 无错误"
        
        # 检查特定测试点
        for test_point in module.get("test_points", []):
            try:
                # 简单的存在性检查
                if "图表" in test_point or "图表" in test_point:
                    # 查找图表元素
                    charts = driver.find_elements(By.CSS_SELECTOR, "canvas, svg, [class*='chart'], [class*='Chart']")
                    if charts:
                        print(f"✅ {test_point}: 找到 {len(charts)} 个图表元素")
                        result["test_points"][test_point] = f"✅ 找到 {len(charts)} 个图表"
                    else:
                        print(f"⚠️  {test_point}: 未找到图表元素")
                        result["test_points"][test_point] = "⚠️  未找到"
                elif "列表" in test_point:
                    # 查找列表元素
                    lists = driver.find_elements(By.CSS_SELECTOR, "[class*='list'], [class*='List'], table, [role='list']")
                    if lists:
                        print(f"✅ {test_point}: 找到列表元素")
                        result["test_points"][test_point] = "✅ 正常"
                    else:
                        print(f"⚠️  {test_point}: 未找到列表元素")
                        result["test_points"][test_point] = "⚠️  未找到"
                else:
                    # 通用检查：查找包含相关文本的元素
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{test_point[:5]}')]")
                    if elements:
                        print(f"✅ {test_point}: 找到相关元素")
                        result["test_points"][test_point] = "✅ 正常"
                    else:
                        print(f"⚠️  {test_point}: 未找到相关元素")
                        result["test_points"][test_point] = "⚠️  未找到"
            except Exception as e:
                print(f"⚠️  {test_point}: 检查失败 - {e}")
                result["test_points"][test_point] = f"⚠️  检查失败: {str(e)[:50]}"
        
        # 滚动页面检查
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0);")
            print("✅ 页面滚动测试通过")
            result["test_points"]["页面滚动"] = "✅ 正常"
        except:
            print("⚠️  页面滚动测试失败")
            result["test_points"]["页面滚动"] = "⚠️  失败"
        
        load_time = time.time() - start_time
        result["load_time"] = round(load_time, 2)
        result["status"] = "success"
        print(f"✅ 测试完成 (耗时: {load_time:.2f}秒)")
        
    except Exception as e:
        load_time = time.time() - start_time
        result["load_time"] = round(load_time, 2)
        result["status"] = "failed"
        result["errors"].append(str(e))
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    return result

def test_ai_chatbot(driver):
    """测试AI Chatbot功能"""
    result = {
        "name": "AI Chatbot",
        "status": "pending",
        "errors": [],
        "warnings": [],
        "test_points": {},
    }
    
    print(f"\n{'='*60}")
    print(f"🤖 测试: AI Chatbot")
    print(f"{'='*60}")
    
    try:
        # 查找AI Chatbot按钮
        print("1. 查找AI Chatbot按钮...")
        try:
            chatbot_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label*='AI'], button[aria-label*='助手']"))
            )
            print("   ✅ 找到AI Chatbot按钮")
            result["test_points"]["按钮存在"] = "✅ 正常"
        except TimeoutException:
            print("   ❌ 未找到AI Chatbot按钮")
            result["status"] = "failed"
            result["errors"].append("未找到AI Chatbot按钮")
            return result
        
        # 点击按钮
        print("2. 点击AI Chatbot按钮...")
        try:
            chatbot_button.click()
            time.sleep(2)
            print("   ✅ 已点击按钮")
            result["test_points"]["按钮点击"] = "✅ 正常"
        except Exception as e:
            print(f"   ❌ 点击按钮失败: {e}")
            result["status"] = "failed"
            result["errors"].append(f"点击按钮失败: {e}")
            return result
        
        # 等待Chatbot窗口出现
        print("3. 等待Chatbot窗口出现...")
        try:
            input_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea, input[type='text'], input[placeholder*='消息']"))
            )
            print("   ✅ Chatbot窗口已打开")
            result["test_points"]["窗口打开"] = "✅ 正常"
        except TimeoutException:
            print("   ❌ Chatbot窗口未出现")
            result["status"] = "failed"
            result["errors"].append("Chatbot窗口未出现")
            return result
        
        # 发送测试消息
        print("4. 发送测试消息...")
        try:
            test_message = "你好"
            input_box.clear()
            input_box.send_keys(test_message)
            print(f"   ✅ 已输入消息: {test_message}")
            
            # 查找发送按钮
            send_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button[aria-label*='发送']")
            send_button.click()
            print("   ✅ 已点击发送按钮")
            result["test_points"]["发送消息"] = "✅ 正常"
            
            # 等待响应
            print("   等待AI响应...")
            time.sleep(15)  # 等待AI响应
            
            # 检查响应
            messages = driver.find_elements(By.CSS_SELECTOR, "[class*='message'], p")
            if len(messages) >= 2:
                print(f"   ✅ 收到响应，找到 {len(messages)} 条消息")
                result["test_points"]["收到响应"] = "✅ 正常"
            else:
                print("   ⚠️  未找到响应消息")
                result["test_points"]["收到响应"] = "⚠️  未找到"
                result["warnings"].append("未找到响应消息")
        except Exception as e:
            print(f"   ❌ 发送消息失败: {e}")
            result["test_points"]["发送消息"] = f"❌ 失败: {str(e)[:50]}"
            result["warnings"].append(f"发送消息失败: {e}")
        
        # 检查控制台错误
        console_errors = get_console_errors(driver)
        if console_errors:
            result["warnings"].append(f"发现 {len(console_errors)} 个控制台错误")
        
        result["status"] = "success" if not result["errors"] else "failed"
        print("✅ AI Chatbot测试完成")
        
    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(str(e))
        print(f"❌ AI Chatbot测试失败: {e}")
    
    return result

def generate_report(results):
    """生成测试报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"/tmp/cloudlens_web_test_report_{timestamp}.json"
    
    # 统计信息
    total = len(results)
    success = len([r for r in results if r["status"] == "success"])
    failed = len([r for r in results if r["status"] == "failed"])
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round(success / total * 100, 2) if total > 0 else 0,
        },
        "results": results,
    }
    
    # 保存JSON报告
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 打印文本报告
    print("\n" + "="*60)
    print("📊 测试报告")
    print("="*60)
    print(f"总测试数: {total}")
    print(f"✅ 成功: {success}")
    print(f"❌ 失败: {failed}")
    print(f"📈 成功率: {report['summary']['success_rate']}%")
    print(f"\n📄 详细报告已保存: {report_file}")
    print("="*60)
    
    # 打印失败项
    if failed > 0:
        print("\n❌ 失败的测试:")
        for r in results:
            if r["status"] == "failed":
                print(f"  - {r['name']}: {', '.join(r['errors'][:2])}")
    
    return report_file

def main():
    """主函数"""
    print("🚀 CloudLens Web功能全面测试")
    print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 测试地址: {BASE_URL}")
    print(f"👤 测试账号: {TEST_ACCOUNT}")
    print()
    
    driver = None
    results = []
    
    try:
        driver = setup_driver()
        print("✅ Chrome浏览器已启动\n")
        
        # 先访问首页，确保登录状态
        print("📌 初始化：访问首页...")
        driver.get(f"{BASE_URL}/a/{TEST_ACCOUNT}")
        time.sleep(5)
        print("✅ 初始化完成\n")
        
        # 测试所有页面
        for module in TEST_MODULES:
            result = test_page(driver, module)
            results.append(result)
            time.sleep(2)  # 页面间等待
        
        # 测试AI Chatbot
        chatbot_result = test_ai_chatbot(driver)
        results.append(chatbot_result)
        
        # 生成报告
        report_file = generate_report(results)
        
        print(f"\n✅ 所有测试完成！")
        print(f"📄 报告文件: {report_file}")
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            print("\n关闭浏览器...")
            driver.quit()
            print("✅ 浏览器已关闭")

if __name__ == '__main__':
    main()
