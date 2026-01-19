#!/bin/bash
# 测试后端服务访问

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     后端服务访问测试                                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. 检查端口8000
echo "1. 检查端口8000..."
if lsof -i :8000 > /dev/null 2>&1; then
    echo "   ✅ 端口8000已被占用"
    lsof -i :8000 | head -3
    echo ""
    echo "   检查是否是Docker容器..."
    if docker ps --format "{{.Names}}" | grep -q cloudlens-backend; then
        echo "   ✅ 是Docker容器: cloudlens-backend"
    else
        echo "   ⚠️  不是Docker容器，可能是本地进程"
    fi
else
    echo "   ❌ 端口8000未被占用"
fi

echo ""

# 2. 测试服务访问
echo "2. 测试后端服务访问..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ 后端服务可访问"
    echo "   响应:"
    curl -s http://localhost:8000/health | head -3
else
    echo "   ❌ 后端服务无法访问"
    echo "   可能原因："
    echo "   • Docker容器未启动"
    echo "   • 服务启动失败"
    echo "   • 端口映射问题"
fi

echo ""

# 3. 检查Docker容器
echo "3. 检查Docker容器状态..."
if docker ps | grep -q cloudlens-backend; then
    echo "   ✅ 后端容器正在运行"
    docker ps --filter "name=cloudlens-backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    echo "   ❌ 后端容器未运行"
    if docker ps -a | grep -q cloudlens-backend; then
        echo "   ⚠️  容器存在但已停止"
        docker ps -a --filter "name=cloudlens-backend" --format "table {{.Names}}\t{{.Status}}"
    fi
fi

echo ""

# 4. 提供修复建议
echo "4. 修复建议..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   • 使用 start.sh 启动服务: ./scripts/start.sh"
    echo "   • 或手动启动: docker compose up -d backend"
    echo "   • 查看日志: docker compose logs -f backend"
fi

echo ""
echo "✅ 测试完成"
