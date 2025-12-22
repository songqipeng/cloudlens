# K8s 部署前技术架构改进方案

## 📋 当前技术栈分析

### 后端技术栈
- **框架**: FastAPI (Python 3.8+)
- **数据库**: MySQL（主数据库，支持SQLite兼容）
- **缓存**: MySQL缓存表
- **云SDK**: 阿里云SDK、腾讯云SDK
- **其他**: pandas, openpyxl, keyring

### 前端技术栈
- **框架**: Next.js (React + TypeScript)
- **构建工具**: npm/webpack
- **UI组件**: 自定义组件库

### 当前数据库使用情况
项目使用MySQL作为主数据库，通过数据库抽象层支持SQLite兼容：

1. **resource_cache** - 资源查询缓存（24小时TTL）
2. **bills.db** - 账单明细数据
3. **dashboards.db** - 仪表盘配置
4. **budgets.db** - 预算管理数据
5. **cost_allocation.db** - 成本分配数据
6. **alerts.db** - 告警规则和记录
7. **virtual_tags.db** - 虚拟标签数据
8. **各种监控数据.db** - 资源监控数据（rds_monitoring_data.db等）

---

## 🎯 核心改进建议

### 1. 数据库迁移到MySQL（高优先级）

#### 1.1 为什么选择MySQL
- ✅ **高可用**: 支持主从复制、读写分离
- ✅ **多副本支持**: K8s中可部署多个Pod
- ✅ **性能**: 比SQLite更适合生产环境
- ✅ **生态**: 丰富的工具和监控方案
- ✅ **事务支持**: 更好的数据一致性
- ⚠️ **注意**: 也可以考虑PostgreSQL（功能更强大，但MySQL更常见）

#### 1.2 迁移策略

**阶段1: 创建统一数据库抽象层**
```python
# core/database.py - 新的数据库抽象层
from abc import ABC, abstractmethod
from typing import Optional
import mysql.connector
from mysql.connector import pooling

class DatabaseAdapter(ABC):
    """数据库适配器抽象基类"""
    
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def execute(self, sql: str, params: tuple = None):
        pass
    
    @abstractmethod
    def query(self, sql: str, params: tuple = None) -> List[Dict]:
        pass

class MySQLAdapter(DatabaseAdapter):
    """MySQL适配器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="cloudlens_pool",
            pool_size=10,
            pool_reset_session=True,
            **config
        )
    
    def connect(self):
        return self.pool.get_connection()
    
    def execute(self, sql: str, params: tuple = None):
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params or ())
            conn.commit()
            return cursor
        finally:
            cursor.close()
            conn.close()
    
    def query(self, sql: str, params: tuple = None) -> List[Dict]:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

class SQLiteAdapter(DatabaseAdapter):
    """SQLite适配器（用于本地开发/兼容）"""
    # 保持现有SQLite实现
    pass

# 数据库工厂
class DatabaseFactory:
    @staticmethod
    def create_adapter(db_type: str = None) -> DatabaseAdapter:
        """根据环境变量或配置创建适配器"""
        db_type = db_type or os.getenv("DB_TYPE", "sqlite")
        
        if db_type == "mysql":
            return MySQLAdapter({
                "host": os.getenv("MYSQL_HOST", "localhost"),
                "port": int(os.getenv("MYSQL_PORT", 3306)),
                "user": os.getenv("MYSQL_USER", "cloudlens"),
                "password": os.getenv("MYSQL_PASSWORD"),
                "database": os.getenv("MYSQL_DATABASE", "cloudlens"),
                "charset": "utf8mb4",
                "collation": "utf8mb4_unicode_ci"
            })
        else:
            return SQLiteAdapter()
```

