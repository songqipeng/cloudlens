import { test, expect, Page } from "@playwright/test"
import { mkdirSync } from "fs"
import { join } from "path"

const AUTH_USERNAME = process.env.E2E_AUTH_USERNAME || "admin"
const AUTH_PASSWORD = process.env.E2E_AUTH_PASSWORD || "CloudLensAdmin2024!"
const ACCOUNT = process.env.E2E_AUTH_ACCOUNT || "cf"
const API_BASE = process.env.E2E_API_BASE || "http://localhost:8000"
const SCREENSHOT_DIR = join(process.cwd(), "test-recordings", "local-regression")

mkdirSync(SCREENSHOT_DIR, { recursive: true })

const PAGES: Array<{ name: string; path: string; expectText: RegExp; settleMs: number }> = [
  { name: "仪表盘", path: "", expectText: /仪表盘|总预估成本|立即扫描/, settleMs: 2500 },
  { name: "资源", path: "/resources", expectText: /资源管理|资源列表|ECS/, settleMs: 2000 },
  { name: "成本分析", path: "/cost", expectText: /成本分析|本月成本|成本构成/, settleMs: 2500 },
  { name: "成本归因", path: "/cost/attribution", expectText: /成本归因|账单数据不足|环比/, settleMs: 2000 },
  { name: "成本趋势", path: "/cost-trend", expectText: /成本趋势|暂无|选择/, settleMs: 1500 },
  { name: "预算管理", path: "/budgets", expectText: /预算管理|新建预算/, settleMs: 1500 },
  { name: "折扣分析", path: "/discounts", expectText: /折扣分析|暂无折扣数据|高级折扣/, settleMs: 4000 },
  { name: "虚拟标签", path: "/virtual-tags", expectText: /虚拟标签|新建标签/, settleMs: 1500 },
  { name: "安全", path: "/security", expectText: /安全合规|安全评分/, settleMs: 2500 },
  { name: "省钱机会", path: "/optimization", expectText: /省钱机会|年化可省|框架合同/, settleMs: 3000 },
  { name: "报告", path: "/reports", expectText: /报告生成|选择报告类型/, settleMs: 1500 },
  { name: "设置", path: "/settings", expectText: /设置|闲置检测|通知配置/, settleMs: 1500 },
]

function accountPath(suffix: string): string {
  return `/a/${encodeURIComponent(ACCOUNT)}${suffix}`
}

async function assertNoCrash(page: Page, name: string) {
  const body = (await page.locator("body").innerText()) || ""
  expect(body, `${name} 出现 [object Object]`).not.toContain("[object Object]")
  expect(body, `${name} 出现 Application error`).not.toContain("Application error")
  expect(body, `${name} 出现 client-side exception`).not.toContain("client-side exception")
  expect(body, `${name} 出现 Internal Server Error`).not.toMatch(/Internal Server Error/i)
}

test.describe.configure({ mode: "serial" })

test.describe("本地 Chrome 全量回归", () => {
  test.use({ viewport: { width: 1600, height: 1000 } })
  // headed 模式 + 折扣页多次请求较慢，给足 10 分钟
  test.setTimeout(600000)

  test("登录后遍历全部业务页，页面可打开且无客户端崩溃", async ({ page }) => {
    // API 登录注入 cookie，避免 UI 输入框偶发未写入用户名
    const loginRes = await page.request.post(`${API_BASE}/api/auth/login`, {
      data: { username: AUTH_USERNAME, password: AUTH_PASSWORD },
    })
    expect(loginRes.ok(), `登录失败 HTTP ${loginRes.status()}`).toBeTruthy()
    const setCookie = loginRes.headersArray().filter((h) => h.name.toLowerCase() === "set-cookie")
    const tokenMatch = setCookie.map((h) => h.value).join("\n").match(/cloudlens_auth_token=([^;]+)/)
    expect(tokenMatch, "登录响应未返回 cloudlens_auth_token").toBeTruthy()
    await page.context().addCookies([
      {
        name: "cloudlens_auth_token",
        value: tokenMatch![1],
        domain: "localhost",
        path: "/",
        httpOnly: true,
        sameSite: "Lax",
      },
    ])
    await page.goto(accountPath(""), { waitUntil: "domcontentloaded", timeout: 45000 })
    await expect.poll(async () => page.url(), { timeout: 30000 }).not.toContain("/login")

    for (const item of PAGES) {
      const url = accountPath(item.path)
      await test.step(item.name, async () => {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 })
        await expect(page.locator("body"), `${item.name} 未渲染预期内容`).toContainText(item.expectText, {
          timeout: 45000,
        })
        await page.waitForTimeout(item.settleMs)
        await assertNoCrash(page, item.name)
        await page.screenshot({
          path: join(SCREENSHOT_DIR, `${item.name}.png`),
          fullPage: true,
        })
      })
    }

    await page.goto(accountPath("/discounts"), { waitUntil: "domcontentloaded", timeout: 45000 })
    await expect(page.locator("body")).toContainText(/折扣分析|暂无折扣数据|高级折扣/, { timeout: 45000 })
    await page.waitForTimeout(2000)
    const tabNames = ["总览", "时间分析", "产品分析", "区域分析", "计费分析", "高级分析"]
    for (const tab of tabNames) {
      await test.step(`折扣分析-${tab}`, async () => {
        const tabBtn = page.getByRole("tab", { name: tab }).or(page.getByRole("button", { name: tab }))
        const count = await tabBtn.count().catch(() => 0)
        if (!count) return
        await tabBtn.first().click({ timeout: 3000 }).catch(() => undefined)
        await page.waitForTimeout(1200)
        await assertNoCrash(page, `折扣分析-${tab}`)
        await page.screenshot({
          path: join(SCREENSHOT_DIR, `折扣分析-${tab}.png`),
          fullPage: true,
        })
      })
    }
  })
})
