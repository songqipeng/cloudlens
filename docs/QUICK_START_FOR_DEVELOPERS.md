# CloudLens 开发者快速开始指南

> **版本**: 1.0  
> **更新日期**: 2026-01-19  
> **适用对象**: 开发者，需要本地开发环境进行开发和测试

---

## 🚀 快速开始（5分钟）

### 前置条件

- ✅ Git 已安装
- ✅ Python 3.11+ 已安装
- ✅ Node.js 20+ 已安装
- ✅ MySQL 8.0+ 已安装（或使用 Docker）
- ✅ Docker 和 Docker Compose（可选，用于数据库）

---

## 📥 步骤 1: 下载最新代码

```bash
# 克隆仓库
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens

# 确保使用最新代码
git pull origin main

# 查看当前分支和最新提交
git log --oneline -5
```

---

## 🔧 步骤 2: 配置开发环境

### 2.1 安装 Python 依赖

```bash
# 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2.2 安装前端依赖

```bash
cd web/frontend
npm install
cd ../..
```

### 2.3 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

**必需配置**:
```bash
# 数据库配置（如果使用本地MySQL）
DB_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=cloudlens123
MYSQL_DATABASE=cloudlens

# AI服务配置（至少一个）
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
LLM_PROVIDER=claude
```

### 2.4 配置云账号（如需要）

```bash
# 创建配置目录
mkdir -p config

# 复制配置模板
cp config/config.json.example config/config.json

# 编辑配置文件
nano config/config.json
```

---

## 🗄️ 步骤 3: 启动数据库

### 方式 A: 使用 Docker（推荐，最简单）

```bash
# 启动 MySQL
docker run -d \
  --name cloudlens-mysql \
  -e MYSQL_ROOT_PASSWORD=cloudlens_root_2024 \
  -e MYSQL_DATABASE=cloudlens \
  -e MYSQL_USER=cloudlens \
  -e MYSQL_PASSWORD=cloudlens123 \
  -p 3306:3306 \
  mysql:8.0

# 等待 MySQL 启动（约10秒）
sleep 10

# 初始化数据库
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/init_mysql_schema.sql
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_chatbot_tables.sql
mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_anomaly_table.sql
```

### 方式 B: 使用本地 MySQL

```bash
# macOS (Homebrew)
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

**注意**: 如果本地没有安装 `mysql` 客户端，可以使用 Docker 容器内的命令：
```bash
# 使用 Docker 容器执行 SQL
docker exec -i cloudlens-mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/init_mysql_schema.sql
docker exec -i cloudlens-mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_chatbot_tables.sql
docker exec -i cloudlens-mysql mysql -u cloudlens -pcloudlens123 cloudlens < migrations/add_anomaly_table.sql
```

---

## 🚀 步骤 4: 启动开发服务

### 启动后端（终端 1）

```bash
cd web/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

后端将在 `http://localhost:8000` 启动，支持热重载。

### 启动前端（终端 2）

```bash
cd web/frontend
npm run dev
```

前端将在 `http://localhost:3000` 启动，支持热重载。

---

## ✅ 步骤 5: 验证开发环境

### 1. 检查后端

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

### 2. 检查前端

打开浏览器访问：**http://localhost:3000**

### 3. 检查 API 文档

访问：**http://localhost:8000/docs**

---

## 🔄 获取最新代码

### 日常更新

```bash
# 拉取最新代码
git pull origin main

# 如果有新的依赖，更新
pip install -r requirements.txt
cd web/frontend && npm install && cd ../..
```

### 检查更新

```bash
# 查看远程更新
git fetch origin
git log HEAD..origin/main --oneline

# 如果有更新，拉取
git pull origin main
```

---

## 🧪 开发工作流

### 1. 创建功能分支

```bash
# 从 main 分支创建新分支
git checkout -b feature/your-feature-name

# 或使用日期命名
git checkout -b dev/$(date +%Y%m%d)-feature-name
```

### 2. 开发功能

