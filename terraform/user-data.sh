#!/bin/bash
# CloudLens EC2实例初始化脚本

set -e

# 日志文件
LOG_FILE="/var/log/cloudlens-init.log"
exec > >(tee -a $LOG_FILE)
exec 2>&1

echo "=========================================="
echo "CloudLens EC2实例初始化"
echo "开始时间: $(date)"
echo "=========================================="

# 更新系统（跳过有冲突的包）
echo "[1/8] 更新系统..."
sudo yum update -y --skip-broken || echo "⚠️  部分包更新失败，继续执行"

# 安装Docker
echo "[2/8] 安装Docker..."
if ! command -v docker &> /dev/null; then
    sudo yum install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker ec2-user
    echo "✅ Docker已安装"
else
    echo "✅ Docker已存在"
fi

# 安装Docker Compose
echo "[3/8] 安装Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose已安装"
else
    echo "✅ Docker Compose已存在"
fi

# 安装其他工具
echo "[4/8] 安装必要工具..."
sudo yum install -y git wget jq --skip-broken || sudo yum install -y git wget jq --allowerasing || echo "⚠️  部分工具安装失败，继续执行"

# 创建目录
echo "[5/8] 创建必要目录..."
mkdir -p /opt/cloudlens
mkdir -p /opt/cloudlens/logs
mkdir -p /opt/cloudlens/data
mkdir -p /root/.cloudlens

# 挂载EBS卷（如果存在）
echo "[6/8] 配置EBS数据卷..."
if [ -b /dev/nvme1n1 ] || [ -b /dev/xvdf ]; then
    DATA_DEVICE=$(lsblk -o NAME,TYPE | grep disk | grep -v nvme0n1 | awk '{print $1}' | head -1)
    if [ -n "$DATA_DEVICE" ]; then
        if ! mountpoint -q /opt/cloudlens/data; then
            # 检查文件系统
            if ! blkid /dev/$DATA_DEVICE; then
                echo "格式化数据卷..."
                sudo mkfs.ext4 /dev/$DATA_DEVICE
            fi
            # 挂载
            echo "/dev/$DATA_DEVICE /opt/cloudlens/data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
            sudo mount /opt/cloudlens/data || true
            echo "✅ 数据卷已挂载"
        else
            echo "✅ 数据卷已挂载"
        fi
    fi
fi

# 克隆或更新代码
echo "[7/8] 准备CloudLens代码..."
if [ ! -d "/opt/cloudlens/app" ]; then
    echo "克隆CloudLens代码..."
    cd /opt/cloudlens
    git clone https://github.com/songqipeng/cloudlens.git app || {
        echo "⚠️  克隆失败，将创建空目录"
        mkdir -p app
    }
else
    echo "更新CloudLens代码..."
    cd /opt/cloudlens/app
    git pull || echo "⚠️  更新失败，使用现有代码"
fi

# 配置环境变量
echo "[8/8] 配置环境变量..."
cd /opt/cloudlens/app

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        # 更新.env文件中的配置
        sed -i "s|MYSQL_USER=.*|MYSQL_USER=${mysql_user}|g" .env || true
        sed -i "s|MYSQL_PASSWORD=.*|MYSQL_PASSWORD=${mysql_password}|g" .env || true
        sed -i "s|MYSQL_DATABASE=.*|MYSQL_DATABASE=${mysql_database}|g" .env || true
        sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=https://${domain_name}/api|g" .env || true
        sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=https://${domain_name}|g" .env || true
    else
        cat > .env <<EOF
# MySQL配置
MYSQL_USER=${mysql_user}
MYSQL_PASSWORD=${mysql_password}
MYSQL_DATABASE=${mysql_database}
MYSQL_ROOT_PASSWORD=${mysql_password}_root_2024

# 应用配置
NEXT_PUBLIC_API_URL=https://${domain_name}/api
CLOUDLENS_ENVIRONMENT=production
CLOUDLENS_DEBUG=false

# CORS配置
CORS_ORIGINS=https://${domain_name}
EOF
    fi
fi

# 修改docker-compose.yml以使用挂载的数据卷
if [ -f "docker-compose.yml" ] && [ -d "/opt/cloudlens/data" ]; then
    # 备份原始文件
    cp docker-compose.yml docker-compose.yml.bak
    
    # 修改MySQL数据卷路径
    sed -i 's|mysql_data:|/opt/cloudlens/data/mysql:|g' docker-compose.yml || true
    sed -i 's|redis_data:|/opt/cloudlens/data/redis:|g' docker-compose.yml || true
fi

# 启动Docker Compose（如果代码存在）
if [ -f "docker-compose.yml" ]; then
    echo "启动CloudLens服务..."
    # 等待Docker服务就绪
    sleep 10
    
    # 拉取镜像
    docker-compose pull || echo "⚠️  镜像拉取失败，将使用本地构建"
    
    # 启动服务
    docker-compose up -d || echo "⚠️  服务启动失败，请检查日志"
    
    echo "✅ CloudLens服务已启动"
else
    echo "⚠️  docker-compose.yml不存在，跳过自动启动"
    echo "请手动部署CloudLens"
fi

# 配置CloudWatch日志代理（可选）
echo "配置CloudWatch日志..."
sudo yum install -y amazon-cloudwatch-agent || echo "⚠️  CloudWatch Agent安装失败"

# 完成
echo ""
echo "=========================================="
echo "✅ 初始化完成！"
echo "完成时间: $(date)"
echo "=========================================="
echo ""
echo "📝 下一步："
echo "1. SSH连接到实例: ssh ec2-user@<instance-ip>"
echo "2. 检查服务状态: cd /opt/cloudlens/app && docker-compose ps"
echo "3. 查看日志: docker-compose logs -f"
echo "4. 访问: https://${domain_name}"
echo ""
