#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖检查脚本
检查 CloudLens 所需的依赖是否已安装
"""

import sys
import importlib

# 必需的依赖列表
REQUIRED_DEPS = {
    "aliyunsdkcore": "aliyun-python-sdk-core>=2.16.0",
    "aliyunsdkecs": "aliyun-python-sdk-ecs>=4.24.0",
    "aliyunsdkrds": "aliyun-python-sdk-rds>=2.3.0",
    "aliyunsdkvpc": "aliyun-python-sdk-vpc>=3.0.0",
    "fastapi": "fastapi>=0.104.0",
    "uvicorn": "uvicorn[standard]>=0.24.0",
    "pandas": "pandas>=1.3.0",
    "keyring": "keyring>=23.0.0",
}

# 可选的依赖列表
OPTIONAL_DEPS = {
    "prophet": "prophet (用于AI成本预测)",
    "scikit-learn": "scikit-learn>=1.3.0 (用于机器学习)",
}

def check_dependency(module_name: str, package_name: str = None) -> tuple[bool, str]:
    """
    检查依赖是否已安装
    
    Returns:
        (is_installed, error_message)
    """
    try:
        importlib.import_module(module_name)
        return True, ""
    except ImportError as e:
        error_msg = f"未安装 {package_name or module_name}"
        return False, error_msg

def main():
    """主函数"""
    print("🔍 检查 CloudLens 依赖...")
    print("=" * 60)
    
    missing_required = []
    missing_optional = []
    
    # 检查必需依赖
    print("\n📦 必需依赖:")
    for module_name, package_name in REQUIRED_DEPS.items():
        is_installed, error_msg = check_dependency(module_name, package_name)
        if is_installed:
            print(f"  ✅ {module_name} ({package_name})")
        else:
            print(f"  ❌ {module_name} ({package_name}) - {error_msg}")
            missing_required.append(package_name)
    
    # 检查可选依赖
    print("\n📦 可选依赖:")
    for module_name, description in OPTIONAL_DEPS.items():
        is_installed, error_msg = check_dependency(module_name)
        if is_installed:
            print(f"  ✅ {module_name} - {description}")
        else:
            print(f"  ⚠️  {module_name} - {description} (未安装)")
            missing_optional.append(module_name)
    
    # 总结
    print("\n" + "=" * 60)
    if missing_required:
        print(f"\n❌ 缺少 {len(missing_required)} 个必需依赖:")
        for dep in missing_required:
            print(f"   - {dep}")
        print("\n💡 安装方法:")
        print("   pip install -r requirements.txt")
        print("\n   或者单独安装:")
        for dep in missing_required:
            print(f"   pip install {dep}")
        return 1
    else:
        print("\n✅ 所有必需依赖已安装！")
        if missing_optional:
            print(f"\n⚠️  可选依赖未安装 ({len(missing_optional)} 个):")
            for dep in missing_optional:
                print(f"   - {dep}")
            print("\n💡 这些依赖用于增强功能，但不影响基本使用。")
        return 0

if __name__ == "__main__":
    sys.exit(main())





