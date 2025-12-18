# 折扣分析器MySQL迁移修复

## 问题描述
- **错误**: `expected str, bytes or os.PathLike object, not NoneType`
- **原因**: `AdvancedDiscountAnalyzer` 仍在使用 `sqlite3.connect(self.db_path)`，但使用MySQL时 `db_path` 为 `None`

## 已修复的方法 ✅

### 1. `get_quarterly_comparison()` - 季度对比分析 ✅
- 已迁移到使用数据库抽象层
- 修复了MySQL的CAST语法（`CAST(... AS UNSIGNED)` vs `CAST(... AS INT)`）
- 测试通过 ✅

### 2. `get_yearly_comparison()` - 年度对比分析 ✅
- 已迁移到使用数据库抽象层
- 测试通过 ✅

## 修复模式

所有方法都遵循以下修复模式：

1. **移除 `sqlite3.connect(self.db_path)`**
2. **使用 `self._query_db()` 方法**（已创建的辅助方法）
3. **处理占位符差异**（SQLite用`?`，MySQL用`%s`）
4. **处理结果格式差异**（SQLite返回元组，MySQL返回字典）
5. **修复SQL语法差异**（如CAST语法）

## 辅助方法

已添加以下辅助方法：

```python
def _get_placeholder(self) -> str:
    """获取SQL占位符"""
    return "?" if self.db_type == "sqlite" else "%s"

def _query_db(self, sql: str, params: Optional[Tuple] = None) -> List:
    """执行数据库查询（统一接口）"""
    placeholder = self._get_placeholder()
    sql = sql.replace("?", placeholder) if self.db_type == "mysql" else sql
    return self.db.query(sql, params)
```

## 待修复的方法（如需要）

以下方法仍使用 `sqlite3.connect(self.db_path)`，如果使用这些功能时遇到错误，需要按相同模式修复：

1. `get_product_discount_trends()` - 产品折扣趋势分析
2. `get_region_discount_ranking()` - 区域折扣排行分析
3. `get_subscription_type_comparison()` - 计费方式对比分析
4. `get_optimization_suggestions()` - 优化建议
5. `detect_anomalies()` - 异常检测
6. `get_product_region_cross_analysis()` - 产品×区域交叉分析
7. `get_moving_average_analysis()` - 移动平均分析
8. `get_cumulative_discount_analysis()` - 累计折扣分析
9. `get_instance_lifecycle_analysis()` - 实例生命周期分析

## 修复示例

修复前：
```python
conn = sqlite3.connect(self.db_path)
cursor = conn.cursor()
try:
    cursor.execute("SELECT ... WHERE account_id = ?", [account_id])
    rows = cursor.fetchall()
    # 处理结果
finally:
    conn.close()
```

修复后：
```python
try:
    rows = self._query_db("SELECT ... WHERE account_id = ?", (account_id,))
    # 处理结果（rows是字典列表，MySQL）或元组列表（SQLite）
    for row in rows:
        if isinstance(row, dict):
            value = row['column_name']
        else:
            value = row[0]
```

## 测试

```bash
# 测试季度对比
curl "http://127.0.0.1:8000/api/discounts/quarterly?account=ydzn&quarters=4"

# 测试年度对比
curl "http://127.0.0.1:8000/api/discounts/yearly?account=ydzn"
```

## 状态

- ✅ 季度对比分析：已修复并测试通过
- ✅ 年度对比分析：已修复并测试通过
- ⚠️ 其他方法：待修复（按需）
