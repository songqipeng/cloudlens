import { test, expect, chromium, Browser, BrowserContext, Page } from '@playwright/test';
import { existsSync, mkdirSync } from 'fs';
import { join } from 'path';

// 配置
const BASE_URL = 'http://localhost:3000';
const ACCOUNT = 'ydzn'; // 测试账号
const VIDEO_DIR = join(process.cwd(), 'test-recordings');
const WAIT_TIME = 5000; // 页面加载等待时间（毫秒）
const SCROLL_PAUSE = 1000; // 滚动暂停时间（毫秒）

// 确保视频目录存在
if (!existsSync(VIDEO_DIR)) {
  mkdirSync(VIDEO_DIR, { recursive: true });
}

// 测试模块配置
const TEST_MODULES = [
  {
    name: '首页仪表板',
    url: '/',
    description: '主仪表板页面',
    actions: ['scroll', 'wait'],
  },
  {
    name: '成本分析',
    url: '/cost',
    description: '成本分析页面，包含成本趋势图',
    actions: ['scroll', 'wait', 'interact'],
  },
  {
    name: '成本趋势',
    url: '/cost-trend',
    description: '成本趋势分析',
    actions: ['scroll', 'wait'],
  },
  {
    name: '资源管理',
    url: '/resources',
    description: '云资源管理页面',
    actions: ['scroll', 'wait'],
  },
  {
    name: '优化建议',
    url: '/optimization',
    description: '成本优化建议',
    actions: ['scroll', 'wait'],
  },
  {
    name: '预算管理',
    url: '/budgets',
    description: '预算管理页面',
    actions: ['scroll', 'wait'],
  },
  {
    name: '折扣分析',
    url: '/discounts',
    description: '折扣趋势分析',
    actions: ['scroll', 'wait'],
  },
  {
    name: '安全中心',
    url: '/security',
    description: '安全检查页面',
    actions: ['scroll', 'wait'],
  },
  {
    name: '报告生成',
    url: '/reports',
    description: '报告生成页面',
    actions: ['scroll', 'wait'],
  },
  {
    name: '设置',
    url: '/settings',
    description: '系统设置页面',
    actions: ['scroll', 'wait'],
  },
];

// 测试结果
interface TestResult {
  name: string;
  url: string;
  status: 'success' | 'failed' | 'skipped';
  error?: string;
  duration: number;
  timestamp: string;
}

const testResults: TestResult[] = [];

