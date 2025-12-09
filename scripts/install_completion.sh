#!/usr/bin/env bash
# CloudLens CLI Shell Completion 安装脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "CloudLens CLI - 安装Shell自动补齐"
echo "===================================="
echo ""

# 检测Shell类型
SHELL_NAME=$(basename "$SHELL")

if [ "$SHELL_NAME" = "bash" ]; then
    echo "检测到Bash shell"
    
    # 检查bash版本
    BASH_VERSION_MAJOR=$(echo $BASH_VERSION | cut -d. -f1)
    BASH_VERSION_MINOR=$(echo $BASH_VERSION | cut -d. -f2)
    
    echo "Bash版本: $BASH_VERSION"
    
    if [ "$BASH_VERSION_MAJOR" -lt 4 ] || ([ "$BASH_VERSION_MAJOR" -eq 4 ] && [ "$BASH_VERSION_MINOR" -lt 4 ]); then
        echo ""
        echo "❌ Bash版本过低（需要4.4+）"
        echo ""
        echo "建议使用以下方案之一:"
        echo ""
        echo "方案1: 升级Bash（推荐）"
        echo "  macOS用户:"
        echo "    brew install bash"
        echo "    sudo sh -c 'echo /usr/local/bin/bash >> /etc/shells'"
        echo "    chsh -s /usr/local/bin/bash"
        echo ""
        echo "方案2: 切换到Zsh"
        echo "  macOS用户（已内置）:"
        echo "    chsh -s /bin/zsh"
        echo "  然后重新运行此脚本"
        echo ""
        echo "方案3: 手动补齐（临时方案）"
        echo "  创建手动补齐脚本到 ~/.bash_completion.d/cl"
        exit 1
    fi
    
    # 生成bash completion脚本
    echo "生成bash completion脚本..."
    _CL_COMPLETE=bash_source "$PROJECT_ROOT/cl" > "$PROJECT_ROOT/completions/cl-complete.bash" 2>/dev/null || {
        echo "❌ 生成completion脚本失败"
        echo "这可能是因为Click版本不支持或其他依赖问题"
        exit 1
    }
    
    # 确定安装位置
    if [ -d "/usr/local/etc/bash_completion.d" ]; then
        COMPLETION_DIR="/usr/local/etc/bash_completion.d"
    elif [ -d "/etc/bash_completion.d" ]; then
        COMPLETION_DIR="/etc/bash_completion.d"
    elif [ -d "$HOME/.bash_completion.d" ]; then
        COMPLETION_DIR="$HOME/.bash_completion.d"
    else
        mkdir -p "$HOME/.bash_completion.d"
        COMPLETION_DIR="$HOME/.bash_completion.d"
    fi
    
    echo "安装completion脚本到: $COMPLETION_DIR"
    cp "$PROJECT_ROOT/completions/cl-complete.bash" "$COMPLETION_DIR/cl"
    
    # 添加到.bashrc
    BASHRC="$HOME/.bashrc"
    if [ -f "$BASHRC" ]; then
        if ! grep -q "bash_completion.d/cl" "$BASHRC"; then
            echo "" >> "$BASHRC"
            echo "# CloudLens CLI completion" >> "$BASHRC"
            echo "[ -f $COMPLETION_DIR/cl ] && source $COMPLETION_DIR/cl" >> "$BASHRC"
            echo "已添加到 $BASHRC"
        else
            echo "$BASHRC 已包含completion配置"
        fi
    fi
    
    echo ""
    echo "✓ Bash completion安装成功!"
    echo "请运行: source ~/.bashrc"
    echo ""
    echo "测试: cl ana<Tab> 应该自动补齐为 cl analyze"
    
