# CloudLens 完整测试计划

## 测试目标
确保产品功能完整、稳定、数据准确，可以交付使用。

---

## 一、功能测试清单

### 1. 账号管理功能 ✅

#### 测试用例
- [ ] 添加新账号
- [ ] 查看账号列表
- [ ] 编辑账号信息
- [ ] 删除账号
- [ ] 账号配置验证

#### API端点
```bash
GET    /api/config/accounts
POST   /api/config/accounts
PUT    /api/config/accounts/{name}
DELETE /api/config/accounts/{name}
```

#### 验证标准
- 账号信息正确保存
- 密钥信息加密存储
- 账号列表正确显示
- 删除后不影响历史数据

---

### 2. 账单查询功能 ✅

#### 测试用例
- [ ] 查询指定月份账单
- [ ] 查询多个月份账单
- [ ] 按产品筛选
- [ ] 按实例筛选
- [ ] 按金额范围筛选
- [ ] 分页查询

#### API端点
```bash
GET /api/billing/list?account=prod&billing_cycle=2024-12
GET /api/billing/summary?account=prod&start_date=2024-06&end_date=2024-12
```

#### 验证标准
- 查询结果准确
- 金额计算正确
- 筛选条件生效
- 分页功能正常

---

### 3. 折扣分析功能 ✅

#### 测试用例
- [ ] 折扣趋势分析（月度）
- [ ] 产品折扣分析
- [ ] 季度折扣对比
- [ ] 年度折扣对比
- [ ] 合同折扣分析
- [ ] 实例折扣统计

#### API端点
```bash
GET /api/discounts/trend?account=prod&months=12
GET /api/discounts/products?account=prod&months=12
GET /api/discounts/quarterly?account=prod&quarters=4
GET /api/discounts/yearly?account=prod
```

#### 验证标准
- 折扣率计算正确（invoice_discount / (pretax_amount + invoice_discount)）
- 趋势分析准确
- 产品排序正确
- 数据聚合无误

---

### 4. 成本分析功能

#### 测试用例
- [ ] 月度成本趋势
- [ ] 产品成本分布
- [ ] 区域成本分析
- [ ] 成本预测
- [ ] 同比环比分析

#### API端点
```bash
GET /api/costs/trend?account=prod&months=12
GET /api/costs/by-product?account=prod
GET /api/costs/by-region?account=prod
GET /api/costs/forecast?account=prod&months=3
```

#### 验证标准
- 成本计算准确
- 趋势数据正确
- 预测算法合理
- 可视化数据完整

---

### 5. 告警功能

#### 测试用例
- [ ] 创建告警规则
- [ ] 修改告警规则
- [ ] 删除告警规则
- [ ] 告警触发测试
- [ ] 告警历史查询
- [ ] 告警通知（邮件/Webhook）

#### API端点
```bash
GET    /api/alerts/rules
POST   /api/alerts/rules
PUT    /api/alerts/rules/{id}
DELETE /api/alerts/rules/{id}
GET    /api/alerts/history
```

#### 验证标准
- 规则创建成功
- 阈值检测准确
- 告警及时触发
- 通知正确发送

---

### 6. 仪表板功能

#### 测试用例
- [ ] 首页总览数据
- [ ] 成本概览卡片
- [ ] 折扣概览卡片
- [ ] 告警概览卡片
- [ ] 趋势图表展示
- [ ] 数据实时刷新

#### API端点
```bash
GET /api/dashboards/summary?account=prod
GET /api/dashboards/widgets?account=prod
```

#### 验证标准
- 所有指标正确
- 图表数据准确
- 刷新功能正常
- 响应时间 < 2s

---

### 7. 资源管理功能

#### 测试用例
- [ ] 查询ECS实例列表
- [ ] 查询RDS实例列表
- [ ] 查询OSS bucket列表
- [ ] 资源成本关联
- [ ] 资源标签管理

#### API端点
```bash
GET /api/resources/ecs?account=prod
GET /api/resources/rds?account=prod
GET /api/resources/oss?account=prod
```

#### 验证标准
- 资源列表完整
- 状态信息准确
- 成本关联正确
- 标签管理正常

---

### 8. 预算管理功能

#### 测试用例
- [ ] 创建月度预算
- [ ] 创建季度预算
- [ ] 创建年度预算
- [ ] 预算超支告警
- [ ] 预算使用率查询
- [ ] 预算对比分析

#### API端点
```bash
GET    /api/budgets/list?account=prod
POST   /api/budgets/create
PUT    /api/budgets/{id}
DELETE /api/budgets/{id}
GET    /api/budgets/usage?account=prod
```

#### 验证标准
- 预算创建成功
- 使用率计算准确
- 超支告警及时
- 对比数据正确

---

### 9. 优化建议功能

