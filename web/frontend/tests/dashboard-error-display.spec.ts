/**
 * 仪表盘错误展示回归测试（Chrome）
 * 确保错误时不会出现 [object Object]，且 404 账号未找到时有友好提示
 */
import { test, expect } from '@playwright/test';

test.describe('仪表盘错误展示', () => {
  test('访问 /a/ydhl 时页面能打开，且不出现 [object Object] 或数据库/服务器错误', async ({ page }) => {
    await page.goto('/a/ydhl', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForLoadState('domcontentloaded');

    // 页面应渲染出内容（加载中、错误提示或仪表盘）
    const body = await page.locator('body').textContent();
    expect(body).toBeTruthy();

    // 绝不能出现 [object Object]
    await expect(page.locator('body')).not.toContainText('[object Object]');
    // 绝不能出现数据库缺失表等服务器错误（每次测试相当于打开页面做一次验证）
    await expect(page.locator('body')).not.toContainText('Internal server error');
    await expect(page.locator('body')).not.toContainText("doesn't exist");
  });

  test('若为错误页，应显示可读错误信息或“前往账号管理”；若未登录则可能为登录页', async ({ page }) => {
    await page.goto('/a/ydhl', { waitUntil: 'domcontentloaded', timeout: 25000 });
    await page.waitForLoadState('domcontentloaded');

    const hasErrorTitle = await page.getByText('错误', { exact: true }).isVisible().catch(() => false);
    const hasRefresh = await page.getByRole('button', { name: /刷新/ }).isVisible().catch(() => false);
    const hasAccountLink = await page.getByRole('link', { name: /账号管理|前往/ }).isVisible().catch(() => false);
    const hasDashboard = await page.getByText('仪表盘').first().isVisible().catch(() => false);
    const hasLogin = await page.getByText(/登录|登入|ACCESS|INITIALIZE|USER_ID/).first().isVisible().catch(() => false);
    const hasSelectAccount = await page.getByText(/选择账号|请选择/).isVisible().catch(() => false);
    const hasCloudLens = await page.getByText(/CLOUDLENS|CloudLens/).first().isVisible().catch(() => false);

    // 正常仪表盘 / 错误页（刷新或账号管理）/ 登录门禁 / 选择账号 均视为页面正常打开
    expect(
      hasDashboard || hasErrorTitle || hasRefresh || hasAccountLink || hasLogin || hasSelectAccount || hasCloudLens
    ).toBeTruthy();
  });

  test('访问 /a/ydhl/discounts 折扣页能打开，不出现 Application error 或 [object Object]', async ({ page }) => {
    await page.goto('/a/ydhl/discounts', { waitUntil: 'domcontentloaded', timeout: 25000 });
    await page.waitForLoadState('domcontentloaded');

    const body = await page.locator('body').textContent();
    expect(body).toBeTruthy();

    // 回归重点：不能出现客户端异常页
    await expect(page.locator('body')).not.toContainText('Application error');
    await expect(page.locator('body')).not.toContainText('client-side exception');
    await expect(page.locator('body')).not.toContainText('[object Object]');

    // 页面应有正常内容（CloudLens 或 折扣 等）
    const hasContent =
      (body && (body.includes('CloudLens') || body.includes('折扣') || body.includes('Discount') || body.includes('无') || body.includes('Loading')));
    expect(hasContent).toBeTruthy();
  });
});
