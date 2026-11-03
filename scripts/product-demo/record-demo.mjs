#!/usr/bin/env node
/**
 * CloudLens 产品演示重录：
 * - 每个页面/Tab 必须 waitLoaded 后再截帧
 * - 输出 scenes/ 下每场景若干 PNG + scenes.json（供旁白对齐）
 */
import { createRequire } from "module"
import { mkdirSync, writeFileSync, rmSync, existsSync, readFileSync } from "fs"
import { join, dirname } from "path"
import { fileURLToPath, pathToFileURL } from "url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, "../..")
const require = createRequire(join(ROOT, "web/frontend/package.json"))
const { chromium } = require("playwright")
const { waitLoaded } = await import(pathToFileURL(join(__dirname, "wait-loaded.mjs")).href)

const OUT = join(ROOT, "artifacts/product-demo/v2")
const SCENES_DIR = join(OUT, "scenes")
if (existsSync(SCENES_DIR)) rmSync(SCENES_DIR, { recursive: true })
mkdirSync(SCENES_DIR, { recursive: true })

const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000"
const API = process.env.E2E_API_BASE || "http://localhost:8000"
const USER = process.env.E2E_AUTH_USERNAME || "admin"
const PASS = process.env.E2E_AUTH_PASSWORD || "CloudLensAdmin2024!"
const ACCOUNT = process.env.E2E_AUTH_ACCOUNT || "cf"
const accountPath = (s) => `/a/${encodeURIComponent(ACCOUNT)}${s}`

const narration = JSON.parse(readFileSync(join(__dirname, "narration.json"), "utf-8"))
const narrById = Object.fromEntries(narration.map((n) => [n.id, n]))

const scenes = []
let sceneIndex = 0

async function caption(page, title, detail = "") {
  await page.evaluate(
    ({ title, detail }) => {
      const id = "__cl_demo_caption__"
      let el = document.getElementById(id)
      if (!el) {
        el = document.createElement("div")
        el.id = id
        el.style.cssText =
          "position:fixed;left:24px;bottom:24px;z-index:2147483647;max-width:min(720px,70vw);padding:14px 18px;border-radius:12px;background:rgba(8,12,24,0.9);border:1px solid rgba(99,140,255,0.45);color:#f5f7ff;font:600 16px/1.4 system-ui,sans-serif;pointer-events:none"
        document.body.appendChild(el)
      }
      el.innerHTML =
        `<div style="font-size:18px;margin-bottom:4px">${title}</div>` +
        (detail ? `<div style="font-weight:400;font-size:13px;opacity:.85">${detail}</div>` : "")
    },
    { title, detail }
  )
}

async function safeClick(locator) {
  try {
    if ((await locator.count()) === 0) return false
    await locator.first().scrollIntoViewIfNeeded().catch(() => {})
    await locator.first().click({ timeout: 5000 })
    return true
  } catch {
    return false
  }
}

async function scrollShots(page, dir, countHint = 3) {
  const hops = await page.evaluate(() => {
    const step = Math.max(360, Math.floor(window.innerHeight * 0.65))
    const max = Math.max(0, document.body.scrollHeight - window.innerHeight)
    const ys = []
    for (let y = 0; y <= max; y += step) ys.push(y)
    return ys.slice(0, 5)
  })
  const files = []
  for (const y of hops.slice(0, countHint)) {
    await page.evaluate((yy) => window.scrollTo({ top: yy, behavior: "instant" }), y)
    await page.waitForTimeout(400)
    const name = `f${String(files.length + 1).padStart(2, "0")}.png`
    await page.screenshot({ path: join(dir, name), type: "png" })
    files.push(name)
  }
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }))
  if (!files.length) {
    const name = "f01.png"
    await page.screenshot({ path: join(dir, name), type: "png" })
    files.push(name)
  }
  return files
}

async function beginScene(id, page) {
  sceneIndex += 1
  const meta = narrById[id] || { id, title: id, text: "" }
  const dir = join(SCENES_DIR, `${String(sceneIndex).padStart(2, "0")}-${id}`)
  mkdirSync(dir, { recursive: true })
  await caption(page, meta.title, meta.text.slice(0, 42) + (meta.text.length > 42 ? "…" : ""))
  console.log(`\n▶ [${sceneIndex}] ${id} · ${meta.title}`)
  return { id, title: meta.title, text: meta.text, dir, index: sceneIndex }
}

async function endScene(scene, page, extraFrames = 1) {
  const files = await scrollShots(page, scene.dir, 3)
  for (let i = 0; i < extraFrames; i++) {
    await page.waitForTimeout(500)
    const name = `f${String(files.length + 1).padStart(2, "0")}.png`
    await page.screenshot({ path: join(scene.dir, name), type: "png" })
    files.push(name)
  }
  const rec = {
    id: scene.id,
    index: scene.index,
    title: scene.title,
    text: scene.text,
    dir: scene.dir,
    frames: files,
  }
  scenes.push(rec)
  writeFileSync(join(scene.dir, "meta.json"), JSON.stringify(rec, null, 2))
  console.log(`  ✓ frames=${files.length}`)
  return rec
}