#### 测试用例
- [ ] 资源优化建议
- [ ] 成本优化建议
- [ ] 性能优化建议
- [ ] 安全优化建议
- [ ] 建议优先级排序

#### API端点
```bash
GET /api/optimization/recommendations?account=prod
GET /api/optimization/cost-saving?account=prod
```

#### 验证标准
- 建议合理可行
- 优先级正确
- 节省金额准确
- 可实施性强

---

### 10. 报告生成功能

#### 测试用例
- [ ] 生成月度报告
- [ ] 生成季度报告
- [ ] 生成年度报告
- [ ] 自定义时间范围报告
- [ ] 报告导出（PDF/Excel）

#### API端点
```bash
POST /api/reports/generate
GET  /api/reports/list
GET  /api/reports/download/{id}
```

#### 验证标准
- 报告数据完整
- 格式正确美观
- 导出功能正常
- 下载速度快

---

## 二、数据准确性测试

### 1. 账单数据准确性

#### 测试场景
```python
# 场景1: 账单金额计算
官方价格 = pretax_amount + invoice_discount
实付金额 = pretax_amount
折扣金额 = invoice_discount
折扣率 = invoice_discount / 官方价格

# 场景2: 月度汇总
月度总额 = SUM(pretax_amount)
月度折扣 = SUM(invoice_discount)
月度官方价 = 月度总额 + 月度折扣

# 场景3: 产品维度聚合
产品成本 = SUM(pretax_amount) WHERE product_name = 'X'
产品折扣 = SUM(invoice_discount) WHERE product_name = 'X'
```

#### 验证方法
- 手动计算对比
- SQL查询验证
- 多次查询结果一致
- 与阿里云账单对比

---

### 2. 折扣分析准确性

#### 测试数据集
```sql
-- 测试数据
account_id='prod'
billing_cycle IN ('2024-06', '2024-07', '2024-08', '2024-09', '2024-10', '2024-11', '2024-12', '2025-01')

-- 预期结果
平均折扣率 ≈ 21.19%
最新折扣率 ≈ 21.28%
趋势方向 = "平稳"
总节省 ≈ ¥20,380
```

#### 验证步骤
1. 查询API返回数据
2. 直接查询数据库
3. 手动Excel计算
4. 三者结果对比

---

### 3. 缓存一致性测试

#### 测试场景
- 缓存数据与数据库一致
- 缓存过期正确刷新
- 缓存清除完全生效
- 并发访问缓存正确

#### 验证方法
```bash
# 查询API（首次，无缓存）
curl "/api/discounts/trend?account=prod&months=8"

# 查询API（第二次，有缓存）
curl "/api/discounts/trend?account=prod&months=8"

# 强制刷新缓存
curl "/api/discounts/trend?account=prod&months=8&force_refresh=true"

# 验证数据一致
```

---

## 三、性能测试

### 1. 响应时间测试

#### 性能标准
| API类型 | 目标响应时间 | 最大响应时间 |
|---------|------------|------------|
| 简单查询 | < 500ms | < 1s |
| 聚合查询 | < 1s | < 2s |
| 复杂分析 | < 2s | < 5s |
| 报告生成 | < 5s | < 10s |

#### 测试工具
```bash
# 使用Apache Bench测试
ab -n 1000 -c 10 http://localhost:8000/health

# 使用wrk测试
wrk -t4 -c100 -d30s http://localhost:8000/api/discounts/trend?account=prod

# 使用curl测试单次
time curl "http://localhost:8000/api/discounts/trend?account=prod&months=12"
```

---

### 2. 并发测试

#### 测试场景
- 100并发用户
- 500并发用户
- 1000并发用户

#### 验证标准
- 无错误返回
- 响应时间稳定
- 数据库连接正常
- 内存使用合理

---

### 3. 数据库性能测试

#### 测试查询
```sql
-- 查询1: 月度聚合（最常用）
SELECT billing_cycle, SUM(pretax_amount), SUM(invoice_discount)
FROM bill_items
WHERE account_id = 'prod'
GROUP BY billing_cycle
ORDER BY billing_cycle DESC
LIMIT 12;

-- 查询2: 产品聚合
SELECT product_name, SUM(pretax_amount)
FROM bill_items
WHERE account_id = 'prod'
  AND billing_cycle BETWEEN '2024-06' AND '2024-12'
GROUP BY product_name
ORDER BY SUM(pretax_amount) DESC
LIMIT 20;

-- 查询3: 实例聚合
SELECT instance_id, product_name, SUM(pretax_amount)
FROM bill_items
WHERE account_id = 'prod'
  AND instance_id IS NOT NULL
GROUP BY instance_id, product_name
ORDER BY SUM(pretax_amount) DESC
LIMIT 50;
```

#### 性能目标
- 每个查询 < 200ms
- 使用正确的索引
- 避免全表扫描