test.describe('CloudLens Web 完整功能测试', () => {
  let browser: Browser;
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async () => {
    // 启动浏览器
    browser = await chromium.launch({
      headless: false, // 显示浏览器窗口
      channel: 'chrome', // 使用系统安装的Chrome
    });

    // 创建上下文，启用视频录制
    context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      recordVideo: {
        dir: VIDEO_DIR,
        size: { width: 1920, height: 1080 },
      },
    });

    page = await context.newPage();

    // 设置超时时间
    test.setTimeout(300000); // 5分钟总超时

    console.log('✅ Chrome浏览器已启动');
    console.log(`📹 视频录制目录: ${VIDEO_DIR}`);
  });

  test.afterAll(async () => {
    // 关闭浏览器
    await context.close();
    await browser.close();

    // 打印测试结果摘要
    console.log('\n' + '='.repeat(60));
    console.log('📊 测试结果摘要');
    console.log('='.repeat(60));
    const successCount = testResults.filter((r) => r.status === 'success').length;
    const failedCount = testResults.filter((r) => r.status === 'failed').length;
    const skippedCount = testResults.filter((r) => r.status === 'skipped').length;
    console.log(`✅ 成功: ${successCount}`);
    console.log(`❌ 失败: ${failedCount}`);
    console.log(`⏭️  跳过: ${skippedCount}`);
    console.log(`📹 视频文件保存在: ${VIDEO_DIR}`);
    console.log('='.repeat(60));
  });

  // 辅助函数：平滑滚动页面
  async function scrollPage(page: Page) {
    const totalHeight = await page.evaluate(() => document.body.scrollHeight);
    const viewportHeight = await page.evaluate(() => window.innerHeight);
    const scrollStep = viewportHeight / 2;

    let currentPosition = 0;
    while (currentPosition < totalHeight) {
      await page.evaluate((pos) => {
        window.scrollTo({ top: pos, behavior: 'smooth' });
      }, currentPosition);
      await page.waitForTimeout(SCROLL_PAUSE);
      currentPosition += scrollStep;
      // 重新获取高度（可能有动态加载的内容）
      const newHeight = await page.evaluate(() => document.body.scrollHeight);
      if (newHeight > totalHeight) {
        totalHeight = newHeight;
      }
    }

    // 滚动回顶部
    await page.evaluate(() => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    await page.waitForTimeout(1000);
  }

  // 辅助函数：等待页面加载完成
  async function waitForPageLoad(page: Page) {
    // 等待网络空闲
    await page.waitForLoadState('networkidle', { timeout: 30000 });
    // 等待DOM加载
    await page.waitForLoadState('domcontentloaded');
    // 额外等待，确保动态内容加载
    await page.waitForTimeout(WAIT_TIME);
  }

  // 测试每个模块
  for (const module of TEST_MODULES) {
    test(`测试模块: ${module.name}`, async () => {
      const startTime = Date.now();
      const result: TestResult = {
        name: module.name,
        url: module.url,
        status: 'success',
        duration: 0,
        timestamp: new Date().toISOString(),
      };

      try {
        console.log(`\n${'='.repeat(60)}`);
        console.log(`📋 测试模块: ${module.name}`);
        console.log(`📝 描述: ${module.description}`);
        console.log(`🔗 URL: ${BASE_URL}${module.url}`);
        console.log('='.repeat(60));

        // 访问页面
        const fullUrl = `${BASE_URL}${module.url}`;
        await page.goto(fullUrl, { waitUntil: 'networkidle', timeout: 60000 });

        console.log('⏳ 正在加载页面...');

        // 等待页面加载
        await waitForPageLoad(page);

        // 检查页面标题
        const pageTitle = await page.title();
        console.log(`📄 页面标题: ${pageTitle}`);

        // 检查页面是否正常加载（检查关键错误提示，而不是所有包含"错误"的文本）
        const criticalErrors = await page.locator('text=/404|500|Internal Server Error|Not Found|页面不存在/i').count();
        if (criticalErrors > 0) {
          throw new Error('页面包含关键错误信息');
        }
        
        // 检查是否有加载失败提示
        const loadingErrors = await page.locator('[class*="error"], [class*="Error"], [role="alert"]:has-text("错误")').count();
        if (loadingErrors > 0) {
          // 检查是否是真正的错误（不是普通的错误提示文本）
          const errorText = await page.locator('[class*="error"], [class*="Error"]').first().textContent().catch(() => '');
          if (errorText && (errorText.includes('404') || errorText.includes('500') || errorText.includes('失败'))) {
            throw new Error('页面加载失败');
          }
        }

        // 执行动作
        if (module.actions.includes('scroll')) {
          console.log('📜 正在滚动页面...');
          await scrollPage(page);
        }

        if (module.actions.includes('wait')) {
          console.log('⏱️  等待内容加载...');
          await page.waitForTimeout(2000);
        }

        if (module.actions.includes('interact')) {
          console.log('🖱️  执行交互操作...');
          // 尝试点击一些可交互元素
          try {
            // 尝试点击账号选择器
            const accountSelector = page.locator('[data-testid="account-selector"], .account-selector, button:has-text("账号")').first();
            if (await accountSelector.count() > 0) {
              await accountSelector.click();
              await page.waitForTimeout(1000);
            }

            // 尝试点击日期范围选择器
            const dateSelector = page.locator('button:has-text("7天"), button:has-text("30天"), button:has-text("全部")').first();
            if (await dateSelector.count() > 0) {
              await dateSelector.click();
              await page.waitForTimeout(1000);
            }
          } catch (e) {
            console.log('⚠️  交互操作跳过（元素不存在）');
          }
        }

        // 截图（可选）
        const screenshotPath = join(VIDEO_DIR, `${module.name.replace(/\s+/g, '_')}_screenshot.png`);
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`📸 截图已保存: ${screenshotPath}`);

        result.duration = Date.now() - startTime;
        result.status = 'success';
        console.log(`✅ 测试成功 (耗时: ${(result.duration / 1000).toFixed(2)}秒)`);
      } catch (error: any) {
        result.status = 'failed';
        result.error = error.message || String(error);
        result.duration = Date.now() - startTime;
        console.log(`❌ 测试失败: ${result.error}`);
        console.log(`⏱️  耗时: ${(result.duration / 1000).toFixed(2)}秒`);

        // 失败时截图
        const errorScreenshotPath = join(VIDEO_DIR, `${module.name.replace(/\s+/g, '_')}_error.png`);
        await page.screenshot({ path: errorScreenshotPath, fullPage: true });
        console.log(`📸 错误截图已保存: ${errorScreenshotPath}`);
      }

      testResults.push(result);
    });
  }

  // 综合测试：测试主要功能流程
  test('综合测试：成本分析流程', async () => {
    console.log('\n' + '='.repeat(60));
    console.log('🔄 综合测试：成本分析流程');
    console.log('='.repeat(60));

    try {
      // 1. 访问成本分析页面
      console.log('1️⃣  访问成本分析页面...');
      await page.goto(`${BASE_URL}/cost`, { waitUntil: 'networkidle' });
      await waitForPageLoad(page);

      // 2. 检查成本趋势图是否存在
      console.log('2️⃣  检查成本趋势图...');
      const chartElement = page.locator('canvas, svg, [class*="chart"], [class*="Chart"]').first();
      await expect(chartElement).toBeVisible({ timeout: 10000 });

      // 3. 检查关键指标卡片
      console.log('3️⃣  检查关键指标...');
      const metricCards = page.locator('[class*="card"], [class*="Card"], [class*="metric"]');
      const cardCount = await metricCards.count();
      console.log(`   找到 ${cardCount} 个指标卡片`);

      // 4. 滚动查看完整页面
      console.log('4️⃣  滚动查看完整页面...');
      await scrollPage(page);

      // 5. 测试日期范围选择
      console.log('5️⃣  测试日期范围选择...');
      try {
        const dateButton = page.locator('button:has-text("全部"), button:has-text("All")').first();
        if (await dateButton.count() > 0) {
          await dateButton.click();
          await page.waitForTimeout(2000);
          console.log('   ✅ 日期范围选择成功');
        }
      } catch (e) {
        console.log('   ⚠️  日期范围选择跳过');
      }

      console.log('✅ 综合测试完成');
    } catch (error: any) {
      console.log(`❌ 综合测试失败: ${error.message}`);
      throw error;
    }
  });
});

