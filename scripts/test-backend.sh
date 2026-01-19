#!/bin/bash
# 后端服务测试脚本

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     后端服务测试                                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. 检查容器状态
echo "1. 检查后端容器..."
if docker ps | grep -q cloudlens-backend; then
    echo "   ✅ 后端容器正在运行"
    CONTAINER_RUNNING=true
else
    echo "   ❌ 后端容器未运行"
    if docker ps -a | grep -q cloudlens-backend; then
        echo "   ⚠️  容器存在但已停止"
        docker ps -a | grep cloudlens-backend
    fi
    CONTAINER_RUNNING=false
fi

echo ""

# 2. 检查端口映射
if [ "$CONTAINER_RUNNING" = "true" ]; then
    echo "2. 检查端口映射..."
    PORT_MAP=$(docker port cloudlens-backend 2>/dev/null | grep 8000)
    if [ -n "$PORT_MAP" ]; then
        echo "   ✅ 端口映射: $PORT_MAP"
    else
        echo "   ❌ 端口8000未映射"
    fi
fi

echo ""

# 3. 测试容器内服务
if [ "$CONTAINER_RUNNING" = "true" ]; then
    echo "3. 测试容器内服务..."
    if docker compose exec -T backend curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ 容器内服务正常"
        docker compose exec -T backend curl -s http://localhost:8000/health | head -3
    else
        echo "   ❌ 容器内服务无法访问"
    fi
fi

echo ""

# 4. 测试本地访问
echo "4. 测试本地访问 (http://localhost:8000/health)..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ 本地访问正常"
    curl -s http://localhost:8000/health | head -3
else
    echo "   ❌ 本地无法访问"
    echo "   可能原因："
    echo "   • 端口映射未正确配置"
    echo "   • 防火墙阻止"
    echo "   • 服务未正确启动"
fi

echo ""

# 5. 查看日志
if [ "$CONTAINER_RUNNING" = "true" ]; then
    echo "5. 查看后端日志（最近10行）..."
    docker compose logs backend --tail 10 2>/dev/null | tail -10
fi

echo ""
echo "✅ 测试完成"
