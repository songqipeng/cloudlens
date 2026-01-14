# CloudLens

<div align="center">

**Unified Multi-Cloud Governance · Smart AI Analysis · Security Compliance · Cost Optimization**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

[Quick Start](#-quick-start) | [Core Capabilities](#-core-capabilities) | [Architecture](#-technical-architecture) | [Documentation](https://songqipeng.github.io/cloudlens/)

</div>

---

## 🚀 Overview

**CloudLens** is a professional-grade multi-cloud governance platform designed for FinOps and Security teams. It provides both a powerful **CLI** for developers and a stunning **Web UI** for stakeholders. 

### Why CloudLens?
*   **Unified Interface**: Manage AWS, Aliyun, and Tencent Cloud through a single data model.
*   **AI-Powered FinOps**: Forecast 90-day costs and detect discount trends using Prophet ML.
*   **Hardened Security**: Audit resources against CIS Benchmarks and detect public exposures instantly.
*   **High Performance**: Parallelized SDK processing with MySQL-backed intelligent caching.

---

## 🔥 Core Capabilities

| Feature | Description | Technical Highlight |
| :--- | :--- | :--- |
| **Smart Analysis** | Detect idle resources & optimization opportunities | Multi-metric threshold engine |
| **Cost Forecasting** | Predicted 3-month cost trends with confidence intervals | Prophet Machine Learning |
| **Security Audit** | CIS Benchmark compliance & IAM permission audit | Automated security scanning |
| **Unified Portal** | Modern responsive dashboard with Chinese/English support | Next.js 14 + Tailwind CSS |
| **Report Engine** | Export professional Excel/HTML/JSON audit reports | Parallel data aggregation |

---

## 🛠️ Quick Start

### 1. Installation
```bash
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens
pip install -r requirements.txt
pip install prophet  # Optional for AI forecast
```

### 2. Configure Account
```bash
./cl config add --provider aliyun --name prod --region cn-hangzhou --ak YOUR_AK --sk YOUR_SK
```

### 3. CLI Power Use
```bash
./cl analyze idle --account prod       # Find wasted money
./cl analyze security --cis --account prod # Security audit
./cl analyze forecast --days 90        # AI Predict future spend
```

### 4. Launch Web Portal
```bash
./scripts/start_web.sh
```
Visit `http://localhost:3000` to explore the dashboard.

---

## 🏗️ Technical Architecture

CloudLens is built for scale and reliability:
*   **Core**: Standardized Python package structure with modular providers.
*   **Performance**: `Concurrent.futures` based parallel SDK fetching.
*   **Storage**: MySQL for structured data & cache, with 24h automatic TTL.
*   **Frontend**: Next.js 14 featuring Glassmorphism UI and i18n support.

---

## 📖 Documentation & Roadmap

*   **[Full Documentation Portal](https://songqipeng.github.io/cloudlens/)**
*   **[Video Tutorials](https://songqipeng.github.io/cloudlens/video.html)**
*   **[2026 Comprehensive Roadmap](./docs/COMPREHENSIVE_ROADMAP_2026.md)**

---

## 🤝 Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md).

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

<div align="right">
  <i>Make cloud governance simple and efficient.</i>
</div>
