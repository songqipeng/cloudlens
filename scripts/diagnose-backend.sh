#!/bin/bash
# 后端服务诊断脚本

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     后端服务诊断工具                                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "1. 检查后端容器状态..."
docker ps -a --filter "name=cloudlens-backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "2. 检查端口8000占用..."
lsof -i :8000 2>/dev/null || echo "   端口8000未被占用"

echo ""
echo "3. 测试本地访问..."
curl -s http://localhost:8000/health 2>&1 | head -3 || echo "   ❌ 无法访问"

echo ""
echo "4. 检查容器内服务..."
docker compose exec backend curl -s http://localhost:8000/health 2>/dev/null || echo "   ❌ 容器内服务未运行"

echo ""
echo "5. 查看后端日志（最近20行）..."
docker compose logs backend --tail 20 2>/dev/null | tail -10

echo ""
echo "6. 检查端口映射..."
docker port cloudlens-backend 2>/dev/null || echo "   无法获取端口映射"

echo ""
echo "✅ 诊断完成"
