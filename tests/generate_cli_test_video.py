#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成CLI测试视频
使用ffmpeg录制终端会话并转换为mp4
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path
from datetime import datetime

# 配置
OUTPUT_DIR = Path("test-recordings/cli")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
VIDEO_FILE = OUTPUT_DIR / f"cli_test_video_{TIMESTAMP}.mp4"
TEST_SCRIPT = Path(__file__).parent / "test_cli_full.py"

# 确保输出目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_terminal_size():
    """获取终端大小"""
    try:
        import shutil
        size = shutil.get_terminal_size()
        return size.columns, size.lines
    except:
        return 120, 40

def run_test_with_recording():
    """运行测试并录制视频"""
    print("🎬 开始录制CLI测试视频...")
    print(f"📹 输出文件: {VIDEO_FILE}")
    
    # 检查ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 未找到 ffmpeg，尝试安装...")
        print("   请运行: brew install ffmpeg")
        return False
    
    # 获取终端大小
    cols, rows = get_terminal_size()
    width = cols * 8  # 假设每个字符8像素宽
    height = rows * 16  # 假设每个字符16像素高
    
    # 使用script命令录制，然后用ffmpeg转换
    script_file = OUTPUT_DIR / f"cli_test_script_{TIMESTAMP}.txt"
    timing_file = OUTPUT_DIR / f"cli_test_timing_{TIMESTAMP}.txt"
    
    print(f"📝 录制终端会话...")
    
    # 创建测试脚本包装器
    test_wrapper = f"""#!/bin/bash
export TERM=xterm-256color
clear
echo "=========================================="
echo "CloudLens CLI 完整功能测试"
echo "=========================================="
echo ""
python3 {TEST_SCRIPT}
echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
sleep 2
exit
"""
    
    wrapper_file = OUTPUT_DIR / f"test_wrapper_{TIMESTAMP}.sh"
    with open(wrapper_file, "w") as f:
        f.write(test_wrapper)
    os.chmod(wrapper_file, 0o755)
    
    # 使用script录制
    try:
        cmd = ["script", "-q", "-t", "2>" + str(timing_file), str(script_file), str(wrapper_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"⚠️  script命令退出码: {result.returncode}")
    except subprocess.TimeoutExpired:
        print("⚠️  测试超时，但继续处理录制文件...")
    except Exception as e:
        print(f"❌ 录制失败: {e}")
        return False
    
    # 检查文件是否存在
    if not script_file.exists() or not timing_file.exists():
        print("❌ 录制文件未生成")
        return False
    
    print(f"✅ 终端会话录制完成")
    print(f"📹 转换为视频文件...")
    
    # 使用scriptreplay + ffmpeg转换为视频
    # 先尝试使用asciinema的方式，如果不行就用其他方法
    try:
        # 方法1: 使用scriptreplay + ffmpeg
        # 创建一个临时脚本来回放并录制
        replay_script = f"""#!/bin/bash
scriptreplay -t {timing_file} {script_file}
"""
        replay_file = OUTPUT_DIR / f"replay_{TIMESTAMP}.sh"
        with open(replay_file, "w") as f:
            f.write(replay_script)
        os.chmod(replay_file, 0o755)
        
        # 使用ffmpeg录制终端回放
        # 需要知道终端窗口的位置，这里使用一个简单的方法
        # 使用x11grab或avfoundation（macOS）
        
        # macOS使用avfoundation
        ffmpeg_cmd = [
            "ffmpeg",
            "-f", "avfoundation",
            "-framerate", "30",
            "-video_size", f"{width}x{height}",
            "-i", "1:0",  # 屏幕录制
            "-t", "180",  # 最多3分钟
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            str(VIDEO_FILE),
            "-y"
        ]
        
        # 实际上，更好的方法是直接使用asciinema + agg
        # 或者使用termtosvg等工具
        
        print("💡 使用替代方案：生成asciinema格式并转换...")
        
        # 使用asciinema格式（如果可用）
        asciinema_file = OUTPUT_DIR / f"cli_test_{TIMESTAMP}.cast"
        
        # 读取script文件并转换为asciinema格式
        with open(script_file, "r", encoding="utf-8", errors="ignore") as f:
            script_content = f.read()
        
        with open(timing_file, "r") as f:
            timing_lines = f.readlines()
        
        # 创建简单的asciinema格式
        import json
        asciinema_data = {
            "version": 2,
            "width": cols,
            "height": rows,
            "timestamp": int(time.time()),
            "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"},
            "stdout": []
        }
        
        # 解析timing文件并创建事件
        current_time = 0.0
        for line in script_content.split('\n'):
            if line:
                # 简单处理：每行作为一个输出事件
                asciinema_data["stdout"].append([current_time, "o", line + "\n"])
                current_time += 0.1  # 假设每行间隔0.1秒
        
        with open(asciinema_file, "w") as f:
            json.dump(asciinema_data, f)
        
        print(f"✅ 生成asciinema文件: {asciinema_file}")
        
        # 尝试使用agg转换为gif，然后转换为mp4
        try:
            # 检查是否有agg
            subprocess.run(["agg", "--version"], capture_output=True, check=True)
            gif_file = OUTPUT_DIR / f"cli_test_{TIMESTAMP}.gif"
            print("🎨 转换为GIF...")
            subprocess.run(["agg", str(asciinema_file), str(gif_file)], check=True)
            
            # 将GIF转换为MP4
            print("🎬 转换为MP4...")
            subprocess.run([
                "ffmpeg", "-i", str(gif_file),
                "-vf", "scale=1920:1080:flags=lanczos",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-y",
                str(VIDEO_FILE)
            ], check=True, capture_output=True)
            
            print(f"✅ 视频文件已生成: {VIDEO_FILE}")
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  agg未安装，使用termtosvg或其他方法...")
            
            # 尝试使用termtosvg
            try:
                subprocess.run(["termtosvg", "--version"], capture_output=True, check=True)
                svg_file = OUTPUT_DIR / f"cli_test_{TIMESTAMP}.svg"
                # termtosvg需要不同的输入格式
                print("⚠️  请手动使用termtosvg或agg转换")
                print(f"   文件: {asciinema_file}")
                return False
            except:
                pass
            
            # 最后的方法：直接使用ffmpeg录制（需要交互）
            print("💡 使用scriptreplay + 手动录制屏幕")
            print(f"   运行: scriptreplay -t {timing_file} {script_file}")
            print(f"   同时使用屏幕录制工具录制终端窗口")
            return False
            
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_test_with_recording()
    sys.exit(0 if success else 1)

