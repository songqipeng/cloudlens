# CloudLens AWS 部署指南

**更新时间**: 2026-01-23  
**目标**: 在AWS上以最低成本部署CloudLens

---

## 📊 资源需求分析

### 当前架构（Docker Compose）

```
服务组件：
├── MySQL 8.0          (数据库)
├── Redis 7            (缓存)
├── FastAPI Backend    (Python 3.11)
├── Next.js Frontend   (Node.js 20)
└── Nginx              (可选，API Gateway)
```

### 资源估算

| 服务 | CPU | 内存 | 存储 | 说明 |
|------|-----|------|------|------|
| MySQL | 0.5-1核 | 1-2GB | 20-100GB | 根据数据量 |
| Redis | 0.25核 | 512MB-1GB | 1-5GB | 缓存数据 |
| Backend | 0.5-1核 | 512MB-1GB | 1GB | Python应用 |
| Frontend | 0.25-0.5核 | 256-512MB | 500MB | Next.js应用 |
| **总计** | **1.5-3核** | **2.5-5GB** | **25-110GB** | **最低配置** |

---

## 🎯 AWS部署方案对比

### 方案1: EC2 + Docker Compose（推荐 - 最经济）⭐

**适用场景**: 小到中型部署，成本敏感

**架构**:
```
单台EC2实例
├── Docker Compose运行所有服务
├── 使用EBS存储（持久化）
└── Application Load Balancer（可选，HTTPS）
```

**推荐配置**:
- **实例类型**: `t3.medium` (2 vCPU, 4GB RAM)
- **存储**: 50GB gp3 EBS
- **网络**: 标准网络

**成本估算**（us-east-1）:
- EC2 t3.medium: **$0.0416/小时** ≈ **$30/月**
- EBS 50GB gp3: **$0.08/GB/月** = **$4/月**
- 数据传输: **$0.09/GB**（前100GB免费）
- **总计**: **约 $35-50/月**

**优点**:
- ✅ 成本最低
- ✅ 部署简单（直接运行docker-compose）
- ✅ 完全控制
- ✅ 适合小规模部署

**缺点**:
- ❌ 单点故障（需要手动备份）
- ❌ 需要手动管理更新
- ❌ 扩展性有限

---

### 方案2: ECS Fargate（推荐 - 按使用付费）⭐

**适用场景**: 需要容器编排，但不想管理服务器

**架构**:
```
ECS Fargate集群
├── MySQL任务（RDS替代，或使用Fargate）
├── Redis任务（ElastiCache替代，或使用Fargate）
├── Backend任务（Fargate）
├── Frontend任务（Fargate）
└── Application Load Balancer
```

**推荐配置**:
- **MySQL**: Fargate 0.5 vCPU, 1GB RAM（或使用RDS t3.micro）
- **Redis**: Fargate 0.25 vCPU, 512MB RAM（或使用ElastiCache t3.micro）
- **Backend**: Fargate 0.5 vCPU, 1GB RAM
- **Frontend**: Fargate 0.25 vCPU, 512MB RAM

**成本估算**（us-east-1）:
- Fargate vCPU: **$0.04048/vCPU/小时**
- Fargate 内存: **$0.004445/GB/小时**
- 任务总计: 1.5 vCPU, 3GB RAM
- **Fargate成本**: **$0.04048 × 1.5 + $0.004445 × 3 = $0.073/小时** ≈ **$53/月**
- **或使用RDS + ElastiCache**: 
  - RDS t3.micro: **$15/月**
  - ElastiCache t3.micro: **$15/月**
  - Fargate (Backend + Frontend): **$23/月**
  - **总计**: **约 $53/月**

**优点**:
- ✅ 按使用付费，无需管理服务器
- ✅ 自动扩展（可配置）
- ✅ 高可用性（多AZ部署）
- ✅ 容器编排

**缺点**:
- ❌ 成本略高于EC2
- ❌ 需要学习ECS配置

---

### 方案3: EKS（Kubernetes）

**适用场景**: 需要Kubernetes特性，多环境管理

**架构**:
```
EKS集群
├── 控制平面（AWS管理）
├── 节点组（EC2或Fargate）
│   ├── MySQL Pod
│   ├── Redis Pod
│   ├── Backend Pod
│   └── Frontend Pod
└── Load Balancer Controller
```

