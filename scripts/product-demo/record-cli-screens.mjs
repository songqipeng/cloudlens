#!/usr/bin/env node
import { createRequire } from "module"
import { existsSync, mkdirSync, readFileSync, writeFileSync, readdirSync } from "fs"
import { join, dirname } from "path"
import { fileURLToPath } from "url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, "../..")
const require = createRequire(join(ROOT, "web/frontend/package.json"))
const { chromium } = require("playwright")

const OUT = join(ROOT, "artifacts/product-demo/cli-frames")
const LOG_PATH = join(ROOT, "artifacts/product-demo/cli-demo.log")
mkdirSync(OUT, { recursive: true })
if (!existsSync(LOG_PATH)) {
  console.error("缺少", LOG_PATH)
  process.exit(1)
}

const raw = readFileSync(LOG_PATH, "utf-8")
const lines = raw.split(/\r?\n/)
const capped = lines.length > 240 ? lines.slice(0, 240).join("\n") + "\n…（完整见 cli-demo.log）" : raw

const browser = await chromium.launch({ channel: "chrome", headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
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

let frame = 0
async function shot() {
  frame += 1
  await page.screenshot({
    path: join(OUT, `frame-${String(frame).padStart(4, "0")}.png`),
    type: "png",
  })
}

await page.waitForTimeout(600)
await shot()

await page.evaluate(async (text) => {
  window.__clLines = text.split("\n")
  window.__clIdx = 0
  window.__clBuf = ""
  window.__clDone = false
}, capped)

// 逐步追加行并截图（控制帧数：每 2 行一帧，命令行单独帧）
while (true) {
  const status = await page.evaluate(() => {
    if (window.__clDone) return { done: true }
    const lines = window.__clLines
    const i = window.__clIdx
    if (i >= lines.length) {
      window.__clDone = true
      document.getElementById("cap").innerHTML =
        "CLI 演示结束<small>完整日志: artifacts/product-demo/cli-demo.log</small>"
      return { done: true }
    }
    const batch = []
    let j = i
    // 命令行单独一批，其它合并最多 3 行
    if ((lines[j] || "").startsWith("$") || (lines[j] || "").includes("════")) {
      batch.push(lines[j])
      j += 1
      if (j < lines.length && !(lines[j] || "").startsWith("$") && !(lines[j] || "").includes("════")) {
        batch.push(lines[j])
        j += 1
      }
    } else {
      for (let k = 0; k < 3 && j < lines.length; k++, j++) {
        if ((lines[j] || "").startsWith("$") || (lines[j] || "").includes("════")) break
        batch.push(lines[j])
      }
      if (!batch.length) {
        batch.push(lines[j])
        j += 1
      }
    }
    for (const line of batch) {
      if ((line || "").includes("════")) {
        const title = (lines[j] || line).replace(/[═]/g, "").trim()
        if (title) {
          document.getElementById("cap").innerHTML = `${title.slice(0, 90)}<small>真实 CLI 输出回放</small>`
        }
      }
      window.__clBuf += (window.__clBuf ? "\n" : "") + line
    }
    window.__clIdx = j
    const term = document.getElementById("term")
    term.textContent = window.__clBuf
    term.scrollTop = term.scrollHeight
    return { done: false, idx: j, total: lines.length }
  })
  await shot()
  if (status.done) break
  if (frame > 320) break
}

// 结尾多留几帧
for (let i = 0; i < 4; i++) await shot()

await context.close()
await browser.close()
writeFileSync(join(OUT, "count.txt"), String(frame))
console.log(`CLI frames=${frame} dir=${OUT} png=${readdirSync(OUT).filter((f) => f.endsWith(".png")).length}`)
