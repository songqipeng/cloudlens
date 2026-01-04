# 成本趋势产品设计方案

## 📊 当前实现分析

### 当前实现逻辑

**数据来源**：
- 使用 `CostTrendAnalyzer` 记录成本快照（snapshot）
- 快照基于资源列表估算成本，不是真实账单数据
- 快照时间不固定，取决于何时调用 `record_cost_snapshot`

**成本计算方式**：
```python
# 当前实现：基于资源规格的简化估算
cost_map = {
    "ecs.t5-lc1m1.small": 50,  # 固定价格表
    "ecs.g6.large": 400,
    ...
}
```

**问题分析**：
1. ❌ **数据不准确**：使用固定价格表估算，不是真实成本
2. ❌ **时间不连续**：快照时间不固定，导致数据点稀疏
3. ❌ **波动大**：基于快照时间点的资源状态，资源变化会导致成本跳跃
4. ❌ **缺少历史数据**：没有按天存储的历史成本数据

---

## 🎯 产品需求

### 用户需求理解

1. **按月成本视图**：从有数据以来的月度成本柱状图/曲线图
2. **按天成本视图**：按天的成本曲线图
3. **数据逻辑清晰**：
   - 一个月内按天的数据，波动应该比较小
   - 不是账单数据，而是根据资源情况计算出来的每天的成本
   - 基于资源规格、计费类型、使用时长等计算

### 核心原则

- ✅ **数据连续性**：每天都有数据点，即使资源没有变化
- ✅ **数据平滑性**：按天数据波动小，反映资源稳定运行的成本
- ✅ **计算准确性**：基于资源实际规格和计费方式计算
- ✅ **历史追溯**：支持从有数据以来的所有历史数据

---

## 🏗️ 产品设计方案

### 1. 数据模型设计

#### 1.1 每日成本记录表（daily_cost_records）

