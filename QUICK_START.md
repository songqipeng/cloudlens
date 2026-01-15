# CloudLens 5分钟快速启动指南

**适用场景**: 只有阿里云AK/SK，没有数据库

---

## 🚀 最快启动方案（3步搞定）

### 前置条件
- ✅ 有阿里云AccessKey ID和AccessKey Secret
- ✅ 已安装Docker（推荐）或愿意手动安装MySQL
- ✅ 已安装Python 3.9+和Node.js 18+

---

## 方案A：使用Docker（推荐，最简单）

### 步骤1: 一键启动MySQL数据库

```bash
# 启动MySQL容器（会自动创建数据库和用户）
docker run -d \
  --name cloudlens-mysql \
  -e MYSQL_ROOT_PASSWORD=cloudlens_root_2024 \
  -e MYSQL_DATABASE=cloudlens \
  -e MYSQL_USER=cloudlens \
  -e MYSQL_PASSWORD=cloudlens123 \
  -p 3306:3306 \
  --restart unless-stopped \
  mysql:8.0

# 验证MySQL已启动
docker ps | grep cloudlens-mysql
```

**数据库信息**（记住这些，下一步要用）:
```
数据库地址: localhost
端口: 3306
数据库名: cloudlens
用户名: cloudlens
密码: cloudlens123
```

### 步骤2: 配置CloudLens

#### 2.1 配置环境变量

```bash
# 在项目根目录
cd /Users/mac/cloudlens

# 复制环境变量模板
cp .env.example .env

# 编辑.env（密码已经自动配置好了）
# 不需要改，Docker已经用这个密码了！
```

**.env文件内容**（已经配置好，无需修改）:
```bash
CLOUDLENS_DATABASE__MYSQL_HOST=localhost
CLOUDLENS_DATABASE__MYSQL_PORT=3306
CLOUDLENS_DATABASE__MYSQL_USER=cloudlens
CLOUDLENS_DATABASE__MYSQL_PASSWORD=cloudlens123  # Docker已设置
CLOUDLENS_DATABASE__MYSQL_DATABASE=cloudlens
```

#### 2.2 配置阿里云账号

```bash
# 复制配置模板
cp config/config.json.example config/config.json

# 编辑config.json
nano config/config.json  # 或用任何编辑器
```

**填入你的真实AK/SK**:
```json
{
  "default_tenant": "ydzn",
  "tenants": {
    "ydzn": {
      "access_key_id": "LTAI5t...",  // 👈 改成你的AK
      "access_key_secret": "xxxxx...",  // 👈 改成你的SK
      "display_name": "云账号"
    }
  }
}
```

### 步骤3: 初始化并启动

```bash
# 3.1 安装Python依赖
pip install -r requirements.txt

# 3.2 初始化数据库表结构
python migrations/run_migrations.py

# 3.3 安装前端依赖
cd web/frontend && npm install && cd ../..

# 3.4 启动服务
./scripts/start_web.sh
```

**访问**: `http://localhost:3000`

---

## 方案B：不用Docker（手动安装MySQL）

### 步骤1: 安装MySQL

#### macOS (Homebrew)
```bash
brew install mysql
brew services start mysql

# 设置root密码
mysql_secure_installation
# 按提示设置root密码为: cloudlens_root_2024
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql

# 设置root密码
sudo mysql_secure_installation
```

### 步骤2: 创建数据库和用户

```bash
# 登录MySQL
mysql -u root -p
# 输入密码: cloudlens_root_2024

# 在MySQL命令行执行:
CREATE DATABASE cloudlens CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cloudlens'@'localhost' IDENTIFIED BY 'cloudlens123';
GRANT ALL PRIVILEGES ON cloudlens.* TO 'cloudlens'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 步骤3: 配置和启动

**剩余步骤同方案A的步骤2和步骤3**

---

## 🔍 验证一切正常

### 1. 检查数据库连接

```bash
# 测试能否连接数据库
mysql -u cloudlens -p cloudlens
# 输入密码: cloudlens123

# 在MySQL里查看表
SHOW TABLES;
# 应该看到 accounts, bill_items, instances 等表
```

### 2. 检查后端API

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 应该返回:
{"status":"healthy","version":"2.1.0"}

# 检查账号API
curl http://127.0.0.1:8000/api/accounts

# 应该返回你的云账号列表
[{"name":"ydzn",...}]
```

### 3. 访问前端

浏览器打开: `http://localhost:3000`

---

## 🛠️ Docker常用命令（方案A适用）

