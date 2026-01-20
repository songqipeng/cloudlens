#!/bin/bash
#
# CloudLens 一键安装脚本
# 适用于全新的 Linux/macOS 系统
#
# 使用方法（用户模式 - 只安装运行环境）:
#   curl -fsSL https://raw.githubusercontent.com/songqipeng/cloudlens/main/install.sh | bash
#
# 使用方法（开发者模式 - 包含源代码）:
#   curl -fsSL https://raw.githubusercontent.com/songqipeng/cloudlens/main/install.sh | bash -s -- --dev
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
REPO_URL="${CLOUDLENS_REPO_URL:-https://github.com/songqipeng/cloudlens.git}"
BRANCH="${CLOUDLENS_BRANCH:-main}"
INSTALL_DIR="${CLOUDLENS_INSTALL_DIR:-$HOME/cloudlens}"
DOCKER_HUB_USERNAME="${DOCKER_HUB_USERNAME:-your-dockerhub-username}"

# 默认用户模式
DEV_MODE=false

# 解析参数
for arg in "$@"; do
    case $arg in
        --dev)
            DEV_MODE=true
            shift
            ;;
    esac
done

echo ""
echo "========================================"
if [ "$DEV_MODE" = true ]; then
    echo "  CloudLens 开发者模式安装"
else
    echo "  CloudLens 用户模式安装"
fi
echo "========================================"
echo ""

# 检测操作系统
detect_os() {
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)

    case "$ARCH" in
        x86_64)
            ARCH="amd64"
            ;;
        aarch64|arm64)
            ARCH="arm64"
            ;;
        *)
            echo -e "${RED}❌ 不支持的架构: $ARCH${NC}"
            exit 1
            ;;
    esac

    echo -e "${GREEN}✓ 检测到系统: $OS/$ARCH${NC}"
}

# 检查并安装 Docker
install_docker() {
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓ Docker 已安装${NC}"
        return
    fi

    echo -e "${YELLOW}⚠️  Docker 未安装，开始安装...${NC}"

    case "$OS" in
        darwin)
            echo -e "${YELLOW}请手动安装 Docker Desktop for Mac:${NC}"
            echo "  https://docs.docker.com/desktop/install/mac-install/"
            exit 1
            ;;
        linux)
            # 使用 Docker 官方安装脚本
            curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
            sudo sh /tmp/get-docker.sh

            # 将当前用户添加到 docker 组
            sudo usermod -aG docker $USER

            echo -e "${GREEN}✓ Docker 安装完成${NC}"
            echo -e "${YELLOW}⚠️  请注销并重新登录以使 Docker 权限生效，然后重新运行此脚本${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ 不支持的操作系统: $OS${NC}"
            exit 1
            ;;
    esac
}

# 检查 Docker Compose
check_docker_compose() {
    if docker compose version &> /dev/null; then
        echo -e "${GREEN}✓ Docker Compose 已安装${NC}"
        return
    fi

    if command -v docker-compose &> /dev/null; then
        echo -e "${GREEN}✓ Docker Compose 已安装 (standalone)${NC}"
        return
    fi

    echo -e "${RED}❌ Docker Compose 未安装${NC}"
    echo "请安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
}

# 创建配置文件
create_config() {
    echo ""
    echo "创建配置文件..."

    # 创建配置目录
    mkdir -p "$HOME/.cloudlens"

    # 创建 .env 文件
    if [ ! -f "$HOME/.cloudlens/.env" ]; then
        cat > "$HOME/.cloudlens/.env" << 'EOF'
# CloudLens 配置文件

# 数据库配置 (Docker 环境使用容器名)
CLOUDLENS_DATABASE__DB_TYPE=mysql
CLOUDLENS_DATABASE__MYSQL_HOST=mysql
CLOUDLENS_DATABASE__MYSQL_PORT=3306
CLOUDLENS_DATABASE__MYSQL_USER=cloudlens
CLOUDLENS_DATABASE__MYSQL_PASSWORD=cloudlens123
CLOUDLENS_DATABASE__MYSQL_DATABASE=cloudlens
CLOUDLENS_DATABASE__POOL_SIZE=20

# 简化变量名
DB_TYPE=mysql
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=cloudlens
MYSQL_PASSWORD=cloudlens123
MYSQL_DATABASE=cloudlens

# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379

# 应用配置
CLOUDLENS_ENVIRONMENT=production
CLOUDLENS_DEBUG=false

# 日志配置
CLOUDLENS_LOGGING__LOG_LEVEL=INFO
EOF
        echo -e "${GREEN}✓ 配置文件已创建: $HOME/.cloudlens/.env${NC}"
    else
        echo -e "${GREEN}✓ 配置文件已存在${NC}"
    fi

    # 创建 config.json（阿里云账号配置）
    if [ ! -f "$HOME/.cloudlens/config.json" ]; then
        cat > "$HOME/.cloudlens/config.json" << 'EOF'
{
  "accounts": [
    {
      "name": "default",
      "provider": "aliyun",
      "access_key_id": "",
      "access_key_secret": "",
      "region": "cn-hangzhou",
      "alias": "默认账号"
    }
  ]
}
EOF
        echo -e "${YELLOW}⚠️  请编辑 $HOME/.cloudlens/config.json 配置阿里云账号${NC}"
    fi
}

