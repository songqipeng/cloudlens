# CloudLens 标准开发流程

## 目标
- ✅ 开发快速迭代
- ✅ 测试准确可靠
- ✅ 发布稳定安全
- ✅ 数据准确一致
- ✅ 流程清晰规范

---

## 一、环境分层策略

### 环境定义

```
开发环境 (Dev)  →  集成测试 (Staging)  →  生产环境 (Production)
   ↓                    ↓                        ↓
  热重载            真实镜像测试              正式运行
  快速迭代          功能验证                 数据准确
  本地数据          测试数据                 真实数据
```

### 环境对比表

| 特性 | 开发环境 (Dev) | 集成测试 (Staging) | 生产环境 (Production) |
|------|---------------|-------------------|---------------------|
| **目的** | 快速开发 | 发布前验证 | 正式服务 |
| **代码来源** | 本地挂载（实时） | Git分支镜像 | Git Tag镜像 |
| **热重载** | ✅ | ❌ | ❌ |
| **数据** | 测试数据 | 模拟真实数据 | 真实数据 |
| **Compose文件** | docker-compose.dev.yml | docker-compose.staging.yml | docker-compose.yml |
| **镜像标签** | 无需镜像 | :staging | :v1.0.0 |
| **配置** | .env.dev | .env.staging | .env.production |
| **域名** | localhost:8000 | staging.cloudlens.com | cloudlens.com |
| **日志级别** | DEBUG | INFO | WARNING |
| **备份** | 不需要 | 每日 | 实时+每日 |

---

## 二、Git工作流（GitFlow简化版）

### 分支策略

```
main (生产)
  ├── develop (开发主线)
  │     ├── feature/xxx (功能分支)
  │     └── fix/xxx (修复分支)
  ├── release/v1.x (发布分支)
  └── hotfix/xxx (紧急修复)
```

### 分支规则

| 分支类型 | 命名 | 来源 | 合并到 | 用途 |
|---------|------|------|--------|------|
| **main** | main | - | - | 生产代码，只接受合并 |
| **develop** | develop | main | main | 开发主线 |
| **feature** | feature/功能名 | develop | develop | 新功能开发 |
| **fix** | fix/问题描述 | develop | develop | Bug修复 |
| **release** | release/v1.x | develop | main + develop | 发布准备 |
| **hotfix** | hotfix/紧急问题 | main | main + develop | 生产紧急修复 |

### 工作流程

#### 1. 功能开发流程

```bash
# 1. 从develop创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/discount-analysis

# 2. 在开发环境工作（热重载）
docker compose -f docker-compose.dev.yml up -d
# 编写代码，实时测试...

# 3. 提交代码
git add .
git commit -m "feat: 添加折扣分析功能"

# 4. 推送并创建PR
git push origin feature/discount-analysis
# 在GitHub上创建 Pull Request: feature/discount-analysis → develop

# 5. Code Review通过后合并到develop
# 合并后自动触发CI/CD
```

#### 2. 发布流程

```bash
# 1. 从develop创建release分支
git checkout develop
git checkout -b release/v1.1.0

# 2. 在Staging环境测试
docker compose -f docker-compose.staging.yml up -d
# 完整功能测试...

# 3. 修复发现的问题（在release分支）
git commit -m "fix: 修复Staging发现的问题"

# 4. 测试通过后，合并到main并打标签
git checkout main
git merge release/v1.1.0
git tag -a v1.1.0 -m "Release v1.1.0: 折扣分析功能"
git push origin main --tags

# 5. 同时合并回develop
git checkout develop
git merge release/v1.1.0
git push origin develop

# 6. 部署到生产
# 自动触发或手动执行生产部署
```

#### 3. 紧急修复流程

```bash
# 1. 从main创建hotfix分支
git checkout main
git checkout -b hotfix/critical-bug

# 2. 快速修复并测试
docker compose -f docker-compose.staging.yml up -d
# 测试修复...

# 3. 合并到main并打标签
git checkout main
git merge hotfix/critical-bug
git tag -a v1.0.1 -m "Hotfix: 修复紧急Bug"
git push origin main --tags

# 4. 同时合并回develop
git checkout develop
git merge hotfix/critical-bug
git push origin develop

# 5. 立即部署到生产
```

