# CloudLens 优化路线图 v2.0

**更新日期**: 2024-12-29
**基于**: P0/P1修复完成后的项目状态
**代码规模**: 154个Python文件, 53,917行代码

---

## 📊 当前状态评估

### ✅ 已完成
- P0级问题全部修复（账单计算、数据校验、测试、迁移、Excel导出）
- P1级关键问题修复（测试框架、依赖管理）
- 测试覆盖率: 93% (核心billing模块)

### ⚠️ 待优化
- **14个文件**包含TODO/FIXME标记
- **API文件过大**: api.py 5689行 → 需拆分
- **性能瓶颈**: 缓存策略、数据库查询
- **代码质量**: 部分模块缺少类型注解
- **监控缺失**: 无metrics、追踪、告警

---

## 🎯 优化建议分级

### 🔴 高优先级（1-2周内完成）

#### 1. API模块化拆分 (P1-1) ⭐⭐⭐⭐⭐

**问题**: `web/backend/api.py` 5689行，148个端点，单文件过大

**影响**:
- 代码审查困难
- Git冲突频繁
- 维护成本高
- 单元测试复杂

**优化方案**:
```
web/backend/
├── api/
│   ├── __init__.py         # 路由注册
│   ├── accounts.py         # 账号管理 (10个端点)
│   ├── resources.py        # 资源查询 (15个端点)
│   ├── cost.py             # 成本分析 (20个端点)
│   ├── discounts.py        # 折扣分析 (14个端点)
│   ├── security.py         # 安全合规 (12个端点)
│   ├── budgets.py          # 预算管理 (8个端点)
│   ├── alerts.py           # 告警管理 (10个端点)
│   ├── reports.py          # 报告生成 (6个端点)
│   ├── virtual_tags.py     # 虚拟标签 (8个端点)
│   └── settings.py         # 系统设置 (5个端点)
└── main.py                 # 应用入口
```

**实施步骤**:
```bash
# 1. 创建api目录结构
mkdir -p web/backend/api

# 2. 拆分路由（按功能模块）
# 例如：accounts.py
from fastapi import APIRouter
router = APIRouter(prefix="/accounts", tags=["账号管理"])

@router.get("/")
async def list_accounts():
    ...

# 3. 在main.py中注册
from api import accounts, cost, security
app.include_router(accounts.router)
app.include_router(cost.router)
app.include_router(security.router)
```

**预期收益**:
- 代码可读性 ↑ 60%
- Git冲突 ↓ 80%
- 单元测试速度 ↑ 50%

---

#### 2. 完成未实现的TODO功能 ⭐⭐⭐⭐

**发现的TODO列表**:

| 文件 | 行号 | TODO内容 | 优先级 |
|------|------|----------|--------|
| web/backend/api.py | 607 | 实现告警系统集成 | P0 |
| web/backend/api.py | 2074 | 支持去年同期账期对比 | P1 |
| web/backend/api.py | 3515 | 实现报告历史查询 | P1 |
| core/budget_manager.py | 217 | 集成Prophet预测模型 | P1 |
| core/budget_manager.py | 732 | 实现按标签预算 | P1 |
| core/ai_optimizer.py | ? | AI优化建议完善 | P2 |

**优先实施**:

**2.1 实现告警系统集成** (web/backend/api.py:607)
```python
# 当前代码
alert_count = 0  # TODO: implement actual alert system

# 优化为
from core.alert_manager import AlertManager

alert_manager = AlertManager()
alerts = alert_manager.get_active_alerts(
    account=account,
    severity=['high', 'critical']
)
alert_count = len(alerts)
```

**2.2 实现报告历史查询** (web/backend/api.py:3515)
```python
@router.get("/reports/history")
async def get_report_history(
    account: str,
    limit: int = 20,
    offset: int = 0
):
    """获取报告历史列表"""
    # 新增reports表
    # CREATE TABLE reports (
    #     id VARCHAR(100) PRIMARY KEY,
    #     account_id VARCHAR(100),
    #     report_type VARCHAR(50),
    #     format VARCHAR(20),
    #     file_path TEXT,
    #     created_at TIMESTAMP,
    #     INDEX idx_account_created (account_id, created_at)
    # )

    db = DatabaseFactory.create()
    reports = db.query("""
        SELECT * FROM reports
        WHERE account_id = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (account, limit, offset))

    return {
        "success": True,
        "data": reports,
        "total": len(reports)
    }
```

