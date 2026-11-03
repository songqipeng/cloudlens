#!/usr/bin/env bash
# 启动 CloudLens 本地 Docker 调试环境
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p logs

release_port() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "${pids}" ]]; then
    echo "释放本机端口 ${port}（PID: ${pids}）"
    # shellcheck disable=SC2086
    kill ${pids} 2>/dev/null || true
    sleep 1
  fi
}

echo "=== CloudLens 本地 Docker 调试 ==="
release_port 3000
release_port 8000
release_port 5678

echo "构建并启动容器（首次会较慢）..."
echo "  前端: http://localhost:3000"
echo "  后端: http://localhost:8000/docs"
echo "  调试: localhost:5678"
echo

exec docker compose -f docker-compose.dev.yml up --build "$@"
