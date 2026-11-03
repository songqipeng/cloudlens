#!/usr/bin/env node
/**
 * Web 演示：截图序列（不依赖 Playwright 内置 ffmpeg）→ 之后用系统 ffmpeg 合成视频
 */
import { createRequire } from "module"
import { mkdirSync, writeFileSync, readdirSync } from "fs"
import { join, dirname } from "path"
import { fileURLToPath } from "url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, "../..")
const require = createRequire(join(ROOT, "web/frontend/package.json"))
const { chromium } = require("playwright")

const OUT = join(ROOT, "artifacts/product-demo/web-frames")
mkdirSync(OUT, { recursive: true })

const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000"
const API = process.env.E2E_API_BASE || "http://localhost:8000"
const USER = process.env.E2E_AUTH_USERNAME || "admin"
const PASS = process.env.E2E_AUTH_PASSWORD || "CloudLensAdmin2024!"
const ACCOUNT = process.env.E2E_AUTH_ACCOUNT || "cf"
const accountPath = (s) => `/a/${encodeURIComponent(ACCOUNT)}${s}`

let frame = 0
const manifest = []

async function caption(page, title, detail = "", ms = 2400) {
  await page.evaluate(
    ({ title, detail }) => {
      const id = "__cl_demo_caption__"
      let el = document.getElementById(id)
      if (!el) {
        el = document.createElement("div")
        el.id = id
        el.style.cssText =
          "position:fixed;left:24px;bottom:24px;z-index:2147483647;max-width:min(720px,70vw);padding:14px 18px;border-radius:12px;background:rgba(8,12,24,0.88);border:1px solid rgba(99,140,255,0.45);color:#f5f7ff;font:600 16px/1.4 system-ui,sans-serif;pointer-events:none"
        document.body.appendChild(el)
      }
      el.innerHTML =
        `<div style="font-size:18px;margin-bottom:4px">${title}</div>` +
        (detail ? `<div style="font-weight:400;font-size:13px;opacity:.85">${detail}</div>` : "")
    },
    { title, detail }
  )
  const hold = Math.max(2, Math.round(ms / 800))
  for (let i = 0; i < hold; i++) {
    await shot(page, `${title}`)
    await page.waitForTimeout(800)
  }
}

async function shot(page, label = "") {
  frame += 1
  const name = `frame-${String(frame).padStart(4, "0")}.png`
  const path = join(OUT, name)
  await page.screenshot({ path, type: "png" })
  manifest.push({ frame, name, label })
  process.stdout.write(`\rframes ${frame} ${label.slice(0, 40).padEnd(40)}`)
}

async function safeClick(locator) {
  try {
    if ((await locator.count()) === 0) return false
    await locator.first().scrollIntoViewIfNeeded().catch(() => {})
    await locator.first().click({ timeout: 3500 })
    return true
  } catch {
    return false
  }
}

async function scrollDemo(page) {
  const hops = await page.evaluate(async () => {
    const step = Math.max(320, Math.floor(window.innerHeight * 0.6))
    const max = Math.max(0, document.body.scrollHeight - window.innerHeight)
    const ys = []
    for (let y = 0; y <= max; y += step) ys.push(y)
    if (!ys.includes(0)) ys.unshift(0)
    return ys
  })
  for (const y of hops) {
    await page.evaluate((yy) => window.scrollTo({ top: yy, behavior: "instant" }), y)
    await page.waitForTimeout(350)
    await shot(page, `scroll-${y}`)
  }
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }))
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
}

const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  args: ["--disable-dev-shm-usage"],
})
const context = await browser.newContext({ viewport: { width: 1600, height: 1000 }, locale: "zh-CN" })
const page = await context.newPage()

const loginRes = await page.request.post(`${API}/api/auth/login`, {
  data: { username: USER, password: PASS },
})
if (!loginRes.ok()) throw new Error(`login ${loginRes.status()}`)
const setCookie = loginRes.headersArray().filter((h) => h.name.toLowerCase() === "set-cookie")
const tokenMatch = setCookie.map((h) => h.value).join("\n").match(/cloudlens_auth_token=([^;]+)/)
if (!tokenMatch) throw new Error("no cookie")
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
await caption(page, "CloudLens 产品演示 · Web", "统一视图 · 成本分析 · 省钱机会 · 安全合规", 3600)

await go(page, "", /仪表盘|总预估成本|立即扫描/, "① 仪表盘", "成本概览、趋势与闲置资源")
await scrollDemo(page)
await safeClick(page.getByRole("button", { name: /立即扫描|重新扫描|刷新/ }))
await page.waitForTimeout(1200)
await shot(page, "dashboard-scan")

await go(page, "/resources", /资源管理|资源列表|ECS/, "② 资源管理", "查询 ECS / RDS / Redis")
await safeClick(page.getByRole("button", { name: /ECS|全部|RDS/ }))
await page.waitForTimeout(800)
await shot(page, "resources-filter")
const search = page.locator('input[type="text"], input[type="search"]').first()
if (await search.count()) {
  await search.fill("ecs")
  await page.waitForTimeout(700)
  await shot(page, "resources-search")
  await search.fill("")
}
await safeClick(page.getByRole("button", { name: /筛选|过滤|导出|CSV/ }))
await page.waitForTimeout(700)
await scrollDemo(page)

