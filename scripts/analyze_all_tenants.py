#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析所有租户的闲置资源
"""

import json
import subprocess
import sys
from datetime import datetime


def load_config():
    """加载配置文件"""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print("❌ 配置文件 config.json 不存在")
        sys.exit(1)
    except json.JSONDecodeError:
        print("❌ 配置文件格式错误")
        sys.exit(1)


def analyze_tenant(tenant_name):
    """分析单个租户的所有资源"""
    print(f"\n{'='*80}")
    print(f"🏢 正在分析租户: {tenant_name}")
    print(f"{'='*80}\n")
    
    cmd = ["python3", "main.py", tenant_name, "cru", "all"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 分析租户 {tenant_name} 时出错: {e}")
        return False


def main():
    """主函数"""
    print("🚀 开始分析所有租户的闲置资源")
    print(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 加载配置
    config = load_config()
    tenants = config.get("tenants", {})
    
    if not tenants:
        print("❌ 未找到任何租户配置")
        return
    
    print(f"📋 发现 {len(tenants)} 个租户: {', '.join(tenants.keys())}\n")
    
    # 分析每个租户
    results = {}
    for tenant_name in tenants.keys():
        success = analyze_tenant(tenant_name)
        results[tenant_name] = "✅ 成功" if success else "❌ 失败"
    
    # 显示汇总
    print("\n" + "="*80)
    print("📊 所有租户分析结果汇总:")
    print("="*80)
    for tenant_name, result in results.items():
        print(f"  {tenant_name}: {result}")
    print("="*80)
    print(f"📅 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)


if __name__ == "__main__":
    main()
