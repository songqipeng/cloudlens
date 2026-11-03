/**
 * CloudLens 产品使用演示 — Web 全功能走查（录制视频）
 *
 * 运行：
 *   E2E_AUTH_USERNAME=admin E2E_AUTH_PASSWORD='...' E2E_AUTH_ACCOUNT=cf \
 *   PW_VIDEO=on npx playwright test tests/product-usage-demo.spec.ts --project=chromium
 *
 * 产出：test-results/.../*.webm → 再拷到 artifacts/product-demo/
 */
import { test, expect, Page } from "@playwright/test"
import { mkdirSync } from "fs"
import { join } from "path"

const AUTH_USERNAME = process.env.E2E_AUTH_USERNAME || "admin"
const AUTH_PASSWORD = process.env.E2E_AUTH_PASSWORD || "CloudLensAdmin2024!"
const ACCOUNT = process.env.E2E_AUTH_ACCOUNT || "cf"
const API_BASE = process.env.E2E_API_BASE || "http://localhost:8000"
const OUT_DIR = join(process.cwd(), "test-recordings", "product-demo-web")

mkdirSync(OUT_DIR, { recursive: true })

function accountPath(suffix: string): string {
  return `/a/${encodeURIComponent(ACCOUNT)}${suffix}`
}

/** 屏幕左下角章节字幕（录进视频） */
async function caption(page: Page, title: string, detail = "", ms = 2800) {
  await page.evaluate(
    ({ title, detail }) => {
      const id = "__cl_demo_caption__"
      let el = document.getElementById(id)
      if (!el) {
        el = document.createElement("div")
        el.id = id
        el.style.cssText = [
          "position:fixed",
          "left:24px",
          "bottom:24px",
          "z-index:2147483647",
          "max-width:min(720px,70vw)",
          "padding:14px 18px",
          "border-radius:12px",
          "background:rgba(8,12,24,0.88)",
          "border:1px solid rgba(99,140,255,0.45)",
          "box-shadow:0 12px 40px rgba(0,0,0,0.45)",
          "color:#f5f7ff",
          "font:600 16px/1.4 system-ui,-apple-system,sans-serif",
          "pointer-events:none",
          "backdrop-filter:blur(10px)",
        ].join(";")
        document.body.appendChild(el)
      }
      el.innerHTML = `<div style="font-size:18px;margin-bottom:4px">${title}</div>` +
        (detail ? `<div style="font-weight:400;font-size:13px;opacity:.85">${detail}</div>` : "")
    },
    { title, detail }
  )
  await page.waitForTimeout(ms)
}

async function hideCaption(page: Page) {
  await page.evaluate(() => document.getElementById("__cl_demo_caption__")?.remove())
}

async function settle(page: Page, ms = 1500) {
  await page.waitForTimeout(ms)
}

async function safeClick(page: Page, locator: ReturnType<Page["locator"]>, opts?: { timeout?: number }) {
  const n = await locator.count().catch(() => 0)
  if (!n) return false
  const target = locator.first()
  await target.scrollIntoViewIfNeeded().catch(() => undefined)
  await target.click({ timeout: opts?.timeout ?? 4000 }).catch(() => undefined)
  return true
}

async function clickByText(page: Page, text: string | RegExp, role?: "button" | "tab" | "link") {
  const loc = role
    ? page.getByRole(role, { name: text })
    : page.getByText(text).first()
  return safeClick(page, loc)
}

async function scrollDemo(page: Page) {
  await page.evaluate(async () => {
    const step = Math.max(280, Math.floor(window.innerHeight * 0.55))
    const max = Math.max(0, document.body.scrollHeight - window.innerHeight)
    for (let y = 0; y <= max; y += step) {
      window.scrollTo({ top: y, behavior: "smooth" })
      await new Promise((r) => setTimeout(r, 450))
    }
    window.scrollTo({ top: 0, behavior: "smooth" })
  })
  await settle(page, 800)
}

async function loginViaApi(page: Page) {
  const loginRes = await page.request.post(`${API_BASE}/api/auth/login`, {
    data: { username: AUTH_USERNAME, password: AUTH_PASSWORD },
  })
  expect(loginRes.ok(), `登录失败 HTTP ${loginRes.status()}`).toBeTruthy()
  const setCookie = loginRes.headersArray().filter((h) => h.name.toLowerCase() === "set-cookie")
  const tokenMatch = setCookie
    .map((h) => h.value)
    .join("\n")
    .match(/cloudlens_auth_token=([^;]+)/)
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
}

async function go(page: Page, suffix: string, expectText: RegExp, captionTitle: string, captionDetail = "") {
  await page.goto(accountPath(suffix), { waitUntil: "domcontentloaded", timeout: 60000 })
  await expect.poll(async () => page.url(), { timeout: 30000 }).not.toContain("/login")
  await expect(page.locator("body")).toContainText(expectText, { timeout: 60000 })
  await caption(page, captionTitle, captionDetail)
  await settle(page, 1200)
}