---

## 三、Docker镜像管理

### 镜像标签策略

```
songqipeng/cloudlens-backend:
  ├── latest          # 指向最新稳定版
  ├── v1.1.0          # 版本标签（生产）
  ├── v1.0.1          # 旧版本（回滚用）
  ├── staging         # Staging环境测试版
  └── dev             # 开发版（可选）
```

### 镜像构建规范

```bash
# 开发环境：不构建镜像，直接挂载代码
docker compose -f docker-compose.dev.yml up -d

# Staging环境：构建staging标签
docker build -t songqipeng/cloudlens-backend:staging .
docker push songqipeng/cloudlens-backend:staging

# 生产环境：构建版本标签
docker build -t songqipeng/cloudlens-backend:v1.1.0 .
docker tag songqipeng/cloudlens-backend:v1.1.0 songqipeng/cloudlens-backend:latest
docker push songqipeng/cloudlens-backend:v1.1.0
docker push songqipeng/cloudlens-backend:latest
```

---

## 四、环境配置文件

### 配置文件结构

```
.
├── .env.example          # 配置模板
├── .env.dev              # 开发环境配置
├── .env.staging          # Staging环境配置
├── .env.production       # 生产环境配置（不提交Git）
└── .gitignore            # 忽略敏感配置
```

### .env.dev（开发环境）

```bash
# 应用配置
CLOUDLENS_ENVIRONMENT=development
CLOUDLENS_DEBUG=true

# 数据库配置
MYSQL_HOST=mysql-dev
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=dev123
MYSQL_DATABASE=cloudlens_dev

# Redis配置
REDIS_HOST=redis-dev
REDIS_PORT=6379

# 日志
LOG_LEVEL=DEBUG

# 镜像标签
IMAGE_TAG=dev
```

### .env.staging（Staging环境）

```bash
# 应用配置
CLOUDLENS_ENVIRONMENT=staging
CLOUDLENS_DEBUG=false

# 数据库配置
MYSQL_HOST=mysql-staging
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=staging_password
MYSQL_DATABASE=cloudlens_staging

# Redis配置
REDIS_HOST=redis-staging
REDIS_PORT=6379

# 日志
LOG_LEVEL=INFO

# 镜像标签
IMAGE_TAG=staging
```

### .env.production（生产环境）

```bash
# 应用配置
CLOUDLENS_ENVIRONMENT=production
CLOUDLENS_DEBUG=false

# 数据库配置（使用密钥管理）
MYSQL_HOST=mysql-prod
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=${MYSQL_PASSWORD_FROM_VAULT}
MYSQL_DATABASE=cloudlens

# Redis配置
REDIS_HOST=redis-prod
REDIS_PORT=6379

# 日志
LOG_LEVEL=WARNING

# 镜像标签
IMAGE_TAG=latest

# 备份
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"
```

---

## 五、CI/CD自动化

### GitHub Actions工作流

#### 1. 开发环境自动测试

```yaml
# .github/workflows/dev.yml
name: Dev Tests

on:
  push:
    branches: [ develop, feature/*, fix/* ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build dev image
        run: docker build -t cloudlens-backend:dev .

      - name: Run unit tests
        run: docker run cloudlens-backend:dev pytest tests/

      - name: Run linting
        run: docker run cloudlens-backend:dev flake8 cloudlens/
```

#### 2. Staging环境自动部署

```yaml
# .github/workflows/staging.yml
name: Deploy to Staging

on:
  push:
    branches: [ release/* ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build staging image
        run: |
          docker build -t songqipeng/cloudlens-backend:staging .
          docker push songqipeng/cloudlens-backend:staging

      - name: Deploy to Staging
        run: |
          ssh staging-server "cd /opt/cloudlens && \
            docker compose -f docker-compose.staging.yml pull && \
            docker compose -f docker-compose.staging.yml up -d"

      - name: Run smoke tests
        run: ./scripts/smoke-tests.sh staging
```

