# Changelog

All notable changes to CloudLens CLI will be documented in this file.

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
