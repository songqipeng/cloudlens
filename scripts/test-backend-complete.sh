#!/bin/bash
# 后端服务完整测试脚本

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     后端服务完整测试                                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. 检查环境
echo "1. 检查环境..."
echo "   • Docker: $(docker --version 2>/dev/null || echo '未安装')"
echo "   • Docker Compose: $(docker compose version 2>/dev/null || echo '未安装')"
echo "   • 架构: $(uname -m)"

echo ""

# 2. 检查端口占用
echo "2. 检查端口8000占用..."
if lsof -i :8000 > /dev/null 2>&1; then
    echo "   ⚠️  端口8000已被占用:"
    lsof -i :8000 | head -3
    echo ""
    read -p "   是否要停止占用端口的进程？(y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   停止进程..."
        lsof -ti :8000 | xargs kill -9 2>/dev/null
        sleep 2
        echo "   ✅ 进程已停止"
    fi
else
    echo "   ✅ 端口8000可用"
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
    fi
fi

echo ""

# 4. 测试服务访问
echo "4. 测试后端服务访问..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ 后端服务可访问"
    echo "   响应:"
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
else
    echo "   ❌ 后端服务无法访问"
    echo ""
    echo "   建议执行："
    echo "   ./scripts/start.sh"
fi

echo ""

# 5. 检查容器日志（如果容器存在）
if docker ps -a | grep -q cloudlens-backend; then
    echo "5. 查看后端容器日志（最近10行）..."
    docker compose logs backend --tail 10 2>/dev/null | tail -10 || echo "   无法获取日志"
fi

echo ""
echo "✅ 测试完成"
