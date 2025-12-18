# 数据库迁移状态

## ✅ 已完成的工作

### 1. 数据库抽象层 ✅
- **文件**: `core/database.py`
- **功能**: 
  - `DatabaseAdapter` 抽象基类
  - `SQLiteAdapter` - SQLite适配器实现
  - `MySQLAdapter` - MySQL适配器实现（支持连接池）
  - `DatabaseFactory` - 数据库工厂类
- **特性**:
  - 统一的数据库操作接口
  - 自动处理SQL语法差异（? vs %s）
  - 支持事务操作
  - 支持连接池（MySQL）

### 2. 缓存管理器迁移 ✅
- **文件**: `core/cache.py`
- **状态**: 已更新为使用数据库抽象层
- **功能**:
  - 支持SQLite和MySQL
  - 自动根据环境变量选择数据库类型
  - 保持向后兼容

### 3. 数据库表结构 ✅
- **文件**: `sql/init_mysql_schema.sql`
- **状态**: 已创建13个表
- **表列表**:
  1. resource_cache - 资源查询缓存
  2. bill_items - 账单明细
  3. dashboards - 仪表盘
  4. budgets - 预算
  5. budget_records - 预算执行记录
  6. budget_alerts - 预算告警
  7. alert_rules - 告警规则
  8. alerts - 告警记录
  9. virtual_tags - 虚拟标签
  10. tag_rules - 标签规则
  11. tag_matches - 标签匹配缓存
  12. resource_monitoring_data - 资源监控数据
  13. cost_allocation - 成本分配

### 4. 数据迁移脚本 ✅
- **文件**: `scripts/migrate_sqlite_to_mysql.py`
- **功能**:
  - 迁移缓存数据（resource_cache）
  - 迁移账单数据（bill_items）
  - 迁移仪表盘数据（dashboards）
  - 支持批量插入
  - 错误处理和进度显示

### 5. 测试脚本 ✅
- **文件**: `test_database_adapter.py`
- **状态**: 所有测试通过（4/4）
- **测试内容**:
  - SQLite适配器测试
  - MySQL适配器测试
  - SQLite缓存管理器测试
  - MySQL缓存管理器测试

## 📋 待完成的工作

### 1. 更新其他核心模块 ⏳
需要更新的模块：
- [ ] `core/bill_storage.py` - 账单存储
- [ ] `core/dashboard_manager.py` - 仪表盘管理
- [ ] `core/budget_manager.py` - 预算管理
- [ ] `core/alert_manager.py` - 告警管理
- [ ] `core/virtual_tags.py` - 虚拟标签
- [ ] `core/db_manager.py` - 数据库管理器（资源监控）

### 2. 配置管理 ⏳
- [ ] 更新配置管理支持数据库类型选择
- [ ] 添加环境变量配置文档

## 🚀 使用方法

### 切换到MySQL

#### 方法1: 使用环境变量
```bash
export DB_TYPE=mysql
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=cloudlens
export MYSQL_PASSWORD=cloudlens123
export MYSQL_DATABASE=cloudlens
```

#### 方法2: 在代码中指定
```python
from core.cache import CacheManager

# 使用MySQL
cache = CacheManager(ttl_seconds=86400, db_type="mysql")
```

### 迁移数据

```bash
# 运行迁移脚本
python3 scripts/migrate_sqlite_to_mysql.py

# 或指定参数
python3 scripts/migrate_sqlite_to_mysql.py \
    --host localhost \
    --user cloudlens \
    --password cloudlens123 \
    --database cloudlens
```

### 测试

```bash
# 运行测试脚本
python3 test_database_adapter.py
```

## 📝 代码示例

### 使用数据库适配器

```python
from core.database import DatabaseFactory

# 创建SQLite适配器
sqlite_db = DatabaseFactory.create_adapter("sqlite", db_path="data.db")

# 创建MySQL适配器
mysql_db = DatabaseFactory.create_adapter("mysql", 
                                          host="localhost",
                                          user="cloudlens",
                                          password="cloudlens123",
                                          database="cloudlens")

# 使用适配器
results = mysql_db.query("SELECT * FROM resource_cache WHERE resource_type = %s", ("ecs",))
```

### 使用缓存管理器

```python
from core.cache import CacheManager

# 使用MySQL（从环境变量读取配置）
cache = CacheManager(ttl_seconds=86400, db_type="mysql")

# 设置缓存
cache.set("ecs", "account1", [{"id": "1", "name": "instance1"}])

# 获取缓存
data = cache.get("ecs", "account1")

# 清除缓存
cache.clear("ecs", "account1")
```

## ⚠️ 注意事项

1. **密码安全**: 生产环境请使用环境变量或密钥管理服务，不要硬编码密码
2. **数据备份**: 迁移前请备份SQLite数据库
3. **测试环境**: 建议先在测试环境验证迁移
4. **向后兼容**: 当前代码保持向后兼容，默认使用SQLite

## 🔄 迁移步骤

1. **准备MySQL数据库**
   ```bash
   # 确保MySQL已安装并运行
   brew services start mysql
   
   # 创建数据库和用户（如果还没有）
   mysql -u root -e "CREATE DATABASE IF NOT EXISTS cloudlens;"
   mysql -u root -e "CREATE USER IF NOT EXISTS 'cloudlens'@'localhost' IDENTIFIED BY 'cloudlens123';"
   mysql -u root -e "GRANT ALL PRIVILEGES ON cloudlens.* TO 'cloudlens'@'localhost';"
   ```

2. **创建表结构**
   ```bash
   mysql -u cloudlens -pcloudlens123 cloudlens < sql/init_mysql_schema.sql
   ```

3. **迁移数据**
   ```bash
   python3 scripts/migrate_sqlite_to_mysql.py
   ```

4. **测试**
   ```bash
   python3 test_database_adapter.py
   ```

5. **切换到MySQL**
   ```bash
   export DB_TYPE=mysql
   # 然后运行你的应用
   ```

## 📚 相关文件

- `core/database.py` - 数据库抽象层
- `core/cache.py` - 缓存管理器（已迁移）
- `sql/init_mysql_schema.sql` - MySQL表结构
- `scripts/migrate_sqlite_to_mysql.py` - 数据迁移脚本
- `test_database_adapter.py` - 测试脚本
- `K8S_PREPARATION_IMPROVEMENTS.md` - 完整改进方案
