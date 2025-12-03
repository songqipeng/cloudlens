#!/bin/bash
# CloudLens CLI 安装脚本

INSTALL_DIR="/usr/local/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Determine shell and RC file
SHELL_NAME=$(basename "$SHELL")
RC_FILE=""
if [ "$SHELL_NAME" = "bash" ]; then
    RC_FILE="$HOME/.bashrc"
elif [ "$SHELL_NAME" = "zsh" ]; then
    RC_FILE="$HOME/.zshrc"
else
    echo "Unsupported shell: $SHELL_NAME. Autocompletion will not be set up."
fi

echo "🚀 Installing CloudLens CLI..."

# 检查是否有权限
if [ ! -w "$INSTALL_DIR" ]; then
    echo "❌ No write permission to $INSTALL_DIR"
    echo "Please run with sudo: sudo ./install.sh"
    exit 1
fi

# 创建符号链接
ln -sf "$SCRIPT_DIR/cl" "$INSTALL_DIR/cl"
ln -sf "$SCRIPT_DIR/cloudlens" "$INSTALL_DIR/cloudlens"

# Create alias
echo "Creating alias 'cl'..."
# Remove existing alias if present
if [ -f "$RC_FILE" ]; then
    sed -i '' '/alias cl=/d' "$RC_FILE"
    echo "alias cl='python3 $SCRIPT_DIR/main_cli.py'" >> "$RC_FILE"
fi

# Setup Autocompletion
echo "Setting up autocompletion..."
COMPLETION_DIR="$HOME/.cloudlens"
mkdir -p "$COMPLETION_DIR"

if [ "$SHELL_NAME" = "zsh" ]; then
    # Zsh completion
    _CL_COMPLETE=zsh_source python3 "$SCRIPT_DIR/main_cli.py" > "$COMPLETION_DIR/cl-complete.zsh" 2>/dev/null
    
    # Remove existing source line if present to avoid duplicates
    if [ -f "$RC_FILE" ]; then
        sed -i '' '/source .*cl-complete.zsh/d' "$RC_FILE"
        echo "source $COMPLETION_DIR/cl-complete.zsh" >> "$RC_FILE"
    fi
    
    echo "Zsh completion installed to $COMPLETION_DIR/cl-complete.zsh"
elif [ "$SHELL_NAME" = "bash" ]; then
    # Bash completion
    _CL_COMPLETE=bash_source python3 "$SCRIPT_DIR/main_cli.py" > "$COMPLETION_DIR/cl-complete.bash" 2>/dev/null
    
    # Remove existing source line if present
    if [ -f "$RC_FILE" ]; then
        sed -i '' '/source .*cl-complete.bash/d' "$RC_FILE"
        echo "source $COMPLETION_DIR/cl-complete.bash" >> "$RC_FILE"
    fi
    
    echo "Bash completion installed to $COMPLETION_DIR/cl-complete.bash"
fi

echo "✅ Installation complete!"
echo "Please run the following command to apply changes:"
echo "  source $RC_FILE"
echo ""
echo "You can now use:"
echo "  cl query ydzn ecs"
echo "  cloudlens query ydzn ecs"
echo ""
echo "Try: cl config list"
