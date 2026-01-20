# 缓存验证机制设计

**设计日期**: 2026-01-20
**目的**: 确保缓存数据的正确性和及时性

---

## 🎯 核心问题

**不能完全依赖缓存的原因**:
1. 缓存可能过期但未失效（TTL内但数据已变化）
2. 缓存可能损坏或不完整
3. 缓存可能与数据库不一致
4. 当月数据每天都在增长，24小时缓存太长

---

## 💡 解决方案：多层验证机制

### 方案1: 基于时间戳的智能验证（推荐）

#### 核心思路

在缓存中存储**元数据**，用于验证缓存是否仍然有效：

```python
cache_data = {
    "data": {...},  # 实际数据
    "metadata": {
        "cached_at": "2026-01-20T10:00:00",      # 缓存时间
        "billing_cycle": "2026-01",               # 账期
        "record_count": 1234,                     # 记录数（用于快速验证）
        "last_bill_date": "2026-01-19",          # 最后一条账单日期
        "data_hash": "abc123...",                # 数据哈希（可选）
        "version": 1                             # 数据版本
    }
}
```

#### 验证逻辑

```python
def is_cache_valid(cached_data, billing_cycle):
    """验证缓存是否仍然有效"""

    if not cached_data or 'metadata' not in cached_data:
        return False, "缓存格式错误"

    metadata = cached_data['metadata']
    now = datetime.now()

    # 1. 检查缓存时间
    cached_at = datetime.fromisoformat(metadata['cached_at'])
    age_hours = (now - cached_at).total_seconds() / 3600

    # 2. 区分当月和历史月份
    current_cycle = now.strftime("%Y-%m")
    is_current_month = (billing_cycle == current_cycle)

    if is_current_month:
        # 当月数据：6小时内有效
        if age_hours > 6:
            return False, f"当月缓存已过期 ({age_hours:.1f}小时)"
    else:
        # 历史月份：7天内有效（已出账数据不会变化）
        if age_hours > 7 * 24:
            return False, f"历史缓存已过期 ({age_hours/24:.1f}天)"

    # 3. 快速验证：记录数检查（可选，定期抽查）
    if should_verify_record_count():
        db_count = quick_count_from_db(billing_cycle)
        cached_count = metadata.get('record_count', 0)

        # 允许5%误差（考虑到数据延迟）
        if abs(db_count - cached_count) / max(db_count, 1) > 0.05:
            return False, f"记录数不匹配 (缓存:{cached_count}, DB:{db_count})"

    # 4. 当月数据：检查是否有新账单
    if is_current_month:
        last_cached_date = metadata.get('last_bill_date')
        latest_db_date = get_latest_bill_date_from_db(billing_cycle)

        if latest_db_date and last_cached_date:
            if latest_db_date > last_cached_date:
                return False, f"有新账单数据 (缓存:{last_cached_date}, DB:{latest_db_date})"

    return True, "缓存有效"
```

---

### 方案2: 基于数据库时间戳的变更检测

#### 思路

在bill_items表添加时间戳字段，追踪数据变更：

```sql
ALTER TABLE bill_items
ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- 为账期添加索引（加速查询）
CREATE INDEX idx_billing_cycle_updated ON bill_items(billing_cycle, updated_at);
```

#### 验证逻辑

```python
def check_data_freshness(billing_cycle, cached_metadata):
    """检查数据库是否有更新"""

    # 查询该账期最新的数据更新时间
    query = f"""
        SELECT MAX(updated_at) as latest_update
        FROM bill_items
        WHERE billing_cycle = '{billing_cycle}'
    """
    result = db.query(query)

    if not result:
        return True  # 数据库无数据，缓存仍有效

    latest_db_update = result[0]['latest_update']
    cached_at = datetime.fromisoformat(cached_metadata['cached_at'])

    # 如果数据库有更新的数据，缓存失效
    if latest_db_update and latest_db_update > cached_at:
        return False

    return True
```

---

### 方案3: 轻量级健康检查（最简单）

#### 思路

每次使用缓存前，执行**快速健康检查**（不查询全量数据）：

