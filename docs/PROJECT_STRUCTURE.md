# CloudLens 项目结构

本文档详细说明 CloudLens 项目的目录结构和各模块的职责。

---

## 📁 目录结构

```
cloudlens/
├── cli/                          # CLI命令行工具
│   ├── main.py                  # CLI主入口
│   ├── utils.py                 # CLI工具函数
│   └── commands/                # 命令模块
│       ├── analyze_cmd.py      # 分析命令（闲置、成本、折扣、安全等）
│       ├── bill_cmd.py          # 账单命令（获取、测试）
│       ├── cache_cmd.py         # 缓存管理命令
│       ├── config_cmd.py        # 配置管理命令
│       ├── query_cmd.py         # 资源查询命令
│       ├── remediate_cmd.py     # 修复命令（标签、安全组）
│       └── misc_cmd.py          # 其他命令（Dashboard、REPL、Scheduler）
│
├── core/                         # 核心业务逻辑
│   ├── database.py              # 数据库抽象层（MySQL/SQLite）
│   ├── config.py                # 配置管理
│   ├── provider.py              # 云厂商抽象基类
│   ├── async_provider.py        # 异步Provider基类
│   ├── cache.py                 # 缓存管理器（MySQL缓存表）
│   ├── bill_storage.py          # 账单存储管理
│   ├── bill_fetcher.py          # 账单获取（BSS OpenAPI）
│   ├── dashboard_manager.py     # 仪表盘管理
│   ├── budget_manager.py        # 预算管理
│   ├── alert_manager.py         # 告警管理
│   ├── alert_engine.py          # 告警引擎
│   ├── virtual_tags.py          # 虚拟标签管理
│   ├── cost_allocation.py       # 成本分配
│   ├── ai_optimizer.py          # AI优化建议
│   ├── idle_detector.py         # 闲置资源检测
│   ├── cost_analyzer.py         # 成本分析
│   ├── cost_trend_analyzer.py   # 成本趋势分析
│   ├── cost_predictor.py        # 成本预测（Prophet ML）
│   ├── discount_analyzer.py    # 折扣分析（基础）
│   ├── discount_analyzer_advanced.py  # 高级折扣分析
│   ├── discount_analyzer_db.py # 折扣分析（数据库版）
│   ├── security_compliance.py  # 安全合规检查
│   ├── cis_compliance.py        # CIS基准检查
│   ├── tag_analyzer.py          # 标签分析
│   ├── report_generator.py     # 报告生成
│   ├── filter_engine.py         # 高级筛选引擎
│   ├── rules_manager.py         # 规则管理
│   ├── remediation_engine.py   # 修复引擎
│   ├── notification_service.py  # 通知服务（邮件、Webhook、短信）
│   ├── services/                # 服务层
│   │   └── analysis_service.py  # 分析服务
│   └── ...                      # 其他核心模块
│
├── providers/                    # 云厂商实现
│   ├── aliyun/                  # 阿里云Provider
│   │   ├── provider.py          # 同步Provider
│   │   └── async_provider.py    # 异步Provider
│   └── tencent/                 # 腾讯云Provider
│       └── provider.py
│
├── resource_modules/             # 资源分析模块
│   ├── ecs_analyzer.py          # ECS分析器
│   ├── rds_analyzer.py          # RDS分析器
│   ├── redis_analyzer.py       # Redis分析器
│   └── ...                      # 其他资源分析器
│
├── web/                          # Web应用
│   ├── backend/                 # 后端API服务
│   │   ├── main.py              # FastAPI应用入口
│   │   ├── run.py               # 启动脚本
│   │   ├── api.py               # 主API路由（148个端点）
│   │   ├── api_alerts.py        # 告警API
│   │   ├── api_cost_allocation.py  # 成本分配API
│   │   ├── api_ai_optimizer.py # AI优化API
│   │   ├── error_handler.py    # 错误处理
│   │   └── i18n.py             # 国际化
│   └── frontend/                # 前端应用
│       ├── app/                 # Next.js App Router
│       │   ├── _pages/          # 页面组件（21个页面）
│       │   │   ├── dashboard.tsx      # Dashboard
│       │   │   ├── resources.tsx      # 资源管理
│       │   │   ├── cost.tsx          # 成本分析
│       │   │   ├── discounts.tsx     # 折扣分析
│       │   │   ├── discount-trend.tsx # 折扣趋势
│       │   │   ├── discount-trend-advanced.tsx # 高级折扣分析
│       │   │   ├── budgets.tsx       # 预算管理
│       │   │   ├── virtual-tags.tsx  # 虚拟标签
│       │   │   ├── alerts.tsx        # 告警管理
│       │   │   ├── cost-allocation.tsx # 成本分配
│       │   │   ├── ai-optimizer.tsx  # AI优化
│       │   │   ├── security.tsx      # 安全合规
│       │   │   ├── cis.tsx           # CIS合规
│       │   │   ├── optimization.tsx  # 优化建议
│       │   │   ├── reports.tsx      # 报告生成
│       │   │   ├── settings.tsx      # 设置
│       │   │   └── ...
│       │   ├── a/[account]/    # 账号路由
│       │   └── ...
│       ├── components/          # React组件
│       │   ├── ui/              # UI基础组件
│       │   ├── layout/          # 布局组件
│       │   ├── charts/          # 图表组件
│       │   └── widgets/        # 小部件组件
│       ├── lib/                 # 工具库
│       │   ├── api.ts           # API请求工具
│       │   ├── i18n.ts          # 国际化
│       │   └── ...
│       ├── contexts/           # React Context
│       │   ├── account-context.tsx  # 账号上下文
│       │   └── locale-context.tsx   # 语言上下文
│       └── ...
│
├── models/                       # 数据模型
│   └── resource.py              # 统一资源模型
│
├── utils/                        # 工具模块
│   ├── logger.py               # 日志工具
│   ├── error_handler.py        # 错误处理
│   ├── retry_helper.py         # 重试助手
│   ├── concurrent_helper.py   # 并发助手
│   ├── credential_manager.py  # 凭证管理
│   └── cost_predictor.py       # 成本预测
│
├── scripts/                      # 工具脚本
│   ├── install_completion.sh   # 安装Shell自动补齐
│   ├── install_cron_mac.sh     # 安装Mac定时任务
│   ├── daily_tasks.sh          # 每日任务脚本
│   ├── sync_to_github.sh       # 同步到GitHub
│   ├── analyze_all_tenants.py # 分析所有租户
│   ├── generate_idle_summary.py # 生成闲置摘要
│   ├── view_idle_resources.py  # 查看闲置资源
│   └── ...                     # 其他工具脚本
│
├── sql/                          # SQL脚本
│   ├── init_mysql_schema.sql    # MySQL表结构
│   └── verify_schema.py        # Schema验证脚本
│
├── tests/                        # 测试用例
│   ├── core/                    # 核心模块测试
│   ├── providers/               # Provider测试
│   ├── resource_modules/       # 资源分析模块测试
│   └── utils/                   # 工具模块测试
│
├── docs/                         # 文档
│   ├── WEB_QUICKSTART.md        # Web快速开始
│   ├── DISCOUNT_ANALYSIS_GUIDE.md  # 折扣分析指南
│   ├── BILL_AUTO_FETCH_GUIDE.md    # 账单自动获取指南
│   ├── PLUGIN_DEVELOPMENT.md   # 插件开发
│   ├── shell_completion.md     # Shell自动补齐
│   └── ...
│
├── examples/                     # 示例代码
│   ├── basic_usage.py          # 基础使用示例
│   └── advanced_usage.py       # 高级使用示例
│
├── completions/                  # Shell自动补齐脚本
│   ├── cl-complete.bash        # Bash自动补齐
│   └── cl-complete.zsh         # Zsh自动补齐
│
├── README.md                     # 项目主README
├── PRODUCT_CAPABILITIES.md      # 产品能力总览
├── PRODUCT_INTRODUCTION.md      # 产品介绍
├── TECHNICAL_ARCHITECTURE.md    # 技术架构文档
├── USER_GUIDE.md                # 用户指南
├── QUICKSTART.md                # 快速开始
├── QUICK_REFERENCE.md           # 快速参考
├── CHANGELOG.md                 # 更新日志
├── IMPROVEMENT_PLAN.md          # 改进计划
├── CONTRIBUTING.md              # 贡献指南
├── pyproject.toml               # Python项目配置
├── requirements.txt             # Python依赖
├── requirements-lock.txt         # Python依赖锁定
├── mypy.ini                      # MyPy配置
├── pytest.ini                   # Pytest配置
├── thresholds.yaml              # 阈值配置示例
├── config.json.example          # 配置示例
└── schedules.yaml.example       # 定时任务配置示例
```

