#!/bin/bash
export TERM=xterm-256color
clear
echo "=========================================="
echo "CloudLens CLI 完整功能测试"
echo "=========================================="
echo ""
python3 /Users/mac/cloudlens/tests/test_cli_full.py
echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
sleep 2
exit
