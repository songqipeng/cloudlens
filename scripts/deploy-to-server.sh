#!/bin/bash
# CloudLens 服务器自动部署脚本
# 使用方法: ./scripts/deploy-to-server.sh

set -e

echo "🚀 CloudLens 服务器自动部署"
echo "================================"

# 配置
SERVER_IP="95.40.35.172"
SERVER_USER="ec2-user"
APP_DIR="/opt/cloudlens/app"
BRANCH="zealous-torvalds"

# 检查SSH连接
echo "📡 检查SSH连接..."
if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "echo '连接成功'" 2>/dev/null; then
    echo "❌ 无法SSH连接到服务器"
    echo "   可能原因:"
    echo "   1. 安全组未开放22端口"
    echo "   2. 需要使用特定的SSH密钥"
    echo "   3. 服务器IP已变更"
    echo ""
    echo "请手动执行以下命令:"
    echo "  ssh ${SERVER_USER}@${SERVER_IP}"
    echo "  cd ${APP_DIR}"
    echo "  git fetch origin"
    echo "  git checkout ${BRANCH}"
    echo "  git pull origin ${BRANCH}"
    echo "  docker-compose restart backend frontend"
    echo "  docker exec cloudlens-redis redis-cli FLUSHDB"
    exit 1
fi

echo "✅ SSH连接成功"
echo ""

# 更新代码
echo "📥 更新代码..."
ssh ${SERVER_USER}@${SERVER_IP} << EOF
    set -e
    cd ${APP_DIR}
    echo "当前目录: \$(pwd)"
    echo "当前分支: \$(git branch --show-current)"
    echo "拉取最新代码..."
    git fetch origin
    git checkout ${BRANCH}
    git pull origin ${BRANCH}
    echo "✅ 代码更新完成"
EOF

# 重启服务
echo ""
echo "🔄 重启服务..."
ssh ${SERVER_USER}@${SERVER_IP} << EOF
    set -e
    cd ${APP_DIR}
    echo "重启Docker服务..."
    docker-compose restart backend frontend
    echo "等待服务启动..."
    sleep 15
    echo "✅ 服务重启完成"
EOF

# 清除缓存
echo ""
echo "🧹 清除缓存..."
ssh ${SERVER_USER}@${SERVER_IP} << EOF
    set -e
    docker exec cloudlens-redis redis-cli FLUSHDB
    echo "✅ 缓存已清除"
EOF

# 验证部署
echo ""
echo "✅ 验证部署..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
    set -e
    echo "检查ECS资源数量..."
    ECS_COUNT=$(curl -s 'http://localhost:8000/api/resources?account=mock-prod&type=ecs&force_refresh=true' | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('pagination',{}).get('total', 0))" 2>/dev/null || echo "0")
    echo "ECS总数: $ECS_COUNT"
    
    if [ "$ECS_COUNT" -ge 1000 ]; then
        echo "✅ 资源数量正确: $ECS_COUNT"
    else
        echo "⚠️  资源数量未达到预期: $ECS_COUNT (预期: 1000+)"
    fi
    
    echo ""
    echo "检查折扣率格式..."
    DISCOUNT_RATE=$(curl -s 'http://localhost:8000/api/discounts/trend?account=mock-prod&months=1' | python3 -c "import sys, json; d=json.load(sys.stdin); timeline=d.get('data',{}).get('trend_analysis',{}).get('timeline',[]); print(timeline[0].get('discount_rate',0) if timeline else 0)" 2>/dev/null || echo "0")
    echo "折扣率: $DISCOUNT_RATE"
    
    if (( $(echo "$DISCOUNT_RATE > 0 && $DISCOUNT_RATE < 1" | bc -l) )); then
        echo "✅ 折扣率格式正确: $DISCOUNT_RATE (小数形式)"
    else
        echo "⚠️  折扣率格式可能有问题: $DISCOUNT_RATE (应该是0.25-0.35之间的小数)"
    fi
EOF

echo ""
echo "================================"
echo "✅ 部署完成！"
echo ""
echo "📊 验证结果:"
echo "   - 代码已更新到 ${BRANCH} 分支"
echo "   - 服务已重启"
echo "   - 缓存已清除"
echo ""
echo "🌐 访问地址: https://cloudlens.songqipeng.com"
