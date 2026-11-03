#!/usr/bin/env bash
# 本机 CLI 连接 Docker 调试库（MySQL 映射在 3307）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export CLOUDLENS_DATABASE__DB_TYPE="${CLOUDLENS_DATABASE__DB_TYPE:-mysql}"
export CLOUDLENS_DATABASE__MYSQL_HOST="${CLOUDLENS_DATABASE__MYSQL_HOST:-127.0.0.1}"
export CLOUDLENS_DATABASE__MYSQL_PORT="${CLOUDLENS_DATABASE__MYSQL_PORT:-3307}"
export CLOUDLENS_DATABASE__MYSQL_USER="${CLOUDLENS_DATABASE__MYSQL_USER:-cloudlens}"
export CLOUDLENS_DATABASE__MYSQL_PASSWORD="${CLOUDLENS_DATABASE__MYSQL_PASSWORD:-cloudlens123}"
export CLOUDLENS_DATABASE__MYSQL_DATABASE="${CLOUDLENS_DATABASE__MYSQL_DATABASE:-cloudlens}"
export MYSQL_SSL_DISABLED="${MYSQL_SSL_DISABLED:-true}"

PYTHON=""
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "未找到 Python，请先创建 .venv"
  exit 1
fi

if [[ $# -eq 0 ]]; then
  echo "用法: bash scripts/cl-dev.sh analyze discount --use-db --account cf"
  echo "      bash scripts/cl-dev.sh bill stats"
  exec "$PYTHON" "$ROOT/cl" --help
fi

exec "$PYTHON" "$ROOT/cl" "$@"
