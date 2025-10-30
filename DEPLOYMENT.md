# 部署指南

本文档提供了阿里云资源分析工具在不同环境下的部署说明。

## 📋 目录

- [系统要求](#系统要求)
- [本地开发环境部署](#本地开发环境部署)
- [生产环境部署](#生产环境部署)
- [Docker部署](#docker部署)
- [定时任务配置](#定时任务配置)
- [监控和日志](#监控和日志)
- [故障排查](#故障排查)

## 系统要求

### 最低要求

- **操作系统**: Linux/macOS/Windows
- **Python版本**: 3.7+（推荐3.11+）
- **内存**: 最低512MB，推荐1GB+
- **磁盘空间**: 最低500MB，推荐2GB+（用于缓存和报告）
- **网络**: 需要访问阿里云API

### 推荐配置

- **操作系统**: Ubuntu 20.04 LTS / CentOS 8+ / macOS 12+
- **Python版本**: 3.11 或 3.12
- **内存**: 2GB+
- **磁盘空间**: 10GB+
- **CPU**: 2核+（支持并发处理）

## 本地开发环境部署

### 1. 克隆项目

```bash
git clone https://github.com/yourorg/aliyunidle.git
cd aliyunidle
```

### 2. 创建虚拟环境

#### 使用venv（推荐）

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Linux/macOS
source venv/bin/activate
# Windows
venv\Scripts\activate
```

#### 使用conda

```bash
conda create -n aliyunidle python=3.11
conda activate aliyunidle
```

### 3. 安装依赖

```bash
# 安装所有依赖
pip install -r requirements.txt

# 如果只需要运行（不需要测试）
pip install -r requirements.txt --no-dev

# 升级pip（可选）
pip install --upgrade pip
```

### 4. 配置文件

```bash
# 复制示例配置
cp config.json.example config.json

# 编辑配置文件
vim config.json
```

### 5. 配置凭证

#### 方法1：使用Keyring（推荐）

```bash
python main.py setup-credentials
```

按提示输入：
- 租户名称
- AccessKey ID
- AccessKey Secret

#### 方法2：直接在config.json中配置

```json
{
  "default_tenant": "my_tenant",
  "tenants": {
    "my_tenant": {
      "access_key_id": "YOUR_ACCESS_KEY_ID",
      "access_key_secret": "YOUR_ACCESS_KEY_SECRET",
      "display_name": "My Tenant"
    }
  }
}
```

### 6. 验证安装

```bash
# 显示帮助信息
python main.py --help

# 显示版本信息
python main.py --version

# 列出已配置的租户
python main.py list-credentials

# 运行测试
pytest tests/ -v
```

## 生产环境部署

### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
sudo yum update -y  # CentOS/RHEL

# 安装Python 3.11
sudo apt install python3.11 python3.11-venv  # Ubuntu
sudo yum install python3.11  # CentOS

# 安装必要工具
sudo apt install git vim curl  # Ubuntu
sudo yum install git vim curl  # CentOS
```

### 2. 创建专用用户

```bash
# 创建用户
sudo useradd -m -s /bin/bash aliyun-analyzer

# 切换到该用户
sudo su - aliyun-analyzer
```

### 3. 部署应用

```bash
# 克隆项目
cd /opt
sudo git clone https://github.com/yourorg/aliyunidle.git
sudo chown -R aliyun-analyzer:aliyun-analyzer /opt/aliyunidle

# 切换到项目目录
cd /opt/aliyunidle

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 配置生产环境

#### 创建配置文件

```bash
# 创建配置文件
cat > config.json <<EOF
{
  "default_tenant": "production",
  "tenants": {
    "production": {
      "use_keyring": true,
      "keyring_key": "aliyun_production",
      "display_name": "Production Environment"
    }
  }
}
EOF
```

#### 设置凭证（使用环境变量）

```bash
# 方法1：使用Keyring
python main.py setup-credentials

# 方法2：使用环境变量
export ALIYUN_ACCESS_KEY_ID="your_key_id"
export ALIYUN_ACCESS_KEY_SECRET="your_secret"

# 添加到 ~/.bashrc 或 ~/.profile 使其永久生效
echo 'export ALIYUN_ACCESS_KEY_ID="your_key_id"' >> ~/.bashrc
echo 'export ALIYUN_ACCESS_KEY_SECRET="your_secret"' >> ~/.bashrc
```

### 5. 目录权限设置

```bash
# 创建必要的目录
mkdir -p data/cache
mkdir -p logs
mkdir -p reports

# 设置权限
chmod 700 config.json  # 仅所有者可读写
chmod 755 main.py
chmod -R 755 core/ utils/ resource_modules/
chmod -R 750 data/  # 数据目录
```

### 6. 日志配置

```bash
# 创建日志目录
mkdir -p /var/log/aliyun-analyzer

# 设置logrotate
sudo cat > /etc/logrotate.d/aliyun-analyzer <<EOF
/var/log/aliyun-analyzer/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 aliyun-analyzer aliyun-analyzer
    sharedscripts
    postrotate
        systemctl reload aliyun-analyzer > /dev/null 2>&1 || true
    endscript
}
EOF
```

## Docker部署

### 1. 创建Dockerfile

```dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建数据目录
RUN mkdir -p data/cache logs reports

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 暴露端口（如果需要）
# EXPOSE 8000

# 运行应用
CMD ["python", "main.py", "--help"]
```

### 2. 创建docker-compose.yml

```yaml
version: '3.8'

services:
  aliyun-analyzer:
    build: .
    container_name: aliyun-analyzer
    volumes:
      - ./config.json:/app/config.json:ro
      - ./data:/app/data
      - ./logs:/app/logs
      - ./reports:/app/reports
    environment:
      - ALIYUN_ACCESS_KEY_ID=${ALIYUN_ACCESS_KEY_ID}
      - ALIYUN_ACCESS_KEY_SECRET=${ALIYUN_ACCESS_KEY_SECRET}
    restart: unless-stopped
```

### 3. 构建和运行

```bash
# 构建镜像
docker build -t aliyun-analyzer:latest .

# 运行容器
docker run -d \
  --name aliyun-analyzer \
  -v $(pwd)/config.json:/app/config.json:ro \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/reports:/app/reports \
  -e ALIYUN_ACCESS_KEY_ID="your_key_id" \
  -e ALIYUN_ACCESS_KEY_SECRET="your_secret" \
  aliyun-analyzer:latest \
  python main.py cru all

# 或使用docker-compose
docker-compose up -d
```

## 定时任务配置

### 使用Cron（Linux/macOS）

```bash
# 编辑crontab
crontab -e

# 每天凌晨2点执行全量分析
0 2 * * * cd /opt/aliyunidle && /opt/aliyunidle/venv/bin/python main.py cru all >> /var/log/aliyun-analyzer/cron.log 2>&1

# 每周一凌晨3点执行折扣分析
0 3 * * 1 cd /opt/aliyunidle && /opt/aliyunidle/venv/bin/python main.py discount all >> /var/log/aliyun-analyzer/discount.log 2>&1

# 每月1号生成月度报告
0 4 1 * * cd /opt/aliyunidle && /opt/aliyunidle/venv/bin/python main.py cru all --monthly-report >> /var/log/aliyun-analyzer/monthly.log 2>&1
```

### 使用Systemd Timer（推荐）

#### 1. 创建service文件

```bash
sudo cat > /etc/systemd/system/aliyun-analyzer.service <<EOF
[Unit]
Description=Aliyun Resource Analyzer
After=network.target

[Service]
Type=oneshot
User=aliyun-analyzer
WorkingDirectory=/opt/aliyunidle
ExecStart=/opt/aliyunidle/venv/bin/python main.py cru all
StandardOutput=append:/var/log/aliyun-analyzer/service.log
StandardError=append:/var/log/aliyun-analyzer/error.log

[Install]
WantedBy=multi-user.target
EOF
```

#### 2. 创建timer文件

```bash
sudo cat > /etc/systemd/system/aliyun-analyzer.timer <<EOF
[Unit]
Description=Aliyun Resource Analyzer Timer
Requires=aliyun-analyzer.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

#### 3. 启用定时器

```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启用并启动定时器
sudo systemctl enable aliyun-analyzer.timer
sudo systemctl start aliyun-analyzer.timer

# 查看定时器状态
sudo systemctl status aliyun-analyzer.timer

# 查看下次执行时间
sudo systemctl list-timers aliyun-analyzer.timer
```

## 监控和日志

### 日志位置

- **应用日志**: `/var/log/aliyun-analyzer/app.log`
- **错误日志**: `/var/log/aliyun-analyzer/error.log`
- **Cron日志**: `/var/log/aliyun-analyzer/cron.log`
- **访问日志**: `logs/access.log`（如果配置）

### 日志查看

```bash
# 实时查看日志
tail -f /var/log/aliyun-analyzer/app.log

# 查看最近100行
tail -n 100 /var/log/aliyun-analyzer/error.log

# 搜索特定错误
grep "ERROR" /var/log/aliyun-analyzer/app.log

# 查看今天的日志
grep "$(date +%Y-%m-%d)" /var/log/aliyun-analyzer/app.log
```

### 监控指标

建议监控以下指标：

- **执行时间**: 分析任务执行时长
- **成功率**: API调用成功率
- **错误率**: 错误日志数量
- **资源发现数**: 发现的资源实例数
- **闲置资源数**: 识别的闲置资源数
- **磁盘使用**: data/cache 目录大小

### 告警配置

使用监控工具（如Prometheus + Grafana）：

```yaml
# prometheus.yml 示例
scrape_configs:
  - job_name: 'aliyun-analyzer'
    static_configs:
      - targets: ['localhost:9090']
```

## 故障排查

### 常见问题

#### 1. 权限问题

```bash
# 检查文件权限
ls -la config.json
ls -la data/

# 修复权限
chmod 600 config.json
chmod -R 750 data/
```

#### 2. 依赖问题

```bash
# 重新安装依赖
pip install --force-reinstall -r requirements.txt

# 检查依赖版本
pip list | grep aliyun
```

#### 3. 网络问题

```bash
# 测试网络连接
ping ecs.aliyuncs.com

# 检查DNS
nslookup ecs.aliyuncs.com

# 测试API连接
curl -I https://ecs.aliyuncs.com
```

#### 4. 内存不足

```bash
# 检查内存使用
free -h

# 增加swap（临时）
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 调试模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python main.py cru ecs

# 禁用缓存（强制刷新）
python main.py cru ecs --no-cache

# 单区域测试
python main.py cru ecs --region cn-hangzhou
```

## 安全建议

### 1. 凭证安全

- ✅ 使用Keyring存储凭证，避免明文配置
- ✅ 使用环境变量传递敏感信息
- ✅ 限制config.json文件权限（600或400）
- ⚠️ 不要将config.json提交到版本控制
- ⚠️ 定期轮换AccessKey

### 2. 网络安全

- ✅ 使用HTTPS访问阿里云API
- ✅ 配置防火墙规则
- ✅ 使用VPC内网访问（如果可能）
- ⚠️ 不要在公网环境暴露配置文件

### 3. 访问控制

- ✅ 使用最小权限原则配置RAM
- ✅ 为不同环境使用不同的AccessKey
- ✅ 启用MFA双因素认证
- ⚠️ 定期审计AccessKey使用情况

## 性能优化

### 1. 并发调优

```python
# 修改concurrent_helper.py中的max_workers
# 根据服务器CPU核心数调整
max_workers = min(20, os.cpu_count() * 2)
```

### 2. 缓存优化

```python
# 修改cache_manager.py中的TTL
# 根据实际需求调整缓存时间
ttl_hours = 12  # 从24小时降至12小时
```

### 3. 数据库优化

```bash
# 定期清理旧数据
find data/ -name "*.db" -mtime +30 -delete

# 定期清理旧缓存
find data/cache/ -name "*.cache" -mtime +7 -delete
```

## 升级指南

### 1. 备份数据

```bash
# 备份配置和数据
tar -czf backup-$(date +%Y%m%d).tar.gz config.json data/ reports/
```

### 2. 更新代码

```bash
# 拉取最新代码
git pull origin main

# 检查变更
git log --oneline -10
```

### 3. 更新依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 更新依赖
pip install --upgrade -r requirements.txt
```

### 4. 运行测试

```bash
# 运行单元测试
pytest tests/ -v

# 验证功能
python main.py --version
```

### 5. 重启服务

```bash
# 如果使用systemd
sudo systemctl restart aliyun-analyzer.timer

# 如果使用docker
docker-compose down && docker-compose up -d
```

## 支持

如遇到部署问题，请：

1. 查看[FAQ.md](FAQ.md)
2. 查看日志文件
3. 提交Issue到GitHub
4. 联系技术支持团队
