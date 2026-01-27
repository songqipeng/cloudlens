# 服务器部署说明

## 当前状态

由于SSH连接失败（`Operation not permitted`），无法直接登录服务器。可能原因：
1. 安全组未开放22端口
2. 需要使用特定的SSH密钥
3. 服务器IP已变更

## 解决方案

### 方案1: 手动SSH连接（推荐）

如果您可以SSH连接到服务器，请执行以下命令：

```bash
# 1. SSH登录
ssh ec2-user@95.40.35.172
# 或使用特定密钥
ssh -i ~/.ssh/your-key.pem ec2-user@95.40.35.172

# 2. 更新代码
cd /opt/cloudlens/app
git fetch origin
git checkout zealous-torvalds
git pull origin zealous-torvalds

# 3. 重启服务
docker-compose restart backend frontend

# 4. 等待服务启动
sleep 15

# 5. 清除缓存
docker exec cloudlens-redis redis-cli FLUSHDB

# 6. 验证部署
curl -s 'http://localhost:8000/api/resources?account=mock-prod&type=ecs&force_refresh=true' | python3 -c "import sys, json; d=json.load(sys.stdin); print('ECS总数:', d.get('pagination',{}).get('total', 0))"
# 应该返回: 1000

curl -s 'http://localhost:8000/api/discounts/trend?account=mock-prod&months=1' | python3 -c "import sys, json; d=json.load(sys.stdin); timeline=d.get('data',{}).get('trend_analysis',{}).get('timeline',[]); rate=timeline[0].get('discount_rate',0) if timeline else 0; print('折扣率:', rate)"
# 应该返回: 0.25-0.35之间的小数
```

### 方案2: 使用AWS Systems Manager (SSM)

如果EC2实例已配置SSM，可以使用：

```bash
# 通过SSM执行命令
aws ssm send-command \
  --instance-ids i-0d9d58a28a95654fd \
  --region ap-northeast-1 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["cd /opt/cloudlens/app && git fetch origin && git checkout zealous-torvalds && git pull origin zealous-torvalds && docker-compose restart backend frontend"]'

# 查看命令执行结果
aws ssm get-command-invocation \
  --command-id <command-id> \
  --instance-id i-0d9d58a28a95654fd \
  --region ap-northeast-1
```

### 方案3: 使用GitHub Actions自动部署

已创建 `.github/workflows/deploy.yml`，需要：
1. 在GitHub仓库设置中添加SSH私钥到Secrets（`SSH_PRIVATE_KEY`）
2. 推送代码到 `zealous-torvalds` 分支时会自动部署

### 方案4: 通过Web界面

如果服务器有Web管理界面，可以通过Web界面执行部署命令。

## 验证部署

部署完成后，运行自动化测试验证：

```bash
cd web/frontend
npx playwright test tests/production-test.spec.ts --project=chromium
```

## 预期结果

部署成功后：
- ✅ ECS资源总数: 1000+
- ✅ 折扣率格式: 0.25-0.35之间的小数
- ✅ 所有前端页面正常访问
- ✅ 折扣分析页面所有Tab正常工作
