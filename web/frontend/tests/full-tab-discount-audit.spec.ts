/**
 * 全量 Tab 遍历 + 折扣数据准确性审计（系统 Chrome headed）
 *
 * 覆盖：
 * - 侧栏全部业务页
 * - 资源页全部类型 Tab
 * - 仪表盘/成本趋势时间范围按钮
 * - 折扣页全部时间范围 + 6 个分析 Tab
 * - 折扣 API 数学一致性与 UI 数字对齐
 */
import { test, expect, Page, APIRequestContext } from "@playwright/test"
import { mkdirSync, writeFileSync } from "fs"
import { join } from "path"

const AUTH_USERNAME = process.env.E2E_AUTH_USERNAME || "admin"
const AUTH_PASSWORD = process.env.E2E_AUTH_PASSWORD || "CloudLensAdmin2024!"
const ACCOUNT = process.env.E2E_AUTH_ACCOUNT || "cf"
const API_BASE = process.env.E2E_API_BASE || "http://localhost:8000"
const SCREENSHOT_DIR = join(process.cwd(), "test-recordings", "full-tab-audit")

mkdirSync(SCREENSHOT_DIR, { recursive: true })

const NAV_PAGES: Array<{ name: string; path: string; expectText: RegExp }> = [
  { name: "仪表盘", path: "", expectText: /仪表盘|总预估成本|立即扫描/ },
  { name: "资源", path: "/resources", expectText: /资源管理|资源列表|ECS/ },
  { name: "成本分析", path: "/cost", expectText: /成本分析|本月成本|成本构成/ },
  { name: "成本归因", path: "/cost/attribution", expectText: /成本归因|账单数据不足|环比/ },
  { name: "成本趋势", path: "/cost-trend", expectText: /成本趋势|暂无|选择/ },
  { name: "预算管理", path: "/budgets", expectText: /预算管理|新建预算/ },
  { name: "折扣分析", path: "/discounts", expectText: /折扣分析|高级折扣|暂无折扣数据/ },
  { name: "虚拟标签", path: "/virtual-tags", expectText: /虚拟标签|新建标签/ },
  { name: "安全", path: "/security", expectText: /安全合规|安全评分/ },
  { name: "优化", path: "/optimization", expectText: /优化建议|节省潜力/ },
  { name: "报告", path: "/reports", expectText: /报告生成|选择报告类型/ },
  { name: "设置", path: "/settings", expectText: /设置|闲置检测|通知配置/ },
]

const RESOURCE_TYPES = ["ECS", "RDS", "Redis", "SLB", "NAT", "EIP", "OSS", "Disk", "Snapshot", "VPC", "MongoDB", "ACK"]
const DISCOUNT_TABS = ["总览", "时间分析", "产品分析", "区域分析", "计费分析", "高级分析"] as const
const DISCOUNT_RANGES = ["全部时间", "最近3个月", "最近6个月", "最近12个月"] as const
const COST_RANGES = ["7天", "30天", "90天", "全部"] as const

type AuditFinding = { level: "ok" | "warn" | "fail"; area: string; message: string }

