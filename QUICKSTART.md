# CloudLens CLI - 快速开始

## 安装

```bash
cd /Users/mac/aliyunidle
pip install -r requirements.txt
chmod +x cloudlens
```

## 新的简化命令格式

### 基本用法

```bash
# 第一次查询 - 会提示选择账号
./cloudlens query ecs

# 指定账号查询
./cloudlens query ydzn ecs

# 后续查询 - 自动使用上次的账号
./cloudlens query rds
./cloudlens query vpc
```

### 完整示例

```bash
# 配置账号（只需一次）
./cloudlens config add

# 查询资源（自动记住账号）
./cloudlens query ydzn ecs      # 查询ydzn账号的ECS
./cloudlens query rds            # 自动使用ydzn账号查询RDS
./cloudlens query zmyc vpc       # 切换到zmyc账号查询VPC
./cloudlens query ecs            # 继续使用zmyc账号

# 分析功能
./cloudlens analyze idle         # 使用记住的账号
./cloudlens analyze ydzn cost    # 指定账号

# 生成报告
./cloudlens report generate      # 使用记住的账号
```

> 仍可使用 `python3 main_cli.py ...` 命令形式；`./cloudlens` 只是封装了账号记忆与位置参数。

## 添加到 PATH（可选）

为了在任何地方都能使用 `cloudlens` 命令：

```bash
# 创建符号链接到 /usr/local/bin
sudo ln -s /Users/mac/aliyunidle/cloudlens /usr/local/bin/cloudlens

# 现在可以直接使用
cloudlens query ecs
```

## 主要改进

1. ✅ **可执行命令** - 不再需要 `python3 main_cli.py`
2. ✅ **简化语法** - `cloudlens query ydzn ecs` 而不是 `cloudlens query ecs --account ydzn`
3. ✅ **智能记忆** - 自动记住上次使用的账号
4. ✅ **交互提示** - 首次使用时友好的账号选择界面
