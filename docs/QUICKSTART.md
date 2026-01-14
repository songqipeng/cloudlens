# CloudLens 快速开始指南

本指南将帮助您在 5 分钟内快速上手 CloudLens。

---

## 📋 前置要求

- **Python**: 3.8 或更高版本
- **Node.js**: 18+ （仅 Web 界面需要）
- **MySQL**: 5.7+ 或 8.0+ （推荐）
- **操作系统**: macOS, Linux, Windows

---

## 🚀 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt

# 可选：安装 AI 预测依赖
pip install prophet
```

### 3. 配置 MySQL 数据库

#### 3.1 创建数据库

```bash
mysql -u root -p
```

```sql
CREATE DATABASE cloudlens CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cloudlens'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON cloudlens.* TO 'cloudlens'@'localhost';
FLUSH PRIVILEGES;
```

#### 3.2 初始化表结构

```bash
mysql -u cloudlens -p cloudlens < sql/init_mysql_schema.sql
```

#### 3.3 配置环境变量

创建 `~/.cloudlens/.env` 文件：

```bash
mkdir -p ~/.cloudlens
cat > ~/.cloudlens/.env << EOF
DB_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=cloudlens
MYSQL_CHARSET=utf8mb4
EOF
```

### 4. 配置云账号

```bash
# 添加阿里云账号
./cl config add \
  --provider aliyun \
  --name prod \
  --region cn-hangzhou \
  --ak YOUR_ACCESS_KEY \
  --sk YOUR_SECRET_KEY

# 查看已配置账号
./cl config list
```

---

## 🎯 快速体验

### CLI 命令行方式

#### 1. 查询资源

```bash
# 查询 ECS 实例
./cl query ecs --account prod

# 查询 RDS 数据库
./cl query rds --account prod

# 导出为 JSON
./cl query ecs --account prod --format json --output ecs.json
```

#### 2. 分析功能

```bash
# 闲置资源分析
./cl analyze idle --account prod

# 成本趋势分析
./cl analyze cost --account prod --trend

# AI 成本预测
./cl analyze forecast --account prod --days 90

# 折扣趋势分析
./cl analyze discount --export

# CIS 安全合规检查
./cl analyze security --account prod --cis
```

#### 3. 账单管理

```bash
# 测试账单 API 连接
./cl bill test --account prod

# 获取最近 3 个月账单
./cl bill fetch --account prod

# 获取指定时间范围账单
./cl bill fetch --account prod --start 2025-01 --end 2025-06
```

#### 4. 自动修复

```bash
# 批量打标签（干运行，不会实际修改）
./cl remediate tags --account prod

# 实际执行修复
./cl remediate tags --account prod --confirm

# 查看修复历史
./cl remediate history
```

---

### Web 界面方式

#### 1. 启动后端服务

```bash
cd web/backend
python -m uvicorn main:app --reload --port 8000
```

后端服务将在 `http://127.0.0.1:8000` 启动。

#### 2. 启动前端服务（新终端）

```bash
cd web/frontend
npm install
npm run dev
```

前端服务将在 `http://localhost:3000` 启动。

#### 3. 访问界面

打开浏览器访问 http://localhost:3000

---

## 📖 下一步

- 查看 [用户指南](USER_GUIDE.md) 了解详细功能
- 查看 [产品能力总览](PRODUCT_CAPABILITIES.md) 了解所有功能
- 查看 [快速参考](QUICK_REFERENCE.md) 快速查找命令

---

## ❓ 常见问题

### Q: 如何验证安装是否成功？

```bash
./cl --version
./cl config list
```

### Q: MySQL 连接失败怎么办？

1. 检查 MySQL 服务是否运行：`mysqladmin ping`
2. 检查环境变量配置：`cat ~/.cloudlens/.env`
3. 测试连接：`mysql -u cloudlens -p cloudlens`

### Q: 如何查看日志？

日志文件位置：`~/.cloudlens/logs/cloudlens.log`

### Q: Web 界面无法访问？

1. 检查后端是否运行：`curl http://127.0.0.1:8000/health`
2. 检查前端是否运行：访问 http://localhost:3000
3. 查看浏览器控制台错误信息

---

**祝您使用愉快！🎉**
