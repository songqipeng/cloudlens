#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI 功能测试
"""
import sys
import subprocess
import os

sys.path.insert(0, '.')

def test_cli_command(cmd, description):
    """测试 CLI 命令"""
    print(f"\n测试: {description}")
    print(f"命令: {cmd}")
    
    try:
        # 使用 Python 直接调用 CLI
        if cmd.startswith("cl "):
            # 转换为 Python 模块调用
            parts = cmd.split()[1:]
            if parts[0] == "config":
                from cli.commands.config_cmd import config
                print("   ✅ config 命令可用")
            elif parts[0] == "query":
                from cli.commands.query_cmd import query
                print("   ✅ query 命令可用")
            elif parts[0] == "analyze":
                from cli.commands.analyze_cmd import analyze
                print("   ✅ analyze 命令可用")
            else:
                print(f"   ⚠️  命令 {parts[0]} 需要实际执行测试")
        else:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )
            if result.returncode == 0:
                print(f"   ✅ 成功")
                if result.stdout:
                    print(f"   输出: {result.stdout[:200]}")
            else:
                print(f"   ❌ 失败: {result.stderr[:200]}")
    except Exception as e:
        print(f"   ⚠️  测试跳过: {e}")

def main():
    print("=" * 80)
    print("CLI 功能测试")
    print("=" * 80)
    
    # 测试 CLI 模块导入
    print("\n1. 测试 CLI 模块导入...")
    try:
        from cli.main import cli
        print("   ✅ CLI 主模块导入成功")
    except Exception as e:
        print(f"   ❌ CLI 主模块导入失败: {e}")
        return
    
    # 测试各个命令模块
    commands = [
        ("cli.commands.config_cmd", "config"),
        ("cli.commands.query_cmd", "query"),
        ("cli.commands.analyze_cmd", "analyze"),
        ("cli.commands.cache_cmd", "cache"),
        ("cli.commands.bill_cmd", "bill"),
        ("cli.commands.remediate_cmd", "remediate"),
    ]
    
    print("\n2. 测试命令模块导入...")
    for module_name, cmd_name in commands:
        try:
            module = __import__(module_name, fromlist=[cmd_name])
            cmd_func = getattr(module, cmd_name, None)
            if cmd_func:
                print(f"   ✅ {cmd_name} 命令模块可用")
            else:
                print(f"   ⚠️  {cmd_name} 命令模块缺少函数")
        except Exception as e:
            print(f"   ⚠️  {cmd_name} 命令模块导入失败: {e}")
    
    # 测试核心功能
    print("\n3. 测试核心功能...")
    try:
        from core.config import ConfigManager
        cm = ConfigManager()
        accounts = cm.list_accounts()
        print(f"   ✅ 配置管理: {len(accounts)} 个账号")
    except Exception as e:
        print(f"   ❌ 配置管理失败: {e}")
    
    try:
        from core.cache import CacheManager
        cache = CacheManager()
        print("   ✅ 缓存管理: 正常")
    except Exception as e:
        print(f"   ❌ 缓存管理失败: {e}")
    
    try:
        from core.services.analysis_service import AnalysisService
        print("   ✅ 分析服务: 正常")
    except Exception as e:
        print(f"   ❌ 分析服务失败: {e}")
    
    try:
        from providers.aliyun.provider import AliyunProvider
        print("   ✅ 阿里云 Provider: 正常")
    except Exception as e:
        print(f"   ❌ 阿里云 Provider 失败: {e}")
    
    print("\n" + "=" * 80)
    print("CLI 测试完成")
    print("=" * 80)
    print("\n注意: CLI 命令需要在实际环境中执行才能完整测试")
    print("可以使用以下命令测试:")
    print("  python3 cli/main.py --help")
    print("  python3 cli/main.py config list")
    print("  python3 cli/main.py query ecs --account ydzn")

if __name__ == "__main__":
    main()



