#!/bin/bash
# CloudLens CLI 完整功能测试录制脚本（使用 asciinema）
# 如果已安装 asciinema，使用此脚本可以获得更好的录制效果

set -e

# 配置
OUTPUT_DIR="test-recordings/cli"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RECORDING_FILE="${OUTPUT_DIR}/cli_test_${TIMESTAMP}.cast"

# 确保输出目录存在
mkdir -p "${OUTPUT_DIR}"

echo "=========================================="
echo "CloudLens CLI 完整功能测试录制 (asciinema)"
echo "=========================================="

# 检查 asciinema 是否安装
if ! command -v asciinema &> /dev/null; then
    echo "❌ 未找到 asciinema 命令"
    echo ""
    echo "安装方法："
    echo "  pip install asciinema"
    echo "  或"
    echo "  brew install asciinema  # macOS"
    echo ""
    echo "使用 script 命令录制："
    echo "  ./tests/record_cli_test.sh"
    exit 1
fi

echo "📹 录制文件: ${RECORDING_FILE}"
echo "=========================================="
echo ""
echo "🎬 开始录制..."
echo "   在录制的终端中，测试脚本将自动运行"
echo "   按 Ctrl+D 结束录制"
echo ""

# 开始录制
asciinema rec "${RECORDING_FILE}" << 'ASCII_EOF'
# 设置终端环境
export TERM=xterm-256color

# 清屏
clear

# 显示欢迎信息
echo "=========================================="
echo "CloudLens CLI 完整功能测试"
echo "=========================================="
echo ""

# 运行CLI测试脚本
python3 tests/test_cli_full.py

# 等待用户查看结果
echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "按 Ctrl+D 结束录制"

# 保持终端打开
exec bash

ASCII_EOF

RECORD_EXIT_CODE=$?

if [ $RECORD_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ 录制完成！"
    echo ""
    echo "📁 文件位置："
    echo "   ${RECORDING_FILE}"
    echo ""
    echo "📊 文件大小："
    ls -lh "${RECORDING_FILE}" | awk '{print "   " $9 " (" $5 ")"}'
    echo ""
    echo "💡 回放录制："
    echo "   asciinema play ${RECORDING_FILE}"
    echo ""
    echo "💡 上传到 asciinema.org："
    echo "   asciinema upload ${RECORDING_FILE}"
    echo ""
    echo "💡 转换为 GIF（需要 agg）："
    echo "   # 安装: pip install agg"
    echo "   agg ${RECORDING_FILE} ${RECORDING_FILE%.cast}.gif"
else
    echo ""
    echo "❌ 录制失败，退出码: $RECORD_EXIT_CODE"
    exit 1
fi

