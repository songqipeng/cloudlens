#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/artifacts/product-demo"
FPS="${FPS:-1.25}"

echo "生成章节卡 PNG…"
"$ROOT/.venv/bin/python" "$ROOT/scripts/product-demo/make-cards.py"

png_card_mp4() {
  local png="$1" out="$2" secs="$3"
  ffmpeg -y -loop 1 -i "$png" -t "$secs" -r 30 \
    -vf "scale=1600:1000:force_original_aspect_ratio=decrease,pad=1600:1000:(ow-iw)/2:(oh-ih)/2:color=0x0b1020" \
    -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$out" </dev/null
}

frames_mp4() {
  local dir="$1" out="$2"
  local n
  n=$(ls "$dir"/frame-*.png 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$n" -lt 1 ]]; then
    echo "ERROR: no frames in $dir"
    return 1
  fi
  echo "编码 $dir ($n frames @ ${FPS}fps) → $out"
  ffmpeg -y -framerate "$FPS" -i "$dir/frame-%04d.png" \
    -vf "scale=1600:1000:force_original_aspect_ratio=decrease,pad=1600:1000:(ow-iw)/2:(oh-ih)/2:color=0x0b1020,fps=30" \
    -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$out" </dev/null
}

png_card_mp4 "$OUT/card-intro.png" "$OUT/card-intro.mp4" 4
png_card_mp4 "$OUT/card-web.png" "$OUT/card-web.mp4" 3
png_card_mp4 "$OUT/card-cli.png" "$OUT/card-cli.mp4" 3
png_card_mp4 "$OUT/card-outro.png" "$OUT/card-outro.mp4" 4

frames_mp4 "$OUT/web-frames" "$OUT/web-demo.mp4"
frames_mp4 "$OUT/cli-frames" "$OUT/cli-demo.mp4"

LIST="$OUT/concat.txt"
{
  echo "file '$OUT/card-intro.mp4'"
  echo "file '$OUT/card-web.mp4'"
  echo "file '$OUT/web-demo.mp4'"
  echo "file '$OUT/card-cli.mp4'"
  echo "file '$OUT/cli-demo.mp4'"
  echo "file '$OUT/card-outro.mp4'"
} > "$LIST"

FINAL="$OUT/CloudLens-产品使用演示.mp4"
echo "拼接最终片…"
ffmpeg -y -f concat -safe 0 -i "$LIST" -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$FINAL" </dev/null
ls -lh "$FINAL" "$OUT/web-demo.mp4" "$OUT/cli-demo.mp4"
echo -n "时长(秒): "
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$FINAL" || true
echo "DONE: $FINAL"
