# CloudLens - 多云资源治理与分析平台

<div align="center">

**统一视图 · 智能分析 · 安全合规 · 降本增效**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.1.0-brightgreen.svg)]()

[快速开始](#-快速开始) • [功能特性](#-功能特性) • [使用文档](#-文档) • [产品能力](#-产品能力)

</div>

---

## 🚀 项目简介

**CloudLens** 是一款企业级多云资源治理与分析平台，提供 **CLI 命令行工具** 和 **Web 可视化界面** 两种使用方式。通过统一的接口管理阿里云、腾讯云等多个云平台的资源，提供智能成本分析、安全合规检查和专业报告生成能力。

### 核心价值

- 🌐 **统一视图** - 一个工具管理多个云平台，告别频繁切换控制台
- 💰 **智能分析** - AI 成本预测、折扣趋势分析，降低 30%+ 云成本
- 🔒 **安全合规** - CIS Benchmark、公网暴露检测、权限审计
- 📊 **降本增效** - 闲置资源识别、自动修复、专业报告生成

---

## ✨ 功能特性

### 核心能力

#### 🌐 多云统一管理
- 支持阿里云、腾讯云（可扩展 AWS、火山引擎）
- 统一的资源数据模型，屏蔽云平台差异
- 支持多账号、多区域管理
- CLI 和 Web 两种使用方式

#### 💰 智能成本分析
- **成本趋势分析**：环比/同比增长，按类型/区域统计
- **AI 成本预测**：基于 Prophet ML 模型，预测未来 90 天成本
- **折扣趋势分析**：分析账单折扣变化，支持产品/合同/实例维度
- **预算管理**：支持月度/季度/年度预算，多级告警阈值
- **成本分配**：支持多维度成本分配规则

#### 🔒 安全合规检查
- **CIS Benchmark**：10+ 安全基线检查，覆盖 IAM/网络/数据/审计
- **公网暴露检测**：识别暴露在公网的资源
- **权限审计**：检查账号权限，识别高危权限
- **安全组审计**：分析安全组规则风险

#### 🤖 自动化修复
- **批量打标签**：自动为资源打标签，支持干运行模式
- **修复历史**：完整的修复操作审计日志
- **安全组修复**：修复安全组规则（开发中）

#### 📊 专业报告生成
- **Excel 报告**：多 Sheet 格式，包含资源清单、闲置分析、成本分析
- **HTML 报告**：精美样式，适合在线分享
- **JSON/CSV 导出**：机器可读，集成到其他系统

#### ⚡ 高性能查询
- **并发查询**：多账号并发，速度提升 3-5 倍
- **智能缓存**：MySQL 缓存表，24 小时 TTL
- **高级筛选**：支持 SQL-like 语法和 JMESPath

### Web 界面特性

- 🎨 **现代化 UI**：Finout 风格界面，响应式布局，支持深色模式
- 🌍 **国际化**：支持中英文双语切换
- 📈 **实时数据**：Dashboard 实时展示关键指标
- 🔍 **高级分析**：折扣趋势、成本分析、安全合规可视化
- 📱 **响应式设计**：支持桌面和移动设备

---

## 📋 支持的资源类型

### 阿里云
ECS、RDS、Redis、OSS、NAS、VPC、EIP、SLB、MongoDB、ACK、ClickHouse、PolarDB、ECI、Disk 等

### 腾讯云
CVM、CDB、Redis、COS、VPC 等

---

## 🛠️ 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/songqipeng/aliyunidle.git
cd aliyunidle

# 安装 Python 依赖
pip install -r requirements.txt

# 可选：安装 AI 预测依赖
pip install prophet
```

### 2. 配置账号

```bash
# 添加阿里云账号
./cl config add \
  --provider aliyun \
  --name prod \
  --region cn-hangzhou \
  --ak YOUR_AK \
  --sk YOUR_SK

# 查看已配置账号
./cl config list
```

### 3. 开始使用

#### CLI 命令行方式

```bash
# 查询 ECS 实例
./cl query ecs --account prod

# 分析闲置资源
./cl analyze idle --account prod

# 成本趋势分析
./cl analyze cost --account prod --trend

# AI 成本预测
./cl analyze forecast --account prod --days 90

# 折扣趋势分析
./cl analyze discount --export

# CIS 安全合规检查
./cl analyze security --account prod --cis

# 自动打标签（干运行）
./cl remediate tags --account prod
```

#### Web 界面方式

```bash
# 启动后端 API 服务
cd web/backend
python -m uvicorn main:app --reload --port 8000

# 启动前端开发服务器（新终端）
cd web/frontend
npm install
npm run dev
```

访问 http://localhost:3000 即可使用 Web 界面。

详细说明请参考 [Web 快速开始指南](docs/WEB_QUICKSTART.md)

---

## 📖 文档

### 核心文档
- [项目深度分析](PROJECT_DEEP_ANALYSIS.md) - 🆕 **完整的代码库深度分析、架构剖析、优化建议和发展方向**
- [产品能力总览](PRODUCT_CAPABILITIES.md) - 完整的产品功能列表
- [产品介绍](PRODUCT_INTRODUCTION.md) - 详细的产品定位和功能介绍
- [技术架构](TECHNICAL_ARCHITECTURE.md) - 系统架构和设计理念
- [项目结构](PROJECT_STRUCTURE.md) - 详细的目录结构和模块说明
- [用户指南](USER_GUIDE.md) - 完整的使用手册
- [快速开始](QUICKSTART.md) - 快速上手指南
- [快速参考](QUICK_REFERENCE.md) - 一页纸命令速查
- [更新日志](CHANGELOG.md) - 版本更新记录

### Web 界面文档
- [Web 快速开始](docs/WEB_QUICKSTART.md) - Web 界面安装和使用指南
- [折扣分析指南](docs/DISCOUNT_ANALYSIS_GUIDE.md) - 折扣分析功能详细说明
- [账单自动获取](docs/BILL_AUTO_FETCH_GUIDE.md) - 账单自动获取功能说明

### 开发文档
- [贡献指南](CONTRIBUTING.md) - 如何参与项目开发
- [插件开发](docs/PLUGIN_DEVELOPMENT.md) - 如何开发自定义插件
- [Shell 自动补齐](docs/shell_completion.md) - Shell 自动补齐功能说明

---

## 🎯 典型应用场景

### 场景 1：每周成本优化会议

```bash
# 生成 Excel 报告（含闲置分析）
cl report generate --account prod --format excel --include-idle

# 查看即将到期资源
cl analyze renewal --days 30
```

**效果**：节省 95% 时间，数据更准确

### 场景 2：安全合规审计

```bash
# 权限审计
cl audit permissions --account prod

# 公网暴露检测
cl analyze security --account prod

# CIS 合规检查
cl analyze security --account prod --cis
```

**效果**：系统化、可追溯、自动化

### 场景 3：资源盘点

```bash
# 并发查询所有账号、所有资源
cl query ecs --concurrent --format csv > all_ecs.csv
cl query rds --concurrent --format csv > all_rds.csv
```

**效果**：完整、快速、可视化

---

## 🔐 安全性

- ✅ **强制 Keyring 存储密钥** - 密钥不会明文保存
- ✅ **零变更机制** - 代码层面无任何 Write/Delete API
- ✅ **权限自动审计** - 检测高危权限
- ✅ **本地运行** - 数据不出网

---

## 🚀 性能优化

- ✅ **并发查询** - 多账号并发，速度提升 3-5 倍
- ✅ **智能缓存** - MySQL 缓存表，24 小时 TTL
- ✅ **懒加载 SDK** - 启动快

---

## 🧪 测试

```bash
# 运行所有测试
python3 -m pytest tests/

# 运行 CLI 流程测试
python3 -m pytest tests/test_cli_flow.py
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

详见 [贡献指南](CONTRIBUTING.md)

---

## 📄 许可证

本项目采用 MIT 许可证。

---

## 📞 联系方式

- GitHub Issues: [提交问题](https://github.com/songqipeng/aliyunidle/issues)
- 文档: [查看文档](https://github.com/songqipeng/aliyunidle/tree/main/docs)

---

**立即开始使用，让云资源管理更简单、更高效！**
