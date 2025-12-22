#!/usr/bin/env python3
"""
批量修复 discount_analyzer_advanced.py 中所有 sqlite3 使用
将 sqlite3.connect(self.db_path) 替换为使用数据库抽象层
"""

import re

file_path = "core/discount_analyzer_advanced.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 统计需要修复的方法数量
sqlite_conn_pattern = r'conn = sqlite3\.connect\(self\.db_path\)'
matches = re.findall(sqlite_conn_pattern, content)
print(f"找到 {len(matches)} 处需要修复的 sqlite3.connect 调用")

# 显示需要修复的行号
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if 'conn = sqlite3.connect(self.db_path)' in line:
        # 找到方法名（向上查找最近的 def）
        for j in range(i-1, max(0, i-20), -1):
            if lines[j].strip().startswith('def '):
                method_name = lines[j].strip().split('(')[0].replace('def ', '')
                print(f"  行 {i}: {method_name}()")
                break

print("\n提示：这些方法需要手动修复，使用 _query_db() 方法替换 sqlite3.connect()")


