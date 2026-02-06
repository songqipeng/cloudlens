# CloudLens ECS Fargate部署指南

如果您选择ECS Fargate方案，这是详细的部署步骤。

---

## 📋 前置要求

- AWS账户
- AWS CLI已安装并配置
- Docker已安装（用于构建镜像）
- ECR仓库已创建

---

## 🚀 部署步骤

### 1. 创建ECR仓库

```bash
# 创建后端镜像仓库
aws ecr create-repository --repository-name cloudlens-backend --region us-east-1

# 创建前端镜像仓库
aws ecr create-repository --repository-name cloudlens-frontend --region us-east-1
```

### 2. 构建并推送镜像

```bash
# 登录ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# 构建后端镜像
docker build -t cloudlens-backend:latest -f web/backend/Dockerfile .
docker tag cloudlens-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/cloudlens-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/cloudlens-backend:latest

# 构建前端镜像
docker build -t cloudlens-frontend:latest -f web/frontend/Dockerfile .
docker tag cloudlens-frontend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/cloudlens-frontend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/cloudlens-frontend:latest
```

### 3. 创建RDS MySQL实例

```bash
aws rds create-db-instance \
  --db-instance-identifier cloudlens-mysql \
  --db-instance-class db.t3.micro \
  --engine mysql \
  --engine-version 8.0 \
  --master-username cloudlens \
  --master-user-password <your-password> \
  --allocated-storage 20 \
  --storage-type gp3 \
  --vpc-security-group-ids <security-group-id> \
  --db-subnet-group-name <subnet-group-name> \
  --backup-retention-period 7 \
  --region us-east-1
```

### 4. 创建ElastiCache Redis实例

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id cloudlens-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --region us-east-1
```

### 5. 创建ECS集群

```bash
aws ecs create-cluster --cluster-name cloudlens-cluster --region us-east-1
```

### 6. 创建任务定义

创建 `task-definition-backend.json`:

```json
{
  "family": "cloudlens-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/cloudlens-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "MYSQL_HOST",
          "value": "<rds-endpoint>"
        },
        {
          "name": "REDIS_HOST",
          "value": "<redis-endpoint>"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/cloudlens-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

注册任务定义:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition-backend.json --region us-east-1
```

### 7. 创建服务

```bash
aws ecs create-service \
  --cluster cloudlens-cluster \
  --service-name cloudlens-backend \
  --task-definition cloudlens-backend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --region us-east-1
```

---

## 💰 成本优化

1. **使用Spot实例**（如果使用EC2节点）: 节省最高90%
2. **Reserved Capacity**（Fargate）: 节省约30%
3. **自动扩展**: 根据负载自动调整，避免浪费
4. **使用CloudWatch监控**: 及时发现资源浪费

---

*更多详细信息请参考AWS官方文档*
