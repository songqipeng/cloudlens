#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudLens Web使用指南视频生成脚本 - 5分钟精简版
基于用户确认的方案生成
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, Route, Request
from typing import List, Dict, Optional
import subprocess
import json
import re

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 视频输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "test-recordings" / "web"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 视频配置 - 5分钟精简版
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
BASE_URL = "http://localhost:3000"
BACKEND_URL = "http://127.0.0.1:8000"

# ============= 数据替换配置 =============
REPLACEMENT_CONFIG = {
    'account_name': {
        'demo': 'demo'  # 保持demo不变
    },
    'ecs': {
        'replace_id': True,
        'replace_name': True,
        'id_prefix': 'i-demo',
        'name_templates': [
            'web-server-{}',
            'api-server-{}',
            'db-server-{}',
            'cache-server-{}',
            'app-server-{}',
            'worker-server-{}'
        ]
    }
}

# 全局映射表
RESOURCE_MAPPING = {
    'ids': {},
    'names': {},
    'counter': 0
}

# 功能模块列表 - 5分钟精简版（更短的等待时间）
FEATURES = [
    {
        "name": "开场介绍",
        "path": "/",
        "description": "CloudLens多云资源治理平台",
        "narration": "CloudLens是一款多云资源治理平台，帮助企业实现云资源的统一管理、成本优化和安全合规。接下来，让我们快速了解主要功能。",
        "wait_time": 3,
        "actions": [
            {"type": "wait", "time": 2},
            {"type": "scroll", "direction": "down", "pixels": 400},
            {"type": "wait", "time": 1},
            {"type": "scroll", "direction": "down", "pixels": 400},
            {"type": "wait", "time": 1},
        ]
    },
    {
        "name": "资源查询",
        "path": "/resources",
        "description": "查看和管理云资源",
        "narration": "在资源管理页面，可以查看所有云资源。支持按类型筛选，比如ECS实例、RDS数据库等。可以通过搜索快速定位资源，点击可以查看详细信息，包括配置、成本和使用情况。",
        "wait_time": 4,
        "actions": [
            {"type": "wait", "time": 2},
            {"type": "scroll", "direction": "down", "pixels": 400},
            {"type": "wait", "time": 1},
            {"type": "scroll", "direction": "down", "pixels": 400},
            {"type": "wait", "time": 1},
        ]
    },
    {
        "name": "成本分析",
        "path": "/cost",
        "description": "成本趋势和构成分析",
        "narration": "成本分析模块提供全面的成本视图。这里展示了成本趋势变化，可以看到最近的成本波动。下方是成本构成分析，按产品类型、区域等维度展示。当前总成本清晰可见，帮助快速掌握支出情况。",
        "wait_time": 4,
        "actions": [
            {"type": "wait", "time": 2},
            {"type": "scroll", "direction": "down", "pixels": 500},
            {"type": "wait", "time": 1.5},
            {"type": "scroll", "direction": "down", "pixels": 500},
            {"type": "wait", "time": 1},
        ]
    },
    {
        "name": "闲置资源",
        "path": "/",
        "description": "识别闲置资源",
        "narration": "仪表盘页面显示了闲置资源统计。系统自动检测CPU、内存使用率，标记出闲置实例。这里显示了潜在节省金额，及时清理可以显著降低成本。",
        "wait_time": 3,
        "actions": [
            {"type": "wait", "time": 2},
            {"type": "scroll", "direction": "down", "pixels": 500},
            {"type": "wait", "time": 1},
            {"type": "scroll", "direction": "down", "pixels": 500},
            {"type": "wait", "time": 1},
        ]
    },
    {
        "name": "安全合规",
        "path": "/security",
        "description": "安全合规检查",
        "narration": "安全合规页面提供全面的安全检查。包括安全组配置、访问控制、数据加密等多个维度。系统会自动识别风险并给出修复建议。",
        "wait_time": 12,  # 增加等待时间，确保数据加载完成
        "actions": [
            {"type": "wait", "time": 8},  # 等待数据加载（小兔子跑完）
            {"type": "scroll", "direction": "down", "pixels": 400},
            {"type": "wait", "time": 1.5},
            {"type": "scroll", "direction": "down", "pixels": 400},
            {"type": "wait", "time": 1.5},
        ]
    },
    {
        "name": "预算管理",
        "path": "/budgets",
        "description": "预算管理和告警",
        "narration": "预算管理功能帮助控制云支出。可以设置月度预算，系统会实时监控预算执行情况。当支出接近或超过预算时，会自动发送告警通知。",
        "wait_time": 2,
        "actions": [
            {"type": "wait", "time": 1.5},
            {"type": "scroll", "direction": "down", "pixels": 300},
            {"type": "wait", "time": 1},
        ]
    },
    {
        "name": "折扣分析",
        "path": "/discounts",
        "description": "折扣使用分析",
        "narration": "折扣分析展示了各类折扣的使用情况，包括预留实例、节省计划等。帮助优化折扣策略，最大化成本节省。",
        "wait_time": 1.5,
        "actions": [
            {"type": "wait", "time": 1.5},
            {"type": "scroll", "direction": "down", "pixels": 300},
            {"type": "wait", "time": 0.8},
        ]
    },
    {
        "name": "虚拟标签",
        "path": "/virtual-tags",
        "description": "虚拟标签和成本分配",
        "narration": "虚拟标签功能通过规则引擎自动为资源打标签。支持灵活的成本分配，帮助精确核算各部门、项目的云成本。",
        "wait_time": 1.5,
        "actions": [
            {"type": "wait", "time": 1.5},
            {"type": "scroll", "direction": "down", "pixels": 300},
            {"type": "wait", "time": 0.8},
        ]
    },
    {
        "name": "优化建议",
        "path": "/optimization",
        "description": "AI优化建议",
        "narration": "优化建议模块由AI驱动，分析资源使用模式，提供个性化的优化方案。包括实例规格调整、购买建议等，并预估节省金额。",
        "wait_time": 2,
        "actions": [
            {"type": "wait", "time": 2},
            {"type": "scroll", "direction": "down", "pixels": 400},
            {"type": "wait", "time": 1},
        ]
    },
    {
        "name": "报告生成",
        "path": "/reports",
        "description": "生成分析报告",
        "narration": "报告生成功能支持导出专业的分析报告，包括资源清单、成本分析、优化建议等。可以定期生成并发送给相关人员。",
        "wait_time": 1.5,
        "actions": [
            {"type": "wait", "time": 1.5},
            {"type": "scroll", "direction": "down", "pixels": 300},
            {"type": "wait", "time": 0.8},
        ]
    },
]


