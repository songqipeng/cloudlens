# SQLite完全迁移计划

## 当前状态

### ✅ 已完全迁移的模块
1. `core/cache.py`
2. `core/bill_storage.py`
3. `core/dashboard_manager.py`
4. `core/discount_analyzer_advanced.py`
5. `core/alert_engine.py`
6. `core/ai_optimizer.py`
7. `core/discount_analyzer_db.py`
8. `core/cost_trend_analyzer.py`
9. `web/backend/api.py`
10. `core/alert_manager.py` ✅ (刚完成)

### ⚠️ 待迁移的模块
1. `core/budget_manager.py` - 部分迁移（初始化已完成，方法待迁移）
2. `core/virtual_tags.py` - 待迁移
3. `core/cost_allocation.py` - 待迁移

## 迁移模式

所有模块都遵循相同的迁移模式：

1. **移除SQLite导入**
   ```python
   # 移除
   import sqlite3
   
   # 添加
   from core.database import DatabaseFactory, DatabaseAdapter
   import os
   ```

2. **修改__init__方法**
   ```python
   def __init__(self, db_path: Optional[str] = None, db_type: Optional[str] = None):
       self.db_type = db_type or os.getenv("DB_TYPE", "mysql").lower()
       
       if self.db_type == "mysql":
           self.db = DatabaseFactory.create_adapter("mysql")
           self.db_path = None
       else:
           # SQLite逻辑
           self.db = DatabaseFactory.create_adapter("sqlite", db_path=db_path)
   ```

3. **添加占位符方法**
   ```python
   def _get_placeholder(self) -> str:
       return "%s" if self.db_type == "mysql" else "?"
   ```

4. **替换所有数据库操作**
   - `conn = sqlite3.connect(...)` → 使用 `self.db`
   - `cursor.execute(...)` → `self.db.execute(...)` 或 `self.db.query(...)`
   - `cursor.fetchone()` → 从 `self.db.query()` 返回的列表中取第一个
   - `cursor.fetchall()` → 使用 `self.db.query()` 的返回值
   - `conn.commit()` → 移除（`execute` 自动提交）
   - `conn.close()` → 移除（连接池管理）
   - `conn.rollback()` → 移除或使用 `self.db.execute()` 的异常处理

5. **处理结果格式差异**
   - MySQL返回字典，SQLite返回元组
   - 使用 `isinstance(row, dict)` 判断并处理

## 下一步

继续完成剩余三个模块的迁移。
