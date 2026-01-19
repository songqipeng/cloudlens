# CloudLens 微服务架构设计

## 架构概览

CloudLens采用微服务架构，通过Nginx作为API Gateway统一入口，将前端、后端和AI服务分离。

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx / Ingress                       │
│                    (API Gateway + 路由)                      │
│                      Port: 80/443                            │
└────────────┬────────────────┬─────────────────┬──────────────┘
             │                │                 │
    ┌────────▼────────┐  ┌───▼───────────┐  ┌──▼──────────────┐
    │  Frontend SPA   │  │  Backend API  │  │   AI Service    │
    │   (Next.js)     │  │   (FastAPI)   │  │  (FastAPI)      │
    │                 │  │               │  │                 │
    │  - 仪表板       │  │  - 成本API    │  │  - Chatbot      │
    │  - 报表页       │  │  - 账号API    │  │  - 根因分析     │
    │  - 设置页       │  │  - 闲置资源API│  │  - 报告生成     │
    │  Port: 3000     │  │  Port: 8000   │  │  Port: 8001    │
    └─────────────────┘  └───┬───────────┘  └──┬──────────────┘
                             │                 │
                    ┌────────▼─────────────────▼─────────┐
                    │        Shared Database             │
                    │          (MySQL + Redis)           │
                    │        Port: 3306 / 6379           │
                    └────────────────────────────────────┘
```

## 服务拆分

### 1. Frontend Service (Next.js)

**职责**:
- 用户界面展示
- 客户端路由
- 状态管理
- API调用

**技术栈**:
- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS

**部署**:
- Docker容器
- 端口: 3000
- 生产环境使用standalone模式

### 2. Backend API Service (FastAPI)

**职责**:
- 业务逻辑处理
- 数据查询和聚合
- 资源管理
- 成本分析

**主要API模块**:
- `/api/v1/accounts` - 账号管理
- `/api/v1/resources` - 资源查询
- `/api/v1/costs` - 成本分析
- `/api/v1/budgets` - 预算管理
- `/api/v1/anomaly` - 异常检测
- `/api/v1/alerts` - 告警管理

**技术栈**:
- FastAPI
- Python 3.11+
- SQLAlchemy (ORM)
- MySQL/Redis

**部署**:
- Docker容器
- 端口: 8000
- 支持多实例负载均衡

### 3. AI Service (FastAPI) - 可选独立服务

**职责**:
- AI Chatbot对话
- 成本根因分析
- 智能优化建议
- 自然语言查询

**主要API模块**:
- `/api/v1/chatbot` - AI对话
- `/api/v1/ai/analyze` - 根因分析
- `/api/v1/ai/optimize` - 优化建议

**技术栈**:
- FastAPI
- Claude API / OpenAI API
- LangChain (可选)

**部署**:
- Docker容器
- 端口: 8001 (如果独立部署)
- 或集成在Backend Service中

## 数据库服务

### MySQL

**用途**:
- 账单数据存储
- 预算记录
- 告警记录
- 对话历史
- 资源缓存

**配置**:
- 端口: 3306
- 数据库名: cloudlens
- 字符集: utf8mb4

### Redis

**用途**:
- 缓存层
- 会话存储
- 任务队列（可选）

**配置**:
- 端口: 6379
- 持久化: AOF + RDB

## Docker Compose 部署

使用 `docker-compose.yml` 一键启动所有服务：

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## Nginx配置

Nginx作为API Gateway，负责：
1. 路由转发
2. 负载均衡
3. SSL终止（生产环境）
4. 静态文件服务（可选）

配置文件: `nginx.conf`

## 服务间通信

### Frontend → Backend
- HTTP REST API
- 通过Nginx代理
- 自动包含账号参数

### Backend → Database
- SQLAlchemy ORM
- 连接池管理
- 读写分离（可选）

### Backend → AI Service
- HTTP REST API
- 异步调用
- 超时控制

## 扩展性设计

### 水平扩展

1. **Backend Service**
   - 可以部署多个实例
   - Nginx负载均衡
   - 无状态设计

2. **Frontend Service**
   - Next.js standalone模式
   - CDN加速静态资源
   - 服务端渲染缓存

### 垂直扩展

1. **数据库优化**
   - 索引优化
   - 分区表
   - 读写分离

2. **缓存策略**
   - Redis缓存热点数据
   - 前端缓存API响应
   - CDN缓存静态资源

## 监控和日志

### 应用监控
- Prometheus指标收集
- Grafana可视化
- 健康检查端点

### 日志管理
- 集中式日志（ELK Stack）
- 结构化日志
- 日志轮转

## 安全考虑

1. **API认证**
   - JWT Token
   - API Key管理

2. **网络安全**
   - HTTPS/TLS
   - 防火墙规则
   - 内网通信

3. **数据安全**
   - 敏感数据加密
   - SQL注入防护
   - XSS防护

## 部署建议

### 开发环境
- 单机Docker Compose
- 所有服务本地运行

### 生产环境
- Kubernetes部署（ACK）
- 服务独立扩缩容
- 高可用配置
- 自动故障恢复

## 未来扩展

1. **消息队列**
   - RabbitMQ / Kafka
   - 异步任务处理

2. **服务网格**
   - Istio
   - 服务发现和治理

3. **API网关增强**
   - Kong / Traefik
   - 限流和熔断
