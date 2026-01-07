#!/bin/bash
# 直接生成CLI测试视频文件

set -e

OUTPUT_DIR="test-recordings/cli"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
VIDEO_FILE="${OUTPUT_DIR}/cli_test_video_${TIMESTAMP}.mp4"
SCRIPT_FILE="${OUTPUT_DIR}/cli_test_script_${TIMESTAMP}.txt"
TIMING_FILE="${OUTPUT_DIR}/cli_test_timing_${TIMESTAMP}.txt"

mkdir -p "${OUTPUT_DIR}"

echo "🎬 开始生成CLI测试视频..."
echo "📹 输出文件: ${VIDEO_FILE}"

# 检查依赖
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ 需要安装 ffmpeg"
    echo "   运行: brew install ffmpeg"
    exit 1
fi

# 使用script录制测试过程
echo "📝 录制测试过程..."
script -q -t 2>"${TIMING_FILE}" "${SCRIPT_FILE}" << 'EOF'
export TERM=xterm-256color
clear
echo "=========================================="
echo "CloudLens CLI 完整功能测试"
echo "=========================================="
echo ""
python3 tests/test_cli_full.py
echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
sleep 2
exit
EOF

# 检查文件
if [ ! -f "${SCRIPT_FILE}" ] || [ ! -f "${TIMING_FILE}" ]; then
    echo "❌ 录制文件未生成"
    exit 1
fi

echo "✅ 录制完成"
echo "🎬 转换为视频..."

# 方法1: 尝试使用asciinema + agg
if command -v agg &> /dev/null; then
    echo "使用 agg 转换为视频..."
    
    # 先转换为asciinema格式
    ASCIINEMA_FILE="${OUTPUT_DIR}/cli_test_${TIMESTAMP}.cast"
    GIF_FILE="${OUTPUT_DIR}/cli_test_${TIMESTAMP}.gif"
    
    # 使用scriptreplay生成asciinema格式（简化版）
    # 这里我们直接使用agg从script文件转换
    # 但agg需要asciinema格式，所以我们需要转换
    
    # 简单方法：使用termtosvg或直接生成
    echo "⚠️  需要asciinema格式，使用替代方案..."
fi

# 方法2: 使用ffmpeg直接录制（需要知道终端窗口）
# 在macOS上，我们可以使用avfoundation

# 方法3: 使用Python脚本生成视频
echo "使用Python脚本生成视频..."
python3 << PYTHON_EOF
import subprocess
import sys
from pathlib import Path

script_file = Path("${SCRIPT_FILE}")
timing_file = Path("${TIMING_FILE}")
video_file = Path("${VIDEO_FILE}")

# 读取script文件内容
with open(script_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# 创建一个简单的视频生成脚本
# 使用PIL和opencv生成视频帧
try:
    from PIL import Image, ImageDraw, ImageFont
    import cv2
    import numpy as np
    
    # 视频参数
    width, height = 1920, 1080
    fps = 30
    font_size = 24
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(video_file), fourcc, fps, (width, height))
    
    # 创建字体
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # 解析内容并生成帧
    lines = content.split('\n')
    current_line = 0
    frame_count = 0
    max_frames = len(lines) * 2  # 每行显示2帧
    
    print(f"生成 {max_frames} 帧...")
    
    for i, line in enumerate(lines[:100]):  # 限制前100行
        # 创建图像
        img = Image.new('RGB', (width, height), color='black')
        draw = ImageDraw.Draw(img)
        
        # 绘制文本
        y = 50
        start_line = max(0, i - 40)  # 显示最近40行
        for j in range(start_line, min(i + 1, len(lines))):
            text = lines[j][:200]  # 限制每行长度
            draw.text((50, y), text, fill='white', font=font)
            y += font_size + 5
            if y > height - 50:
                break
        
        # 转换为OpenCV格式
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # 写入多帧（让每行显示更久）
        for _ in range(2):
            out.write(frame)
            frame_count += 1
    
    out.release()
    print(f"✅ 视频已生成: {video_file} ({frame_count} 帧)")
    
except ImportError as e:
    print(f"❌ 缺少依赖: {e}")
    print("   安装: pip3 install opencv-python pillow")
    sys.exit(1)
except Exception as e:
    print(f"❌ 生成失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_EOF

if [ -f "${VIDEO_FILE}" ]; then
    echo ""
    echo "✅ 视频文件已生成！"
    echo "📹 文件: ${VIDEO_FILE}"
    ls -lh "${VIDEO_FILE}"
    echo ""
    echo "💡 播放视频:"
    echo "   open ${VIDEO_FILE}"
else
    echo "❌ 视频文件未生成"
    exit 1
fi

