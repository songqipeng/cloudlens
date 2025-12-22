# Kubernetes 部署实施细节

## 📋 当前系统分析

### 数据存储现状

#### MySQL 数据库
项目使用MySQL作为主数据库，所有数据存储在统一的MySQL实例中：

1. **resource_cache** - 资源查询缓存
2. **bill_items** - 账单明细数据
3. **dashboards** - 仪表盘配置
4. **budgets** - 预算管理数据
5. **budget_records** - 预算执行记录
6. **budget_alerts** - 预算告警
7. **alert_rules** - 告警规则
8. **alerts** - 告警记录
9. **virtual_tags** - 虚拟标签数据
10. **cost_allocation** - 成本分配数据
11. 等13+个表

#### 配置文件
- **config.json** - 账号配置（存储在 `~/.cloudlens/config.json`）
- **credentials** - 凭证文件（可选）
- **thresholds.yaml** - 阈值配置

### 关键挑战

1. **SQLite 在 K8s 中的限制**
   - SQLite 不支持多进程并发写入
   - 多副本部署时会有数据一致性问题
   - 需要持久化存储（PVC）

2. **配置管理**
   - 敏感信息（AccessKey）需要安全存储
   - 配置文件需要版本管理

3. **日志和监控**
   - 当前使用标准 logging
   - 需要集成 OpenTelemetry

---

## 🎯 推荐方案

### 方案A: 渐进式迁移（推荐）

#### 阶段1: 保持 SQLite，单副本部署
- **优点**: 快速部署，无需数据库迁移
- **缺点**: 不支持高可用
- **适用**: 小规模部署、测试环境

#### 阶段2: 迁移到 PostgreSQL
- **优点**: 支持高可用、多副本、更好的性能
- **缺点**: 需要数据迁移、增加运维复杂度
- **适用**: 生产环境、大规模部署

### 方案B: 直接迁移到 PostgreSQL（推荐生产环境）

#### 优势
- 支持多副本高可用
- 更好的并发性能
- 支持事务和复杂查询
- 更好的备份和恢复

#### 迁移步骤
1. 创建 PostgreSQL 数据库
2. 设计统一数据库 schema
3. 数据迁移脚本
4. 更新代码使用 PostgreSQL
5. 验证数据完整性

---

## 🔧 OpenTelemetry 集成详细设计

### 后端集成（FastAPI）

#### 1. 依赖安装
```python
# web/backend/requirements.txt 需要添加
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-instrumentation-fastapi>=0.42b0
opentelemetry-instrumentation-sqlite3>=0.42b0
opentelemetry-instrumentation-requests>=0.42b0
opentelemetry-exporter-otlp-proto-grpc>=1.20.0
opentelemetry-exporter-otlp-proto-http>=1.20.0
```

#### 2. 初始化代码（在 main.py 中）
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource

# 配置资源属性
resource = Resource.create({
    "service.name": "cloudlens-backend",
    "service.version": "2.1.0",
    "deployment.environment": os.getenv("ENVIRONMENT", "production"),
})

# 配置 Tracer
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# 配置 OTLP Exporter
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"),
    insecure=True,
)

# 添加 Span Processor
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# 自动注入 FastAPI
FastAPIInstrumentor.instrument_app(app)

# 自动注入 requests（用于云 API 调用）
RequestsInstrumentor().instrument()
```

#### 3. Metrics 埋点示例
```python
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# 配置 Metrics
metric_exporter = OTLPMetricExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"),
    insecure=True,
)

metric_reader = PeriodicExportingMetricReader(
    metric_exporter,
    export_interval_millis=60000,  # 每分钟导出一次
)

metrics.set_meter_provider(MeterProvider(
    resource=resource,
    metric_readers=[metric_reader],
))

meter = metrics.get_meter(__name__)

# 定义指标
api_request_counter = meter.create_counter(
    "cloudlens.api.requests",
    description="Total number of API requests",
    unit="1",
)

api_duration_histogram = meter.create_histogram(
    "cloudlens.api.duration",
    description="API request duration",
    unit="ms",
)

cache_hit_counter = meter.create_counter(
    "cloudlens.cache.hits",
    description="Cache hit count",
    unit="1",
)