#### 3. 生产环境手动部署

```yaml
# .github/workflows/production.yml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production  # 需要手动批准

    steps:
      - uses: actions/checkout@v3

      - name: Get version
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/}" >> $GITHUB_OUTPUT

      - name: Build production image
        run: |
          docker build -t songqipeng/cloudlens-backend:${{ steps.version.outputs.VERSION }} .
          docker tag songqipeng/cloudlens-backend:${{ steps.version.outputs.VERSION }} \
                     songqipeng/cloudlens-backend:latest
          docker push songqipeng/cloudlens-backend:${{ steps.version.outputs.VERSION }}
          docker push songqipeng/cloudlens-backend:latest

      - name: Deploy to Production
        run: |
          ssh production-server "cd /opt/cloudlens && \
            docker compose pull && \
            docker compose up -d"

      - name: Health check
        run: |
          sleep 10
          curl --fail https://cloudlens.com/health || exit 1

      - name: Notify deployment
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -d '{"text":"✅ CloudLens ${{ steps.version.outputs.VERSION }} 部署成功"}'
```

---

## 六、质量保证机制

### 1. 代码质量检查

#### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "🔍 运行代码质量检查..."

# Python代码检查
echo "检查Python代码..."
docker run --rm -v $(pwd):/app \
  python:3.11-slim sh -c "
    pip install -q flake8 black &&
    flake8 cloudlens/ web/backend/ --max-line-length=120 &&
    black --check cloudlens/ web/backend/
  "

if [ $? -ne 0 ]; then
  echo "❌ 代码质量检查失败，请修复后再提交"
  exit 1
fi

echo "✅ 代码质量检查通过"
```

#### 代码格式化

```bash
# 自动格式化Python代码
docker run --rm -v $(pwd):/app python:3.11-slim \
  sh -c "pip install black && black cloudlens/ web/backend/"

# 自动修复代码风格
docker run --rm -v $(pwd):/app python:3.11-slim \
  sh -c "pip install autopep8 && autopep8 --in-place --recursive cloudlens/"
```

### 2. 自动化测试

#### 测试分层

```
单元测试 (Unit Tests)
  ├── 测试单个函数/方法
  ├── 速度快，覆盖率高
  └── 每次提交都运行

集成测试 (Integration Tests)
  ├── 测试模块间集成
  ├── 包含数据库交互
  └── PR合并前运行

端到端测试 (E2E Tests)
  ├── 测试完整用户流程
  ├── 模拟真实场景
  └── 发布前在Staging运行
```

#### 测试脚本

```bash
# tests/run_tests.sh
#!/bin/bash

echo "🧪 运行测试套件..."

# 1. 单元测试
echo "▶️  单元测试..."
docker compose -f docker-compose.test.yml run --rm backend \
  pytest tests/unit/ -v --cov=cloudlens --cov-report=html

# 2. 集成测试
echo "▶️  集成测试..."
docker compose -f docker-compose.test.yml run --rm backend \
  pytest tests/integration/ -v

# 3. API测试
echo "▶️  API测试..."
docker compose -f docker-compose.test.yml up -d
sleep 5
pytest tests/api/ -v
docker compose -f docker-compose.test.yml down

echo "✅ 所有测试通过！"
```

### 3. 数据库迁移管理

#### 使用Alembic管理数据库版本

```bash
# 初始化Alembic
alembic init migrations

# 创建迁移脚本
alembic revision -m "add discount_cache table"

# 升级到最新版本
alembic upgrade head

# 回滚到指定版本
alembic downgrade -1
```

#### 迁移脚本模板

```python
# migrations/versions/001_add_discount_cache.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'discount_cache',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('account_id', sa.String(100), nullable=False),
        sa.Column('cache_data', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Index('idx_discount_cache_account', 'account_id')
    )