function accountPath(suffix: string): string {
  return `/a/${encodeURIComponent(ACCOUNT)}${suffix}`
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `¥${Math.round(value / 1_000_000)}M`
  if (value >= 1000) return `¥${Math.round(value / 1000)}K`
  return `¥${Math.round(value)}`
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function almostEqual(a: number, b: number, absTol = 0.02, relTol = 1e-6): boolean {
  const diff = Math.abs(a - b)
  return diff <= absTol || diff <= Math.max(Math.abs(a), Math.abs(b)) * relTol
}

async function assertNoCrash(page: Page, name: string) {
  const body = (await page.locator("body").innerText()) || ""
  expect(body, `${name} 出现 [object Object]`).not.toContain("[object Object]")
  expect(body, `${name} 出现 Application error`).not.toContain("Application error")
  expect(body, `${name} 出现 client-side exception`).not.toContain("client-side exception")
  expect(body, `${name} 出现 Internal Server Error`).not.toMatch(/Internal Server Error/i)
  return body
}

async function login(page: Page) {
  // 先走 API 登录拿 cookie，避免 UI 输入框偶发未写入
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
  await expect
    .poll(async () => page.url(), { timeout: 30000 })
    .not.toContain("/login")
}

async function apiGetJson(request: APIRequestContext, path: string) {
  const res = await request.get(`${API_BASE}${path}`, { timeout: 60000 })
  expect(res.ok(), `${path} HTTP ${res.status()}`).toBeTruthy()
  return res.json()
}

async function auditDiscountApis(request: APIRequestContext): Promise<{
  findings: AuditFinding[]
  snapshot: Record<string, unknown>
}> {
  const findings: AuditFinding[] = []
  const q = `account=${encodeURIComponent(ACCOUNT)}`

  const quarterly = await apiGetJson(request, `/api/discounts/quarterly?${q}&quarters=8`)
  const yearly = await apiGetJson(request, `/api/discounts/yearly?${q}`)
  const products = await apiGetJson(request, `/api/discounts/product-trends?${q}&months=19&top_n=10`)
  const regions = await apiGetJson(request, `/api/discounts/regions?${q}`)
  const subscription = await apiGetJson(request, `/api/discounts/subscription-types?${q}`)
  const suggestions = await apiGetJson(request, `/api/discounts/optimization-suggestions?${q}`)
  const anomalies = await apiGetJson(request, `/api/discounts/anomalies?${q}&threshold=0.10`)
  const cumulative = await apiGetJson(request, `/api/discounts/cumulative?${q}`)
  const moving = await apiGetJson(request, `/api/discounts/moving-average?${q}&windows=3%2C6%2C12`)
  // force_refresh 避开旧缓存里错误的百分数折扣率
  const trend = await apiGetJson(request, `/api/discounts/trend?${q}&months=19&force_refresh=true`)

  const quarters = quarterly?.data?.quarters || []
  const years = yearly?.data?.years || []
  const productList = products?.data?.products || []
  const regionList = regions?.data?.regions || []
  const cumSeries = cumulative?.data?.cumulative_data || []
  const totalDiscount = Number(cumulative?.data?.total_discount || 0)
  const timeline = trend?.data?.trend_analysis?.timeline || []

  expect(quarters.length, "季度折扣数据不能为空").toBeGreaterThan(0)
  expect(years.length, "年度折扣数据不能为空").toBeGreaterThan(0)
  expect(productList.length, "产品折扣趋势不能为空").toBeGreaterThan(0)
  expect(regionList.length, "区域折扣数据不能为空").toBeGreaterThan(0)
  expect(cumSeries.length, "累计折扣序列不能为空").toBeGreaterThan(0)
  expect(totalDiscount, "累计折扣总额应 > 0").toBeGreaterThan(0)

  findings.push({ level: "ok", area: "API.coverage", message: `季度${quarters.length}/年${years.length}/产品${productList.length}/区域${regionList.length}/累计月${cumSeries.length}` })

  // 1) 折扣恒等式：original ≈ paid + discount；rate ≈ discount / original
  for (const item of quarters) {
    const original = Number(item.total_original || 0)
    const discount = Number(item.total_discount || 0)
    const paid = Number(item.total_paid || 0)
    const rate = Number(item.avg_discount_rate || 0)
    expect(almostEqual(original, paid + discount, 1), `${item.period} original≠paid+discount`).toBeTruthy()
    if (original > 0) {
      expect(almostEqual(rate, discount / original, 1e-4), `${item.period} rate 不一致`).toBeTruthy()
    }
    expect(rate).toBeGreaterThanOrEqual(0)
    expect(rate).toBeLessThanOrEqual(1)
  }
  findings.push({ level: "ok", area: "API.quarterly", message: "季度 original=paid+discount 且 rate=discount/original 成立" })

  for (const item of years) {
    const original = Number(item.total_original || 0)
    const discount = Number(item.total_discount || 0)
    const paid = Number(item.total_paid || 0)
    const rate = Number(item.avg_discount_rate || 0)
    expect(almostEqual(original, paid + discount, 1), `${item.year} original≠paid+discount`).toBeTruthy()
    if (original > 0) {
      expect(almostEqual(rate, discount / original, 1e-4), `${item.year} rate 不一致`).toBeTruthy()
    }
  }
  findings.push({ level: "ok", area: "API.yearly", message: "年度折扣恒等式成立" })

  // 2) 累计折扣爬升：每月累计 = 上月累计 + 当月折扣
  for (let i = 0; i < cumSeries.length; i++) {
    const row = cumSeries[i]
    const monthly = Number(row.monthly_discount || 0)
    const cumulativeValue = Number(row.cumulative_discount || 0)
    if (i === 0) {
      expect(almostEqual(cumulativeValue, monthly, 0.05), `首月累计应为当月折扣`).toBeTruthy()
    } else {
      const prev = Number(cumSeries[i - 1].cumulative_discount || 0)
      expect(almostEqual(cumulativeValue, prev + monthly, 0.05), `${row.month} 累计不连续`).toBeTruthy()
    }
  }
  const lastCum = Number(cumSeries[cumSeries.length - 1]?.cumulative_discount || 0)
  expect(almostEqual(lastCum, totalDiscount, 0.05), "累计总额与末月累计不一致").toBeTruthy()
  findings.push({
    level: "ok",
    area: "API.cumulative",
    message: `累计爬升连续，总额 ${formatCurrency(totalDiscount)}（${totalDiscount.toFixed(2)}）`,
  })

  // 3) 区域折扣合计 vs 累计总额：允许未归属差额，但不应离谱
  const regionDiscountSum = regionList.reduce((s: number, r: any) => s + Number(r.total_discount || 0), 0)
  const regionGap = Math.abs(regionDiscountSum - totalDiscount)
  const regionGapPct = totalDiscount > 0 ? regionGap / totalDiscount : 0
  if (regionGapPct > 0.05) {
    findings.push({
      level: "warn",
      area: "API.regions",
      message: `区域折扣合计 ${regionDiscountSum.toFixed(2)} 与累计总额 ${totalDiscount.toFixed(2)} 相差 ${(regionGapPct * 100).toFixed(1)}%，请确认是否有未归属区域账单`,
    })
  } else {
    findings.push({
      level: "ok",
      area: "API.regions",
      message: `区域折扣合计与累计总额偏差 ${(regionGapPct * 100).toFixed(2)}%（可接受）`,
    })
  }
  for (const r of regionList) {
    const rate = Number(r.avg_discount_rate || 0)
    expect(rate).toBeGreaterThanOrEqual(0)
    expect(rate).toBeLessThanOrEqual(1)
  }

  // 4) 产品折扣率边界
  for (const p of productList.slice(0, 20)) {
    const rate = Number(p.avg_discount_rate || 0)
    expect(rate).toBeGreaterThanOrEqual(0)
    expect(rate).toBeLessThanOrEqual(1)
    for (const t of p.trends || []) {
      const tr = Number(t.discount_rate || 0)
      expect(tr).toBeGreaterThanOrEqual(0)
      expect(tr).toBeLessThanOrEqual(1)
      const o = Number(t.official_price || 0)
      const d = Number(t.discount_amount || 0)
      const paid = Number(t.paid_amount || 0)
      if (o > 0) {
        expect(almostEqual(o, paid + d, 1), `${p.product_name} ${t.month} 金额恒等式`).toBeTruthy()
      }
    }
  }
  findings.push({ level: "ok", area: "API.products", message: "产品折扣率落在 [0,1]，金额恒等式成立" })

  // 5) 移动平均：窗口均值应接近手工计算
  const original = moving?.data?.original_data || []
  const ma3 = moving?.data?.moving_averages?.ma_3 || []
  if (original.length >= 3 && ma3.length >= 3) {
    const rates = original.map((x: any) => Number(x.rate || 0))
    const last3 = rates.slice(-3)
    const expected = last3.reduce((a: number, b: number) => a + b, 0) / last3.length
    const actual = Number(ma3[ma3.length - 1]?.ma ?? NaN)
    expect(almostEqual(actual, expected, 1e-4), "ma_3 末值计算错误").toBeTruthy()
    findings.push({ level: "ok", area: "API.movingAverage", message: `ma_3 末值 ${formatPercent(actual)} 与手工均值一致` })
  } else {
    findings.push({ level: "warn", area: "API.movingAverage", message: "移动平均样本不足，跳过均值核对" })
  }

  // 6) 异常/建议数量合理
  const anomalyCount = Number(anomalies?.data?.total_anomalies || 0)
  const suggestionCount = Number(suggestions?.data?.total_suggestions || 0)
  const potential = Number(suggestions?.data?.total_potential_savings || 0)
  expect(anomalyCount).toBeGreaterThanOrEqual(0)
  expect(suggestionCount).toBeGreaterThanOrEqual(0)
  expect(potential).toBeGreaterThanOrEqual(0)
  findings.push({
    level: "ok",
    area: "API.suggestions",
    message: `异常 ${anomalyCount} 条，优化建议 ${suggestionCount} 条，潜在年节省 ${formatCurrency(potential)}`,
  })

  // 7) 趋势页折扣率必须是 0~1；若出现 >1 说明后端误把百分数当小数（会显示成上千%）
  const avgRate = Number(trend?.data?.trend_analysis?.average_discount_rate || 0)
  const latestRate = Number(trend?.data?.trend_analysis?.latest_discount_rate || 0)
  expect(avgRate).toBeGreaterThanOrEqual(0)
  expect(avgRate).toBeLessThanOrEqual(1)
  expect(latestRate).toBeGreaterThanOrEqual(0)
  expect(latestRate, `latest_discount_rate=${latestRate} 疑似未归一化到 0~1`).toBeLessThanOrEqual(1)
  for (const row of timeline) {
    const rate = Number(row.discount_rate || 0)
    expect(rate, `${row.period} timeline.discount_rate=${rate}`).toBeGreaterThanOrEqual(0)
    expect(rate, `${row.period} timeline.discount_rate=${rate}`).toBeLessThanOrEqual(1)
    const o = Number(row.official_price || 0)
    const d = Number(row.discount_amount || 0)
    if (o > 0) {
      expect(almostEqual(rate, d / o, 1e-3), `${row.period} rate 与金额不符`).toBeTruthy()
    }
  }
  findings.push({
    level: "ok",
    area: "API.trend",
    message: `平均折扣率 ${formatPercent(avgRate)}，最新 ${formatPercent(latestRate)}，方向 ${trend?.data?.trend_analysis?.trend_direction}`,
  })

  // 8) 包年包月 vs 按量差应在 [-1,1]
  const rateDiff = Number(subscription?.data?.rate_difference || 0)
  expect(rateDiff).toBeGreaterThanOrEqual(-1)
  expect(rateDiff).toBeLessThanOrEqual(1)
  findings.push({
    level: "ok",
    area: "API.subscription",
    message: `包年包月相对按量折扣率差 ${formatPercent(rateDiff)}`,
  })

  const latestQuarter = quarters[quarters.length - 1]
  const snapshot = {
    latestQuarterPeriod: latestQuarter?.period,
    latestQuarterRate: formatPercent(Number(latestQuarter?.avg_discount_rate || 0)),
    latestQuarterDiscount: formatCurrency(Number(latestQuarter?.total_discount || 0)),
    suggestionCount,
    suggestionCountText: `${suggestionCount}个实例`,
    anomalyCount,
    anomalyCountText: `${anomalyCount}个月份`,
    potentialSavings: formatCurrency(potential),
    totalDiscount: formatCurrency(totalDiscount),
    monthlyAverageBySeries: formatCurrency(totalDiscount / Math.max(cumSeries.length, 1)),
    monthlyAverageByHardcoded19: formatCurrency(totalDiscount / 19),
    topRegion: regionList[0]?.region || regionList[0]?.region_name,
    topRegionRate: formatPercent(Number(regionList[0]?.avg_discount_rate || 0)),
    topProduct: productList[0]?.product_name,
    topProductRate: formatPercent(Number(productList[0]?.avg_discount_rate || 0)),
  }

  return { findings, snapshot }
}

async function clickVisibleButton(page: Page, name: string): Promise<boolean> {
  const candidates = [
    page.getByRole("button", { name, exact: true }),
    page.getByRole("tab", { name, exact: true }),
    page.locator("button", { hasText: new RegExp(`^\\s*${name}\\s*$`) }),
  ]
  for (const loc of candidates) {
    const first = loc.first()
    if ((await first.count().catch(() => 0)) === 0) continue
    if (!(await first.isVisible().catch(() => false))) continue
    await first.click({ timeout: 3000, force: true }).catch(() => undefined)
    return true
  }
  return false
}

test.describe.configure({ mode: "serial" })

test.describe("全量 Tab 遍历与折扣数据审计", () => {
  test.use({ viewport: { width: 1600, height: 1000 } })
  test.setTimeout(480000)

  test("API 数学校验 + 全 Tab 点击 + UI 数字对齐", async ({ page }) => {
    const findings: AuditFinding[] = []

    await test.step("登录", async () => {
      await login(page)
    })

    // page.request 会自动携带登录后的 cookie
    const authed = page.request

    let snapshot: Record<string, unknown> = {}
    await test.step("折扣 API 数学准确性审计", async () => {
      const result = await auditDiscountApis(authed)
      findings.push(...result.findings)
      snapshot = result.snapshot
    })

    for (const item of NAV_PAGES) {
      await test.step(`导航-${item.name}`, async () => {
        await page.goto(accountPath(item.path), { waitUntil: "domcontentloaded", timeout: 45000 })
        await expect(page.locator("body")).toContainText(item.expectText, { timeout: 45000 })
        await page.waitForTimeout(1200)
        await assertNoCrash(page, item.name)
        await page.screenshot({ path: join(SCREENSHOT_DIR, `nav-${item.name}.png`), fullPage: true })
      })
    }

    await test.step("仪表盘时间范围按钮", async () => {
      console.log("STEP 仪表盘时间范围")
      await page.goto(accountPath(""), { waitUntil: "domcontentloaded", timeout: 45000 })
      await expect(page.locator("body")).toContainText(/仪表盘|总预估成本/, { timeout: 45000 })
      for (const label of COST_RANGES) {
        const clicked = await clickVisibleButton(page, label)
        if (!clicked) {
          findings.push({ level: "warn", area: "UI.dashboard", message: `未找到时间按钮 ${label}` })
          continue
        }
        await page.waitForTimeout(500)
        await assertNoCrash(page, `仪表盘-${label}`)
      }
      await page.screenshot({ path: join(SCREENSHOT_DIR, "dashboard-ranges.png") })
    })

    await test.step("资源页全部类型 Tab", async () => {
      console.log("STEP 资源类型 Tab")
      await page.goto(accountPath("/resources"), { waitUntil: "domcontentloaded", timeout: 45000 })
      await expect(page.locator("body")).toContainText(/资源管理|ECS/, { timeout: 45000 })
      for (const type of RESOURCE_TYPES) {
        const clicked = await clickVisibleButton(page, type)
        expect(clicked, `资源页缺少类型 ${type}`).toBeTruthy()
        await page.waitForTimeout(800)
        const body = await assertNoCrash(page, `资源-${type}`)
        expect(body.length).toBeGreaterThan(50)
        await page.screenshot({ path: join(SCREENSHOT_DIR, `resource-${type}.png`) })
      }
    })

    await test.step("成本趋势时间范围", async () => {
      console.log("STEP 成本趋势时间范围")
      await page.goto(accountPath("/cost-trend"), { waitUntil: "domcontentloaded", timeout: 45000 })
      await expect(page.locator("body")).toContainText(/成本趋势/, { timeout: 45000 })
      for (const label of COST_RANGES) {
        const clicked = await clickVisibleButton(page, label)
        if (clicked) {
          await page.waitForTimeout(600)
          await assertNoCrash(page, `成本趋势-${label}`)
        } else {
          findings.push({ level: "warn", area: "UI.costTrend", message: `未找到时间按钮 ${label}` })
        }
      }
      await page.screenshot({ path: join(SCREENSHOT_DIR, "cost-trend-ranges.png") })
    })

    await test.step("折扣页：时间范围 × 全部 Tab + UI 数字对齐", async () => {
      console.log("STEP 折扣页审计")
      await page.goto(accountPath("/discounts"), { waitUntil: "domcontentloaded", timeout: 45000 })
      await expect(page.locator("body")).toContainText(/高级折扣分析|折扣分析/, { timeout: 60000 })
      // 等总览关键指标出现
      await expect(page.getByText("最新季度折扣率").first()).toBeVisible({ timeout: 60000 })

      // 时间范围全点一遍（会触发重新拉数）
      for (const range of DISCOUNT_RANGES) {
        console.log("  range", range)
        const clicked = await clickVisibleButton(page, range)
        expect(clicked, `折扣页应有时间范围 ${range}`).toBeTruthy()
        await expect(page.getByText("最新季度折扣率").first()).toBeVisible({ timeout: 60000 })
        await page.waitForTimeout(1000)
        await assertNoCrash(page, `折扣时间-${range}`)
        await page.screenshot({ path: join(SCREENSHOT_DIR, `discount-range-${range}.png`) })
      }

      // 切回全部时间，再对 6 个 Tab 做内容核对
      await clickVisibleButton(page, "全部时间")
      await expect(page.getByText("最新季度折扣率").first()).toBeVisible({ timeout: 60000 })

      // 总览数字对齐
      const overviewBody = await page.locator("body").innerText()
      expect(overviewBody).toContain(String(snapshot.latestQuarterRate))
      expect(overviewBody).toContain(String(snapshot.latestQuarterDiscount))
      expect(overviewBody).toContain(String(snapshot.suggestionCountText))
      expect(overviewBody).toContain(String(snapshot.anomalyCountText))
      expect(overviewBody).toContain(String(snapshot.potentialSavings))
      findings.push({
        level: "ok",
        area: "UI.overview",
        message: `总览对齐：季度 ${snapshot.latestQuarterPeriod} 折扣率 ${snapshot.latestQuarterRate}，节省 ${snapshot.latestQuarterDiscount}，建议 ${snapshot.suggestionCountText}，异常 ${snapshot.anomalyCountText}`,
      })

      for (const tab of DISCOUNT_TABS) {
        const tabBtn = page.getByRole("tab", { name: tab }).or(page.getByRole("button", { name: tab }))
        await expect(tabBtn.first()).toBeVisible({ timeout: 10000 })
        await tabBtn.first().click({ timeout: 5000 })
        await page.waitForTimeout(1800)
        const body = await assertNoCrash(page, `折扣Tab-${tab}`)

        if (tab === "总览") {
          expect(body).toMatch(/最新季度折扣率|季度总节省|优化机会|异常检测/)
          expect(body).toContain(String(snapshot.latestQuarterRate))
        }
        if (tab === "时间分析") {
          expect(body).toMatch(/季度|年度|异常|折扣/)
        }
        if (tab === "产品分析") {
          expect(body).toMatch(/产品|折扣率|ECS|云服务器|趋势/)
          if (snapshot.topProduct) {
            expect(body.includes(String(snapshot.topProduct)) || body.includes("云服务器")).toBeTruthy()
          }
        }
        if (tab === "区域分析") {
          expect(body).toMatch(/区域|中国香港|折扣/)
          if (snapshot.topRegion) {
            expect(body).toContain(String(snapshot.topRegion))
          }
          expect(body).toContain(String(snapshot.topRegionRate))
        }
        if (tab === "计费分析") {
          expect(body).toMatch(/包年包月|按量|优化|建议|折扣率/)
        }
        if (tab === "高级分析") {
          await expect(page.getByText(/累计总折扣|折扣率移动平均|累计折扣金额/).first()).toBeVisible({ timeout: 60000 })
          const advancedBody = await page.locator("body").innerText()
          expect(advancedBody).toContain(String(snapshot.totalDiscount))
          // 卡片月均应按实际序列长度
          expect(advancedBody).toContain(String(snapshot.monthlyAverageBySeries))
          // 不应再出现硬编码 19 个月的错误文案
          expect(advancedBody).not.toMatch(/19个月/)
          findings.push({
            level: "ok",
            area: "UI.advanced",
            message: `高级分析对齐累计总折扣 ${snapshot.totalDiscount}，月均 ${snapshot.monthlyAverageBySeries}`,
          })
        }

        console.log("  tab", tab)
        await page.screenshot({ path: join(SCREENSHOT_DIR, `discount-tab-${tab}.png`) })
      }
    })

    // 写出审计报告，便于人工复核
    const reportPath = join(SCREENSHOT_DIR, "discount-audit-report.json")
    const fails = findings.filter((f) => f.level === "fail")
    const warns = findings.filter((f) => f.level === "warn")
    writeFileSync(
      reportPath,
      JSON.stringify({ account: ACCOUNT, snapshot, findings, failCount: fails.length, warnCount: warns.length }, null, 2),
      "utf-8"
    )

    expect(fails, `存在失败项: ${fails.map((f) => f.message).join(" | ")}`).toHaveLength(0)

    // 控制台摘要
    console.log("==== 折扣审计摘要 ====")
    for (const f of findings) {
      console.log(`[${f.level}] ${f.area}: ${f.message}`)
    }
    console.log("报告:", reportPath)
  })
})
