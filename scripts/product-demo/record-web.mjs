#!/usr/bin/env node
/**
 * 独立 Web 演示录制：使用 Playwright 自带 Chromium + recordVideo，避开系统 Chrome/ffmpeg 兼容问题。
 */
import { createRequire } from "module"
import { mkdirSync, copyFileSync, readdirSync, statSync } from "fs"
import { join, dirname } from "path"
import { fileURLToPath } from "url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, "../..")
const FRONTEND = join(ROOT, "web/frontend")
const require = createRequire(join(FRONTEND, "package.json"))
const { chromium } = require("playwright")
const OUT = join(ROOT, "artifacts/product-demo")
const VIDEO_DIR = join(OUT, "web-raw")
mkdirSync(VIDEO_DIR, { recursive: true })

const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000"
const API = process.env.E2E_API_BASE || "http://localhost:8000"
const USER = process.env.E2E_AUTH_USERNAME || "admin"
const PASS = process.env.E2E_AUTH_PASSWORD || "CloudLensAdmin2024!"
const ACCOUNT = process.env.E2E_AUTH_ACCOUNT || "cf"

const accountPath = (s) => `/a/${encodeURIComponent(ACCOUNT)}${s}`

async function caption(page, title, detail = "", ms = 2600) {
  await page.evaluate(
    ({ title, detail }) => {
      const id = "__cl_demo_caption__"
      let el = document.getElementById(id)
      if (!el) {
        el = document.createElement("div")
        el.id = id
        el.style.cssText =
          "position:fixed;left:24px;bottom:24px;z-index:2147483647;max-width:min(720px,70vw);padding:14px 18px;border-radius:12px;background:rgba(8,12,24,0.88);border:1px solid rgba(99,140,255,0.45);box-shadow:0 12px 40px rgba(0,0,0,0.45);color:#f5f7ff;font:600 16px/1.4 system-ui,sans-serif;pointer-events:none;backdrop-filter:blur(10px)"
        document.body.appendChild(el)
      }
      el.innerHTML =
        `<div style="font-size:18px;margin-bottom:4px">${title}</div>` +
        (detail ? `<div style="font-weight:400;font-size:13px;opacity:.85">${detail}</div>` : "")
    },
    { title, detail }
  )
  await page.waitForTimeout(ms)
}

async function safeClick(locator, timeout = 3500) {
  try {
    if ((await locator.count()) === 0) return false
    const t = locator.first()
    await t.scrollIntoViewIfNeeded().catch(() => {})
    await t.click({ timeout })
    return true
  } catch {
    return false
  }
}

async function scrollDemo(page) {
  await page.evaluate(async () => {
    const step = Math.max(280, Math.floor(window.innerHeight * 0.55))
    const max = Math.max(0, document.body.scrollHeight - window.innerHeight)
    for (let y = 0; y <= max; y += step) {
      window.scrollTo({ top: y, behavior: "smooth" })
      await new Promise((r) => setTimeout(r, 400))
    }
    window.scrollTo({ top: 0, behavior: "smooth" })
  })
  await page.waitForTimeout(700)
}

async function go(page, suffix, expectRe, title, detail) {
  await page.goto(BASE + accountPath(suffix), { waitUntil: "domcontentloaded", timeout: 60000 })
  await page.waitForFunction(() => !location.pathname.includes("/login"), null, { timeout: 30000 })
  await page.waitForFunction(
    (reSrc) => new RegExp(reSrc, "i").test(document.body?.innerText || ""),
    expectRe.source,
    { timeout: 60000 }
  )
  await caption(page, title, detail)
  await page.waitForTimeout(900)
}

