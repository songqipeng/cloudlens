#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudLens CLI 完整功能测试脚本
自动测试所有CLI命令并录制测试过程
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 配置
CLI_MODULE = "cli.main"
TEST_ACCOUNT = "ydzn"  # 测试账号
TEST_OUTPUT_DIR = Path("test-recordings/cli")
TEST_RESULTS_FILE = TEST_OUTPUT_DIR / f"cli_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# 确保输出目录存在
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 测试命令配置
CLI_TEST_COMMANDS = [
    {
        "name": "帮助信息",
        "command": ["--help"],
        "description": "显示CLI帮助信息",
        "expected_output": ["Usage:", "Commands:"],
    },
    {
        "name": "版本信息",
        "command": ["--version"],
        "description": "显示CLI版本信息",
        "expected_output": ["2.1.0"],
    },
    {
        "name": "配置列表",
        "command": ["config", "list"],
        "description": "列出所有配置的账号",
        "expected_output": ["账号", "account", "ydzn"],
    },
    {
        "name": "配置查看",
        "command": ["config", "show", TEST_ACCOUNT],
        "description": "查看指定账号的配置",
        "expected_output": ["ydzn", "access_key"],
    },
    {
        "name": "查询ECS资源",
        "command": ["query", "resources", TEST_ACCOUNT, "ecs", "--format", "table"],
        "description": "查询ECS资源（表格格式）",
        "expected_output": ["实例", "instance", "ID"],
        "timeout": 60,  # ECS查询可能需要较长时间
    },
    {
        "name": "查询RDS资源",
        "command": ["query", "resources", TEST_ACCOUNT, "rds", "--format", "table"],
        "description": "查询RDS资源（表格格式）",
        "expected_output": ["数据库", "RDS", "ID"],
        "timeout": 60,
    },
    {
        "name": "查询资源JSON格式",
        "command": ["query", "resources", TEST_ACCOUNT, "ecs", "--format", "json"],
        "description": "查询ECS资源（JSON格式）",
        "expected_output": ["[", "{", "InstanceId"],
        "timeout": 60,
    },
    {
        "name": "缓存状态",
        "command": ["cache", "status"],
        "description": "查看缓存状态",
        "expected_output": ["缓存", "cache", "状态"],
    },
    {
        "name": "成本分析",
        "command": ["analyze", "cost", "--account", TEST_ACCOUNT, "--days", "30"],
        "description": "分析最近30天的成本",
        "expected_output": ["成本", "cost", "总计"],
        "timeout": 120,  # 成本分析可能需要较长时间
    },
    {
        "name": "闲置资源分析",
        "command": ["analyze", "idle", "--account", TEST_ACCOUNT],
        "description": "分析闲置资源",
        "expected_output": ["闲置", "idle", "资源"],
        "timeout": 120,
    },
    {
        "name": "账单查询",
        "command": ["bill", "fetch", "--account", TEST_ACCOUNT, "--start", "2024-12", "--end", "2024-12"],
        "description": "查询账单信息",
        "expected_output": ["账单", "bill", "账期"],
        "timeout": 60,
    },
    {
        "name": "查询命令帮助",
        "command": ["query", "--help"],
        "description": "显示查询命令帮助",
        "expected_output": ["query", "资源查询"],
    },
    {
        "name": "分析命令帮助",
        "command": ["analyze", "--help"],
        "description": "显示分析命令帮助",
        "expected_output": ["analyze", "分析"],
    },
    {
        "name": "配置命令帮助",
        "command": ["config", "--help"],
        "description": "显示配置命令帮助",
        "expected_output": ["config", "配置"],
    },
]


