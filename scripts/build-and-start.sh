#!/bin/bash
# CloudLens 本地构建并启动脚本（ARM64 兼容）

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     CloudLens 本地构建并启动脚本                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 设置默认平台为 amd64（通过 Rosetta 2 运行）
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export DOCKER_BUILDKIT=1

echo "📋 配置信息："
echo "   • 平台: linux/amd64 (通过 Rosetta 2 运行)"
echo "   • 构建模式: 本地构建"
echo ""

echo "🔍 检查 Docker 环境..."
if ! docker info > /dev/null 2>&1; then
    echo "   ❌ Docker 未运行，请启动 Docker Desktop"
    exit 1
fi
echo "   ✅ Docker 运行正常"

echo ""
echo "🛑 停止现有服务（如果有）..."
docker compose down 2>/dev/null || true

echo ""
echo "🔨 构建镜像（这可能需要几分钟）..."
echo "   构建后端镜像..."
docker compose build --platform linux/amd64 backend

echo "   构建前端镜像..."
docker compose build --platform linux/amd64 frontend

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