```python
def quick_cache_health_check(billing_cycle, cached_data):
    """快速健康检查（<100ms）"""

    # 1. 检查关键字段是否存在
    required_fields = ['total_pretax', 'by_product', 'data_source']
    if not all(field in cached_data for field in required_fields):
        return False, "缓存数据不完整"

    # 2. 检查金额合理性（避免异常值）
    total = cached_data.get('total_pretax', 0)
    if total < 0:
        return False, "金额异常（负数）"

    # 3. 快速采样验证（每10次查询验证1次，避免性能影响）
    import random
    if random.random() < 0.1:  # 10%概率
        # 从数据库快速查询总额（不查明细）
        quick_query = f"""
            SELECT SUM(payment_amount) as total
            FROM bill_items
            WHERE billing_cycle = '{billing_cycle}'
            LIMIT 1
        """
        db_total = db.query(quick_query)[0]['total'] or 0

        # 允许1%误差
        if abs(db_total - total) / max(db_total, 1) > 0.01:
            return False, f"金额不匹配（缓存:{total}, DB:{db_total}）"

    return True, "健康检查通过"
```

---

## 🛠️ 推荐实现：混合方案

结合三种方案的优点，实现**分层验证策略**：

```python
class SmartCacheValidator:
    """智能缓存验证器"""

    def __init__(self):
        self.db = get_database_adapter()
        self.verification_interval = 10  # 每10次验证1次完整性
        self.check_counter = 0

    def validate(self, cached_data, billing_cycle, force_deep_check=False):
        """
        验证缓存有效性

        Args:
            cached_data: 缓存数据
            billing_cycle: 账期
            force_deep_check: 强制深度检查

        Returns:
            (is_valid, reason, should_refresh)
        """

        # L1: 基础检查（每次都做，<1ms）
        if not self._basic_check(cached_data):
            return False, "缓存格式错误", True

        # L2: 时间戳检查（每次都做，<5ms）
        valid, reason = self._timestamp_check(cached_data, billing_cycle)
        if not valid:
            return False, reason, True

        # L3: 定期深度检查（10%概率或强制，<100ms）
        self.check_counter += 1
        if force_deep_check or (self.check_counter % self.verification_interval == 0):
            valid, reason = self._deep_check(cached_data, billing_cycle)
            if not valid:
                return False, reason, True

        return True, "缓存有效", False

    def _basic_check(self, cached_data):
        """基础格式检查"""
        if not isinstance(cached_data, dict):
            return False

        required = ['data', 'metadata']
        return all(k in cached_data for k in required)

    def _timestamp_check(self, cached_data, billing_cycle):
        """时间戳检查"""
        metadata = cached_data.get('metadata', {})

        if 'cached_at' not in metadata:
            return False, "缺少缓存时间戳"

        now = datetime.now()
        cached_at = datetime.fromisoformat(metadata['cached_at'])
        age_hours = (now - cached_at).total_seconds() / 3600

        # 区分当月和历史月
        current_cycle = now.strftime("%Y-%m")
        is_current = (billing_cycle == current_cycle)

        max_age = 6 if is_current else 24 * 7

        if age_hours > max_age:
            return False, f"缓存过期（{age_hours:.1f}h > {max_age}h）"

        return True, "时间戳有效"

    def _deep_check(self, cached_data, billing_cycle):
        """深度检查（快速查询数据库验证）"""
        metadata = cached_data.get('metadata', {})

        # 快速查询总额和记录数
        query = f"""
            SELECT
                COUNT(*) as count,
                SUM(payment_amount) as total,
                MAX(billing_date) as latest_date
            FROM bill_items
            WHERE billing_cycle = '{billing_cycle}'
        """

        try:
            result = self.db.query(query)
            if not result:
                return True, "数据库无数据"

            db_data = result[0]
            db_count = db_data.get('count', 0)
            db_total = float(db_data.get('total') or 0)

            # 验证记录数
            cached_count = metadata.get('record_count', 0)
            if abs(db_count - cached_count) > max(db_count * 0.01, 10):
                return False, f"记录数不匹配（缓存:{cached_count}, DB:{db_count}）"

            # 验证金额
            cached_total = cached_data['data'].get('total_pretax', 0)
            if abs(db_total - cached_total) > max(db_total * 0.01, 0.1):
                return False, f"金额不匹配（缓存:{cached_total:.2f}, DB:{db_total:.2f}）"

            return True, "深度检查通过"

        except Exception as e:
            logger.warning(f"深度检查失败: {e}")
            return True, "深度检查异常，保留缓存"
```

