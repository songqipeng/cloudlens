import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright 测试配置
 * 用于 CloudLens Web 应用的自动化测试和视频录制
 */
export default defineConfig({
  testDir: './tests',
  
  // 测试超时设置（全量业务页遍历 + headed Chrome 需要更长时间）
  timeout: 600000, // 10分钟
  expect: {
    timeout: 15000, // 15秒
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
  
  // 共享配置（BASE_URL 或 PLAYWRIGHT_BASE_URL 可指定远端，如 https://cloudlens.songqipeng.com）
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || process.env.BASE_URL || 'http://localhost:3000',
    
    // 浏览器上下文选项
    viewport: { width: 1920, height: 1080 },
    
    // 视频录制：默认关闭。本机 ffmpeg 可能被 macOS 杀掉，导致 Chrome 都拉不起来。
    // 需要录像时：PW_VIDEO=on npx playwright test
    video: process.env.PW_VIDEO === "on" ? "on" : "off",
    screenshot: "only-on-failure",
    
    // 仅失败时保留 trace，避免全量回归收尾时写大包卡住
    trace: 'retain-on-failure',
    
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