# 使用示例
@router.get("/resources")
async def list_resources(...):
    with tracer.start_as_current_span("list_resources") as span:
        # 记录请求
        api_request_counter.add(1, {
            "endpoint": "/api/resources",
            "method": "GET",
        })
        
        start_time = time.time()
        try:
            # 业务逻辑
            result = ...
            
            # 记录成功
            span.set_attribute("result.count", len(result))
            span.set_status(trace.Status(trace.StatusCode.OK))
            
            return result
        except Exception as e:
            # 记录错误
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
        finally:
            # 记录耗时
            duration = (time.time() - start_time) * 1000
            api_duration_histogram.record(duration, {
                "endpoint": "/api/resources",
            })
```

#### 4. Logs 集成
```python
from opentelemetry import _logs
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

# 配置 Logs
log_exporter = OTLPLogExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"),
    insecure=True,
)

_logs.set_logger_provider(LoggerProvider(resource=resource))
logger_provider = _logs.get_logger_provider()
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

# 配置 logging handler
handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logging.getLogger().addHandler(handler)
```

### 前端集成（Next.js）

#### 1. 安装依赖
```bash
npm install @opentelemetry/api @opentelemetry/sdk-web @opentelemetry/instrumentation @opentelemetry/instrumentation-fetch @opentelemetry/exporter-otlp-http
```

#### 2. 创建 OTEL 初始化文件
```typescript
// web/frontend/lib/otel.ts
import { WebSDK } from '@opentelemetry/sdk-web';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { OTLPTraceExporter } from '@opentelemetry/exporter-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

export function initOpenTelemetry() {
  if (typeof window === 'undefined') {
    // 服务端不初始化
    return;
  }

  const sdk = new WebSDK({
    resource: new Resource({
      [SemanticResourceAttributes.SERVICE_NAME]: 'cloudlens-frontend',
      [SemanticResourceAttributes.SERVICE_VERSION]: '2.1.0',
    }),
    traceExporter: new OTLPTraceExporter({
      url: process.env.NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318/v1/traces',
    }),
    instrumentations: [
      new FetchInstrumentation({
        propagateTraceHeaderCorsUrls: [
          /^https?:\/\/localhost:8000/,
          /^https?:\/\/.*\.example\.com/,
        ],
      }),
    ],
  });

  sdk.start();
}

// 在 app/layout.tsx 中调用
```

#### 3. 自定义 Span 示例
```typescript
import { trace } from '@opentelemetry/api';

const tracer = trace.getTracer('cloudlens-frontend');

export async function fetchResources(type: string) {
  const span = tracer.startSpan('fetchResources');
  span.setAttribute('resource.type', type);
  
  try {
    const response = await fetch(`/api/resources?type=${type}`);
    span.setAttribute('http.status_code', response.status);
    const data = await response.json();
    span.setAttribute('result.count', data.length);
    return data;
  } catch (error) {
    span.recordException(error);
    span.setStatus({ code: SpanStatusCode.ERROR });
    throw error;
  } finally {
    span.end();
  }
}
```

---

## 📦 Kubernetes 清单文件

### 1. Namespace
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cloudlens
  labels:
    name: cloudlens
```

### 2. ConfigMap（应用配置）
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cloudlens-config
  namespace: cloudlens
data:
  # 应用配置
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "production"
  
  # OpenTelemetry 配置
  OTEL_SERVICE_NAME: "cloudlens-backend"
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4317"
  OTEL_RESOURCE_ATTRIBUTES: "service.name=cloudlens-backend,service.version=2.1.0"
  
  # 数据库配置（如果使用 PostgreSQL）
  DATABASE_HOST: "postgresql"
  DATABASE_PORT: "5432"
  DATABASE_NAME: "cloudlens"
```

### 3. Secret（敏感信息）
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: cloudlens-secrets
  namespace: cloudlens
type: Opaque
stringData:
  # 数据库密码（如果使用 PostgreSQL）
  DATABASE_PASSWORD: "your-password"
  
  # 云账号凭证（可选，建议使用外部密钥管理）
  # ALIYUN_ACCESS_KEY_ID: "..."
  # ALIYUN_ACCESS_KEY_SECRET: "..."
```

