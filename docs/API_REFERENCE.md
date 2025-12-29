# API 参考文档

> CloudLens API v2.1.0  
> 最后更新：2025-12-23

---

## 📋 目录

- [基础信息](#基础信息)
- [认证](#认证)
- [错误处理](#错误处理)
- [API端点](#api端点)
  - [账号管理](#账号管理)
  - [配置管理](#配置管理)
  - [仪表板](#仪表板)
  - [资源查询](#资源查询)
  - [成本分析](#成本分析)
  - [安全合规](#安全合规)
  - [优化建议](#优化建议)
  - [预算管理](#预算管理)
  - [虚拟标签](#虚拟标签)
  - [告警管理](#告警管理)
  - [成本分配](#成本分配)
  - [AI优化器](#ai优化器)
  - [折扣分析](#折扣分析)
  - [报告生成](#报告生成)
  - [仪表板配置](#仪表板配置)

---

## 基础信息

### Base URL

```
开发环境: http://localhost:8000
生产环境: https://your-domain.com
```

### API 版本

当前版本：`v2.1.0`

### 内容类型

所有请求和响应都使用 `application/json` 格式。

### 交互式文档

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## 认证

> ⚠️ **注意**：当前版本（v2.1.0）API 认证功能尚未实现。所有端点都是公开访问的。  
> 计划在 Phase 5 中实现 JWT 认证和 API 限流。

### 未来认证方式（计划中）

```http
Authorization: Bearer <token>
```

---

## 错误处理

### 错误响应格式

所有错误响应都遵循统一格式：

```json
{
  "success": false,
  "error": "错误描述",
  "error_type": "ErrorType",
  "endpoint": "endpoint_name"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 错误类型

| 错误类型 | 说明 | 状态码 |
|---------|------|--------|
| `ValueError` | 参数值错误 | 400 |
| `KeyError` | 缺少必需参数 | 400 |
| `NotFoundError` | 资源不存在 | 404 |
| `PermissionError` | 权限不足 | 403 |
| `Exception` | 其他错误 | 500 |

---

## API端点

### 账号管理

#### 获取账号列表

```http
GET /api/accounts
```

**响应示例**：

```json
[
  {
    "name": "ydzn",
    "region": "cn-beijing",
    "access_key_id": "LTAI5t..."
  },
  {
    "name": "zmyc",
    "region": "cn-beijing",
    "access_key_id": "LTAI5t..."
  }
]
```

---

### 配置管理

#### 获取优化规则

```http
GET /api/config/rules
```

**响应示例**：

```json
{
  "idle_rules": {
    "ecs": {
      "cpu_threshold_percent": 5,
      "network_threshold_bytes_sec": 1000
    }
  }
}
```

#### 更新优化规则

```http
POST /api/config/rules
Content-Type: application/json

{
  "idle_rules": {
    "ecs": {
      "cpu_threshold_percent": 5,
      "network_threshold_bytes_sec": 1000
    }
  }
}
```

#### 获取通知配置

```http
GET /api/config/notifications
```

**响应示例**：

```json
{
  "email": "user@example.com",
  "auth_code": "***",
  "default_receiver_email": "alerts@example.com",
  "smtp_host": "smtp.qq.com",
  "smtp_port": 587
}
```

#### 更新通知配置

```http
POST /api/config/notifications
Content-Type: application/json

{
  "email": "user@example.com",
  "auth_code": "your_auth_code",
  "default_receiver_email": "alerts@example.com"
}
```

---

### 仪表板

#### 获取仪表板摘要

```http
GET /api/dashboard/summary?account={account_name}&force_refresh=false
```

**查询参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `account` | string | 是 | 账号名称 |
| `force_refresh` | boolean | 否 | 强制刷新缓存（默认：false） |

**响应示例**：

```json
{
  "account": "ydzn",
  "total_cost": 143299.34,
  "idle_count": 31,
  "cost_trend": "下降",
  "trend_pct": -53.79,
  "total_resources": 464,
  "resource_breakdown": {
    "ecs": 378,
    "rds": 52,
    "redis": 34
  },
  "alert_count": 0,
  "tag_coverage": 78.23,
  "savings_potential": 31299.17,
  "cached": false
}
```

#### 获取成本趋势

```http
GET /api/dashboard/trend?account={account_name}&days=30
```

**查询参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `account` | string | 是 | 账号名称 |
| `days` | integer | 否 | 查询天数（默认：30） |

#### 获取闲置资源

```http
GET /api/dashboard/idle?account={account_name}
```

**查询参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `account` | string | 是 | 账号名称 |

---

### 资源查询

#### 获取资源列表

```http
GET /api/resources?account={account_name}&resource_type={type}&limit=100
```

**查询参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `account` | string | 是 | 账号名称 |
| `resource_type` | string | 否 | 资源类型（ecs, rds, redis等） |
| `limit` | integer | 否 | 返回数量限制（默认：100） |

**响应示例**：

```json
{
  "resources": [
    {
      "id": "i-xxx",
      "name": "ECS实例",
      "type": "ecs",
      "status": "Running",
      "region": "cn-beijing",
      "cost": 100.50
    }
  ],
  "total": 378
}
```

#### 获取资源详情

```http
GET /api/resources/{resource_id}?account={account_name}
```

#### 获取资源监控指标

```http
GET /api/resources/{resource_id}/metrics?account={account_name}&days=14
```

---

### 成本分析

#### 获取成本概览

```http
GET /api/cost/overview?account={account_name}&start_date={date}&end_date={date}
```

#### 获取成本明细

```http
GET /api/cost/breakdown?account={account_name}&group_by=service
```

**查询参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `account` | string | 是 | 账号名称 |
| `group_by` | string | 否 | 分组方式（service, region, product） |

#### 获取账单概览

```http
GET /api/billing/overview?account={account_name}&billing_cycle={cycle}
```

#### 获取实例账单

```http
GET /api/billing/instance-bill?account={account_name}&instance_id={id}
```

---

### 安全合规

#### 获取安全概览

```http
GET /api/security/overview?account={account_name}
```

#### 获取安全检查列表

```http
GET /api/security/checks?account={account_name}&severity={level}
```

**查询参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `account` | string | 是 | 账号名称 |
| `severity` | string | 否 | 严重程度（high, medium, low） |

#### CIS合规检查

```http
GET /api/security/cis?account={account_name}
```

---

### 优化建议

#### 获取优化建议

```http
GET /api/optimization/suggestions?account={account_name}&limit=20
```

**查询参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `account` | string | 是 | 账号名称 |
| `limit` | integer | 否 | 返回数量限制（默认：20） |

**响应示例**：

```json
{
  "suggestions": [
    {
      "type": "idle_resource",
      "resource_id": "i-xxx",
      "resource_type": "ecs",
      "savings": 100.50,
      "action": "停止或释放闲置实例",
      "priority": "high"
    }
  ],
  "total_savings": 31299.17
}
```

---

### 预算管理

#### 获取预算列表

```http
GET /api/budgets?account={account_name}
```

**查询参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `account` | string | 否 | 账号名称（可选） |

**响应示例**：

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "12月预算",
      "amount": 50000.0,
      "period": "monthly",
      "type": "total",
      "start_date": "2025-12-01T00:00:00",
      "end_date": "2026-01-01T00:00:00",
      "alerts": [
        {
          "percentage": 90.0,
          "enabled": true
        }
      ]
    }
  ]
}
```

#### 获取预算详情

```http
GET /api/budgets/{budget_id}
```

#### 创建预算

```http
POST /api/budgets
Content-Type: application/json

{
  "name": "12月预算",
  "amount": 50000.0,
  "period": "monthly",
  "type": "total",
  "account_id": "account_id",
  "start_date": "2025-12-01",
  "end_date": "2026-01-01",
  "alerts": [
    {
      "percentage": 90.0,
      "enabled": true
    }
  ]
}
```

#### 更新预算

```http
PUT /api/budgets/{budget_id}
Content-Type: application/json

{
  "name": "更新后的预算名称",
  "amount": 60000.0
}
```

#### 删除预算

```http
DELETE /api/budgets/{budget_id}
```

#### 获取预算状态

```http
GET /api/budgets/{budget_id}/status
```

**响应示例**：

```json
{
  "budget_id": "uuid",
  "spent": 45000.0,
  "remaining": 5000.0,
  "percentage": 90.0,
  "status": "warning",
  "alerts_triggered": [
    {
      "threshold": 90.0,
      "current_rate": 90.0,
      "channels": ["email"]
    }
  ]
}
```

#### 获取预算趋势

```http
GET /api/budgets/{budget_id}/trend?days=30
```

---

### 虚拟标签

#### 获取虚拟标签列表

```http
GET /api/virtual-tags?account={account_name}
```

#### 获取虚拟标签详情

```http
GET /api/virtual-tags/{tag_id}
```

#### 创建虚拟标签

```http
POST /api/virtual-tags
Content-Type: application/json

{
  "name": "生产环境",
  "description": "生产环境资源",
  "rules": [
    {
      "field": "tag.Environment",
      "operator": "equals",
      "value": "production"
    }
  ],
  "account_id": "account_id"
}
```

#### 更新虚拟标签

```http
PUT /api/virtual-tags/{tag_id}
Content-Type: application/json

{
  "name": "更新后的标签名称",
  "rules": [...]
}
```

#### 删除虚拟标签

```http
DELETE /api/virtual-tags/{tag_id}
```

#### 预览虚拟标签匹配

```http
POST /api/virtual-tags/preview
Content-Type: application/json

{
  "rules": [
    {
      "field": "tag.Environment",
      "operator": "equals",
      "value": "production"
    }
  ],
  "account": "account_name"
}
```

#### 获取虚拟标签成本

```http
GET /api/virtual-tags/{tag_id}/cost?start_date={date}&end_date={date}
```

#### 清除虚拟标签缓存

```http
POST /api/virtual-tags/clear-cache
```

---

### 告警管理

#### 获取告警规则列表

```http
GET /api/alerts/rules?account={account_name}&enabled_only=false
```

#### 获取告警规则详情

```http
GET /api/alerts/rules/{rule_id}
```

#### 创建告警规则

```http
POST /api/alerts/rules
Content-Type: application/json

{
  "name": "高成本告警",
  "description": "当日成本超过阈值时触发",
  "metric": "daily_cost",
  "threshold": 1000.0,
  "operator": "greater_than",
  "account_id": "account_id",
  "enabled": true,
  "notification_channels": ["email"]
}
```

#### 更新告警规则

```http
PUT /api/alerts/rules/{rule_id}
Content-Type: application/json

{
  "threshold": 1500.0,
  "enabled": true
}
```

#### 删除告警规则

```http
DELETE /api/alerts/rules/{rule_id}
```

#### 获取告警列表

```http
GET /api/alerts?account={account_name}&status={status}&severity={level}
```

#### 检查告警规则

```http
POST /api/alerts/rules/{rule_id}/check
```

#### 检查所有告警规则

```http
POST /api/alerts/check-all
```

#### 更新告警状态

```http
PUT /api/alerts/{alert_id}/status
Content-Type: application/json

{
  "status": "resolved"
}
```

---

### 成本分配

#### 获取分配规则列表

```http
GET /api/cost-allocation/rules?account={account_name}&enabled_only=false
```

#### 获取分配规则详情

```http
GET /api/cost-allocation/rules/{rule_id}
```

#### 创建分配规则

```http
POST /api/cost-allocation/rules
Content-Type: application/json

{
  "name": "按部门分配",
  "description": "根据标签分配成本",
  "method": "equal",
  "account_id": "account_id",
  "tag_filter": "Department",
  "allocation_targets": ["dept1", "dept2"],
  "enabled": true
}
```

#### 更新分配规则

```http
PUT /api/cost-allocation/rules/{rule_id}
Content-Type: application/json

{
  "method": "weighted",
  "allocation_weights": "{\"dept1\": 0.6, \"dept2\": 0.4}"
}
```

#### 删除分配规则

```http
DELETE /api/cost-allocation/rules/{rule_id}
```

#### 执行分配规则

```http
POST /api/cost-allocation/rules/{rule_id}/execute
Content-Type: application/json

{
  "start_date": "2025-12-01",
  "end_date": "2025-12-31"
}
```

#### 获取分配结果列表

```http
GET /api/cost-allocation/results?account={account_name}&rule_id={id}
```

#### 获取分配结果详情

```http
GET /api/cost-allocation/results/{result_id}
```

---

### AI优化器

#### 获取优化建议

```http
GET /api/ai-optimizer/suggestions?account={account_name}&limit=20
```

#### 成本预测

```http
GET /api/ai-optimizer/predict?account={account_name}&days=30
```

#### 分析资源

```http
GET /api/ai-optimizer/analyze/{resource_type}/{resource_id}?account={account_name}
```

---

### 折扣分析

#### 获取折扣趋势

```http
GET /api/discounts/trend?account={account_name}&days=90
```

#### 获取产品折扣

```http
GET /api/discounts/products?account={account_name}&product_code={code}
```

#### 获取账单折扣

```http
GET /api/billing/discounts?account={account_name}&billing_cycle={cycle}
```

#### 获取季度折扣

```http
GET /api/discounts/quarterly?account={account_name}&year={year}
```

#### 获取年度折扣

```http
GET /api/discounts/yearly?account={account_name}&year={year}
```

#### 获取产品趋势

```http
GET /api/discounts/product-trends?account={account_name}&product_code={code}
```

#### 获取区域折扣

```http
GET /api/discounts/regions?account={account_name}
```

#### 获取订阅类型折扣

```http
GET /api/discounts/subscription-types?account={account_name}
```

#### 获取优化建议

```http
GET /api/discounts/optimization-suggestions?account={account_name}
```

#### 获取异常折扣

```http
GET /api/discounts/anomalies?account={account_name}
```

#### 获取产品区域矩阵

```http
GET /api/discounts/product-region-matrix?account={account_name}
```

#### 获取移动平均

```http
GET /api/discounts/moving-average?account={account_name}&window=7
```

#### 获取累计折扣

```http
GET /api/discounts/cumulative?account={account_name}
```

#### 获取实例生命周期

```http
GET /api/discounts/instance-lifecycle?account={account_name}&instance_id={id}
```

#### 获取折扣洞察

```http
GET /api/discounts/insights?account={account_name}
```

#### 导出折扣数据

```http
GET /api/discounts/export?account={account_name}&format=excel
```

---

### 报告生成

#### 生成报告

```http
POST /api/reports/generate
Content-Type: application/json

{
  "account": "account_name",
  "report_type": "cost",
  "format": "excel",
  "start_date": "2025-12-01",
  "end_date": "2025-12-31"
}
```

#### 获取报告列表

```http
GET /api/reports?account={account_name}
```

---

### 仪表板配置

#### 获取仪表板列表

```http
GET /api/dashboards?account={account_name}
```

#### 获取仪表板详情

```http
GET /api/dashboards/{dashboard_id}
```

#### 创建仪表板

```http
POST /api/dashboards
Content-Type: application/json

{
  "name": "成本仪表板",
  "account_id": "account_id",
  "widgets": [
    {
      "type": "cost_trend",
      "config": {...}
    }
  ]
}
```

#### 更新仪表板

```http
PUT /api/dashboards/{dashboard_id}
Content-Type: application/json

{
  "name": "更新后的仪表板名称",
  "widgets": [...]
}
```

#### 删除仪表板

```http
DELETE /api/dashboards/{dashboard_id}
```

---

### 账号设置

#### 获取账号设置列表

```http
GET /api/settings/accounts
```

#### 创建账号

```http
POST /api/settings/accounts
Content-Type: application/json

{
  "name": "new_account",
  "alias": "新账号",
  "provider": "aliyun",
  "region": "cn-beijing",
  "access_key_id": "LTAI5t...",
  "access_key_secret": "xxx"
}
```

#### 更新账号

```http
PUT /api/settings/accounts/{account_name}
Content-Type: application/json

{
  "alias": "更新后的别名",
  "region": "cn-shanghai"
}
```

#### 删除账号

```http
DELETE /api/settings/accounts/{account_name}
```

---

### 分析触发

#### 触发闲置资源分析

```http
POST /api/analyze/trigger
Content-Type: application/json

{
  "account": "account_name",
  "days": 7,
  "force": true
}
```

**响应示例**：

```json
{
  "status": "success",
  "count": 31,
  "cached": false,
  "data": [...]
}
```

---

## 速率限制

> ⚠️ **注意**：当前版本（v2.1.0）API 限流功能尚未实现。  
> 计划在 Phase 5 中实现 API 限流（100 请求/分钟）。

---

## 最佳实践

### 1. 使用缓存

大多数端点都支持缓存。如果不需要最新数据，可以依赖缓存以减少响应时间。

### 2. 分页查询

对于可能返回大量数据的端点（如资源列表），使用 `limit` 参数进行分页。

### 3. 错误处理

始终检查响应的 `success` 字段，并处理可能的错误情况。

### 4. 账号参数

大多数端点都需要 `account` 参数。确保始终提供正确的账号名称。

---

## 更新日志

### v2.1.0 (2025-12-23)

- ✅ 添加预算管理 API
- ✅ 添加虚拟标签 API
- ✅ 添加告警管理 API
- ✅ 添加成本分配 API
- ✅ 添加 AI 优化器 API
- ✅ 添加折扣分析 API
- ✅ 添加仪表板配置 API

---

## 相关文档

- [开发指南](DEVELOPMENT_GUIDE.md)
- [测试指南](TESTING_GUIDE.md)
- [贡献指南](CONTRIBUTING.md)
- [技术架构](TECHNICAL_ARCHITECTURE.md)

---

**如有问题，请查看 [Swagger UI](http://localhost:8000/docs) 获取交互式 API 文档。**

