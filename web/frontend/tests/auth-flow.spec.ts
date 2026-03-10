import { test, expect } from '@playwright/test';

const AUTH_USERNAME = process.env.E2E_AUTH_USERNAME;
const AUTH_PASSWORD = process.env.E2E_AUTH_PASSWORD;
const ACCOUNT = process.env.E2E_AUTH_ACCOUNT || 'ydhl';

test.describe('认证流程回归', () => {
  test.skip(!AUTH_USERNAME || !AUTH_PASSWORD, '未提供 E2E_AUTH_USERNAME / E2E_AUTH_PASSWORD，跳过认证回归');

  test.use({ viewport: { width: 1600, height: 1000 } });

  test('未登录门禁、登录、退出登录链路正常', async ({ page, context }) => {
    await page.goto(`/a/${ACCOUNT}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(1000);

    await expect(page).toHaveURL(new RegExp(`/login\\?redirect=%2Fa%2F${ACCOUNT}`));

    await page.getByPlaceholder('ENTER_USERNAME').fill(AUTH_USERNAME!);
    await page.getByPlaceholder('••••••••••••').fill(AUTH_PASSWORD!);
    await page.getByRole('button', { name: 'INITIALIZE ACCESS' }).click();

    await expect.poll(
      async () => (await context.cookies()).some((cookie) => cookie.name === 'cloudlens_auth_token'),
      { timeout: 30000 }
    ).toBeTruthy();

    await expect.poll(
      async () => page.url(),
      { timeout: 30000 }
    ).toContain(`/a/${ACCOUNT}`);

    await page.goto(`/a/${ACCOUNT}/discounts`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3000);

    await expect(page.locator('body')).not.toContainText('[object Object]');
    await expect(page.locator('body')).not.toContainText('Application error');
    await expect(page.locator('body')).not.toContainText('client-side exception');

    const logoutButton = page.getByRole('button', { name: /退出登录|Sign Out/ }).last();
    await logoutButton.evaluate((element) => {
      (element as HTMLButtonElement).click();
    });

    await expect.poll(
      async () => (await context.cookies()).some((cookie) => cookie.name === 'cloudlens_auth_token'),
      { timeout: 30000 }
    ).toBeFalsy();

    await expect.poll(
      async () => page.url(),
      { timeout: 30000 }
    ).toContain('/login');

    await page.goto(`/a/${ACCOUNT}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(1000);
    await expect(page).toHaveURL(new RegExp(`/login\\?redirect=%2Fa%2F${ACCOUNT}`));
  });
});