### 4. PersistentVolumeClaim（SQLite 数据）
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: cloudlens-data
  namespace: cloudlens
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard  # 根据集群调整
```

### 5. 后端 Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudlens-backend
  namespace: cloudlens
  labels:
    app: cloudlens-backend
spec:
  replicas: 2  # 如果使用 SQLite，建议设为 1
  selector:
    matchLabels:
      app: cloudlens-backend
  template:
    metadata:
      labels:
        app: cloudlens-backend
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: backend
        image: your-registry/cloudlens-backend:2.1.0
        imagePullPolicy: IfNotPresent
        ports:
        - name: http
          containerPort: 8000
          protocol: TCP
        env:
        - name: OTEL_SERVICE_NAME
          valueFrom:
            configMapKeyRef:
              name: cloudlens-config
              key: OTEL_SERVICE_NAME
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          valueFrom:
            configMapKeyRef:
              name: cloudlens-config
              key: OTEL_EXPORTER_OTLP_ENDPOINT
        - name: DATABASE_PATH
          value: "/data/cloudlens.db"
        envFrom:
        - configMapRef:
            name: cloudlens-config
        - secretRef:
            name: cloudlens-secrets
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
        volumeMounts:
        - name: data
          mountPath: /data
        - name: config
          mountPath: /app/.cloudlens
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: cloudlens-data
      - name: config
        emptyDir: {}
```

### 6. 前端 Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudlens-frontend
  namespace: cloudlens
  labels:
    app: cloudlens-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: cloudlens-frontend
  template:
    metadata:
      labels:
        app: cloudlens-frontend
    spec:
      containers:
      - name: frontend
        image: your-registry/cloudlens-frontend:2.1.0
        imagePullPolicy: IfNotPresent
        ports:
        - name: http
          containerPort: 3000
          protocol: TCP
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "http://cloudlens-backend:8000"
        - name: NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT
          value: "http://otel-collector:4318/v1/traces"
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 7. Service
```yaml
# 后端 Service
apiVersion: v1
kind: Service
metadata:
  name: cloudlens-backend
  namespace: cloudlens
  labels:
    app: cloudlens-backend
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
    name: http
  selector:
    app: cloudlens-backend

---
# 前端 Service
apiVersion: v1
kind: Service
metadata:
  name: cloudlens-frontend
  namespace: cloudlens
  labels:
    app: cloudlens-frontend
spec:
  type: ClusterIP
  ports:
  - port: 3000
    targetPort: 3000
    protocol: TCP
    name: http
  selector:
    app: cloudlens-frontend
```

### 8. OpenTelemetry Collector Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: cloudlens
spec:
  replicas: 1
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      containers:
      - name: otel-collector
        image: otel/opentelemetry-collector:latest
        args: ["--config=/etc/otel-collector-config.yaml"]
        volumeMounts:
        - name: otel-collector-config
          mountPath: /etc/otel-collector-config.yaml
          subPath: otel-collector-config.yaml
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 1000m
            memory: 1Gi
      volumes:
      - name: otel-collector-config
        configMap:
          name: otel-collector-config

---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: cloudlens
spec:
  type: ClusterIP
  ports:
  - port: 4317
    targetPort: 4317
    protocol: TCP
    name: otlp-grpc
  - port: 4318
    targetPort: 4318
    protocol: TCP
    name: otlp-http
  selector:
    app: otel-collector
```

---

## 🔐 安全考虑

### 1. Secret 管理
- **选项1**: Kubernetes Secret（基础）
- **选项2**: 外部密钥管理（推荐）
  - HashiCorp Vault
  - AWS Secrets Manager
  - 阿里云 KMS
  - 腾讯云 SSM

### 2. 网络策略
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cloudlens-network-policy
  namespace: cloudlens
spec:
  podSelector:
    matchLabels:
      app: cloudlens-backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: cloudlens-frontend
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: otel-collector
    ports:
    - protocol: TCP
      port: 4317
  - to: []  # 允许访问外部云 API
```

