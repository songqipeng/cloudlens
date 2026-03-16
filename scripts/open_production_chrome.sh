#!/usr/bin/env bash
# 用 Chrome 打开生产环境（必须用 HTTP，当前 ALB 未配置 HTTPS）
set -e
URL="http://cloudlens.songqipeng.com"
echo "用 Chrome 打开: $URL"
echo "说明: 当前仅支持 HTTP。若浏览器自动跳到 https 会无法访问，请手动改为 http://"
if [[ "$(uname)" == "Darwin" ]]; then
  open -a "Google Chrome" "$URL" 2>/dev/null || open -a "Chromium" "$URL" 2>/dev/null || open "$URL"
else
  xdg-open "$URL" 2>/dev/null || echo "请手动在浏览器打开: $URL"
fi
