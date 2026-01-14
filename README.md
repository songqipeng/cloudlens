# CloudLens | 多云资源治理与分析平台

<div align="center">

**统一视图 · 智能分析 · 安全合规 · 降本增效**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

[快速开始](#-快速开始) | [核心能力](#-核心能力) | [技术架构](#-技术架构) | [在线文档](https://songqipeng.github.io/cloudlens/)

</div>

---

## 🚀 项目简介

**CloudLens** 是一款专为 FinOps 和安全团队打造的企业级多云治理平台。它集成了强大的 **CLI 命令行工具** 和极致体验的 **Web 可视化界面**，旨在解决云原生时代的资源散乱、成本失控与合规难题。

### 为什么选择 CloudLens?
*   **统一抽象**：通过标准化的数据模型，一个界面通管 阿里云、腾讯云 及 AWS。
*   **AI 赋能**：利用 Prophet 机器学习模型预测 90 天成本趋势，洞察折扣异常。
*   **安全加固**：深度适配 CIS Benchmark 基线检查，毫秒级识别公网暴露风险。
*   **极客性能**：基于 Python 并发 SDK 架构，配合 MySQL 智能缓存实现海量资源秒级加载。

---

## 🔥 核心能力

| 功能模块 | 描述 | 技术亮点 |
| :--- | :--- | :--- |
| **智能分析** | 识别闲置资源与降本机会 | 多指标复合阈值引擎 |
| **成本预测** | 预测未来 3 个月成本走向与区间 | Prophet 机器学习模型 |
| **安全审计** | CIS 合规性检查与 IAM 审计 | 自动化安全扫描路径 |
| **统一终端** | 现代响应式看板，支持中英双语 | Next.js 14 + Tailwind CSS |
| **报告引擎** | 导出专业级 Excel/HTML/JSON 报告 | 并行数据聚合与渲染 |

---

## 🛠️ 快速开始

### 1. 安装环境
```bash
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens
pip install -r requirements.txt
pip install prophet  # (可选) 用于 AI 预测功能
```

### 2. 配置账号
```bash
./cl config add --provider aliyun --name prod --region cn-hangzhou --ak YOUR_AK --sk YOUR_SK
```

### 3. CLI 命令行操作
```bash
./cl analyze idle --account prod       # 扫描闲置资源 (搞定浪费)
./cl analyze security --cis --account prod # 安全合规检查
./cl analyze forecast --days 90        # AI 预测未来支出
```

### 4. 启动 Web 界面
```bash
./scripts/start_web.sh
```
访问 `http://localhost:3000` 即可开启可视化治理之旅。

---

## 🏗️ 技术架构

CloudLens 为规模化运行而生：
*   **核心层**：标准化 Python 包结构，采用 Provider 设计模式。
*   **性能层**：基于 `Concurrent.futures` 的多账号并发 SDK 调用。
*   **存储层**：MySQL 强持久化数据与 24 小时自动 TTL 缓存机制。
*   **展现层**：Next.js 14 实现的毛玻璃风格 UI，深度集成国际化支持。

---

## 📖 文档与规划

*   **[官方首页 & 文档中心](https://songqipeng.github.io/cloudlens/)**
*   **[视频演示教程](https://songqipeng.github.io/cloudlens/video.html)**
*   **[2026 综合路线图](./docs/COMPREHENSIVE_ROADMAP_2026.md)**

---

## 🤝 参与贡献

我们欢迎任何形式的贡献！请阅读 [贡献指南](CONTRIBUTING.md) 了解更多。

---

## 📄 许可证

本项目采用 MIT 许可证，详情请参阅 [LICENSE](LICENSE) 文件。

<div align="right">
  <i>让云治理更简单、更高效。</i>
</div>
