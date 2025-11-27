#!/bin/bash
# CloudLens CLI 安装脚本

INSTALL_DIR="/usr/local/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

echo "✅ Installation complete!"
echo ""
echo "You can now use:"
echo "  cl query ydzn ecs"
echo "  cloudlens query ydzn ecs"
echo ""
echo "Try: cl config list"
