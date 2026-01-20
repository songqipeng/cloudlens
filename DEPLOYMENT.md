# CloudLens 部署指南

本文档详细说明如何在不同环境下部署 CloudLens 多云资源治理平台。

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [生产环境部署](#生产环境部署)
- [开发/测试环境部署](#开发测试环境部署)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [维护操作](#维护操作)

---

## 系统要求

### 硬件要求

- **最低配置**：
  - CPU: 2核
  - 内存: 4GB
  - 磁盘: 20GB

- **推荐配置**：
  - CPU: 4核+
  - 内存: 8GB+
  - 磁盘: 50GB+

### 软件要求

- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **操作系统**:
  - Linux (Ubuntu 20.04+, CentOS 7+, Debian 10+)
  - macOS 11+ (Intel/Apple Silicon)

### 支持的架构

- x86_64 (amd64)
- ARM64 (aarch64)

---

## 快速开始

### 一键部署（生产环境）

```bash
# 1. 克隆仓库
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens

# 2. 执行部署脚本
./deploy-production.sh
```

部署完成后访问：
- 前端界面: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

---

## 生产环境部署

### 步骤详解

#### 1. 准备配置文件

首次部署会自动创建 `~/.cloudlens/.env` 配置文件。

**重要配置项**：

```bash
# 数据库配置（Docker环境使用容器名）
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=your_secure_password_here  # ⚠️ 请修改

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379

# 阿里云凭证（可选，用于账单获取和资源查询）
# 在 ~/.cloudlens/config.json 中配置
```

#### 2. 配置阿里云账号

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

#### 3. 执行部署

```bash
./deploy-production.sh
```

脚本会自动：
1. 检测系统环境
2. 拉取Docker镜像
3. 启动所有服务
4. 执行健康检查
5. 初始化数据库

#### 4. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 测试API
curl http://localhost:8000/health
```

### 使用自定义镜像

如果你构建了自己的镜像：

```bash
# 设置环境变量
export DOCKER_HUB_USERNAME=your_username
export IMAGE_TAG=v1.0.0

# 部署
./deploy-production.sh
```

---

## 开发/测试环境部署

开发环境支持源代码挂载和热重载，适合开发调试。

### 快速启动

```bash
./deploy-dev.sh
```

### 开发环境特性

- ✅ **源代码挂载**: 修改代码自动重载
- ✅ **热重载**: 前后端都支持热重载
- ✅ **详细日志**: DEBUG级别日志
- ✅ **断点调试**: 支持远程调试

### 目录结构

```
cloudlens/
├── cloudlens/          # 后端核心代码（挂载）
├── web/
│   ├── backend/       # 后端API（挂载）
│   └── frontend/      # 前端代码（挂载）
├── config/            # 配置文件（挂载）
├── migrations/        # 数据库迁移（挂载）
└── logs/              # 日志目录（挂载）
```

### 开发工作流

1. **修改代码**：直接在本地编辑器修改
2. **自动重载**：服务自动检测变化并重启
3. **查看日志**：
   ```bash
   # 后端日志
   docker-compose -f docker-compose.dev.yml logs -f backend

   # 前端日志
   docker-compose -f docker-compose.dev.yml logs -f frontend
   ```

4. **调试**：
   ```bash
   # 进入后端容器
   docker exec -it cloudlens-backend-dev bash

   # 进入前端容器
   docker exec -it cloudlens-frontend-dev sh
   ```

---

## 配置说明

### 环境变量配置

#### `~/.cloudlens/.env`

```bash
# ===================
# 数据库配置
# ===================
# 注意：Docker Compose环境中使用容器名，本地开发使用localhost
CLOUDLENS_DATABASE__DB_TYPE=mysql
CLOUDLENS_DATABASE__MYSQL_HOST=mysql      # Docker: mysql, 本地: localhost
CLOUDLENS_DATABASE__MYSQL_PORT=3306
CLOUDLENS_DATABASE__MYSQL_USER=cloudlens
CLOUDLENS_DATABASE__MYSQL_PASSWORD=cloudlens123
CLOUDLENS_DATABASE__MYSQL_DATABASE=cloudlens
CLOUDLENS_DATABASE__POOL_SIZE=20

# 简化变量名（兼容旧代码）
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=cloudlens123
MYSQL_DATABASE=cloudlens

# ===================
# Redis配置
# ===================
REDIS_HOST=redis
REDIS_PORT=6379

# ===================
# 应用配置
# ===================
CLOUDLENS_ENVIRONMENT=production      # development/production
CLOUDLENS_DEBUG=false                 # true/false

# ===================
# CORS配置
# ===================
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# ===================
# 日志配置
# ===================
CLOUDLENS_LOGGING__LOG_LEVEL=INFO    # DEBUG/INFO/WARNING/ERROR
CLOUDLENS_LOGGING__LOG_DIR=logs
CLOUDLENS_LOGGING__MAX_LOG_SIZE_MB=10
```

### Docker Compose 配置

#### 生产环境 (`docker-compose.yml`)

- 使用预构建镜像
- 数据持久化
- 健康检查
- 自动重启

#### 开发环境 (`docker-compose.dev.yml`)

- 源代码挂载
- 热重载
- 调试端口暴露
- 详细日志

### 端口映射

| 服务 | 容器端口 | 主机端口 | 说明 |
|-----|---------|---------|------|
| Frontend | 3000 | 3000 | Web界面 |
| Backend | 8000 | 8000 | API服务 |
| MySQL | 3306 | 3306 | 数据库 |
| Redis | 6379 | 6379 | 缓存 |

---

## 常见问题

### Q: 容器启动失败

**A**: 检查端口占用

```bash
# 检查端口
netstat -tlnp | grep -E '3000|8000|3306|6379'

# 或使用lsof (macOS)
lsof -i :3000
lsof -i :8000
```

### Q: 数据库连接失败

**A**: 检查配置

```bash
# 检查容器网络
docker network ls
docker network inspect cloudlens_cloudlens-network

# 检查环境变量
docker exec cloudlens-backend printenv | grep MYSQL
```

**常见错误**：
- ❌ `MYSQL_HOST=localhost` (Docker环境错误)
- ✅ `MYSQL_HOST=mysql` (Docker环境正确)

### Q: 前端无法连接后端

**A**: 检查CORS配置

```bash
# 检查后端环境变量
docker exec cloudlens-backend printenv | grep CORS

# 应包含前端地址
CORS_ORIGINS=http://localhost:3000
```

### Q: 数据持久化

**A**: 数据存储在Docker Volumes

```bash
# 查看volumes
docker volume ls | grep cloudlens

# 备份数据
docker run --rm -v cloudlens_mysql_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/mysql_backup.tar.gz /data
```

### Q: 内存不足

**A**: 调整Docker资源限制

```bash
# 检查资源使用
docker stats

# 在docker-compose.yml中添加资源限制
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
```

---

## 维护操作

### 查看日志

```bash
# 所有服务
docker-compose logs -f

# 特定服务
docker-compose logs -f backend
docker-compose logs -f frontend

# 最近100行
docker-compose logs --tail=100 backend
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

### 更新镜像

```bash
# 拉取最新镜像
docker-compose pull

# 重新创建容器
docker-compose up -d --force-recreate
```

### 清理环境

```bash
# 停止服务
docker-compose down

# 删除volume（⚠️ 会删除所有数据）
docker-compose down -v

# 清理未使用的镜像
docker image prune -a
```

### 数据库维护

```bash
# 进入MySQL容器
docker exec -it cloudlens-mysql bash

# 连接数据库
mysql -u cloudlens -pcloudlens123 cloudlens

# 执行SQL
mysql -u cloudlens -pcloudlens123 cloudlens -e "SELECT COUNT(*) FROM bill_items;"
```

### 备份数据

```bash
# 备份MySQL
docker exec cloudlens-mysql mysqldump \
  -u cloudlens -pcloudlens123 cloudlens \
  > backup_$(date +%Y%m%d).sql

# 备份配置
tar czf config_backup.tar.gz ~/.cloudlens/
```

### 恢复数据

```bash
# 恢复MySQL
docker exec -i cloudlens-mysql mysql \
  -u cloudlens -pcloudlens123 cloudlens \
  < backup_20260120.sql
```

---

## 生产环境最佳实践

### 安全

1. **修改默认密码**
   ```bash
   # MySQL root密码
   # Redis密码（如需要）
   ```

2. **限制网络访问**
   ```yaml
   # 只暴露必要端口
   ports:
     - "127.0.0.1:3306:3306"  # 只允许本地访问MySQL
   ```

3. **使用secrets管理敏感信息**
   ```yaml
   secrets:
     mysql_password:
       file: ./secrets/mysql_password.txt
   ```

### 性能

1. **调整数据库连接池**
   ```bash
   MYSQL_POOL_SIZE=50  # 根据并发量调整
   ```

2. **启用Redis缓存**
   ```bash
   REDIS_HOST=redis
   ```

3. **使用CDN**：静态资源使用CDN加速

### 监控

1. **健康检查**
   ```bash
   # 定时检查
   */5 * * * * curl -f http://localhost:8000/health || alert
   ```

2. **日志监控**
   - 使用ELK stack
   - 或使用云服务日志

3. **资源监控**
   ```bash
   docker stats
   ```

---

## 支持

- **文档**: https://github.com/songqipeng/cloudlens/wiki
- **问题反馈**: https://github.com/songqipeng/cloudlens/issues
- **邮件支持**: support@cloudlens.com

---

## 更新日志

### v2.1.0 (2026-01-20)
- ✅ 修复MySQL数据库连接问题
- ✅ 修复alert_history表外键约束
- ✅ 添加账单数据状态API
- ✅ 优化Docker Compose配置
- ✅ 添加一键部署脚本

---

*最后更新: 2026-01-20*