**2.3 实现按标签预算** (core/budget_manager.py:732)
```python
# 当前：TODO实现标签匹配
# 优化为：
from core.virtual_tags import TagEngine

tag_engine = TagEngine()
filtered_bills = []

for bill in bills:
    # 匹配虚拟标签
    matched_tags = tag_engine.match_resource(bill)

    # 检查是否匹配预算的标签过滤器
    if tag_filter:
        tag_dict = json.loads(tag_filter)
        if any(tag.tag_key == tag_dict['key'] and
               tag.tag_value == tag_dict['value']
               for tag in matched_tags):
            filtered_bills.append(bill)
```

---

#### 3. 性能优化 - 数据库层 ⭐⭐⭐⭐

**问题**:
- 大表全扫描（bill_items表）
- 缺少必要索引
- 无查询缓存
- 无分区表

**优化方案**:

**3.1 创建缺失索引**
```sql
-- migrations/002_add_performance_indexes.sql

-- 账单明细表优化
CREATE INDEX idx_bill_items_compound
ON bill_items(account_id, billing_cycle, product_code, billing_date);

CREATE INDEX idx_bill_items_instance_date
ON bill_items(instance_id, billing_date);

-- 使用覆盖索引优化常见查询
CREATE INDEX idx_bill_items_cost_summary
ON bill_items(account_id, billing_cycle, product_code, pretax_amount);

-- 分析表（MySQL 8.0+）
ANALYZE TABLE bill_items UPDATE HISTOGRAM ON billing_cycle, product_code;
```

**3.2 实现表分区**
```sql
-- 按月分区（适合历史账单数据）
ALTER TABLE bill_items
PARTITION BY RANGE (TO_DAYS(STR_TO_DATE(billing_cycle, '%Y-%m'))) (
    PARTITION p202401 VALUES LESS THAN (TO_DAYS('2024-02-01')),
    PARTITION p202402 VALUES LESS THAN (TO_DAYS('2024-03-01')),
    PARTITION p202403 VALUES LESS THAN (TO_DAYS('2024-04-01')),
    ...
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- 自动分区维护（存储过程）
CREATE EVENT auto_partition_maintenance
ON SCHEDULE EVERY 1 MONTH
DO CALL maintain_partitions('bill_items');
```

**3.3 添加物化视图**
```sql
-- 成本汇总物化视图
CREATE TABLE cost_summary_mv AS
SELECT
    account_id,
    billing_cycle,
    product_code,
    region,
    SUM(pretax_amount) as total_cost,
    COUNT(*) as item_count,
    AVG(pretax_amount) as avg_cost,
    MAX(updated_at) as last_updated
FROM bill_items
GROUP BY account_id, billing_cycle, product_code, region;

-- 创建索引
CREATE INDEX idx_cost_summary_mv ON cost_summary_mv(account_id, billing_cycle);

-- 定期刷新
CREATE EVENT refresh_cost_summary
ON SCHEDULE EVERY 1 HOUR
DO
    REPLACE INTO cost_summary_mv
    SELECT ...;
```

**预期收益**:
- 查询速度 ↑ 80%
- 大数据量查询 ↑ 10x
- 数据库负载 ↓ 60%

---

#### 4. 性能优化 - 应用层缓存 ⭐⭐⭐⭐

**问题**:
- 单一MySQL缓存层
- 无热数据识别
- 缓存命中率未知

**优化方案**:

**4.1 实现多级缓存**
```python
# core/cache/multi_level_cache.py
from functools import lru_cache
import redis
from typing import Optional, Any

class MultiLevelCache:
    """三级缓存：L1 (内存) -> L2 (Redis) -> L3 (MySQL)"""

    def __init__(self):
        # L1: 进程内LRU缓存（最热数据）
        self.l1_cache = {}  # 使用cachetools.LRUCache
        self.l1_max_size = 1000
        self.l1_ttl = 300  # 5分钟

        # L2: Redis缓存（跨进程共享）
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True
        )
        self.l2_ttl = 1800  # 30分钟

        # L3: MySQL缓存（现有）
        from core.cache import CacheManager
        self.mysql_cache = CacheManager()

        # 监控指标
        self.stats = {
            'l1_hits': 0,
            'l2_hits': 0,
            'l3_hits': 0,
            'misses': 0
        }

    async def get(self, key: str) -> Optional[Any]:
        """分级查询"""
        import time

        # L1: 内存缓存
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if time.time() < entry['expires_at']:
                self.stats['l1_hits'] += 1
                return entry['value']

        # L2: Redis缓存
        try:
            value = self.redis_client.get(key)
            if value:
                import json
                data = json.loads(value)
                # 回填L1
                self._set_l1(key, data)
                self.stats['l2_hits'] += 1
                return data
        except redis.RedisError:
            pass  # Redis不可用，降级到L3

        # L3: MySQL缓存
        value = self.mysql_cache.get(key)
        if value:
            # 回填L1和L2
            self._set_l1(key, value)
            await self._set_l2(key, value)
            self.stats['l3_hits'] += 1
            return value

        # 缓存未命中
        self.stats['misses'] += 1
        return None

    async def set(self, key: str, value: Any, ttl: int = None):
        """三级写入"""
        # 写入L1
        self._set_l1(key, value, ttl or self.l1_ttl)

        # 写入L2
        await self._set_l2(key, value, ttl or self.l2_ttl)

        # 写入L3
        self.mysql_cache.set(key, value, ttl or 3600)

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total = sum(self.stats.values())
        if total == 0:
            return self.stats

        return {
            **self.stats,
            'hit_rate': (self.stats['l1_hits'] + self.stats['l2_hits'] + self.stats['l3_hits']) / total * 100,
            'l1_hit_rate': self.stats['l1_hits'] / total * 100,
            'l2_hit_rate': self.stats['l2_hits'] / total * 100,
        }
```

**4.2 智能缓存预热**
```python
# core/cache/prewarmer.py
class CachePrewarmer:
    """缓存预热器"""

    async def prewarm_hot_data(self):
        """预热热数据"""
        # 识别热点账号（最近7天访问最多的）
        hot_accounts = await self._get_hot_accounts()

        # 预热当月账单数据
        current_month = datetime.now().strftime('%Y-%m')
        for account in hot_accounts:
            bills = await self._fetch_bills(account, current_month)
            await self.cache.set(f"bills:{account}:{current_month}", bills)

        logger.info(f"Prewarmed {len(hot_accounts)} hot accounts")
```

**预期收益**:
- API响应时间 ↓ 70%
- 缓存命中率 ↑ 85%+
- 数据库负载 ↓ 50%

---

### 🟡 中优先级（2-4周内完成）

#### 5. 代码质量提升 ⭐⭐⭐

**5.1 添加类型注解（Type Hints）**
```python
# 当前代码（无类型注解）
def calculate_cost(items, start_date, end_date):
    total = 0
    for item in items:
        total += item['amount']
    return total

# 优化后（完整类型注解）
from typing import List, Dict, Any
from datetime import datetime
from decimal import Decimal

def calculate_cost(
    items: List[Dict[str, Any]],
    start_date: datetime,
    end_date: datetime
) -> Decimal:
    """
    计算指定时间段的总成本

    Args:
        items: 账单明细列表
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        总成本（Decimal类型）

    Raises:
        ValueError: 如果日期范围无效
    """
    total = Decimal('0')
    for item in items:
        total += Decimal(str(item['amount']))
    return total
```