**最低配置**:
- **控制平面**: **$0.10/小时** = **$73/月**（固定费用）
- **节点**: 1个 t3.medium = **$30/月**
- **总计**: **约 $103/月**（最低配置）

**成本估算**（us-east-1）:
- EKS控制平面: **$73/月**（固定）
- 节点（t3.medium × 1）: **$30/月**
- EBS存储: **$4/月**
- **总计**: **约 $107/月**

**优点**:
- ✅ Kubernetes完整功能
- ✅ 高度可扩展
- ✅ 适合多环境、多团队

**缺点**:
- ❌ **成本最高**（控制平面$73/月固定费用）
- ❌ 配置复杂
- ❌ 对于单应用来说可能过度设计

**结论**: ❌ **不推荐** - 对于CloudLens来说，EKS的成本（$73/月控制平面）太高，除非您需要Kubernetes的特定功能。

---

### 方案4: App Runner（无服务器容器）

**适用场景**: 简单部署，自动扩展

**架构**:
```
App Runner服务
├── Backend服务（App Runner）
├── Frontend服务（App Runner）
├── RDS MySQL（独立）
└── ElastiCache Redis（独立）
```

**成本估算**（us-east-1）:
- App Runner: **$0.007/vCPU/小时 + $0.0008/GB/小时**
- 假设平均使用: 0.5 vCPU, 1GB RAM
- **App Runner成本**: **约 $3-5/月**（按实际使用）
- RDS t3.micro: **$15/月**
- ElastiCache t3.micro: **$15/月**
- **总计**: **约 $33-35/月**

**优点**:
- ✅ 按使用付费，成本低
- ✅ 自动扩展
- ✅ 零运维

**缺点**:
- ❌ 不支持有状态服务（MySQL/Redis需要独立）
- ❌ 配置选项有限

---

### 方案5: Lightsail（固定价格）

**适用场景**: 简单部署，固定预算

**推荐配置**:
- **Lightsail $20套餐**: 2 vCPU, 4GB RAM, 80GB SSD
- **或 $40套餐**: 4 vCPU, 8GB RAM, 160GB SSD

**成本估算**:
- Lightsail $20套餐: **$20/月**
- 数据传输: 包含3TB
- **总计**: **$20/月**（最简单）

**优点**:
- ✅ 固定价格，简单明了
- ✅ 包含数据传输
- ✅ 一键部署

**缺点**:
- ❌ 扩展性有限
- ❌ 功能相对简单

---

## 🏆 推荐方案排序

### 1. **EC2 + Docker Compose**（最推荐）⭐

**理由**:
- ✅ 成本最低（$35-50/月）
- ✅ 部署最简单（直接运行docker-compose）
- ✅ 完全控制
- ✅ 适合CloudLens的架构

**实施步骤**:
```bash
# 1. 启动EC2实例（t3.medium）
# 2. 安装Docker和Docker Compose
# 3. 上传docker-compose.yml
# 4. 运行 docker-compose up -d
```

---

### 2. **ECS Fargate**（次推荐）

**理由**:
- ✅ 按使用付费
- ✅ 无需管理服务器
- ✅ 自动扩展
- ✅ 成本适中（$53/月）

**适用场景**: 需要容器编排，但不想管理EC2

---

### 3. **Lightsail**（最简单）

**理由**:
- ✅ 固定价格（$20/月）
- ✅ 最简单部署
- ✅ 适合小规模使用

---

### 4. **App Runner**（按使用付费）

**理由**:
- ✅ 成本低（$33-35/月）
- ✅ 自动扩展
- ⚠️ 需要RDS和ElastiCache（额外成本）

---

### 5. **EKS**（不推荐）

**理由**:
- ❌ 成本太高（$107/月最低）
- ❌ 配置复杂
- ❌ 对于单应用过度设计

---

## 💰 成本对比表

| 方案 | 月成本 | 按使用付费 | 复杂度 | 推荐度 |
|------|--------|-----------|--------|--------|
| **EC2 + Docker Compose** | **$35-50** | ❌ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **ECS Fargate** | **$53** | ✅ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Lightsail** | **$20** | ❌ | ⭐ | ⭐⭐⭐ |
| **App Runner** | **$33-35** | ✅ | ⭐⭐ | ⭐⭐⭐ |
| **EKS** | **$107+** | ❌ | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## 🚀 推荐实施方案：EC2 + Docker Compose

