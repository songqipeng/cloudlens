# CloudLens CLI - 多云资源治理工具

<div align="center">

**统一视图 · 智能分析 · 安全合规 · 降本增效**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

## 🚀 项目简介

**CloudLens CLI** 是一款企业级多云资源治理与分析工具，专为运维团队打造。通过统一的命令行界面管理阿里云、腾讯云等多个云平台的资源，提供智能成本分析、安全合规检查和专业报告生成能力。

### 核心特性（当前版本）

- 🌐 **多云统一管理** - 支持阿里云、腾讯云（AWS/火山引擎规划中）
- 💰 **基础成本洞察** - 闲置分析（当前覆盖阿里云 ECS）、续费提醒
- 🔒 **基础安全检查** - 公网暴露与未绑定 EIP 统计，简易权限审计
- 🏷️ **标签治理** - 标签覆盖率分析、缺失标签提示
- 📊 **报告导出** - Excel/HTML/JSON/CSV，多账号并发查询
- 🔐 **零风险设计** - 只读操作，强制 Keyring 存储密钥

## 📋 支持的资源类型

### 已实现
- **阿里云**: ECS, RDS, Redis, OSS, NAS, VPC, EIP, SLB
- **腾讯云**: CVM, CDB, Redis, COS, VPC

### 规划中（未实现）
- 阿里云: MongoDB, ClickHouse, PolarDB, ACK, ECI
- AWS/火山引擎: EC2, RDS, S3 等

## 🛠️ 快速开始

### 1. 安装

```bash
git clone <repository>
cd aliyunidle
pip install -r requirements.txt
```

- 如需生成 PDF 报告，额外安装 weasyprint 或使用本地 wkhtmltopdf

### 2. 配置账号

```bash
# 添加阿里云账号
python3 main_cli.py config add \
  --provider aliyun \
  --name prod \
  --region cn-hangzhou \
  --ak YOUR_AK \
  --sk YOUR_SK

# 查看已配置账号
python3 main_cli.py config list

# 或使用封装命令（会记住最近一次使用的账号；账号也可作为位置参数）
./cloudlens config add
./cloudlens query prod ecs   # 指定账号
./cloudlens query ecs        # 复用上次账号

# 简写版（可执行文件同目录下的 cl）
./cl query ecs
./cl query prod ecs
```

### 3. 开始使用

```bash
# 查询ECS实例
python3 main_cli.py query ecs --account prod

# 生成Excel报告
python3 main_cli.py report generate --account prod --format excel

# 分析闲置资源
python3 main_cli.py analyze idle --account prod
```

## 📖 使用指南

### 资源查询

```bash
# 查询各类资源
python3 main_cli.py query ecs --account prod
python3 main_cli.py query rds --account prod
python3 main_cli.py query vpc --account prod

# 导出为JSON/CSV
python3 main_cli.py query ecs --account prod --format json --output ecs.json
python3 main_cli.py query ecs --account prod --format csv --output ecs.csv

# 并发查询多账号
python3 main_cli.py query ecs --concurrent

# 高级筛选
python3 main_cli.py query ecs --status Running --region cn-hangzhou
python3 main_cli.py query ecs --filter "charge_type=PrePaid AND expire_days<7"
```

### 分析功能

```bash
# 闲置资源分析
python3 main_cli.py analyze idle --account prod --days 14

# 续费提醒
python3 main_cli.py analyze renewal --account prod --days 30

# 成本分析
python3 main_cli.py analyze cost --account prod

# 安全合规检查
python3 main_cli.py analyze security --account prod

# 标签治理
python3 main_cli.py analyze tags --account prod
```

### 报告生成

```bash
# 生成Excel报告
python3 main_cli.py report generate --account prod --format excel

# 生成HTML报告
python3 main_cli.py report generate --account prod --format html

# 包含闲置分析
python3 main_cli.py report generate --account prod --format excel --include-idle
```

### 网络拓扑

