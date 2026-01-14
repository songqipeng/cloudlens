# CloudLens CLI 命令模块

本目录包含所有CLI命令的模块化实现。

## 目录结构

```
cli/commands/
├── __init__.py         # 命令包入口
├── config_cmd.py       # 配置管理命令
├── query_cmd.py        # 资源查询命令（带缓存）
├── cache_cmd.py        # 缓存管理命令
└── misc_cmd.py         # Dashboard, REPL, Scheduler等
```

## 功能特性

### 1. 配置管理 (`config_cmd.py`)
- ✅ Rich Table美化输出
- ✅ 凭证验证
- ✅ 彩色状态提示

### 2. 资源查询 (`query_cmd.py`)
- ✅ 智能缓存集成
- ✅ 多格式输出 (table/json/csv)
- ✅ 进度条显示
- ✅ 批量查询支持

### 3. 缓存管理 (`cache_cmd.py`)
- ✅ 缓存状态查看
- ✅ 条件清理
- ✅ 自动过期清理

### 4. 其他命令 (`misc_cmd.py`)
- ✅ TUI Dashboard
- ✅ 交互式REPL
- ✅ 任务调度器

## 使用示例

```bash
# 配置管理
cl config list
cl config add --provider aliyun --name myaccount

# 资源查询（使用缓存）
cl query resources ecs
cl query resources rds --no-cache

# 缓存管理
cl cache status
cl cache clear --resource-type ecs
cl cache cleanup

# Dashboard
cl dashboard

# REPL
cl repl

# 调度器
cl scheduler --config schedules.yaml
```

## 开发指南

### 添加新命令

1. 在 `commands/` 目录创建新模块
2. 定义click命令组或命令
3. 在 `__init__.py` 中导出
4. 在 `cl_new.py` 中注册

### 使用Rich UI

```python
from rich.console import Console
from rich.table import Table

console = Console()

# 表格
table = Table(title="标题")
table.add_column("列1", style="cyan")
console.print(table)

# 彩色输出
console.print("[green]成功[/green]")
console.print("[red]失败[/red]")
```

### 集成缓存

```python
from core.cache import CacheManager

cache = CacheManager()

# 读取缓存
cached = cache.get(resource_type, account_name, region)

# 写入缓存
cache.set(resource_type, account_name, data, region)
```

## 迁移说明

原 `main_cli.py` (1764行) 已拆分为：
- `cli/commands/` - 命令模块
- `cli/utils.py` - 工具函数
- `cl_new.py` - 新入口文件 (~80行)

建议逐步迁移到新架构，旧版本保留作为兼容。