**阶段2: 统一数据库Schema设计**
```sql
-- 统一数据库设计（MySQL）
CREATE DATABASE cloudlens CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 1. 缓存表
CREATE TABLE resource_cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    resource_type VARCHAR(50) NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    region VARCHAR(50),
    data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    INDEX idx_resource_type_account (resource_type, account_name),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 账单表
CREATE TABLE bills (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_name VARCHAR(100) NOT NULL,
    billing_cycle VARCHAR(20) NOT NULL,
    product_code VARCHAR(50),
    product_name VARCHAR(200),
    resource_id VARCHAR(200),
    cost DECIMAL(15, 4) NOT NULL,
    currency VARCHAR(10) DEFAULT 'CNY',
    region VARCHAR(50),
    tags JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_account_cycle (account_name, billing_cycle),
    INDEX idx_resource_id (resource_id),
    INDEX idx_product_code (product_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 仪表盘表
CREATE TABLE dashboards (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    layout VARCHAR(50) DEFAULT 'grid',
    widgets JSON NOT NULL,
    account_id VARCHAR(100),
    is_shared TINYINT(1) DEFAULT 0,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_account_id (account_id),
    INDEX idx_shared (is_shared)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 预算表
CREATE TABLE budgets (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    amount DECIMAL(15, 4) NOT NULL,
    period VARCHAR(50) NOT NULL,
    type VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    tag_filter JSON,
    service_filter JSON,
    alerts JSON,
    account_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_account_id (account_id),
    INDEX idx_period (period, start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 告警表
CREATE TABLE alerts (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL,
    condition_config JSON NOT NULL,
    notification_config JSON,
    enabled TINYINT(1) DEFAULT 1,
    account_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_account_id (account_id),
    INDEX idx_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. 虚拟标签表
CREATE TABLE virtual_tags (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    rules JSON NOT NULL,
    account_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_account_id (account_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. 资源监控数据表（统一设计）
CREATE TABLE resource_monitoring_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(200) NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    region VARCHAR(50),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15, 4),
    timestamp TIMESTAMP NOT NULL,
    metadata JSON,
    INDEX idx_resource (resource_type, resource_id),
    INDEX idx_account (account_name),
    INDEX idx_timestamp (timestamp),
    INDEX idx_metric (metric_name, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**阶段3: 数据迁移脚本**
```python
# scripts/migrate_to_mysql.py
"""
SQLite到MySQL数据迁移脚本
"""
import sqlite3
import mysql.connector
from pathlib import Path
import json
from datetime import datetime

