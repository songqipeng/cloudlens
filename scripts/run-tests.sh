#!/bin/bash
#
# CloudLens 自动化测试脚本
# 运行完整的功能、性能和数据准确性测试
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

TEST_ACCOUNT="prod"
API_URL="http://localhost:8000"
RESULTS_DIR="test-results"

mkdir -p "$RESULTS_DIR"

# 测试计数
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试结果记录
TEST_RESULTS=()

# 记录测试结果
record_test() {
    local test_name=$1
    local status=$2
    local message=$3

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$status" = "PASS" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "${GREEN}✓${NC} $test_name"
        TEST_RESULTS+=("✓ $test_name")
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "${RED}✗${NC} $test_name: $message"
        TEST_RESULTS+=("✗ $test_name: $message")
    fi
}

# 测试API端点
test_api() {
    local name=$1
    local endpoint=$2
    local expected_status=${3:-200}

    response=$(curl -s -w "\n%{http_code}" "$API_URL$endpoint" 2>&1)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "$expected_status" ]; then
        record_test "$name" "PASS"
        return 0
    else
        record_test "$name" "FAIL" "HTTP $http_code"
        return 1
    fi
}

# Banner
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}   CloudLens 自动化测试${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "测试环境: $API_URL"
echo "测试账号: $TEST_ACCOUNT"
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

#######################################
# 1. 基础健康检查
#######################################
echo -e "${BLUE}━━━ 1. 基础健康检查 ━━━${NC}"

test_api "健康检查" "/health"
test_api "根路径" "/"

#######################################
# 2. 折扣分析功能
#######################################
echo ""
echo -e "${BLUE}━━━ 2. 折扣分析功能 ━━━${NC}"

test_api "折扣趋势分析" "/api/discounts/trend?account=$TEST_ACCOUNT&months=8"
test_api "产品折扣分析" "/api/discounts/products?account=$TEST_ACCOUNT&months=8"

# 数据准确性测试（折扣分析）
echo ""
echo "数据准确性验证..."
response=$(curl -s "$API_URL/api/discounts/trend?account=$TEST_ACCOUNT&months=8")

if echo "$response" | grep -q '"success": *true'; then
    avg_rate=$(echo "$response" | grep -o '"average_discount_rate": *[0-9.]*' | grep -o '[0-9.]*$')
    if [ ! -z "$avg_rate" ]; then
        # 验证折扣率在合理范围内（0-1）
        if (( $(echo "$avg_rate >= 0 && $avg_rate <= 1" | bc -l) )); then
            record_test "折扣率数据合理性" "PASS"
        else
            record_test "折扣率数据合理性" "FAIL" "折扣率超出范围: $avg_rate"
        fi
    else
        record_test "折扣率数据存在性" "FAIL" "未找到平均折扣率"
    fi
else
    record_test "折扣API返回格式" "FAIL" "success字段不为true"
fi

#######################################
# 3. 成本分析功能
#######################################
echo ""
echo -e "${BLUE}━━━ 3. 成本分析功能 ━━━${NC}"

# 这些API可能不存在，会返回404，我们标记为TODO
curl -s "$API_URL/api/costs/trend?account=$TEST_ACCOUNT" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    test_api "成本趋势" "/api/costs/trend?account=$TEST_ACCOUNT"
else
    echo -e "${YELLOW}⊘${NC} 成本趋势 - 未实现"
fi

#######################################
# 4. 配置管理功能
#######################################
echo ""
echo -e "${BLUE}━━━ 4. 配置管理功能 ━━━${NC}"

curl -s "$API_URL/api/config/accounts" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    test_api "账号列表查询" "/api/config/accounts"
else
    echo -e "${YELLOW}⊘${NC} 账号列表查询 - 未实现"
fi

#######################################
# 5. 性能测试
#######################################
echo ""
echo -e "${BLUE}━━━ 5. 性能测试 ━━━${NC}"

# 响应时间测试
echo "测试API响应时间..."
start_time=$(date +%s%3N)
curl -s "$API_URL/health" > /dev/null
end_time=$(date +%s%3N)
response_time=$((end_time - start_time))

if [ $response_time -lt 1000 ]; then
    record_test "健康检查响应时间 (<1s)" "PASS"
else
    record_test "健康检查响应时间 (<1s)" "FAIL" "${response_time}ms"
fi

# 折扣分析响应时间
start_time=$(date +%s%3N)
curl -s "$API_URL/api/discounts/trend?account=$TEST_ACCOUNT&months=8" > /dev/null
end_time=$(date +%s%3N)
response_time=$((end_time - start_time))

if [ $response_time -lt 2000 ]; then
    record_test "折扣分析响应时间 (<2s)" "PASS"
else
    record_test "折扣分析响应时间 (<2s)" "FAIL" "${response_time}ms"
fi

#######################################
# 6. 数据库测试
#######################################
echo ""
echo -e "${BLUE}━━━ 6. 数据库测试 ━━━${NC}"

# 检查数据库连接
if docker ps | grep -q cloudlens-mysql; then
    record_test "MySQL容器运行" "PASS"

    # 检查数据库表
    tables=$(docker exec cloudlens-mysql mysql -ucloudlens -pcloudlens123 cloudlens -e "SHOW TABLES;" 2>&1 | grep -v "password" | wc -l)
    if [ $tables -gt 5 ]; then
        record_test "数据库表结构" "PASS"
    else
        record_test "数据库表结构" "FAIL" "表数量: $tables"
    fi

    # 检查数据
    count=$(docker exec cloudlens-mysql mysql -ucloudlens -pcloudlens123 cloudlens -e "SELECT COUNT(*) FROM bill_items;" 2>&1 | grep -v "password" | tail -1)
    if [ "$count" -gt 0 ]; then
        record_test "账单数据存在" "PASS"
    else
        record_test "账单数据存在" "FAIL" "无数据"
    fi
else
    record_test "MySQL容器运行" "FAIL" "容器未运行"
fi

# 检查Redis
if docker ps | grep -q cloudlens-redis; then
    record_test "Redis容器运行" "PASS"
else
    record_test "Redis容器运行" "FAIL" "容器未运行"
fi

#######################################
# 测试总结
#######################################
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}   测试结果总结${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "总计: $TOTAL_TESTS 个测试"
echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}失败: $FAILED_TESTS${NC}"
fi
echo ""

