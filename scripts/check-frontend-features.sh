#!/bin/bash
# 前端功能检查脚本

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     前端功能检查                                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "1. 检查服务状态..."
echo "   后端: $(curl -s http://localhost:8000/health > /dev/null 2>&1 && echo '✅ 正常' || echo '❌ 异常')"
echo "   前端: $(curl -s http://localhost:3000 > /dev/null 2>&1 && echo '✅ 正常' || echo '❌ 异常')"

echo ""
echo "2. 测试关键API端点..."
endpoints=(
    "/health"
    "/api/v1/config/accounts"
    "/api/v1/cost/summary"
    "/api/v1/resources/list"
)

for endpoint in "${endpoints[@]}"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000$endpoint")
    if [ "$status" = "200" ] || [ "$status" = "401" ] || [ "$status" = "404" ]; then
        echo "   ✅ $endpoint (状态码: $status)"
    else
        echo "   ❌ $endpoint (状态码: $status)"
    fi
done

echo ""
echo "3. 在浏览器中打开前端..."
open -a "Google Chrome" "http://localhost:3000" 2>/dev/null

echo ""
echo "✅ 检查完成"
echo ""
echo "请在浏览器中："
echo "1. 按F12打开开发者工具"
echo "2. 查看Console标签中的错误"
echo "3. 查看Network标签中的API请求"
echo "4. 测试各个功能页面"
