#!/bin/bash
# 后端服务修复脚本

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     后端服务修复工具                                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. 检查后端服务
echo "1. 检查后端服务状态..."
if docker ps | grep -q cloudlens-backend; then
    echo "   ✅ 后端容器正在运行"
    STATUS=$(docker ps --filter "name=cloudlens-backend" --format "{{.Status}}")
    echo "   状态: $STATUS"
else
    echo "   ❌ 后端容器未运行"
    if docker ps -a | grep -q cloudlens-backend; then
        echo "   ⚠️  容器存在但已停止，查看停止原因..."
        docker ps -a | grep cloudlens-backend
    fi
fi

echo ""

# 2. 检查端口
echo "2. 检查端口8000..."
if lsof -i :8000 > /dev/null 2>&1; then
    echo "   ⚠️  端口8000已被占用:"
    lsof -i :8000 | head -3
else
    echo "   ✅ 端口8000可用"
fi

echo ""

# 3. 测试访问
echo "3. 测试后端服务访问..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ 后端服务可访问"
    curl -s http://localhost:8000/health | head -3
else
    echo "   ❌ 后端服务无法访问"
fi

echo ""

# 4. 查看日志
echo "4. 查看后端日志（最近30行）..."
docker compose logs backend --tail 30 2>/dev/null | tail -20

echo ""

# 5. 提供修复建议
echo "5. 修复建议..."
if ! docker ps | grep -q cloudlens-backend; then
    echo "   • 后端容器未运行，尝试重启..."
    echo "   执行: docker compose up -d backend"
elif ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   • 后端容器运行但服务无法访问，可能原因："
    echo "     1. 服务启动失败（查看日志）"
    echo "     2. 端口映射问题"
    echo "     3. 数据库连接失败"
    echo "   执行: docker compose restart backend"
    echo "   然后查看日志: docker compose logs -f backend"
fi

echo ""
echo "✅ 诊断完成"