---

## 四、兼容性测试

### 1. 浏览器兼容性
- [ ] Chrome (最新版)
- [ ] Firefox (最新版)
- [ ] Safari (最新版)
- [ ] Edge (最新版)

### 2. 数据库兼容性
- [ ] MySQL 8.0+
- [ ] MariaDB 10.5+ (可选)

### 3. Python版本
- [ ] Python 3.11
- [ ] Python 3.10 (可选)

---

## 五、安全测试

### 1. 认证授权
- [ ] API密钥验证
- [ ] 会话管理
- [ ] 权限控制
- [ ] 密码加密存储

### 2. 数据安全
- [ ] SQL注入防护
- [ ] XSS防护
- [ ] CSRF防护
- [ ] 敏感数据加密

### 3. 网络安全
- [ ] HTTPS配置
- [ ] CORS配置
- [ ] 安全头设置
- [ ] 速率限制

---

## 六、测试执行计划

### 阶段1: 单元测试（1-2天）
```bash
# 运行所有单元测试
./scripts/dev.sh test

# 检查代码覆盖率
pytest --cov=cloudlens --cov-report=html
```

### 阶段2: 集成测试（2-3天）
```bash
# 启动测试环境
docker compose -f docker-compose.staging.yml up -d

# 运行集成测试
pytest tests/integration/ -v

# API端点测试
pytest tests/api/ -v
```

### 阶段3: 功能测试（3-5天）
- 按功能模块逐一测试
- 记录测试结果
- 修复发现的Bug
- 回归测试

### 阶段4: 性能测试（1-2天）
- 响应时间测试
- 并发测试
- 数据库性能测试
- 优化慢查询

### 阶段5: 安全测试（1天）
- 安全扫描
- 漏洞检查
- 修复安全问题

### 阶段6: 用户验收测试（2-3天）
- 完整业务流程测试
- 数据准确性验证
- 用户体验测试
- 收集反馈

---

## 七、Bug追踪

### Bug优先级定义

| 级别 | 定义 | 响应时间 | 示例 |
|------|------|---------|------|
| P0 | 系统崩溃 | 立即 | 服务无法启动 |
| P1 | 核心功能失效 | 4小时 | 账单查询失败 |
| P2 | 重要功能异常 | 1天 | 折扣计算错误 |
| P3 | 次要功能问题 | 3天 | UI显示异常 |
| P4 | 优化建议 | 下版本 | 性能优化 |

### Bug追踪表格

| ID | 功能 | 描述 | 优先级 | 状态 | 修复人 | 修复时间 |
|----|------|------|--------|------|--------|---------|
| BUG-001 | 折扣分析 | account_id格式错误 | P1 | ✅已修复 | Claude | 2026-01-20 |
| BUG-002 | 折扣分析 | 缺少聚合方法 | P1 | ✅已修复 | Claude | 2026-01-20 |

---

## 八、测试报告模板

### 测试报告结构
```markdown
# CloudLens 测试报告 - [日期]

## 1. 测试概况
- 测试版本: v1.1.0
- 测试环境: Staging
- 测试周期: [开始日期] - [结束日期]
- 测试人员: [姓名]

## 2. 测试结果汇总
- 测试用例总数: XX
- 通过: XX (XX%)
- 失败: XX (XX%)
- 阻塞: XX (XX%)

## 3. 功能测试结果
### 账单查询
- 状态: ✅ 通过
- 测试用例: 15/15
- 发现问题: 0

### 折扣分析
- 状态: ✅ 通过
- 测试用例: 12/12
- 发现问题: 0

## 4. 性能测试结果
- 平均响应时间: XXms
- 并发处理能力: XX req/s
- 数据库查询性能: ✅ 达标

## 5. 发现的问题
| ID | 描述 | 优先级 | 状态 |
|----|------|--------|------|
| ... | ... | ... | ... |

## 6. 结论与建议
- 总体评价: [优秀/良好/一般/差]
- 是否可发布: [是/否]
- 建议: ...
```

---

## 九、交付标准

### 产品交付清单
- [ ] 所有P0/P1/P2 Bug已修复
- [ ] 核心功能100%通过测试
- [ ] 性能达标
- [ ] 安全测试通过
- [ ] 文档完整（API文档、用户手册、部署文档）
- [ ] 代码已提交并打标签
- [ ] 镜像已构建并推送
- [ ] 生产环境部署成功
- [ ] 健康检查通过
- [ ] 用户验收通过

### 质量标准
- ✅ 代码覆盖率 > 80%
- ✅ API响应时间 < 2s
- ✅ 并发支持 > 100 req/s
- ✅ 数据准确率 100%
- ✅ 7x24小时稳定运行

---

**测试是质量的保证！让我们确保交付一个稳定可靠的产品！** 🎯