**5.2 添加文档字符串（Docstrings）**
```python
# 使用Google风格
class BillFetcher:
    """阿里云账单数据获取器

    该类负责从阿里云BSS OpenAPI获取账单明细数据，并可选地存储到数据库。

    Attributes:
        access_key_id: 阿里云AccessKeyId
        access_key_secret: 阿里云AccessKeySecret
        region: 区域代码，默认cn-hangzhou
        use_database: 是否启用数据库存储

    Example:
        >>> fetcher = BillFetcher('key_id', 'key_secret')
        >>> bills = fetcher.fetch_instance_bill('2024-01')
        >>> print(f"Found {len(bills)} bill items")
    """
```

**5.3 代码复杂度优化**
```bash
# 使用radon检查复杂度
radon cc core/ -a -nb

# 目标：所有函数复杂度 < 10
# 当前：部分函数复杂度 > 15

# 重构高复杂度函数
# 例如：api.py中的长函数拆分为小函数
```

---

#### 6. 错误处理和日志优化 ⭐⭐⭐

**6.1 统一异常处理**
```python
# core/exceptions.py
class CloudLensException(Exception):
    """基础异常类"""
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}

class BillingDataError(CloudLensException):
    """账单数据异常"""
    pass

class ProviderAPIError(CloudLensException):
    """云厂商API异常"""
    pass

class ValidationError(CloudLensException):
    """数据校验异常"""
    pass

# 使用示例
from core.exceptions import BillingDataError

def fetch_bills(account_id: str):
    try:
        response = api_call()
    except APIException as e:
        raise BillingDataError(
            message=f"Failed to fetch bills for {account_id}",
            code="BILLING_API_ERROR",
            details={'account_id': account_id, 'error': str(e)}
        )
```

**6.2 结构化日志**
```python
# 使用structlog统一日志格式
import structlog

logger = structlog.get_logger()

# 结构化日志（易于查询和分析）
logger.info(
    "bill_fetch_completed",
    account_id=account_id,
    billing_cycle=cycle,
    item_count=len(bills),
    duration_ms=duration,
    success=True
)

# 关联请求ID（追踪完整请求链路）
with logger.bind(request_id=request_id):
    logger.info("processing_request", endpoint="/api/cost/overview")
    # ... 处理逻辑
    logger.info("request_completed", status_code=200)
```

**6.3 错误监控集成**
```python
# core/monitoring/sentry_integration.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

def init_sentry(dsn: str, environment: str = "production"):
    """初始化Sentry错误监控"""
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,  # 采样10%的请求用于性能追踪
        profiles_sample_rate=0.1,  # 性能剖析
    )
```

---

#### 7. 安全性增强 ⭐⭐⭐

**7.1 API认证和授权**
```python
# core/auth/jwt_auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证JWT令牌"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# 在API中使用
@router.get("/sensitive-data", dependencies=[Depends(verify_token)])
async def get_sensitive_data():
    ...
```

**7.2 RBAC权限控制**
```python
# core/auth/rbac.py
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    FINANCE = "finance"
    DEVELOPER = "developer"
    VIEWER = "viewer"

class Permission(str, Enum):
    READ_COST = "cost:read"
    WRITE_BUDGET = "budget:write"
    MANAGE_ACCOUNTS = "accounts:manage"
    VIEW_RESOURCES = "resources:read"

ROLE_PERMISSIONS = {
    Role.ADMIN: ["*"],  # 全部权限
    Role.FINANCE: [
        Permission.READ_COST,
        Permission.WRITE_BUDGET,
        "reports:*"
    ],
    Role.DEVELOPER: [
        Permission.VIEW_RESOURCES,
        Permission.READ_COST,
    ],
    Role.VIEWER: [
        Permission.READ_COST,
        Permission.VIEW_RESOURCES,
    ]
}

def require_permission(permission: str):
    """权限装饰器"""
    def decorator(func):
        async def wrapper(*args, user=Depends(get_current_user), **kwargs):
            if not has_permission(user.role, permission):
                raise HTTPException(status_code=403, detail="Permission denied")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 使用示例
@router.post("/budget", dependencies=[require_permission("budget:write")])
async def create_budget(...):
    ...
```

