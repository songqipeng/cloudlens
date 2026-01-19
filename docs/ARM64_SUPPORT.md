# ARM64 (Apple Silicon) 架构支持说明

## 问题说明

在 Apple Silicon (M1/M2/M3) Mac 上使用 Docker 时，可能会遇到平台架构不匹配的问题。

## 解决方案

### 方案1: 使用平台指定（推荐）

`docker-compose.yml` 已配置 `platform: linux/amd64`，Docker 会自动使用 Rosetta 2 模拟运行。

**优点**:
- 无需修改代码
- 兼容所有镜像
- 性能可接受

**缺点**:
- 性能略低于原生 ARM64
- 内存占用稍高

### 方案2: 构建 ARM64 原生镜像

如果需要更好的性能，可以构建 ARM64 原生镜像：

```bash
# 构建后端镜像（ARM64）
docker buildx build --platform linux/arm64 \
  -t songqipeng/cloudlens-backend:latest \
  -f web/backend/Dockerfile .

# 构建前端镜像（ARM64）
docker buildx build --platform linux/arm64 \
  -t songqipeng/cloudlens-frontend:latest \
  -f web/frontend/Dockerfile .
```

### 方案3: 使用本地开发环境（推荐用于开发）

对于开发环境，建议使用本地开发方式，避免 Docker 架构问题：

```bash
# 按照开发者快速开始指南
# 使用本地 Python 和 Node.js 环境
```

## 网络问题

如果遇到网络连接问题（无法拉取 Docker Hub 镜像）：

### 解决方案1: 使用镜像加速器

配置 Docker 镜像加速器（中国用户推荐）：

1. 打开 Docker Desktop
2. 进入 Settings → Docker Engine
3. 添加以下配置：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
```

4. 点击 "Apply & Restart"

### 解决方案2: 使用代理

如果有代理，配置 Docker 使用代理：

```bash
# 设置代理环境变量
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

# 然后运行 docker-compose
docker compose up -d
```

## 验证

检查 Docker 平台支持：

```bash
# 检查 Docker 平台
docker version

# 检查镜像平台
docker inspect songqipeng/cloudlens-backend:latest | grep Architecture
```

## 常见问题

### Q: 为什么使用 `platform: linux/amd64`？

A: 确保兼容性。如果镜像不支持 ARM64，Docker 会自动使用 Rosetta 2 模拟。

### Q: 性能影响大吗？

A: 对于大多数应用，性能影响可以接受（约 10-20%）。如果追求最佳性能，建议构建 ARM64 原生镜像。

### Q: 如何检查当前架构？

A: 运行 `uname -m`，如果显示 `arm64`，说明是 Apple Silicon。