elif [ "$SHELL_NAME" = "zsh" ]; then
    echo "检测到Zsh shell"
    
    # 生成zsh completion脚本
    echo "生成zsh completion脚本..."
    _CL_COMPLETE=zsh_source "$PROJECT_ROOT/cl" > "$PROJECT_ROOT/completions/cl-complete.zsh" 2>/dev/null || {
        echo "❌ 生成completion脚本失败"
        exit 1
    }
    
    # 确定安装位置
    if [ -d "/usr/local/share/zsh/site-functions" ]; then
        COMPLETION_DIR="/usr/local/share/zsh/site-functions"
        NEED_SUDO=true
    else
        mkdir -p "$HOME/.zsh/completion"
        COMPLETION_DIR="$HOME/.zsh/completion"
        NEED_SUDO=false
    fi
    
    echo "安装completion脚本到: $COMPLETION_DIR"
    
    if [ "$NEED_SUDO" = true ]; then
        echo "需要sudo权限安装到系统目录..."
        sudo cp "$PROJECT_ROOT/completions/cl-complete.zsh" "$COMPLETION_DIR/_cl"
    else
        cp "$PROJECT_ROOT/completions/cl-complete.zsh" "$COMPLETION_DIR/_cl"
    fi
    
    # 添加到.zshrc
    ZSHRC="$HOME/.zshrc"
    if [ -f "$ZSHRC" ]; then
        NEEDS_FPATH=false
        NEEDS_COMPINIT=false
        
        if ! grep -q "fpath.*zsh/completion" "$ZSHRC" 2>/dev/null && [ "$NEED_SUDO" = false ]; then
            NEEDS_FPATH=true
        fi
        
        if ! grep -q "compinit" "$ZSHRC" 2>/dev/null; then
            NEEDS_COMPINIT=true
        fi
        
        if [ "$NEEDS_FPATH" = true ] || [ "$NEEDS_COMPINIT" = true ]; then
            echo "" >> "$ZSHRC"
            echo "# CloudLens CLI completion" >> "$ZSHRC"
            
            if [ "$NEEDS_FPATH" = true ]; then
                echo "fpath=($HOME/.zsh/completion \$fpath)" >> "$ZSHRC"
            fi
            
            if [ "$NEEDS_COMPINIT" = true ]; then
                echo "autoload -Uz compinit && compinit" >> "$ZSHRC"
            fi
            
            echo "已添加到 $ZSHRC"
        else
            echo "$ZSHRC 已包含必要配置"
        fi
    else
        # 创建.zshrc
        cat > "$ZSHRC" << 'EOF'
# CloudLens CLI completion
fpath=(~/.zsh/completion $fpath)
autoload -Uz compinit && compinit
EOF
        echo "已创建 $ZSHRC"
    fi
    
    echo ""
    echo "✓ Zsh completion安装成功!"
    echo "请运行: source ~/.zshrc"
    echo ""
    echo "测试: cl ana<Tab> 应该自动补齐为 cl analyze"
    
else
    echo "不支持的shell: $SHELL_NAME"
    echo "目前支持: bash (4.4+), zsh"
    echo ""
    echo "您可以切换到zsh:"
    echo "  chsh -s /bin/zsh"
    exit 1
fi

echo ""
echo "现在您可以使用Tab键自动补齐cl命令了!"
echo ""
echo "使用示例:"
echo "  cl ana<Tab>              → cl analyze"
echo "  cl analyze <Tab>         → 显示子命令列表"
echo "  cl query <Tab>           → 显示资源类型"
echo "  cl analyze cost --<Tab>  → 显示选项参数"

    
    # 添加到.zshrc
    ZSHRC="$HOME/.zshrc"
    if [ -f "$ZSHRC" ]; then
        if ! grep -q "fpath.*\.zsh/completion" "$ZSHRC"; then
            echo "" >> "$ZSHRC"
            echo "# CloudLens CLI completion" >> "$ZSHRC"
            echo "fpath=($HOME/.zsh/completion \$fpath)" >> "$ZSHRC"
            echo "autoload -Uz compinit && compinit" >> "$ZSHRC"
            echo "已添加到 $ZSHRC"
        fi
    fi
    
    echo ""
    echo "✓ Zsh completion安装成功!"
    echo "请运行: source ~/.zshrc"
    
else
    echo "不支持的shell: $SHELL_NAME"
    echo "目前支持: bash, zsh"
    exit 1
fi

echo ""
echo "现在您可以使用Tab键自动补齐cl命令了!"
echo "示例:"
echo "  cl ana<Tab>      → cl analyze"
echo "  cl analyze <Tab> → 显示子命令列表"
echo "  cl query <Tab>   → 显示资源类型"