class CLITester:
    """CLI测试器"""
    
    def __init__(self):
        self.results: List[Dict] = []
        self.start_time = datetime.now()
        
    def run_command(
        self,
        name: str,
        command: List[str],
        description: str,
        expected_output: List[str] = None,
        timeout: int = 30,
    ) -> Dict:
        """运行单个命令并记录结果"""
        print(f"\n{'='*60}")
        print(f"📋 测试: {name}")
        print(f"📝 描述: {description}")
        print(f"🔧 命令: python -m {CLI_MODULE} {' '.join(command)}")
        print(f"{'='*60}")
        
        result = {
            "name": name,
            "command": " ".join(command),
            "description": description,
            "status": "unknown",
            "duration": 0,
            "output": "",
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }
        
        start_time = time.time()
        
        try:
            # 构建完整命令
            full_command = [sys.executable, "-m", CLI_MODULE] + command
            
            # 运行命令
            process = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            
            result["duration"] = time.time() - start_time
            result["output"] = process.stdout + process.stderr
            result["return_code"] = process.returncode
            
            # 检查输出
            if expected_output:
                output_lower = result["output"].lower()
                found_keywords = [
                    keyword
                    for keyword in expected_output
                    if keyword.lower() in output_lower
                ]
                
                if found_keywords:
                    result["status"] = "success"
                    result["matched_keywords"] = found_keywords
                    print(f"✅ 测试成功 (耗时: {result['duration']:.2f}秒)")
                    print(f"   匹配关键词: {', '.join(found_keywords)}")
                else:
                    result["status"] = "warning"
                    result["error"] = f"未找到预期关键词: {expected_output}"
                    print(f"⚠️  测试警告: 未找到预期关键词")
                    print(f"   预期关键词: {', '.join(expected_output)}")
            else:
                # 如果没有预期输出，检查返回码
                if process.returncode == 0:
                    result["status"] = "success"
                    print(f"✅ 测试成功 (耗时: {result['duration']:.2f}秒)")
                else:
                    result["status"] = "failed"
                    result["error"] = f"命令返回非零退出码: {process.returncode}"
                    print(f"❌ 测试失败: 返回码 {process.returncode}")
            
            # 显示输出摘要（前500字符）
            output_preview = result["output"][:500].replace("\n", "\\n")
            if len(result["output"]) > 500:
                output_preview += "..."
            print(f"📄 输出摘要: {output_preview}")
            
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = f"命令执行超时（{timeout}秒）"
            result["duration"] = timeout
            print(f"⏰ 测试超时: {timeout}秒")
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            result["duration"] = time.time() - start_time
            print(f"❌ 测试错误: {e}")
        
        self.results.append(result)
        return result
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("🚀 开始CLI完整功能测试")
        print("="*60)
        print(f"📅 测试时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 结果文件: {TEST_RESULTS_FILE}")
        print("="*60)
        
        for test_case in CLI_TEST_COMMANDS:
            self.run_command(
                name=test_case["name"],
                command=test_case["command"],
                description=test_case["description"],
                expected_output=test_case.get("expected_output"),
                timeout=test_case.get("timeout", 30),
            )
            # 测试之间稍作延迟
            time.sleep(1)
        
        self.save_results()
        self.print_summary()
    
    def save_results(self):
        """保存测试结果"""
        summary = {
            "test_start_time": self.start_time.isoformat(),
            "test_end_time": datetime.now().isoformat(),
            "total_duration": (datetime.now() - self.start_time).total_seconds(),
            "total_tests": len(self.results),
            "results": self.results,
        }
        
        with open(TEST_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 测试结果已保存: {TEST_RESULTS_FILE}")
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("📊 测试结果摘要")
        print("="*60)
        
        success_count = sum(1 for r in self.results if r["status"] == "success")
        warning_count = sum(1 for r in self.results if r["status"] == "warning")
        failed_count = sum(1 for r in self.results if r["status"] in ["failed", "error", "timeout"])
        
        print(f"✅ 成功: {success_count}")
        print(f"⚠️  警告: {warning_count}")
        print(f"❌ 失败: {failed_count}")
        print(f"📈 总计: {len(self.results)}")
        print(f"⏱️  总耗时: {(datetime.now() - self.start_time).total_seconds():.2f}秒")
        print("="*60)
        
        # 显示失败的测试
        if failed_count > 0:
            print("\n❌ 失败的测试:")
            for result in self.results:
                if result["status"] in ["failed", "error", "timeout"]:
                    print(f"   - {result['name']}: {result.get('error', '未知错误')}")
        
        # 显示警告的测试
        if warning_count > 0:
            print("\n⚠️  警告的测试:")
            for result in self.results:
                if result["status"] == "warning":
                    print(f"   - {result['name']}: {result.get('error', '未找到预期输出')}")


def main():
    """主函数"""
    tester = CLITester()
    tester.run_all_tests()
    
    # 返回退出码
    failed_count = sum(
        1 for r in tester.results
        if r["status"] in ["failed", "error", "timeout"]
    )
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

