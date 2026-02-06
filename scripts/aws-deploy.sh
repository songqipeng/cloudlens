#!/bin/bash
# CloudLens AWS部署脚本
# 用于在EC2实例上快速部署CloudLens

set -e

echo "🚀 CloudLens AWS部署脚本"
echo "=========================="
echo ""

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then 
   echo "⚠️  请不要使用root用户运行此脚本"
   echo "请使用普通用户（如ec2-user）运行"
   exit 1
fi

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装"
    echo "正在安装Docker..."
    
    # 检测操作系统
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        echo "❌ 无法检测操作系统"
        exit 1
    fi
    
    if [ "$OS" == "amzn" ] || [ "$OS" == "amazon" ]; then
        # Amazon Linux
        sudo yum update -y
        sudo yum install docker -y
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
        echo "✅ Docker已安装（Amazon Linux）"
    elif [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
        # Ubuntu/Debian
        sudo apt-get update
        sudo apt-get install -y docker.io
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
        echo "✅ Docker已安装（Ubuntu/Debian）"
    else
        echo "❌ 不支持的操作系统: $OS"
        exit 1
    fi
    
    echo "⚠️  请重新登录以使Docker组权限生效"
    echo "或运行: newgrp docker"
    exit 0
fi

# 检查Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装"
    echo "正在安装Docker Compose..."
    
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    echo "✅ Docker Compose已安装"
fi

# 检查项目目录
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 未找到docker-compose.yml"
    echo "请确保在CloudLens项目根目录运行此脚本"
    exit 1
fi

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env文件不存在"
    if [ -f ".env.example" ]; then
        echo "从.env.example创建.env文件..."
        cp .env.example .env
        echo "✅ 已创建.env文件，请编辑配置："
        echo "   - MySQL密码"
        echo "   - API密钥等"
        read -p "按Enter继续..."
    else
        echo "❌ 未找到.env.example文件"
        exit 1
    fi
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p logs
mkdir -p ~/.cloudlens
echo "✅ 目录已创建"

# 检查Docker服务状态
if ! sudo systemctl is-active --quiet docker; then
    echo "⚠️  Docker服务未运行，正在启动..."
    sudo systemctl start docker
fi

# 拉取镜像
echo "📥 拉取Docker镜像..."
docker-compose pull || echo "⚠️  部分镜像拉取失败，将使用本地构建"

# 启动服务
echo "🚀 启动CloudLens服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动（30秒）..."
sleep 30

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

# 检查健康状态
echo "🏥 检查服务健康状态..."
sleep 10

# 检查后端
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端服务正常"
else
    echo "⚠️  后端服务可能未就绪，请检查日志: docker-compose logs backend"
fi

# 检查前端
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ 前端服务正常"
else
    echo "⚠️  前端服务可能未就绪，请检查日志: docker-compose logs frontend"
fi

echo ""
echo "=========================="
echo "✅ 部署完成！"
echo ""
echo "📝 访问地址:"
echo "   前端: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):3000"
echo "   后端API: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
echo ""
echo "📋 常用命令:"
echo "   查看日志: docker-compose logs -f"
echo "   停止服务: docker-compose down"
echo "   重启服务: docker-compose restart"
echo "   查看状态: docker-compose ps"
echo ""
echo "🔒 安全建议:"
echo "   1. 配置安全组，只开放必要端口"
echo "   2. 使用Application Load Balancer + HTTPS"
echo "   3. 定期备份MySQL数据"
echo "   4. 设置CloudWatch监控和告警"
echo ""