---

## 📦 核心模块说明

### CLI 命令行工具 (`cli/`)

**职责**：提供命令行接口，封装核心功能为易用的命令。

**主要模块**：
- `main.py`：CLI 入口，注册所有命令组
- `commands/`：命令模块，每个文件对应一个命令组
  - `analyze_cmd.py`：分析命令（闲置、成本、折扣、安全等）
  - `bill_cmd.py`：账单管理命令
  - `query_cmd.py`：资源查询命令
  - `remediate_cmd.py`：自动修复命令

### 核心业务逻辑 (`core/`)

**职责**：实现所有业务逻辑，提供可复用的功能模块。

**主要模块**：
- **数据库层**：`database.py`（数据库抽象层）
- **配置管理**：`config.py`（账号配置、规则配置）
- **Provider 抽象**：`provider.py`、`async_provider.py`（云厂商抽象）
- **缓存系统**：`cache.py`（MySQL 缓存表）
- **账单管理**：`bill_storage.py`、`bill_fetcher.py`
- **分析模块**：
  - `idle_detector.py`：闲置资源检测
  - `cost_analyzer.py`：成本分析
  - `cost_trend_analyzer.py`：成本趋势分析
  - `discount_analyzer_advanced.py`：高级折扣分析
  - `security_compliance.py`：安全合规检查
  - `cis_compliance.py`：CIS 基准检查
