#!/usr/bin/env bash
# 一键销毁所有 Terraform 管理的资源（不调试/不演示时节省成本）
# 使用前请确认：已配置 Terraform 与 AWS 凭证；销毁后如需再使用请执行 scripts/create-all.sh

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TERRAFORM_DIR="${REPO_ROOT}/terraform"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "   CloudLens 一键销毁资源"
echo "=========================================="
echo ""

if [[ ! -d "$TERRAFORM_DIR" ]]; then
  echo -e "${RED}未找到 terraform 目录: $TERRAFORM_DIR${NC}"
  exit 1
fi

if ! command -v terraform &> /dev/null; then
  echo -e "${RED}未安装 Terraform，请先安装 (如 brew install terraform)${NC}"
  exit 1
fi

echo -e "${YELLOW}即将销毁当前 Terraform 管理的所有资源（如 EC2 等）。${NC}"
echo "如需恢复，请执行: ./scripts/create-all.sh"
echo ""
read -p "确认销毁？输入 yes 继续: " confirm
if [[ "$confirm" != "yes" ]]; then
  echo "已取消"
  exit 0
fi

cd "$TERRAFORM_DIR"
terraform init -input=false
terraform destroy -auto-approve

echo ""
echo -e "${GREEN}资源已销毁。${NC}"
echo "需要演示或调试时请执行: ./scripts/create-all.sh"
