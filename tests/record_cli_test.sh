#!/bin/bash
# CloudLens CLI 完整功能测试录制脚本
# 使用script命令录制终端会话

set -e

# 配置
OUTPUT_DIR="test-recordings/cli"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RECORDING_FILE="${OUTPUT_DIR}/cli_test_recording_${TIMESTAMP}.txt"
TIMING_FILE="${OUTPUT_DIR}/cli_test_timing_${TIMESTAMP}.txt"
VIDEO_OUTPUT="${OUTPUT_DIR}/cli_test_video_${TIMESTAMP}.mp4"

# 确保输出目录存在
mkdir -p "${OUTPUT_DIR}"

echo "=========================================="
echo "CloudLens CLI 完整功能测试录制"
echo "=========================================="
echo "📹 录制文件: ${RECORDING_FILE}"
echo "⏱️  时间文件: ${TIMING_FILE}"
echo "=========================================="
echo ""

# 检查依赖
if ! command -v script &> /dev/null; then
    echo "❌ 未找到 script 命令"
    echo "   在 macOS 上，script 命令应该已内置"
    exit 1
fi

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3"
    exit 1
fi

# 开始录制
echo "🎬 开始录制..."
echo "   按 Ctrl+D 或输入 exit 结束录制"
echo ""

# 使用script命令录制（macOS版本）
# -t 2> 将时间戳输出到stderr，重定向到文件
script -q -t 2>"${TIMING_FILE}" "${RECORDING_FILE}" << 'SCRIPT_EOF'
# 设置终端环境
export TERM=xterm-256color
export PS1='\$ '

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

# 保持终端打开，等待用户结束
exec bash

SCRIPT_EOF

RECORD_EXIT_CODE=$?

if [ $RECORD_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ 录制完成！"
    echo ""
    echo "📁 文件位置："
    echo "   - 录制文件: ${RECORDING_FILE}"
    echo "   - 时间文件: ${TIMING_FILE}"
    echo ""
    echo "📊 文件大小："
    ls -lh "${RECORDING_FILE}" "${TIMING_FILE}" 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}'
    echo ""
    echo "💡 回放录制："
    echo "   scriptreplay -t ${TIMING_FILE} ${RECORDING_FILE}"
    echo ""
    echo "💡 转换为视频（需要asciinema2gif或类似工具）："
    echo "   # 可以使用 asciinema 或其他工具转换"
else
    echo ""
    echo "❌ 录制失败，退出码: $RECORD_EXIT_CODE"
    exit 1
fi