async function goScene(page, id, suffix, expectRe) {
  await page.goto(BASE + accountPath(suffix), { waitUntil: "domcontentloaded", timeout: 90000 })
  await page.waitForFunction(() => !location.pathname.includes("/login"), null, { timeout: 45000 })
  const info = await waitLoaded(page, { expectText: expectRe, timeout: 120000 })
  console.log(`  loaded ${info.waitedMs}ms · ${info.preview}`)
  const scene = await beginScene(id, page)
  await endScene(scene, page)
}

const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  args: ["--disable-dev-shm-usage"],
})
const context = await browser.newContext({
  viewport: { width: 1600, height: 1000 },
  locale: "zh-CN",
})
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

// intro on dashboard shell
await page.goto(BASE + accountPath(""), { waitUntil: "domcontentloaded", timeout: 90000 })
await waitLoaded(page, { expectText: /仪表盘|总预估成本|立即扫描/, timeout: 120000 })
{
  const scene = await beginScene("intro", page)
  await endScene(scene, page, 2)
}

await goScene(page, "dashboard", "", /仪表盘|总预估成本|立即扫描/)
await safeClick(page.getByRole("button", { name: /立即扫描|重新扫描|刷新/ }))
await waitLoaded(page, { expectText: /仪表盘|总预估成本|闲置/, timeout: 90000 })

await page.goto(BASE + accountPath("/resources"), { waitUntil: "domcontentloaded", timeout: 90000 })
await waitLoaded(page, { expectText: /资源管理|资源列表|ECS/, timeout: 120000 })

async function clearResourceSearch() {
  const searchBox = page.locator('input[placeholder*="搜索"]').first()
  if (await searchBox.count()) {
    await searchBox.fill("")
    await page.waitForTimeout(350)
  }
}

async function waitResourceTableReady(typeLabel) {
  await waitLoaded(page, {
    expectText: new RegExp(`资源列表|${typeLabel}|共 \\d+|显示`),
    timeout: 180000,
    idleMs: 800,
  })
  // 等 loading 骨架结束，并出现表格行或明确的 0 条
  await page
    .waitForFunction(
      () => {
        const main =
          document.querySelector("main") ||
          document.querySelector(".p-6") ||
          document.body
        const text = main?.innerText || ""
        if (/正在加载|Loading/i.test(text) && !/共 \d+ 个资源/.test(text)) return false
        if (document.querySelector(".animate-spin")) {
          const spins = [...document.querySelectorAll(".animate-spin")]
          if (spins.some((el) => el.getBoundingClientRect().height > 20)) return false
        }
        const rows = document.querySelectorAll("table tbody tr")
        if (rows.length > 0) return true
        // 空列表也算就绪
        if (/共 0 个资源|暂无资源|No resources|0 \/ 0/i.test(text)) return true
        if (/共 \d+ 个资源/.test(text)) return true
        return false
      },
      null,
      { timeout: 180000 }
    )
    .catch(() => {})
  await page.waitForTimeout(600)
}

