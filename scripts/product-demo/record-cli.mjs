#!/usr/bin/env node
import { createRequire } from "module"
import { existsSync, mkdirSync, readFileSync, copyFileSync, readdirSync, statSync } from "fs"
import { join, dirname } from "path"
import { fileURLToPath } from "url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, "../..")
const require = createRequire(join(ROOT, "web/frontend/package.json"))
const { chromium } = require("playwright")
const OUT = join(ROOT, "artifacts/product-demo")
const VIDEO_DIR = join(OUT, "cli-raw")
const LOG_PATH = join(OUT, "cli-demo.log")
mkdirSync(VIDEO_DIR, { recursive: true })

if (!existsSync(LOG_PATH)) {
  console.error("缺少", LOG_PATH, "请先运行 capture-cli-log.sh")
  process.exit(1)
}

const raw = readFileSync(LOG_PATH, "utf-8")
const lines = raw.split(/\r?\n/)
const capped =
  lines.length > 240
    ? lines.slice(0, 240).join("\n") + "\n…（完整输出见 cli-demo.log）"
    : raw

let browser
try {
  browser = await chromium.launch({ headless: true })
} catch (e) {
  console.warn("bundled chromium unavailable, fallback to system chrome:", e.message)
  browser = await chromium.launch({ channel: "chrome", headless: true })
}
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: { dir: VIDEO_DIR, size: { width: 1440, height: 900 } },
})
const page = await context.newPage()

await page.setContent(`<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;background:#0b1020;color:#d7e0ff;font-family:ui-monospace,Menlo,Monaco,Consolas,monospace}
.frame{display:flex;flex-direction:column;height:100%}
.bar{display:flex;align-items:center;gap:8px;padding:12px 16px;background:#121833;border-bottom:1px solid #243056}
.dot{width:10px;height:10px;border-radius:50%}.r{background:#ff5f57}.y{background:#febc2e}.g{background:#28c840}
.title{margin-left:12px;font-weight:600;font-size:14px;color:#9eb1ff}
#term{flex:1;padding:18px 20px;overflow:auto;white-space:pre-wrap;word-break:break-word;font-size:13px;line-height:1.45}
.caption{position:fixed;left:20px;bottom:18px;max-width:70vw;padding:12px 16px;border-radius:12px;
background:rgba(8,12,24,.9);border:1px solid rgba(99,140,255,.45);font:600 15px/1.4 system-ui,sans-serif;color:#fff}
.caption small{display:block;font-weight:400;opacity:.85;margin-top:4px;font-size:12px}
</style></head><body>
<div class="frame">
  <div class="bar"><span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
  <span class="title">CloudLens CLI · 核心功能演示</span></div>
  <pre id="term"></pre>
</div>
<div class="caption" id="cap">CloudLens CLI<small>config · query · analyze · bill · savings</small></div>
</body></html>`)

await page.waitForTimeout(1500)
await page.evaluate(async (text) => {
  const term = document.getElementById("term")
  const cap = document.getElementById("cap")
  const chunks = text.split("\n")
  let buf = ""
  for (let i = 0; i < chunks.length; i++) {
    const line = chunks[i]
    if (line.includes("════")) {
      const title = (chunks[i + 1] || line).replace(/[═]/g, "").trim()
      if (title) cap.innerHTML = `${title.slice(0, 90)}<small>真实 CLI 输出回放</small>`
    }
    buf += (i === 0 ? "" : "\n") + line
    term.textContent = buf
    term.scrollTop = term.scrollHeight
    const delay = line.startsWith("$") ? 380 : line.includes("════") ? 600 : 48
    await new Promise((r) => setTimeout(r, delay))
  }
  cap.innerHTML = `CLI 演示结束<small>完整日志: artifacts/product-demo/cli-demo.log</small>`
}, capped)
await page.waitForTimeout(3000)

await context.close()
await browser.close()

const files = readdirSync(VIDEO_DIR)
  .filter((f) => f.endsWith(".webm"))
  .map((f) => join(VIDEO_DIR, f))
  .sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs)
const dest = join(OUT, "cli-demo.webm")
copyFileSync(files[0], dest)
console.log("CLI VIDEO:", dest, "bytes", statSync(dest).size)