```bash
# 修改代码
# ...

# 测试功能
# 在浏览器中测试前端
# 使用 curl 或 Postman 测试 API

# 提交更改
git add .
git commit -m "feat: 添加新功能"
```

### 3. 推送并创建 PR

```bash
# 推送到远程
git push origin feature/your-feature-name

# 在 GitHub 上创建 Pull Request
```

---

## 🧪 运行测试

### Python 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/core/test_cache.py

# 运行并查看覆盖率
pytest --cov=cloudlens.core --cov-report=html
```

### 前端测试

```bash
cd web/frontend

# 运行 Playwright 测试
npx playwright test

# 运行特定测试
npx playwright test tests/test-chatbot-display.spec.ts
```

### 代码检查

```bash
# Python 代码检查（如果安装了 ruff）
ruff check .

# TypeScript 类型检查
cd web/frontend
npm run build  # 这会进行类型检查
```

---

## 🐛 调试技巧

### 后端调试

```bash
# 使用 Python 调试器
import pdb; pdb.set_trace()

# 查看日志
# 日志会在终端输出（使用 --reload 模式）
```

### 前端调试

```bash
# 使用浏览器开发者工具
# F12 → Console 标签查看日志
# F12 → Network 标签查看 API 请求
# F12 → Elements 标签检查 DOM
```

### 数据库调试

```bash
# 连接数据库
mysql -u cloudlens -pcloudlens123 cloudlens

# 查看表
SHOW TABLES;

# 查看数据
SELECT * FROM chat_sessions LIMIT 10;
```

---

## 📦 使用 Docker 镜像（可选）

如果您想使用预构建的 Docker 镜像而不是本地开发：

```bash
# 使用 docker-compose 启动（自动拉取镜像）
docker-compose up -d

# 查看日志
docker-compose logs -f
```

---

## 🔍 常见问题

### 问题1: 端口被占用

**解决方案**:
```bash
# 检查端口占用
lsof -i :8000
lsof -i :3000

# 修改端口
# 后端：修改 uvicorn 命令的 --port 参数
# 前端：修改 package.json 中的 dev 脚本
```

### 问题2: 数据库连接失败

**解决方案**:
```bash
# 检查 MySQL 是否运行
docker ps | grep mysql
# 或
brew services list | grep mysql

# 测试连接（如果本地有 mysql 客户端）
mysql -u cloudlens -pcloudlens123 -h localhost cloudlens -e "SELECT 1;"

# 或使用 Docker 容器测试连接
docker exec cloudlens-mysql mysql -u cloudlens -pcloudlens123 cloudlens -e "SELECT 1;"
```

### 问题3: 前端构建失败

**解决方案**:
```bash
cd web/frontend
rm -rf .next node_modules
npm install
npm run build
```

### 问题4: 依赖安装失败

**解决方案**:
```bash
# Python 依赖
pip install --upgrade pip
pip install -r requirements.txt

# 如果遇到编译错误，可能需要安装系统依赖
# macOS
brew install mysql-client

# Ubuntu/Debian
sudo apt-get install default-libmysqlclient-dev

# 前端依赖
cd web/frontend
rm -rf node_modules package-lock.json
npm install
```

---

## 📚 相关文档

- **用户快速开始**: [用户快速开始指南](./QUICK_START_FOR_USERS.md)
- **开发指南**: [开发指南](./DEVELOPMENT_GUIDE.md)
- **代码规范**: [代码规范](./.cursorrules)
- **测试指南**: [测试指南](./TESTING_GUIDE.md)
- **API 文档**: http://localhost:8000/docs（启动后端后）

---

## 🎯 开发检查清单

开始开发前，请确认：

- [ ] 代码已更新到最新版本（`git pull origin main`）
- [ ] 虚拟环境已激活
- [ ] Python 依赖已安装
- [ ] 前端依赖已安装
- [ ] 数据库已启动并初始化
- [ ] 环境变量已配置（`.env` 文件）
- [ ] 后端服务可以启动
- [ ] 前端服务可以启动
- [ ] 可以访问 http://localhost:3000

---

**最后更新**: 2026-01-19  
**维护者**: CloudLens Team