await go(page, "/cost", /成本分析|本月成本|成本构成/, "③ 成本分析", "本月成本与构成")
await scrollDemo(page)
await go(page, "/cost/attribution", /成本归因|账单数据不足|环比/, "③b 成本归因", "拆解账期变化原因")
await safeClick(page.getByRole("button", { name: /环比|同比/ }))
await page.waitForTimeout(900)
await shot(page, "attribution")
await safeClick(page.getByRole("button", { name: /同比|环比/ }))
await page.waitForTimeout(900)
await shot(page, "attribution-2")
await scrollDemo(page)
await go(page, "/cost-trend", /成本趋势|暂无|选择/, "③c 成本趋势", "历史成本曲线")
await scrollDemo(page)

await go(page, "/budgets", /预算管理|新建预算/, "④ 预算管理", "预算与告警阈值")
await safeClick(page.getByRole("button", { name: /新建预算|创建/ }))
await page.waitForTimeout(1000)
await shot(page, "budget-create")
await page.keyboard.press("Escape").catch(() => {})
await scrollDemo(page)

await go(page, "/discounts", /折扣分析|暂无折扣数据|高级折扣/, "⑤ 折扣分析", "多维折扣洞察")
for (const tab of ["总览", "时间分析", "产品分析", "区域分析", "计费分析", "高级分析"]) {
  await caption(page, `折扣分析 · ${tab}`, "", 1600)
  await safeClick(page.getByRole("tab", { name: tab }).or(page.getByRole("button", { name: tab })))
  await page.waitForTimeout(1000)
  await scrollDemo(page)
}

await go(page, "/virtual-tags", /虚拟标签|新建标签/, "⑥ 虚拟标签", "规则化虚拟标签")
await safeClick(page.getByRole("button", { name: /新建|创建/ }))
await page.waitForTimeout(900)
await shot(page, "vtags")
await page.keyboard.press("Escape").catch(() => {})
await scrollDemo(page)

await go(page, "/security", /安全合规|安全评分/, "⑦ 安全合规", "公网暴露与 CIS")
await safeClick(page.getByRole("button", { name: /扫描|刷新|重新检测/ }))
await page.waitForTimeout(1200)
await scrollDemo(page)

await go(page, "/optimization", /省钱机会|年化可省|框架合同/, "⑧ 省钱机会", "框架合同 + 年化可省")
await page.waitForTimeout(1500)
await shot(page, "savings")
const kpis = page.locator("button").filter({ hasText: /年化可省|框架合规|利用率|弱建议/ })
const n = await kpis.count()
for (let i = 0; i < Math.min(n, 4); i++) {
  await safeClick(kpis.nth(i))
  await page.waitForTimeout(900)
  await shot(page, `kpi-${i}`)
}
await caption(page, "框架合同", "导入 PDF → 核对 → 发布", 2000)
await safeClick(page.getByRole("button", { name: /框架合同/ }))
await page.waitForTimeout(1500)
await shot(page, "contract")
await safeClick(page.getByRole("button", { name: /高级|编辑规则|确认发布|保存/ }))
await page.waitForTimeout(1000)
await shot(page, "contract-adv")
await safeClick(page.getByRole("button", { name: /总览|机会|省钱/ }))
await page.waitForTimeout(1000)
await scrollDemo(page)

await go(page, "/reports", /报告生成|选择报告类型/, "⑨ 报告生成", "导出报告")
await safeClick(page.getByRole("button", { name: /综合|成本|安全|资源/ }))
await page.waitForTimeout(800)
await shot(page, "reports")
await safeClick(page.getByRole("button", { name: /生成|导出|下载/ }))
await page.waitForTimeout(1200)
await scrollDemo(page)

await go(page, "/settings", /设置|闲置检测|通知配置/, "⑩ 设置", "账号与规则配置")
for (const t of [/账号|云账号/, /闲置|规则/, /通知/, /语言|通用|系统/]) {
  await safeClick(page.getByRole("button", { name: t }).or(page.getByRole("tab", { name: t })))
  await page.waitForTimeout(800)
  await shot(page, "settings")
}
await scrollDemo(page)

for (const extra of [
  { path: "/alerts", re: /告警|规则|通知/i, title: "扩展 · 告警管理", detail: "告警规则与历史" },
  { path: "/cost-allocation", re: /成本分配|分配规则|权重/i, title: "扩展 · 成本分配", detail: "账单分摊规则" },
  { path: "/ai-optimizer", re: /AI|优化|建议|预测/i, title: "扩展 · AI 优化", detail: "优先优化建议" },
]) {
  try {
    await page.goto(BASE + accountPath(extra.path), { waitUntil: "domcontentloaded", timeout: 45000 })
    const body = (await page.locator("body").innerText()) || ""
    if (extra.re.test(body) && !/Application error|404/i.test(body)) {
      await caption(page, extra.title, extra.detail, 1800)
      await scrollDemo(page)
    } else {
      await caption(page, extra.title, "本环境该页暂无数据或路由受限", 1200)
    }
  } catch {
    await caption(page, extra.title, "本环境该页暂无数据或路由受限", 1200)
  }
}

await page.goto(BASE + accountPath("/optimization"), { waitUntil: "domcontentloaded" })
await caption(page, "Web 演示结束", "接下来介绍 CLI 核心命令", 3600)

await context.close()
await browser.close()
writeFileSync(join(OUT, "manifest.json"), JSON.stringify(manifest, null, 2))
console.log(`\nDONE frames=${frame} dir=${OUT} png=${readdirSync(OUT).filter((f) => f.endsWith(".png")).length}`)
