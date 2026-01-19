# Docker Hub 镜像使用指南

> **版本**: 1.0  
> **更新日期**: 2026-01-18  
> **说明**: 本指南介绍如何使用 Docker Hub 上的预构建镜像快速启动 CloudLens

---

## 🚀 快速开始（无需构建）

### 前置条件

- ✅ 已安装 Docker 和 Docker Compose
- ✅ 已配置 AI API 密钥（Claude 或 OpenAI）

### 一键启动

```bash
# 1. 克隆代码（仅需要配置文件）
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，至少配置 AI API 密钥：
# ANTHROPIC_API_KEY=your_claude_api_key
# LLM_PROVIDER=claude

# 3. 启动所有服务（自动拉取镜像）
docker-compose up -d

# 4. 查看服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f
```

**就这么简单！** 所有镜像会自动从 Docker Hub 拉取，无需本地构建。

---

## 📦 使用的镜像

CloudLens 使用以下预构建镜像：

- **后端**: `songqipeng/cloudlens-backend:latest`
- **前端**: `songqipeng/cloudlens-frontend:latest`
- **MySQL**: `mysql:8.0` (官方镜像)
- **Redis**: `redis:7-alpine` (官方镜像)
- **Nginx**: `nginx:alpine` (官方镜像)

### 镜像标签说明

- `latest`: 最新稳定版本（main 分支）
- `main-<commit-sha>`: 特定提交版本
- `v1.0.0`: 语义化版本标签

---

## ⚙️ 环境变量配置

### 必需配置

在 `.env` 文件中至少配置以下内容：

```bash
# AI 服务（至少一个）
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
LLM_PROVIDER=claude

# 或使用 OpenAI
OPENAI_API_KEY=sk-xxxxx
LLM_PROVIDER=openai
```

### 可选配置

```bash
# 数据库配置（默认值通常可用）
MYSQL_ROOT_PASSWORD=cloudlens_root_2024
MYSQL_USER=cloudlens
MYSQL_PASSWORD=cloudlens123
MYSQL_DATABASE=cloudlens

# 端口配置（如果默认端口被占用）
BACKEND_PORT=8000
FRONTEND_PORT=3000
MYSQL_PORT=3306
REDIS_PORT=6379

# 通知服务（可选）
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_password
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

---

## 🔄 更新镜像

### 拉取最新镜像

```bash
# 拉取最新镜像
docker-compose pull

# 重启服务以使用新镜像
docker-compose up -d
```

### 使用特定版本

在 `docker-compose.yml` 中设置镜像标签：

```yaml
backend:
  image: songqipeng/cloudlens-backend:v1.0.0  # 使用特定版本

frontend:
  image: songqipeng/cloudlens-frontend:v1.0.0  # 使用特定版本
```

或使用环境变量：

```bash
# 在 .env 文件中
IMAGE_TAG=v1.0.0
```

---

## 🗄️ 数据库初始化

数据库会在首次启动时自动初始化：

1. MySQL 容器启动时自动创建数据库
2. 后端容器启动时自动执行迁移脚本
3. 创建所有必要的表结构

**无需手动执行 SQL 脚本！**

---

## 🔍 验证安装

### 1. 检查服务状态

```bash
docker-compose ps
```

所有服务应该显示为 `Up` 状态。

### 2. 检查后端健康

```bash
curl http://localhost:8000/health
```

应该返回：
```json
{
  "status": "healthy",
  "timestamp": "2026-01-18T10:00:00Z",
  "service": "cloudlens-api",
  "version": "1.1.0"
}
```

### 3. 访问前端

打开浏览器访问：http://localhost:3000

### 4. 查看 API 文档

访问：http://localhost:8000/docs

---

## 🛠️ 常用命令

### 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 启动并查看日志
docker-compose up

# 启动特定服务
docker-compose up -d backend frontend
```

### 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（⚠️ 会删除所有数据）
docker-compose down -v
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mysql
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

### 进入容器

```bash
# 进入后端容器
docker-compose exec backend bash

# 进入 MySQL 容器
docker-compose exec mysql mysql -u cloudlens -pcloudlens123 cloudlens
```

---

## 🔧 故障排查

### 问题1: 镜像拉取失败

**症状**: `Error response from daemon: pull access denied`

**解决方案**:
1. 检查网络连接
2. 确认镜像名称正确：`songqipeng/cloudlens-backend:latest`
3. 如果镜像尚未构建，需要先构建并推送（见下方）

### 问题2: 服务启动失败

**症状**: 容器状态为 `Exit 1`

**排查步骤**:
```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs frontend

# 检查环境变量
docker-compose config

# 检查端口占用
lsof -i :8000
lsof -i :3000
lsof -i :3306
```

### 问题3: 数据库连接失败

**症状**: 后端日志显示数据库连接错误

**解决方案**:
```bash
# 检查 MySQL 是否运行
docker-compose ps mysql

# 检查 MySQL 日志
docker-compose logs mysql

# 手动测试连接
docker-compose exec mysql mysql -u cloudlens -pcloudlens123 cloudlens -e "SELECT 1;"
```

### 问题4: AI Chatbot 不工作

**症状**: AI 功能返回错误

**解决方案**:
1. 检查 `.env` 文件中是否配置了 AI API 密钥
2. 验证密钥是否有效
3. 查看后端日志：`docker-compose logs backend | grep -i "ai\|llm\|anthropic\|openai"`

---

## 📝 构建和推送镜像（开发者）

如果你需要构建和推送新镜像到 Docker Hub：

### 1. 配置 Docker Hub 凭证

在 GitHub Secrets 中配置：
- `DOCKER_HUB_TOKEN`: Docker Hub 访问令牌

### 2. 自动构建（推荐）

GitHub Actions 会在推送到 `main` 分支时自动构建并推送镜像。

### 3. 手动构建

```bash
# 构建后端镜像
docker build -f web/backend/Dockerfile -t songqipeng/cloudlens-backend:latest .

# 构建前端镜像
docker build -f web/frontend/Dockerfile -t songqipeng/cloudlens-frontend:latest .

# 登录 Docker Hub
docker login -u songqipeng

# 推送镜像
docker push songqipeng/cloudlens-backend:latest
docker push songqipeng/cloudlens-frontend:latest
```

---

## 📚 相关文档

- [Q1功能使用指南](./Q1_USER_GUIDE.md)
- [本地测试指南](./LOCAL_TESTING_GUIDE.md)
- [部署清单](./Q1_DEPLOYMENT_CHECKLIST.md)

---

**最后更新**: 2026-01-18  
**维护者**: CloudLens Team
