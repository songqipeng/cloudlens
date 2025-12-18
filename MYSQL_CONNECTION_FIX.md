# MySQL连接数过多问题修复

## 问题描述
- **错误**: `1040 (08004): Too many connections`
- **原因**: MySQL连接池连接泄漏，连接没有正确归还
- **当前状态**: 81个连接（最大151个）

## 已修复的问题

### 1. 连接泄漏修复 ✅
**问题**: `query()` 和 `execute()` 方法从连接池获取连接后，没有归还连接

**修复**:
- 修改 `core/database.py` 中的 `MySQLAdapter.query()` 和 `MySQLAdapter.execute()` 方法
- 每次操作完成后立即调用 `conn.close()` 归还连接到连接池
- 不再使用 `self.conn` 缓存连接，每次操作都获取新连接

**修改前**:
```python
def query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict]:
    conn = self.connect()  # 使用缓存的连接
    cursor = conn.cursor(dictionary=True)
    try:
        # ... 执行查询
        return cursor.fetchall()
    finally:
        cursor.close()  # 只关闭cursor，连接未归还
```

**修改后**:
```python
def query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict]:
    conn = self.pool.get_connection()  # 直接从连接池获取
    cursor = conn.cursor(dictionary=True)
    try:
        # ... 执行查询
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()  # 归还连接到连接池
```

### 2. 连接池大小优化 ✅
- **默认连接池大小**: 从 10 增加到 **20**
- **环境变量**: `MYSQL_POOL_SIZE` (默认20)

### 3. MySQL配置优化（需要手动执行）

由于需要root权限，请手动执行以下SQL：

```sql
-- 增加最大连接数
SET GLOBAL max_connections = 500;

-- 设置空闲连接超时（5分钟）
SET GLOBAL wait_timeout = 300;
SET GLOBAL interactive_timeout = 300;
```

或使用脚本：
```bash
# 设置root密码环境变量
export MYSQL_ROOT_PASSWORD=your_root_password

# 执行修复脚本
./scripts/fix_mysql_connections.sh
```

## 验证修复

### 1. 重启后端服务
```bash
cd /Users/mac/aliyunidle
python3 -m uvicorn web.backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. 检查连接数
```bash
mysql -u cloudlens -pcloudlens123 -e "SHOW STATUS LIKE 'Threads_connected';"
```

### 3. 测试年度对比分析
访问前端页面，测试年度对比分析功能是否正常。

## 预期效果

- ✅ 连接正确归还到连接池
- ✅ 连接数保持在合理范围（< 50）
- ✅ 年度对比分析正常工作
- ✅ 不再出现 "Too many connections" 错误

## 注意事项

1. **连接池大小**: 如果并发请求很多，可以进一步增加 `MYSQL_POOL_SIZE`
2. **MySQL配置**: 修改 `max_connections` 需要重启MySQL服务才能永久生效
3. **监控**: 建议定期检查连接数，确保没有新的连接泄漏

## 永久配置MySQL（可选）

编辑MySQL配置文件（macOS Homebrew安装）:
```bash
# 编辑配置文件
vim /opt/homebrew/etc/my.cnf

# 添加以下配置
[mysqld]
max_connections = 500
wait_timeout = 300
interactive_timeout = 300

# 重启MySQL
brew services restart mysql
```
