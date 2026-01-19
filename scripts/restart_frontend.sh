#!/bin/bash
# 重启前端服务脚本

echo "正在重启前端服务..."

cd /Users/songqipeng/cloudlens/web/frontend

# 查找并停止现有进程
PID=$(ps aux | grep "next dev" | grep -v grep | awk '{print $2}')
if [ ! -z "$PID" ]; then
    echo "停止现有前端服务 (PID: $PID)..."
    kill $PID
    sleep 2
fi

# 清除缓存
echo "清除Next.js缓存..."
rm -rf .next

# 重新启动
echo "启动前端服务..."
npm run dev > /tmp/frontend.log 2>&1 &

echo "✅ 前端服务已重启"
echo "📝 日志文件: /tmp/frontend.log"
echo "🌐 访问: http://localhost:3000"
echo ""
echo "等待5秒后检查服务状态..."
sleep 5

# 检查服务是否启动
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ 前端服务运行正常"
else
    echo "⚠️  前端服务可能还在启动中，请稍候..."
fi
