#!/bin/bash
#
# CloudLens 一键部署脚本
# 支持：开发环境 / 生产环境
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logo
show_logo() {
    cat << "EOF"
    ______ __                 __ __
   / ____// /____   __  __ ____/ // /   ___   ____   _____
  / /    / // __ \ / / / // __  // /   / _ \ / __ \ / ___/
 / /___ / // /_/ // /_/ // /_/ // /__ /  __// / / /(__  )
 \____//_/ \____/ \__,_/ \__,_//_____/\___//_/ /_//____/

 Cloud Cost Management Platform - 云成本管理平台
EOF
}

# 检测环境类型
detect_mode() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}   CloudLens 一键部署向导${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "请选择部署模式:"
    echo ""
    echo "  ${GREEN}1)${NC} 开发环境 (Developer Mode)"
    echo "     - 代码热重载，快速迭代"
    echo "     - 适合：开发者日常开发"
    echo ""
    echo "  ${GREEN}2)${NC} 生产环境 (Production Mode)"
    echo "     - 稳定镜像，正式服务"
    echo "     - 适合：用户部署使用"
    echo ""
    echo "  ${GREEN}3)${NC} Staging环境 (测试环境)"
    echo "     - 发布前测试验证"
    echo "     - 适合：发布前验证"
    echo ""
    read -p "请选择 [1-3]: " mode_choice
    echo ""

    case "$mode_choice" in
        1)
            MODE="dev"
            MODE_NAME="开发环境"
            ;;
        2)
            MODE="production"
            MODE_NAME="生产环境"
            ;;
        3)
            MODE="staging"
            MODE_NAME="Staging环境"
            ;;
        *)
            echo -e "${RED}❌ 无效选择${NC}"
            exit 1
            ;;
    esac

    echo -e "${GREEN}✓${NC} 选择: ${YELLOW}$MODE_NAME${NC}"
    echo ""
}

# 系统环境检查
check_requirements() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}   系统环境检查${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker 未安装${NC}"
        echo ""
        echo "请先安装Docker:"
        echo "  macOS: https://docs.docker.com/desktop/install/mac-install/"
        echo "  Linux: https://docs.docker.com/engine/install/"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Docker: $(docker --version | awk '{print $3}')"

    # 检查Docker Compose
    if ! docker compose version &> /dev/null; then
        echo -e "${RED}❌ Docker Compose 未安装${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Docker Compose: $(docker compose version --short)"

    # 检查Docker是否运行
    if ! docker ps &> /dev/null; then
        echo -e "${RED}❌ Docker 服务未运行${NC}"
        echo "请启动Docker Desktop"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Docker 服务运行正常"

    # 检查端口占用
    check_port 3000 "前端"
    check_port 8000 "后端"
    check_port 3306 "MySQL"
    check_port 6379 "Redis"

    echo ""
    echo -e "${GREEN}✓${NC} 系统环境检查通过"
    echo ""
}

# 检查端口占用
check_port() {
    local port=$1
    local service=$2

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${YELLOW}⚠${NC}  端口 $port ($service) 已被占用"
        read -p "是否停止占用端口的服务？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            lsof -ti:$port | xargs kill -9 2>/dev/null || true
            echo -e "${GREEN}✓${NC} 端口 $port 已释放"
        fi
    else
        echo -e "${GREEN}✓${NC} 端口 $port ($service) 可用"
    fi
}

# 配置环境
setup_environment() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}   环境配置${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 创建配置目录
    mkdir -p ~/.cloudlens
    mkdir -p logs
    mkdir -p backups

    # 生产环境需要配置
    if [ "$MODE" = "production" ]; then
        if [ ! -f ~/.cloudlens/config.json ]; then
            echo -e "${YELLOW}⚠${NC}  首次运行需要配置账号信息"
            echo ""
            echo "配置文件位置: ~/.cloudlens/config.json"
            echo ""
            read -p "是否现在配置账号？(Y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                setup_account
            else
                echo -e "${YELLOW}⚠${NC}  请稍后手动配置 ~/.cloudlens/config.json"
            fi
        fi
    fi

    echo -e "${GREEN}✓${NC} 环境配置完成"
    echo ""
}

# 配置账号
setup_account() {
    echo ""
    read -p "账号名称 (如: aliyun-prod): " account_name
    read -p "AccessKey ID: " access_key_id
    read -sp "AccessKey Secret: " access_key_secret
    echo ""
    read -p "区域 (默认: cn-hangzhou): " region
    region=${region:-cn-hangzhou}

    cat > ~/.cloudlens/config.json << EOF
{
  "accounts": [
    {
      "name": "$account_name",
      "provider": "aliyun",
      "access_key_id": "$access_key_id",
      "access_key_secret": "$access_key_secret",
      "region": "$region"
    }
  ]
}
EOF

    echo -e "${GREEN}✓${NC} 账号配置已保存"
}

