# 用户测试指南

## 快速测试后端服务

### 1. 从GitHub下载代码

```bash
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens
```

### 2. 启动服务

```bash
# 使用智能启动脚本（推荐）
./scripts/start.sh
```

脚本会自动：
- 检测系统架构（ARM64/x86_64）
- 拉取或构建Docker镜像
- 启动所有服务（MySQL, Redis, 后端, 前端）

### 3. 验证后端服务

#### 方式1：使用curl测试

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

#### 方式2：使用浏览器测试

在浏览器中打开：
- 健康检查：http://localhost:8000/health
- API文档：http://localhost:8000/docs

#### 方式3：使用测试脚本

```bash
./scripts/test-backend-simple.sh
```

### 4. 如果遇到问题

#### 检查容器状态

```bash
docker compose ps
```

#### 查看后端日志

```bash
docker compose logs backend --tail 50
```

#### 运行诊断脚本

```bash
./scripts/diagnose-backend.sh
```

#### 查看详细排查文档

```bash
cat docs/BACKEND_SERVICE_TROUBLESHOOTING.md
```

## 常见问题

### 问题1：端口8000被占用

**症状：** 启动失败，提示端口被占用

**解决：**
```bash
# 停止占用端口的进程
lsof -ti :8000 | xargs kill -9

# 重新启动
./scripts/start.sh
```

### 问题2：ARM64架构问题

**症状：** 错误信息包含 `no matching manifest for linux/arm64/v8`

**解决：**
- `start.sh` 脚本会自动处理
- 确保Docker Desktop已启用Rosetta 2支持

### 问题3：后端服务无法访问

**症状：** curl或浏览器无法访问 http://localhost:8000

**解决：**
1. 检查容器是否运行：`docker compose ps`
2. 查看日志：`docker compose logs backend`
3. 重启服务：`docker compose restart backend`

## 完整测试流程

```bash
# 1. 下载代码
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens

# 2. 启动服务
./scripts/start.sh

# 3. 等待服务启动（约30-60秒）
sleep 60

# 4. 测试后端
curl http://localhost:8000/health

# 5. 在浏览器中打开
open http://localhost:8000/docs
```

## 验证清单

- [ ] 后端容器运行正常
- [ ] 健康检查端点返回200
- [ ] API文档页面可以访问
- [ ] 浏览器控制台无错误
- [ ] 网络请求成功

## 联系支持

如果以上步骤都无法解决问题，请提供：
1. `docker compose ps` 的输出
2. `docker compose logs backend` 的输出
3. 浏览器控制台错误信息（F12）

## ⚠️ 重要提示：服务启动需要时间

### 第一次启动

**需要等待60-90秒**，因为：
- MySQL容器需要初始化（约30秒）
- 数据库迁移需要执行（约10-20秒）
- 后端服务需要启动（约10-20秒）

### 测试步骤

```bash
# 1. 启动服务
./scripts/start.sh

# 2. 等待服务完全启动（重要！）
echo "等待服务启动（90秒）..."
sleep 90

# 3. 测试后端服务
curl http://localhost:8000/health

# 应该返回：
# {"status":"healthy","timestamp":"...","service":"cloudlens-api","version":"1.1.0"}
```

### 如果遇到 "Connection reset by peer"

这通常意味着服务还在启动中，请：

1. **等待更长时间**
   ```bash
   sleep 90
   curl http://localhost:8000/health
   ```

2. **检查服务状态**
   ```bash
   docker compose ps
   ```

3. **查看后端日志**
   ```bash
   docker compose logs backend --tail 50
   ```
   
   应该看到：
   - "MySQL已就绪！"
   - "启动后端服务..."
   - "Uvicorn running on http://0.0.0.0:8000"

4. **如果仍然失败**
   ```bash
   # 查看完整日志
   docker compose logs backend
   
   # 重启服务
   docker compose restart backend
   ```