const resourceTabs = [
  "ECS",
  "RDS",
  "Redis",
  "SLB",
  "NAT",
  "EIP",
  "OSS",
  "Disk",
  "Snapshot",
  "VPC",
  "MongoDB",
  "ACK",
]
{
  await clearResourceSearch()
  const scene = await beginScene("resources", page)
  const shotFiles = []
  for (const tab of resourceTabs) {
    console.log(`  · resource tab ${tab}`)
    await safeClick(page.getByRole("button", { name: tab, exact: true }))
    await clearResourceSearch()
    await waitResourceTableReady(tab)
    const name = `tab-${tab.toLowerCase()}.png`
    await page.screenshot({ path: join(scene.dir, name), type: "png" })
    shotFiles.push(name)
  }
  // 有数据时进 ECS 详情
  await safeClick(page.getByRole("button", { name: "ECS", exact: true }))
  await clearResourceSearch()
  await waitResourceTableReady("ECS")
  const firstRow = page.locator("table tbody tr").first()
  if ((await firstRow.count()) > 0) {
    await firstRow.click()
    await waitLoaded(page, {
      expectText: /详情|规格|区域|状态|实例|资源|返回|ECS|i-/,
      timeout: 120000,
    })
    await page.screenshot({ path: join(scene.dir, "detail.png"), type: "png" })
    shotFiles.push("detail.png")
    await page.goto(BASE + accountPath("/resources"), {
      waitUntil: "domcontentloaded",
      timeout: 90000,
    })
    await waitResourceTableReady("ECS")
  }
  // 规范为 f01.. 供合成使用（保留关键有数据的帧：ECS/RDS/Redis/详情 + 其余各一帧）
  const prefer = ["tab-ecs.png", "tab-rds.png", "tab-redis.png", "detail.png", "tab-slb.png", "tab-vpc.png", "tab-oss.png", "tab-disk.png"]
  const picked = []
  for (const f of prefer) {
    if (shotFiles.includes(f) && existsSync(join(scene.dir, f))) picked.push(f)
  }
  for (const f of shotFiles) {
    if (!picked.includes(f) && picked.length < 12) picked.push(f)
  }
  const { copyFileSync, unlinkSync, readdirSync: rd } = await import("fs")
  const frames = []
  picked.forEach((src, i) => {
    const dest = `f${String(i + 1).padStart(2, "0")}.png`
    copyFileSync(join(scene.dir, src), join(scene.dir, dest))
    frames.push(dest)
  })
  // 清理非 fXX 临时图
  for (const f of rd(scene.dir)) {
    if (f.endsWith(".png") && !/^f\d+\.png$/.test(f)) {
      try {
        unlinkSync(join(scene.dir, f))
      } catch {
        /* ignore */
      }
    }
  }
  const rec = {
    id: scene.id,
    index: scene.index,
    title: scene.title,
    text: scene.text,
    dir: scene.dir,
    frames,
  }
  scenes.push(rec)
  writeFileSync(join(scene.dir, "meta.json"), JSON.stringify(rec, null, 2))
  console.log(`  ✓ resource tabs=${resourceTabs.length} frames=${frames.length}`)
}

await goScene(page, "cost", "/cost", /成本分析|本月成本|成本构成/)
await page.goto(BASE + accountPath("/cost/attribution"), {
  waitUntil: "domcontentloaded",
  timeout: 90000,
})
await waitLoaded(page, { expectText: /成本归因|账单数据不足|环比/, timeout: 120000 })
await safeClick(page.getByRole("button", { name: /环比/ }))
await waitLoaded(page, { expectText: /成本归因|环比|同比|暂无|数据/, timeout: 90000 })
await safeClick(page.getByRole("button", { name: /同比/ }))
await waitLoaded(page, { expectText: /成本归因|环比|同比|暂无|数据/, timeout: 90000 })
{
  const scene = await beginScene("cost-attribution", page)
  await endScene(scene, page)
}
await goScene(page, "cost-trend", "/cost-trend", /成本趋势|暂无|选择/)

await page.goto(BASE + accountPath("/budgets"), { waitUntil: "domcontentloaded", timeout: 90000 })
await waitLoaded(page, { expectText: /预算管理|新建预算/, timeout: 120000 })
await safeClick(page.getByRole("button", { name: /新建预算|创建/ }))
await page.waitForTimeout(1000)
{
  const scene = await beginScene("budgets", page)
  await endScene(scene, page)
}
await page.keyboard.press("Escape").catch(() => {})

// 折扣各 Tab：必须等加载
await page.goto(BASE + accountPath("/discounts"), { waitUntil: "domcontentloaded", timeout: 90000 })
await waitLoaded(page, {
  expectText: /折扣分析|暂无折扣数据|季度|年度|总览|高级折扣/,
  timeout: 180000,
  idleMs: 1500,
})
{
  const scene = await beginScene("discounts-overview", page)
  await endScene(scene, page)
}

const discountTabs = [
  ["时间分析", "discounts-time", /时间分析|季度|年度|同比|环比|暂无/],
  ["产品分析", "discounts-product", /产品分析|产品|趋势|暂无/],
  ["区域分析", "discounts-region", /区域分析|地域|区域|暂无/],
  ["计费分析", "discounts-billing", /计费分析|包年|按量|订阅|暂无/],
  ["高级分析", "discounts-advanced", /高级分析|优化建议|异常|年化|暂无/],
]
for (const [tab, id, re] of discountTabs) {
  const tabBtn = page.getByRole("tab", { name: tab }).or(page.getByRole("button", { name: tab }))
  await safeClick(tabBtn)
  await waitLoaded(page, { expectText: re, timeout: 180000, idleMs: 1200 })
  const scene = await beginScene(id, page)
  await endScene(scene, page)
}

await goScene(page, "virtual-tags", "/virtual-tags", /虚拟标签|新建标签/)
await goScene(page, "security", "/security", /安全合规|安全评分/)
await safeClick(page.getByRole("button", { name: /扫描|刷新|重新检测/ }))
await waitLoaded(page, { expectText: /安全|评分|风险|暂无/, timeout: 120000 })

