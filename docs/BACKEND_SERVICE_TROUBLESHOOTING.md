# 后端服务访问问题排查指南

## 问题现象

用户报告后端8000端口服务无法访问。

## 常见原因

### 1. Docker容器未启动

**症状：**
- `docker compose ps` 显示没有运行中的容器
- `curl http://localhost:8000/health` 无法访问

**解决方案：**
```bash
# 使用智能启动脚本（推荐）
./scripts/start.sh

# 或手动启动
docker compose up -d backend
```

### 2. 端口被本地进程占用

**症状：**
- `lsof -i :8000` 显示有Python进程占用端口
- 但 `docker compose ps` 显示容器未运行

**解决方案：**
```bash
# 停止本地进程
lsof -ti :8000 | xargs kill -9

# 然后启动Docker容器
./scripts/start.sh
```

### 3. ARM64架构兼容性问题

**症状：**
- 错误信息：`no matching manifest for linux/arm64/v8`
- 在Apple Silicon (M1/M2/M3) 上出现

**解决方案：**
- `start.sh` 脚本会自动检测架构并使用 `linux/amd64` 平台
- 确保 Docker Desktop 已启用 Rosetta 2 支持

### 4. 迁移文件路径问题

**症状：**
- 后端容器启动失败
- 日志显示找不到迁移文件

**解决方案：**
- 确保 `migrations/` 目录存在且包含必要的SQL文件
- 检查 `docker-compose.yml` 中的 volume 挂载配置

## 诊断步骤

### 步骤1: 检查端口占用

```bash
lsof -i :8000
```

### 步骤2: 检查Docker容器状态

```bash
docker compose ps
docker ps -a | grep cloudlens-backend
```

### 步骤3: 测试服务访问

```bash
curl http://localhost:8000/health
```

### 步骤4: 查看容器日志

```bash
docker compose logs backend --tail 50
```

## 快速修复脚本

使用提供的诊断脚本：

```bash
# 测试后端服务访问
./scripts/test-backend-access.sh

# 诊断后端服务问题
./scripts/diagnose-backend.sh

# 修复后端服务
./scripts/fix-backend.sh
```

## 完整启动流程

1. **停止现有服务**
   ```bash
   docker compose down
   ```

2. **使用智能启动脚本**
   ```bash
   ./scripts/start.sh
   ```

3. **验证服务**
   ```bash
   curl http://localhost:8000/health
   ```

## 预期结果

成功启动后，应该看到：

```json
{
  "status": "healthy",
  "timestamp": "2026-01-19T...",
  "service": "cloudlens-api",
  "version": "1.1.0"
}
```

## 联系支持

如果以上步骤都无法解决问题，请提供：
1. `docker compose logs backend` 的完整输出
2. `docker compose ps` 的输出
3. `lsof -i :8000` 的输出

## 问题：后端服务卡在"等待MySQL就绪..."

### 症状
- `docker compose logs backend` 显示 "等待MySQL就绪..." 但之后没有更多日志
- `curl localhost:8000` 返回 "Connection reset by peer"
- 后端容器可能处于退出状态

### 原因
1. MySQL用户或数据库未创建
2. MySQL连接权限问题
3. 网络连接问题

### 解决方案

#### 方案1：检查并创建MySQL用户和数据库

```bash
# 进入MySQL容器
docker compose exec mysql mysql -u root -pcloudlens_root_2024

# 在MySQL中执行
CREATE DATABASE IF NOT EXISTS cloudlens CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'cloudlens'@'%' IDENTIFIED BY 'cloudlens123';
GRANT ALL PRIVILEGES ON cloudlens.* TO 'cloudlens'@'%';
FLUSH PRIVILEGES;
EXIT;
```

#### 方案2：重新初始化MySQL（会清除数据）

```bash
# 停止所有服务
docker compose down

# 删除MySQL数据卷
docker volume rm cloudlens_mysql_data

# 重新启动
./scripts/start.sh
```

#### 方案3：检查init.sql是否执行

```bash
# 检查init.sql是否在MySQL容器中
docker compose exec mysql ls -la /docker-entrypoint-initdb.d/

# 如果不存在，检查挂载配置
grep -A 1 "init.sql" docker-compose.yml
```

### 验证修复

```bash
# 1. 检查MySQL用户
docker compose exec mysql mysql -u root -pcloudlens_root_2024 -e "SELECT User FROM mysql.user WHERE User='cloudlens';"

# 2. 测试后端容器连接MySQL
docker compose exec backend bash -c "mysql -h mysql -u cloudlens -pcloudlens123 -e 'SELECT 1'"

# 3. 重启后端服务
docker compose restart backend

# 4. 查看日志
docker compose logs backend --tail 50

# 5. 测试服务
curl http://localhost:8000/health
```
