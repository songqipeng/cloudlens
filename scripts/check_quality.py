#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码质量检查脚本
运行 flake8, black, isort 检查
"""

import os
import subprocess
import sys


def run_command(command, description):
    print(f"🔍 正在运行 {description}...")
    try:
        subprocess.run(command, check=True, shell=True)
        print(f"✅ {description} 通过")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ {description} 失败")
        return False


def main():
    print("🚀 开始代码质量检查...")
    print("=" * 50)

    # 检查依赖
    dependencies = ["flake8", "black", "isort"]
    missing_deps = []
    for dep in dependencies:
        # 检查模块是否可导入
        try:
            __import__(dep)
        except ImportError:
            missing_deps.append(dep)

    if missing_deps:
        print(f"⚠️  缺少必要的工具: {', '.join(missing_deps)}")
        print(f"   请运行: pip install {' '.join(missing_deps)}")
        sys.exit(1)

    success = True

    # 1. isort (Import排序)
    if not run_command("python3 -m isort . --check-only --diff", "isort (Import排序检查)"):
        print("   💡 运行 'python3 -m isort .' 自动修复")
        success = False

    print("-" * 30)

    # 2. black (代码格式化)
    if not run_command("python3 -m black . --check --diff", "black (代码格式化检查)"):
        print("   💡 运行 'python3 -m black .' 自动修复")
        success = False

    print("-" * 30)

    # 3. flake8 (代码风格检查)
    if not run_command("python3 -m flake8 .", "flake8 (代码风格检查)"):
        success = False

    print("=" * 50)
    if success:
        print("🎉 所有检查通过！代码质量棒棒哒！")
        sys.exit(0)
    else:
        print("❌ 存在代码质量问题，请修复后重试。")
        sys.exit(1)


if __name__ == "__main__":
    main()
