# Changelog

All notable changes to CloudLens will be documented in this file.

## [2.1.1] - 2025-12-22

### Changed
- 📚 **项目深度梳理** - 全面清理和重构项目文档
  - 删除所有过时的迁移文档（K8S_*, 迁移脚本等）
  - 删除过程性的修复文档和测试脚本
  - 清理根目录的临时/调试文件
  - 重新编写 README、产品能力文档、技术架构文档
  - 统一文档结构，提升可维护性和可读性

### Fixed
- 🐛 修复资源列表中 VPC 名称/ID 显示为空的问题
- 🐛 修复后端国际化 API 参数顺序问题
- 🐛 修复预算状态 API 的日期解析问题
- 🐛 修复闲置资源获取时的数据格式处理问题
- 🐛 修复成本构成饼图工具提示显示不清晰的问题
- 🐛 优化 API 超时处理，增加默认超时时间到 60 秒

## [2.1.0] - 2025-01-XX

### Added

#### 🌐 Web 可视化界面
- **现代化 Web 应用**：基于 Next.js 16.0.8 + FastAPI 的现代化 Web 应用
- **中英文双语支持**：完整的国际化系统，支持中英文切换
- **Dashboard 仪表盘**：实时展示成本、资源、安全等关键指标
- **资源管理页面**：支持多类型资源查询和筛选
- **成本分析页面**：成本趋势和明细查看，成本构成饼图
- **折扣分析页面**：折扣趋势和高级分析（季度/年度对比、异常检测等）
- **安全合规页面**：展示安全评分和 CIS 检查结果
- **优化建议页面**：提供资源优化建议
- **预算管理**：支持月度/季度/年度预算，多级告警阈值
- **告警管理**：告警规则创建和管理，通知配置
- **成本分配**：支持多维度成本分配规则
- **AI 优化**：AI 生成的资源优化建议和成本预测
- **虚拟标签**：基于规则创建虚拟标签，支持成本分析
- **报告生成**：支持 Excel、HTML、PDF 格式报告
- **Finout 风格 UI**：现代化界面设计，响应式布局，支持深色模式

#### 📈 成本分析增强
- **成本趋势分析**：环比/同比增长分析，按类型/区域统计
- **AI 成本预测**：基于 Prophet ML 模型，预测未来 90 天成本趋势
- **折扣趋势分析**：基于账单 CSV，分析最近 6 个月折扣变化
  - 支持产品/合同/实例维度分析
  - 季度/年度对比分析
  - 异常检测和优化建议
  - 支持 Excel/HTML 报告导出

#### 📥 账单管理
- **账单自动获取**：通过 BSS OpenAPI 自动获取账单数据
- **定时任务支持**：支持 cron 定时自动获取账单
- **账单存储**：MySQL 数据库存储账单明细数据

#### 🛡️ 安全合规增强
- **CIS Benchmark**：10+ 安全基线检查，覆盖 IAM/网络/数据/审计
- **安全概览**：安全评分、风险统计可视化

#### 🔧 自动化修复
- **批量打标签**：自动为资源打标签，支持干运行模式
- **修复历史**：完整的修复操作审计日志

#### ⚡ 性能优化
- **异步 I/O 架构**：AsyncProvider 基础，为高性能查询做准备
- **MySQL 缓存**：MySQL 缓存表，24 小时 TTL
- **数据库迁移**：从 SQLite 迁移到 MySQL，支持更好的并发性能

### Changed
- **数据库架构**：从 SQLite 迁移到 MySQL，支持更好的并发和扩展性
- **缓存系统**：从 SQLite 缓存迁移到 MySQL 缓存表
- **API 超时处理**：优化超时处理，增加默认超时时间，改进错误信息

### Fixed
- 修复 MySQL 连接问题
- 修复 MySQL 语法兼容性问题（CREATE INDEX IF NOT EXISTS）
- 修复后端环境变量加载问题
- 修复前端 Next.js 构建缓存问题

## [2.0.0] - 2025-11-28

### Added

#### 🎨 Interactive Experience
- **Interactive REPL Mode**: Auto-launches when running without arguments
  - Auto-completion powered by `prompt_toolkit`
  - Command history and suggestions
  - Beautiful output with `rich` library
  - Execution timing display
- **TUI Dashboard**: Full-screen monitoring interface using `textual`
  - Resource navigation tree (by category)
  - Live data tables
  - Keyboard shortcuts (q=quit, r=refresh)

#### 🔍 Advanced Query Capabilities
- **Pandas Data Analysis**: `--analysis` option for aggregation
  - Group by: `groupby:region`
  - Aggregations: `sum`, `mean`, `count`
  - Sorting and top-N: `sort:field|top:N`
- **JMESPath Querying**: `--jmespath` option for AWS CLI-style filtering
  - Example: `[?Status=='Running'].{ID:InstanceId,Name:InstanceName}`
  - JSON output integration

#### ⚙️ Configuration Management
- **Environment Variable Support**:
  - `CLOUDLENS_ACCESS_KEY_ID`
  - `CLOUDLENS_ACCESS_KEY_SECRET`
  - `CLOUDLENS_PROVIDER`
  - `CLOUDLENS_PROFILE`
- **Credentials File**: `~/.cloudlens/credentials` (AWS CLI compatible)
- **Multi-source Loading**: ENV > credentials file > config.json + keyring

#### 🗄️ Performance & Infrastructure
- **SQLite Caching**: `core/cache.py`
  - Configurable TTL (default 5 minutes)
  - Cache key generation per resource/account/region
  - Automatic expiration cleanup
- **Auto-Remediation Framework**: `core/remediation.py`
  - Dry-run mode (default)
  - Supported actions: stop_instance, delete_snapshot, modify_security_group, release_eip, delete_idle_disk
  - Batch execution with statistics

#### 🔌 Plugin Ecosystem
- **External Plugin Support**: via Python `entry_points`
  - Auto-discovery at startup
  - Documentation: `docs/PLUGIN_DEVELOPMENT.md`
  - Backward compatible with Python 3.8+

### Changed

- **Configuration Model**: Renamed `AccountConfig` to `CloudAccount` for clarity
- **Config Loading**: Enhanced `ConfigManager` with multi-source support
- **CLI Behavior**: Defaults to REPL when no arguments provided

### Fixed

- Import errors after configuration refactoring
- Compatibility with Python 3.8/3.9 for `importlib.metadata`

### Documentation

- Updated `README.md` with v2.0 features
- Created `docs/PLUGIN_DEVELOPMENT.md`
- Created `docs/credentials.sample`
- Generated comprehensive walkthrough

## [1.0.0] - 2025-11 (Earlier)

### Initial Release

- Multi-cloud resource management (Aliyun, Tencent Cloud)
- Resource querying: ECS, RDS, Redis, OSS, VPC, etc.
- Idle resource analysis
- Excel/HTML/JSON/CSV report generation
- Concurrent querying
- Security compliance checks
- Tag governance
- Advanced filtering engine
- Keyring-based credential storage
