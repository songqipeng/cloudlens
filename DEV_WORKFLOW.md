# CloudLens 开发和测试流程说明

## 当前的两套环境

### 1. 开发环境 (docker-compose.dev.yml)
用于**日常开发和快速测试**

**特点：**
- ✅ **源代码挂载** - 代码实时同步，无需重新构建镜像
- ✅ **热重载** - 后端使用 `uvicorn --reload`，前端使用 `npm run dev`
- ✅ **独立数据** - 使用独立的数据卷 (`mysql_data_dev`, `redis_data_dev`)
- ✅ **快速启动** - 直接使用基础镜像 (python:3.11-slim, node:18-alpine)

**数据持久化：**
```yaml
volumes:
  # 源代码挂载（实时同步）
  - ./cloudlens:/app/cloudlens
  - ./web/backend:/app/web/backend
  - ./config:/app/config
  - ~/.cloudlens:/root/.cloudlens  # 配置文件

  # 数据卷（独立存储）
  - mysql_data_dev:/var/lib/mysql
  - redis_data_dev:/data
```

**启动方式：**
```bash
# 方式1: 使用脚本
./deploy-dev.sh

# 方式2: 直接使用docker compose
docker compose -f docker-compose.dev.yml up -d
```

**开发流程：**
1. 修改本地代码 (cloudlens/, web/backend/)
2. 保存文件 → 服务自动重启（热重载）
3. 立即测试 http://localhost:8000
4. 无需重新构建镜像！

---

### 2. 生产环境 (docker-compose.yml)
用于**生产部署和正式测试**

**特点：**
- 🔒 **使用构建的镜像** - `songqipeng/cloudlens-backend:latest`
- 🔒 **代码只读挂载** - 配置文件只读，不挂载源代码
- 🔒 **独立数据** - 使用生产数据卷 (`mysql_data`, `redis_data`)
- 🔒 **生产配置** - 关闭DEBUG，使用环境变量配置

**数据持久化：**
```yaml
volumes:
  # 只读配置
  - ./config:/app/config:ro
  - ./logs:/app/logs

  # 生产数据卷
  - mysql_data:/var/lib/mysql  # 这里有你的真实数据！
  - redis_data:/data
```

**部署流程：**
```bash
# 1. 构建镜像
docker build -t songqipeng/cloudlens-backend:latest .

# 2. 推送到仓库（可选）
docker push songqipeng/cloudlens-backend:latest

# 3. 启动服务
./deploy-production.sh
# 或
docker compose up -d
```

---

## 数据情况分析

### 生产环境的数据 ✅

你说"容器里的redis和mysql已经有数据了"，这是正确的！

生产环境的数据卷：
```bash
docker volume ls
# cloudlens_mysql_data   <- 生产数据在这里！
# cloudlens_redis_data   <- 生产缓存在这里！
```

这些数据卷：
- ✅ **持久化存储** - 即使容器停止/删除，数据仍然保留
- ✅ **包含真实数据** - 你之前导入的账单数据、配置等
- ✅ **独立于代码** - 不会被覆盖

### 开发环境的数据 ⚠️

开发环境使用**独立的数据卷**：
```bash
docker volume ls
# elated-bell_mysql_data_dev  <- 开发环境，独立的！
# elated-bell_redis_data_dev  <- 开发环境，独立的！
```

当前状态：
- ⚠️ **新创建的卷** - 刚才启动时创建，是空的
- ⚠️ **没有数据** - 需要重新导入测试数据
- ✅ **不影响生产** - 生产数据完全独立，很安全

---

## 推荐的开发流程

### 日常开发 → 使用开发环境

```bash
# 1. 启动开发环境
docker compose -f docker-compose.dev.yml up -d

# 2. 修改代码
vim web/backend/api/v1/discounts.py

# 3. 保存后自动重载，立即测试
curl http://localhost:8000/health

# 4. 查看日志排查问题
docker logs -f cloudlens-backend-dev

# 5. 停止开发环境
docker compose -f docker-compose.dev.yml down
```

**优点：**
- ⚡️ 修改代码立即生效
- 🔄 自动热重载
- 🛡️ 不影响生产数据
- 🚀 无需构建镜像

### 测试发布 → 使用生产环境

```bash
# 1. 构建新镜像
docker build -t songqipeng/cloudlens-backend:latest .

# 2. 停止旧容器
docker compose down

# 3. 启动新容器
docker compose up -d

# 4. 测试（使用真实数据）
curl http://localhost:8000/api/discounts/trend?account=aliyun-prod
```

**优点：**
- ✅ 使用真实数据测试
- ✅ 验证镜像构建正确
- ✅ 模拟生产环境

---

## 数据管理建议

### 方案1: 开发环境导入测试数据

如果想在开发环境测试：

```bash
# 从生产环境导出数据
docker exec cloudlens-mysql mysqldump \
  -ucloudlens -pcloudlens123 cloudlens > backup.sql

# 导入到开发环境
docker exec -i cloudlens-mysql-dev mysql \
  -ucloudlens -pcloudlens123 cloudlens < backup.sql

# 或复制配置文件
docker cp cloudlens-backend:/root/.cloudlens/. ~/.cloudlens/
```

### 方案2: 开发环境连接生产数据（不推荐）

修改 `docker-compose.dev.yml`：
```yaml
backend:
  environment:
    # 指向生产MySQL（危险！）
    MYSQL_HOST: host.docker.internal  # 如果生产在本机
```

⚠️ **风险**：可能误修改生产数据

### 方案3: 混合模式（推荐）

```bash
# 日常开发：用开发环境 + 空数据或小数据集
docker compose -f docker-compose.dev.yml up -d

# 完整测试：切换到生产环境
docker compose -f docker-compose.dev.yml down
docker compose up -d  # 使用真实数据
```

---

## 当前情况总结

✅ **生产数据安全**
- 数据在 `cloudlens_mysql_data` 卷中
- 没有被破坏或修改

✅ **开发环境已启动**
- 使用独立的数据卷
- 代码热重载工作正常
- 但数据是空的（需要导入）

✅ **代码修复已完成**
- account_id格式已修复
- 提交到 elated-bell 分支
- 开发容器已加载最新代码

🔧 **下一步建议**
1. 如果只是验证代码修复 → 导入少量测试数据到开发环境
2. 如果要完整测试 → 切换到生产环境（有真实数据）
3. 开发新功能 → 继续用开发环境（快速迭代）

---

## 快速切换命令

```bash
# 查看当前运行的环境
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

# 切换到开发环境
docker compose down  # 停止生产
docker compose -f docker-compose.dev.yml up -d  # 启动开发

# 切换到生产环境
docker compose -f docker-compose.dev.yml down  # 停止开发
docker compose up -d  # 启动生产

# 查看数据卷
docker volume ls | grep cloudlens
```
