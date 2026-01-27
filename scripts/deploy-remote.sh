#!/bin/bash
# 远程服务器部署脚本
# 使用方法: ./scripts/deploy-remote.sh

set -e

SERVER_IP="95.40.35.172"
SERVER_USER="ec2-user"
APP_DIR="/opt/cloudlens/app"
BRANCH="zealous-torvalds"

echo "🚀 CloudLens 远程服务器部署"
echo "================================"
echo "服务器: ${SERVER_USER}@${SERVER_IP}"
echo "应用目录: ${APP_DIR}"
echo "分支: ${BRANCH}"
echo ""

# 检查SSH连接
echo "📡 测试SSH连接..."
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "echo '连接成功'" 2>/dev/null; then
    echo "✅ SSH连接成功"
else
    echo "❌ SSH连接失败，请检查："
    echo "   1. 网络连接"
    echo "   2. SSH密钥配置"
    echo "   3. 安全组设置"
    exit 1
fi

echo ""
echo "📥 步骤1: 更新代码..."
ssh ${SERVER_USER}@${SERVER_IP} << EOF
    set -e
    cd ${APP_DIR}
    echo "当前目录: \$(pwd)"
    echo "当前分支: \$(git branch --show-current 2>/dev/null || echo '未知')"
    echo ""
    echo "拉取最新代码..."
    git fetch origin
    git checkout ${BRANCH} 2>/dev/null || git checkout -b ${BRANCH} origin/${BRANCH}
    git pull origin ${BRANCH}
    echo "✅ 代码更新完成"
    echo ""
    echo "最新提交:"
    git log -1 --oneline
EOF

echo ""
echo "🔄 步骤2: 重启服务..."
ssh ${SERVER_USER}@${SERVER_IP} << EOF
    set -e
    cd ${APP_DIR}
    echo "重启Docker服务..."
    docker-compose restart backend frontend
    echo "等待服务启动..."
    sleep 20
    echo "✅ 服务重启完成"
EOF

echo ""
echo "🧹 步骤3: 清除缓存..."
ssh ${SERVER_USER}@${SERVER_IP} << EOF
    set -e
    docker exec cloudlens-redis redis-cli FLUSHDB 2>/dev/null || echo "Redis未运行或无法访问"
    echo "✅ 缓存清除完成"
EOF

echo ""
echo "✅ 步骤4: 验证部署..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
    set -e
    echo "等待API就绪..."
    sleep 5
    
    echo ""
    echo "检查ECS资源数量..."
    ECS_COUNT=$(curl -s 'http://localhost:8000/api/resources?account=mock-prod&type=ecs&force_refresh=true' 2>/dev/null | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('pagination',{}).get('total', 0))" 2>/dev/null || echo "0")
    echo "ECS总数: $ECS_COUNT"
    
    if [ "$ECS_COUNT" -ge 1000 ]; then
        echo "✅ 资源数量正确: $ECS_COUNT"
    else
        echo "⚠️  资源数量未达到预期: $ECS_COUNT (预期: 1000+)"
    fi
    
    echo ""
    echo "检查折扣率格式..."
    DISCOUNT_RATE=$(curl -s 'http://localhost:8000/api/discounts/trend?account=mock-prod&months=1' 2>/dev/null | python3 -c "import sys, json; d=json.load(sys.stdin); timeline=d.get('data',{}).get('trend_analysis',{}).get('timeline',[]); print(timeline[0].get('discount_rate',0) if timeline else 0)" 2>/dev/null || echo "0")
    echo "折扣率: $DISCOUNT_RATE"
    
    if python3 -c "exit(0 if 0 < float('$DISCOUNT_RATE') < 1 else 1)" 2>/dev/null; then
        echo "✅ 折扣率格式正确: $DISCOUNT_RATE (小数形式)"
    else
        echo "⚠️  折扣率格式可能有问题: $DISCOUNT_RATE (应该是0.25-0.35之间的小数)"
    fi
    
    echo ""
    echo "检查服务状态..."
    docker-compose ps
EOF

echo ""
echo "================================"
echo "✅ 部署完成！"
echo ""
echo "🌐 访问地址: https://cloudlens.songqipeng.com"
echo ""
echo "📊 下一步: 运行自动化测试验证"
echo "   cd web/frontend && npx playwright test tests/production-test.spec.ts"
