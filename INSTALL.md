# CloudLens 安装指南

本文档提供 CloudLens 的各种安装方式。

---

## 🚀 一键安装（推荐）

### 适用场景
- 全新的 Linux 或 macOS 系统
- 只需要快速启动和使用
- 不需要修改源代码

### 安装命令

使用 curl：
```bash
curl -fsSL https://raw.githubusercontent.com/songqipeng/cloudlens/main/install.sh | bash
```

或使用 wget：
```bash
wget -qO- https://raw.githubusercontent.com/songqipeng/cloudlens/main/install.sh | bash
```

### 安装过程

脚本会自动完成以下步骤：

1. **环境检测**
   - 检测操作系统（Linux/macOS）
   - 检测CPU架构（x86_64/arm64）

2. **依赖安装**
   - 检查 Git 是否安装
   - 检查 Docker 是否安装
   - 如果 Docker 未安装，提供安装指导（macOS）或自动安装（Linux）

3. **代码获取**
   - 从 GitHub 克隆代码到 `~/cloudlens`
   - 如果目录已存在，询问是否覆盖

4. **配置生成**
   - 创建 `~/.cloudlens/.env` 配置文件
   - 创建 `~/.cloudlens/config.json` 账号配置

5. **服务启动**
   - 拉取 Docker 镜像
   - 启动所有服务（MySQL、Redis、Backend、Frontend）
   - 执行健康检查

6. **完成提示**
   - 显示访问地址
   - 显示常用命令

### 安装时间

- 首次安装：3-12分钟（取决于网络速度）
- 再次安装：1-3分钟

### 安装后

安装完成后：

```bash
# 访问前端界面
open http://localhost:3000

# 访问后端API
open http://localhost:8000

# 查看API文档
open http://localhost:8000/docs
```

---

## 📦 手动安装

### 前提条件

- Docker 20.10+
- Docker Compose 2.0+
- Git

### 生产环境部署

```bash
# 1. 克隆代码
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens

# 2. 执行部署脚本
./deploy-production.sh
```

### 开发环境部署

```bash
# 1. 克隆代码
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens

# 2. 执行开发部署脚本
./deploy-dev.sh
```

开发环境特性：
- ✅ 源代码挂载（修改后自动重载）
- ✅ 详细调试日志
- ✅ 支持断点调试

---

## 🐳 Docker 安装指南

### macOS

1. 下载 Docker Desktop for Mac
2. 访问：https://docs.docker.com/desktop/install/mac-install/
3. 安装 DMG 包
4. 启动 Docker Desktop

### Linux (Ubuntu/Debian)

```bash
# 使用官方脚本
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 添加当前用户到 docker 组
sudo usermod -aG docker $USER

# 注销并重新登录使权限生效
```

### Linux (CentOS/RHEL)

```bash
# 安装 Docker
sudo yum install -y docker

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 添加当前用户到 docker 组
sudo usermod -aG docker $USER
```

---

## ⚙️ 配置说明

### 环境变量配置

编辑 `~/.cloudlens/.env`：

```bash
# 数据库配置
MYSQL_HOST=mysql                    # Docker环境使用容器名
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=your_password_here   # 建议修改

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379

# 应用配置
CLOUDLENS_ENVIRONMENT=production
CLOUDLENS_DEBUG=false
```

### 阿里云账号配置

编辑 `~/.cloudlens/config.json`：

```json
{
  "accounts": [
    {
      "name": "prod",
      "provider": "aliyun",
      "access_key_id": "YOUR_ACCESS_KEY_ID",
      "access_key_secret": "YOUR_ACCESS_KEY_SECRET",
      "region": "cn-hangzhou",
      "alias": "生产账号"
    }
  ]
}
```

---

## 🔍 验证安装

### 检查服务状态

```bash
cd ~/cloudlens  # 或你的安装目录
docker-compose ps
```

预期输出：
```
NAME                    STATUS              PORTS
cloudlens-backend       Up (healthy)        0.0.0.0:8000->8000/tcp
cloudlens-frontend      Up                  0.0.0.0:3000->3000/tcp
cloudlens-mysql         Up (healthy)        0.0.0.0:3306->3306/tcp
cloudlens-redis         Up (healthy)        0.0.0.0:6379->6379/tcp
```

### 测试后端API

```bash
curl http://localhost:8000/health
```

预期输出：
```json
{
  "status": "healthy",
  "timestamp": "2026-01-20T..."
}
```

### 测试前端

在浏览器打开：http://localhost:3000

应该看到 CloudLens 登录界面。

---

## 🛠️ 故障排查

### 端口被占用

```bash
# 检查端口占用
lsof -i :3000
lsof -i :8000
lsof -i :3306

# 停止占用端口的进程
kill -9 <PID>

# 或修改 docker-compose.yml 中的端口映射
```

### Docker 内存不足

```bash
# Docker Desktop (macOS)
# Settings -> Resources -> Memory -> 8GB+

# Linux
# 检查系统内存
free -h

# 清理 Docker 资源
docker system prune -a
```

### 服务启动失败

```bash
# 查看日志
docker-compose logs backend
docker-compose logs frontend

# 重启服务
docker-compose restart

# 完全重建
docker-compose down
docker-compose up -d --force-recreate
```

### 数据库连接失败

```bash
# 检查 MySQL 容器
docker exec cloudlens-mysql mysql -u cloudlens -pcloudlens123 -e "SELECT 1"

# 检查环境变量
docker exec cloudlens-backend printenv | grep MYSQL

# 确保 MYSQL_HOST=mysql（容器名），而不是 localhost
```

---

## 📊 系统要求

### 最低配置
- CPU: 2核
- 内存: 4GB
- 磁盘: 20GB
- 操作系统: Ubuntu 20.04+ / macOS 11+

### 推荐配置
- CPU: 4核+
- 内存: 8GB+
- 磁盘: 50GB+
- 操作系统: Ubuntu 22.04+ / macOS 12+

### 支持的平台
- ✅ macOS 11+ (Intel & Apple Silicon)
- ✅ Ubuntu 20.04+
- ✅ CentOS 7+
- ✅ Debian 10+
- ⚠️ Windows (WSL2 模式，未充分测试)

---

## 🗑️ 卸载

### 保留数据的卸载

```bash
cd ~/cloudlens
docker-compose stop
```

稍后可以通过 `docker-compose start` 重新启动。

### 完全卸载

```bash
cd ~/cloudlens

# 停止并删除容器和卷
docker-compose down -v

# 删除代码
cd ~
rm -rf cloudlens

# 删除配置
rm -rf ~/.cloudlens

# 删除镜像（可选）
docker rmi $(docker images | grep cloudlens | awk '{print $3}')
```

---

## 📞 获取帮助

- **文档**: [部署指南](DEPLOYMENT.md)
- **问题反馈**: [GitHub Issues](https://github.com/songqipeng/cloudlens/issues)
- **常见问题**: [FAQ](docs/FAQ.md)

---

*最后更新: 2026-01-20*
