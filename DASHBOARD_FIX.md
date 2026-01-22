# 仪表盘数据丢失问题修复

## 问题描述

您报告的问题：
> "比如告警卡片，刚刷新有数据过两秒就没数据了"

## 问题分析

### 现象
1. 页面刷新后，告警卡片显示正确的数据（alert_count: 51）
2. 大约2秒后，数据变为0
3. 同样的问题也影响标签覆盖率（tag_coverage）和资源总数（total_resources）

### 根本原因

通过Chrome浏览器调试和日志分析，发现了问题的根本原因：

1. **数据加载流程**:
   ```
   初始加载时:
   17:55:10 - /api/dashboard/summary 返回 alert_count: 0
   17:55:10 - /api/security/overview 返回 alert_count: 51 ✅
   17:55:10 - summary状态更新为 alert_count: 51

   2秒后的polling:
   17:55:12 - /api/dashboard/summary 再次调用，返回 alert_count: 0
   17:55:12 - 使用 ...refreshedSummary 覆盖整个summary对象
   17:55:12 - alert_count 被覆盖为 0 ❌
   ```

2. **问题代码** (dashboard.tsx:367-371):
   ```typescript
   setSummary((prev: any) => ({
     ...(prev || {}),
     ...refreshedSummary,  // ❌ 这会覆盖所有字段
     loading: false
   }))
   ```

3. **为什么会这样**:
   - dashboard.tsx 有一个polling机制，用于等待summary数据加载完成
   - 当初始summary显示loading状态时，会每2秒轮询一次
   - 轮询时使用 `...refreshedSummary` 会将所有字段覆盖
   - 由于 `/api/dashboard/summary` 返回的 alert_count、tag_coverage 等字段都是0
   - 这些0值覆盖了之前从其他API获取的正确值

## 解决方案

### 修改内容

修改 `web/frontend/app/_pages/dashboard.tsx` 中的两处代码：

1. **初始加载时** (行311-325):
   ```typescript
   // 只设置 summary API 提供的核心字段，其他字段由后续的API补充
   setSummary((prev: any) => ({
     ...(prev || {}),
     total_cost: actualData.total_cost ?? prev?.total_cost ?? 0,
     cost_trend: actualData.cost_trend ?? prev?.cost_trend ?? "N/A",
     trend_pct: actualData.trend_pct ?? prev?.trend_pct ?? 0,
     idle_count: actualData.idle_count ?? prev?.idle_count ?? 0,
     savings_potential: actualData.savings_potential ?? prev?.savings_potential ?? 0,
     loading: actualData.loading ?? false
   }))
   ```

2. **Polling更新时** (行349-382):
   ```typescript
   // 只更新 summary API 应该提供的字段，保留从其他API获取的数据
   setSummary((prev: any) => ({
     ...(prev || {}),
     total_cost: refreshedSummary.total_cost ?? prev?.total_cost ?? 0,
     cost_trend: refreshedSummary.cost_trend ?? prev?.cost_trend ?? "N/A",
     trend_pct: refreshedSummary.trend_pct ?? prev?.trend_pct ?? 0,
     idle_count: refreshedSummary.idle_count ?? prev?.idle_count ?? 0,
     savings_potential: refreshedSummary.savings_potential ?? prev?.savings_potential ?? 0,
     loading: false
   }))
   ```

### 修改原理

- ✅ **只更新summary API应该提供的字段**: total_cost, cost_trend, trend_pct, idle_count, savings_potential
- ✅ **保留其他API设置的字段**: alert_count (来自security/overview), tag_coverage (来自security/overview), total_resources (来自resources API)
- ✅ **使用 `??` 运算符确保数据优先级**: 新值 ?? 旧值 ?? 默认值

## 测试方法

### 1. 重新构建前端Docker镜像

```bash
cd /Users/songqipeng/cloudlens
docker-compose build frontend
docker-compose up -d frontend
```

### 2. 测试步骤

1. 打开浏览器: http://localhost:3000/a/ydzn
2. 刷新页面（F5）
3. 观察告警卡片:
   - 初始显示应该显示: **51** (红色)
   - 2秒后应该仍然显示: **51** (不应该变成0)
4. 观察标签覆盖率:
   - 应该显示: **76.8%** (紫色)
   - 不应该变成0.0%
5. 观察资源总数:
   - 应该显示: **475** (绿色)
   - 不应该变成0

### 3. 验证控制台日志

打开Chrome开发者工具 (F12) -> Console，应该看到：

```
[Dashboard] 📊 安全概览数据: 标签覆盖率=76.77%, 告警数量=51
[Dashboard] ✅ 更新安全概览数据到 summary
[Dashboard] Summary 数据已返回，停止轮询
```

**重要**: 在"停止轮询"之后，alert_count 和 tag_coverage 应该保持不变。

## 影响范围

### 修复的问题
- ✅ 告警数量不再被覆盖为0
- ✅ 标签覆盖率不再被覆盖为0%
- ✅ 资源总数不再被覆盖为0

### 不影响的功能
- ✅ 总成本、成本趋势等数据仍然正常更新
- ✅ 闲置资源数量正常显示
- ✅ 节省潜力数据正常显示

## 文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| web/frontend/app/_pages/dashboard.tsx | 修改 | 修复polling覆盖数据的问题 |

## Git提交

```bash
Commit: 29de992
Message: fix(frontend): 修复仪表盘数据被polling覆盖的问题
Branch: youthful-saha
```

## 后续建议

### 1. 后端API优化
考虑让 `/api/dashboard/summary` 返回完整的数据，包括：
- alert_count (从security/overview获取)
- tag_coverage (从security/overview获取)
- total_resources (从resources API计算)

这样前端就不需要并行调用多个API来补充数据。

### 2. 前端架构优化
可以考虑使用React Query或SWR等数据获取库，提供更好的：
- 缓存管理
- 重新验证策略
- 乐观更新
- 避免不必要的数据覆盖

---

**修复日期**: 2026-01-22
**修复人员**: Claude Sonnet 4.5
