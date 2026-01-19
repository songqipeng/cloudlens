#!/bin/bash
# 修复 ARM64 平台拉取问题

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     修复 ARM64 镜像拉取问题                                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

export DOCKER_DEFAULT_PLATFORM=linux/amd64

echo "📋 方法1: 使用 docker pull 强制拉取 amd64 镜像..."
echo ""

echo "拉取后端镜像..."
docker pull --platform linux/amd64 songqipeng/cloudlens-backend:latest || {
    echo "   ⚠️  后端镜像拉取失败，将使用本地构建"
    docker compose build --platform linux/amd64 backend
}

echo ""
echo "拉取前端镜像..."
docker pull --platform linux/amd64 songqipeng/cloudlens-frontend:latest || {
    echo "   ⚠️  前端镜像拉取失败，将使用本地构建"
    docker compose build --platform linux/amd64 frontend
}

echo ""
echo "拉取基础镜像..."
docker pull --platform linux/amd64 mysql:8.0
docker pull --platform linux/amd64 redis:7-alpine
docker pull --platform linux/amd64 nginx:alpine

echo ""
echo "✅ 镜像拉取完成"
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
echo "✅ 完成！"
