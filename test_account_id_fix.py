#!/usr/bin/env python3
"""测试account_id修复"""

import requests
import json

# 测试后端健康检查
print("=== 测试后端健康 ===")
response = requests.get("http://localhost:8000/health")
print(f"健康检查: {response.json()}")
print()

# 验证account_id格式修复
print("=== 验证修复总结 ===")
import subprocess

# 检查是否还有错误格式
result = subprocess.run(
    ['grep', '-r', 'account_id = f"{account_config.access_key_id', 'web/backend/', '--include=*.py'],
    capture_output=True,
    text=True
)

if result.returncode == 0 and result.stdout:
    print(f"❌ 仍有{len(result.stdout.splitlines())}处使用错误格式")
    print(result.stdout)
else:
    print("✅ 所有account_id格式已修复")

# 检查已修复的数量
result2 = subprocess.run(
    ['grep', '-r', '# Use account name directly', 'web/backend/', '--include=*.py'],
    capture_output=True,
    text=True
)

if result2.stdout:
    count = len(result2.stdout.strip().splitlines())
    print(f"✅ 已修复{count}处account_id定义")

print("\n=== 修复说明 ===")
print("修复前: account_id = f\"{account_config.access_key_id[:10]}-{account_name}\"")
print("修复后: account_id = account_name  # Use account name directly")
print("\n这样account_id将直接使用账号名称（如'aliyun-prod'），")
print("而不是组合格式（如'LTAI******-aliyun-prod'），")
print("从而与数据库中的account_id列保持一致。")
