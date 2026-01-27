# 部署检查清单

## 当前状态

### ✅ 已完成的代码修复
1. **资源数量增加**: ECS 1000+, RDS 122+, Redis 80+ (总计 1202+)
2. **Mock Provider**: 已实现完整的Mock数据生成
3. **折扣分析API**: 所有端点已支持Mock模式
4. **区域查询**: `_get_all_regions` 已支持Mock模式

### ⚠️ 需要服务器更新的问题

#### 1. 资源数量不足
- **当前**: 319 ECS
- **预期**: 1000+ ECS
- **原因**: 服务器代码未更新到最新版本
- **解决方案**: 
  ```bash
  ssh ec2-user@95.40.35.172
  cd /opt/cloudlens/app
  git fetch origin
  git checkout zealous-torvalds
  git pull origin zealous-torvalds
  docker-compose restart backend
  # 清除缓存
  docker exec cloudlens-redis redis-cli FLUSHDB
  ```

#### 2. 折扣率格式
- **当前显示**: 30.0%
- **代码中**: 已经是小数形式 (0.25-0.35)
- **可能原因**: 前端显示时乘以了100，或者服务器返回了旧格式
- **验证方法**: 
  ```bash
  curl 'https://cloudlens.songqipeng.com/api/discounts/trend?account=mock-prod&months=1' | jq '.data.trend_analysis.timeline[0].discount_rate'
  ```
- **如果返回30.0**: 需要检查服务器代码是否更新
- **如果返回0.3**: 前端显示逻辑需要调整

#### 3. 服务器连接问题
- **错误**: `ERR_CONNECTION_CLOSED`
- **可能原因**: 
  - SSL证书配置问题
  - 服务器防火墙规则
  - ALB健康检查失败
- **检查方法**:
  ```bash
  # 检查ALB目标组健康状态
  aws elbv2 describe-target-health \
    --target-group-arn <target-group-arn> \
    --region ap-northeast-1
  
  # 检查EC2实例状态
  aws ec2 describe-instance-status \
    --instance-ids i-0d9d58a28a95654fd \
    --region ap-northeast-1
  ```

## 自动化测试结果

### 测试通过 (2/6)
- ✅ 成本分析页面: 图表正常显示
- ✅ API响应验证: API可访问，但数据需要更新

### 测试失败 (3/6)
- ❌ 登录页面: 连接失败
- ❌ 仪表盘页面: 连接失败  
- ❌ 资源管理页面: 连接失败
- ❌ 折扣分析页面: 连接失败

### 测试跳过 (1/6)
- ⏭️ 登录页面: 连接失败后跳过

## 下一步操作

### 立即执行
1. **SSH到服务器更新代码**
   ```bash
   ssh ec2-user@95.40.35.172
   cd /opt/cloudlens/app
   git pull origin zealous-torvalds
   docker-compose restart backend frontend
   ```

2. **清除缓存**
   ```bash
   docker exec cloudlens-redis redis-cli FLUSHDB
   ```

3. **验证资源数量**
   ```bash
   curl 'https://cloudlens.songqipeng.com/api/resources?account=mock-prod&type=ecs&force_refresh=true' | jq '.pagination.total'
   # 应该返回 1000+
   ```

4. **验证折扣率格式**
   ```bash
   curl 'https://cloudlens.songqipeng.com/api/discounts/trend?account=mock-prod&months=1' | jq '.data.trend_analysis.timeline[0].discount_rate'
   # 应该返回 0.25-0.35 之间的小数
   ```

### 验证完成后
5. **重新运行自动化测试**
   ```bash
   cd web/frontend
   npx playwright test tests/production-test.spec.ts --project=chromium
   ```

6. **检查测试报告**
   - 查看 `web/frontend/test-recordings/` 中的截图
   - 查看 `web/frontend/tests/test-report.md`

## 代码提交记录

- `3adf13e`: 增加Mock资源数量到1000+，修复区域查询支持Mock模式
- `28a37e7`: 添加生产环境自动化测试脚本

## 测试文件位置

- 测试脚本: `web/frontend/tests/production-test.spec.ts`
- 测试报告: `web/frontend/tests/test-report.md`
- 测试截图: `web/frontend/test-recordings/`
