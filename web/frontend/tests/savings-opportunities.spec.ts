import { test, expect } from "@playwright/test"

const USER = process.env.E2E_AUTH_USERNAME || "admin"
const PASS = process.env.E2E_AUTH_PASSWORD || "CloudLensAdmin2024!"
const ACCOUNT = process.env.E2E_AUTH_ACCOUNT || "cf"
const API = process.env.E2E_API_BASE || "http://localhost:8000"

test.describe("省钱机会 / 框架合同", () => {
  test.use({ viewport: { width: 1600, height: 1000 } })

  test("API: 合同列表、省钱扫描、HTML 报告", async ({ request }) => {
    const login = await request.post(`${API}/api/auth/login`, {
      data: { username: USER, password: PASS },
    })
    expect(login.ok()).toBeTruthy()

    const contracts = await request.get(`${API}/api/contracts?account=${ACCOUNT}`)
    expect(contracts.ok()).toBeTruthy()
    const cjson = await contracts.json()
    expect(cjson.success).toBeTruthy()
    expect(Array.isArray(cjson.data.contracts)).toBeTruthy()

    const savings = await request.get(
      `${API}/api/optimization/savings-opportunities?account=${ACCOUNT}&force_refresh=true&include_legacy=true`
    )
    expect(savings.ok()).toBeTruthy()
    const sjson = await savings.json()
    expect(sjson.success).toBeTruthy()
    expect(sjson.data.summary).toBeTruthy()
    expect(typeof sjson.data.summary.annual_savings_total).toBe("number")
    expect(Array.isArray(sjson.data.opportunities)).toBeTruthy()

    const report = await request.get(
      `${API}/api/optimization/savings-report?account=${ACCOUNT}`
    )
    expect(report.ok()).toBeTruthy()
    const html = await report.text()
    expect(html).toContain("省钱机会报告")
  })

  test("页面: 省钱机会 KPI 与合同面板", async ({ page, context }) => {
    // 先走登录门禁（与 auth-flow 一致）
    await page.goto(`/a/${ACCOUNT}/optimization`, {
      waitUntil: "domcontentloaded",
      timeout: 60000,
    })
    await page.waitForTimeout(1000)

    if (page.url().includes("/login")) {
      await page.getByPlaceholder("ENTER_USERNAME").fill(USER)
      await page.getByPlaceholder("••••••••••••").fill(PASS)
      await page.getByRole("button", { name: "INITIALIZE ACCESS" }).click()
      await expect
        .poll(
          async () =>
            (await context.cookies()).some((c) => c.name === "cloudlens_auth_token"),
          { timeout: 30000 }
        )
        .toBeTruthy()
      await page.goto(`/a/${ACCOUNT}/optimization`, {
        waitUntil: "domcontentloaded",
        timeout: 60000,
      })
    }

    await expect(page.getByRole("heading", { name: /省钱机会|Savings/ })).toBeVisible({
      timeout: 60000,
    })
    await expect(page.getByRole("button", { name: /机会总览|Overview/ })).toBeVisible()
    await expect(page.getByRole("button", { name: /框架合同|Contracts/ })).toBeVisible()
    // 总览页合同摘要
    await expect(page.getByText(/框架合同/).first()).toBeVisible({ timeout: 60000 })
    // KPI：等扫描结束（允许缓存命中）
    await expect(page.getByText(/年化可省合计|Annual/)).toBeVisible({
      timeout: 120000,
    })
    // 分类区块
    await expect(page.getByText(/框架合规|Framework/).first()).toBeVisible({ timeout: 30000 })
  })
})
