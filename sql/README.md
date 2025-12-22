# MySQL 数据库表结构

## 📋 概述

本文档描述了 CloudLens 项目的 MySQL 数据库表结构。所有表都使用 `utf8mb4` 字符集和 `utf8mb4_unicode_ci` 排序规则。

## 📊 表列表

### 核心表（13个）

1. **resource_cache** - 资源查询缓存表
2. **bill_items** - 账单明细表
3. **dashboards** - 仪表盘表
4. **budgets** - 预算表
5. **budget_records** - 预算执行记录表
6. **budget_alerts** - 预算告警记录表
7. **alert_rules** - 告警规则表
8. **alerts** - 告警记录表
9. **virtual_tags** - 虚拟标签表
10. **tag_rules** - 标签规则表
11. **tag_matches** - 标签匹配缓存表
12. **resource_monitoring_data** - 资源监控数据表
13. **cost_allocation** - 成本分配表

## 🚀 使用方法

### 创建表结构

```bash
# 使用cloudlens用户执行
mysql -u cloudlens -pcloudlens123 cloudlens < sql/init_mysql_schema.sql
```

### 验证表结构

```bash
# 运行验证脚本
python3 sql/verify_schema.py
```

### 查看所有表

```bash
mysql -u cloudlens -pcloudlens123 cloudlens -e "SHOW TABLES;"
```

### 查看表结构

```bash
# 查看特定表的结构
mysql -u cloudlens -pcloudlens123 cloudlens -e "DESCRIBE resource_cache;"
```

## 📝 表结构详情

### 1. resource_cache - 资源查询缓存表

**用途**: 存储资源查询的缓存数据，支持TTL过期机制

**关键字段**:
- `cache_key` (VARCHAR(255), PRIMARY KEY) - 缓存键（MD5哈希）
- `resource_type` (VARCHAR(50)) - 资源类型
- `account_name` (VARCHAR(100)) - 账号名称
- `data` (JSON) - 缓存数据
- `expires_at` (TIMESTAMP) - 过期时间

**索引**:
- `idx_resource_type_account` - 资源类型和账号索引
- `idx_expires_at` - 过期时间索引

### 2. bill_items - 账单明细表

**用途**: 存储详细的账单数据

**关键字段**:
- `id` (BIGINT, AUTO_INCREMENT, PRIMARY KEY) - 自增ID
- `account_id` (VARCHAR(100)) - 账号ID
- `billing_cycle` (VARCHAR(20)) - 账期（YYYY-MM）
- `instance_id` (VARCHAR(200)) - 实例ID
- `pretax_amount` (DECIMAL(15,4)) - 税前金额
- `payment_amount` (DECIMAL(15,4)) - 实付金额
- `raw_data` (JSON) - 原始数据

**索引**:
- `idx_account_cycle` - 账号和账期索引
- `idx_billing_date` - 账单日期索引
- `idx_product_code` - 产品代码索引
- `idx_instance_id` - 实例ID索引

### 3. dashboards - 仪表盘表

**用途**: 存储用户自定义仪表盘配置

**关键字段**:
- `id` (VARCHAR(100), PRIMARY KEY) - 仪表盘ID（UUID）
- `name` (VARCHAR(200)) - 仪表盘名称
- `widgets` (JSON) - 组件配置
- `account_id` (VARCHAR(100)) - 账号ID
- `is_shared` (TINYINT(1)) - 是否共享

### 4. budgets - 预算表

**用途**: 存储预算配置

**关键字段**:
- `id` (VARCHAR(100), PRIMARY KEY) - 预算ID
- `name` (VARCHAR(200)) - 预算名称
- `amount` (DECIMAL(15,4)) - 预算金额
- `period` (VARCHAR(50)) - 周期（monthly, quarterly, yearly）
- `start_date` (DATE) - 开始日期
- `end_date` (DATE) - 结束日期

### 5. resource_monitoring_data - 资源监控数据表

**用途**: 统一存储所有资源的监控数据

**关键字段**:
- `id` (BIGINT, AUTO_INCREMENT, PRIMARY KEY) - 自增ID
- `resource_type` (VARCHAR(50)) - 资源类型
- `resource_id` (VARCHAR(200)) - 资源ID
- `account_name` (VARCHAR(100)) - 账号名称
- `metric_name` (VARCHAR(100)) - 指标名称
- `metric_value` (DECIMAL(15,4)) - 指标值
- `timestamp` (TIMESTAMP) - 时间戳

**索引**:
- `idx_resource` - 资源索引
- `idx_account` - 账号索引
- `idx_timestamp` - 时间戳索引
- `idx_metric` - 指标和时间戳索引

## 🔧 维护命令

### 查看表大小

```sql
SELECT 
    table_name,
    table_rows,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.tables 
WHERE table_schema = 'cloudlens'
ORDER BY size_mb DESC;
```

### 查看表索引

```sql
SHOW INDEX FROM resource_cache;
```

### 优化表

```sql
OPTIMIZE TABLE resource_cache;
```

### 清理过期缓存

```sql
DELETE FROM resource_cache WHERE expires_at < NOW();
```

## 📌 注意事项

1. **字符集**: 所有表使用 `utf8mb4` 字符集，支持完整的UTF-8字符（包括emoji）
2. **存储引擎**: 使用 `InnoDB` 引擎，支持事务和外键约束
3. **JSON字段**: MySQL 5.7+ 支持JSON类型，用于存储灵活的配置数据
4. **外键约束**: 部分表使用外键约束保证数据完整性
5. **索引优化**: 根据查询模式创建了合适的索引

## 🔄 迁移说明

从SQLite迁移到MySQL时，需要注意：

1. **数据类型映射**:
   - SQLite `TEXT` → MySQL `VARCHAR` 或 `TEXT`
   - SQLite `INTEGER` → MySQL `INT` 或 `BIGINT`
   - SQLite `REAL` → MySQL `DECIMAL`
   - SQLite `BLOB` → MySQL `JSON`（如果存储JSON数据）

2. **保留关键字**: MySQL的保留关键字（如 `usage`）需要用反引号包裹

3. **外键约束**: MySQL支持外键约束，SQLite需要手动维护

4. **字符集**: MySQL需要明确指定字符集和排序规则

## 📚 相关文件

- `sql/init_mysql_schema.sql` - 表结构创建脚本
- `sql/verify_schema.py` - 表结构验证脚本
- `K8S_PREPARATION_IMPROVEMENTS.md` - 数据库迁移方案文档



