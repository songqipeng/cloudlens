#!/bin/bash
# CloudLens Web 一键启动脚本

echo "🚀 正在启动 CloudLens Web 服务..."
echo ""

# 检查依赖
if ! command -v uvicorn &> /dev/null; then
    echo "❌ uvicorn 未安装，请先安装: pip install uvicorn"
    exit 1
fi

if [ ! -d "web/frontend/node_modules" ]; then
    echo "📦 检测到前端依赖未安装，正在安装..."
    cd web/frontend && npm install && cd ../..
fi

# 启动后端（后台）
echo "🔧 启动后端 FastAPI 服务（端口 8000）..."
cd web/backend
nohup uvicorn main:app --reload --host 127.0.0.1 --port 8000 > ../../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   ✅ 后端PID: $BACKEND_PID"
cd ../..

# 等待后端启动
sleep 2

# 启动前端（前台）
echo "🎨 启动前端 Next.js 服务（端口 3000）..."
echo ""
cd web/frontend
npm run dev

# 清理后端进程（当前端退出时）
trap "kill $BACKEND_PID 2>/dev/null" EXIT
