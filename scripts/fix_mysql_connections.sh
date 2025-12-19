#!/bin/bash
# 修复MySQL连接数过多问题
# 需要root权限

echo "修复MySQL连接配置..."

# 尝试使用root用户（需要密码）
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-}"

if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
    echo "请设置MYSQL_ROOT_PASSWORD环境变量，或手动执行以下SQL："
    echo ""
    echo "mysql -u root -p"
    echo "SET GLOBAL max_connections = 500;"
    echo "SET GLOBAL wait_timeout = 300;"
    echo "SET GLOBAL interactive_timeout = 300;"
    echo ""
    exit 1
fi

mysql -u root -p"$MYSQL_ROOT_PASSWORD" <<EOF
SET GLOBAL max_connections = 500;
SET GLOBAL wait_timeout = 300;
SET GLOBAL interactive_timeout = 300;
SHOW VARIABLES LIKE 'max_connections';
SHOW VARIABLES LIKE 'wait_timeout';
EOF

echo ""
echo "✅ MySQL配置已更新"
echo "最大连接数: 500"
echo "空闲连接超时: 300秒"