### 步骤1: 创建EC2实例

```bash
# 推荐配置
实例类型: t3.medium (2 vCPU, 4GB RAM)
操作系统: Amazon Linux 2023 或 Ubuntu 22.04 LTS
存储: 50GB gp3 EBS
安全组: 开放 22(SSH), 80(HTTP), 443(HTTPS), 3000(前端), 8000(后端)
```

### 步骤2: 安装Docker

```bash
# Amazon Linux 2023
sudo yum update -y
sudo yum install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 步骤3: 部署应用

```bash
# 1. 克隆代码
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库密码等

# 3. 启动服务
docker-compose up -d

# 4. 检查状态
docker-compose ps
docker-compose logs -f
```

### 步骤4: 配置域名和HTTPS（可选）

```bash
# 使用AWS Certificate Manager (ACM) 获取SSL证书
# 使用Application Load Balancer + Route 53
# 或使用CloudFront + S3（静态资源）
```

---

## 🔧 成本优化建议

### 1. 使用Reserved Instances（EC2）

- **1年期**: 节省约30%
- **3年期**: 节省约50%
- **适用**: 如果确定长期使用

### 2. 使用Spot Instances（EC2）

- **节省**: 最高90%
- **风险**: 可能被中断
- **适用**: 非关键环境，可以容忍中断

### 3. 使用RDS和ElastiCache（替代容器）

- **RDS t3.micro**: $15/月（比Fargate MySQL更稳定）
- **ElastiCache t3.micro**: $15/月（比Fargate Redis更稳定）
- **优势**: 自动备份、高可用、维护简单

### 4. 使用S3存储静态资源

- **CloudFront + S3**: 前端静态资源
- **成本**: 几乎免费（<$1/月）

### 5. 监控和告警

- **CloudWatch**: 基础监控免费
- **成本告警**: 设置预算告警，避免意外费用

---

## 📋 最低配置推荐

### EC2方案（最经济）

```
实例: t3.small (2 vCPU, 2GB RAM)
存储: 30GB gp3 EBS
月成本: 约 $20-25/月

注意: 2GB RAM可能较紧张，建议至少t3.medium (4GB)
```

### ECS Fargate方案

```
Backend: 0.5 vCPU, 1GB RAM
Frontend: 0.25 vCPU, 512MB RAM
RDS t3.micro: 1 vCPU, 1GB RAM
ElastiCache t3.micro: 1 vCPU, 1.37GB RAM
月成本: 约 $50-55/月
```

---

## ⚠️ 关于EKS的结论

**最低配置EKS成本**:
- 控制平面: **$73/月**（固定，无法避免）
- 节点: **$30/月**（最低1个t3.medium）
- **总计**: **$103/月**

**结论**: ❌ **不推荐使用EKS**

**理由**:
1. **成本太高** - 控制平面$73/月是固定费用，即使不用也要付
2. **过度设计** - CloudLens是单应用，不需要Kubernetes的复杂功能
3. **配置复杂** - 需要学习Kubernetes，维护成本高
4. **性价比低** - 同样的功能，EC2方案只需$35/月

**EKS适合的场景**:
- 需要多环境（dev/staging/prod）
- 需要多团队共享集群
- 需要Kubernetes的特定功能（如Operator、Helm等）
- 已有Kubernetes运维团队

---

## 🎯 最终推荐

### 最佳方案：EC2 t3.medium + Docker Compose

**配置**:
- 实例: t3.medium (2 vCPU, 4GB RAM)
- 存储: 50GB gp3 EBS
- 网络: 标准网络

**成本**: **约 $35-50/月**

**优势**:
- ✅ 成本最低
- ✅ 部署最简单
- ✅ 完全控制
- ✅ 适合CloudLens架构

**部署时间**: **30分钟**

---

## 📝 下一步

1. **选择方案**: 推荐EC2 + Docker Compose
2. **创建EC2实例**: 使用推荐配置
3. **部署应用**: 按照步骤3执行
4. **配置域名**: 使用Route 53 + ALB
5. **设置监控**: CloudWatch监控和告警

---

*文档生成时间: 2026-01-23*  
*基于AWS us-east-1区域价格（2026年1月）*
