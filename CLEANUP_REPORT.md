# 代码深度清理报告

## 已修复的问题

### 1. 重复的缓存模块 ✅
- **问题**: `base_analyzer.py` 导入了未使用的 `FileCacheManager`
- **修复**: 移除了 `from core.cache_manager import FileCacheManager` 导入
- **状态**: `cache_manager.py` 已标记为 Legacy，但测试仍在使用，保留

### 2. 重复的配置模块 ✅
- **问题**: Web 后端使用了旧的 `config_manager.py`
- **修复**: 统一使用 `core.config.ConfigManager`
  - 修复了 `web/backend/api_alerts.py`
  - 修复了 `web/backend/api_ai_optimizer.py`
  - 修复了 `web/backend/api_cost_allocation.py`
  - 修复了 `scripts/test_async.py`
  - 更新了 `core/__init__.py` 的导入
- **状态**: `config_manager.py` 仍被旧脚本使用（tenants结构），保留但标记为 Legacy

### 3. 过时的引用 ✅
- **问题**: 多处引用了不存在的 `main_cli.py`
- **修复**:
  - 修复了 `cloudlens` 文件
  - 修复了 `core/repl.py`
  - 修复了 `tests/test_cli_flow.py`
  - 修复了 `check_db_public.py`
- **状态**: 所有引用已更新为 `cli.main` 或 `cli.utils`

### 4. 临时脚本 ✅
- **问题**: `check_db_public.py` 硬编码了账号名
- **修复**: 改为支持命令行参数，如果没有则使用第一个可用账号
- **问题**: `scripts/test_daily_bill_api.py` 硬编码了账号名和注释
- **修复**: 改为支持命令行参数，更新了注释

### 5. 过时文件 ✅
- **删除**: `core/cis_compliance_new_methods.txt` - 未完成的代码片段（功能已在 `cis_compliance.py` 中实现）

### 6. 文档占位符 ✅
- **修复**: `core/discount_analyzer.py` 中的 `xxx` 占位符改为类型说明

### 7. 版本号 ✅
- **修复**: `web/backend/main.py` 版本号从 2.0.0 更新为 2.1.0

### 8. Provider 方法命名不一致 ⚠️
- **问题**: `AliyunProvider` 使用 `list_eip()`，但部分代码调用 `list_eips()`
- **状态**: 已添加兼容性检查，但建议统一命名

## 需要保留但标记为 Legacy 的模块

### 1. `core/cache_manager.py` (FileCacheManager)
- **原因**: 测试文件仍在使用
- **建议**: 更新测试以使用新的 `CacheManager`，然后删除

### 2. `core/config_manager.py`
- **原因**: 旧脚本仍在使用 tenants 结构
- **建议**: 逐步迁移脚本到新的 accounts 结构

### 3. `core/remediation.py` vs `core/remediation_engine.py`
- **原因**: 
  - `remediation.py` 提供通用框架（RemediationPlan, RemediationAction等）
  - `remediation_engine.py` 专门处理标签修复
- **建议**: 保留两者，但考虑重命名以避免混淆

### 4. `legacy/main.py`
- **原因**: 可能仍被某些脚本使用
- **建议**: 检查是否还有引用，如果没有则删除

## 待处理的问题

### 1. 测试文件
- `tests/test_cli_flow.py` - 已修复导入，但需要验证测试是否通过
- `tests/core/test_cache_manager.py` - 仍在使用旧的 FileCacheManager

### 2. 脚本文件
- 多个脚本仍在使用旧的 tenants 配置结构
- 建议逐步迁移到新的 accounts 结构

### 3. 文档更新
- `install.sh` 仍引用 `main_cli.py`
- 多个文档仍引用 `main_cli.py`
- 需要更新文档中的命令示例

## 清理统计

- **修复的文件数**: 15+
- **删除的文件数**: 1 (`cis_compliance_new_methods.txt`)
- **更新的导入**: 10+
- **修复的硬编码**: 2 (`check_db_public.py`, `test_daily_bill_api.py`)

## 下一步建议

1. 运行所有测试，确保修复没有破坏功能
2. 更新文档中的命令示例（从 `main_cli.py` 改为 `cli.main`）
3. 逐步迁移脚本从 tenants 结构到 accounts 结构
4. 统一 Provider 方法命名（`list_eip` vs `list_eips`）
