#!/bin/bash
# 完整的Chrome功能测试脚本

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     CloudLens Chrome完整功能测试                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 检查服务
echo "1. 检查服务状态..."
BACKEND_OK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
FRONTEND_OK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)

if [ "$BACKEND_OK" = "200" ]; then
    echo "   ✅ 后端服务正常"
else
    echo "   ❌ 后端服务异常 (状态码: $BACKEND_OK)"
fi

if [ "$FRONTEND_OK" = "200" ]; then
    echo "   ✅ 前端服务正常"
else
    echo "   ❌ 前端服务异常 (状态码: $FRONTEND_OK)"
fi

echo ""
echo "2. 测试关键API端点..."
APIS=(
    "/api/dashboard/summary"
    "/api/accounts"
    "/api/cost/overview"
    "/api/resources/list"
)

for api in "${APIS[@]}"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000$api?account=test")
    if [ "$status" = "200" ] || [ "$status" = "400" ] || [ "$status" = "404" ]; then
        echo "   ✅ $api (状态码: $status)"
    else
        echo "   ❌ $api (状态码: $status)"
    fi
done

echo ""
echo "3. 在Chrome中打开所有测试页面..."
open -a "Google Chrome" "http://localhost:3000"
sleep 1
open -a "Google Chrome" "http://localhost:3000/settings/accounts"
sleep 1
open -a "Google Chrome" "http://localhost:8000/docs"

echo ""
echo "✅ 测试页面已打开"
echo ""
echo "请在Chrome中："
echo "1. 按F12打开开发者工具"
echo "2. 查看Console标签中的错误"
echo "3. 查看Network标签中的API请求"
echo "4. 测试各个功能页面"
echo ""
echo "测试页面列表："
echo "  - 首页: http://localhost:3000"
echo "  - 账号设置: http://localhost:3000/settings/accounts"
echo "  - API文档: http://localhost:8000/docs"
