#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudLens CLI - 统一入口 (v2.1.0)
自动使用新的模块化架构
"""

import os
import sys
from pathlib import Path

# 添加当前目录到路径
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# 优先用项目 .venv，避免本机 python3 缺依赖
_venv_python = ROOT / ".venv" / "bin" / "python"
if _venv_python.exists():
    _current = Path(sys.executable).resolve()
    if _current != _venv_python.resolve():
        os.execv(str(_venv_python), [str(_venv_python), str(ROOT / "cl"), *sys.argv[1:]])


def _load_project_env() -> None:
    """加载项目根目录 .env，让本机 CLI 能连 Docker 映射出来的 MySQL。"""
    root = Path(__file__).resolve().parent
    for name in (".env.local", ".env"):
        path = root / name
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
        break


_load_project_env()

# 导入并运行新版CLI
from cloudlens.cli.main import cli

if __name__ == '__main__':
    cli()
