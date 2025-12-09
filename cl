#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudLens CLI - 统一入口 (v2.1.0)
自动使用新的模块化架构
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入并运行新版CLI
from cl_new import cli

if __name__ == '__main__':
    cli()
