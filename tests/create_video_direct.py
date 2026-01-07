#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接生成CLI测试视频（不依赖ffmpeg）
使用PIL和opencv生成视频
"""

import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("test-recordings/cli")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
VIDEO_FILE = OUTPUT_DIR / f"cli_test_video_{TIMESTAMP}.mp4"
SCRIPT_FILE = OUTPUT_DIR / f"cli_test_script_{TIMESTAMP}.txt"
TIMING_FILE = OUTPUT_DIR / f"cli_test_timing_{TIMESTAMP}.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("🎬 开始生成CLI测试视频...")
print(f"📹 输出文件: {VIDEO_FILE}")

# 步骤1: 录制测试过程
print("📝 录制测试过程...")
try:
    test_script = Path("tests/test_cli_full.py")
    wrapper_script = OUTPUT_DIR / f"test_wrapper_{TIMESTAMP}.sh"
    
    with open(wrapper_script, "w") as f:
        f.write(f"""#!/bin/bash
export TERM=xterm-256color
clear
echo "=========================================="
echo "CloudLens CLI 完整功能测试"
echo "=========================================="
echo ""
python3 {test_script.absolute()}
echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
sleep 2
exit
""")
    wrapper_script.chmod(0o755)
    
    # 运行多个实际命令并捕获输出
    print("   运行实际CLI命令...")
    
    commands_to_run = [
        # 基础信息
        ("CLI帮助信息", ["python3", "-m", "cli.main", "--help"]),
        ("版本信息", ["python3", "-m", "cli.main", "--version"]),
        
        # 配置管理
        ("配置列表", ["python3", "-m", "cli.main", "config", "list"]),
        ("查看账号详情", ["python3", "-m", "cli.main", "config", "show", "ydzn"]),
        ("配置命令帮助", ["python3", "-m", "cli.main", "config", "--help"]),
        
        # 缓存管理
        ("缓存状态", ["python3", "-m", "cli.main", "cache", "status"]),
        ("缓存命令帮助", ["python3", "-m", "cli.main", "cache", "--help"]),
        
        # 资源查询 - 基础
        ("查询命令帮助", ["python3", "-m", "cli.main", "query", "--help"]),
        ("查询ECS资源(表格)", ["python3", "-m", "cli.main", "query", "resources", "ydzn", "ecs", "--format", "table"]),
        ("查询ECS资源(JSON)", ["python3", "-m", "cli.main", "query", "resources", "ydzn", "ecs", "--format", "json"]),
        ("查询ECS资源(CSV)", ["python3", "-m", "cli.main", "query", "resources", "ydzn", "ecs", "--format", "csv"]),
        ("查询ECS资源(无缓存)", ["python3", "-m", "cli.main", "query", "resources", "ydzn", "ecs", "--no-cache", "--format", "table"]),
        
        # 资源查询 - 不同资源类型
        ("查询RDS资源", ["python3", "-m", "cli.main", "query", "resources", "ydzn", "rds", "--format", "table"]),
        ("查询Redis资源", ["python3", "-m", "cli.main", "query", "resources", "ydzn", "redis", "--format", "table"]),
        ("查询SLB资源", ["python3", "-m", "cli.main", "query", "resources", "ydzn", "slb", "--format", "table"]),
        ("查询OSS资源", ["python3", "-m", "cli.main", "query", "resources", "ydzn", "oss", "--format", "table"]),
        
        # 资源查询 - 批量查询
        ("查询所有资源类型", ["python3", "-m", "cli.main", "query", "all", "ydzn"]),
        
        # 资源查询 - 指定区域
        ("查询ECS(指定区域)", ["python3", "-m", "cli.main", "query", "resources", "ydzn", "ecs", "--region", "cn-hangzhou", "--format", "table"]),
        
        # 分析功能
        ("分析命令帮助", ["python3", "-m", "cli.main", "analyze", "--help"]),
        ("成本分析(30天)", ["python3", "-m", "cli.main", "analyze", "cost", "--account", "ydzn", "--days", "30"]),
        ("成本分析(带趋势)", ["python3", "-m", "cli.main", "analyze", "cost", "--account", "ydzn", "--days", "30", "--trend"]),
        ("闲置资源检测(7天)", ["python3", "-m", "cli.main", "analyze", "idle", "--account", "ydzn", "--days", "7"]),
        ("闲置资源检测(30天)", ["python3", "-m", "cli.main", "analyze", "idle", "--account", "ydzn", "--days", "30"]),
        ("安全合规检查", ["python3", "-m", "cli.main", "analyze", "security", "--account", "ydzn"]),
        ("续费提醒", ["python3", "-m", "cli.main", "analyze", "renewal", "--account", "ydzn"]),
        
        # 账单管理
        ("账单命令帮助", ["python3", "-m", "cli.main", "bill", "--help"]),
        ("账单统计", ["python3", "-m", "cli.main", "bill", "stats"]),
        
        # 自动修复
        ("修复命令帮助", ["python3", "-m", "cli.main", "remediate", "--help"]),
        
        # 其他功能
        ("Dashboard帮助", ["python3", "-m", "cli.main", "dashboard", "--help"]),
        ("REPL帮助", ["python3", "-m", "cli.main", "repl", "--help"]),
        ("调度器帮助", ["python3", "-m", "cli.main", "scheduler", "--help"]),
    ]
    
    all_output = []
    all_output.append("=" * 60)
    all_output.append("CloudLens CLI 完整功能测试")
    all_output.append("=" * 60)
    all_output.append("")
    
    for cmd_name, cmd in commands_to_run:
        all_output.append("")
        all_output.append("=" * 60)
        all_output.append(f"命令: {cmd_name}")
        all_output.append(f"执行: {' '.join(cmd)}")
        all_output.append("=" * 60)
        all_output.append("")
        
        try:
            result = subprocess.run(
                cmd,
                timeout=60,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            
            # 添加输出
            if result.stdout:
                all_output.append(result.stdout)
            if result.stderr and "Traceback" not in result.stderr:
                all_output.append(result.stderr)
            
            # 如果输出太长，截取前150行（增加显示内容）
            output_lines = '\n'.join(all_output).split('\n')
            if len(output_lines) > 300:
                all_output = output_lines[:300]
                all_output.append("\n... (输出已截断，实际测试包含更多内容) ...\n")
                break
                
        except subprocess.TimeoutExpired:
            all_output.append("⏰ 命令执行超时")
        except Exception as e:
            all_output.append(f"❌ 执行失败: {e}")
    
    all_output.append("")
    all_output.append("=" * 60)
    all_output.append("测试完成！")
    all_output.append("=" * 60)
    
    # 保存输出
    output_text = '\n'.join(all_output)
    with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(output_text)
    
    print(f"   输出已保存 ({len(output_text)} 字符)")
    
    print("✅ 录制完成")
    
except Exception as e:
    print(f"❌ 录制失败: {e}")
    sys.exit(1)

# 步骤2: 读取录制内容
print("📖 读取录制内容...")
try:
    with open(SCRIPT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    lines = [line for line in content.split('\n') if line.strip()]
    print(f"   读取 {len(lines)} 行内容")
    
except Exception as e:
    print(f"❌ 读取失败: {e}")
    sys.exit(1)

# 步骤3: 生成视频
print("🎨 生成视频文件...")
try:
    from PIL import Image, ImageDraw, ImageFont
    import cv2
    import numpy as np
    
    # 视频参数
    width, height = 1920, 1080
    fps = 15  # 提高帧率使更流畅
    font_size = 30  # 稍微减小字体以显示更多内容
    line_height = font_size + 8
    padding = 50
    max_lines = (height - 2 * padding - 100) // line_height  # 为标题和进度条留空间
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(VIDEO_FILE), fourcc, fps, (width, height))
    
    # 创建字体（支持中文）- 优先使用PingFang（更美观）
    font = None
    font_paths = [
        ("/System/Library/Fonts/PingFang.ttc", [0, 1, 2, 3]),  # 苹方（最美观，首选）
        ("/System/Library/Fonts/Supplemental/PingFang SC.ttc", [0, 1]),  # 苹方简体
        ("/Library/Fonts/PingFang.ttc", [0, 1]),  # 其他位置的PingFang
        ("/System/Library/Fonts/STHeiti Light.ttc", [0]),  # 黑体（备选）
        ("/System/Library/Fonts/Helvetica.ttc", [0]),  # Helvetica（备选）
    ]
    
    for path, indices in font_paths:
        if Path(path).exists():
            try:
                if path.endswith('.ttc'):
                    # TTC字体文件，尝试不同的索引
                    for index in indices:
                        try:
                            font = ImageFont.truetype(path, font_size, index=index)
                            # 测试是否能渲染中文
                            test_img = Image.new('RGB', (200, 50), 'white')
                            test_draw = ImageDraw.Draw(test_img)
                            test_draw.text((10, 10), '测试中文CloudLens', fill='black', font=font)
                            font_name = "PingFang" if "PingFang" in path else "STHeiti" if "STHeiti" in path else "Helvetica"
                            print(f"   使用字体: {font_name} ({path}, 索引 {index})")
                            break
                        except Exception as e:
                            continue
                    if font:
                        break
                else:
                    font = ImageFont.truetype(path, font_size)
                    test_img = Image.new('RGB', (200, 50), 'white')
                    test_draw = ImageDraw.Draw(test_img)
                    test_draw.text((10, 10), '测试中文', fill='black', font=font)
                    print(f"   使用字体: {path}")
                    break
            except Exception as e:
                continue
    
    if font is None:
        print("   ⚠️  未找到合适字体，尝试加载默认字体")
        try:
            font = ImageFont.load_default()
        except:
            # 如果默认字体也不行，创建一个简单的字体
            font = ImageFont.load_default()
    
    # 生成视频帧
    total_frames = 0
    display_lines = []
    
    for i, line in enumerate(lines):
        # 限制行长度
        line = line[:150] if len(line) > 150 else line
        
        # 添加到显示列表
        display_lines.append(line)
        if len(display_lines) > max_lines:
            display_lines.pop(0)
        
        # 每行生成2-4帧（根据内容类型调整显示时间）
        # 命令分隔行显示更久，数据行显示稍短
        if line.strip().startswith('=') or '命令:' in line or '执行:' in line:
            frame_count = 4  # 分隔线和命令标题显示更久
        elif any(keyword in line.lower() for keyword in ['错误', 'error', '失败', 'traceback']):
            frame_count = 5  # 错误信息显示更久
        else:
            frame_count = 2  # 普通内容
        
        for frame_idx in range(frame_count):
            # 创建图像
            img = Image.new('RGB', (width, height), color=(20, 20, 20))
            draw = ImageDraw.Draw(img)
            
            # 绘制标题（更美观的样式）
            title_text = "CloudLens CLI 完整功能测试"
            # 绘制标题背景
            title_bbox = draw.textbbox((padding, 20), title_text, font=font)
            draw.rectangle(
                [(padding - 10, 15), (title_bbox[2] + 10, title_bbox[3] + 10)],
                fill=(30, 60, 120),
                outline=(100, 200, 255),
                width=2
            )
            draw.text((padding, 20), title_text, 
                     fill=(255, 255, 255), font=font)
            
            # 绘制内容行
            y = padding + 80
            for j, text_line in enumerate(display_lines):
                # 确保文本是UTF-8编码的字符串
                if isinstance(text_line, bytes):
                    text_line = text_line.decode('utf-8', errors='replace')
                elif not isinstance(text_line, str):
                    text_line = str(text_line)
                
                # 清理文本，移除控制字符，但保留所有可打印字符（包括中文）
                # 保留ASCII可打印字符(32-126)和中文字符(\u4e00-\u9fff)
                cleaned = []
                for char in text_line:
                    code = ord(char)
                    if (32 <= code <= 126) or ('\u4e00' <= char <= '\u9fff') or char in '\n\t':
                        cleaned.append(char)
                text_line = ''.join(cleaned)
                
                # 高亮某些关键词
                color = (220, 220, 220)
                if any(keyword in text_line.lower() for keyword in ['成功', 'success', '✅', '测试', '完成']):
                    color = (100, 255, 100)
                elif any(keyword in text_line.lower() for keyword in ['错误', 'error', '失败', '❌', 'traceback']):
                    color = (255, 100, 100)
                elif any(keyword in text_line.lower() for keyword in ['警告', 'warning', '⚠️']):
                    color = (255, 200, 100)
                elif any(keyword in text_line.lower() for keyword in ['命令', 'command', '执行', '执行:']):
                    color = (100, 200, 255)  # 蓝色
                elif any(keyword in text_line.lower() for keyword in ['实例', 'instance', '资源', 'resource', '账号', 'account', 'id', 'name']):
                    color = (255, 255, 150)  # 黄色
                elif any(keyword in text_line.lower() for keyword in ['配置', 'config', '缓存', 'cache']):
                    color = (150, 255, 150)  # 浅绿色
                elif text_line.strip().startswith('='):
                    color = (100, 100, 100)  # 分隔线灰色
                
                # 处理长行，自动换行
                max_width = width - 2 * padding
                try:
                    # 尝试绘制，如果失败可能是字体问题
                    bbox = draw.textbbox((0, 0), text_line, font=font)
                    text_width = bbox[2] - bbox[0]
                    
                    if text_width > max_width:
                        # 文本太长，需要换行
                        words = text_line.split()
                        current_line = ""
                        for word in words:
                            test_line = current_line + " " + word if current_line else word
                            test_bbox = draw.textbbox((0, 0), test_line, font=font)
                            if test_bbox[2] - test_bbox[0] > max_width and current_line:
                                draw.text((padding, y), current_line, fill=color, font=font)
                                y += line_height
                                current_line = word
                            else:
                                current_line = test_line
                        if current_line:
                            draw.text((padding, y), current_line, fill=color, font=font)
                            y += line_height
                    else:
                        draw.text((padding, y), text_line, fill=color, font=font)
                        y += line_height
                except Exception:
                    # 如果绘制失败，使用简单方法
                    try:
                        draw.text((padding, y), text_line[:100], fill=color, font=font)
                        y += line_height
                    except:
                        pass
                
                if y > height - padding - 40:
                    break
            
            # 绘制进度信息（更美观）
            progress_text = f"进度: {i+1}/{len(lines)}"
            progress_percent = int((i+1) / len(lines) * 100)
            # 进度条背景
            bar_width = 200
            bar_height = 8
            bar_x = width - bar_width - 20
            bar_y = height - 35
            draw.rectangle(
                [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
                fill=(50, 50, 50),
                outline=(100, 100, 100)
            )
            # 进度条填充
            fill_width = int(bar_width * progress_percent / 100)
            draw.rectangle(
                [(bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height)],
                fill=(100, 200, 255)
            )
            # 进度文本
            draw.text((bar_x - 80, bar_y - 5), progress_text, 
                     fill=(200, 200, 200), font=font)
            
            # 转换为OpenCV格式
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            out.write(frame)
            total_frames += 1
        
        # 每100行显示进度
        if (i + 1) % 100 == 0:
            print(f"   已处理 {i+1}/{len(lines)} 行 ({total_frames} 帧)")
    
    # 添加结束帧（停留3秒）
    for _ in range(fps * 3):
        img = Image.new('RGB', (width, height), color=(20, 20, 20))
        draw = ImageDraw.Draw(img)
        draw.text((width//2 - 200, height//2), "测试完成！", 
                 fill=(100, 255, 100), font=font)
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        out.write(frame)
        total_frames += 1
    
    out.release()
    print(f"✅ 视频已生成: {VIDEO_FILE}")
    print(f"   总帧数: {total_frames}")
    print(f"   时长: {total_frames/fps:.1f}秒")
    
    # 显示文件信息
    file_size = VIDEO_FILE.stat().st_size / (1024 * 1024)
    print(f"   文件大小: {file_size:.2f} MB")
    
except ImportError as e:
    print(f"❌ 缺少依赖: {e}")
    print("   正在安装依赖...")
    subprocess.run([sys.executable, "-m", "pip", "install", "opencv-python", "pillow", "--quiet"])
    print("   请重新运行此脚本")
    sys.exit(1)
except Exception as e:
    print(f"❌ 生成失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ 完成！")
print(f"📹 视频文件: {VIDEO_FILE}")
print(f"💡 播放: open {VIDEO_FILE}")