async function main() {
  console.log("Launching browser with recordVideo…")
  let browser
  try {
    browser = await chromium.launch({
      headless: true,
      args: ["--disable-dev-shm-usage"],
    })
  } catch (e) {
    console.warn("bundled chromium unavailable, fallback to system chrome:", e.message)
    browser = await chromium.launch({
      channel: "chrome",
      headless: true,
      args: ["--disable-dev-shm-usage"],
    })
  }
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1000 },
    recordVideo: { dir: VIDEO_DIR, size: { width: 1600, height: 1000 } },
    locale: "zh-CN",
  })
  const page = await context.newPage()

  // API 登录注入 cookie
  const loginRes = await page.request.post(`${API}/api/auth/login`, {
    data: { username: USER, password: PASS },
  })
  if (!loginRes.ok()) throw new Error(`login failed ${loginRes.status()}`)
  const setCookie = loginRes.headersArray().filter((h) => h.name.toLowerCase() === "set-cookie")
  const tokenMatch = setCookie.map((h) => h.value).join("\n").match(/cloudlens_auth_token=([^;]+)/)
  if (!tokenMatch) throw new Error("no auth cookie")
  await context.addCookies([
    {
      name: "cloudlens_auth_token",
      value: tokenMatch[1],
      domain: "localhost",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
  ])

  await page.goto(BASE + accountPath(""), { waitUntil: "domcontentloaded", timeout: 60000 })
  await caption(
    page,
    "CloudLens 产品演示 · Web",
    "企业级多云资源治理：统一视图 · 成本分析 · 省钱机会 · 安全合规",
    4000
  )

  // 1 仪表盘
  await go(page, "", /仪表盘|总预估成本|立即扫描/, "① 仪表盘", "成本概览、趋势与闲置资源一览")
  await scrollDemo(page)
  await safeClick(page.getByRole("button", { name: /立即扫描|重新扫描|刷新/ }))
  await page.waitForTimeout(1800)

  // 2 资源
  await go(page, "/resources", /资源管理|资源列表|ECS/, "② 资源管理", "查询 ECS / RDS / Redis 等云资源")
  await safeClick(page.getByRole("button", { name: /ECS|全部|RDS/ }))
  await page.waitForTimeout(1200)
  const search = page.locator('input[type="text"], input[type="search"]').first()
  if (await search.count()) {
    await search.fill("ecs")
    await page.waitForTimeout(1000)
    await search.fill("")
  }
  await safeClick(page.getByRole("button", { name: /筛选|过滤|导出|CSV/ }))
  await page.waitForTimeout(1000)
  await scrollDemo(page)

  // 3 成本
  await go(page, "/cost", /成本分析|本月成本|成本构成/, "③ 成本分析", "本月/上月成本、构成与趋势")
  await scrollDemo(page)
  await go(page, "/cost/attribution", /成本归因|账单数据不足|环比/, "③b 成本归因", "对比账期，拆解成本为何变化")
  await safeClick(page.getByRole("button", { name: /环比|同比/ }))
  await page.waitForTimeout(1500)
  await safeClick(page.getByRole("button", { name: /同比|环比/ }))
  await page.waitForTimeout(1500)
  await scrollDemo(page)
  await go(page, "/cost-trend", /成本趋势|暂无|选择/, "③c 成本趋势", "按日/月查看历史成本曲线")
  await scrollDemo(page)

  // 4 预算
  await go(page, "/budgets", /预算管理|新建预算/, "④ 预算管理", "设定月度/季度预算与告警阈值")
  await safeClick(page.getByRole("button", { name: /新建预算|创建/ }))
  await page.waitForTimeout(1500)
  await page.keyboard.press("Escape").catch(() => {})
  await scrollDemo(page)

  // 5 折扣
  await go(page, "/discounts", /折扣分析|暂无折扣数据|高级折扣/, "⑤ 折扣分析", "季度/产品/区域/计费方式多维折扣")
  for (const tab of ["总览", "时间分析", "产品分析", "区域分析", "计费分析", "高级分析"]) {
    await caption(page, `折扣分析 · ${tab}`, "", 1000)
    await safeClick(page.getByRole("tab", { name: tab }).or(page.getByRole("button", { name: tab })))
    await page.waitForTimeout(1400)
    await scrollDemo(page)
  }

  // 6 虚拟标签
  await go(page, "/virtual-tags", /虚拟标签|新建标签/, "⑥ 虚拟标签", "用规则给资源打虚拟标签")
  await safeClick(page.getByRole("button", { name: /新建|创建/ }))
  await page.waitForTimeout(1200)
  await page.keyboard.press("Escape").catch(() => {})
  await scrollDemo(page)

  // 7 安全
  await go(page, "/security", /安全合规|安全评分/, "⑦ 安全合规", "公网暴露、CIS 基线与风险概览")
  await safeClick(page.getByRole("button", { name: /扫描|刷新|重新检测/ }))
  await page.waitForTimeout(1800)
  await scrollDemo(page)

  // 8 省钱机会
  await go(page, "/optimization", /省钱机会|年化可省|框架合同/, "⑧ 省钱机会", "对照框架合同与利用率，年化可省")
  await page.waitForTimeout(2200)
  const kpis = page.locator("button").filter({ hasText: /年化可省|框架合规|利用率|弱建议/ })
  const n = await kpis.count()
  for (let i = 0; i < Math.min(n, 4); i++) {
    await safeClick(kpis.nth(i))
    await page.waitForTimeout(1200)
  }
  await caption(page, "框架合同", "导入 PDF → 核对规则 → 确认发布后参与扫描", 2200)
  await safeClick(page.getByRole("button", { name: /框架合同/ }))
  await page.waitForTimeout(2000)
  await safeClick(page.getByRole("button", { name: /高级|编辑规则|确认发布|保存/ }))
  await page.waitForTimeout(1400)
  await safeClick(page.getByRole("button", { name: /总览|机会|省钱/ }))
  await page.waitForTimeout(1400)
  await scrollDemo(page)

  // 9 报告
  await go(page, "/reports", /报告生成|选择报告类型/, "⑨ 报告生成", "导出综合 / 成本 / 安全报告")
  await safeClick(page.getByRole("button", { name: /综合|成本|安全|资源/ }))
  await page.waitForTimeout(1000)
  await safeClick(page.getByRole("button", { name: /生成|导出|下载/ }))
  await page.waitForTimeout(1600)
  await scrollDemo(page)

  // 10 设置
  await go(page, "/settings", /设置|闲置检测|通知配置/, "⑩ 设置", "账号、闲置规则、通知与语言")
  for (const t of [/账号|云账号/, /闲置|规则/, /通知/, /语言|通用|系统/]) {
    await safeClick(page.getByRole("button", { name: t }).or(page.getByRole("tab", { name: t })))
    await page.waitForTimeout(1000)
  }
  await scrollDemo(page)

  // 扩展页
  for (const extra of [
    { path: "/alerts", re: /告警|规则|通知/i, title: "扩展 · 告警管理", detail: "告警规则与触发历史" },
    { path: "/cost-allocation", re: /成本分配|分配规则|权重/i, title: "扩展 · 成本分配", detail: "按规则分摊账单" },
    { path: "/ai-optimizer", re: /AI|优化|建议|预测/i, title: "扩展 · AI 优化", detail: "优先优化建议" },
  ]) {
    try {
      await page.goto(BASE + accountPath(extra.path), { waitUntil: "domcontentloaded", timeout: 45000 })
      const body = (await page.locator("body").innerText()) || ""
      if (extra.re.test(body) && !/Application error|404/i.test(body)) {
        await caption(page, extra.title, extra.detail, 2000)
        await scrollDemo(page)
      } else {
        await caption(page, extra.title, "本环境该页暂无数据或路由受限", 1400)
      }
    } catch {
      await caption(page, extra.title, "本环境该页暂无数据或路由受限", 1400)
    }
  }

  await page.goto(BASE + accountPath("/optimization"), { waitUntil: "domcontentloaded" })
  await caption(
    page,
    "Web 演示结束",
    "接下来介绍 CLI：config / query / analyze / bill / savings",
    4000
  )

  await context.close()
  await browser.close()

  // 找到刚录的 webm
  const files = readdirSync(VIDEO_DIR)
    .filter((f) => f.endsWith(".webm"))
    .map((f) => join(VIDEO_DIR, f))
    .sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs)
  if (!files.length) throw new Error("no webm produced")
  const dest = join(OUT, "web-demo.webm")
  copyFileSync(files[0], dest)
  console.log("WEB VIDEO:", dest, "bytes", statSync(dest).size)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