- **管理模块**：
  - `dashboard_manager.py`：仪表盘管理
  - `budget_manager.py`：预算管理
  - `alert_manager.py`：告警管理
  - `virtual_tags.py`：虚拟标签管理
  - `cost_allocation.py`：成本分配
- **AI 和优化**：
  - `ai_optimizer.py`：AI 优化建议
  - `cost_predictor.py`：成本预测（Prophet ML）

### 云厂商实现 (`providers/`)

**职责**：实现各云厂商的 Provider，封装云平台 API 调用。

**主要模块**：
- `aliyun/provider.py`：阿里云同步 Provider
- `aliyun/async_provider.py`：阿里云异步 Provider
- `tencent/provider.py`：腾讯云 Provider

### Web 应用 (`web/`)

#### 后端 (`web/backend/`)

**职责**：提供 RESTful API，处理业务逻辑。

**主要模块**：
- `main.py`：FastAPI 应用入口，注册所有路由
- `api.py`：主 API 路由（148 个端点）
  - Dashboard API
  - 资源查询 API
  - 成本分析 API
  - 折扣分析 API
  - 预算管理 API
  - 虚拟标签 API
  - 报告生成 API
  - 等等
- `api_alerts.py`：告警 API
- `api_cost_allocation.py`：成本分配 API
- `api_ai_optimizer.py`：AI 优化 API
- `error_handler.py`：统一错误处理
- `i18n.py`：国际化支持

#### 前端 (`web/frontend/`)

**职责**：提供用户界面，展示数据和交互。

**主要模块**：
- `app/_pages/`：页面组件（21 个页面）
- `components/`：可复用组件
  - `ui/`：基础 UI 组件（Button、Card、Table 等）
  - `layout/`：布局组件（Sidebar、DashboardLayout 等）
  - `charts/`：图表组件
  - `widgets/`：小部件组件
- `lib/`：工具库
  - `api.ts`：API 请求工具（重试、超时、去重）
  - `i18n.ts`：国际化系统
- `contexts/`：React Context
  - `account-context.tsx`：账号管理上下文
  - `locale-context.tsx`：语言切换上下文

---

## 🔄 数据流

### 1. 资源查询流程

```
CLI/Web → ConfigManager → CacheManager → Provider → 云平台API → 统一资源模型 → 返回结果
```

### 2. 成本分析流程

```
CLI/Web → CostAnalyzer → BillStorage → MySQL → 成本计算 → 返回结果
```

### 3. 闲置资源检测流程

```
CLI/Web → IdleDetector → Provider → CloudMonitor API → 规则匹配 → 判定结果 → 返回
```

### 4. 折扣分析流程

```
CLI/Web → DiscountAnalyzer → BillStorage → MySQL → 趋势分析 → 返回结果
```

---

## 🗄️ 数据存储

### MySQL 数据库

所有业务数据存储在 MySQL 数据库中，主要表包括：

