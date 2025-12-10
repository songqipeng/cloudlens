#!/bin/bash
# CloudLens Daily Task Runner
# 每天运行一次，用于采集成本数据、检查闲置资源

# 获取当前脚本所在目录的上一级目录 (项目根目录)
PROJECT_ROOT=$(cd "$(dirname "$0")/.."; pwd)
LOG_FILE="$PROJECT_ROOT/logs/daily_tasks.log"

# 创建日志目录
mkdir -p "$PROJECT_ROOT/logs"

echo "========================================" >> "$LOG_FILE"
echo "Starting CloudLens Daily Tasks at $(date)" >> "$LOG_FILE"
echo "Project Root: $PROJECT_ROOT" >> "$LOG_FILE"

# 切换到项目目录
cd "$PROJECT_ROOT"

# 激活虚拟环境 (如果存在)
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 1. 采集成本数据 (用于AI预测积累数据)
echo "[1/2] Running analyze cost..." >> "$LOG_FILE"
./cl analyze cost >> "$LOG_FILE" 2>&1

# 2. 检查闲置资源
echo "[2/2] Running analyze idle..." >> "$LOG_FILE"
./cl analyze idle >> "$LOG_FILE" 2>&1

echo "Daily tasks completed at $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
