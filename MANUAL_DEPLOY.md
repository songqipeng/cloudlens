# 手动部署指南

由于当前环境无法直接SSH连接，请手动执行以下命令：

## 快速部署命令

```bash
# 1. SSH登录服务器
ssh ec2-user@95.40.35.172

# 2. 执行以下命令（一次性复制粘贴）
cd /opt/cloudlens/app && \
git fetch origin && \
git checkout zealous-torvalds && \
git pull origin zealous-torvalds && \
docker-compose restart backend frontend && \
sleep 20 && \
docker exec cloudlens-redis redis-cli FLUSHDB && \
echo "✅ 部署完成"
```

## 验证部署

```bash
# 在服务器上执行
curl -s 'http://localhost:8000/api/resources?account=mock-prod&type=ecs&force_refresh=true' | python3 -c "import sys, json; d=json.load(sys.stdin); print('ECS总数:', d.get('pagination',{}).get('total', 0))"
# 应该返回: 1000

curl -s 'http://localhost:8000/api/discounts/trend?account=mock-prod&months=1' | python3 -c "import sys, json; d=json.load(sys.stdin); timeline=d.get('data',{}).get('trend_analysis',{}).get('timeline',[]); rate=timeline[0].get('discount_rate',0) if timeline else 0; print('折扣率:', rate)"
# 应该返回: 0.25-0.35之间的小数
```

## 或者使用部署脚本

如果您可以SSH连接，可以使用部署脚本：

```bash
chmod +x scripts/deploy-remote.sh
./scripts/deploy-remote.sh
```

## 部署后验证

部署完成后，在本地运行自动化测试：

```bash
cd web/frontend
npx playwright test tests/production-test.spec.ts --project=chromium
```

预期结果：
- ✅ ECS资源总数: 1000+
- ✅ 折扣率格式: 0.25-0.35之间的小数
- ✅ 所有前端页面正常