await page.goto(BASE + accountPath("/optimization"), {
  waitUntil: "domcontentloaded",
  timeout: 90000,
})
await waitLoaded(page, {
  expectText: /年化可省合计|暂无优化建议|框架合同|扫描失败/,
  timeout: 240000,
  idleMs: 1500,
})
{
  const scene = await beginScene("optimization", page)
  await endScene(scene, page)
}
{
  const kpis = page.locator("button").filter({ hasText: /年化可省|框架合规|利用率|弱建议/ })
  const n = await kpis.count()
  for (let i = 0; i < Math.min(n, 4); i++) {
    await safeClick(kpis.nth(i))
    await waitLoaded(page, {
      expectText: /年化可省|框架|利用率|弱建议|暂无|省钱/,
      timeout: 90000,
    })
  }
  const scene = await beginScene("optimization-kpi", page)
  await endScene(scene, page)
}

await safeClick(page.getByRole("button", { name: /框架合同/ }))
await waitLoaded(page, { expectText: /框架合同|确认发布|草稿|生效|导入|PDF|未配置/, timeout: 90000 })
{
  const scene = await beginScene("contract", page)
  await endScene(scene, page)
}
await safeClick(page.getByRole("button", { name: /高级|编辑规则/ }))
await page.waitForTimeout(600)
await safeClick(page.getByRole("button", { name: /总览|机会|省钱/ }))
await waitLoaded(page, { expectText: /省钱机会|年化可省/, timeout: 90000 })

await goScene(page, "reports", "/reports", /报告生成|选择报告类型/)
await page.goto(BASE + accountPath("/settings"), { waitUntil: "domcontentloaded", timeout: 90000 })
await waitLoaded(page, { expectText: /设置|闲置检测|通知配置/, timeout: 120000 })
for (const t of [/账号|云账号/, /闲置|规则/, /通知/, /语言|通用|系统/]) {
  await safeClick(page.getByRole("button", { name: t }).or(page.getByRole("tab", { name: t })))
  await waitLoaded(page, { timeout: 45000, idleMs: 600 })
}
{
  const scene = await beginScene("settings", page)
  await endScene(scene, page)
}

{
  // 扩展页路由在 /alerts 等，不在 /a/{account}/ 下；走无账号前缀避免 404
  const scene = await beginScene("extras", page)
  const { copyFileSync, unlinkSync, readdirSync: rd } = await import("fs")
  const extras = [
    { path: "/alerts", re: /告警|规则|通知|Alerts/i },
    { path: "/cost-allocation", re: /成本分配|分配规则|权重|allocation/i },
    { path: "/ai-optimizer", re: /AI|优化|建议|预测/i },
  ]
  const raw = []
  for (const item of extras) {
    await page.goto(BASE + item.path, { waitUntil: "domcontentloaded", timeout: 60000 })
    await page.waitForFunction(() => !location.pathname.includes("/login"), null, { timeout: 30000 }).catch(() => {})
    // 若仍 404 则跳过该页
    const body = (await page.locator("body").innerText().catch(() => "")) || ""
    if (/This page could not be found|404/.test(body)) {
      console.log(`  · skip 404 ${item.path}`)
      continue
    }
    await waitLoaded(page, { expectText: item.re, timeout: 90000, allowEmptyOk: true }).catch(() => {})
    const name = `raw-${item.path.replace(/\W+/g, "")}.png`
    await page.screenshot({ path: join(scene.dir, name), type: "png" })
    raw.push(name)
  }
  const frames = []
  raw.forEach((src, i) => {
    const dest = `f${String(i + 1).padStart(2, "0")}.png`
    copyFileSync(join(scene.dir, src), join(scene.dir, dest))
    frames.push(dest)
  })
  if (!frames.length) {
    // 回落到设置页，保证不出现 404
    await page.goto(BASE + accountPath("/settings"), { waitUntil: "domcontentloaded", timeout: 60000 })
    await waitLoaded(page, { expectText: /设置/, timeout: 60000 })
    await page.screenshot({ path: join(scene.dir, "f01.png"), type: "png" })
    frames.push("f01.png")
  }
  for (const f of rd(scene.dir)) {
    if (f.endsWith(".png") && !/^f\d+\.png$/.test(f)) {
      try {
        unlinkSync(join(scene.dir, f))
      } catch {
        /* ignore */
      }
    }
  }
  const rec = {
    id: scene.id,
    index: scene.index,
    title: scene.title,
    text: scene.text,
    dir: scene.dir,
    frames,
  }
  scenes.push(rec)
  writeFileSync(join(scene.dir, "meta.json"), JSON.stringify(rec, null, 2))
  console.log(`  ✓ extras frames=${frames.length}`)
}

await context.close()
await browser.close()

const timeline = { account: ACCOUNT, generatedAt: new Date().toISOString(), scenes }
writeFileSync(join(OUT, "scenes.json"), JSON.stringify(timeline, null, 2))
console.log(`\nDONE scenes=${scenes.length} → ${join(OUT, "scenes.json")}`)
