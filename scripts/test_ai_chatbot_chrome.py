#!/usr/bin/env python3
"""
使用Chrome浏览器测试AI Chatbot功能
捕获Console日志和Network请求，诊断问题
"""
import time
import sys
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

BASE_URL = "http://localhost:3000"

def setup_driver():
    """设置Chrome驱动，启用日志"""
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # 启用浏览器日志
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

def get_console_logs(driver):
    """获取浏览器Console日志"""
    logs = []
    try:
        browser_logs = driver.get_log('browser')
        for log in browser_logs:
            logs.append({
                'level': log['level'],
                'message': log['message'],
                'timestamp': log['timestamp']
            })
    except Exception as e:
        print(f"⚠️  无法获取Console日志: {e}")
    return logs

def test_ai_chatbot(driver):
    """测试AI Chatbot功能"""
    print("=" * 60)
    print("🤖 测试AI Chatbot功能")
    print("=" * 60)
    print()
    
    # 1. 访问首页
    print("1. 访问首页...")
    try:
        driver.get(BASE_URL)
        time.sleep(3)
        print("   ✅ 页面加载完成")
    except Exception as e:
        print(f"   ❌ 页面加载失败: {e}")
        return False
    
    # 2. 查找AI Chatbot按钮
    print("2. 查找AI Chatbot按钮...")
    try:
        # 等待AI Chatbot按钮出现（右下角浮动按钮）
        chatbot_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label='打开AI助手'], button[aria-label='Open AI Assistant']"))
        )
        print("   ✅ 找到AI Chatbot按钮")
        
        # 点击按钮
        chatbot_button.click()
        time.sleep(2)
        print("   ✅ 已点击AI Chatbot按钮")
    except TimeoutException:
        print("   ❌ 未找到AI Chatbot按钮")
        return False
    except Exception as e:
        print(f"   ❌ 点击按钮失败: {e}")
        return False
    
    # 3. 等待Chatbot窗口出现
    print("3. 等待Chatbot窗口出现...")
    try:
        # 查找输入框
        input_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "textarea, input[type='text'], input[placeholder*='消息'], input[placeholder*='message']"))
        )
        print("   ✅ Chatbot窗口已打开")
    except TimeoutException:
        print("   ❌ Chatbot窗口未出现")
        return False
    
    # 4. 检查当前模型选择
    print("4. 检查当前模型选择...")
    try:
        # 查找模型选择器
        model_selectors = driver.find_elements(By.CSS_SELECTOR, "select, button[aria-label*='模型'], button[aria-label*='Model']")
        if model_selectors:
            print(f"   ✅ 找到模型选择器")
            for selector in model_selectors:
                try:
                    print(f"      - {selector.get_attribute('value') or selector.text}")
                except:
                    pass
        else:
            print("   ⚠️  未找到模型选择器")
    except Exception as e:
        print(f"   ⚠️  检查模型选择失败: {e}")
    
    # 5. 发送测试消息
    print("5. 发送测试消息...")
    try:
        # 先注入JavaScript来捕获Console日志
        driver.execute_script("""
            window.__chatbot_logs = [];
            const originalLog = console.log;
            const originalError = console.error;
            const originalWarn = console.warn;
            
            console.log = function(...args) {
                window.__chatbot_logs.push({type: 'log', message: args.join(' '), time: Date.now()});
                originalLog.apply(console, args);
            };
            console.error = function(...args) {
                window.__chatbot_logs.push({type: 'error', message: args.join(' '), time: Date.now()});
                originalError.apply(console, args);
            };
            console.warn = function(...args) {
                window.__chatbot_logs.push({type: 'warn', message: args.join(' '), time: Date.now()});
                originalWarn.apply(console, args);
            };
        """)
        
        # 查找输入框
        input_box = driver.find_element(By.CSS_SELECTOR, "textarea, input[type='text'], input[placeholder*='消息'], input[placeholder*='message']")
        
        # 输入消息
        test_message = "你好"
        input_box.clear()
        input_box.send_keys(test_message)
        print(f"   ✅ 已输入消息: {test_message}")
        time.sleep(1)
        
        # 查找发送按钮
        send_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button[aria-label*='发送'], button[aria-label*='Send']")
        send_button.click()
        print("   ✅ 已点击发送按钮")
        
        # 等待响应 - 检查是否有新消息出现
        print("   等待AI响应...")
        max_wait = 30
        waited = 0
        while waited < max_wait:
            time.sleep(2)
            waited += 2
            # 检查是否有新消息
            try:
                messages = driver.find_elements(By.CSS_SELECTOR, "[class*='message'], [class*='Message'], div[role='log'] > div, [data-role='assistant']")
                if len(messages) >= 2:  # 至少应该有用户消息和AI回复
                    print(f"   ✅ 检测到 {len(messages)} 条消息，响应可能已收到")
                    break
            except:
                pass
            print(f"   等待中... ({waited}/{max_wait}秒)")
        
    except Exception as e:
        print(f"   ❌ 发送消息失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. 检查响应
    print("6. 检查AI响应...")
    try:
        # 等待更长时间，确保消息渲染完成
        time.sleep(5)
        
        # 多种选择器尝试查找消息
        selectors = [
            "[class*='message']",
            "[class*='Message']",
            "div[role='log'] > div",
            "div[class*='flex'][class*='gap']",  # 消息容器
            "div > p",  # 消息文本
            "div[class*='text-']",  # 文本元素
        ]
        
        messages = []
        for selector in selectors:
            try:
                found = driver.find_elements(By.CSS_SELECTOR, selector)
                if found:
                    messages.extend(found)
            except:
                pass
        
        # 去重（通过元素ID）
        unique_messages = []
        seen_ids = set()
        for msg in messages:
            try:
                elem_id = msg.id
                if elem_id and elem_id not in seen_ids:
                    unique_messages.append(msg)
                    seen_ids.add(elem_id)
                elif not elem_id:
                    unique_messages.append(msg)
            except:
                unique_messages.append(msg)
        
        if unique_messages:
            print(f"   ✅ 找到 {len(unique_messages)} 个可能的消息元素")
            # 显示有文本的元素
            text_messages = [msg for msg in unique_messages if msg.text and len(msg.text.strip()) > 0]
            if text_messages:
                print(f"   ✅ 其中 {len(text_messages)} 个包含文本:")
                for i, msg in enumerate(text_messages[-5:], 1):  # 只显示最后5条
                    try:
                        text = msg.text[:150] if msg.text else "无文本"
                        print(f"      消息{i}: {text[:100]}...")
                    except:
                        pass
            else:
                print("   ⚠️  但所有元素都没有文本内容")
        else:
            print("   ⚠️  未找到消息元素")
            # 尝试获取页面源码中的消息
            try:
                page_source = driver.page_source
                if "assistant" in page_source.lower() or "你好" in page_source or "CloudLens AI" in page_source:
                    print("   💡 页面源码中包含消息相关文本，但元素可能还未渲染")
            except:
                pass
    except Exception as e:
        print(f"   ⚠️  检查响应失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 7. 获取Console日志
    print("7. 获取Console日志...")
    
    # 方法1: 从注入的JavaScript获取
    try:
        js_logs = driver.execute_script("return window.__chatbot_logs || [];")
        if js_logs:
            chatbot_js_logs = [log for log in js_logs if any(keyword in log.get('message', '').lower() for keyword in ['chatbot', 'ai', 'chat', 'api', 'error', '失败'])]
            if chatbot_js_logs:
                print(f"   ✅ 从JavaScript捕获到 {len(chatbot_js_logs)} 条相关日志:")
                for log in chatbot_js_logs[-10:]:
                    log_type = log.get('type', 'unknown')
                    message = log.get('message', '')[:200]
                    print(f"      [{log_type}] {message}")
            else:
                print("   ⚠️  JavaScript日志中未找到AI Chatbot相关日志")
        else:
            print("   ⚠️  未捕获到JavaScript日志")
    except Exception as e:
        print(f"   ⚠️  获取JavaScript日志失败: {e}")
    
    # 方法2: 从Selenium日志获取
    console_logs = get_console_logs(driver)
    chatbot_logs = [log for log in console_logs if any(keyword in log['message'].lower() for keyword in ['chatbot', 'ai', 'chat', 'api', 'error'])]
    
    if chatbot_logs:
        print(f"   ✅ 从Selenium日志找到 {len(chatbot_logs)} 条相关日志:")
        for log in chatbot_logs[-10:]:
            level = log['level']
            message = log['message'][:200]
            print(f"      [{level}] {message}")
    else:
        print("   ⚠️  Selenium日志中未找到AI Chatbot相关日志")
    
    # 8. 检查错误
    print("8. 检查错误...")
    errors = [log for log in console_logs if log['level'] == 'SEVERE']
    if errors:
        print(f"   ❌ 发现 {len(errors)} 个严重错误:")
        for error in errors[-5:]:  # 只显示最后5个
            print(f"      - {error['message'][:200]}")
    else:
        print("   ✅ 没有严重错误")
    
    # 9. 检查Network请求（通过性能日志）
    print("9. 检查Network请求...")
    try:
        performance_logs = driver.get_log('performance')
        chatbot_requests = []
        for log in performance_logs:
            try:
                message = json.loads(log['message'])
                method = message.get('message', {}).get('method', '')
                if method == 'Network.responseReceived':
                    params = message.get('message', {}).get('params', {})
                    response = params.get('response', {})
                    url = response.get('url', '')
                    if 'chatbot' in url.lower() or '/v1/chatbot' in url.lower() or '/chat' in url.lower():
                        status = response.get('status', 0)
                        chatbot_requests.append({
                            'url': url,
                            'status': status,
                            'timestamp': log['timestamp']
                        })
            except Exception as e:
                pass
        
        if chatbot_requests:
            print(f"   ✅ 找到 {len(chatbot_requests)} 个Chatbot相关请求:")
            for req in chatbot_requests[-5:]:  # 只显示最后5个
                status_icon = "✅" if 200 <= req['status'] < 300 else "❌"
                print(f"      {status_icon} {req['status']} - {req['url'][:80]}")
        else:
            print("   ⚠️  未找到Chatbot相关请求")
            print("   💡 提示: 可能需要在浏览器中手动打开Network标签查看")
    except Exception as e:
        print(f"   ⚠️  检查Network请求失败: {e}")
    
    # 10. 使用JavaScript检查页面状态
    print("10. 检查页面状态...")
    try:
        # 检查是否有错误消息显示
        error_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='error'], [class*='Error'], [class*='不可用'], [class*='unavailable']")
        if error_elements:
            print(f"   ⚠️  找到 {len(error_elements)} 个可能的错误元素:")
            for elem in error_elements[:3]:
                try:
                    text = elem.text[:100] if elem.text else "无文本"
                    print(f"      - {text}")
                except:
                    pass
        else:
            print("   ✅ 未发现明显的错误元素")
        
        # 检查加载状态
        loading_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='loading'], [class*='Loading'], [aria-busy='true']")
        if loading_elements:
            print(f"   ⚠️  发现 {len(loading_elements)} 个加载中的元素（可能还在等待响应）")
    except Exception as e:
        print(f"   ⚠️  检查页面状态失败: {e}")
    
    print()
    print("=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    print()
    print("💡 提示:")
    print("1. 浏览器窗口将保持打开30秒，您可以手动检查")
    print("2. 按F12打开开发者工具查看详细日志")
    print("3. 在Network标签中查看API请求详情")
    print()
    
    # 保持浏览器打开30秒
    time.sleep(30)
    
    return True

def main():
    """主函数"""
    print("🚀 启动Chrome浏览器测试AI Chatbot...")
    print()
    
    driver = None
    try:
        driver = setup_driver()
        print("✅ Chrome浏览器已启动")
        print()
        
        test_ai_chatbot(driver)
        
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