---

## 📦 集成到现有代码

### 修改 _get_billing_overview_totals()

```python
def _get_billing_overview_totals(
    account_config: CloudAccount,
    billing_cycle: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """从账单概览计算总额和分类"""

    if billing_cycle is None:
        billing_cycle = _get_billing_cycle_default()

    cache_key = f"billing_overview_totals_{billing_cycle}"
    cache_manager = CacheManager(ttl_seconds=86400)
    validator = SmartCacheValidator()

    # 检查缓存
    if not force_refresh:
        cached = cache_manager.get(
            resource_type=cache_key,
            account_name=account_config.name
        )

        if cached:
            # ✅ 新增：验证缓存
            is_valid, reason, should_refresh = validator.validate(
                cached,
                billing_cycle,
                force_deep_check=False
            )

            if is_valid:
                logger.info(f"✅ 缓存有效，使用缓存数据: {billing_cycle}")
                return cached['data']
            else:
                logger.warning(f"⚠️ 缓存验证失败: {reason}，重新查询")
                # 继续往下执行，从数据库或API获取

    # 优先从本地数据库读取
    if not force_refresh:
        db_result = _get_billing_overview_from_db(account_config, billing_cycle)
        if db_result is not None:
            logger.info(f"✅ 从数据库读取: {billing_cycle}")

            # ✅ 新增：写缓存时附加元数据
            cache_data = {
                "data": db_result,
                "metadata": {
                    "cached_at": datetime.now().isoformat(),
                    "billing_cycle": billing_cycle,
                    "record_count": db_result.get('record_count', 0),
                    "last_bill_date": db_result.get('last_bill_date'),
                    "version": 1
                }
            }

            cache_manager.set(
                resource_type=cache_key,
                account_name=account_config.name,
                data=cache_data  # 存储带元数据的结构
            )
            return db_result

    # 从API查询
    logger.info(f"📡 从API查询: {billing_cycle}")
    items = _bss_query_bill_overview(account_config, billing_cycle)

    # ... 处理数据 ...

    # ✅ 新增：写缓存时附加元数据
    cache_data = {
        "data": result,
        "metadata": {
            "cached_at": datetime.now().isoformat(),
            "billing_cycle": billing_cycle,
            "record_count": len(items),
            "last_bill_date": max([item.get('BillingDate') for item in items]) if items else None,
            "version": 1
        }
    }

    cache_manager.set(
        resource_type=cache_key,
        account_name=account_config.name,
        data=cache_data
    )

    return result
```

---

## 📊 验证策略对比

| 方案 | 检查频率 | 性能影响 | 准确性 | 适用场景 |
|-----|---------|---------|--------|---------|
| **时间戳检查** | 每次 | 极低(<5ms) | 中 | 基础验证 |
| **快速采样** | 10% | 低(<100ms) | 高 | 定期抽查 |
| **数据库时间戳** | 每次 | 低(<50ms) | 高 | 需要表结构修改 |
| **完整对比** | 按需 | 高(>500ms) | 最高 | 强制刷新时 |

---

## 🎯 推荐配置

### 不同数据类型的验证策略

