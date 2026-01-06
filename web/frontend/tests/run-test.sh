#!/bin/bash
# CloudLens Web 完整功能测试脚本
# 使用 Playwright 进行自动化测试并录制视频

set -e

echo "=========================================="
echo "CloudLens Web 完整功能测试"
echo "=========================================="

# 检查依赖
echo "📦 检查依赖..."
if ! command -v npx &> /dev/null; then
    echo "❌ 未找到 npx，请先安装 Node.js"
    exit 1
fi

# 检查 Playwright 是否安装
if [ ! -d "node_modules/@playwright" ]; then
    echo "📥 安装 Playwright..."
    npm install --save-dev @playwright/test playwright
    npx playwright install chromium
fi

# 检查后端服务是否运行
echo "🔍 检查后端服务..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠️  后端服务未运行，请先启动后端服务："
    echo "   cd web/backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000"
    exit 1
fi

# 检查前端服务是否运行
echo "🔍 检查前端服务..."
if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "⚠️  前端服务未运行，请先启动前端服务："
    echo "   cd web/frontend && npm run dev"
    exit 1
fi

# 创建测试结果目录
mkdir -p test-recordings
mkdir -p test-results

# 运行测试
echo ""
echo "🚀 开始运行测试..."
echo "=========================================="

npx playwright test web-full-test.spec.ts --project=chromium

# 检查测试结果
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 测试完成！"
    echo "=========================================="
    echo "📹 视频文件保存在: test-recordings/"
    echo "📊 测试报告保存在: test-results/html-report/index.html"
    echo ""
    echo "查看测试报告："
    echo "   open test-results/html-report/index.html"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ 测试失败"
    echo "=========================================="
    exit 1
fi


