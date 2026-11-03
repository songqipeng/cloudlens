#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="$ROOT/artifacts/product-demo"
mkdir -p "$OUT_DIR"
LOG="$OUT_DIR/cli-demo.log"
export E2E_AUTH_ACCOUNT="${E2E_AUTH_ACCOUNT:-cf}"
export PYTHONUNBUFFERED=1
# 过滤掉超长 JSON / 噪声，保留可读演示输出
bash "$ROOT/scripts/product-demo/cli-walkthrough.sh" 2>&1 \
  | sed -E 's/\x1b\[[0-9;]*[a-zA-Z]//g' \
  | tee "$LOG"
echo "CLI log saved: $LOG"
