# CloudLens 快速开始指南

> **版本**: 2.0  
> **更新日期**: 2026-01-19  
> **适用场景**: 新开发者快速上手、普通用户快速启动

---

## 🎯 两种使用场景

### 场景1: 普通用户（只想快速使用）

**目标**: 最快速度启动 CloudLens，无需了解开发细节

👉 **推荐**: 使用 Docker Compose（3步搞定）

### 场景2: 开发者（需要开发和测试）

**目标**: 本地开发环境，可以修改代码并实时看到效果

👉 **推荐**: 本地开发环境（适合开发调试）

---

## 🚀 场景1: 普通用户快速启动（推荐）

### 前置条件

- ✅ 已安装 Docker 和 Docker Compose
- ✅ 有 AI API 密钥（Claude 或 OpenAI）

### 3步启动

```bash
# 1. 下载最新代码
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens

# 2. 配置环境变量（至少配置AI API密钥）
cp .env.example .env
# 编辑 .env，添加：
# ANTHROPIC_API_KEY=your_claude_api_key
# LLM_PROVIDER=claude

# 3. 一键启动（自动拉取Docker镜像）
docker-compose up -d
```

### 访问应用

- **前端**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

### 查看服务状态

```bash
# 查看所有服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 🛠️ 场景2: 开发者本地开发环境

### 前置条件

- ✅ Python 3.11+
- ✅ Node.js 20+
- ✅ MySQL 8.0+（或使用 Docker 启动 MySQL）

### 完整步骤

#### 1. 下载最新代码

```bash
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens

# 拉取最新代码
git pull origin main
```

#### 2. 启动 MySQL（如果使用 MySQL）

**选项A: 使用 Docker 启动 MySQL（推荐）**

```bash
docker run -d \
  --name cloudlens-mysql \
  -e MYSQL_ROOT_PASSWORD=cloudlens_root_2024 \
  -e MYSQL_DATABASE=cloudlens \
  -e MYSQL_USER=cloudlens \
  -e MYSQL_PASSWORD=cloudlens123 \
  -p 3306:3306 \
  mysql:8.0

# 等待MySQL启动（约10秒）
sleep 10

# 初始化数据库
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/init_mysql_schema.sql
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_chatbot_tables.sql
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_anomaly_table.sql
```

**选项B: 使用本地 MySQL**

```bash
# macOS
brew services start mysql

# 创建数据库和用户
mysql -u root -p <<EOF
CREATE DATABASE cloudlens CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cloudlens'@'localhost' IDENTIFIED BY 'cloudlens123';
GRANT ALL PRIVILEGES ON cloudlens.* TO 'cloudlens'@'localhost';
FLUSH PRIVILEGES;
EOF

# 初始化数据库
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/init_mysql_schema.sql
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_chatbot_tables.sql
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_anomaly_table.sql
```

#### 3. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装前端依赖
cd web/frontend
npm install
cd ../..
```

#### 4. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，至少配置：
# - AI API密钥（ANTHROPIC_API_KEY 或 OPENAI_API_KEY）
# - 数据库配置（如果使用MySQL）
```

#### 5. 启动服务

**终端1 - 启动后端**:
```bash
cd web/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**终端2 - 启动前端**:
```bash
cd web/frontend
npm run dev
```

#### 6. 访问应用

- **前端**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

---

## 📋 快速启动脚本（普通用户）

我们提供了一个一键启动脚本：

```bash
# 下载代码
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens

# 运行快速启动脚本
./scripts/quick-start.sh
```

脚本会自动：
1. 检查 Docker 是否安装
2. 配置环境变量（如果不存在）
3. 启动所有服务
4. 显示访问地址

---

## 🔄 更新到最新版本

### 普通用户（Docker方式）

```bash
# 进入项目目录
cd cloudlens

# 拉取最新代码
git pull origin main

# 拉取最新Docker镜像
docker-compose pull

# 重启服务
docker-compose up -d
```

### 开发者（本地环境）

```bash
# 拉取最新代码
git pull origin main

# 更新Python依赖（如果有新依赖）
pip install -r requirements.txt

# 更新前端依赖（如果有新依赖）
cd web/frontend
npm install
cd ../..

# 重启服务（停止并重新启动）
```

---

## ✅ 验证安装

### 1. 检查服务状态

**Docker方式**:
```bash
docker-compose ps
# 所有服务应该显示为 "Up"
```

**本地方式**:
```bash
# 检查后端
curl http://localhost:8000/health
# 应该返回: {"status":"healthy",...}

# 检查前端
curl http://localhost:3000
# 应该返回HTML内容
```

### 2. 访问前端

打开浏览器访问：http://localhost:3000

### 3. 测试AI Chatbot

1. 在页面右下角找到蓝色圆形按钮
2. 点击打开AI助手
3. 输入问题测试

---

## 🐛 常见问题

### 问题1: Docker镜像拉取失败

**症状**: `Error response from daemon: pull access denied`

**解决方案**:
```bash
# 检查网络连接
ping hub.docker.com

# 手动拉取镜像
docker pull songqipeng/cloudlens-backend:latest
docker pull songqipeng/cloudlens-frontend:latest
```

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
lsof -i :8000  # 后端端口
lsof -i :3000  # 前端端口
```

### 问题3: 数据库连接失败

**症状**: 后端日志显示数据库连接错误

**解决方案**:
```bash
# 检查MySQL是否运行
docker-compose ps mysql  # Docker方式
brew services list | grep mysql  # 本地方式

# 测试数据库连接
mysql -u cloudlens -pcloudlens123 -h localhost cloudlens -e "SELECT 1;"
```

### 问题4: AI Chatbot不工作

**症状**: AI功能返回错误

**解决方案**:
1. 检查 `.env` 文件中是否配置了 AI API 密钥
2. 验证密钥是否有效
3. 查看后端日志：`docker-compose logs backend | grep -i "ai\|llm"`

---

## 📚 相关文档

- [Docker Hub 使用指南](./DOCKER_HUB_SETUP.md) - Docker镜像使用说明
- [本地测试指南](./LOCAL_TESTING_GUIDE.md) - 详细测试步骤
- [Q1功能使用指南](./Q1_USER_GUIDE.md) - Q1功能详细说明
- [开发指南](./DEVELOPMENT_GUIDE.md) - 开发者文档

---

**最后更新**: 2026-01-19  
**维护者**: CloudLens Team
