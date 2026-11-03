/**
 * CloudLens CLI 演示视频：把真实 CLI 日志以打字机效果呈现在终端 UI 中并录制。
 *
 * 依赖：先运行 scripts/product-demo/capture-cli-log.sh 生成 artifacts/product-demo/cli-demo.log
 */
import { test, expect } from "@playwright/test"
import { existsSync, mkdirSync, readFileSync } from "fs"
import { join } from "path"

const ROOT = join(process.cwd(), "..", "..")
const LOG_PATH = join(ROOT, "artifacts", "product-demo", "cli-demo.log")
const OUT_DIR = join(process.cwd(), "test-recordings", "product-demo-cli")

mkdirSync(OUT_DIR, { recursive: true })

test.describe.configure({ mode: "serial" })

test.describe("CloudLens 产品使用演示（CLI）", () => {
  test.use({ viewport: { width: 1440, height: 900 } })
  test.setTimeout(600000)

  test("终端打字机回放 CLI 核心命令", async ({ page }) => {
    test.skip(!existsSync(LOG_PATH), `缺少 CLI 日志: ${LOG_PATH}，请先运行 capture-cli-log.sh`)

    const raw = readFileSync(LOG_PATH, "utf-8")
    // 控制时长：截断过长日志，保留关键段落
    const lines = raw.split(/\r?\n/)
    const capped = lines.length > 220 ? lines.slice(0, 220).join("\n") + "\n…（输出已截断，完整见 cli-demo.log）" : raw

    await page.setContent(`<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<title>CloudLens CLI Demo</title>
<style>
  html,body{margin:0;height:100%;background:#0b1020;color:#d7e0ff;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}
  .frame{display:flex;flex-direction:column;height:100%}
  .bar{display:flex;align-items:center;gap:8px;padding:12px 16px;background:#121833;border-bottom:1px solid #243056}
  .dot{width:10px;height:10px;border-radius:50%}
  .r{background:#ff5f57}.y{background:#febc2e}.g{background:#28c840}
  .title{margin-left:12px;font-weight:600;font-size:14px;color:#9eb1ff}
  #term{flex:1;padding:18px 20px;overflow:auto;white-space:pre-wrap;word-break:break-word;font-size:13px;line-height:1.45}
  .cursor{display:inline-block;width:8px;height:14px;background:#7aa2ff;margin-left:2px;vertical-align:-2px;animation:blink 1s step-end infinite}
  @keyframes blink{50%{opacity:0}}
  .caption{position:fixed;left:20px;bottom:18px;max-width:70vw;padding:12px 16px;border-radius:12px;
    background:rgba(8,12,24,.9);border:1px solid rgba(99,140,255,.45);font:600 15px/1.4 system-ui,sans-serif}
  .caption small{display:block;font-weight:400;opacity:.85;margin-top:4px;font-size:12px}
</style>
</head>
<body>
  <div class="frame">
    <div class="bar"><span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
      <span class="title">CloudLens CLI · 核心功能演示</span></div>
    <pre id="term"></pre>
  </div>
  <div class="caption" id="cap">CloudLens CLI<div><small>config · query · analyze · bill · savings</small></div></div>
</body>
</html>`)

    await page.waitForTimeout(1800)

    await page.evaluate(async (text) => {
      const term = document.getElementById("term")!
      const cap = document.getElementById("cap")!
      const chunks = text.split("\n")
      let buf = ""
      for (let i = 0; i < chunks.length; i++) {
        const line = chunks[i]
        if (line.includes("════") || line.match(/^\s*\d\)/)) {
          const title = line.replace(/[═]/g, "").trim() || chunks[i + 1] || "CLI"
          cap.innerHTML = `${title.slice(0, 80)}<small>真实命令输出回放</small>`
        }
        buf += (i === 0 ? "" : "\n") + line
        term.textContent = buf
        term.scrollTop = term.scrollHeight
        // 章节行稍慢，普通行较快
        const delay = line.startsWith("$") ? 420 : line.includes("════") ? 700 : 55
        await new Promise((r) => setTimeout(r, delay))
      }
      cap.innerHTML = `CLI 演示结束<small>完整日志见 artifacts/product-demo/cli-demo.log</small>`
    }, capped)

    await page.waitForTimeout(3500)
    await page.screenshot({ path: join(OUT_DIR, "cli-finale.png") })
  })
})