- `resource_cache`：资源查询缓存（24 小时 TTL）
- `bill_items`：账单明细数据
- `dashboards`：仪表盘配置
- `budgets`：预算数据
- `budget_records`：预算执行记录
- `budget_alerts`：预算告警
- `alert_rules`：告警规则
- `alerts`：告警记录
- `virtual_tags`：虚拟标签
- `tag_rules`：标签规则
- `tag_matches`：标签匹配缓存
- `cost_allocation`：成本分配规则
- `cost_allocation_results`：成本分配结果

### 配置文件

- `~/.cloudlens/config.json`：账号配置
- `~/.cloudlens/.env`：环境变量（MySQL 配置等）
- `~/.cloudlens/notifications.json`：通知配置
- Keyring：凭证安全存储

---

## 🔌 扩展点

### 1. 添加新的云厂商

1. 在 `providers/` 目录创建新目录
2. 实现 `BaseProvider` 接口
3. 在 `ConfigManager` 中注册 Provider

### 2. 添加新的资源类型

1. 在 `providers/aliyun/provider.py` 中添加 `list_xxx()` 方法
2. 在 `resource_modules/` 中添加对应的分析器
3. 在 CLI 和 Web 中添加相应的查询功能

### 3. 添加新的分析功能

1. 在 `core/` 中创建新的分析器模块
2. 在 CLI `commands/analyze_cmd.py` 中添加命令
3. 在 Web `web/backend/api.py` 中添加 API 端点
4. 在 Web `web/frontend/app/_pages/` 中添加页面

---

## 🧪 测试

### 测试结构

```
tests/
├── core/                    # 核心模块测试
│   ├── test_api_wrapper.py
│   ├── test_cache_manager.py
│   ├── test_db_manager.py
│   ├── test_idle_detector.py
│   └── ...
├── providers/               # Provider测试
│   └── test_aliyun_provider.py
├── resource_modules/        # 资源分析模块测试
│   ├── test_discount_analyzer.py
│   ├── test_rds_analyzer.py
│   └── ...
└── utils/                   # 工具模块测试
    └── test_error_handler.py
```

### 运行测试

```bash
# 运行所有测试
python3 -m pytest tests/

# 运行特定模块测试
python3 -m pytest tests/core/

# 运行 CLI 流程测试
python3 -m pytest tests/test_cli_flow.py
```

---

## 📚 文档

### 核心文档
- `README.md`：项目主 README
- `PRODUCT_CAPABILITIES.md`：产品能力总览
- `PRODUCT_INTRODUCTION.md`：产品介绍
- `TECHNICAL_ARCHITECTURE.md`：技术架构文档
- `USER_GUIDE.md`：用户指南
- `QUICKSTART.md`：快速开始
- `QUICK_REFERENCE.md`：快速参考
- `CHANGELOG.md`：更新日志
- `IMPROVEMENT_PLAN.md`：改进计划

### 功能文档
- `docs/WEB_QUICKSTART.md`：Web 快速开始
- `docs/DISCOUNT_ANALYSIS_GUIDE.md`：折扣分析指南
- `docs/BILL_AUTO_FETCH_GUIDE.md`：账单自动获取指南
- `docs/PLUGIN_DEVELOPMENT.md`：插件开发
- `docs/shell_completion.md`：Shell 自动补齐

---

## 🚀 开发指南

### 添加新功能

1. **确定功能位置**：CLI、Web 或两者
2. **实现核心逻辑**：在 `core/` 中实现业务逻辑
3. **添加 CLI 命令**：在 `cli/commands/` 中添加命令
4. **添加 Web API**：在 `web/backend/api.py` 中添加端点
5. **添加 Web 页面**：在 `web/frontend/app/_pages/` 中添加页面
6. **添加测试**：在 `tests/` 中添加测试用例
7. **更新文档**：更新相关文档

### 代码规范

- Python：遵循 PEP 8，使用类型提示
- TypeScript：遵循 ESLint 规则
- 提交信息：使用清晰的提交信息
- 测试：新功能必须包含测试用例

---

## 📊 项目统计

- **总文件数**：200+ 文件
- **Python 代码**：~15,000 行
- **TypeScript 代码**：~20,000 行
- **API 端点**：148 个
- **Web 页面**：21 个
- **支持资源类型**：20+ 种
- **支持云平台**：2 个（阿里云、腾讯云）
