#!/usr/bin/env python3
"""用 Chrome（Selenium）访问生产环境并记录状态、标题、控制台错误与截图。"""
import sys
import time

def main():
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        print("请先安装: pip install selenium")
        sys.exit(1)

    urls = [
        ("域名 HTTPS", "https://cloudlens.songqipeng.com"),
        ("域名 HTTP", "http://cloudlens.songqipeng.com"),
        ("ALB HTTP", "http://cloudlens-alb-v2-554727073.ap-east-1.elb.amazonaws.com"),
    ]

    opts = Options()
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--ignore-certificate-errors")
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    # 无头模式便于在终端运行
    opts.add_argument("--headless=new")

    driver = None
    try:
        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(30)
    except Exception as e:
        print(f"Chrome 启动失败: {e}")
        print("请确保已安装 Chrome 与 chromedriver（或 PATH 中有）。")
        sys.exit(2)

    results = []
    for name, url in urls:
        print(f"\n--- {name}: {url} ---")
        try:
            driver.get(url)
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)
            title = driver.title or "(无标题)"
            current = driver.current_url
            status = "OK"
            # 控制台错误
            try:
                logs = driver.get_log("browser")
                errs = [e for e in logs if e.get("level") == "SEVERE"]
                if errs:
                    status = f"控制台 {len(errs)} 条 SEVERE"
                    for e in errs[:5]:
                        print(f"  [CONSOLE] {e.get('message', '')[:200]}")
            except Exception:
                pass
            print(f"  状态: {status}, 标题: {title[:60]}")
            print(f"  当前 URL: {current[:80]}")
            results.append((name, url, status, title))
        except Exception as e:
            print(f"  失败: {e}")
            results.append((name, url, str(e), ""))

    # 截图（最后访问的页面）
    try:
        path = "scripts/production_test_screenshot.png"
        driver.save_screenshot(path)
        print(f"\n截图已保存: {path}")
    except Exception as e:
        print(f"\n截图失败: {e}")

    if driver:
        driver.quit()

    print("\n=== 汇总 ===")
    for name, url, status, title in results:
        ok = "✅" if status == "OK" else "❌"
        print(f"  {ok} {name}: {status}")

if __name__ == "__main__":
    main()