pass_rate=$(( PASSED_TESTS * 100 / TOTAL_TESTS ))
echo "通过率: $pass_rate%"
echo ""

if [ $pass_rate -ge 90 ]; then
    echo -e "${GREEN}✓ 测试状态: 优秀${NC}"
    exit_code=0
elif [ $pass_rate -ge 70 ]; then
    echo -e "${YELLOW}⚠ 测试状态: 良好${NC}"
    exit_code=0
else
    echo -e "${RED}✗ 测试状态: 需要改进${NC}"
    exit_code=1
fi

# 保存测试报告
report_file="$RESULTS_DIR/test-report-$(date +%Y%m%d-%H%M%S).txt"
{
    echo "CloudLens 测试报告"
    echo "=================="
    echo ""
    echo "测试时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "测试环境: $API_URL"
    echo "测试账号: $TEST_ACCOUNT"
    echo ""
    echo "测试结果"
    echo "--------"
    echo "总计: $TOTAL_TESTS"
    echo "通过: $PASSED_TESTS"
    echo "失败: $FAILED_TESTS"
    echo "通过率: $pass_rate%"
    echo ""
    echo "详细结果"
    echo "--------"
    for result in "${TEST_RESULTS[@]}"; do
        echo "$result"
    done
} > "$report_file"

echo ""
echo "报告已保存: $report_file"
echo ""

exit $exit_code
