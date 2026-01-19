#!/bin/bash
# CloudLens 启动脚本 - 强制使用 amd64 平台

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     CloudLens 启动脚本 (ARM64 兼容)                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 设置默认平台为 amd64
export DOCKER_DEFAULT_PLATFORM=linux/amd64

echo "📋 配置信息："
echo "   • 平台: linux/amd64 (通过 Rosetta 2 运行)"
echo "   • Docker Compose: $(docker compose version --short 2>/dev/null || docker-compose --version)"
echo ""

echo "🔍 检查 Docker Desktop Rosetta 设置..."
if docker info 2>/dev/null | grep -q "OSType: linux"; then
    echo "   ✅ Docker 运行正常"
else
    echo "   ⚠️  请确保 Docker Desktop 正在运行"
    exit 1
fi

echo ""
echo "📦 拉取镜像（强制使用 amd64 平台）..."
docker compose pull --platform linux/amd64 2>&1 | grep -E "Pulling|Pulled|Error" || true

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