```python
VALIDATION_CONFIG = {
    # 当月账单（每天都在变化）
    "current_month": {
        "cache_ttl": 6 * 3600,        # 6小时
        "validation_level": "strict",  # 严格验证
        "check_frequency": 0.2,        # 20%请求深度检查
        "allow_deviation": 0.01        # 允许1%误差
    },

    # 上月账单（已出账，变化少）
    "last_month": {
        "cache_ttl": 24 * 3600,       # 24小时
        "validation_level": "normal",  # 正常验证
        "check_frequency": 0.05,       # 5%请求深度检查
        "allow_deviation": 0.001       # 允许0.1%误差
    },

    # 历史账单（不会变化）
    "historical": {
        "cache_ttl": 7 * 24 * 3600,   # 7天
        "validation_level": "light",   # 轻量验证
        "check_frequency": 0.01,       # 1%请求深度检查
        "allow_deviation": 0            # 不允许误差
    },

    # Dashboard摘要（聚合数据）
    "dashboard_summary": {
        "cache_ttl": 12 * 3600,       # 12小时
        "validation_level": "normal",
        "check_frequency": 0.1,        # 10%请求深度检查
        "allow_deviation": 0.05        # 允许5%误差
    }
}

def get_validation_config(billing_cycle):
    """根据账期获取验证配置"""
    now = datetime.now()
    current_cycle = now.strftime("%Y-%m")

    # 上月
    first_day_this_month = now.replace(day=1)
    last_month = (first_day_this_month - timedelta(days=1)).strftime("%Y-%m")

    if billing_cycle == current_cycle:
        return VALIDATION_CONFIG["current_month"]
    elif billing_cycle == last_month:
        return VALIDATION_CONFIG["last_month"]
    else:
        return VALIDATION_CONFIG["historical"]
```

---

## 🔍 监控与告警

### 缓存健康度指标

```python
class CacheHealthMonitor:
    """缓存健康度监控"""

    def __init__(self):
        self.metrics = {
            "total_checks": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "validation_failures": 0,
            "deep_checks": 0,
            "deep_check_failures": 0
        }

    def record_check(self, hit, valid, deep_check):
        """记录检查结果"""
        self.metrics["total_checks"] += 1

        if hit:
            self.metrics["cache_hits"] += 1
            if not valid:
                self.metrics["validation_failures"] += 1
        else:
            self.metrics["cache_misses"] += 1

        if deep_check:
            self.metrics["deep_checks"] += 1
            if not valid:
                self.metrics["deep_check_failures"] += 1

    def get_health_score(self):
        """计算健康度评分（0-100）"""
        if self.metrics["total_checks"] == 0:
            return 100

        hit_rate = self.metrics["cache_hits"] / self.metrics["total_checks"]

        if self.metrics["cache_hits"] > 0:
            validation_success_rate = 1 - (
                self.metrics["validation_failures"] / self.metrics["cache_hits"]
            )
        else:
            validation_success_rate = 1

        # 综合评分
        score = (hit_rate * 0.6 + validation_success_rate * 0.4) * 100
        return round(score, 2)

    def get_report(self):
        """生成健康报告"""
        total = self.metrics["total_checks"]
        if total == 0:
            return "无数据"

        return f"""
        缓存健康报告:
        - 总请求数: {total}
        - 缓存命中率: {self.metrics['cache_hits']/total*100:.1f}%
        - 验证失败率: {self.metrics['validation_failures']/total*100:.1f}%
        - 深度检查率: {self.metrics['deep_checks']/total*100:.1f}%
        - 健康度评分: {self.get_health_score()}/100
        """
```

---

## ✅ 实施步骤

### Phase 1: 基础验证（1天）

1. 实现 `SmartCacheValidator` 类
2. 修改缓存结构，添加metadata
3. 集成到 `_get_billing_overview_totals()`

### Phase 2: 差异化TTL（半天）

1. 实现 `get_validation_config()`
2. 根据账期调整缓存TTL
3. 更新 `CacheManager` 调用

### Phase 3: 监控告警（1天）

1. 实现 `CacheHealthMonitor`
2. 添加监控日志
3. 设置告警阈值

---

## 📝 总结

### 核心原则

1. **不盲目信任缓存** - 每次使用前验证
2. **分层验证** - 轻量检查 + 定期深度验证
3. **差异化策略** - 当月严格，历史宽松
4. **性能优先** - 避免每次都查数据库
5. **可监控** - 记录验证结果，持续优化

### 推荐方案

**混合验证策略**:
- ✅ 每次请求：时间戳检查（<5ms）
- ✅ 10%请求：深度检查（<100ms）
- ✅ 当月数据：6小时TTL + 严格验证
- ✅ 历史数据：7天TTL + 轻量验证

这样既保证了**数据准确性**，又不会**牺牲性能**。

---

**设计版本**: 1.0
**设计完成**: 2026-01-20
**待实施**: Phase 1

