#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量迁移剩余模块到MySQL的辅助脚本
用于检查和验证迁移状态
"""

import re
import os
from pathlib import Path

def check_sqlite_usage(file_path: str) -> dict:
    """检查文件中的SQLite使用情况"""
    if not os.path.exists(file_path):
        return {"exists": False}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    sqlite_imports = len(re.findall(r'import sqlite3|from sqlite3', content))
    sqlite_connects = len(re.findall(r'sqlite3\.connect', content))
    cursor_executes = len(re.findall(r'cursor\.execute', content))
    conn_closes = len(re.findall(r'conn\.close', content))
    
    return {
        "exists": True,
        "sqlite_imports": sqlite_imports,
        "sqlite_connects": sqlite_connects,
        "cursor_executes": cursor_executes,
        "conn_closes": conn_closes,
        "total": sqlite_imports + sqlite_connects + cursor_executes + conn_closes
    }

def main():
    """检查所有核心模块的SQLite使用情况"""
    modules = [
        "core/alert_manager.py",
        "core/budget_manager.py",
        "core/virtual_tags.py",
        "core/cost_allocation.py"
    ]
    
    print("=" * 60)
    print("剩余模块SQLite使用情况检查")
    print("=" * 60)
    
    for module in modules:
        result = check_sqlite_usage(module)
        if not result["exists"]:
            print(f"⚠️  {module}: 文件不存在")
            continue
        
        if result["total"] == 0:
            print(f"✅ {module}: 已完全迁移")
        else:
            print(f"⚠️  {module}:")
            print(f"   - sqlite3导入: {result['sqlite_imports']}")
            print(f"   - sqlite3.connect: {result['sqlite_connects']}")
            print(f"   - cursor.execute: {result['cursor_executes']}")
            print(f"   - conn.close: {result['conn_closes']}")
            print(f"   - 总计: {result['total']}处")
    
    print("=" * 60)

if __name__ == "__main__":
    main()


