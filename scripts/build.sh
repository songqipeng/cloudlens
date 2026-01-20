#!/bin/bash
#
# CloudLens 镜像构建脚本
# 支持多环境构建和版本管理
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

REGISTRY="songqipeng"
IMAGE_NAME="cloudlens-backend"

show_help() {
    cat << EOF
${BLUE}CloudLens 镜像构建工具${NC}

用法: $0 <environment> [version]

环境:
  dev         开发环境（无需构建，使用代码挂载）
  staging     Staging环境
  production  生产环境

参数:
  version     版本号（如 v1.1.0），生产环境必需

示例:
  $0 staging                  # 构建Staging镜像
  $0 production v1.1.0        # 构建生产镜像 v1.1.0

EOF
}

build_staging() {
    echo -e "${BLUE}🔨 构建Staging镜像...${NC}"

    local tag="$REGISTRY/$IMAGE_NAME:staging"

    echo "构建: $tag"
    docker build \
        --platform linux/amd64 \
        -t "$tag" \
        -f web/backend/Dockerfile \
        .

    echo ""
    echo -e "${YELLOW}是否推送到Docker Hub? (y/N)${NC}"
    read -p "Push? " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "推送镜像..."
        docker push "$tag"
        echo -e "${GREEN}✅ 镜像已推送${NC}"
    fi

    echo -e "${GREEN}✅ Staging镜像构建完成${NC}"
    echo "镜像: $tag"
}

build_production() {
    local version=$1

    if [ -z "$version" ]; then
        echo -e "${RED}❌ 生产环境必须指定版本号${NC}"
        echo "用法: $0 production v1.1.0"
        exit 1
    fi

    # 验证版本号格式
    if [[ ! $version =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo -e "${RED}❌ 版本号格式错误${NC}"
        echo "格式: v1.0.0"
        exit 1
    fi

    echo -e "${BLUE}🔨 构建生产镜像 $version...${NC}"

    local version_tag="$REGISTRY/$IMAGE_NAME:$version"
    local latest_tag="$REGISTRY/$IMAGE_NAME:latest"

    # 构建镜像
    echo "构建: $version_tag"
    docker build \
        --platform linux/amd64 \
        -t "$version_tag" \
        -t "$latest_tag" \
        -f web/backend/Dockerfile \
        .

    echo ""
    echo -e "${YELLOW}是否推送到Docker Hub? (Y/n)${NC}"
    read -p "Push? " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "推送镜像..."
        docker push "$version_tag"
        docker push "$latest_tag"
        echo -e "${GREEN}✅ 镜像已推送${NC}"
    fi

    echo -e "${GREEN}✅ 生产镜像构建完成${NC}"
    echo "版本镜像: $version_tag"
    echo "Latest镜像: $latest_tag"

    # 创建Git标签
    echo ""
    echo -e "${YELLOW}是否创建Git标签? (Y/n)${NC}"
    read -p "Create tag? " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        git tag -a "$version" -m "Release $version"
        git push origin "$version"
        echo -e "${GREEN}✅ Git标签已创建${NC}"
    fi
}

main() {
    local environment=${1:-help}
    local version=$2

    case "$environment" in
        dev)
            echo -e "${YELLOW}开发环境无需构建镜像（使用代码挂载）${NC}"
            echo "直接运行: ./scripts/dev.sh start"
            ;;
        staging)
            build_staging
            ;;
        production|prod)
            build_production "$version"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}❌ 未知环境: $environment${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
