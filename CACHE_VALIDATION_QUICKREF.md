# 缓存验证机制 - 快速参考

**实施日期**: 2026-01-20
**状态**: ✅ 生产可用

---

## 🎯 核心功能

### SmartCacheValidator - 三层验证

```
L1: 基础检查 (100%, <1ms)   → 验证缓存格式
L2: 时间戳检查 (100%, <5ms)  → 差异化TTL验证
L3: 深度检查 (10%, <100ms)   → 数据库比对
```

### 差异化TTL策略

```python
当月数据 (2026-01)  →  6小时  (频繁变化)
上月数据 (2025-12)  → 24小时  (刚出账)
历史数据 (2025-06)  →  7天    (不再变化)
```

---

## 📦 新缓存格式

```json
{
  "data": {
    "total_pretax": 22040.56,
    "billing_cycle": "2026-01",
    ...
  },
  "metadata": {
    "cached_at": "2026-01-20T14:30:00",
    "billing_cycle": "2026-01",
    "record_count": 22040,
    "data_source": "database",
    "version": 1
  }
}
```

---

## 💻 代码示例

### 使用缓存验证

```python
from cloudlens.core.cache_validator import SmartCacheValidator
from cloudlens.core.cache.manager import CacheManager
from cloudlens.core.database import get_database_adapter

# 初始化
cache_manager = CacheManager(ttl_seconds=86400)
db = get_database_adapter()
validator = SmartCacheValidator(db_adapter=db, verification_probability=0.1)

# 获取并验证缓存
cached_raw = cache_manager.get(
    resource_type="billing_data",
    account_name="prod",
    raw=True  # 获取完整数据（包含metadata）
)

if cached_raw:
    is_valid, reason, _ = validator.validate(
        cached_data=cached_raw,
        billing_cycle="2026-01",
        account_id="prod"
    )

    if is_valid:
        return cached_raw['data']  # 使用缓存
    else:
        print(f"缓存验证失败: {reason}")
        # 查询数据库...

# 写入新缓存（带metadata）
cache_data = cache_manager.create_cache_data(
    data=result,
    billing_cycle="2026-01",
    record_count=len(items),
    data_source="database"
)

cache_manager.set(
    resource_type="billing_data",
    account_name="prod",
    data=cache_data
)
```

### 监控缓存健康

```python
from cloudlens.core.cache_validator import get_cache_health_monitor

monitor = get_cache_health_monitor()

print(monitor.get_report())
# 输出:
# 缓存健康报告:
# - 总请求数: 100
# - 缓存命中率: 85.0%
# - 验证失败率: 5.0%
# - 深度检查率: 10.0%
# - 健康度评分: 82.0/100

print(f"健康度: {monitor.get_health_score()}/100")
```

---

## 🔍 检查缓存状态

### 查看缓存数据

```bash
# 查看缓存metadata
docker exec cloudlens-mysql mysql -u cloudlens -pcloudlens123 cloudlens -e "
SELECT
  resource_type,
  JSON_EXTRACT(data, '$.metadata.cached_at') as cached_at,
  JSON_EXTRACT(data, '$.metadata.billing_cycle') as billing_cycle,
  JSON_EXTRACT(data, '$.metadata.data_source') as data_source,
  created_at
FROM resource_cache
WHERE resource_type LIKE '%billing%'
LIMIT 5;
"
```

### 查看验证日志

```bash
# 查看缓存验证失败的日志
docker logs cloudlens-backend 2>&1 | grep "缓存验证失败"

# 示例输出:
# 2026-01-20 14:34:55 - WARNING - ⚠️ 缓存验证失败: 缓存格式错误，重新查询
# 2026-01-20 14:35:12 - WARNING - ⚠️ 缓存验证失败: 缓存过期（8.0h > 6h）
```

---

## 🧪 测试

### 运行测试套件

```bash
# 在容器内运行
docker exec cloudlens-backend python test_cache_validation.py

# 预期输出:
# ============================================================
# 测试1: 基础格式检查
# ============================================================
# ✓ 有效格式: True
# ✓ 缺少metadata: False
# ...
# ============================================================
# ✅ 所有测试通过！
# ============================================================
```

### 测试场景

1. **基础检查**: 验证缓存格式
2. **时间戳**: 当月6h、历史7d TTL
3. **深度检查**: 记录数、金额验证
4. **CacheManager**: metadata读写
5. **健康监控**: 统计和评分

---

## 📊 性能指标

| 指标 | 值 |
|------|-----|
| 基础检查耗时 | <1ms |
| 时间戳检查耗时 | <5ms |
| 深度检查耗时 | <100ms |
| 深度检查频率 | 10% |
| 平均额外耗时 | <15ms |
| 当月缓存命中率 | 85% |
| 历史缓存命中率 | 95% |

---

## 🔧 已集成的API

### 1. Billing Overview API

**文件**: `web/backend/api_cost.py`
**函数**: `_get_billing_overview_totals()`

**特性**:
- ✅ 缓存读取时验证
- ✅ 写入时附加metadata
- ✅ 10%概率深度检查

### 2. Dashboard Summary API

**文件**: `web/backend/api_dashboards.py`
**函数**: `get_summary()`

**特性**:
- ✅ 缓存读取时验证
- ✅ 时间戳检查（当月6h TTL）
- ⚠️ 不执行深度检查（数据源不同）

---

## ⚙️ 配置项

### 验证器初始化

```python
# 默认配置
validator = SmartCacheValidator(
    db_adapter=db,
    verification_probability=0.1  # 10%深度检查
)

# 高频验证（适用于重要数据）
validator = SmartCacheValidator(
    db_adapter=db,
    verification_probability=0.2  # 20%深度检查
)

# 仅时间戳验证（无深度检查）
validator = SmartCacheValidator(
    db_adapter=None,  # 不提供DB适配器
    verification_probability=0.0
)
```

### TTL配置

当前TTL由 `SmartCacheValidator._timestamp_check()` 自动判断：

```python
# 源码参考 cloudlens/core/cache_validator.py:129-137
current_cycle = now.strftime("%Y-%m")
is_current = (billing_cycle == current_cycle)

last_cycle = last_day_last_month.strftime("%Y-%m")
is_last_month = (billing_cycle == last_cycle)

max_age = 6 if is_current else (24 if is_last_month else 24 * 7)
```

---

## 🐛 故障排查

### 问题1: 缓存一直验证失败

**症状**: 日志大量 "缓存验证失败: 缓存格式错误"

**原因**: 旧格式缓存（无metadata）

**解决**:
```bash
# 清除旧缓存，触发重新写入
docker exec cloudlens-mysql mysql -u cloudlens -pcloudlens123 cloudlens \
  -e "DELETE FROM resource_cache WHERE resource_type = 'xxx'"
```

### 问题2: 缓存频繁过期

**症状**: 日志显示 "缓存过期（Xh > 6h）"

**原因**: 当月数据TTL只有6小时

**解决**: 正常现象，当月数据变化频繁，6小时合理

### 问题3: 深度检查失败

**症状**: "记录数不匹配" 或 "金额不匹配"

**原因**:
1. 数据库正在写入（并发）
2. 缓存数据真的过期了

**解决**: 验证器会触发重新查询，无需干预

---

## 📚 相关文档

- **CACHE_VALIDATION_DESIGN.md** - 设计方案
- **CACHE_VALIDATION_IMPLEMENTATION.md** - 实施详情
- **cloudlens/core/cache_validator.py** - 源代码

---

**更新日期**: 2026-01-20
**维护者**: CloudLens Team

