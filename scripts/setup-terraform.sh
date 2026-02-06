#!/bin/bash
# Terraform环境设置脚本

set -e

echo "🚀 CloudLens Terraform环境设置"
echo "================================"
echo ""

# 检查Terraform
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform未安装"
    echo ""
    echo "安装方法:"
    echo "  macOS: brew install terraform"
    echo "  Linux: 从 https://www.terraform.io/downloads 下载"
    echo "  Windows: choco install terraform"
    exit 1
fi

echo "✅ Terraform已安装: $(terraform version | head -1)"
echo ""

# 检查AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI未安装"
    echo ""
    echo "安装方法:"
    echo "  macOS: brew install awscli"
    echo "  Linux: pip install awscli"
    exit 1
fi

echo "✅ AWS CLI已安装: $(aws --version)"
echo ""

# 检查AWS凭证
echo "🔐 检查AWS凭证配置..."
if aws sts get-caller-identity &> /dev/null; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo "✅ AWS凭证已配置"
    echo "   账户ID: $ACCOUNT_ID"
    echo "   区域: $(aws configure get region || echo '未设置，将使用默认值')"
else
    echo "❌ AWS凭证未配置或无效"
    echo ""
    echo "请运行: aws configure"
    echo "需要:"
    echo "  - AWS Access Key ID"
    echo "  - AWS Secret Access Key"
    echo "  - Default region (例如: us-east-1)"
    exit 1
fi
echo ""

# 检查SSH密钥
echo "🔑 检查SSH密钥..."
if [ -f ~/.ssh/id_rsa.pub ] || [ -f ~/.ssh/id_ed25519.pub ]; then
    SSH_KEY=$(cat ~/.ssh/id_rsa.pub 2>/dev/null || cat ~/.ssh/id_ed25519.pub 2>/dev/null)
    echo "✅ 找到SSH公钥:"
    echo "   ${SSH_KEY:0:50}..."
    echo ""
    echo "💡 提示: 如果要在terraform.tfvars中使用，复制以下内容:"
    echo "$SSH_KEY"
else
    echo "⚠️  未找到SSH公钥"
    echo ""
    echo "生成SSH密钥:"
    echo "  ssh-keygen -t rsa -b 4096 -C 'your-email@example.com'"
fi
echo ""

# 检查terraform目录
if [ ! -d "terraform" ]; then
    echo "❌ terraform目录不存在"
    echo "请确保在CloudLens项目根目录运行此脚本"
    exit 1
fi

# 检查terraform.tfvars
cd terraform
if [ ! -f "terraform.tfvars" ]; then
    echo "📝 创建terraform.tfvars..."
    if [ -f "terraform.tfvars.example" ]; then
        cp terraform.tfvars.example terraform.tfvars
        echo "✅ 已从terraform.tfvars.example创建terraform.tfvars"
        echo ""
        echo "⚠️  请编辑terraform.tfvars，填写以下信息:"
        echo "   1. domain_name = 'cloudlens.songqipeng.com'"
        echo "   2. route53_zone_name = 'songqipeng.com'"
        echo "   3. mysql_password = 'YOUR_SECURE_PASSWORD'"
        echo "   4. ssh_public_key = '$(cat ~/.ssh/id_rsa.pub 2>/dev/null || echo 'YOUR_SSH_PUBLIC_KEY')'"
        echo ""
        read -p "按Enter继续..."
    else
        echo "❌ terraform.tfvars.example不存在"
        exit 1
    fi
else
    echo "✅ terraform.tfvars已存在"
fi

# 初始化Terraform
echo ""
echo "🔧 初始化Terraform..."
terraform init

echo ""
echo "================================"
echo "✅ 环境设置完成！"
echo ""
echo "📝 下一步:"
echo "   1. 编辑 terraform/terraform.tfvars"
echo "   2. 运行: cd terraform && terraform plan"
echo "   3. 运行: terraform apply"
echo ""