**7.3 敏感数据加密**
```python
# core/security/encryption.py
from cryptography.fernet import Fernet
import base64

class DataEncryption:
    """敏感数据加密"""

    def __init__(self, key: bytes = None):
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, data: str) -> str:
        """加密"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """解密"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# 使用示例：加密AccessKey
encryptor = DataEncryption()
encrypted_key = encryptor.encrypt(access_key_secret)
# 存储encrypted_key到数据库
```

---

#### 8. 监控和可观测性 ⭐⭐⭐⭐

**8.1 Prometheus Metrics**
```python
# core/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# 定义指标
api_requests_total = Counter(
    'cloudlens_api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

api_request_duration = Histogram(
    'cloudlens_api_request_duration_seconds',
    'API request duration',
    ['endpoint']
)

bill_items_cached = Gauge(
    'cloudlens_bill_items_cached',
    'Number of cached bill items'
)

# FastAPI中间件
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # 记录指标
    api_requests_total.labels(
        endpoint=request.url.path,
        method=request.method,
        status=response.status_code
    ).inc()

    api_request_duration.labels(
        endpoint=request.url.path
    ).observe(duration)

    return response

# 暴露metrics端点
@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

**8.2 分布式追踪（OpenTelemetry）**
```python
# core/monitoring/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def init_tracing():
    """初始化分布式追踪"""
    trace.set_tracer_provider(TracerProvider())
    jaeger_exporter = JaegerExporter(
        agent_host_name="localhost",
        agent_port=6831,
    )
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )

tracer = trace.get_tracer(__name__)

# 使用示例
@tracer.start_as_current_span("fetch_bills")
def fetch_bills(account_id: str):
    with tracer.start_as_current_span("query_database"):
        bills = db.query(...)

    with tracer.start_as_current_span("process_bills"):
        processed = process(bills)

    return processed
