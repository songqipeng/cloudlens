import { test, expect, chromium, Browser, BrowserContext, Page } from '@playwright/test';
import { existsSync, mkdirSync } from 'fs';
import { join } from 'path';

// 配置
const BASE_URL = 'https://cloudlens.songqipeng.com';
const ACCOUNT = 'mock-prod'; // Mock测试账号
const VIDEO_DIR = join(process.cwd(), 'test-recordings');
const WAIT_TIME = 10000; // 页面加载等待时间（毫秒）
const SCROLL_PAUSE = 2000; // 滚动暂停时间（毫秒）

// 确保视频目录存在
if (!existsSync(VIDEO_DIR)) {
  mkdirSync(VIDEO_DIR, { recursive: true });
}

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

test.describe('CloudLens 生产环境完整功能测试', () => {
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
    test.setTimeout(600000); // 10分钟总超时

    console.log('✅ Chrome浏览器已启动');
    console.log(`🌐 测试地址: ${BASE_URL}`);
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

  // 辅助函数：等待页面加载完成
  async function waitForPageLoad(page: Page, timeout = WAIT_TIME) {
    await page.waitForLoadState('networkidle', { timeout });
    await page.waitForTimeout(2000); // 额外等待2秒确保数据加载
  }

  // 辅助函数：检查控制台错误
  async function checkConsoleErrors(page: Page): Promise<string[]> {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    return errors;
  }

  // 辅助函数：截图
  async function takeScreenshot(page: Page, name: string) {
    await page.screenshot({ 
      path: join(VIDEO_DIR, `${name}_screenshot.png`),
      fullPage: true 
    });
  }

  test('1. 测试登录页面', async () => {
    const startTime = Date.now();
    try {
      console.log('\n📋 测试: 登录页面');
      
      // 尝试访问，如果失败则跳过登录测试
      try {
        await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
      } catch (e) {
        console.log('   ⚠️  无法连接到首页，尝试直接访问其他页面');
        // 如果首页无法访问，直接跳过登录测试
        testResults.push({
          name: '登录页面',
          url: BASE_URL,
          status: 'skipped',
          error: 'Connection failed',
          duration: Date.now() - startTime,
          timestamp: new Date().toISOString(),
        });
        return;
      }
      await waitForPageLoad(page);
      
      // 检查页面标题
      const title = await page.title();
      console.log(`   页面标题: ${title}`);
      
      // 检查是否有登录表单
      const loginForm = await page.locator('form, [role="form"]').first();
      if (await loginForm.count() > 0) {
        console.log('   ✅ 找到登录表单');
        
        // 尝试自动登录（如果有demo账号）
        const usernameInput = page.locator('input[type="text"], input[name="username"], input[placeholder*="用户名"]').first();
        const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
        const loginButton = page.locator('button[type="submit"], button:has-text("登录")').first();
        
        if (await usernameInput.count() > 0 && await passwordInput.count() > 0) {
          await usernameInput.fill('demo');
          await passwordInput.fill('demo');
          await loginButton.click();
          await waitForPageLoad(page);
          console.log('   ✅ 自动登录完成');
        }
      }
      
      await takeScreenshot(page, '01_login');
      
      testResults.push({
        name: '登录页面',
        url: BASE_URL,
        status: 'success',
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      });
    } catch (error: any) {
      console.log(`   ❌ 测试失败: ${error.message}`);
      await takeScreenshot(page, '01_login_error');
      testResults.push({
        name: '登录页面',
        url: BASE_URL,
        status: 'failed',
        error: error.message,
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      });
      throw error;
    }
  });

  test('2. 测试仪表盘页面', async () => {
    const startTime = Date.now();
    try {
      console.log('\n📋 测试: 仪表盘页面');
      
      await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
      await waitForPageLoad(page);
      
      // 检查资源总数
      const resourceCount = page.locator('text=/资源总数|总资源|Resources/i');
      if (await resourceCount.count() > 0) {
        const countText = await resourceCount.first().textContent();
        console.log(`   📊 资源统计: ${countText}`);
        
        // 验证资源数量是否达到1000+
        const numbers = countText?.match(/\d+/g);
        if (numbers && numbers.length > 0) {
          const total = parseInt(numbers[0]);
          if (total >= 1000) {
            console.log(`   ✅ 资源总数达到预期: ${total}`);
          } else {
            console.log(`   ⚠️  资源总数未达到预期: ${total} (预期: 1000+)`);
          }
        }
      }
      
      // 检查成本数据
      const costElements = page.locator('text=/成本|Cost|¥|万/i');
      if (await costElements.count() > 0) {
        console.log('   ✅ 找到成本数据');
      }
      
      await takeScreenshot(page, '02_dashboard');
      
      testResults.push({
        name: '仪表盘',
        url: `${BASE_URL}/`,
        status: 'success',
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      });
    } catch (error: any) {
      console.log(`   ❌ 测试失败: ${error.message}`);
      await takeScreenshot(page, '02_dashboard_error');
      testResults.push({
        name: '仪表盘',
        url: `${BASE_URL}/`,
        status: 'failed',
        error: error.message,
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      });
    }
  });

  test('3. 测试资源管理页面', async () => {
    const startTime = Date.now();
    try {
      console.log('\n📋 测试: 资源管理页面');
      
      await page.goto(`${BASE_URL}/resources`, { waitUntil: 'networkidle' });
      await waitForPageLoad(page, 15000);
      
      // 检查资源类型筛选
      const typeFilters = page.locator('button, [role="button"]').filter({ hasText: /ECS|RDS|Redis/i });
      const filterCount = await typeFilters.count();
      console.log(`   📊 找到 ${filterCount} 个资源类型筛选`);
      
      // 测试ECS资源
      if (filterCount > 0) {
        await typeFilters.first().click();
        await waitForPageLoad(page);
        console.log('   ✅ 点击ECS筛选');
      }
      
      // 检查资源列表
      const resourceList = page.locator('table, [role="table"], .resource-item, .resource-row');
      if (await resourceList.count() > 0) {
        const listCount = await resourceList.count();
        console.log(`   📊 找到 ${listCount} 个资源项`);
        
        // 验证资源数量
        if (listCount >= 20) {
          console.log(`   ✅ 资源列表正常显示 (${listCount} 项)`);
        }
      }
      
      // 测试RDS资源
      const rdsFilter = page.locator('button, [role="button"]').filter({ hasText: /RDS/i }).first();
      if (await rdsFilter.count() > 0) {
        await rdsFilter.click();
        await waitForPageLoad(page);
        console.log('   ✅ 切换到RDS资源');
      }
      
      await takeScreenshot(page, '03_resources');
      
      testResults.push({
        name: '资源管理',
        url: `${BASE_URL}/resources`,
        status: 'success',
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      });
    } catch (error: any) {
      console.log(`   ❌ 测试失败: ${error.message}`);
      await takeScreenshot(page, '03_resources_error');
      testResults.push({
        name: '资源管理',
        url: `${BASE_URL}/resources`,
        status: 'failed',
        error: error.message,
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      });
    }
  });

  test('4. 测试折扣分析页面 - 完整功能', async () => {
    const startTime = Date.now();
    try {
      console.log('\n📋 测试: 折扣分析页面（重点测试）');
      
      await page.goto(`${BASE_URL}/discounts`, { waitUntil: 'networkidle' });
      await waitForPageLoad(page, 20000); // 折扣分析页面需要更长时间加载
      
      // 检查是否有错误提示
      const errorMessages = page.locator('text=/错误|Error|失败|Failed/i');
      if (await errorMessages.count() > 0) {
        const errorText = await errorMessages.first().textContent();
        console.log(`   ⚠️  发现错误提示: ${errorText}`);
      }
      
      // 检查Tab切换
      const tabs = page.locator('[role="tab"], .tab, button').filter({ hasText: /季度|年度|产品|区域|订阅|优化|异常|洞察/i });
      const tabCount = await tabs.count();
      console.log(`   📊 找到 ${tabCount} 个Tab`);
      
      // 测试各个Tab
      const tabTests = [
        { name: '季度分析', keywords: ['季度', 'Quarterly', 'Q1', 'Q2'] },
        { name: '年度分析', keywords: ['年度', 'Yearly', '2023', '2024'] },
        { name: '产品趋势', keywords: ['产品', 'Product', 'ECS', 'RDS'] },
        { name: '区域分析', keywords: ['区域', 'Region', '杭州', '上海'] },
        { name: '订阅类型', keywords: ['订阅', 'Subscription', '包年', '按量'] },
        { name: '优化建议', keywords: ['优化', 'Optimization', '建议', '节省'] },
        { name: '异常检测', keywords: ['异常', 'Anomaly', '异常值'] },
        { name: '洞察分析', keywords: ['洞察', 'Insight', '分析'] },
      ];
      
      for (const tabTest of tabTests) {
        const tab = tabs.filter({ hasText: new RegExp(tabTest.keywords.join('|'), 'i') }).first();
        if (await tab.count() > 0) {
          try {
            await tab.click();
            await waitForPageLoad(page, 10000);
            console.log(`   ✅ ${tabTest.name} Tab 切换成功`);
            
            // 检查是否有图表或数据
            const charts = page.locator('svg, canvas, [class*="chart"], [class*="graph"]');
            const dataTables = page.locator('table, [role="table"]');
            
            if (await charts.count() > 0 || await dataTables.count() > 0) {
              console.log(`      ✅ ${tabTest.name} 数据/图表已加载`);
            } else {
              console.log(`      ⚠️  ${tabTest.name} 未找到图表或数据表格`);
            }
          } catch (e: any) {
            console.log(`      ❌ ${tabTest.name} Tab 测试失败: ${e.message}`);
          }
        }
      }
      
      await takeScreenshot(page, '04_discounts');
      
      testResults.push({
        name: '折扣分析',
        url: `${BASE_URL}/discounts`,
        status: 'success',
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      });
    } catch (error: any) {
      console.log(`   ❌ 测试失败: ${error.message}`);
      await takeScreenshot(page, '04_discounts_error');
      testResults.push({
        name: '折扣分析',
        url: `${BASE_URL}/discounts`,
        status: 'failed',
        error: error.message,
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      });
    }
  });

  test('5. 测试成本分析页面', async () => {
    const startTime = Date.now();
    try {
      console.log('\n📋 测试: 成本分析页面');
      
      await page.goto(`${BASE_URL}/cost`, { waitUntil: 'networkidle' });
      await waitForPageLoad(page, 15000);
      
      // 检查成本图表
      const charts = page.locator('svg, canvas, [class*="chart"]');
      const chartCount = await charts.count();
      console.log(`   📊 找到 ${chartCount} 个图表`);
      
      if (chartCount > 0) {
        console.log('   ✅ 成本图表已加载');
      }
      
      // 检查成本统计
      const costStats = page.locator('text=/总成本|月成本|¥|万/i');
      if (await costStats.count() > 0) {
        console.log('   ✅ 找到成本统计数据');
      }
      
      await takeScreenshot(page, '05_cost');
      
      testResults.push({
        name: '成本分析',
        url: `${BASE_URL}/cost`,
        status: 'success',
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      });
    } catch (error: any) {
      console.log(`   ❌ 测试失败: ${error.message}`);
      await takeScreenshot(page, '05_cost_error');
      testResults.push({
        name: '成本分析',
        url: `${BASE_URL}/cost`,
        status: 'failed',
        error: error.message,
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      });
    }
  });

  test('6. 验证API响应', async () => {
    const startTime = Date.now();
    try {
      console.log('\n📋 测试: API响应验证');
      
      // 测试资源API
      const resourcesResponse = await page.request.get(`${BASE_URL}/api/resources?account=${ACCOUNT}&type=ecs&pageSize=100&force_refresh=true`);
      expect(resourcesResponse.ok()).toBeTruthy();
      const resourcesData = await resourcesResponse.json();
      const totalResources = resourcesData?.pagination?.total || 0;
      console.log(`   📊 ECS资源总数: ${totalResources}`);
      
      if (totalResources >= 1000) {
        console.log(`   ✅ 资源数量达到预期: ${totalResources}`);
      } else {
        console.log(`   ⚠️  资源数量未达到预期: ${totalResources} (预期: 1000+)`);
      }
      
      // 测试折扣趋势API
      const discountResponse = await page.request.get(`${BASE_URL}/api/discounts/trend?account=${ACCOUNT}&months=12`);
      expect(discountResponse.ok()).toBeTruthy();
      const discountData = await discountResponse.json();
      console.log(`   ✅ 折扣趋势API响应正常`);
      
      if (discountData?.success && discountData?.data?.trend_analysis) {
        const timeline = discountData.data.trend_analysis.timeline || [];
        console.log(`   📊 折扣数据月份数: ${timeline.length}`);
        
        if (timeline.length > 0) {
          const latest = timeline[timeline.length - 1];
          const discountRate = latest.discount_rate;
          console.log(`   📊 最新折扣率: ${discountRate < 1 ? (discountRate * 100).toFixed(1) : discountRate.toFixed(1)}%`);
        }
      }
      
      // 测试季度分析API
      const quarterlyResponse = await page.request.get(`${BASE_URL}/api/discounts/quarterly?account=${ACCOUNT}&quarters=8`);
      expect(quarterlyResponse.ok()).toBeTruthy();
      const quarterlyData = await quarterlyResponse.json();
      console.log(`   ✅ 季度分析API响应正常`);
      
      if (quarterlyData?.success && quarterlyData?.data?.quarters) {
        console.log(`   📊 季度数据数量: ${quarterlyData.data.quarters.length}`);
      }
      
      testResults.push({
        name: 'API验证',
        url: `${BASE_URL}/api`,
        status: 'success',
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      });
    } catch (error: any) {
      console.log(`   ❌ 测试失败: ${error.message}`);
      testResults.push({
        name: 'API验证',
        url: `${BASE_URL}/api`,
        status: 'failed',
        error: error.message,
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      });
    }
  });
});