### 3. RBAC
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cloudlens-backend
  namespace: cloudlens

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: cloudlens-backend
  namespace: cloudlens
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]
  resourceNames: ["cloudlens-config", "cloudlens-secrets"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: cloudlens-backend
  namespace: cloudlens
subjects:
- kind: ServiceAccount
  name: cloudlens-backend
  namespace: cloudlens
roleRef:
  kind: Role
  name: cloudlens-backend
  apiGroup: rbac.authorization.k8s.io
```

---

## 📊 监控指标设计

### 业务指标
```python
# 资源查询指标
cloudlens.resources.queries_total{type="ecs",account="prod"}
cloudlens.resources.query_duration_ms{type="ecs"}

# 缓存指标
cloudlens.cache.hits_total{resource_type="ecs"}
cloudlens.cache.misses_total{resource_type="ecs"}
cloudlens.cache.hit_rate{resource_type="ecs"}

# API 调用指标
cloudlens.provider.api.calls_total{provider="aliyun",api="DescribeInstances"}
cloudlens.provider.api.duration_ms{provider="aliyun",api="DescribeInstances"}
cloudlens.provider.api.errors_total{provider="aliyun",api="DescribeInstances"}

# 成本分析指标
cloudlens.cost.analysis.duration_ms
cloudlens.cost.analysis.resources_analyzed_total

# 告警指标
cloudlens.alerts.triggered_total{severity="critical"}
cloudlens.alerts.resolved_total{severity="critical"}
```

### 系统指标
- CPU 使用率
- 内存使用率
- 网络 I/O
- 磁盘 I/O（如果使用 PVC）

---

## 🚨 告警规则示例

### Prometheus 告警规则
```yaml
groups:
- name: cloudlens
  rules:
  - alert: HighErrorRate
    expr: rate(cloudlens_api_errors_total[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "API 错误率过高"
      description: "错误率: {{ $value }}"

  - alert: HighLatency
    expr: histogram_quantile(0.95, cloudlens_api_duration_ms_bucket) > 1000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "API 延迟过高"
      description: "P95 延迟: {{ $value }}ms"

  - alert: LowCacheHitRate
    expr: cloudlens_cache_hit_rate < 0.5
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "缓存命中率过低"
      description: "命中率: {{ $value }}"

  - alert: PodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Pod 重启频繁"
      description: "Pod {{ $labels.pod }} 在 15 分钟内重启了 {{ $value }} 次"
```

---

## 📈 Grafana 仪表盘设计

### 1. 概览仪表盘
- API 请求总数和 QPS
- 错误率
- 平均响应时间（P50, P95, P99）
- 活跃用户数（如果有）

### 2. 业务指标仪表盘
- 资源查询统计（按类型、账号）
- 缓存命中率趋势
- 成本分析执行情况
- 告警触发统计

### 3. 系统指标仪表盘
- CPU/内存使用率
- 网络流量
- Pod 状态
- 数据库连接数（如果使用 PostgreSQL）

### 4. 追踪视图
- 服务依赖图
- 慢请求分析
- 错误追踪

---

## 🔄 CI/CD 流程（可选）

### GitHub Actions 示例
```yaml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Build backend image
      run: |
        docker build -t ${{ secrets.REGISTRY }}/cloudlens-backend:${{ github.sha }} -f Dockerfile.backend .
        docker push ${{ secrets.REGISTRY }}/cloudlens-backend:${{ github.sha }}
    
    - name: Build frontend image
      run: |
        docker build -t ${{ secrets.REGISTRY }}/cloudlens-frontend:${{ github.sha }} -f Dockerfile.frontend .
        docker push ${{ secrets.REGISTRY }}/cloudlens-frontend:${{ github.sha }}
    
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/cloudlens-backend backend=${{ secrets.REGISTRY }}/cloudlens-backend:${{ github.sha }} -n cloudlens
        kubectl set image deployment/cloudlens-frontend frontend=${{ secrets.REGISTRY }}/cloudlens-frontend:${{ github.sha }} -n cloudlens
```

---

## 💰 成本估算

### 基础设施成本（自建方案）

#### Kubernetes 集群
- **Master 节点**: 3 x (2 CPU, 4GB RAM) = 约 ¥500/月
- **Worker 节点**: 3 x (4 CPU, 8GB RAM) = 约 ¥1500/月
- **总计**: 约 ¥2000/月

#### 可观测性后端
- **Prometheus**: 2 CPU, 4GB RAM = 约 ¥300/月
- **Jaeger**: 2 CPU, 4GB RAM = 约 ¥300/月
- **Loki**: 2 CPU, 4GB RAM = 约 ¥300/月
- **Grafana**: 1 CPU, 2GB RAM = 约 ¥150/月
- **总计**: 约 ¥1050/月

#### 存储
- **PVC**: 100GB = 约 ¥200/月

#### 总计
- **自建方案**: 约 ¥3250/月

### 云服务方案（推荐）

#### 使用云服务商的托管服务
- **Kubernetes 集群**: 约 ¥1000-2000/月
- **Grafana Cloud**: 免费版或 $49/月起
- **或使用云服务商的 APM**: 约 ¥500-1000/月

#### 总计
- **云服务方案**: 约 ¥1500-3000/月

---

## ✅ 实施检查清单

### 准备阶段
- [ ] Kubernetes 集群已准备（或使用云服务商托管集群）
- [ ] kubectl 已配置
- [ ] 容器镜像仓库已创建
- [ ] 可观测性后端已部署（Prometheus, Jaeger, Loki, Grafana）
- [ ] 域名和 SSL 证书已准备（如果使用 Ingress）

### 代码集成
- [ ] 后端 OpenTelemetry SDK 已安装
- [ ] 后端 Metrics 埋点已完成
- [ ] 后端 Logs 集成已完成
- [ ] 后端 Traces 埋点已完成
- [ ] 前端 OpenTelemetry SDK 已安装
- [ ] 前端追踪已集成
- [ ] 本地测试通过

### 容器化
- [ ] 后端 Dockerfile 已创建
- [ ] 前端 Dockerfile 已创建
- [ ] .dockerignore 已配置
- [ ] 镜像已构建并测试
- [ ] 镜像已推送到 Registry

### Kubernetes 部署
- [ ] Namespace 已创建
- [ ] ConfigMap 已创建
- [ ] Secret 已创建（或使用外部密钥管理）
- [ ] PersistentVolumeClaim 已创建（如果使用 SQLite）
- [ ] 后端 Deployment 和 Service 已创建
- [ ] 前端 Deployment 和 Service 已创建
- [ ] OpenTelemetry Collector 已部署
- [ ] Ingress 已配置
- [ ] 网络策略已配置（可选）
- [ ] RBAC 已配置（可选）

### 验证
- [ ] 服务可以正常访问
- [ ] 健康检查通过
- [ ] Metrics 数据已收集到 Prometheus
- [ ] Logs 数据已收集到 Loki
- [ ] Traces 数据已收集到 Jaeger
- [ ] Grafana 仪表盘已配置
- [ ] 告警规则已设置并测试
- [ ] 性能测试通过

---

## 📚 参考资料

### OpenTelemetry
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [OpenTelemetry JavaScript Documentation](https://opentelemetry.io/docs/instrumentation/js/)
- [OTEL Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)

### Kubernetes
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)

### 可观测性工具
- [Prometheus](https://prometheus.io/docs/)
- [Jaeger](https://www.jaegertracing.io/docs/)
- [Loki](https://grafana.com/docs/loki/latest/)
- [Grafana](https://grafana.com/docs/grafana/latest/)

---

## 💡 建议

### 短期（1-2周）
1. 先完成 OpenTelemetry 集成和本地测试
2. 创建 Dockerfile 并构建镜像
3. 在测试环境部署验证

### 中期（1个月）
1. 迁移到生产环境
2. 配置 Grafana 仪表盘
3. 设置告警规则
4. 性能优化

### 长期（3个月+）
1. 考虑迁移到 PostgreSQL（如果需要高可用）
2. 实现 CI/CD 自动化部署
3. 添加更多业务指标
4. 优化资源使用和成本

---

**注意**: 这是一个详细的技术设计方案，实际实施时请根据您的具体环境和需求进行调整。


