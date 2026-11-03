#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/artifacts/product-demo"
mkdir -p "$OUT"

FONT="/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
WEB_WEBM="$OUT/web-demo.webm"
CLI_WEBM="$OUT/cli-demo.webm"

make_card() {
  local file="$1" title="$2" sub="$3" secs="$4"
  ffmpeg -y -f lavfi -i "color=c=0x0b1020:s=1600x1000:d=${secs}" \
    -vf "drawtext=fontfile=${FONT}:text='${title}':fontcolor=white:fontsize=42:x=(w-text_w)/2:y=(h-text_h)/2-36,drawtext=fontfile=${FONT}:text='${sub}':fontcolor=0xa8b8ff:fontsize=22:x=(w-text_w)/2:y=(h-text_h)/2+36" \
    -c:v libx264 -pix_fmt yuv420p -r 30 "$file" </dev/null
}

to_mp4() {
  local in="$1" out="$2"
  ffmpeg -y -i "$in" -c:v libx264 -pix_fmt yuv420p -r 30 \
    -vf "scale=1600:1000:force_original_aspect_ratio=decrease,pad=1600:1000:(ow-iw)/2:(oh-ih)/2:color=0x0b1020" \
    "$out" </dev/null
}

echo "生成片头片尾…"
make_card "$OUT/card-intro.mp4" "CloudLens 产品使用演示" "Web 全功能 + CLI 核心功能 | 现有账号数据" 4
make_card "$OUT/card-web.mp4" "第一部分  Web 控制台" "仪表盘 / 资源 / 成本 / 折扣 / 省钱机会 / 安全 / 报告 / 设置" 3
make_card "$OUT/card-cli.mp4" "第二部分  CLI 命令行" "config / query / analyze / bill / savings" 3
make_card "$OUT/card-outro.mp4" "演示结束 谢谢观看" "docs/USER_GUIDE.md  |  cloudlens.songqipeng.com" 4

LIST="$OUT/concat.txt"
{
  echo "file '$OUT/card-intro.mp4'"
  echo "file '$OUT/card-web.mp4'"
} > "$LIST"

if [[ -f "$WEB_WEBM" ]]; then
  echo "转码 Web…"
  to_mp4 "$WEB_WEBM" "$OUT/web-demo.mp4"
  echo "file '$OUT/web-demo.mp4'" >> "$LIST"
else
  echo "WARNING: 缺少 $WEB_WEBM"
fi

echo "file '$OUT/card-cli.mp4'" >> "$LIST"
if [[ -f "$CLI_WEBM" ]]; then
  echo "转码 CLI…"
  to_mp4 "$CLI_WEBM" "$OUT/cli-demo.mp4"
  echo "file '$OUT/cli-demo.mp4'" >> "$LIST"
else
  echo "WARNING: 缺少 $CLI_WEBM"
fi

echo "file '$OUT/card-outro.mp4'" >> "$LIST"

FINAL="$OUT/CloudLens-产品使用演示.mp4"
echo "拼接最终视频…"
ffmpeg -y -f concat -safe 0 -i "$LIST" -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$FINAL" </dev/null
ls -lh "$FINAL" "$WEB_WEBM" "$CLI_WEBM" 2>/dev/null || true
echo "DONE: $FINAL"
