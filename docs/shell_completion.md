# CloudLens CLI - Shell Completion

## 快速安装

### 自动安装（推荐）

```bash
./scripts/install_completion.sh
```

安装脚本会自动检测您的shell类型（bash或zsh）并安装相应的completion脚本。

### 手动安装

#### Bash

```bash
# 生成completion脚本
_CL_COMPLETE=bash_source ./cl > completions/cl-complete.bash

# 安装到系统目录（需要sudo）
sudo cp completions/cl-complete.bash /usr/local/etc/bash_completion.d/cl

# 或安装到用户目录
mkdir -p ~/.bash_completion.d
cp completions/cl-complete.bash ~/.bash_completion.d/cl

# 添加到 ~/.bashrc
echo '[ -f ~/.bash_completion.d/cl ] && source ~/.bash_completion.d/cl' >> ~/.bashrc

# 重新加载
source ~/.bashrc
```

#### Zsh

```bash
# 生成completion脚本
_CL_COMPLETE=zsh_source ./cl > completions/cl-complete.zsh

# 安装到系统目录（需要sudo）
sudo cp completions/cl-complete.zsh /usr/local/share/zsh/site-functions/_cl

# 或安装到用户目录
mkdir -p ~/.zsh/completion
cp completions/cl-complete.zsh ~/.zsh/completion/_cl

# 添加到 ~/.zshrc
cat >> ~/.zshrc << 'EOF'
# CloudLens CLI completion
fpath=(~/.zsh/completion $fpath)
autoload -Uz compinit && compinit
EOF

# 重新加载
source ~/.zshrc
```

## 使用示例

安装完成后，您可以使用Tab键自动补齐：

```bash
# 补齐主命令
cl ana<Tab>              → cl analyze

# 补齐子命令
cl analyze <Tab>         → 显示: idle, renewal, cost, forecast, security, tags

# 补齐选项参数
cl analyze cost --<Tab>  → 显示: --account, --days, --trend, --help

# 补齐账号名称
cl query ecs --account <Tab>  → 显示已配置的账号列表
```

## 支持的Shell

- ✅ Bash 4.0+
- ✅ Zsh 5.0+
- ❌ Fish (计划支持)
- ❌ PowerShell (计划支持)

## 故障排查

### Bash completion不工作

1. 确保已安装bash-completion:
   ```bash
   # macOS
   brew install bash-completion@2
   
   # Ubuntu/Debian
   sudo apt-get install bash-completion
   ```

2. 检查.bashrc是否加载了bash-completion:
   ```bash
   grep -i bash-completion ~/.bashrc
   ```

3. 重新加载配置:
   ```bash
   source ~/.bashrc
   ```

### Zsh completion不工作

1. 确保启用了compinit:
   ```bash
   autoload -Uz compinit && compinit
   ```

2. 清除completion缓存:
   ```bash
   rm ~/.zcompdump*
   compinit
   ```

3. 检查fpath:
   ```bash
   echo $fpath
   ```

## 卸载

### Bash

```bash
rm -f ~/.bash_completion.d/cl
# 或
sudo rm -f /usr/local/etc/bash_completion.d/cl

# 从.bashrc中删除相关行
```

### Zsh

```bash
rm -f ~/.zsh/completion/_cl
# 或
sudo rm -f /usr/local/share/zsh/site-functions/_cl

# 从.zshrc中删除相关行
```

---

**享受更高效的命令行体验!** ✨
