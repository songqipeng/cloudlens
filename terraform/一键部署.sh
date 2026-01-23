#!/bin/bash
# CloudLens 一键部署脚本

set -e

echo "🚀 CloudLens AWS 一键部署"
echo "=========================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Terraform
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform未安装${NC}"
    echo ""
    echo "安装方法:"
    echo "  macOS: brew install terraform"
    echo "  Linux: 从 https://www.terraform.io/downloads 下载"
    exit 1
fi

# 检查AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI未安装${NC}"
    echo ""
    echo "安装方法:"
    echo "  macOS: brew install awscli"
    echo "  Linux: pip install awscli"
    exit 1
fi

# 检查AWS凭证
echo "🔐 检查AWS凭证..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${YELLOW}⚠️  AWS凭证未配置${NC}"
    echo ""
    echo "请运行: aws configure"
    echo "需要输入:"
    echo "  - AWS Access Key ID"
    echo "  - AWS Secret Access Key"
    echo "  - Default region (ap-northeast-1 或 ap-east-1)"
    echo "  - Default output format (json)"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "未设置")
echo -e "${GREEN}✅ AWS凭证已配置${NC}"
echo "   账户ID: $ACCOUNT_ID"
echo "   区域: $REGION"
echo ""

# 进入terraform目录
cd "$(dirname "$0")"
SCRIPT_DIR=$(pwd)

# 检查terraform.tfvars
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${YELLOW}📝 创建配置文件...${NC}"
    if [ -f "terraform.tfvars.example" ]; then
        cp terraform.tfvars.example terraform.tfvars
        echo -e "${GREEN}✅ 已创建 terraform.tfvars${NC}"
        echo ""
        echo -e "${YELLOW}⚠️  请编辑 terraform.tfvars，填写以下信息:${NC}"
        echo "   1. aws_region = 'ap-northeast-1' (日本) 或 'ap-east-1' (香港)"
        echo "   2. domain_name = 'cloudlens.songqipeng.com'"
        echo "   3. mysql_password = 'YOUR_SECURE_PASSWORD'"
        echo "   4. ssh_public_key = 'YOUR_SSH_PUBLIC_KEY'"
        echo ""
        read -p "按Enter继续编辑配置文件..."
        
        # 尝试打开编辑器
        if command -v nano &> /dev/null; then
            nano terraform.tfvars
        elif command -v vim &> /dev/null; then
            vim terraform.tfvars
        else
            echo "请手动编辑 terraform.tfvars"
        fi
    else
        echo -e "${RED}❌ terraform.tfvars.example 不存在${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ terraform.tfvars 已存在${NC}"
fi

# 初始化Terraform
echo ""
echo "🔧 初始化Terraform..."
terraform init

# 检查部署计划
echo ""
echo "📋 检查部署计划..."
terraform plan

echo ""
echo -e "${YELLOW}⚠️  请检查上述计划，确认无误后继续${NC}"
read -p "是否继续部署？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "已取消部署"
    exit 0
fi

# 执行部署
echo ""
echo "🚀 开始部署..."
terraform apply -auto-approve

# 显示输出
echo ""
echo "=========================="
echo -e "${GREEN}✅ 部署完成！${NC}"
echo "=========================="
echo ""
terraform output

echo ""
echo "📝 下一步:"
echo "   1. 等待几分钟让服务启动"
echo "   2. 访问: $(terraform output -raw domain_name 2>/dev/null || echo 'https://cloudlens.songqipeng.com')"
echo "   3. SSH连接: $(terraform output -raw ssh_command 2>/dev/null || echo '查看上方输出')"
echo ""
