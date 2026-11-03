/**
 * 等「主内容区」数据就绪，忽略侧栏常驻导航文案。
 * 策略：loading/spinner 消失 + 期望文案出现在 main + 短网络空闲。
 * 真实等待可很长；录制只在就绪后截帧，成片相当于跳过转圈（快进）。
 */

function mainTextExpr() {
  return `(() => {
    const main =
      document.querySelector("main") ||
      document.querySelector("[class*='max-w']") ||
      document.querySelector(".p-6, .p-8, [class*='DashboardLayout']") ||
      document.body
    // 去掉侧栏：优先取 main 内文本
    return (main && main.innerText) || document.body.innerText || ""
  })()`
}

export async function waitLoaded(page, {
  expectText = null,
  timeout = 180000,
  idleMs = 1000,
  allowEmptyOk = false,
} = {}) {
  const start = Date.now()
  const deadline = start + timeout

  await page.waitForLoadState("domcontentloaded", { timeout: Math.min(30000, timeout) }).catch(() => {})

  // 等全屏/主区 loading 消失
  await page
    .waitForFunction(
      () => {
        const pick = () => {
          const main =
            document.querySelector("main") ||
            document.querySelector(".p-6") ||
            document.querySelector(".p-8") ||
            document.body
          return (main && main.innerText) || ""
        }
        const text = pick()
        // 明显的加载态
        if (/正在加载|正在扫描|请稍候|Loading…|Loading\.\.\.|Scanning/i.test(text)) {
          // 若同时已有实质内容（如年化可省数字），可放过
          if (!/年化可省合计|本月成本|资源列表|折扣趋势|安全评分|预算列表|报告类型|框架合同|暂无|无数据/.test(text)) {
            return false
          }
        }
        const spinners = [...document.querySelectorAll(".animate-spin, [aria-busy='true']")]
        for (const el of spinners) {
          const r = el.getBoundingClientRect()
          // 主视口内较大 spinner
          if (r.width >= 24 && r.height >= 24 && r.top < window.innerHeight * 0.85 && r.bottom > 80) {
            return false
          }
        }
        return true
      },
      null,
      { timeout: Math.max(8000, deadline - Date.now()) }
    )
    .catch(() => {})

  // API 流量缓和
  await page
    .waitForLoadState("networkidle", {
      timeout: Math.min(45000, Math.max(5000, deadline - Date.now())),
    })
    .catch(() => {})
  await page.waitForTimeout(idleMs)

  if (expectText) {
    const reSrc = expectText.source || String(expectText)
    await page
      .waitForFunction(
        (src) => {
          const main =
            document.querySelector("main") ||
            document.querySelector(".p-6") ||
            document.querySelector(".p-8") ||
            document.body
          const text = (main && main.innerText) || ""
          return new RegExp(src, "i").test(text)
        },
        reSrc,
        { timeout: Math.max(10000, deadline - Date.now()) }
      )
      .catch(() => {})
  }

  // 再确认：若仍只有「加载中」则继续等一会
  for (let i = 0; i < 8; i++) {
    const text = await page.evaluate(() => {
      const main =
        document.querySelector("main") ||
        document.querySelector(".p-6") ||
        document.querySelector(".p-8") ||
        document.body
      return (main && main.innerText) || ""
    })
    const loadingOnly =
      /正在加载|正在扫描省钱机会|Loading/i.test(text) &&
      !/年化可省合计|本月成本|资源列表|ECS|折扣|安全评分|预算|报告|设置|框架合同|暂无|无数据|Empty/i.test(
        text
      )
    if (!loadingOnly) break
    if (Date.now() > deadline) break
    await page.waitForTimeout(2000)
  }

  const body = await page.evaluate(() => {
    const main =
      document.querySelector("main") ||
      document.querySelector(".p-6") ||
      document.querySelector(".p-8") ||
      document.body
    return (main && main.innerText) || ""
  })

  if (!allowEmptyOk && /Application error|client-side exception|Internal Server Error/i.test(body)) {
    throw new Error("页面错误: " + body.slice(0, 120))
  }

  return {
    waitedMs: Date.now() - start,
    preview: body.slice(0, 100).replace(/\s+/g, " "),
  }
}
