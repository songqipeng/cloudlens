#!/bin/bash
#
# CloudLens 生产环境一键部署脚本
# 支持 Linux (amd64/arm64) 和 macOS (amd64/arm64)
#
# 使用方法：
#   ./deploy-production.sh
#

set -e  # 遇到错误立即退出

echo "========================================"
echo "CloudLens 生产环境部署"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检测操作系统和架构
detect_platform() {
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

    echo -e "${GREEN}✓ 检测到平台: $OS/$ARCH${NC}"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker 未安装${NC}"
        echo "请先安装 Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}❌ Docker Compose 未安装${NC}"
        echo "请先安装 Docker Compose"
        exit 1
    fi

    echo -e "${GREEN}✓ Docker 环境检查通过${NC}"
}

# 检查配置文件
check_config() {
    echo ""
    echo "检查配置文件..."

    # 检查 ~/.cloudlens/.env
    if [ ! -f "$HOME/.cloudlens/.env" ]; then
        echo -e "${YELLOW}⚠️  配置文件不存在，创建默认配置...${NC}"
        mkdir -p "$HOME/.cloudlens"
        cp .env.example "$HOME/.cloudlens/.env"

        # 设置Docker环境的默认值
        sed -i.bak 's/MYSQL_HOST=.*/MYSQL_HOST=mysql/' "$HOME/.cloudlens/.env"
        sed -i.bak 's/REDIS_HOST=.*/REDIS_HOST=redis/' "$HOME/.cloudlens/.env"

        echo -e "${YELLOW}⚠️  请编辑 ~/.cloudlens/.env 配置文件，设置：${NC}"
        echo "  - 数据库密码"
        echo "  - 阿里云 AccessKey"
        echo "  - 其他自定义配置"
        echo ""
        read -p "配置完成后按回车继续..."
    else
        echo -e "${GREEN}✓ 配置文件已存在${NC}"
    fi
}

# 拉取最新镜像
pull_images() {
    echo ""
    echo "拉取 Docker 镜像..."

    # 检查是否使用自定义镜像
    if [ ! -z "$DOCKER_HUB_USERNAME" ]; then
        docker-compose pull
    else
        echo -e "${YELLOW}ℹ️  使用默认镜像配置${NC}"
        docker-compose pull
    fi

    echo -e "${GREEN}✓ 镜像拉取完成${NC}"
}

# 启动服务
start_services() {
    echo ""
    echo "启动服务..."

    # 停止并删除旧容器
    docker-compose down 2>/dev/null || true

    # 启动所有服务
    docker-compose up -d

    echo ""
    echo "等待服务启动..."
    sleep 10

    # 检查服务状态
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✓ 服务启动成功${NC}"
    else
        echo -e "${RED}❌ 服务启动失败${NC}"
        echo "请查看日志: docker-compose logs"
        exit 1
    fi
}

# 健康检查
health_check() {
    echo ""
    echo "执行健康检查..."

    # 检查后端健康状态
    max_retries=30
    retry=0

    while [ $retry -lt $max_retries ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ 后端服务健康${NC}"
            break
        fi

        retry=$((retry + 1))
        echo "等待后端服务就绪... ($retry/$max_retries)"
        sleep 2
    done

    if [ $retry -eq $max_retries ]; then
        echo -e "${RED}❌ 后端服务未就绪${NC}"
        exit 1
    fi

    # 检查前端
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 前端服务健康${NC}"
    else
        echo -e "${YELLOW}⚠️  前端服务可能需要更多时间启动${NC}"
    fi

    # 检查数据库连接
    if docker exec cloudlens-mysql mysql -u cloudlens -pcloudlens123 -e "SELECT 1" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 数据库连接正常${NC}"
    else
        echo -e "${RED}❌ 数据库连接失败${NC}"
        exit 1
    fi
}

# 显示访问信息
show_info() {
    echo ""
    echo "========================================"
    echo -e "${GREEN}✅ CloudLens 部署完成！${NC}"
    echo "========================================"
    echo ""
    echo "访问地址："
    echo "  - 前端界面: http://localhost:3000"
    echo "  - 后端API:  http://localhost:8000"
    echo "  - API文档:  http://localhost:8000/docs"
    echo ""
    echo "常用命令："
    echo "  - 查看日志:   docker-compose logs -f"
    echo "  - 停止服务:   docker-compose stop"
    echo "  - 重启服务:   docker-compose restart"
    echo "  - 删除服务:   docker-compose down"
    echo ""
    echo "数据目录："
    echo "  - 配置文件:   ~/.cloudlens/.env"
    echo "  - 数据库:     Docker volume (mysql_data)"
    echo "  - 日志:       ./logs/"
    echo ""
}

# 主流程
main() {
    detect_platform
    check_docker
    check_config
    pull_images
    start_services
    health_check
    show_info
}

# 执行主流程
main
