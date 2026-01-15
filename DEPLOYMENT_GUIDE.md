# CloudLens 部署指南

**从GitHub克隆后的完整环境搭建文档**

---

## 📋 目录

1. [缺失内容清单](#缺失内容清单)
2. [系统要求](#系统要求)
3. [完整部署步骤](#完整部署步骤)
4. [配置文件说明](#配置文件说明)
5. [数据库初始化](#数据库初始化)
6. [启动服务](#启动服务)
7. [验证部署](#验证部署)
8. [常见问题](#常见问题)

---

## 🚨 缺失内容清单

从GitHub克隆项目后，以下内容**不会包含**在仓库中（已添加到`.gitignore`）：

### 1. 配置文件（**必须手动创建**）

#### 敏感配置
- ❌ `config/config.json` - 云账号AK/SK配置（⚠️ 敏感信息）
- ❌ `.env` - 环境变量配置（包含数据库密码）

#### 参考模板（仓库包含）
- ✅ `config/config.json.example` - 配置模板
- ✅ `.env.example` - 环境变量模板

### 2. 数据库

- ❌ MySQL数据库实例
- ❌ 数据库schema和初始数据
- ❌ 数据库迁移历史

### 3. 依赖环境

#### Python依赖
- ❌ Python虚拟环境（venv/）
- ❌ 已安装的Python包

#### Node.js依赖
- ❌ `web/frontend/node_modules/` - 前端依赖包
- ❌ `web/frontend/.next/` - Next.js构建缓存

### 4. 开发工具脚本（**需要单独安装**）

- ❌ `~/cloudlens-scripts/` - 开发自动化脚本目录
  - `quick-test.sh` - 快速健康检查
  - `git-safe-commit.sh` - 安全提交
  - `create-stable-tag.sh` - 创建稳定标签
  - `emergency-rollback.sh` - 紧急回滚

### 5. 运行时文件

- ❌ `logs/` - 日志目录
- ❌ `.coverage` - 测试覆盖率数据
- ❌ `htmlcov/` - 覆盖率报告
- ❌ `test-recordings/` - 测试录制文件
- ❌ `*.pkl` - 缓存文件
- ❌ 已生成的报告文件（*.xlsx, *.pdf, *.html）

### 6. 账单数据

- ❌ `bills_data/` - 历史账单数据
- ❌ CSV账单文件

---

## 💻 系统要求

### 必需环境

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| **Python** | ≥ 3.9 | 核心运行环境 |
| **MySQL** | ≥ 5.7 或 8.0+ | 主数据库 |
| **Node.js** | ≥ 18.0 | 前端构建环境 |
| **npm** | ≥ 9.0 | Node包管理器 |

### 可选组件

| 组件 | 用途 | 优先级 |
|------|------|--------|
| **Redis** | L2缓存、Pub/Sub（Q1 Week 4-5后必选） | 中 |
| **Prophet** | AI成本预测 | 低 |

### 操作系统

- ✅ macOS 10.15+
- ✅ Linux (Ubuntu 20.04+, CentOS 8+)
- ⚠️ Windows (需要WSL2或Git Bash)

---

## 📦 完整部署步骤

### 步骤1: 克隆仓库

```bash
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens
```

### 步骤2: 创建Python虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

### 步骤3: 安装Python依赖

```bash
# 安装核心依赖
pip install -r requirements.txt

# 安装开发依赖（可选，用于测试）
pip install -r requirements-dev.txt

# 安装AI预测依赖（可选）
pip install prophet
```

### 步骤4: 安装MySQL数据库

#### macOS (Homebrew)
```bash
brew install mysql
brew services start mysql
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
```

#### Docker (推荐用于开发)
```bash
docker run -d \
  --name cloudlens-mysql \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=cloudlens \
  -e MYSQL_USER=cloudlens \
  -e MYSQL_PASSWORD=cloudlens123 \
  -p 3306:3306 \
  mysql:8.0
```

### 步骤5: 创建数据库

```bash
# 登录MySQL
mysql -u root -p

# 创建数据库和用户
CREATE DATABASE cloudlens CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cloudlens'@'localhost' IDENTIFIED BY 'cloudlens123';
GRANT ALL PRIVILEGES ON cloudlens.* TO 'cloudlens'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 步骤6: 配置环境变量

```bash
# 复制模板
cp .env.example .env

# 编辑.env文件
nano .env  # 或使用你喜欢的编辑器
```

**必须修改的配置**:
```bash
# .env文件中修改以下内容
CLOUDLENS_DATABASE__MYSQL_PASSWORD=cloudlens123  # 改为你的MySQL密码
CLOUDLENS_DATABASE__MYSQL_DATABASE=cloudlens
CLOUDLENS_DATABASE__MYSQL_USER=cloudlens
CLOUDLENS_DATABASE__MYSQL_HOST=localhost
```

### 步骤7: 配置云账号

```bash
# 复制配置模板
cp config/config.json.example config/config.json

# 编辑config.json
nano config/config.json
```

**配置示例**:
```json
{
  "default_tenant": "prod",
  "tenants": {
    "prod": {
      "access_key_id": "YOUR_ALIYUN_ACCESS_KEY_ID",
      "access_key_secret": "YOUR_ALIYUN_ACCESS_KEY_SECRET",
      "display_name": "生产环境"
    }
  }
}
```

⚠️ **重要**:
- 将`YOUR_ALIYUN_ACCESS_KEY_ID`替换为真实的阿里云AccessKey ID
- 将`YOUR_ALIYUN_ACCESS_KEY_SECRET`替换为真实的AccessKey Secret
- **切勿将此文件提交到Git**

### 步骤8: 初始化数据库Schema

```bash
# 运行数据库迁移
python migrations/run_migrations.py

# 或者手动执行SQL文件（如果有）
mysql -u cloudlens -p cloudlens < migrations/schema.sql
```

### 步骤9: 安装前端依赖

```bash
cd web/frontend

# 安装Node.js依赖
npm install

cd ../..
```

### 步骤10: 安装开发脚本（可选但推荐）

```bash
# 创建脚本目录
mkdir -p ~/cloudlens-scripts

# 复制脚本（需要从其他地方获取，或手动创建）
# 注意: 这些脚本不在GitHub仓库中，需要参考DEVELOPMENT_WORKFLOW.md创建

# 给脚本添加执行权限
chmod +x ~/cloudlens-scripts/*.sh
```

**脚本内容参考**: 查看`DEVELOPMENT_WORKFLOW.md`文档获取完整脚本内容

### 步骤11: 创建日志目录

```bash
mkdir -p logs
```

---

## ⚙️ 配置文件说明

### 1. `.env` - 环境变量配置

**位置**: 项目根目录
**作用**: 配置应用运行参数

```bash
# 应用配置
CLOUDLENS_APP_NAME=CloudLens
CLOUDLENS_APP_VERSION=2.1.0
CLOUDLENS_ENVIRONMENT=production  # production/development
CLOUDLENS_DEBUG=false

# 数据库配置（必须修改）
CLOUDLENS_DATABASE__DB_TYPE=mysql
CLOUDLENS_DATABASE__MYSQL_HOST=localhost
CLOUDLENS_DATABASE__MYSQL_PORT=3306
CLOUDLENS_DATABASE__MYSQL_USER=cloudlens
CLOUDLENS_DATABASE__MYSQL_PASSWORD=your_password_here  # ⚠️ 修改这里
CLOUDLENS_DATABASE__MYSQL_DATABASE=cloudlens
CLOUDLENS_DATABASE__POOL_SIZE=20

# 缓存配置
CLOUDLENS_CACHE__DEFAULT_TTL=3600
CLOUDLENS_CACHE__RESOURCE_TTL=3600

# 日志配置
CLOUDLENS_LOGGING__LOG_LEVEL=INFO  # DEBUG/INFO/WARNING/ERROR
CLOUDLENS_LOGGING__LOG_DIR=logs
```

### 2. `config/config.json` - 云账号配置

**位置**: `config/config.json`
**作用**: 配置云平台账号和凭证

```json
{
  "default_tenant": "prod",
  "tenants": {
    "prod": {
      "access_key_id": "LTAI5t...",  // ⚠️ 阿里云AK
      "access_key_secret": "xxx...",  // ⚠️ 阿里云SK
      "display_name": "生产环境"
    },
    "test": {
      "access_key_id": "LTAI5t...",
      "access_key_secret": "xxx...",
      "display_name": "测试环境"
    }
  }
}
```

**支持多账号**: 可以添加多个租户配置

### 3. `config/thresholds.yaml` - 告警阈值配置

**位置**: `config/thresholds.yaml`
**作用**: 配置资源使用率告警阈值

这个文件**已包含在仓库中**，可根据需要修改：

```yaml
# ECS实例告警阈值
ecs:
  cpu_idle_threshold: 10    # CPU低于10%视为闲置
  memory_idle_threshold: 20  # 内存低于20%视为闲置
  idle_days: 7              # 持续7天低使用率

# RDS数据库告警阈值
rds:
  cpu_idle_threshold: 10
  connection_idle_threshold: 5
  idle_days: 7
```

---

## 🗄️ 数据库初始化

### 方法1: 使用迁移脚本（推荐）

```bash
# 运行迁移
python migrations/run_migrations.py

# 查看迁移状态
python migrations/run_migrations.py --status
```

### 方法2: 手动导入Schema

```bash
# 如果有SQL文件
mysql -u cloudlens -p cloudlens < migrations/schema.sql
```

### 数据库表结构（核心表）

| 表名 | 说明 | 用途 |
|------|------|------|
| `accounts` | 云账号表 | 存储租户信息 |
| `instances` | 资源实例表 | ECS/RDS等资源 |
| `bill_items` | 账单明细表 | 成本数据 |
| `cache_metadata` | 缓存元数据 | L3缓存管理 |
| `security_findings` | 安全发现 | 安全扫描结果 |
| `optimization_recommendations` | 优化建议 | 智能推荐 |

### 验证数据库

```bash
# 登录数据库
mysql -u cloudlens -p cloudlens

# 查看表
SHOW TABLES;

# 应该看到类似输出
+----------------------+
| Tables_in_cloudlens  |
+----------------------+
| accounts             |
| bill_items           |
| cache_metadata       |
| instances            |
| ...                  |
+----------------------+
```

---

## 🚀 启动服务

### 启动后端服务

```bash
# 方法1: 使用启动脚本
./scripts/start_backend.sh

# 方法2: 手动启动
cd web/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端服务启动在: `http://localhost:8000`

### 启动前端服务

```bash
# 方法1: 使用启动脚本
./scripts/start_frontend.sh

# 方法2: 手动启动
cd web/frontend
npm run dev
```

前端服务启动在: `http://localhost:3000`

### 一键启动（推荐）

```bash
# 同时启动前后端
./scripts/start_web.sh
```

### 后台运行（生产环境）

```bash
# 后端
cd web/backend
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > ../../logs/backend.log 2>&1 &

# 前端
cd web/frontend
npm run build
npm run start > ../../logs/frontend.log 2>&1 &
```

---

## ✅ 验证部署

### 1. 检查后端健康

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 期望输出
{"status":"healthy","version":"2.1.0"}
```

### 2. 检查API可用性

```bash
# 账号列表API
curl http://127.0.0.1:8000/api/accounts

# 期望输出（账号列表）
[{"name":"prod","display_name":"生产环境",...}]
```

### 3. 检查前端

浏览器访问: `http://localhost:3000`

应该看到CloudLens登录界面或仪表板

### 4. 运行完整测试（如果安装了开发脚本）

```bash
~/cloudlens-scripts/quick-test.sh
```

**期望输出**:
```
🚀 CloudLens 快速健康检查
======================================
测试：后端健康检查 ... ✅ 通过
测试：前端服务检查 ... ✅ 通过
测试：账号列表API ... ✅ 通过
测试：Dashboard摘要API ... ✅ 通过
测试：成本分析API ... ✅ 通过
======================================
🎉 所有测试通过！系统运行正常。
```

---

## 🐛 常见问题

### 问题1: 数据库连接失败

**错误**: `Can't connect to MySQL server on 'localhost'`

**解决方案**:
```bash
# 检查MySQL是否运行
sudo systemctl status mysql  # Linux
brew services list | grep mysql  # macOS

# 检查.env配置
cat .env | grep MYSQL

# 测试数据库连接
mysql -u cloudlens -p -h localhost cloudlens
```

### 问题2: 前端启动失败

**错误**: `Error: Cannot find module 'next'`

**解决方案**:
```bash
cd web/frontend
rm -rf node_modules package-lock.json
npm install
```

### 问题3: Python包导入错误

**错误**: `ModuleNotFoundError: No module named 'xxx'`

**解决方案**:
```bash
# 确认虚拟环境已激活
source venv/bin/activate

# 重新安装依赖
pip install -r requirements.txt
```

### 问题4: 端口被占用

**错误**: `Address already in use: 8000` 或 `3000`

**解决方案**:
```bash
# 查找占用端口的进程
lsof -ti:8000  # 后端
lsof -ti:3000  # 前端

# 杀死进程
kill -9 $(lsof -ti:8000)
```

### 问题5: MySQL连接池错误

**错误**: `MySQLConnectionPool() got multiple values for keyword argument 'autocommit'`

**解决方案**:
这个bug已在最新版本修复。如果遇到，更新`core/database.py`:

```python
# 移除self.config中的autocommit配置
self.config = {
    'host': config.get('host', 'localhost'),
    'port': config.get('port', 3306),
    'user': config.get('user', 'cloudlens'),
    'password': config.get('password', ''),
    'database': config.get('database', 'cloudlens'),
    'charset': config.get('charset', 'utf8mb4'),
    'collation': config.get('collation', 'utf8mb4_unicode_ci'),
    # 移除这行: 'autocommit': False,
}
```

### 问题6: 阿里云API调用失败

**错误**: `InvalidAccessKeyId.NotFound`

**解决方案**:
```bash
# 检查config.json配置
cat config/config.json

# 验证AK/SK格式正确
# AccessKey ID格式: LTAI5t开头，24位
# AccessKey Secret: 30位随机字符串

# 测试AK/SK（使用CLI）
./cl config list
```

---

## 📚 下一步

部署完成后，你可以：

1. **阅读完整文档**:
   - `DEVELOPMENT_PLAN_2026_CLAUDE.md` - AI增强版开发规划
   - `DEVELOPMENT_WORKFLOW.md` - 开发工作流程
   - `README.md` - 项目概览

2. **运行CLI命令**:
   ```bash
   ./cl analyze idle --account prod       # 分析闲置资源
   ./cl analyze security --account prod   # 安全检查
   ./cl analyze forecast --days 90        # 成本预测
   ```

3. **访问Web界面**: `http://localhost:3000`

4. **开始开发**: 按照`DEVELOPMENT_PLAN_2026_CLAUDE.md`的Q1规划开始实施AI功能

---

## 🔐 安全建议

1. **敏感信息管理**:
   - ❌ 永远不要将`.env`和`config/config.json`提交到Git
   - ✅ 使用环境变量或密钥管理系统（如AWS Secrets Manager）
   - ✅ 定期轮换AccessKey

2. **生产环境部署**:
   - 使用HTTPS（反向代理Nginx/Caddy）
   - 配置防火墙规则
   - 启用MySQL SSL连接
   - 配置日志轮转

3. **最小权限原则**:
   - 为CloudLens创建只读或最小权限的云账号
   - 不要使用主账号的AK/SK

---

## 📞 获取帮助

- **GitHub Issues**: https://github.com/songqipeng/cloudlens/issues
- **文档中心**: https://songqipeng.github.io/cloudlens/
- **邮件支持**: support@cloudlens.ai

---

**文档版本**: 1.0.0
**最后更新**: 2026-01-15
**适用版本**: CloudLens 2.1.0+