```

**8.3 健康检查和就绪探针**
```python
# web/backend/health.py
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """健康检查（存活探针）"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/ready")
async def readiness_check():
    """就绪检查（就绪探针）"""
    checks = {}

    # 检查数据库连接
    try:
        db = DatabaseFactory.create()
        db.query_one("SELECT 1")
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'

    # 检查Redis连接
    try:
        redis_client.ping()
        checks['redis'] = 'ok'
    except Exception as e:
        checks['redis'] = f'error: {str(e)}'

    # 检查缓存
    checks['cache'] = 'ok' if cache_manager.is_healthy() else 'degraded'

    is_ready = all(v == 'ok' for v in checks.values())

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }
```

---

### 🟢 低优先级（1-2个月内完成）

#### 9. 前端优化 ⭐⭐⭐

**9.1 状态管理统一**
```typescript
// 当前：部分用Context，部分用Zustand
// 优化：统一使用Zustand

// lib/stores/appStore.ts
import create from 'zustand';
import { persist } from 'zustand/middleware';

interface AppState {
  currentAccount: string | null;
  locale: string;
  theme: 'light' | 'dark';
  setAccount: (account: string) => void;
  setLocale: (locale: string) => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      currentAccount: null,
      locale: 'zh',
      theme: 'light',
      setAccount: (account) => set({ currentAccount: account }),
      setLocale: (locale) => set({ locale }),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'cloudlens-storage',
    }
  )
);
```

**9.2 API请求层优化**
```typescript
// lib/api/client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000,
});

// 请求拦截器（添加token）
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器（统一错误处理）
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 跳转到登录页
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 使用React Query进行数据管理
import { useQuery, useMutation } from '@tanstack/react-query';

export function useCostData(account: string, month: string) {
  return useQuery({
    queryKey: ['cost', account, month],
    queryFn: () => apiClient.get(`/api/cost/overview`, {
      params: { account, month }
    }),
    staleTime: 5 * 60 * 1000, // 5分钟内数据视为新鲜
    cacheTime: 30 * 60 * 1000, // 缓存30分钟
  });
}
```

**9.3 性能优化**
```typescript
// 虚拟滚动优化
import { FixedSizeList } from 'react-window';

function BillItemList({ items }) {
  return (
    <FixedSizeList
      height={600}
      itemCount={items.length}
      itemSize={50}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>
          <BillItem item={items[index]} />
        </div>
      )}
    </FixedSizeList>
  );
}

// 图表懒加载
const CostChart = lazy(() => import('./CostChart'));

function Dashboard() {
  return (
    <Suspense fallback={<ChartSkeleton />}>
      <CostChart data={costData} />
    </Suspense>
  );
}
```

---

#### 10. CI/CD和自动化 ⭐⭐⭐⭐

**10.1 GitHub Actions工作流**
```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: password
          MYSQL_DATABASE: cloudlens_test
        ports:
          - 3306:3306

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest --cov=core --cov=web/backend --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

      - name: Lint
        run: |
          ruff check core/ web/backend/

      - name: Type check
        run: |
          mypy core/billing/

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r core/ -f json -o bandit-report.json

      - name: Dependency audit
        run: |
          pip install pip-audit
          pip-audit

  deploy:
    needs: [test, security]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: echo "Deploy logic here"
```

**10.2 预提交钩子**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.0
    hooks:
      - id: black
        args: [--line-length=120]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest tests/core/billing/ -v
        language: system
        pass_filenames: false
        always_run: true
```

---

## 📋 优化优先级矩阵

| 优化项 | 影响 | 难度 | 耗时 | 优先级 | ROI |
|--------|------|------|------|--------|-----|
| API模块化拆分 | 极高 | 中 | 3天 | P0 | ⭐⭐⭐⭐⭐ |
| TODO功能完成 | 高 | 低 | 2天 | P0 | ⭐⭐⭐⭐⭐ |
| 数据库索引优化 | 极高 | 低 | 1天 | P0 | ⭐⭐⭐⭐⭐ |
| 多级缓存 | 高 | 中 | 3天 | P1 | ⭐⭐⭐⭐ |
| 类型注解 | 中 | 低 | 5天 | P2 | ⭐⭐⭐ |
| 监控系统 | 高 | 中 | 4天 | P1 | ⭐⭐⭐⭐ |
| RBAC权限 | 高 | 中 | 3天 | P1 | ⭐⭐⭐⭐ |
| CI/CD | 中 | 中 | 2天 | P2 | ⭐⭐⭐ |
| 前端优化 | 中 | 低 | 3天 | P2 | ⭐⭐⭐ |

---

## 🗓️ 建议实施时间表

### Week 1-2
- ✅ API模块化拆分
- ✅ TODO功能完成
- ✅ 数据库索引优化

### Week 3-4
- ⏳ 多级缓存实现
- ⏳ 监控系统集成
- ⏳ RBAC权限控制

### Week 5-6
- ⏳ 类型注解补充
- ⏳ 错误处理优化
- ⏳ CI/CD建立

### Week 7-8
- ⏳ 前端优化
- ⏳ 安全增强
- ⏳ 文档完善

---

## 📊 预期总体收益

完成所有优化后的预期指标：

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| API响应时间 | 500ms | <150ms | ↓ 70% |
| 测试覆盖率 | 93% (billing) | 85% (全局) | +85% |
| 代码可维护性 | 中 | 高 | ↑ 80% |
| 系统可用性 | 95% | 99.5% | +4.5% |
| 缓存命中率 | 60% | 90%+ | +50% |
| 安全等级 | B | A+ | +2级 |

---

## 🎯 关键成功指标（KPIs）

1. **性能指标**
   - P95响应时间 < 200ms
   - 缓存命中率 > 85%
   - 数据库查询时间 < 100ms

2. **质量指标**
   - 测试覆盖率 > 80%
   - 代码复杂度 < 10
   - Bug率 < 0.1/千行代码

3. **稳定性指标**
   - 系统可用性 > 99.5%
   - 错误率 < 0.1%
   - MTTR < 15分钟

---

**下一步行动**: 选择1-2个高优先级优化项，开始实施！