test.describe.configure({ mode: "serial" })

test.describe("CloudLens 产品使用演示（Web）", () => {
  test.use({ viewport: { width: 1600, height: 1000 } })
  test.setTimeout(900000) // 15 分钟

  test("完整 Web 功能演示", async ({ page }) => {
    await loginViaApi(page)

    // —— 开场 ——
    await page.goto(accountPath(""), { waitUntil: "domcontentloaded", timeout: 60000 })
    await expect.poll(async () => page.url(), { timeout: 30000 }).not.toContain("/login")
    await caption(
      page,
      "CloudLens 产品演示 · Web",
      "企业级多云资源治理：统一视图 · 成本分析 · 省钱机会 · 安全合规",
      4200
    )

    // —— 1. 仪表盘 ——
    await go(page, "", /仪表盘|总预估成本|立即扫描/, "① 仪表盘", "成本概览、趋势与闲置资源一览")
    await scrollDemo(page)
    await clickByText(page, /立即扫描|重新扫描|刷新/, "button")
    await settle(page, 2000)
    // 尝试打开账号选择
    const accountBtn = page.locator("button").filter({ hasText: new RegExp(ACCOUNT, "i") }).first()
    if (await accountBtn.count()) {
      await caption(page, "切换云账号", "侧栏可在多账号间切换，数据按账号隔离", 2200)
      await safeClick(page, accountBtn)
      await settle(page, 1500)
      await page.keyboard.press("Escape").catch(() => undefined)
    }

    // —— 2. 资源管理 ——
    await go(page, "/resources", /资源管理|资源列表|ECS/, "② 资源管理", "查询 ECS / RDS / Redis 等云资源")
    await clickByText(page, /ECS|全部|RDS/, "button")
    await settle(page, 1500)
    await safeClick(page, page.getByPlaceholder(/搜索|search/i).or(page.locator('input[type="search"]')))
    const search = page.locator('input[type="text"], input[type="search"]').first()
    if (await search.count()) {
      await search.fill("ecs")
      await settle(page, 1200)
      await search.fill("")
    }
    await clickByText(page, /筛选|过滤/, "button")
    await settle(page, 1000)
    await clickByText(page, /导出|CSV|Excel/, "button")
    await settle(page, 1200)
    await scrollDemo(page)
    // 点第一行详情（若有）
    const row = page.locator("table tbody tr, [role='row']").nth(1)
    if (await row.count()) {
      await safeClick(page, row)
      await settle(page, 2000)
      await page.goBack().catch(() => undefined)
      await settle(page, 1000)
    }

    // —— 3. 成本分析 ——
    await go(page, "/cost", /成本分析|本月成本|成本构成/, "③ 成本分析", "本月/上月成本、构成与趋势")
    await scrollDemo(page)
    await clickByText(page, /成本归因|归因/, "link")
    await settle(page, 800)
    await go(
      page,
      "/cost/attribution",
      /成本归因|账单数据不足|环比/,
      "③b 成本归因",
      "对比账期，拆解成本为什么变化"
    )
    await clickByText(page, /环比|同比/, "button")
    await settle(page, 1800)
    await clickByText(page, /同比|环比/, "button")
    await settle(page, 1800)
    await scrollDemo(page)
    await go(page, "/cost-trend", /成本趋势|暂无|选择/, "③c 成本趋势", "按日/月查看历史成本曲线")
    await scrollDemo(page)

    // —— 4. 预算 ——
    await go(page, "/budgets", /预算管理|新建预算/, "④ 预算管理", "设定月度/季度预算与告警阈值")
    await clickByText(page, /新建预算|创建/, "button")
    await settle(page, 1800)
    await page.keyboard.press("Escape").catch(() => undefined)
    await settle(page, 800)
    await scrollDemo(page)

    // —— 5. 折扣分析 ——
    await go(
      page,
      "/discounts",
      /折扣分析|暂无折扣数据|高级折扣/,
      "⑤ 折扣分析",
      "季度/产品/区域/计费方式多维折扣洞察"
    )
    const discountTabs = ["总览", "时间分析", "产品分析", "区域分析", "计费分析", "高级分析"]
    for (const tab of discountTabs) {
      await caption(page, `折扣分析 · ${tab}`, "", 1200)
      const tabBtn = page.getByRole("tab", { name: tab }).or(page.getByRole("button", { name: tab }))
      await safeClick(page, tabBtn)
      await settle(page, 1600)
      await scrollDemo(page)
    }
    await clickByText(page, /刷新|强制刷新/, "button")
    await settle(page, 2000)

    // —— 6. 虚拟标签 ——
    await go(page, "/virtual-tags", /虚拟标签|新建标签/, "⑥ 虚拟标签", "用规则给资源打虚拟标签，便于成本分摊")
    await clickByText(page, /新建|创建/, "button")
    await settle(page, 1500)
    await page.keyboard.press("Escape").catch(() => undefined)
    await scrollDemo(page)

    // —— 7. 安全 ——
    await go(page, "/security", /安全合规|安全评分/, "⑦ 安全合规", "公网暴露、CIS 基线与风险概览")
    await clickByText(page, /扫描|刷新|重新检测/, "button")
    await settle(page, 2000)
    await scrollDemo(page)
    // CIS 子页（若有入口）
    if (await page.getByText(/CIS|基线/).count()) {
      await clickByText(page, /CIS|基线/, "link")
      await settle(page, 2000)
      await page.goto(accountPath("/security"), { waitUntil: "domcontentloaded" }).catch(() => undefined)
    }

    // —— 8. 省钱机会（重点） ——
    await go(
      page,
      "/optimization",
      /省钱机会|年化可省|框架合同/,
      "⑧ 省钱机会",
      "对照框架合同与利用率，年化可省金额"
    )
    await settle(page, 2500)
    // KPI 点击筛选
    const kpiBtns = page.locator("button").filter({ hasText: /年化可省|框架合规|利用率|弱建议/ })
    const kpiCount = await kpiBtns.count()
    for (let i = 0; i < Math.min(kpiCount, 4); i++) {
      await safeClick(page, kpiBtns.nth(i))
      await settle(page, 1400)
    }
    // 展开一条机会
    const expandBtn = page.locator("button").filter({ hasText: /详情|展开|查看/ }).first()
    await safeClick(page, expandBtn)
    await settle(page, 1600)
    // 框架合同 Tab
    await caption(page, "框架合同", "导入 PDF → 核对规则 → 确认发布后参与扫描", 2500)
    await clickByText(page, /框架合同/, "button")
    await settle(page, 2200)
    await clickByText(page, /高级|编辑规则/, "button")
    await settle(page, 1500)
    await clickByText(page, /总览|机会|省钱/, "button")
    await settle(page, 1500)
    await scrollDemo(page)

    // —— 9. 报告 ——
    await go(page, "/reports", /报告生成|选择报告类型/, "⑨ 报告生成", "导出综合 / 成本 / 安全报告")
    await clickByText(page, /综合|成本|安全|资源/, "button")
    await settle(page, 1200)
    await clickByText(page, /生成|导出|下载/, "button")
    await settle(page, 2000)
    await scrollDemo(page)

    // —— 10. 设置 ——
    await go(page, "/settings", /设置|闲置检测|通知配置/, "⑩ 设置", "账号、闲置规则、通知与语言")
    const settingTabs = [/账号|云账号/, /闲置|规则/, /通知/, /语言|通用|系统/]
    for (const t of settingTabs) {
      await clickByText(page, t, "button")
      await settle(page, 1200)
      await clickByText(page, t, "tab")
      await settle(page, 1000)
    }
    await scrollDemo(page)

    // —— 扩展入口：告警 / 成本分配 / AI（可能无侧栏，直接访问） ——
    for (const extra of [
      { path: "/alerts", re: /告警|规则|通知|Alerts/i, title: "扩展 · 告警管理", detail: "告警规则与触发历史" },
      {
        path: "/cost-allocation",
        re: /成本分配|分配规则|权重|allocation/i,
        title: "扩展 · 成本分配",
        detail: "按规则把账单分摊到业务维度",
      },
      {
        path: "/ai-optimizer",
        re: /AI|优化|建议|预测/i,
        title: "扩展 · AI 优化",
        detail: "基于分析给出优先优化建议",
      },
    ] as const) {
      try {
        await page.goto(accountPath(extra.path), { waitUntil: "domcontentloaded", timeout: 45000 })
        const body = (await page.locator("body").innerText()) || ""
        if (extra.re.test(body) && !/404|Not Found|Application error/i.test(body)) {
          await caption(page, extra.title, extra.detail, 2200)
          await scrollDemo(page)
        } else {
          await caption(page, extra.title, "本环境该页暂无数据或路由受限", 1600)
        }
      } catch {
        await caption(page, extra.title, "本环境该页暂无数据或路由受限", 1600)
      }
    }

    // —— AI 聊天助手（悬浮） ——
    await page.goto(accountPath(""), { waitUntil: "domcontentloaded" })
    await caption(page, "AI 助手", "右下角可打开对话，快速问成本与资源问题", 2200)
    const chatBtn = page
      .locator("button")
      .filter({ hasText: /AI|助手|聊天|Chat/ })
      .or(page.locator('[aria-label*="chat" i], [aria-label*="助手"]'))
      .first()
    if (await chatBtn.count()) {
      await safeClick(page, chatBtn)
      await settle(page, 2000)
      await page.keyboard.press("Escape").catch(() => undefined)
    }

    // —— 收尾 ——
    await page.goto(accountPath("/optimization"), { waitUntil: "domcontentloaded" })
    await caption(
      page,
      "Web 演示结束",
      "接下来介绍 CLI 核心命令：config / query / analyze / bill / savings",
      4200
    )
    await hideCaption(page)
    await page.screenshot({ path: join(OUT_DIR, "web-finale.png"), fullPage: true })
  })
})
