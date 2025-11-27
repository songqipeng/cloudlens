#!/bin/bash
# 自动同步到GitHub（每5分钟）

cd /Users/mac/aliyunidle
git add -A
if [ -n "$(git status --porcelain)" ]; then
    git commit -m "自动同步: $(date '+%Y-%m-%d %H:%M:%S')"
    git push origin main
fi
