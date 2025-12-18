# SQLite到MySQL迁移状态

## 已修复的方法 ✅

### `discount_analyzer_advanced.py`

1. ✅ `get_quarterly_comparison()` - 季度对比分析
2. ✅ `get_yearly_comparison()` - 年度对比分析  
3. ✅ `get_optimization_suggestions()` - 优化建议生成
4. ✅ `get_product_discount_trends()` - 产品折扣趋势分析
5. ✅ `get_region_discount_ranking()` - 区域折扣排行分析
6. ✅ `get_subscription_type_comparison()` - 计费方式对比分析

## 待修复的方法 ⚠️

### `discount_analyzer_advanced.py`

以下方法仍使用 `sqlite3.connect(self.db_path)`，如果使用这些功能时遇到错误，需要按相同模式修复：

1. ⚠️ `detect_anomalies()` - 异常检测（行844）
2. ⚠️ `get_product_region_cross_analysis()` - 产品×区域交叉分析（行950）
3. ⚠️ `get_moving_average_analysis()` - 移动平均分析（行1069）
4. ⚠️ `get_cumulative_discount_analysis()` - 累计折扣分析（行1152）
5. ⚠️ `get_instance_lifecycle_analysis()` - 实例生命周期分析（行1222）

## 修复模式

所有方法都遵循以下修复模式：

### 1. 移除 sqlite3 导入和连接
```python
# 修复前
conn = sqlite3.connect(self.db_path)
cursor = conn.cursor()
```

### 2. 使用数据库抽象层
```python
# 修复后
placeholder = self._get_placeholder()
rows = self._query_db("SELECT ... WHERE account_id = ?", (account_id,))
```

### 3. 处理结果格式差异
```python
# MySQL返回字典，SQLite返回元组
for row in rows:
    if isinstance(row, dict):
        value = row['column_name']
    else:
        value = row[0]
```

### 4. 移除 finally 块中的 conn.close()
```python
# 修复前
finally:
    conn.close()

# 修复后（不需要，数据库抽象层自动管理连接）
```

## 测试

已测试通过的功能：
- ✅ 季度对比分析
- ✅ 年度对比分析
- ✅ 优化建议生成

## 注意事项

- 所有修复的方法都使用 `_query_db()` 辅助方法
- 占位符自动处理（SQLite用`?`，MySQL用`%s`）
- 结果格式兼容处理（字典 vs 元组）
- 连接自动管理，无需手动关闭
