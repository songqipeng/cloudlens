#!/bin/bash
# 简单的后端服务浏览器测试脚本

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     后端服务浏览器测试                                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. 检查Docker容器
echo "1. 检查Docker容器状态..."
if docker ps | grep -q cloudlens-backend; then
    echo "   ✅ 后端容器正在运行"
    docker ps --filter "name=cloudlens-backend" --format "   {{.Names}}: {{.Status}} - {{.Ports}}"
else
    echo "   ❌ 后端容器未运行"
    echo "   请运行: docker compose up -d backend"
    exit 1
fi

echo ""

# 2. 测试API
echo "2. 测试后端API..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ 后端服务可访问"
    echo "   响应:"
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
else
    echo "   ❌ 后端服务无法访问"
    exit 1
fi

echo ""

# 3. 在浏览器中打开
echo "3. 在Chrome浏览器中打开测试页面..."
open -a "Google Chrome" "http://localhost:8000/health" 2>/dev/null
sleep 1
open -a "Google Chrome" "http://localhost:8000/docs" 2>/dev/null

echo ""
echo "✅ 测试完成！"
echo ""
echo "请在浏览器中检查："
echo "  • /health 应显示JSON响应"
echo "  • /docs 应显示Swagger UI"
echo "  • 按F12查看控制台和网络请求"