def downgrade():
    op.drop_table('discount_cache')
```

---

## 七、发布检查清单

### Pre-Release Checklist

```markdown
## 发布前检查清单 v1.1.0

### 代码质量
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 代码覆盖率 > 80%
- [ ] 代码Review完成
- [ ] 无严重Bug

### 功能验证
- [ ] 新功能在Staging测试通过
- [ ] 回归测试通过（核心功能无影响）
- [ ] 性能测试通过
- [ ] 兼容性测试通过

### 文档更新
- [ ] API文档已更新
- [ ] CHANGELOG已更新
- [ ] 部署文档已更新
- [ ] 用户文档已更新

### 数据库
- [ ] 数据库迁移脚本已测试
- [ ] 数据备份已完成
- [ ] 回滚方案已准备

### 配置
- [ ] 环境变量已配置
- [ ] 密钥已更新
- [ ] 监控告警已配置

### 发布准备
- [ ] Release Notes已撰写
- [ ] 回滚计划已准备
- [ ] 发布时间已确定
- [ ] 团队已通知

### 签字确认
- [ ] 开发负责人: ________
- [ ] 测试负责人: ________
- [ ] 运维负责人: ________
```

---

## 八、快速命令参考

### 日常开发

```bash
# 启动开发环境
./scripts/dev.sh start

# 查看日志
./scripts/dev.sh logs

# 重启服务
./scripts/dev.sh restart

# 运行测试
./scripts/dev.sh test

# 停止环境
./scripts/dev.sh stop
```

### 测试发布

```bash
# 构建Staging镜像
./scripts/build.sh staging

# 部署到Staging
./scripts/deploy.sh staging

# 运行烟雾测试
./scripts/smoke-test.sh staging

# 查看Staging日志
./scripts/logs.sh staging
```

### 生产发布

```bash
# 创建发布分支
git checkout -b release/v1.1.0

# 构建生产镜像
./scripts/build.sh production v1.1.0

# 备份生产数据
./scripts/backup.sh production

# 部署到生产
./scripts/deploy.sh production v1.1.0

# 健康检查
./scripts/health-check.sh production

# 回滚（如需要）
./scripts/rollback.sh production v1.0.0
```

---

## 九、监控和告警

### 监控指标

```yaml
# 应用监控
- API响应时间
- API错误率
- 并发请求数
- 数据库连接数

# 系统监控
- CPU使用率
- 内存使用率
- 磁盘使用率
- 网络流量

# 业务监控
- 账单查询次数
- 折扣分析请求数
- 用户活跃度
- 数据准确性
```

### 告警规则

```yaml
# Prometheus告警规则示例
groups:
  - name: cloudlens_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "API错误率过高"

      - alert: SlowResponse
        expr: http_request_duration_seconds > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API响应时间过长"
```

---

## 十、总结

### 核心原则

1. **分层明确**: Dev → Staging → Production
2. **代码审查**: 所有代码必须经过Review
3. **自动化测试**: 多层次测试保证质量
4. **版本控制**: Git分支管理清晰
5. **镜像标签**: 环境和版本严格区分
6. **配置分离**: 环境配置独立管理
7. **CI/CD**: 自动化部署流程
8. **监控告警**: 实时监控系统状态
9. **文档同步**: 文档与代码同步更新
10. **回滚准备**: 任何发布都有回滚方案

### 优势

✅ **开发效率**: 热重载快速迭代
✅ **质量保证**: 多层测试机制
✅ **发布稳定**: 严格的发布流程
✅ **数据安全**: 分层数据隔离
✅ **快速回滚**: 版本管理清晰
✅ **团队协作**: 流程规范统一

### 下一步

1. [ ] 创建docker-compose.staging.yml
2. [ ] 配置GitHub Actions CI/CD
3. [ ] 编写自动化测试
4. [ ] 配置监控告警
5. [ ] 编写操作手册
6. [ ] 团队培训

---

**让开发更规范，让发布更可靠！** 🚀
