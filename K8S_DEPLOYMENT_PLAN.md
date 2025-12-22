# CloudLens Kubernetes 部署与 OpenTelemetry 可观测性方案

## 📋 目录

1. [架构概览](#架构概览)
2. [技术栈选择](#技术栈选择)
3. [Kubernetes 部署设计](#kubernetes-部署设计)
4. [OpenTelemetry 集成方案](#opentelemetry-集成方案)
5. [需要准备的内容](#需要准备的内容)
6. [实施步骤](#实施步骤)
7. [配置文件示例](#配置文件示例)

---

## 🏗️ 架构概览

### 当前架构
```
┌─────────────────┐
│  Next.js 前端   │  (端口 3000)
│  (React/TS)     │
└────────┬────────┘
         │ HTTP/API
         ▼
┌─────────────────┐
│  FastAPI 后端    │  (端口 8000)
│  (Python)       │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│MySQL  │ │Aliyun │
│DB     │ │SDK    │
└───────┘ └───────┘
```

### 目标架构（K8s + OpenTelemetry）
```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Ingress (Nginx/Traefik)                 │  │
│  └───────────────┬──────────────────┬───────────────────┘  │
│                  │                  │                        │
│         ┌────────▼────────┐  ┌──────▼────────┐              │
│         │  Frontend       │  │  Backend      │              │
│         │  (Next.js)     │  │  (FastAPI)    │              │
│         │  Deployment     │  │  Deployment   │              │
│         └────────┬────────┘  └──────┬─────────┘              │
│                  │                  │                        │
│                  │  OpenTelemetry   │                        │
│                  │  SDK (Metrics/   │                        │
│                  │  Logs/Traces)    │                        │
│                  │                  │                        │
│         ┌────────▼──────────────────▼────────┐              │
│         │  OpenTelemetry Collector           │              │
│         │  (OTEL Collector)                   │              │
│         └────────┬───────────────────────────┘              │
│                  │                                            │
└──────────────────┼──────────────────────────────────────────┘
                   │
         ┌─────────┼─────────┐
         │         │         │
    ┌────▼───┐ ┌───▼───┐ ┌───▼────┐
    │Prometheus│ │Jaeger │ │Loki   │
    │(Metrics) │ │(Trace)│ │(Logs) │
    └────┬─────┘ └───────┘ └───┬───┘
         │                      │
         └──────────┬───────────┘
                    │
              ┌─────▼─────┐
              │  Grafana  │
              │ (可视化)  │
              └───────────┘
```

---

## 🛠️ 技术栈选择

### Kubernetes 组件
- **Ingress Controller**: Nginx Ingress 或 Traefik
- **Service Mesh** (可选): Istio 或 Linkerd（用于更高级的流量管理）
- **ConfigMap/Secret**: 管理配置和敏感信息
- **PersistentVolume**: 用于 SQLite 数据库持久化（可选，建议迁移到 PostgreSQL）

### OpenTelemetry 组件
- **OTEL Collector**: OpenTelemetry Collector（推荐使用 OTLP 协议）
- **后端存储**:
  - **Metrics**: Prometheus + Grafana
  - **Traces**: Jaeger 或 Tempo
  - **Logs**: Loki + Grafana
  - **统一方案**: Grafana Cloud 或 Elastic Stack

### 容器化
- **后端镜像**: Python 3.8+ 基础镜像
- **前端镜像**: Node.js 18+ 基础镜像（Next.js 需要构建阶段）

---

## 🚀 Kubernetes 部署设计

### 1. 命名空间设计
```yaml
# 建议创建独立的命名空间
apiVersion: v1
kind: Namespace
metadata:
  name: cloudlens
```

### 2. 后端部署 (FastAPI)

#### 2.1 Deployment
- **副本数**: 2-3 个（高可用）
- **资源限制**: 
  - CPU: 500m - 2000m
  - Memory: 512Mi - 2Gi
- **健康检查**: `/health` 端点
- **就绪检查**: `/health` 端点
- **环境变量**: 
  - 数据库路径（如果使用 SQLite）
  - OpenTelemetry 配置
  - 日志级别

#### 2.2 Service
- **类型**: ClusterIP（内部访问）或 NodePort（测试）
- **端口**: 8000
- **选择器**: 匹配后端 Deployment

#### 2.3 ConfigMap
- 应用配置（非敏感）
- OpenTelemetry 配置

#### 2.4 Secret
- 云账号凭证（AccessKey）
- 数据库密码（如果迁移到 PostgreSQL）

### 3. 前端部署 (Next.js)

#### 3.1 构建策略
- **选项1**: 在 CI/CD 中构建，推送镜像到 Registry
- **选项2**: 在 K8s 中使用 BuildKit 或 Kaniko 构建（不推荐生产环境）

#### 3.2 Deployment
- **副本数**: 2-3 个
- **资源限制**:
  - CPU: 200m - 1000m
  - Memory: 256Mi - 1Gi
- **环境变量**: API 后端地址

#### 3.3 Service
- **类型**: ClusterIP
- **端口**: 3000

### 4. Ingress
- **域名**: cloudlens.example.com
- **TLS**: 使用 Let's Encrypt 或自签名证书
- **路由规则**:
  - `/api/*` → 后端 Service
  - `/*` → 前端 Service

### 5. 持久化存储（可选）

#### 选项1: 保持 SQLite（简单但不推荐生产）
- 使用 PersistentVolumeClaim
- 单 Pod 访问（ReadWriteOnce）

#### 选项2: 迁移到 PostgreSQL（推荐）
- 使用 StatefulSet 或外部数据库服务
- 支持多副本、高可用

---

## 📊 OpenTelemetry 集成方案

### 1. Metrics（指标）

#### 后端 (FastAPI)
- **HTTP 指标**: 请求数、延迟、错误率
- **业务指标**: 
  - 资源查询次数
  - 缓存命中率
  - API 调用耗时
  - 账号数量
  - 资源类型统计
- **系统指标**: CPU、内存使用率（通过 cAdvisor）

#### 前端 (Next.js)
- **页面加载时间**
- **API 调用次数和延迟**
- **错误率**
- **用户交互事件**（可选）

#### 导出格式
- **OTLP (OpenTelemetry Protocol)**: 推荐
- **Prometheus**: 兼容现有 Prometheus 生态

### 2. Logs（日志）

#### 后端
- **结构化日志**: 使用 OpenTelemetry Logs SDK
- **日志级别**: DEBUG, INFO, WARNING, ERROR
- **日志字段**:
  - Trace ID（关联到 Trace）
  - Span ID
  - 服务名称
  - 时间戳
  - 日志级别
  - 消息内容
  - 上下文信息（账号、资源类型等）

#### 前端
- **控制台日志**: 通过 OpenTelemetry Browser SDK 收集
- **错误日志**: 自动捕获 React 错误边界

#### 导出
- **OTLP Logs**: 发送到 OTEL Collector
- **Loki**: 通过 Collector 的 Loki exporter

### 3. Traces（追踪）

#### 后端
- **HTTP 请求追踪**: 自动追踪所有 FastAPI 路由
- **自定义 Span**: 
  - 云 API 调用（Aliyun SDK）
  - 数据库查询
  - 缓存操作
  - 业务逻辑处理
- **Span 属性**:
  - 账号名称
  - 资源类型
  - 区域
  - 操作类型

#### 前端
- **页面导航追踪**
- **API 调用追踪**
- **用户操作追踪**（可选）

#### 导出
- **OTLP Traces**: 发送到 OTEL Collector
- **Jaeger**: 通过 Collector 的 Jaeger exporter

### 4. OpenTelemetry Collector 配置

#### 接收器 (Receivers)
- **OTLP**: 接收来自应用的 OTLP 数据
- **Prometheus**: 接收 Prometheus 格式的 metrics（可选）

#### 处理器 (Processors)
- **Batch**: 批量处理数据，提高效率
- **Memory Limiter**: 防止内存溢出
- **Resource**: 添加资源属性（服务名称、版本等）
- **Filter**: 过滤不需要的数据（可选）

#### 导出器 (Exporters)
- **Prometheus**: 导出 metrics 到 Prometheus
- **Jaeger**: 导出 traces 到 Jaeger
- **Loki**: 导出 logs 到 Loki
- **OTLP**: 转发到其他 OTEL Collector（可选）

---

## 📦 需要准备的内容

### 1. 基础设施

#### Kubernetes 集群
- **最小配置**: 3 个节点（1 master + 2 worker）
- **推荐配置**: 3 master + 3+ worker（高可用）
- **节点规格**: 
  - Master: 2 CPU, 4GB RAM
  - Worker: 4 CPU, 8GB RAM（每个节点）

#### 容器镜像仓库
- **选项1**: Docker Hub（公开或私有）
- **选项2**: 私有 Registry（Harbor, GitLab Registry）
- **选项3**: 云服务商 Registry（阿里云 ACR, 腾讯云 TCR）

### 2. 可观测性后端

#### 方案A: 自建（推荐用于生产）
- **Prometheus**: Metrics 存储和查询
- **Jaeger**: Traces 存储和查询
- **Loki**: Logs 存储和查询
- **Grafana**: 统一可视化界面
- **存储**: 需要持久化存储（PV）

#### 方案B: 云服务（推荐用于快速启动）
- **Grafana Cloud**: 提供 Metrics, Logs, Traces 一体化服务
- **Datadog**: 商业可观测性平台
- **阿里云 ARMS**: 应用实时监控服务
- **腾讯云 APM**: 应用性能监控

#### 方案C: 混合方案
- 关键指标使用自建 Prometheus
- 日志和追踪使用云服务

### 3. 依赖软件

#### 后端依赖
```python
# 需要添加到 requirements.txt
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-instrumentation-fastapi>=0.42b0
opentelemetry-instrumentation-requests>=0.42b0
opentelemetry-instrumentation-sqlite3>=0.42b0
opentelemetry-exporter-otlp-proto-grpc>=1.20.0
opentelemetry-exporter-prometheus>=1.20.0  # 可选
```

#### 前端依赖
```json
{
  "dependencies": {
    "@opentelemetry/api": "^1.7.0",
    "@opentelemetry/sdk-web": "^0.40.0",
    "@opentelemetry/instrumentation": "^0.40.0",
    "@opentelemetry/instrumentation-fetch": "^0.40.0",
    "@opentelemetry/exporter-otlp-http": "^0.40.0"
  }
}
```

### 4. 配置文件

#### Dockerfile
- 后端 Dockerfile
- 前端 Dockerfile（多阶段构建）

#### Kubernetes 清单
- Namespace
- ConfigMap（应用配置、OTEL 配置）
- Secret（敏感信息）
- Deployment（后端、前端）
- Service（后端、前端）
- Ingress
- PersistentVolumeClaim（如果需要）

#### OpenTelemetry Collector 配置
- Collector 配置文件
- Collector Deployment 和 Service

### 5. CI/CD 流程（可选但推荐）

#### 构建阶段
- 构建 Docker 镜像
- 运行测试
- 安全扫描

#### 部署阶段
- 推送镜像到 Registry
- 更新 Kubernetes 清单
- 执行滚动更新

---

## 📝 实施步骤

### 阶段1: 准备阶段（1-2天）

1. **准备 Kubernetes 集群**
   - 创建集群或使用现有集群
   - 配置 kubectl 访问
   - 安装 Ingress Controller

2. **准备容器镜像仓库**
   - 创建 Registry
   - 配置访问凭证

3. **准备可观测性后端**
   - 选择方案（自建/云服务）
   - 部署 Prometheus, Jaeger, Loki（如果自建）
   - 部署 Grafana

### 阶段2: 代码集成（2-3天）

1. **后端 OpenTelemetry 集成**
   - 安装依赖
   - 配置 OTEL SDK
   - 添加自动和手动埋点
   - 测试 metrics, logs, traces 导出

2. **前端 OpenTelemetry 集成**
   - 安装依赖
   - 配置 OTEL SDK
   - 添加页面和 API 追踪
   - 测试数据导出

3. **OpenTelemetry Collector 部署**
   - 创建 Collector 配置
   - 部署 Collector 到 K8s
   - 验证数据接收

### 阶段3: 容器化（1-2天）

1. **创建 Dockerfile**
   - 后端 Dockerfile
   - 前端 Dockerfile（多阶段构建）

2. **构建和测试镜像**
   - 本地构建测试
   - 推送到 Registry
   - 验证镜像运行

### 阶段4: Kubernetes 部署（1-2天）

1. **创建 Kubernetes 清单**
   - Namespace
   - ConfigMap 和 Secret
   - Deployment 和 Service
   - Ingress

2. **部署和验证**
   - 部署后端
   - 部署前端
   - 验证服务可用性
   - 验证可观测性数据

### 阶段5: 优化和监控（持续）

1. **性能优化**
   - 调整资源限制
   - 优化副本数
   - 优化 Collector 配置

2. **监控和告警**
   - 配置 Grafana 仪表盘
   - 设置告警规则
   - 建立监控流程

---

## 📄 配置文件示例

### 1. 后端 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt web/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 设置环境变量
ENV PYTHONPATH=/app
ENV OTEL_SERVICE_NAME=cloudlens-backend
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# 启动命令
CMD ["uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2. 前端 Dockerfile（多阶段构建）

```dockerfile
# 构建阶段
FROM node:18-alpine AS builder

WORKDIR /app

# 复制依赖文件
COPY web/frontend/package*.json ./
RUN npm ci

# 复制源代码
COPY web/frontend/ .

# 构建应用
RUN npm run build

# 运行阶段
FROM node:18-alpine

WORKDIR /app

# 复制构建产物和必要文件
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules

# 设置环境变量
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV OTEL_SERVICE_NAME=cloudlens-frontend
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
ENV NEXT_PUBLIC_API_URL=http://cloudlens-backend:8000

# 暴露端口
EXPOSE 3000

# 启动命令
CMD ["npm", "start"]
```

### 3. 后端 Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudlens-backend
  namespace: cloudlens
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cloudlens-backend
  template:
    metadata:
      labels:
        app: cloudlens-backend
    spec:
      containers:
      - name: backend
        image: your-registry/cloudlens-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: OTEL_SERVICE_NAME
          value: "cloudlens-backend"
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: "http://otel-collector:4317"
        - name: OTEL_RESOURCE_ATTRIBUTES
          value: "service.name=cloudlens-backend,service.version=2.1.0"
        - name: DATABASE_PATH
          value: "/data/cloudlens.db"
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: cloudlens-data
```

### 4. OpenTelemetry Collector 配置

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s
    send_batch_size: 1024
  memory_limiter:
    limit_mib: 512
  resource:
    attributes:
      - key: deployment.environment
        value: production
        action: upsert

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
  
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
  
  loki:
    endpoint: http://loki:3100/loki/api/v1/push

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch, resource]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch, resource]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch, resource]
      exporters: [loki]
```

### 5. Ingress 配置

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: cloudlens-ingress
  namespace: cloudlens
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - cloudlens.example.com
    secretName: cloudlens-tls
  rules:
  - host: cloudlens.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: cloudlens-backend
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: cloudlens-frontend
            port:
              number: 3000
```

---

## 🔍 关键考虑事项

### 1. 数据持久化
- **SQLite**: 当前使用 SQLite，在 K8s 中需要 PVC
- **建议**: 迁移到 PostgreSQL 或 MySQL（支持多副本、高可用）

### 2. 配置管理
- **敏感信息**: 使用 Secret（AccessKey、数据库密码）
- **非敏感配置**: 使用 ConfigMap
- **环境变量**: 区分 dev/staging/prod

### 3. 安全性
- **网络策略**: 限制 Pod 间通信
- **RBAC**: 配置最小权限
- **镜像扫描**: 定期扫描镜像漏洞
- **Secret 加密**: 使用 K8s Secret 加密

### 4. 性能优化
- **资源限制**: 合理设置 requests 和 limits
- **副本数**: 根据负载调整
- **HPA**: 考虑使用 Horizontal Pod Autoscaler
- **缓存策略**: 优化缓存配置

### 5. 监控和告警
- **关键指标**: 
  - API 响应时间
  - 错误率
  - 资源使用率
  - 缓存命中率
- **告警规则**: 
  - 服务不可用
  - 错误率过高
  - 资源使用率过高

---

## 📚 参考资料

### OpenTelemetry
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [OpenTelemetry JavaScript](https://opentelemetry.io/docs/instrumentation/js/)
- [OTEL Collector](https://opentelemetry.io/docs/collector/)

### Kubernetes
- [Kubernetes 官方文档](https://kubernetes.io/docs/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)

### 可观测性工具
- [Prometheus](https://prometheus.io/docs/)
- [Jaeger](https://www.jaegertracing.io/docs/)
- [Loki](https://grafana.com/docs/loki/latest/)
- [Grafana](https://grafana.com/docs/grafana/latest/)

---

## ✅ 检查清单

### 准备阶段
- [ ] Kubernetes 集群已准备
- [ ] 容器镜像仓库已配置
- [ ] 可观测性后端已部署（Prometheus, Jaeger, Loki, Grafana）
- [ ] kubectl 已配置并可以访问集群

### 代码集成
- [ ] 后端 OpenTelemetry SDK 已集成
- [ ] 前端 OpenTelemetry SDK 已集成
- [ ] Metrics 埋点已完成
- [ ] Logs 集成已完成
- [ ] Traces 埋点已完成
- [ ] 本地测试通过

### 容器化
- [ ] 后端 Dockerfile 已创建
- [ ] 前端 Dockerfile 已创建
- [ ] 镜像已构建并推送到 Registry
- [ ] 镜像已测试

### Kubernetes 部署
- [ ] Namespace 已创建
- [ ] ConfigMap 和 Secret 已创建
- [ ] 后端 Deployment 和 Service 已创建
- [ ] 前端 Deployment 和 Service 已创建
- [ ] OpenTelemetry Collector 已部署
- [ ] Ingress 已配置
- [ ] 服务已部署并验证

### 验证
- [ ] 服务可以正常访问
- [ ] Metrics 数据已收集
- [ ] Logs 数据已收集
- [ ] Traces 数据已收集
- [ ] Grafana 仪表盘已配置
- [ ] 告警规则已设置

---

## 💡 下一步行动

1. **确认方案**:  review 本方案，确认技术选型和架构设计
2. **准备环境**: 准备 Kubernetes 集群和可观测性后端
3. **代码集成**: 开始集成 OpenTelemetry SDK
4. **容器化**: 创建 Dockerfile 并构建镜像
5. **部署测试**: 在测试环境部署并验证
6. **生产部署**: 部署到生产环境

---

**注意**: 这是一个设计方案文档，实际实施前请根据您的具体环境进行调整。