class VideoGuideGenerator:
    """5分钟视频指南生成器"""
    
    def __init__(self):
        self.browser: Browser = None
        self.page: Page = None
        self.video_paths: List[str] = []
        self.narration_texts: List[Dict] = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.api_intercept_stats = {'total': 0, 'modified': 0}
        
    async def setup(self):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        
        # 启动Chrome（普通窗口模式，避免应用模式导致的黑屏）
        self.browser = await playwright.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
                f'--window-size={VIDEO_WIDTH},{VIDEO_HEIGHT}',
            ]
        )
        
        # 创建上下文（延迟启动录制）
        context = await self.browser.new_context(
            viewport={'width': VIDEO_WIDTH, 'height': VIDEO_HEIGHT},
            locale='zh-CN',
            no_viewport=False,
        )
        
        self.page = await context.new_page()
        self.page.set_default_timeout(30000)
        self.page.set_default_navigation_timeout(30000)
        
        await self.page.set_extra_http_headers({
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        
        # 启用API拦截
        print("🔧 启用API数据拦截...")
        await self.page.route('**/api/**', self.handle_api_route)
        print("   ✅ API拦截已启用")
        print()
        
        # 先访问首页，等待完全加载后再开始录制
        print("🌐 预加载首页，避免黑屏...")
        await self.page.goto(BASE_URL, wait_until="networkidle")
        await asyncio.sleep(3)
        print("   ✅ 首页预加载完成")
        print()
        
        # 现在开始录制
        print("🎥 开始录制视频...")
        await context.close()
        
        # 重新创建带录制功能的上下文
        context = await self.browser.new_context(
            viewport={'width': VIDEO_WIDTH, 'height': VIDEO_HEIGHT},
            record_video_dir=str(OUTPUT_DIR),
            record_video_size={'width': VIDEO_WIDTH, 'height': VIDEO_HEIGHT},
            locale='zh-CN',
        )
        
        self.page = await context.new_page()
        self.page.set_default_timeout(30000)
        self.page.set_default_navigation_timeout(30000)
        
        await self.page.set_extra_http_headers({
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        
        # 重新启用API拦截
        await self.page.route('**/api/**', self.handle_api_route)
        print("   ✅ 录制已启动（无黑屏）")
        print()
        
    async def handle_api_route(self, route: Route, request: Request):
        """拦截并处理API请求，替换ECS数据"""
        self.api_intercept_stats['total'] += 1
        
        try:
            response = await route.fetch()
            try:
                body = await response.json()
            except:
                await route.fulfill(response=response)
                return
            
            url = request.url
            modified = False
            
            if '/api/resources' in url or '/api/dashboard' in url or '/api/idle' in url:
                body = self.replace_ecs_resources(body)
                modified = True
            
            if modified:
                self.api_intercept_stats['modified'] += 1
            
            await route.fulfill(
                status=response.status,
                headers=dict(response.headers),
                body=json.dumps(body, ensure_ascii=False)
            )
        
        except Exception as e:
            try:
                await route.fallback()
            except:
                pass
    
    def replace_ecs_resources(self, data):
        """替换ECS资源的ID和名称"""
        if isinstance(data, dict):
            new_data = {}
            for key, value in data.items():
                if key in ['instanceId', 'instance_id', 'id'] and isinstance(value, str) and value.startswith('i-'):
                    new_data[key] = self.get_fake_ecs_id(value)
                elif key in ['instanceName', 'instance_name', 'name'] and isinstance(value, str):
                    new_data[key] = self.get_fake_ecs_name(value)
                else:
                    new_data[key] = self.replace_ecs_resources(value)
            return new_data
        elif isinstance(data, list):
            return [self.replace_ecs_resources(item) for item in data]
        else:
            return data
    
    def get_fake_ecs_id(self, real_id: str) -> str:
        """生成一致的假ECS ID"""
        if real_id not in RESOURCE_MAPPING['ids']:
            RESOURCE_MAPPING['counter'] += 1
            fake_id = f"{REPLACEMENT_CONFIG['ecs']['id_prefix']}{RESOURCE_MAPPING['counter']:04d}"
            RESOURCE_MAPPING['ids'][real_id] = fake_id
        return RESOURCE_MAPPING['ids'][real_id]
    
    def get_fake_ecs_name(self, real_name: str) -> str:
        """生成一致的假ECS名称"""
        if real_name not in RESOURCE_MAPPING['names']:
            templates = REPLACEMENT_CONFIG['ecs']['name_templates']
            index = len(RESOURCE_MAPPING['names'])
            template = templates[index % len(templates)]
            fake_name = template.format(index + 1)
            RESOURCE_MAPPING['names'][real_name] = fake_name
        return RESOURCE_MAPPING['names'][real_name]
    
    async def navigate_to_page(self, path: str, description: str):
        """导航到指定页面"""
        print(f"📹 正在录制: {description}")
        
        url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
        
        try:
            await self.page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)  # 页面稳定等待
        except Exception as e:
            print(f"   ⚠️  导航失败: {e}")
            await asyncio.sleep(2)
    
    async def execute_actions(self, actions: List[Dict]):
        """执行页面操作"""
        for action in actions:
            try:
                if action["type"] == "wait":
                    if "selector" in action:
                        await self.page.wait_for_selector(action["selector"], timeout=action.get("timeout", 10000))
                    elif "time" in action:
                        await asyncio.sleep(action["time"])
                
                elif action["type"] == "scroll":
                    if action["direction"] == "down":
                        await self.page.mouse.wheel(0, action.get("pixels", 300))
                    elif action["direction"] == "up":
                        await self.page.mouse.wheel(0, -action.get("pixels", 300))
                    await asyncio.sleep(0.5)
                
                elif action["type"] == "click":
                    await self.page.click(action["selector"])
                    await asyncio.sleep(0.5)
            
            except Exception as e:
                print(f"   ⚠️  操作失败: {e}")
                continue
    
    def generate_narration_audio(self, text: str, output_file: str) -> tuple:
        """生成中文语音"""
        try:
            cmd = [
                "say",
                "-v", "Ting-Ting",  # 中文语音
                "-o", output_file,
                "--data-format=LEF32@22050",
                text
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(output_file):
                # 获取音频时长
                probe_cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    output_file
                ]
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                duration = float(probe_result.stdout.strip()) if probe_result.stdout.strip() else 0
                
                return True, duration
            else:
                return False, 0
        
        except Exception as e:
            print(f"   ⚠️  语音生成失败: {e}")
            return False, 0
    
    async def record_feature(self, feature: Dict, start_time: float, narration_duration: float = 0.0):
        """录制单个功能模块"""
        navigation_start = time.time() - start_time
        
        await self.navigate_to_page(feature["path"], feature["description"])
        
        if "actions" in feature:
            await self.execute_actions(feature["actions"])
        
        await asyncio.sleep(2)  # 确保页面完全稳定
        
        # 记录语音开始时间（页面稳定后）
        narration_start_time = time.time() - start_time
        
        # 等待语音播放完成
        if narration_duration > 0:
            wait_time = narration_duration + 0.5
            await asyncio.sleep(wait_time)
        else:
            await asyncio.sleep(feature.get("wait_time", 3))
        
        total_duration = time.time() - start_time - navigation_start
        
        # 记录旁白信息
        self.narration_texts.append({
            "feature": feature["name"],
            "text": feature["narration"],
            "start": narration_start_time,
            "end": narration_start_time + narration_duration if narration_duration > 0 else narration_start_time + feature.get("wait_time", 3),
            "duration": narration_duration
        })
        
        print(f"   ✅ 完成录制 (总时长: {total_duration:.1f}秒, 语音开始: {narration_start_time:.1f}秒)")
    
    async def generate_video(self):
        """生成视频主流程"""
        print("=" * 60)
        print("开始生成CloudLens Web使用指南视频 - 5分钟版")
        print("=" * 60)
        print()
        
        # 检查服务
        print("🔍 检查服务状态...")
        try:
            import requests
            requests.get(BACKEND_URL, timeout=5)
            print("   ✅ 后端服务正常")
            requests.get(BASE_URL, timeout=5)
            print("   ✅ 前端服务正常")
        except:
            print("   ⚠️  服务未启动，请先启动前端和后端")
            return
        
        print()
        
        # 预生成所有语音文件
        print("🎤 预生成中文语音...")
        print()
        narration_durations = {}
        
        for i, feature in enumerate(FEATURES):
            audio_file = OUTPUT_DIR / f"pre_narration_{i}.wav"
            success, duration = self.generate_narration_audio(feature["narration"], str(audio_file))
            if success:
                narration_durations[i] = duration
                print(f"   ✅ {feature['name']}: {duration:.1f}秒")
            else:
                print(f"   ⚠️  {feature['name']}: 语音生成失败")
        
        print()
        
        # 访问首页，等待完全加载避免黑屏
        print("📹 访问首页...")
        await self.page.goto(BASE_URL, wait_until="networkidle")
        await asyncio.sleep(5)  # 增加等待时间，确保页面完全渲染，避免黑屏
        print("   ✅ 页面已完全加载")
        
        # 开始录制
        print("📹 开始录制功能模块...")
        print()
        
        start_time = time.time()
        
        for i, feature in enumerate(FEATURES, 1):
            print(f"[{i}/{len(FEATURES)}] {feature['name']}")
            try:
                narration_duration = narration_durations.get(i-1, 0.0)
                await self.record_feature(feature, start_time, narration_duration)
            except Exception as e:
                print(f"   ❌ 录制失败: {e}")
                continue
            print()
        
        # 保存视频
        print("💾 保存视频...")
        await self.page.close()
        await self.browser.close()
        await asyncio.sleep(2)
        
        # 查找视频文件
        video_files = list(OUTPUT_DIR.glob("*.webm"))
        if not video_files:
            print("   ⚠️  未找到录制的视频文件")
            return
        
        video_file = max(video_files, key=lambda p: p.stat().st_mtime)
        print(f"   ✅ 找到视频文件: {video_file.name}")
        
        # 处理视频
        print()
        print("🎬 处理视频...")
        output_video = OUTPUT_DIR / f"cloudlens_web_guide_5min_{self.timestamp}.mp4"
        
        # 转换为MP4
        print("   1. 转换为MP4格式...")
        mp4_file = OUTPUT_DIR / f"temp_{self.timestamp}.mp4"
        
        cmd = [
            "ffmpeg",
            "-i", str(video_file),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-y",
            str(mp4_file)
        ]
        
        subprocess.run(cmd, capture_output=True, timeout=300)
        print("   ✅ MP4转换完成")
        
        # 合并音频
        print("   2. 合并音频...")
        audio_files = []
        for i in range(len(FEATURES)):
            audio_file = OUTPUT_DIR / f"pre_narration_{i}.wav"
            if audio_file.exists():
                audio_files.append(str(audio_file))
        
        if audio_files:
            # 构建ffmpeg命令（添加2秒额外延迟）
            EXTRA_DELAY = 2.0
            filter_parts = []
            input_parts = []
            
            for i, (audio_file, narration) in enumerate(zip(audio_files, self.narration_texts)):
                start_time = narration["start"] + EXTRA_DELAY
                delay_ms = int(start_time * 1000)
                
                input_parts.extend(["-i", audio_file])
                filter_parts.append(f"[{i+1}:a]aformat=channel_layouts=mono,adelay={delay_ms}|{delay_ms}[a{i}]")
            
            mix_inputs = "".join([f"[a{i}]" for i in range(len(audio_files))])
            filter_complex = ";".join(filter_parts) + f";{mix_inputs}amix=inputs={len(audio_files)}:duration=longest:dropout_transition=2[outa]"
            
            cmd = [
                "ffmpeg",
                "-i", str(mp4_file),
            ] + input_parts + [
                "-filter_complex", filter_complex,
                "-map", "0:v:0",
                "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                "-y",
                str(output_video)
            ]
            
            subprocess.run(cmd, capture_output=True, timeout=300)
            print("   ✅ 音频合并完成")
        else:
            output_video = mp4_file
        
        print()
        print("=" * 60)
        print("✅ 视频生成完成！")
        print("=" * 60)
        print()
        print(f"📁 视频文件: {output_video}")
        print(f"📊 视频大小: {output_video.stat().st_size / 1024 / 1024:.2f} MB")
        print(f"⏱️  总时长: 约5分钟")
        print()
        print(f"📊 API拦截统计: 总请求{self.api_intercept_stats['total']}次, 替换{self.api_intercept_stats['modified']}次")
    
    async def cleanup(self):
        """清理资源"""
        if self.page:
            try:
                await self.page.close()
            except:
                pass
        if self.browser:
            try:
                await self.browser.close()
            except:
                pass


async def main():
    """主函数"""
    generator = VideoGuideGenerator()
    
    try:
        await generator.setup()
        await generator.generate_video()
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await generator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
