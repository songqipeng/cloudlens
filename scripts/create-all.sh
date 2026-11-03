#!/usr/bin/env bash
# 一键创建所有 Terraform 管理的资源，并可选地更新阿里云 DNS 解析到新 IP
# 使用前请确认：已配置 Terraform、AWS 凭证；若需 DNS 联动，请配置阿里云凭证（见 docs/阿里云DNS联动与一键销毁创建.md）

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TERRAFORM_DIR="${REPO_ROOT}/terraform"
SCRIPT_DIR="$REPO_ROOT/scripts"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "   CloudLens 一键创建资源"
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

cd "$TERRAFORM_DIR"
terraform init -input=false
terraform apply -auto-approve

# 获取新实例公网 IP
NEW_IP=$(terraform output -raw instance_public_ip 2>/dev/null || true)
if [[ -z "$NEW_IP" ]]; then
  echo -e "${YELLOW}未获取到 instance_public_ip，请检查 terraform output。${NC}"
  echo "创建完成。若需手动更新阿里云解析，请执行:"
  echo "  ALIYUN_ACCESS_KEY_ID=xxx ALIYUN_ACCESS_KEY_SECRET=xxx python3 scripts/aliyun_dns_update.py --domain 你的主域名 --rr cloudlens --ip <新IP>"
  exit 0
fi

echo ""
echo -e "${GREEN}资源已创建，公网 IP: $NEW_IP${NC}"

# 若存在 scripts/.env.aliyun 或环境变量已配置，则更新阿里云解析（aliyun_dns_update.py 会自行读取 .env.aliyun）
if [[ -f "$SCRIPT_DIR/.env.aliyun" ]] || [[ -n "$ALIYUN_ACCESS_KEY_ID" && -n "$ALIYUN_DNS_DOMAIN" ]]; then
  echo "正在更新阿里云解析 -> $NEW_IP"
  if (cd "$REPO_ROOT" && python3 "$SCRIPT_DIR/aliyun_dns_update.py" --ip "$NEW_IP"); then
    echo -e "${GREEN}域名解析已更新。${NC}"
  else
    echo -e "${YELLOW}域名解析更新失败，请检查 scripts/.env.aliyun 或环境变量，或手动执行: python3 scripts/aliyun_dns_update.py --domain 主域名 --rr 子域名 --ip $NEW_IP${NC}"
  fi
else
  echo "提示：创建 scripts/.env.aliyun（参考 .env.aliyun.example）或设置阿里云环境变量后，可自动更新域名解析，详见 docs/阿里云DNS联动与一键销毁创建.md"
fi

echo ""
echo "SSH 连接: terraform -chdir=$TERRAFORM_DIR output -raw ssh_command"
