#!/bin/bash
# CloudLens 数据库初始化脚本
# 在容器启动后执行，创建所有必要的表结构

set -e

echo "=========================================="
echo "CloudLens 数据库初始化开始"
echo "=========================================="

# 等待MySQL完全启动
echo "等待MySQL服务启动..."
until mysql -h mysql -u cloudlens -pcloudlens123 -e "SELECT 1" > /dev/null 2>&1; do
  echo "MySQL未就绪，等待5秒..."
  sleep 5
done

echo "MySQL已就绪，开始初始化数据库..."

# 执行数据库迁移
MYSQL_CMD="mysql -h mysql -u cloudlens -pcloudlens123 cloudlens"

echo "1. 创建基础表结构..."
$MYSQL_CMD < /app/migrations/init_mysql_schema.sql

echo "2. 创建Chatbot表..."
$MYSQL_CMD < /app/migrations/add_chatbot_tables.sql

echo "3. 创建异常检测表..."
$MYSQL_CMD < /app/migrations/add_anomaly_table.sql

echo "=========================================="
echo "数据库初始化完成！"
echo "=========================================="
