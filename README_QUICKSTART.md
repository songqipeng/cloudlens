# CloudLens - 云成本管理平台

> 一键部署，轻松管理云成本

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)

---

## ⚡️ 快速开始

### 对于用户（生产环境）

```bash
# 克隆项目
git clone https://github.com/your-org/cloudlens.git
cd cloudlens

# 一键启动
./quick-start.sh

# 选择选项 2 (生产环境)
# 按提示配置账号信息
# 等待启动完成

# 访问
open http://localhost:3000
```

**就这么简单！** 🎉

### 对于开发者（开发环境）

```bash
# 克隆项目
git clone https://github.com/your-org/cloudlens.git
cd cloudlens

# 一键启动开发环境
./quick-start.sh

# 选择选项 1 (开发环境)
# 等待启动完成

# 访问
open http://localhost:3000

# 代码修改会自动重载 ✨
```

---

## 📋 系统要求

- Docker Desktop (Mac/Windows) 或 Docker Engine (Linux)
- 8GB RAM
- 20GB 可用磁盘空间

---

## 🎯 核心功能

### 💰 账单管理
- 多账号管理
- 账单查询与分析
- 历史数据追溯

### 📊 折扣分析
- 折扣趋势分析
- 产品维度统计
- 合同折扣追踪

### 📈 成本分析
- 成本趋势预测
- 产品成本分布
- 区域成本对比

### 🔔 告警管理
- 自定义告警规则
- 多渠道通知
- 告警历史记录

### 📑 报告生成
- 一键生成报告
- 多种导出格式
- 自动化定时报告

---

## 🛠️ 开发者工具

### 快速命令

```bash
# 启动开发环境
./scripts/dev.sh start

# 查看日志
./scripts/dev.sh logs

# 运行测试
./scripts/dev.sh test

# 代码检查
./scripts/dev.sh lint

# 代码格式化
./scripts/dev.sh format

# 进入容器
./scripts/dev.sh shell

# 数据库操作
./scripts/dev.sh db backup
./scripts/dev.sh db connect

# 查看帮助
./scripts/dev.sh help
```

### 构建镜像

```bash
# Staging环境
./scripts/build.sh staging

# 生产环境
./scripts/build.sh production v1.0.0
```

---

## 📂 项目结构

```
cloudlens/
├── cloudlens/              # 核心业务逻辑
│   ├── core/              # 核心模块
│   └── providers/         # 云服务商适配
├── web/
│   ├── backend/           # FastAPI后端
│   └── frontend/          # Next.js前端
├── scripts/               # 运维脚本
├── migrations/            # 数据库迁移
├── docker-compose.yml     # 生产环境配置
├── docker-compose.dev.yml # 开发环境配置
├── quick-start.sh         # 一键启动脚本 ⭐️
└── README.md              # 项目文档
```

---

## 🔧 配置说明

### 账号配置

配置文件位置: `~/.cloudlens/config.json`

```json
{
  "accounts": [
    {
      "name": "aliyun-prod",
      "provider": "aliyun",
      "access_key_id": "YOUR_ACCESS_KEY_ID",
      "access_key_secret": "YOUR_ACCESS_KEY_SECRET",
      "region": "cn-hangzhou"
    }
  ]
}
```

### 环境变量

```bash
# 数据库配置
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=cloudlens

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379

# 应用配置
CLOUDLENS_ENVIRONMENT=production
CLOUDLENS_DEBUG=false
```

---

## 🚀 部署流程

### 开发流程

```
编写代码 → 本地测试 → 提交PR → Code Review → 合并到develop
```

### 发布流程

```
develop → release分支 → Staging测试 → 合并到main → 打Tag → 生产部署
```

详见：[开发流程文档](DEVELOPMENT_WORKFLOW_STANDARD.md)

---

## 📊 API文档

启动服务后访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🧪 测试

```bash
# 运行所有测试
./scripts/dev.sh test

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=cloudlens --cov-report=html
```

---

## 📝 常见问题

### 端口被占用？

```bash
# 查看端口占用
lsof -i :8000

# 停止占用的进程
lsof -ti:8000 | xargs kill -9
```

### 数据库连接失败？

```bash
# 检查MySQL服务状态
docker compose ps mysql

# 查看MySQL日志
docker compose logs mysql
```

### 镜像拉取失败？

```bash
# 使用国内镜像源
# 编辑 /etc/docker/daemon.json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn"
  ]
}

# 重启Docker
sudo systemctl restart docker
```

---

## 📚 文档

- [完整文档](https://docs.cloudlens.com)
- [API参考](https://api.cloudlens.com)
- [开发指南](DEVELOPMENT_WORKFLOW_STANDARD.md)
- [部署指南](DEPLOYMENT.md)
- [测试计划](TESTING_PLAN.md)

---

## 🤝 贡献

欢迎贡献代码！请查看 [贡献指南](CONTRIBUTING.md)

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交代码 (`git commit -m 'feat: Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE)

---

## 💬 联系我们

- 问题反馈: [GitHub Issues](https://github.com/your-org/cloudlens/issues)
- 邮件: support@cloudlens.com
- 文档: https://docs.cloudlens.com

---

## ⭐️ Star History

如果这个项目对你有帮助，请给我们一个 Star！

---

**让云成本管理变得简单！** 🚀
