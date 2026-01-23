#!/bin/bash
# 配置AWS凭证脚本

set -e

echo "🔐 配置 AWS 凭证"
echo "=================="
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

echo "您的 AWS 信息:"
echo "  Access Key ID: AKIAUZM7BBYUDP4UQITJ"
echo "  账户ID: 329435385384"
echo "  用户名: songqipeng"
echo ""

# 检查是否已配置
if aws sts get-caller-identity &> /dev/null; then
    CURRENT_AK=$(aws configure get aws_access_key_id 2>/dev/null || echo "")
    if [ "$CURRENT_AK" = "AKIAUZM7BBYUDP4UQITJ" ]; then
        echo "✅ 凭证已配置"
        aws sts get-caller-identity
        echo ""
        echo "当前区域: $(aws configure get region || echo '未设置')"
        echo ""
        read -p "是否要重新配置？(y/n): " reconfigure
        if [ "$reconfigure" != "y" ]; then
            echo "✅ 配置完成"
            exit 0
        fi
    fi
fi

echo "⚠️  请准备好您的 Secret Access Key"
echo "   （如果忘记了，需要在AWS控制台重新创建）"
echo ""

read -p "请输入 Secret Access Key: " -s SECRET_KEY
echo ""

if [ -z "$SECRET_KEY" ]; then
    echo "❌ Secret Access Key 不能为空"
    exit 1
fi

echo ""
echo "选择AWS区域:"
echo "  1) ap-northeast-1 (日本东京) - 推荐"
echo "  2) ap-east-1 (香港)"
echo "  3) 其他区域"
read -p "请选择 (1-3): " region_choice

case $region_choice in
    1)
        REGION="ap-northeast-1"
        ;;
    2)
        REGION="ap-east-1"
        ;;
    3)
        read -p "请输入区域代码: " REGION
        ;;
    *)
        REGION="ap-northeast-1"
        echo "使用默认区域: $REGION"
        ;;
esac

# 配置AWS凭证
aws configure set aws_access_key_id AKIAUZM7BBYUDP4UQITJ
aws configure set aws_secret_access_key "$SECRET_KEY"
aws configure set default.region "$REGION"
aws configure set default.output json

echo ""
echo "✅ AWS凭证配置完成！"
echo ""
echo "验证配置..."
if aws sts get-caller-identity &> /dev/null; then
    echo "✅ 凭证验证成功"
    aws sts get-caller-identity
    echo ""
    echo "当前配置:"
    echo "  Access Key ID: $(aws configure get aws_access_key_id)"
    echo "  区域: $(aws configure get region)"
    echo "  输出格式: $(aws configure get output)"
    echo ""
    echo "🎉 可以开始部署了！"
    echo ""
    echo "下一步:"
    echo "  cd terraform"
    echo "  ./一键部署.sh"
else
    echo "❌ 凭证验证失败，请检查 Secret Access Key 是否正确"
    exit 1
fi
