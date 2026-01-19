#!/bin/bash
# CloudLens 智能启动脚本 - 自动检测架构并处理

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     CloudLens 智能启动脚本                                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 检测 CPU 架构
ARCH=$(uname -m)
OS=$(uname -s)

echo "🔍 检测系统信息..."
echo "   • 操作系统: $OS"
echo "   • CPU 架构: $ARCH"

# 确定 Docker 平台
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    if [ "$OS" = "Darwin" ]; then
        # Apple Silicon (M1/M2/M3)
        echo "   • 检测到: Apple Silicon (ARM64)"
        echo "   • 使用平台: linux/amd64 (通过 Rosetta 2)"
        PLATFORM="linux/amd64"
        USE_ROSETTA=true
    else
        # Linux ARM64
        echo "   • 检测到: Linux ARM64"
        echo "   • 使用平台: linux/arm64"
        PLATFORM="linux/arm64"
        USE_ROSETTA=false
    fi
else
    # x86_64 / amd64
    echo "   • 检测到: x86_64/amd64"
    echo "   • 使用平台: linux/amd64"
    PLATFORM="linux/amd64"
    USE_ROSETTA=false
fi

export DOCKER_DEFAULT_PLATFORM=$PLATFORM

echo ""
echo "📦 拉取镜像..."

# 尝试拉取镜像，如果失败则本地构建
pull_image() {
    local image=$1
    local name=$2
    
    echo "   拉取 $name..."
    if docker pull --platform $PLATFORM "$image" 2>/dev/null; then
        echo "   ✅ $name 拉取成功"
        return 0
    else
        echo "   ⚠️  $name 拉取失败，将使用本地构建"
        return 1
    fi
}

# 拉取基础镜像（总是需要的）
docker pull --platform $PLATFORM mysql:8.0 >/dev/null 2>&1 || true
docker pull --platform $PLATFORM redis:7-alpine >/dev/null 2>&1 || true
docker pull --platform $PLATFORM nginx:alpine >/dev/null 2>&1 || true

# 拉取应用镜像
NEED_BUILD_BACKEND=false
NEED_BUILD_FRONTEND=false

if ! pull_image "songqipeng/cloudlens-backend:latest" "后端镜像"; then
    NEED_BUILD_BACKEND=true
fi

if ! pull_image "songqipeng/cloudlens-frontend:latest" "前端镜像"; then
    NEED_BUILD_FRONTEND=true
fi

# 如果需要构建，执行构建
if [ "$NEED_BUILD_BACKEND" = "true" ] || [ "$NEED_BUILD_FRONTEND" = "true" ]; then
    echo ""
    echo "🔨 开始本地构建..."
    export DOCKER_BUILDKIT=1
    
    if [ "$NEED_BUILD_BACKEND" = "true" ]; then
        echo "   构建后端镜像..."
        docker compose build --platform $PLATFORM backend
    fi
    
    if [ "$NEED_BUILD_FRONTEND" = "true" ]; then
        echo "   构建前端镜像..."
        docker compose build --platform $PLATFORM frontend
    fi
fi

echo ""
echo "🚀 启动服务..."
docker compose up -d

echo ""
echo "⏳ 等待服务启动（约 30 秒）..."
sleep 30

echo ""
echo "📊 服务状态："
docker compose ps

echo ""
echo "✅ 启动完成！"
echo ""
echo "访问地址："
echo "   • 前端: http://localhost:3000"
echo "   • 后端: http://localhost:8000"
echo "   • API 文档: http://localhost:8000/docs"
echo ""
echo "查看日志："
echo "   docker compose logs -f"
echo ""

if [ "$USE_ROSETTA" = "true" ]; then
    echo "💡 提示："
    echo "   您使用的是 Apple Silicon，服务通过 Rosetta 2 运行"
    echo "   如果遇到性能问题，请确保 Docker Desktop 已启用 Rosetta 2"
    echo "   Docker Desktop → Settings → General → Use Rosetta for x86/amd64 emulation"
    echo ""
fi