# 拉取镜像
pull_images() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}   拉取Docker镜像${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ "$MODE" = "dev" ]; then
        echo "开发环境使用基础镜像..."
        docker pull python:3.11-slim
        docker pull node:18-alpine
    else
        echo "拉取应用镜像..."
        local tag="latest"
        if [ "$MODE" = "staging" ]; then
            tag="staging"
        fi

        docker pull songqipeng/cloudlens-backend:$tag || {
            echo -e "${YELLOW}⚠${NC}  无法拉取镜像，将使用本地构建"
            return 1
        }
        docker pull songqipeng/cloudlens-frontend:$tag || true
    fi

    # 拉取基础服务镜像
    docker pull mysql:8.0
    docker pull redis:7-alpine
    docker pull nginx:alpine

    echo ""
    echo -e "${GREEN}✓${NC} 镜像拉取完成"
    echo ""
}

# 启动服务
start_services() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}   启动 $MODE_NAME${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 选择compose文件
    local compose_file="docker-compose.yml"
    case "$MODE" in
        dev)
            compose_file="docker-compose.dev.yml"
            ;;
        staging)
            compose_file="docker-compose.staging.yml"
            ;;
    esac

    echo "使用配置: $compose_file"
    echo ""

    # 启动服务
    docker compose -f "$compose_file" up -d

    echo ""
    echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
    sleep 10

    # 健康检查
    echo ""
    echo "检查服务健康状态..."
    local retry=0
    local max_retry=30

    while [ $retry -lt $max_retry ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} 后端服务已就绪"
            break
        fi
        echo -n "."
        sleep 2
        retry=$((retry+1))
    done

    if [ $retry -eq $max_retry ]; then
        echo -e "${YELLOW}⚠${NC}  后端服务启动可能需要更多时间"
    fi

    echo ""
}

# 显示访问信息
show_info() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}   🎉 部署完成！${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${GREEN}访问地址:${NC}"

    case "$MODE" in
        dev)
            echo -e "  ${CYAN}前端:${NC} http://localhost:3000"
            echo -e "  ${CYAN}后端:${NC} http://localhost:8000"
            echo -e "  ${CYAN}API文档:${NC} http://localhost:8000/docs"
            ;;
        production)
            echo -e "  ${CYAN}前端:${NC} http://localhost:3000"
            echo -e "  ${CYAN}后端:${NC} http://localhost:8000"
            echo -e "  ${CYAN}Nginx:${NC} http://localhost"
            ;;
        staging)
            echo -e "  ${CYAN}前端:${NC} http://localhost:3001"
            echo -e "  ${CYAN}后端:${NC} http://localhost:8001"
            ;;
    esac

    echo ""
    echo -e "${GREEN}常用命令:${NC}"
    echo -e "  ${YELLOW}查看日志:${NC}"
    case "$MODE" in
        dev)
            echo "    docker compose -f docker-compose.dev.yml logs -f"
            ;;
        production)
            echo "    docker compose logs -f"
            ;;
        staging)
            echo "    docker compose -f docker-compose.staging.yml logs -f"
            ;;
    esac

    echo ""
    echo -e "  ${YELLOW}查看状态:${NC}"
    case "$MODE" in
        dev)
            echo "    docker compose -f docker-compose.dev.yml ps"
            ;;
        production)
            echo "    docker compose ps"
            ;;
        staging)
            echo "    docker compose -f docker-compose.staging.yml ps"
            ;;
    esac

    echo ""
    echo -e "  ${YELLOW}停止服务:${NC}"
    case "$MODE" in
        dev)
            echo "    docker compose -f docker-compose.dev.yml down"
            ;;
        production)
            echo "    docker compose down"
            ;;
        staging)
            echo "    docker compose -f docker-compose.staging.yml down"
            ;;
    esac

    if [ "$MODE" = "dev" ]; then
        echo ""
        echo -e "${GREEN}开发工具:${NC}"
        echo -e "  ${YELLOW}快速命令:${NC}"
        echo "    ./scripts/dev.sh start    # 启动开发环境"
        echo "    ./scripts/dev.sh logs     # 查看日志"
        echo "    ./scripts/dev.sh test     # 运行测试"
        echo "    ./scripts/dev.sh help     # 查看更多命令"
    fi

    echo ""
    echo -e "${CYAN}配置文件位置:${NC}"
    echo "  ~/.cloudlens/config.json    # 账号配置"
    echo "  ./logs/                     # 日志目录"
    echo "  ./backups/                  # 备份目录"
    echo ""

    if [ "$MODE" = "production" ] && [ ! -f ~/.cloudlens/config.json ]; then
        echo -e "${YELLOW}⚠${NC}  ${RED}重要:${NC} 请配置账号信息后重启服务"
        echo "  编辑: ~/.cloudlens/config.json"
        echo ""
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# 主程序
main() {
    clear
    show_logo
    echo ""

    detect_mode
    check_requirements
    setup_environment
    pull_images || true
    start_services
    show_info

    echo -e "${GREEN}🚀 CloudLens 已成功启动！${NC}"
    echo ""
}

main "$@"
