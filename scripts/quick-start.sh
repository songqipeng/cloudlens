#!/bin/bash
# CloudLens 快速启动脚本
# 适用于：普通用户快速启动、新开发者快速上手

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     CloudLens 快速启动脚本                                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: 未检测到 Docker"
    echo ""
    echo "请先安装 Docker:"
    echo "  • macOS: https://www.docker.com/products/docker-desktop"
    echo "  • Linux: sudo apt install docker.io docker-compose"
    echo "  • Windows: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ 错误: 未检测到 Docker Compose"
    echo ""
    echo "请安装 Docker Compose 或使用 Docker Desktop（包含 Compose）"
    exit 1
fi

echo "✅ Docker 已安装"
echo ""

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ 已创建 .env 文件（从 .env.example 复制）"
    else
        echo "⚠️  未找到 .env.example，创建空的 .env 文件"
        touch .env
    fi
    echo ""
    echo "⚠️  重要: 请编辑 .env 文件，至少配置 AI API 密钥："
    echo "   ANTHROPIC_API_KEY=your_claude_api_key"
    echo "   LLM_PROVIDER=claude"
    echo ""
    read -p "按 Enter 继续（稍后可以编辑 .env 文件）..."
else
    echo "✅ .env 文件已存在"
fi

# 检查AI API密钥配置
if ! grep -q "ANTHROPIC_API_KEY=" .env && ! grep -q "OPENAI_API_KEY=" .env; then
    echo ""
    echo "⚠️  警告: 未检测到 AI API 密钥配置"
    echo "   AI Chatbot 功能将不可用"
    echo "   请编辑 .env 文件添加："
    echo "   ANTHROPIC_API_KEY=your_claude_api_key"
    echo "   LLM_PROVIDER=claude"
    echo ""
    read -p "按 Enter 继续（可以稍后配置）..."
fi

# 启动服务
echo ""
echo "🚀 启动 CloudLens 服务..."
echo ""

# 使用 docker-compose 或 docker compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

echo "📦 拉取最新镜像（如果需要）..."
$COMPOSE_CMD pull --quiet || echo "   （部分镜像可能已是最新）"

echo ""
echo "🔧 启动所有服务..."
$COMPOSE_CMD up -d

echo ""
echo "⏳ 等待服务启动（约15秒）..."
sleep 15

# 检查服务状态
echo ""
echo "📊 服务状态："
$COMPOSE_CMD ps

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     ✅ CloudLens 启动完成！                                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 访问地址："
echo "   • 前端界面: http://localhost:3000"
echo "   • 后端API:  http://localhost:8000"
echo "   • API文档:  http://localhost:8000/docs"
echo ""
echo "📝 常用命令："
echo "   • 查看日志: docker-compose logs -f"
echo "   • 停止服务: docker-compose down"
echo "   • 重启服务: docker-compose restart"
echo ""
echo "💡 提示："
echo "   • 首次启动可能需要几分钟初始化数据库"
echo "   • 如果前端无法访问，请等待30秒后重试"
echo "   • 查看日志了解详细启动过程: docker-compose logs -f"
echo ""