```bash
# 生成网络拓扑图（Mermaid格式）
python3 main_cli.py topology generate --account prod --output topology.md
```

### 权限审计

```bash
# 审计账号权限
python3 main_cli.py audit permissions --account prod
```

## 📁 项目结构

```
aliyunidle/
├── main_cli.py                 # CLI主入口
├── core/                       # 核心模块
│   ├── config.py              # 配置管理
│   ├── provider.py            # 云厂商抽象层
│   ├── idle_detector.py       # 闲置检测
│   ├── cost_analyzer.py       # 成本分析
│   ├── security_compliance.py # 安全合规
│   ├── tag_analyzer.py        # 标签分析
│   ├── topology_generator.py  # 拓扑生成
│   ├── report_generator.py    # 报告生成
│   └── filter_engine.py       # 高级筛选
├── providers/                  # 云厂商实现
│   ├── aliyun/                # 阿里云
│   └── tencent/               # 腾讯云
├── models/                     # 数据模型
│   └── resource.py            # 统一资源模型
├── scripts/                    # 独立脚本
│   ├── analyze_all_tenants.py
│   ├── check_current_identity.py
│   └── ...
├── tests/                      # 测试用例
│   └── test_cli_flow.py       # CLI流程测试
└── docs/                       # 文档
    ├── PRODUCT_INTRODUCTION.md
    ├── TECHNICAL_ARCHITECTURE.md
    └── USER_GUIDE.md
```

## 🎯 典型应用场景

### 场景1：每周成本优化会议

```bash
# 生成Excel报告（含闲置分析）
python3 main_cli.py report generate --account prod --format excel --include-idle

# 查看即将到期资源
python3 main_cli.py analyze renewal --days 30

# 耗时：5分钟（传统方式需4-6小时）
```

### 场景2：安全合规审计

```bash
# 权限审计
python3 main_cli.py audit permissions --account prod

# 公网暴露检测
python3 main_cli.py analyze security --account prod

# 标签合规检查
python3 main_cli.py analyze tags --account prod
```

### 场景3：资源盘点

```bash
# 并发查询所有账号、所有资源
python3 main_cli.py query ecs --concurrent --format csv > all_ecs.csv
python3 main_cli.py query rds --concurrent --format csv > all_rds.csv

# 生成网络拓扑
python3 main_cli.py topology generate --account prod
```

## 📊 分析标准

### ECS闲置标准（或关系）
- CPU利用率 < 5%
- 内存利用率 < 20%
- Load Average < vCPU * 5%
- 磁盘IOPS < 100
- EIP带宽使用率 < 峰值 * 10%

> 当前闲置分析仅对阿里云 ECS 实现（基于 CloudMonitor）。RDS 及其他资源的闲置检测仍在规划，标准以文档为准。

更多说明详见 [USER_GUIDE.md](USER_GUIDE.md)

## 🔐 安全性

- ✅ **强制Keyring存储密钥** - 密钥不会明文保存
- ✅ **零变更机制** - 代码层面无任何Write/Delete API
- ✅ **权限自动审计** - 检测高危权限
- ✅ **本地运行** - 数据不出网

## 🚀 性能优化

- ✅ **并发查询** - 多账号并发，速度提升3倍
- ✅ **懒加载SDK** - 启动快
- ✅ **智能缓存** - 减少API调用

## 📚 文档

- [产品介绍](PRODUCT_INTRODUCTION.md) - 详细的产品定位和功能介绍
- [技术架构](TECHNICAL_ARCHITECTURE.md) - 系统架构和设计理念
- [用户指南](USER_GUIDE.md) - 完整的使用手册
- [开发日志](CHANGELOG.md) - 版本更新记录

## 🧪 测试

```bash
# 运行所有测试
python3 -m pytest tests/

# 运行CLI流程测试
python3 -m pytest tests/test_cli_flow.py
```

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

本项目采用MIT许可证。

---

**立即开始使用，让云资源管理更简单、更高效！**
