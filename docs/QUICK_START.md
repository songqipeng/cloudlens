# CloudLens 快速开始指南

> **版本**: 2.0  
> **更新日期**: 2026-01-19  
> **适用对象**: 所有用户（统一流程）

---

## 🚀 3步快速启动

### 前置条件

- ✅ 已安装 Docker 和 Docker Compose
- ✅ 已安装 Git
- ✅ 有 AI API 密钥（Claude 或 OpenAI）

---

## 步骤 1: 下载代码

```bash
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens
```

---

## 步骤 2: 配置环境变量

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

---

## 步骤 3: 一键启动

```bash
# 使用智能启动脚本（自动检测架构、拉取镜像、启动服务）
./scripts/start.sh
```

脚本会自动：
- ✅ 检测代码是否有更新（自动询问是否拉取）
- ✅ 检测 CPU 架构（ARM64/AMD64）
- ✅ 检测运行中的服务（自动询问是否重启）
- ✅ 拉取或构建相应平台的镜像
- ✅ 启动所有服务

**等待约 30-60 秒**，然后访问：**http://localhost:3000**

---

## ✅ 验证安装

### 1. 检查服务状态

```bash
docker compose ps
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

## 🔄 更新到最新版本

```bash
cd cloudlens
./scripts/start.sh
```

脚本会自动：
- ✅ 检测代码是否有更新
- ✅ 询问是否拉取最新代码（默认 Y）
- ✅ 检测运行中的服务
- ✅ 询问是否重启服务
- ✅ 拉取最新镜像
- ✅ 启动服务

> 📖 **详细更新指南**: 查看 [更新指南](./UPDATE_GUIDE.md)

---

## 🛠️ 常用命令

### 启动服务

```bash
./scripts/start.sh
```

### 停止服务

```bash
docker compose down
```

### 查看日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f backend
docker compose logs -f frontend
```

### 重启服务

```bash
docker compose restart
```

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

## 🔧 故障排查

### 问题1: 服务无法启动

**可能原因**:
- 端口被占用
- 之前的容器未清理
- 配置错误

**解决方案**:
```bash
# 1. 检查端口占用
lsof -i :3000  # 前端端口
lsof -i :8000  # 后端端口
lsof -i :3306  # MySQL端口
lsof -i :6379  # Redis端口

# 2. 清理并重启
docker compose down
./scripts/start.sh
```

### 问题2: 前端页面空白

**解决方案**:
```bash
# 查看前端日志
docker compose logs frontend

# 重启前端
docker compose restart frontend
```

### 问题3: AI Chatbot 不工作

**解决方案**:
1. 检查 `.env` 文件中是否配置了 AI API 密钥
2. 验证密钥是否有效
3. 查看后端日志：`docker compose logs backend | grep -i "ai\|llm"`

### 问题4: 数据库连接失败

**解决方案**:
```bash
# 检查 MySQL 是否运行
docker compose ps mysql

# 查看 MySQL 日志
docker compose logs mysql

# 重启 MySQL
docker compose restart mysql
```

### 问题5: 架构相关问题

**如果遇到架构相关错误，使用智能启动脚本**:

```bash
./scripts/start.sh
```

脚本会自动：
- 检测您的系统架构
- 选择正确的平台（ARM64 或 AMD64）
- 拉取或构建相应镜像
- 启动服务

---

## 💻 开发相关

### 本地开发环境

如果您需要修改代码并实时看到效果：

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 安装前端依赖
cd web/frontend && npm install && cd ../..

# 3. 启动数据库（使用 Docker）
docker run -d --name cloudlens-mysql \
  -e MYSQL_ROOT_PASSWORD=cloudlens_root_2024 \
  -e MYSQL_DATABASE=cloudlens \
  -e MYSQL_USER=cloudlens \
  -e MYSQL_PASSWORD=cloudlens123 \
  -p 3306:3306 mysql:8.0

# 4. 初始化数据库
sleep 10
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/init_mysql_schema.sql
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_chatbot_tables.sql
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_anomaly_table.sql

# 5. 启动开发服务
# 终端1 - 后端（支持热重载）
cd web/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 终端2 - 前端（支持热重载）
cd web/frontend
npm run dev
```

> 📖 **详细开发指南**: 查看 [开发者快速开始指南](./QUICK_START_FOR_DEVELOPERS.md)（可选）

---

## 📚 相关文档

- **更新指南**: [更新指南](./UPDATE_GUIDE.md)
- **Q1功能使用**: [Q1功能使用指南](./Q1_USER_GUIDE.md)
- **本地测试**: [本地测试指南](./LOCAL_TESTING_GUIDE.md)
- **Docker Hub**: [Docker Hub 使用指南](./DOCKER_HUB_SETUP.md)

---

**最后更新**: 2026-01-19  
**维护者**: CloudLens Team
