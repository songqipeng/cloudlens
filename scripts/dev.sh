#!/bin/bash
#
# CloudLens 开发环境管理脚本
# 用于快速管理开发环境的启动、停止、测试等
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 显示帮助
show_help() {
    cat << EOF
${BLUE}CloudLens 开发环境管理工具${NC}

用法: $0 <command>

命令:
  start       启动开发环境
  stop        停止开发环境
  restart     重启开发环境
  logs        查看日志
  test        运行测试
  lint        代码检查
  format      代码格式化
  shell       进入容器shell
  db          数据库操作
  clean       清理环境
  status      查看状态
  help        显示帮助

示例:
  $0 start              # 启动开发环境
  $0 logs backend       # 查看后端日志
  $0 test               # 运行所有测试
  $0 db backup          # 备份数据库

EOF
}

# 启动开发环境
start_env() {
    echo -e "${BLUE}🚀 启动开发环境...${NC}"

    # 检查docker-compose.dev.yml
    if [ ! -f "docker-compose.dev.yml" ]; then
        echo -e "${RED}❌ 找不到 docker-compose.dev.yml${NC}"
        exit 1
    fi

    # 启动服务
    docker compose -f docker-compose.dev.yml up -d

    echo ""
    echo -e "${GREEN}✅ 开发环境已启动！${NC}"
    echo ""
    echo -e "访问地址:"
    echo -e "  前端: ${BLUE}http://localhost:3000${NC}"
    echo -e "  后端: ${BLUE}http://localhost:8000${NC}"
    echo -e "  API文档: ${BLUE}http://localhost:8000/docs${NC}"
    echo ""
    echo -e "查看日志:"
    echo -e "  ${YELLOW}$0 logs${NC}"
}

# 停止环境
stop_env() {
    echo -e "${BLUE}🛑 停止开发环境...${NC}"
    docker compose -f docker-compose.dev.yml down
    echo -e "${GREEN}✅ 开发环境已停止${NC}"
}

# 重启环境
restart_env() {
    echo -e "${BLUE}🔄 重启开发环境...${NC}"
    docker compose -f docker-compose.dev.yml restart
    echo -e "${GREEN}✅ 开发环境已重启${NC}"
}

# 查看日志
view_logs() {
    local service=$1
    if [ -z "$service" ]; then
        docker compose -f docker-compose.dev.yml logs -f
    else
        docker compose -f docker-compose.dev.yml logs -f "$service"
    fi
}

# 运行测试
run_tests() {
    echo -e "${BLUE}🧪 运行测试套件...${NC}"

    # 确保测试环境运行
    echo "启动测试环境..."
    docker compose -f docker-compose.dev.yml up -d

    # 等待服务就绪
    echo "等待服务就绪..."
    sleep 5

    # 运行测试
    echo ""
    echo -e "${YELLOW}▶️  运行单元测试...${NC}"
    docker compose -f docker-compose.dev.yml exec backend \
        pytest tests/unit/ -v || true

    echo ""
    echo -e "${YELLOW}▶️  运行集成测试...${NC}"
    docker compose -f docker-compose.dev.yml exec backend \
        pytest tests/integration/ -v || true

    echo ""
    echo -e "${GREEN}✅ 测试完成${NC}"
}

# 代码检查
lint_code() {
    echo -e "${BLUE}🔍 运行代码检查...${NC}"

    echo "检查Python代码..."
    docker run --rm -v "$(pwd)":/app \
        python:3.11-slim sh -c "
            pip install -q flake8 black
            echo '▶️  Flake8...'
            flake8 cloudlens/ web/backend/ --max-line-length=120 --statistics || true
            echo '▶️  Black...'
            black --check cloudlens/ web/backend/ || true
        "

    echo -e "${GREEN}✅ 代码检查完成${NC}"
}

# 代码格式化
format_code() {
    echo -e "${BLUE}✨ 格式化代码...${NC}"

    docker run --rm -v "$(pwd)":/app \
        python:3.11-slim sh -c "
            pip install -q black
            black cloudlens/ web/backend/
        "

    echo -e "${GREEN}✅ 代码已格式化${NC}"
}

# 进入shell
enter_shell() {
    local service=${1:-backend}
    echo -e "${BLUE}🐚 进入 $service 容器...${NC}"
    docker compose -f docker-compose.dev.yml exec "$service" /bin/bash
}

# 数据库操作
db_operation() {
    local operation=$1

    case "$operation" in
        backup)
            echo -e "${BLUE}💾 备份数据库...${NC}"
            timestamp=$(date +%Y%m%d_%H%M%S)
            backup_file="backups/cloudlens_dev_$timestamp.sql"
            mkdir -p backups

            docker compose -f docker-compose.dev.yml exec -T mysql \
                mysqldump -ucloudlens -pcloudlens123 cloudlens > "$backup_file"

            echo -e "${GREEN}✅ 备份完成: $backup_file${NC}"
            ;;

        restore)
            local backup_file=$2
            if [ -z "$backup_file" ]; then
                echo -e "${RED}❌ 请指定备份文件${NC}"
                echo "用法: $0 db restore <备份文件>"
                exit 1
            fi

            echo -e "${BLUE}📥 恢复数据库...${NC}"
            docker compose -f docker-compose.dev.yml exec -T mysql \
                mysql -ucloudlens -pcloudlens123 cloudlens < "$backup_file"

            echo -e "${GREEN}✅ 数据库已恢复${NC}"
            ;;

        connect)
            echo -e "${BLUE}🔗 连接数据库...${NC}"
            docker compose -f docker-compose.dev.yml exec mysql \
                mysql -ucloudlens -pcloudlens123 cloudlens
            ;;

        *)
            echo -e "${RED}❌ 未知操作: $operation${NC}"
            echo "可用操作: backup, restore, connect"
            exit 1
            ;;
    esac
}

# 清理环境
clean_env() {
    echo -e "${YELLOW}⚠️  清理开发环境（包括数据卷）${NC}"
    read -p "确认删除所有容器和数据卷？(y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🧹 清理中...${NC}"
        docker compose -f docker-compose.dev.yml down -v
        echo -e "${GREEN}✅ 清理完成${NC}"
    else
        echo -e "${YELLOW}❌ 已取消${NC}"
    fi
}

# 查看状态
show_status() {
    echo -e "${BLUE}📊 开发环境状态:${NC}"
    echo ""
    docker compose -f docker-compose.dev.yml ps
    echo ""

    echo -e "${BLUE}💾 数据卷:${NC}"
    docker volume ls | grep "$(basename $PROJECT_ROOT)" || echo "  无数据卷"
    echo ""

    echo -e "${BLUE}🌐 网络:${NC}"
    docker network ls | grep "$(basename $PROJECT_ROOT)" || echo "  无网络"
}

# 主程序
main() {
    local command=${1:-help}

    case "$command" in
        start)
            start_env
            ;;
        stop)
            stop_env
            ;;
        restart)
            restart_env
            ;;
        logs)
            view_logs "$2"
            ;;
        test)
            run_tests
            ;;
        lint)
            lint_code
            ;;
        format)
            format_code
            ;;
        shell)
            enter_shell "$2"
            ;;
        db)
            db_operation "$2" "$3"
            ;;
        clean)
            clean_env
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}❌ 未知命令: $command${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