```bash
# 查看MySQL容器状态
docker ps | grep cloudlens-mysql

# 查看MySQL日志
docker logs cloudlens-mysql

# 停止MySQL
docker stop cloudlens-mysql

# 启动MySQL
docker start cloudlens-mysql

# 重启MySQL
docker restart cloudlens-mysql

# 进入MySQL容器
docker exec -it cloudlens-mysql mysql -u cloudlens -p
# 输入密码: cloudlens123

# 完全删除MySQL容器（危险！会删除所有数据）
docker stop cloudlens-mysql
docker rm cloudlens-mysql
docker volume prune  # 清理数据卷
```

---

## ❓ 常见问题

### Q1: 没有Docker怎么办？

**A**: 使用方案B手动安装MySQL，或者安装Docker:
```bash
# macOS
brew install --cask docker

# Ubuntu
sudo apt install docker.io docker-compose

# Windows
# 下载Docker Desktop: https://www.docker.com/products/docker-desktop
```

### Q2: Docker启动MySQL失败？

**A**: 可能端口被占用
```bash
# 检查3306端口
lsof -i:3306

# 如果被占用，停止占用的进程或使用其他端口
docker run -d \
  --name cloudlens-mysql \
  -e MYSQL_ROOT_PASSWORD=cloudlens_root_2024 \
  -e MYSQL_DATABASE=cloudlens \
  -e MYSQL_USER=cloudlens \
  -e MYSQL_PASSWORD=cloudlens123 \
  -p 3307:3306 \  # 👈 改用3307端口
  mysql:8.0

# 修改.env文件
CLOUDLENS_DATABASE__MYSQL_PORT=3307  # 改成3307
```

### Q3: 忘记MySQL密码了？

**A**: 使用Docker方案的话，密码就是 `cloudlens123`，忘了就看这个文档！

### Q4: 数据库初始化失败？

**A**: 手动执行SQL
```bash
# 导出schema（如果有）
mysql -u cloudlens -p cloudlens < migrations/schema.sql

# 或者查看migrations目录的SQL文件
ls migrations/
```

### Q5: 我想修改密码可以吗？

**A**: 可以，但要同时改3个地方:
1. Docker启动命令的 `MYSQL_PASSWORD=新密码`
2. `.env`文件的 `CLOUDLENS_DATABASE__MYSQL_PASSWORD=新密码`
3. 数据库用户密码:
   ```sql
   ALTER USER 'cloudlens'@'localhost' IDENTIFIED BY '新密码';
   ```

---

## 📦 完整启动脚本（一键复制粘贴）

```bash
#!/bin/bash
# CloudLens 一键启动脚本

echo "🚀 CloudLens 快速启动"
echo "===================="

# 1. 启动MySQL（Docker）
echo "📦 启动MySQL数据库..."
docker run -d \
  --name cloudlens-mysql \
  -e MYSQL_ROOT_PASSWORD=cloudlens_root_2024 \
  -e MYSQL_DATABASE=cloudlens \
  -e MYSQL_USER=cloudlens \
  -e MYSQL_PASSWORD=cloudlens123 \
  -p 3306:3306 \
  --restart unless-stopped \
  mysql:8.0

sleep 10  # 等待MySQL启动

# 2. 配置环境变量
echo "⚙️  配置环境变量..."
cp .env.example .env

# 3. 配置云账号（需要手动填AK/SK）
if [ ! -f config/config.json ]; then
  cp config/config.json.example config/config.json
  echo "⚠️  请编辑 config/config.json 填入你的阿里云AK/SK"
  echo "   nano config/config.json"
  exit 1
fi

# 4. 安装依赖
echo "📥 安装Python依赖..."
pip install -r requirements.txt

echo "📥 安装前端依赖..."
cd web/frontend && npm install && cd ../..

# 5. 初始化数据库
echo "🗄️  初始化数据库..."
python migrations/run_migrations.py

# 6. 启动服务
echo "🎉 启动服务..."
./scripts/start_web.sh

echo ""
echo "✅ CloudLens已启动！"
echo "   前端: http://localhost:3000"
echo "   后端: http://localhost:8000"
echo ""
echo "数据库信息:"
echo "   地址: localhost:3306"
echo "   用户: cloudlens"
echo "   密码: cloudlens123"
echo "   数据库: cloudlens"
```

保存为 `quick_start.sh`，然后:
```bash
chmod +x quick_start.sh
./quick_start.sh
```

---

## 🎯 总结

**只要3步**:
1. `docker run ...` - 启动MySQL
2. 编辑 `config/config.json` - 填AK/SK
3. `./scripts/start_web.sh` - 启动服务

**数据库密码**: `cloudlens123`（固定的，不需要记忆）

---

**文档版本**: 1.0.0
**最后更新**: 2026-01-15
**适用场景**: 快速启动、本地开发、测试环境
