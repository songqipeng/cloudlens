#!/bin/bash
# CloudLens EC2实例初始化脚本

# 不使用 set -e，允许部分步骤失败但继续执行
set +e

# 日志文件
LOG_FILE="/var/log/cloudlens-init.log"
exec > >(tee -a $LOG_FILE)
exec 2>&1

echo "=========================================="
echo "CloudLens EC2实例初始化"
echo "开始时间: $(date)"
echo "=========================================="

# 确保SSH服务正常启动
echo "[0/9] 确保SSH服务正常..."
# 写入兼容性配置（Kex/Ciphers），并确保 sshd_config.d 存在（AL2023 默认有，AL2 可能需创建）
sudo mkdir -p /etc/ssh/sshd_config.d
sudo tee /etc/ssh/sshd_config.d/99-cloudlens-kex.conf << 'SSHKEX'
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256,diffie-hellman-group14-sha256,diffie-hellman-group14-sha1
Ciphers aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-ctr,aes256-ctr
SSHKEX
sudo systemctl enable sshd
sudo systemctl start sshd
sleep 2
sudo systemctl status sshd || echo "⚠️  SSH服务状态检查失败，但继续执行"
# 确保SSH服务正在监听
ss -tlnp | grep :22 || echo "⚠️  SSH端口22未监听，尝试重启服务"
sudo systemctl restart sshd
sleep 3
sudo systemctl status sshd --no-pager | head -10

# 更新系统（跳过有冲突的包）
echo "[1/9] 更新系统..."
sudo yum update -y --skip-broken || echo "⚠️  部分包更新失败，继续执行"

# 安装Docker
echo "[2/9] 安装Docker..."
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
echo "[3/9] 安装Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose已安装"
else
    echo "✅ Docker Compose已存在"
fi

# 安装其他工具
echo "[4/9] 安装必要工具..."
sudo yum install -y git wget jq --skip-broken || sudo yum install -y git wget jq --allowerasing || echo "⚠️  部分工具安装失败，继续执行"

# 创建目录
echo "[5/9] 创建必要目录..."
mkdir -p /opt/cloudlens
mkdir -p /opt/cloudlens/logs
mkdir -p /opt/cloudlens/data
mkdir -p /root/.cloudlens

# 挂载EBS卷（如果存在）
echo "[6/9] 配置EBS数据卷..."
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
echo "[7/9] 准备CloudLens代码..."
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
echo "[8/9] 配置环境变量..."
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

# 不再修改docker-compose.yml的volumes配置，使用默认的命名卷
# 数据持久化由docker volumes自动管理

# 创建数据目录（用于bind mount，如果需要的话）
mkdir -p /opt/cloudlens/data/mysql
mkdir -p /opt/cloudlens/data/redis
chown -R 999:999 /opt/cloudlens/data/mysql  # MySQL容器用户

# 修复nginx.conf - 确保/api/路径保留前缀（不strip）
if [ -f "nginx.conf" ]; then
    echo "检查nginx.conf配置..."
    # 确保proxy_pass不带末尾斜杠，这样不会strip掉/api前缀
    # 后端路由使用/api前缀，所以需要保留
    sed -i 's|proxy_pass http://backend/;|proxy_pass http://backend;|g' nginx.conf
    # 增加超时时间
    sed -i 's|proxy_connect_timeout 60s;|proxy_connect_timeout 120s;|g' nginx.conf
    sed -i 's|proxy_send_timeout 60s;|proxy_send_timeout 120s;|g' nginx.conf
    sed -i 's|proxy_read_timeout 60s;|proxy_read_timeout 120s;|g' nginx.conf
    echo "✅ nginx.conf已检查"
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
echo "[9/9] 配置CloudWatch日志..."
sudo yum install -y amazon-cloudwatch-agent || echo "⚠️  CloudWatch Agent安装失败"

# 最终确保SSH服务运行
echo "最终检查SSH服务..."
sudo systemctl restart sshd
sleep 3
sudo systemctl enable sshd
sudo systemctl status sshd --no-pager | head -10
ss -tlnp | grep :22 && echo "✅ SSH服务正在监听端口22" || echo "❌ SSH服务未监听端口22"
echo "SSH服务配置完成"

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
