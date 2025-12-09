#!/usr/bin/env python3
# -*- coding: #!/usr/bin/env bash
# CloudLens CLI - 统一入口
# 版本: v2.1.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 使用新的模块化架构
python3 "$SCRIPT_DIR/cl_new.py" "$@"
import cli

if __name__ == '__main__':
    cli()
