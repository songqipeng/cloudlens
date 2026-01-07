# CloudLens CLI 完整功能测试

## 概述

本目录包含 CloudLens CLI 的完整自动化测试脚本，用于测试所有CLI命令的功能。

## 测试内容

测试覆盖以下CLI命令：

1. **帮助信息** - 显示CLI帮助
2. **版本信息** - 显示CLI版本
3. **配置管理** - 配置列表、查看配置
4. **资源查询** - ECS、RDS等资源查询（支持多种格式）
5. **缓存管理** - 缓存状态查看
6. **成本分析** - 成本分析功能
7. **闲置资源分析** - 闲置资源检测
8. **账单管理** - 账单列表查询
9. **命令帮助** - 各命令组的帮助信息

## 运行测试

### 方式1：直接运行测试脚本（不录制）

```bash
cd /Users/mac/cloudlens
python3 tests/test_cli_full.py
```

### 方式2：录制测试过程（推荐）

```bash
cd /Users/mac/cloudlens
./tests/record_cli_test.sh
```

录制脚本会：
- 使用 `script` 命令录制终端会话
- 生成录制文件（`.txt`）和时间戳文件（`.txt`）
- 可以回放录制的会话

### 方式3：使用 asciinema 录制（如果已安装）

```bash
# 安装 asciinema
pip install asciinema

# 录制
asciinema rec test-recordings/cli/cli_test_$(date +%Y%m%d_%H%M%S).cast

# 在录制的终端中运行测试
python3 tests/test_cli_full.py

# 按 Ctrl+D 结束录制
```

## 测试输出

### 测试结果文件

测试结果保存在：
- `test-recordings/cli/cli_test_results_YYYYMMDD_HHMMSS.json`

包含：
- 每个测试的详细结果
- 命令输出
- 执行时间
- 成功/失败状态

### 录制文件

如果使用录制脚本：
- 录制文件：`test-recordings/cli/cli_test_recording_YYYYMMDD_HHMMSS.txt`
- 时间文件：`test-recordings/cli/cli_test_timing_YYYYMMDD_HHMMSS.txt`

### 回放录制

```bash
# 使用 scriptreplay 回放
scriptreplay -t test-recordings/cli/cli_test_timing_*.txt test-recordings/cli/cli_test_recording_*.txt
```

## 测试配置

可以在 `test_cli_full.py` 中修改：

- `TEST_ACCOUNT` - 测试账号名称
- `CLI_TEST_COMMANDS` - 测试命令列表
- `timeout` - 每个命令的超时时间

## 测试结果解读

- ✅ **成功** - 命令执行成功，输出包含预期关键词
- ⚠️ **警告** - 命令执行成功，但未找到预期关键词
- ❌ **失败** - 命令执行失败或超时

## 故障排查

### 测试失败

1. **检查CLI是否正常**：
   ```bash
   python3 -m cli.main --help
   ```

2. **检查测试账号配置**：
   ```bash
   python3 -m cli.main config list
   ```

3. **查看详细错误**：
   - 检查测试结果JSON文件中的 `error` 字段
   - 查看 `output` 字段中的命令输出

### 录制失败

1. **检查 script 命令**：
   ```bash
   which script
   ```

2. **检查权限**：
   ```bash
   ls -l tests/record_cli_test.sh
   chmod +x tests/record_cli_test.sh
   ```

## 自定义测试

可以修改 `test_cli_full.py` 中的 `CLI_TEST_COMMANDS` 列表来：

- 添加新的测试命令
- 修改预期输出
- 调整超时时间
- 添加自定义验证逻辑

## 示例测试命令

```python
{
    "name": "自定义测试",
    "command": ["query", "resources", "ydzn", "ecs"],
    "description": "测试ECS查询",
    "expected_output": ["实例", "InstanceId"],
    "timeout": 60,
}
```

## 相关文件

- `test_cli_full.py` - 主测试脚本
- `record_cli_test.sh` - 录制脚本
- `README_CLI_TEST.md` - 本文档

