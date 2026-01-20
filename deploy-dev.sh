#!/bin/bash
#
# CloudLens 开发/测试环境一键部署脚本
# 包含源代码挂载，支持热重载
#
# 使用方法：
#   ./deploy-dev.sh
#

set -e

echo "========================================"
echo "CloudLens 开发/测试环境部署"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查Docker环境
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker 未安装${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker 环境检查通过${NC}"
}

# 创建开发环境配置
create_dev_config() {
    echo ""
    echo "创建开发环境配置..."

    # 创建 docker compose.dev.yml
    cat > docker compose.dev.yml << 'EOF'
version: '3.8'

services:
  # MySQL 数据库
  mysql:
    image: mysql:8.0
    container_name: cloudlens-mysql-dev
    environment:
      MYSQL_ROOT_PASSWORD: cloudlens_root_2024
      MYSQL_DATABASE: cloudlens
      MYSQL_USER: cloudlens
      MYSQL_PASSWORD: cloudlens123
    ports:
      - "3306:3306"
    volumes:
      - mysql_data_dev:/var/lib/mysql
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-pcloudlens_root_2024"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - cloudlens-dev

  # Redis 缓存
  redis:
    image: redis:7-alpine
    container_name: cloudlens-redis-dev
    ports:
      - "6379:6379"
    volumes:
      - redis_data_dev:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - cloudlens-dev

  # 后端 API 服务（开发模式，挂载源代码）
  backend:
    image: python:3.11-slim
    container_name: cloudlens-backend-dev
    working_dir: /app
    environment:
      # 数据库配置
      MYSQL_HOST: mysql
      MYSQL_PORT: 3306
      MYSQL_USER: cloudlens
      MYSQL_PASSWORD: cloudlens123
      MYSQL_DATABASE: cloudlens
      # Redis配置
      REDIS_HOST: redis
      REDIS_PORT: 6379
      # 开发模式
      CLOUDLENS_ENVIRONMENT: development
      CLOUDLENS_DEBUG: "true"
      PYTHONUNBUFFERED: 1
    ports:
      - "8000:8000"
    volumes:
      - ./cloudlens:/app/cloudlens
      - ./web/backend:/app/web/backend
      - ./config:/app/config
      - ./migrations:/app/migrations
      - ./logs:/app/logs
      - ~/.cloudlens:/root/.cloudlens
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: >
      bash -c "
      echo '安装依赖...' &&
      pip install -q fastapi uvicorn[standard] mysql-connector-python redis aliyun-python-sdk-core aliyun-python-sdk-bssopenapi pydantic python-multipart &&
      echo '初始化数据库...' &&
      mysql -h mysql -u cloudlens -pcloudlens123 cloudlens < /app/migrations/init_mysql_schema.sql 2>&1 || true &&
      mysql -h mysql -u cloudlens -pcloudlens123 cloudlens < /app/migrations/add_chatbot_tables.sql 2>&1 || true &&
      mysql -h mysql -u cloudlens -pcloudlens123 cloudlens < /app/migrations/add_anomaly_table.sql 2>&1 || true &&
      echo '启动开发服务器...' &&
      uvicorn web.backend.main:app --host 0.0.0.0 --port 8000 --reload
      "
    restart: unless-stopped
    networks:
      - cloudlens-dev

  # 前端 Web 服务（开发模式）
  frontend:
    image: node:18-alpine
    container_name: cloudlens-frontend-dev
    working_dir: /app
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NODE_ENV: development
    ports:
      - "3000:3000"
    volumes:
      - ./web/frontend:/app
      - /app/node_modules
      - /app/.next
    command: >
      sh -c "
      if [ ! -d node_modules ]; then
        echo '安装依赖...' &&
        npm install
      fi &&
      echo '启动开发服务器...' &&
      npm run dev
      "
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - cloudlens-dev

volumes:
  mysql_data_dev:
  redis_data_dev:

networks:
  cloudlens-dev:
    driver: bridge
EOF

    echo -e "${GREEN}✓ 开发环境配置已创建${NC}"
}

# 配置环境变量
setup_env() {
    echo ""
    echo "配置环境变量..."

    if [ ! -f "$HOME/.cloudlens/.env" ]; then
        mkdir -p "$HOME/.cloudlens"
        cat > "$HOME/.cloudlens/.env" << 'EOF'
CLOUDLENS_DATABASE__DB_TYPE=mysql
CLOUDLENS_DATABASE__MYSQL_HOST=mysql
CLOUDLENS_DATABASE__MYSQL_PORT=3306
CLOUDLENS_DATABASE__MYSQL_USER=cloudlens
CLOUDLENS_DATABASE__MYSQL_PASSWORD=cloudlens123
CLOUDLENS_DATABASE__MYSQL_DATABASE=cloudlens

# 简化的环境变量名
DB_TYPE=mysql
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=cloudlens123
MYSQL_DATABASE=cloudlens
EOF
        echo -e "${GREEN}✓ 默认配置已创建${NC}"
    else
        echo -e "${GREEN}✓ 配置文件已存在${NC}"
    fi
}

# 启动开发环境
start_dev() {
    echo ""
    echo "启动开发环境..."

    # 停止旧服务
    docker compose -f docker compose.dev.yml down 2>/dev/null || true

    # 启动新服务
    docker compose -f docker compose.dev.yml up -d

    echo ""
    echo "等待服务启动..."
    sleep 15

    # 显示服务状态
    docker compose -f docker compose.dev.yml ps
}

# 显示信息
show_dev_info() {
    echo ""
    echo "========================================"
    echo -e "${GREEN}✅ 开发环境部署完成！${NC}"
    echo "========================================"
    echo ""
    echo "访问地址："
    echo "  - 前端界面: http://localhost:3000  (热重载)"
    echo "  - 后端API:  http://localhost:8000  (热重载)"
    echo "  - API文档:  http://localhost:8000/docs"
    echo ""
    echo "开发特性："
    echo "  - ✓ 源代码已挂载，修改后自动重载"
    echo "  - ✓ 支持断点调试"
    echo "  - ✓ 详细日志输出"
    echo ""
    echo "常用命令："
    echo "  - 查看日志:   docker compose -f docker compose.dev.yml logs -f [service]"
    echo "  - 重启服务:   docker compose -f docker compose.dev.yml restart [service]"
    echo "  - 进入容器:   docker exec -it cloudlens-backend-dev bash"
    echo "  - 停止环境:   docker compose -f docker compose.dev.yml down"
    echo ""
}

# 主流程
main() {
    check_docker
    create_dev_config
    setup_env
    start_dev
    show_dev_info
}

main
