#!/bin/bash
# 设置默认使用MySQL的脚本

echo "设置环境变量，使程序默认使用MySQL..."

# 创建.env文件（如果不存在）
ENV_FILE="$HOME/.cloudlens/.env"
mkdir -p "$HOME/.cloudlens"

# 检查是否已存在.env文件
if [ -f "$ENV_FILE" ]; then
    echo "⚠️  .env文件已存在，将更新DB_TYPE设置"
    # 更新或添加DB_TYPE
    if grep -q "DB_TYPE" "$ENV_FILE"; then
        sed -i '' 's/^DB_TYPE=.*/DB_TYPE=mysql/' "$ENV_FILE"
    else
        echo "DB_TYPE=mysql" >> "$ENV_FILE"
    fi
else
    echo "创建新的.env文件"
    cat > "$ENV_FILE" << EOF
# CloudLens 环境配置
# 数据库类型: mysql 或 sqlite
DB_TYPE=mysql

# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=cloudlens123
MYSQL_DATABASE=cloudlens
MYSQL_CHARSET=utf8mb4
EOF
fi

echo "✅ 环境变量已设置"
echo ""
echo "当前配置:"
cat "$ENV_FILE"
echo ""
echo "提示: 在shell中运行以下命令使环境变量生效:"
echo "  export \$(cat $ENV_FILE | xargs)"
echo ""
echo "或者添加到 ~/.bashrc 或 ~/.zshrc:"
echo "  source $ENV_FILE"


