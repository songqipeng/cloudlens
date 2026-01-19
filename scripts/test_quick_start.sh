#!/bin/bash
# CloudLens 快速开始指南测试脚本
# 用于验证文档中的步骤是否可行

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     CloudLens 快速开始指南测试                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试结果统计
PASSED=0
FAILED=0
WARNINGS=0

# 测试函数
test_check() {
    local name="$1"
    local command="$2"
    
    echo -n "测试: $name ... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 通过${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ 失败${NC}"
        ((FAILED++))
        return 1
    fi
}

test_warn() {
    local name="$1"
    local command="$2"
    
    echo -n "检查: $name ... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 通过${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${YELLOW}⚠️  警告${NC}"
        ((WARNINGS++))
        return 1
    fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 测试1: 用户快速开始指南"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1.1 检查 Docker
test_check "Docker 已安装" "docker --version"
test_warn "Docker Compose 已安装" "docker compose version || docker-compose --version"

# 1.2 检查必需文件
test_check ".env.example 文件存在" "[ -f .env.example ]"
test_check "docker-compose.yml 文件存在" "[ -f docker-compose.yml ]"

# 1.3 检查 docker-compose 配置
test_check "docker-compose.yml 配置有效" "docker compose config > /dev/null 2>&1 || docker-compose config > /dev/null 2>&1"

# 1.4 检查镜像配置
test_check "后端镜像配置存在" "grep -q 'cloudlens-backend' docker-compose.yml"
test_check "前端镜像配置存在" "grep -q 'cloudlens-frontend' docker-compose.yml"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 测试2: 开发者快速开始指南"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 2.1 检查开发工具
test_warn "Python 3.11+ 已安装" "python3 --version | grep -E 'Python 3\.(1[1-9]|[2-9][0-9])'"
test_warn "Node.js 20+ 已安装" "node --version | grep -E 'v(2[0-9]|[3-9][0-9])'"
test_warn "npm 已安装" "npm --version"

# 2.2 检查必需文件
test_check "requirements.txt 文件存在" "[ -f requirements.txt ]"
test_check "web/frontend/package.json 文件存在" "[ -f web/frontend/package.json ]"

# 2.3 检查数据库迁移文件
test_check "init_mysql_schema.sql 存在" "[ -f migrations/init_mysql_schema.sql ]"
test_check "add_chatbot_tables.sql 存在" "[ -f migrations/add_chatbot_tables.sql ]"
test_check "add_anomaly_table.sql 存在" "[ -f migrations/add_anomaly_table.sql ]"

# 2.4 检查后端启动文件
test_check "后端 main.py 存在" "[ -f web/backend/main.py ]"

# 2.5 检查前端启动配置
test_check "前端 next.config.ts 存在" "[ -f web/frontend/next.config.ts ]"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 测试3: 文档完整性检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 3.1 检查文档文件
test_check "用户快速开始指南存在" "[ -f docs/QUICK_START_FOR_USERS.md ]"
test_check "开发者快速开始指南存在" "[ -f docs/QUICK_START_FOR_DEVELOPERS.md ]"

# 3.2 检查文档中的链接
test_warn "用户指南中的链接有效" "grep -q 'DOCKER_HUB_SETUP.md' docs/QUICK_START_FOR_USERS.md && [ -f docs/DOCKER_HUB_SETUP.md ]"
test_warn "开发者指南中的链接有效" "grep -q 'DEVELOPMENT_GUIDE.md' docs/QUICK_START_FOR_DEVELOPERS.md || true"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 测试结果汇总"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✅ 通过: $PASSED${NC}"
echo -e "${YELLOW}⚠️  警告: $WARNINGS${NC}"
echo -e "${RED}❌ 失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 所有必需测试通过！${NC}"
    echo ""
    echo "下一步："
    echo "  1. 按照文档步骤实际执行一次"
    echo "  2. 验证 docker-compose up -d 可以正常启动"
    echo "  3. 验证开发环境可以正常启动"
    exit 0
else
    echo -e "${RED}❌ 有测试失败，请检查上述问题${NC}"
    exit 1
fi
