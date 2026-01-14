# CloudLens - 多云资源治理与分析平台

<div align="center">

**统一视图 · 智能分析 · 安全合规 · 降本增效**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.1.0-brightgreen.svg)]()

[快速开始](#-快速开始) • [视频教程](#-视频教程) • [功能特性](#-功能特性) • [使用文档](#-文档) • [产品能力](#-产品能力)

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

## 📹 视频教程

**NEW!** 3分59秒 Web 界面完整使用指南视频已发布！

**📥 [下载视频文件](./docs/web_guide_5min.mp4)** (8.8 MB)

**视频内容**：
- ✅ 9个核心功能完整演示（资源查询、成本分析、安全合规等）
- ✅ 真实操作流程展示（敏感信息已脱敏）
- ✅ 中文专业讲解，音画同步
- ✅ Full HD 1080p，无黑屏，页面完整展示

> 💡 **观看方式**：
> - 📥 **下载观看**：点击上方链接下载到本地，使用任意视频播放器观看
> - 🌐 **在线播放**：下载后可直接拖拽到浏览器窗口播放
> - 📱 **移动设备**：下载后可在手机/平板上观看

📖 **详细说明**：[视频使用指南](./docs/VIDEO_GUIDE.md)

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

### 📚 文档中心
**完整文档索引**: [docs/README.md](./docs/README.md) - 按角色分类的文档导航

### 🎬 视频教程
- **[Web 使用指南视频](./docs/web_guide_5min.mp4)** - 🆕 **3分59秒完整教程视频（需下载观看，8.8 MB）**
- [视频使用指南](./docs/VIDEO_GUIDE.md) - 视频功能说明和使用方法
- [视频技术报告](./docs/WEB_GUIDE_5MIN_REPORT.md) - 视频制作技术细节

### 📘 快速开始
- [CLI 快速开始](./docs/QUICKSTART.md) - 命令行工具 5分钟上手
- [Web 快速开始](./docs/WEB_QUICKSTART.md) - Web 界面快速部署
- [快速参考](./docs/QUICK_REFERENCE.md) - 常用命令一页速查
- [Shell 补全](./docs/shell_completion.md) - Bash/Zsh 自动补全配置

### 📖 产品文档
- [产品介绍](./docs/PRODUCT_INTRODUCTION.md) - 产品定位、核心价值和应用场景
- [产品能力](./docs/PRODUCT_CAPABILITIES.md) - 完整功能特性列表
- [用户手册](./docs/USER_GUIDE.md) - 详细使用说明

### 🔧 功能指南
- [账单自动获取](./docs/BILL_AUTO_FETCH_GUIDE.md) - 配置自动账单获取
- [折扣分析指南](./docs/DISCOUNT_ANALYSIS_GUIDE.md) - 折扣趋势分析功能

### 🏗️ 开发文档
- [开发指南](./docs/DEVELOPMENT_GUIDE.md) - 开发环境配置和流程
- [技术架构](./docs/TECHNICAL_ARCHITECTURE.md) - 系统架构和设计
- [项目结构](./docs/PROJECT_STRUCTURE.md) - 目录结构说明
- [API 参考](./docs/API_REFERENCE.md) - 后端 API 文档
- [贡献指南](./docs/CONTRIBUTING.md) - 如何参与贡献
- [插件开发](./docs/PLUGIN_DEVELOPMENT.md) - 自定义插件开发
- [测试指南](./docs/TESTING_GUIDE.md) - 测试策略和方法

### 🗺️ 规划文档
- [2026 综合路线图](./docs/COMPREHENSIVE_ROADMAP_2026.md) - 产品战略规划
- [2026 开发计划](./docs/DEVELOPMENT_PLAN_2026.md) - 详细开发计划
- [更新日志](./docs/CHANGELOG.md) - 版本发布记录
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
