# CloudLens 用户快速开始指南

> **版本**: 1.0  
> **更新日期**: 2026-01-19  
> **适用对象**: 普通用户，希望快速启动并使用 CloudLens

---

## 🚀 3步快速启动

### 前置条件

- ✅ 已安装 Docker 和 Docker Compose
- ✅ 有 AI API 密钥（Claude 或 OpenAI）
- ✅ **Apple Silicon (M1/M2/M3) 用户**: 确保 Docker Desktop 已启用 Rosetta 2 支持

### 步骤 1: 下载代码

```bash
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens
```

### 步骤 2: 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，至少配置 AI API 密钥
nano .env
```

**必需配置**（至少一个）:
```bash
# 使用 Claude（推荐）
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
LLM_PROVIDER=claude

# 或使用 OpenAI
OPENAI_API_KEY=sk-xxxxx
LLM_PROVIDER=openai
```

### 步骤 3: 一键启动

```bash
# 启动所有服务（自动拉取最新镜像）
docker compose up -d
# 或使用旧版本: docker-compose up -d

# 查看服务状态
docker compose ps
# 或使用旧版本: docker-compose ps

# 查看日志（等待数据库初始化完成）
docker compose logs -f
# 或使用旧版本: docker-compose logs -f
```

**等待约 30-60 秒**，然后访问：**http://localhost:3000**

---

## ✅ 验证安装

### 1. 检查服务状态

```bash
docker compose ps
# 或使用旧版本: docker-compose ps
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
  "timestamp": "...",
  "service": "cloudlens-api",
  "version": "1.1.0"
}
```

### 3. 访问前端

打开浏览器访问：**http://localhost:3000**

---

## 🎯 使用功能

### AI Chatbot

1. 打开浏览器访问 http://localhost:3000
2. 点击右下角的**蓝色圆形按钮**（AI助手图标）
3. 开始对话，例如：
   - "为什么这个月成本提升了10%？"
   - "有哪些闲置资源可以优化？"

### 折扣分析

1. 访问：http://localhost:3000/a/[账号名]/discounts
2. 查看折扣数据，支持排序、筛选、搜索

### 成本异常检测

通过 API 调用：
```bash
curl -X POST "http://localhost:8000/api/v1/anomaly/detect?account=your_account"
```

### 预算管理

通过 API 调用：
```bash
curl "http://localhost:8000/api/v1/budgets"
```

---

## 🔄 更新到最新版本

```bash
# 1. 拉取最新代码
cd cloudlens
git pull origin main

# 2. 拉取最新镜像
docker compose pull
# 或使用旧版本: docker-compose pull

# 3. 重启服务
docker compose up -d
# 或使用旧版本: docker-compose up -d
```

---

## 🛠️ 常用命令

### 启动服务

```bash
docker-compose up -d
```

### 停止服务

```bash
docker-compose down
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 重启服务

```bash
docker-compose restart
```

---

## 🔧 故障排查

### 问题0: ARM64 (Apple Silicon) 架构问题

**症状**: 错误信息包含 `no matching manifest for linux/arm64/v8`

**解决方案**:
- `docker-compose.yml` 已配置 `platform: linux/amd64`，应该可以自动处理
- 如果仍有问题，查看 [ARM64 支持说明](./ARM64_SUPPORT.md)

### 问题1: 服务无法启动

**可能原因**:
- 端口被占用
- 之前的容器未清理
- 配置错误
- 架构不匹配（ARM64/Apple Silicon）

**解决方案**:
```bash
# 1. 检查端口占用
lsof -i :3000  # 前端端口
lsof -i :8000  # 后端端口
lsof -i :3306  # MySQL端口
lsof -i :6379  # Redis端口

# 2. 如果端口被占用，停止占用端口的服务，或修改 docker-compose.yml 中的端口映射

# 3. 清理并重启
docker compose down
docker compose up -d
# 或使用旧版本: docker-compose down && docker-compose up -d

# 4. 如果仍有问题，查看日志
docker compose logs
```

### 问题1.1: ARM64 (Apple Silicon) 架构问题

**错误信息**:
```
no matching manifest for linux/arm64/v8 in the manifest list entries
```

**解决方案**:
```bash
# 方案1: 使用 Rosetta 2 运行（推荐，已自动配置）
# docker-compose.yml 已添加 platform: linux/amd64 配置
# 直接运行即可：
docker compose up -d

# 方案2: 如果仍有问题，确保 Docker Desktop 已启用 Rosetta
# Docker Desktop → Settings → General → Use Rosetta for x86/amd64 emulation on Apple Silicon

# 方案3: 本地构建镜像（如果镜像不支持 ARM64）
docker compose build
docker compose up -d
```

### 问题2: 前端页面空白

**解决方案**:
```bash
# 查看前端日志
docker compose logs frontend
# 或使用旧版本: docker-compose logs frontend

# 重启前端
docker compose restart frontend
# 或使用旧版本: docker-compose restart frontend
```

### 问题3: AI Chatbot 不工作

**解决方案**:
1. 检查 `.env` 文件中是否配置了 AI API 密钥
2. 验证密钥是否有效
3. 查看后端日志：`docker compose logs backend | grep -i "ai\|llm"`
   # 或使用旧版本: docker-compose logs backend | grep -i "ai\|llm"

### 问题4: 数据库连接失败

**解决方案**:
```bash
# 检查 MySQL 是否运行
docker compose ps mysql
# 或使用旧版本: docker-compose ps mysql

# 查看 MySQL 日志
docker compose logs mysql
# 或使用旧版本: docker-compose logs mysql

# 重启 MySQL
docker compose restart mysql
# 或使用旧版本: docker-compose restart mysql
```

---

## 📚 更多帮助

- **详细使用指南**: [Q1功能使用指南](./Q1_USER_GUIDE.md)
- **本地测试指南**: [本地测试指南](./LOCAL_TESTING_GUIDE.md)
- **Docker Hub 使用**: [Docker Hub 使用指南](./DOCKER_HUB_SETUP.md)

---

**最后更新**: 2026-01-19  
**维护者**: CloudLens Team