# 用户模式：使用 Docker 镜像
install_user_mode() {
    echo ""
    echo "用户模式：使用预构建镜像部署..."

    # 创建临时目录
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"

    # 下载 docker-compose.yml
    echo "下载配置文件..."
    curl -fsSL "https://raw.githubusercontent.com/songqipeng/cloudlens/$BRANCH/docker-compose.yml" -o docker-compose.yml

    # 拉取镜像
    echo "拉取 Docker 镜像..."
    docker-compose pull

    # 启动服务
    echo "启动所有服务..."
    docker-compose up -d

    # 保存 docker-compose 路径
    echo "$TEMP_DIR" > "$HOME/.cloudlens/install_dir"

    echo -e "${GREEN}✓ 服务启动完成${NC}"
}

# 开发者模式：克隆代码
install_dev_mode() {
    echo ""
    echo "开发者模式：克隆代码仓库..."

    # 检查 Git
    if ! command -v git &> /dev/null; then
        echo -e "${RED}❌ Git 未安装${NC}"
        echo "请先安装 Git"
        exit 1
    fi

    # 克隆代码
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}⚠️  目录已存在: $INSTALL_DIR${NC}"
        read -p "是否删除并重新克隆? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            echo "使用现有目录"
            cd "$INSTALL_DIR"
            git pull origin $BRANCH || true
            return
        fi
    fi

    git clone -b $BRANCH $REPO_URL "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    echo -e "${GREEN}✓ 代码克隆完成${NC}"

    # 启动开发环境
    echo ""
    echo "启动开发环境..."
    ./deploy-dev.sh

    echo -e "${GREEN}✓ 开发环境启动完成${NC}"
}

# 健康检查
health_check() {
    echo ""
    echo "执行健康检查..."

    max_retries=30
    retry=0

    while [ $retry -lt $max_retries ]; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ 后端服务健康${NC}"
            break
        fi

        retry=$((retry + 1))
        echo "等待后端服务就绪... ($retry/$max_retries)"
        sleep 2
    done

    if [ $retry -eq $max_retries ]; then
        echo -e "${RED}❌ 后端服务未就绪${NC}"
        echo "请检查日志"
        exit 1
    fi

    # 检查前端
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 前端服务健康${NC}"
    else
        echo -e "${YELLOW}⚠️  前端服务可能需要更多时间启动${NC}"
    fi
}

# 显示完成信息
show_completion() {
    echo ""
    echo "========================================"
    echo -e "${GREEN}✅ CloudLens 安装完成！${NC}"
    echo "========================================"
    echo ""
    echo "访问地址："
    echo -e "  ${BLUE}前端界面:${NC} http://localhost:3000"
    echo -e "  ${BLUE}后端API:${NC}  http://localhost:8000"
    echo -e "  ${BLUE}API文档:${NC}  http://localhost:8000/docs"
    echo ""
    echo "配置文件："
    echo -e "  ${BLUE}环境配置:${NC}   $HOME/.cloudlens/.env"
    echo -e "  ${BLUE}账号配置:${NC}   $HOME/.cloudlens/config.json"
    echo ""

    if [ "$DEV_MODE" = true ]; then
        echo "开发者命令："
        echo -e "  ${BLUE}查看日志:${NC}   cd $INSTALL_DIR && docker-compose -f docker-compose.dev.yml logs -f"
        echo -e "  ${BLUE}重启服务:${NC}   cd $INSTALL_DIR && docker-compose -f docker-compose.dev.yml restart"
        echo -e "  ${BLUE}停止服务:${NC}   cd $INSTALL_DIR && docker-compose -f docker-compose.dev.yml stop"
        echo ""
        echo "代码位置："
        echo -e "  ${BLUE}源代码:${NC}     $INSTALL_DIR"
    else
        INSTALL_PATH=$(cat "$HOME/.cloudlens/install_dir" 2>/dev/null || echo "~/.cloudlens")
        echo "常用命令："
        echo -e "  ${BLUE}查看日志:${NC}   cd $INSTALL_PATH && docker-compose logs -f"
        echo -e "  ${BLUE}停止服务:${NC}   cd $INSTALL_PATH && docker-compose stop"
        echo -e "  ${BLUE}重启服务:${NC}   cd $INSTALL_PATH && docker-compose restart"
    fi

    echo ""
    echo "下一步："
    echo "  1. 编辑 $HOME/.cloudlens/config.json 配置阿里云账号"
    echo "  2. 访问 http://localhost:3000 开始使用"
    echo ""
}

# 主流程
main() {
    detect_os
    install_docker
    check_docker_compose
    create_config

    if [ "$DEV_MODE" = true ]; then
        install_dev_mode
    else
        install_user_mode
    fi

    health_check
    show_completion
}

# 执行主流程
main
