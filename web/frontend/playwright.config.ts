import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright 测试配置
 * 用于 CloudLens Web 应用的自动化测试和视频录制
 */
export default defineConfig({
  testDir: './tests',
  
  // 测试超时设置
  timeout: 300000, // 5分钟
  expect: {
    timeout: 10000, // 10秒
  },
  
  // 完全并行运行测试
  fullyParallel: false, // 顺序执行，确保视频连续
  
  // 失败时不重试
  retries: 0,
  
  // 工作进程数
  workers: 1, // 单进程，确保视频录制连续
  
  // 报告配置
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }],
  ],
  
  // 共享配置
  use: {
    // 基础URL
    baseURL: 'http://localhost:3000',
    
    // 浏览器上下文选项
    viewport: { width: 1920, height: 1080 },
    
    // 视频录制配置
    video: 'on', // 录制所有测试的视频
    screenshot: 'only-on-failure', // 仅在失败时截图
    
    // 追踪配置（可选）
    trace: 'on', // 启用追踪
    
    // 动作超时
    actionTimeout: 30000,
    
    // 导航超时
    navigationTimeout: 60000,
  },

  // 项目配置
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        channel: 'chrome', // 使用系统安装的Chrome
      },
    },
  ],

  // Web服务器配置（如果需要启动本地服务器）
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120000,
  // },
});

