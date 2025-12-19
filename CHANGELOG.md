# Changelog

All notable changes to CloudLens will be documented in this file.

## [2.1.1] - 2025-01-XX

### Changed
- 📚 **项目深度梳理** - 全面清理和重构项目文档
  - 删除所有过时的迁移文档（SQLITE_*, MYSQL_*, MIGRATION_*）
  - 删除过程性的修复文档（*_FIX.md, CLEANUP_REPORT.md）
  - 清理根目录的测试/调试脚本（test_*.py, check_*.py）
  - 更新 K8S 部署文档，移除 SQLite 相关内容，更新为 MySQL
  - 创建新的项目结构文档（PROJECT_STRUCTURE.md）
  - 更新 README.md，添加项目结构链接和更完整的文档索引
  - 更新技术架构文档，添加 Web 应用和数据库架构说明
  - 统一文档结构，提升可维护性和可读性

### Fixed
- 🐛 修复资源列表中 VPC 名称/ID 显示为空的问题
- 🐛 修复后端国际化 API 参数顺序问题
- 🐛 修复预算状态 API 的日期解析问题
- 🐛 修复闲置资源获取时的数据格式处理问题

## [2.1.0] - 2025-01-XX

### Added
- 🌐 **Web 可视化界面** - 基于 Next.js + FastAPI 的现代化 Web 应用
  - 支持中英文双语切换
  - Dashboard 仪表盘，实时展示成本、资源、安全等关键指标
  - 资源管理页面，支持多类型资源查询和筛选
  - 成本分析页面，支持成本趋势和明细查看
  - 折扣分析页面，支持折扣趋势和高级分析
  - 安全合规页面，展示安全评分和检查结果
  - 优化建议页面，提供资源优化建议
  - 预算管理、告警管理、成本分配、AI优化等高级功能
  - Finout 风格的现代化 UI 设计

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