def migrate_cache_db():
    """迁移缓存数据库"""
    # SQLite读取
    sqlite_conn = sqlite3.connect(Path.home() / ".cloudlens" / "cache.db")
    sqlite_cursor = sqlite_conn.cursor()
    
    # MySQL写入
    mysql_conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )
    mysql_cursor = mysql_conn.cursor()
    
    # 迁移逻辑
    sqlite_cursor.execute("SELECT * FROM resource_cache")
    for row in sqlite_cursor.fetchall():
        mysql_cursor.execute("""
            INSERT INTO resource_cache 
            (cache_key, resource_type, account_name, region, data, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (row[0], row[1], row[2], row[3], json.dumps(row[4]), row[6]))
    
    mysql_conn.commit()
    # ... 其他表迁移
```

#### 1.3 代码改造清单

需要修改的模块：
- ✅ `core/cache.py` - 使用新的DatabaseAdapter
- ✅ `core/bill_storage.py` - 迁移到MySQL
- ✅ `core/dashboard_manager.py` - 迁移到MySQL
- ✅ `core/budget_manager.py` - 迁移到MySQL
- ✅ `core/alert_manager.py` - 迁移到MySQL
- ✅ `core/virtual_tags.py` - 迁移到MySQL
- ✅ `core/db_manager.py` - 改为使用DatabaseAdapter
- ✅ `resource_modules/*.py` - 所有使用SQLite的分析器

---

### 2. 配置管理改进

#### 2.1 环境变量配置
```python
# core/config.py - 改进配置管理
import os
from typing import Optional
from pydantic import BaseSettings

class AppConfig(BaseSettings):
    """应用配置（从环境变量读取）"""
    
    # 数据库配置
    db_type: str = os.getenv("DB_TYPE", "sqlite")  # sqlite | mysql
    mysql_host: Optional[str] = os.getenv("MYSQL_HOST")
    mysql_port: int = int(os.getenv("MYSQL_PORT", 3306))
    mysql_user: Optional[str] = os.getenv("MYSQL_USER")
    mysql_password: Optional[str] = os.getenv("MYSQL_PASSWORD")
    mysql_database: Optional[str] = os.getenv("MYSQL_DATABASE", "cloudlens")
    
    # 缓存配置
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", 86400))
    
    # OpenTelemetry配置
    otel_service_name: str = os.getenv("OTEL_SERVICE_NAME", "cloudlens-backend")
    otel_exporter_endpoint: Optional[str] = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    # 日志配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

#### 2.2 K8s ConfigMap和Secret
```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cloudlens-config
  namespace: cloudlens
data:
  DB_TYPE: "mysql"
  MYSQL_HOST: "mysql-service"
  MYSQL_PORT: "3306"
  MYSQL_DATABASE: "cloudlens"
  CACHE_TTL_SECONDS: "86400"
  LOG_LEVEL: "INFO"
  OTEL_SERVICE_NAME: "cloudlens-backend"

---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: cloudlens-secrets
  namespace: cloudlens
type: Opaque
stringData:
  MYSQL_USER: "cloudlens"
  MYSQL_PASSWORD: "your-secure-password"
  # 云账号凭证通过其他方式管理（如Vault）
```

---

### 3. 日志和监控改进

#### 3.1 结构化日志
```python
# utils/logger.py - 改进日志
import structlog
import logging
from opentelemetry import trace

def get_logger(name: str):
    """获取结构化日志记录器"""
    logger = structlog.get_logger(name)
    
    # 集成OpenTelemetry Trace ID
    tracer = trace.get_tracer(__name__)
    span = trace.get_current_span()
    if span:
        trace_id = format(span.get_span_context().trace_id, '032x')
        logger = logger.bind(trace_id=trace_id)
    
    return logger

# 使用示例
logger = get_logger(__name__)
logger.info("Processing VPC", 
            vpc_id=vpc_id, 
            account=account_name,
            region=region)
```

#### 3.2 OpenTelemetry集成
```python
# web/backend/main.py - OpenTelemetry集成
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.mysql import MySQLInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# 初始化Tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer_provider().get_tracer(__name__)

# 配置OTLP导出器
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"),
    insecure=True
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# 自动instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# 自动instrument MySQL
MySQLInstrumentor().instrument()
```

---

### 4. 依赖管理改进

#### 4.1 requirements.txt 更新
```txt
# 数据库
mysql-connector-python>=8.0.33
# 或使用 pymysql（更轻量）
# PyMySQL>=1.1.0

# OpenTelemetry
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-instrumentation-fastapi>=0.42b0
opentelemetry-instrumentation-mysql>=0.42b0
opentelemetry-instrumentation-requests>=0.42b0
opentelemetry-exporter-otlp-proto-grpc>=1.20.0

# 结构化日志
structlog>=23.1.0

# 其他现有依赖保持不变
```

---

### 5. 容器化准备

#### 5.1 Dockerfile优化
```dockerfile
# web/backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（包括MySQL客户端库）
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt web/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 设置环境变量
ENV PYTHONPATH=/app
ENV DB_TYPE=mysql

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

EXPOSE 8000

CMD ["uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 6. 数据库连接池优化

```python
# core/database.py - 连接池配置
import mysql.connector
from mysql.connector import pooling

class MySQLConnectionPool:
    """MySQL连接池管理器"""
    
    def __init__(self, config: dict):
        self.pool = pooling.MySQLConnectionPool(
            pool_name="cloudlens_pool",
            pool_size=10,  # 连接池大小
            pool_reset_session=True,
            host=config.get("host"),
            port=config.get("port", 3306),
            user=config.get("user"),
            password=config.get("password"),
            database=config.get("database"),
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False,
            # 连接超时
            connection_timeout=10,
            # 连接重试
            failover=[
                {
                    "host": config.get("host"),
                    "port": config.get("port", 3306),
                }
            ]
        )
    
    def get_connection(self):
        """从连接池获取连接"""
        return self.pool.get_connection()
```

---

## 📊 改进优先级

### 高优先级（K8s部署前必须完成）
1. ✅ **数据库迁移到MySQL** - 核心改进
2. ✅ **统一数据库抽象层** - 支持SQLite和MySQL
3. ✅ **配置管理改进** - 使用环境变量和ConfigMap
4. ✅ **依赖更新** - 添加MySQL和OpenTelemetry依赖

### 中优先级（建议完成）
5. ⚠️ **结构化日志** - 更好的日志管理
6. ⚠️ **OpenTelemetry集成** - 可观测性
7. ⚠️ **连接池优化** - 性能提升

### 低优先级（可以后续完成）
8. 📝 **数据库迁移脚本** - 自动化迁移
9. 📝 **监控仪表盘** - Grafana配置
10. 📝 **性能测试** - 压力测试

---

## 🚀 实施计划

### 第1周：数据库迁移
- [ ] 创建DatabaseAdapter抽象层
- [ ] 设计MySQL Schema
- [ ] 实现MySQLAdapter
- [ ] 更新core模块使用新适配器
- [ ] 本地测试

### 第2周：配置和依赖
- [ ] 更新requirements.txt
- [ ] 改进配置管理
- [ ] 创建K8s ConfigMap和Secret
- [ ] 更新Dockerfile

### 第3周：集成和测试
- [ ] OpenTelemetry集成
- [ ] 结构化日志
- [ ] 端到端测试
- [ ] 性能测试

### 第4周：部署准备
- [ ] 数据迁移脚本
- [ ] K8s清单文件
- [ ] 文档更新
- [ ] 生产环境验证

---

## ⚠️ 注意事项

### MySQL vs PostgreSQL
- **MySQL**: 更常见，生态成熟，适合大多数场景
- **PostgreSQL**: 功能更强大，JSON支持更好，但学习曲线稍高
- **建议**: 如果团队熟悉MySQL，选择MySQL；如果需要更强大的功能，选择PostgreSQL

### 数据迁移风险
- 备份所有SQLite数据库
- 在测试环境先验证
- 准备回滚方案
- 考虑双写过渡期（同时写入SQLite和MySQL）

### 性能考虑
- 使用连接池
- 添加适当的索引
- 考虑读写分离（如果负载高）
- 监控慢查询

---

## 📚 参考资料

- [MySQL官方文档](https://dev.mysql.com/doc/)
- [mysql-connector-python文档](https://dev.mysql.com/doc/connector-python/en/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [FastAPI最佳实践](https://fastapi.tiangolo.com/deployment/)