```sql
CREATE TABLE daily_cost_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    account_name VARCHAR(64) NOT NULL,
    date DATE NOT NULL,  -- 日期：YYYY-MM-DD
    total_cost DECIMAL(12, 2) NOT NULL,  -- 当日总成本（元）
    
    -- 按资源类型分解
    ecs_cost DECIMAL(12, 2) DEFAULT 0,
    rds_cost DECIMAL(12, 2) DEFAULT 0,
    redis_cost DECIMAL(12, 2) DEFAULT 0,
    oss_cost DECIMAL(12, 2) DEFAULT 0,
    slb_cost DECIMAL(12, 2) DEFAULT 0,
    eip_cost DECIMAL(12, 2) DEFAULT 0,
    nat_cost DECIMAL(12, 2) DEFAULT 0,
    disk_cost DECIMAL(12, 2) DEFAULT 0,
    mongodb_cost DECIMAL(12, 2) DEFAULT 0,
    ack_cost DECIMAL(12, 2) DEFAULT 0,
    other_cost DECIMAL(12, 2) DEFAULT 0,
    
    -- 元数据
    resource_count INT DEFAULT 0,  -- 当日资源总数
    calculation_method VARCHAR(32),  -- 计算方式：estimated/billing/hybrid
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_account_date (account_name, date),
    INDEX idx_account_date (account_name, date),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 1.2 月度成本汇总表（monthly_cost_summary）

```sql
CREATE TABLE monthly_cost_summary (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    account_name VARCHAR(64) NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,  -- 1-12
    total_cost DECIMAL(12, 2) NOT NULL,
    
    -- 按资源类型分解（同daily_cost_records）
    ecs_cost DECIMAL(12, 2) DEFAULT 0,
    rds_cost DECIMAL(12, 2) DEFAULT 0,
    ...
    
    -- 统计信息
    avg_daily_cost DECIMAL(12, 2),  -- 日均成本
    max_daily_cost DECIMAL(12, 2),  -- 单日最高成本
    min_daily_cost DECIMAL(12, 2),  -- 单日最低成本
    days_count INT DEFAULT 0,  -- 有效天数
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_account_year_month (account_name, year, month),
    INDEX idx_account_year_month (account_name, year, month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

### 2. 成本计算逻辑

#### 2.1 每日成本计算流程

```
┌─────────────────────────────────────────┐
│  每日成本计算任务（定时任务）            │
│  每天 00:05 执行                        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  1. 获取昨日所有资源列表                 │
│     - ECS, RDS, Redis, OSS, SLB...     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  2. 对每个资源计算日成本                 │
│     - 包年包月：月成本 / 30             │
│     - 按量付费：小时成本 * 24           │
│     - 存储类：按容量和存储类型计算       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  3. 汇总当日总成本                      │
│     - 按资源类型分组                     │
│     - 计算总成本                         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  4. 保存到 daily_cost_records           │
│     - 如果记录已存在，更新               │
│     - 如果不存在，插入                   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  5. 更新月度汇总（如果是月末）           │
│     - 计算当月日均、最高、最低成本       │
│     - 保存到 monthly_cost_summary        │
└─────────────────────────────────────────┘
```

#### 2.2 资源成本计算公式

**ECS 实例（包年包月）**：
```
日成本 = 实例月价格 / 30
```

**ECS 实例（按量付费）**：
```
日成本 = 实例小时价格 × 24
```

**RDS 实例（包年包月）**：
```
日成本 = RDS月价格 / 30
```

**RDS 实例（按量付费）**：
```
日成本 = RDS小时价格 × 24
```

**OSS 存储**：
```
日成本 = (存储容量(GB) × 存储类型单价(元/GB/月) / 30) + 
         (流量费用(GB) × 流量单价(元/GB)) + 
         (请求次数 × 请求单价(元/万次))
```

**SLB 实例**：
```
日成本 = SLB月价格 / 30  (包年包月)
日成本 = SLB小时价格 × 24  (按量付费)
```

**EIP**：
```
日成本 = EIP月价格 / 30  (包年包月)
日成本 = EIP小时价格 × 24  (按量付费) + 流量费用
```

**云盘（Disk）**：
```
日成本 = 云盘容量(GB) × 云盘类型单价(元/GB/月) / 30
```

#### 2.3 价格数据来源优先级

1. **优先使用真实账单数据**（如果可用）：
   - 从 BSS API 获取实际账单
   - 从 MySQL 账单表查询历史账单

2. **其次使用询价API**：
   - 调用阿里云询价API获取实时价格
   - 缓存价格数据，避免频繁调用

3. **最后使用价格表估算**：
   - 维护常用规格的价格表
   - 根据规格模式匹配估算

---

### 3. 产品形态设计

#### 3.1 视图切换

```
┌─────────────────────────────────────────┐
│  成本趋势图表                            │
├─────────────────────────────────────────┤
│  [7天] [30天] [90天] [全部] [按月]      │  ← 时间范围选择
│                                         │
│  ┌─────────────────────────────────┐   │
│  │                                 │   │
│  │     成本趋势曲线图              │   │
│  │     (Area Chart / Line Chart)   │   │
│  │                                 │   │
│  └─────────────────────────────────┘   │
│                                         │
│  图例：[ECS] [RDS] [Redis] [OSS] ...   │
└─────────────────────────────────────────┘
```

#### 3.2 按月视图（柱状图）

**数据聚合**：
```python
# 从 daily_cost_records 按月聚合
SELECT 
    DATE_FORMAT(date, '%Y-%m') as month,
    SUM(total_cost) as monthly_cost,
    AVG(total_cost) as avg_daily_cost,
    MAX(total_cost) as max_daily_cost,
    MIN(total_cost) as min_daily_cost
FROM daily_cost_records
WHERE account_name = ?
GROUP BY DATE_FORMAT(date, '%Y-%m')
ORDER BY month
```

**图表类型**：
- **柱状图**：显示每月总成本
- **折线图**：显示每月日均成本趋势
- **组合图**：柱状图 + 折线图（总成本 + 日均成本）

#### 3.3 按天视图（曲线图）

**数据查询**：
```python
# 从 daily_cost_records 按天查询
SELECT 
    date,
    total_cost,
    ecs_cost,
    rds_cost,
    redis_cost,
    ...
FROM daily_cost_records
WHERE account_name = ?
  AND date >= ? AND date <= ?
ORDER BY date
```

**图表类型**：
- **面积图（Area Chart）**：显示总成本趋势，支持堆叠显示各资源类型
- **折线图（Line Chart）**：显示总成本趋势，简洁清晰
- **组合图**：总成本折线 + 各资源类型堆叠面积

#### 3.4 数据平滑处理

**问题**：资源创建/删除会导致成本跳跃

**解决方案**：
1. **资源生命周期追踪**：
   - 记录资源创建时间、删除时间
   - 计算资源在当天的实际使用时长
   - 按使用时长比例计算成本

2. **平滑算法**：
   ```python
   # 如果资源在当天创建或删除，按使用时长计算
   if resource.created_date == target_date:
       daily_cost = hourly_cost * (24 - created_hour) / 24
   elif resource.deleted_date == target_date:
       daily_cost = hourly_cost * deleted_hour / 24
   else:
       daily_cost = hourly_cost * 24  # 完整一天
   ```

3. **异常值处理**：
   - 检测成本突增/突降（超过50%变化）
   - 标记异常日期，显示提示信息
   - 允许用户查看详细原因

---

### 4. API 设计

#### 4.1 获取成本趋势数据

```python
GET /api/dashboard/trend

参数：
- account: 账号名称（必需）
- granularity: 粒度（daily/monthly，默认daily）
- start_date: 开始日期 YYYY-MM-DD（可选）
- end_date: 结束日期 YYYY-MM-DD（可选）
- days: 最近N天（可选，与日期范围二选一）
- group_by: 分组方式（resource_type/region，可选）

响应：
{
    "success": true,
    "data": {
        "granularity": "daily",  // 或 "monthly"
        "period": {
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "days": 31
        },
        "chart_data": [
            {
                "date": "2025-01-01",
                "total_cost": 1234.56,
                "breakdown": {
                    "ecs": 800.00,
                    "rds": 300.00,
                    "redis": 100.00,
                    "oss": 34.56
                }
            },
            ...
        ],
        "summary": {
            "total_cost": 38256.78,
            "avg_daily_cost": 1234.09,
            "max_daily_cost": 1500.00,
            "min_daily_cost": 1000.00,
            "trend": "上升",  // 上升/下降/平稳
            "trend_pct": 5.2  // 变化百分比
        }
    }
}
```

#### 4.2 获取月度成本汇总

```python
GET /api/cost/monthly-summary

参数：
- account: 账号名称（必需）
- start_month: 开始月份 YYYY-MM（可选）
- end_month: 结束月份 YYYY-MM（可选）

响应：
{
    "success": true,
    "data": [
        {
            "month": "2025-01",
            "total_cost": 37000.00,
            "avg_daily_cost": 1193.55,
            "max_daily_cost": 1500.00,
            "min_daily_cost": 1000.00,
            "days_count": 31,
            "breakdown": {
                "ecs": 24000.00,
                "rds": 9000.00,
                "redis": 3000.00,
                "oss": 1000.00
            }
        },
        ...
    ]
}
```

---

### 5. 数据计算任务

#### 5.1 定时任务设计

**任务1：每日成本计算任务**
- **执行时间**：每天 00:05（凌晨5分）
- **执行内容**：
  1. 获取昨日所有资源列表
  2. 计算每个资源的日成本
  3. 汇总并保存到 `daily_cost_records`
  4. 如果是月末，更新月度汇总

**任务2：历史数据补全任务**
- **执行时间**：每天 02:00（凌晨2点）
- **执行内容**：
  1. 检查是否有缺失的日期数据
  2. 如果有，使用最近一次的资源快照计算
  3. 补全缺失的日期数据

**任务3：月度汇总任务**
- **执行时间**：每月1日 01:00
- **执行内容**：
  1. 计算上月的月度汇总数据
  2. 保存到 `monthly_cost_summary`

#### 5.2 手动触发计算

```python
POST /api/cost/calculate-daily

参数：
- account: 账号名称（必需）
- date: 日期 YYYY-MM-DD（可选，默认昨天）
- force: 是否强制重新计算（默认false）

用途：
- 手动触发某一天的成本计算
- 用于数据修复或补全
```

---

### 6. 前端展示设计

#### 6.1 图表组件

**按天视图**：
```typescript
<CostTrendChart
  data={dailyData}
  type="area"  // area/line
  showBreakdown={true}  // 是否显示资源类型分解
  smooth={true}  // 是否平滑曲线
/>
```

**按月视图**：
```typescript
<CostTrendChart
  data={monthlyData}
  type="bar"  // bar/line
  showAvgLine={true}  // 是否显示日均成本折线
/>
```

#### 6.2 交互功能

1. **时间范围选择**：
   - 快捷选择：7天、30天、90天、全部
   - 自定义范围：日期选择器

2. **视图切换**：
   - 按天视图 / 按月视图
   - 图表类型切换：面积图/折线图/柱状图

3. **数据钻取**：
   - 点击日期/月份，查看详细成本分解
   - 悬停显示具体数值

4. **数据导出**：
   - 导出CSV/Excel
   - 导出图表图片

---

### 7. 实施计划

#### Phase 1: 数据模型和计算逻辑（1周）
- [ ] 创建 `daily_cost_records` 表
- [ ] 创建 `monthly_cost_summary` 表
- [ ] 实现每日成本计算逻辑
- [ ] 实现价格查询逻辑（优先账单，其次询价API，最后价格表）

#### Phase 2: 定时任务（3天）
- [ ] 实现每日成本计算任务
- [ ] 实现历史数据补全任务
- [ ] 实现月度汇总任务

#### Phase 3: API开发（3天）
- [ ] 实现 `/api/dashboard/trend` API（支持按天/按月）
- [ ] 实现 `/api/cost/monthly-summary` API
- [ ] 实现手动触发计算API

#### Phase 4: 前端开发（5天）
- [ ] 实现按天视图图表组件
- [ ] 实现按月视图图表组件
- [ ] 实现时间范围选择
- [ ] 实现视图切换功能
- [ ] 实现数据钻取和导出

#### Phase 5: 测试和优化（3天）
- [ ] 数据准确性测试
- [ ] 性能优化（数据量大时的查询优化）
- [ ] 用户体验优化

**总计：约3周**

---

### 8. 技术要点

#### 8.1 数据准确性保证

1. **价格数据优先级**：
   - 真实账单 > 询价API > 价格表估算

2. **资源状态追踪**：
   - 记录资源创建/删除时间
   - 按实际使用时长计算成本

3. **异常检测**：
   - 检测成本突增/突降
   - 标记异常数据，提示用户

#### 8.2 性能优化

1. **数据聚合**：
   - 月度数据预聚合，避免实时计算
   - 使用索引优化查询

2. **缓存策略**：
   - 历史数据缓存（7天以上）
   - 月度汇总缓存（1个月）

3. **分页加载**：
   - 超过90天的数据分页加载
   - 前端虚拟滚动

#### 8.3 数据一致性

1. **幂等性**：
   - 每日成本计算任务支持重复执行
   - 如果数据已存在，更新而非插入

2. **数据修复**：
   - 提供数据修复工具
   - 支持重新计算历史数据

---

## 📋 总结

### 核心改进点

1. ✅ **数据连续性**：每天都有数据点，不再依赖快照
2. ✅ **数据准确性**：优先使用真实账单，其次询价API
3. ✅ **数据平滑性**：按资源使用时长计算，避免跳跃
4. ✅ **历史追溯**：支持从有数据以来的所有历史数据
5. ✅ **灵活视图**：支持按天和按月两种视图

### 关键设计原则

- **数据驱动**：基于真实资源状态计算，而非估算
- **时间连续**：每天都有数据，保证图表连续性
- **计算准确**：优先使用真实账单，确保准确性
- **用户友好**：提供多种视图和交互方式

---

**文档版本**：v1.0  
**创建时间**：2026-01-04  
**作者**：Auto (AI Assistant)

