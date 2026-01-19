import { test, expect } from '@playwright/test';

test('检查AI Chatbot是否显示', async ({ page }) => {
  // 访问首页
  await page.goto('http://localhost:3000');
  
  // 等待页面加载
  await page.waitForLoadState('networkidle');
  
  // 等待一下确保React组件渲染完成
  await page.waitForTimeout(2000);
  
  // 检查AI Chatbot按钮是否存在
  const chatbotButton = page.locator('button[aria-label="打开AI助手"]');
  
  // 检查按钮是否可见
  await expect(chatbotButton).toBeVisible({ timeout: 5000 });
  
  // 检查按钮位置（应该在右下角）
  const box = await chatbotButton.boundingBox();
  if (box) {
    console.log(`按钮位置: x=${box.x}, y=${box.y}, width=${box.width}, height=${box.height}`);
    console.log(`窗口大小: ${await page.viewportSize()?.width}x${await page.viewportSize()?.height}`);
  }
  
  // 截图保存
  await page.screenshot({ path: 'test-results/chatbot-button-check.png', fullPage: true });
  
  console.log('✅ AI Chatbot按钮已找到并可见');
});

test('测试AI Chatbot交互', async ({ page }) => {
  // 访问首页
  await page.goto('http://localhost:3000');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);
  
  // 点击AI Chatbot按钮
  const chatbotButton = page.locator('button[aria-label="打开AI助手"]');
  await chatbotButton.click();
  
  // 等待聊天窗口打开
  await page.waitForTimeout(1000);
  
  // 检查聊天窗口是否显示
  const chatWindow = page.locator('text=CloudLens AI 助手');
  await expect(chatWindow).toBeVisible({ timeout: 3000 });
  
  // 截图
  await page.screenshot({ path: 'test-results/chatbot-window-open.png', fullPage: true });
  
  console.log('✅ AI Chatbot窗口已打开');
});
