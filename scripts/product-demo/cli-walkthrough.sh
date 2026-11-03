#!/usr/bin/env bash
# CloudLens CLI 核心功能演示（对接本地 docker-compose.dev MySQL 3307）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
export MYSQL_PORT="${MYSQL_PORT:-3307}"
export MYSQL_USER="${MYSQL_USER:-cloudlens}"
export MYSQL_PASSWORD="${MYSQL_PASSWORD:-cloudlens123}"
export MYSQL_DATABASE="${MYSQL_DATABASE:-cloudlens}"
export CLOUDLENS_DATABASE__MYSQL_HOST="${CLOUDLENS_DATABASE__MYSQL_HOST:-127.0.0.1}"
export CLOUDLENS_DATABASE__MYSQL_PORT="${CLOUDLENS_DATABASE__MYSQL_PORT:-3307}"
export CLOUDLENS_DATABASE__MYSQL_USER="${CLOUDLENS_DATABASE__MYSQL_USER:-cloudlens}"
export CLOUDLENS_DATABASE__MYSQL_PASSWORD="${CLOUDLENS_DATABASE__MYSQL_PASSWORD:-cloudlens123}"
export CLOUDLENS_DATABASE__MYSQL_DATABASE="${CLOUDLENS_DATABASE__MYSQL_DATABASE:-cloudlens}"
export PYTHONUNBUFFERED=1

CL="${CL:-$ROOT/.venv/bin/python -m cloudlens.cli.main}"
ACC="${E2E_AUTH_ACCOUNT:-cf}"

pause() { sleep "${1:-1.0}"; }

banner() {
  echo
  echo "════════════════════════════════════════════════════════"
  echo "  $1"
  echo "════════════════════════════════════════════════════════"
  echo
  pause 1.2
}

run() {
  echo "\$ $*"
  pause 0.3
  # shellcheck disable=SC2086
  eval "$@" || true
  pause 1.2
}

banner "CloudLens CLI 产品演示 · 核心功能"
echo "账号: $ACC"
echo "MySQL: ${CLOUDLENS_DATABASE__MYSQL_HOST}:${CLOUDLENS_DATABASE__MYSQL_PORT}"
pause 1.5

banner "1) 查看 CLI 概览"
run "$CL --help"

banner "2) 配置管理 · 列出云账号"
run "$CL config list"

banner "3) 资源查询 · ECS"
run "$CL query resources $ACC ecs --format table 2>&1 | head -40"

banner "4) 闲置资源分析"
run "$CL analyze idle -a $ACC 2>&1 | head -50"

banner "5) 成本分析"
run "$CL analyze cost -a $ACC 2>&1 | head -40"

banner "6) 账单 · 测试连接"
run "$CL bill test --account $ACC --limit 3 2>&1 | head -35"

banner "7) 省钱机会扫描（框架合同 + 年化可省）"
run "$CL savings scan -a $ACC --no-legacy 2>&1 | head -60"

banner "8) 框架合同列表"
run "$CL savings contracts -a $ACC 2>&1 | head -40"

banner "演示结束 · 更多命令: cl --help / cl analyze --help / cl savings --help"
pause 1.5
