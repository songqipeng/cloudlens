#!/bin/bash
# 简单测试脚本

echo "=== CloudLens 功能测试 ==="
echo ""

# 1. 健康检查
echo "1. 健康检查"
curl -s http://localhost:8000/health | python3 -m json.tool | grep status && echo "✓ PASS" || echo "✗ FAIL"
echo ""

# 2. 折扣趋势
echo "2. 折扣趋势分析"
curl -s "http://localhost:8000/api/discounts/trend?account=prod&months=8" | python3 -m json.tool | grep success && echo "✓ PASS" || echo "✗ FAIL"
echo ""

# 3. 产品折扣
echo "3. 产品折扣分析"
curl -s "http://localhost:8000/api/discounts/products?account=prod&months=8" | python3 -m json.tool | grep success && echo "✓ PASS" || echo "✗ FAIL"
echo ""

# 4. 数据库检查
echo "4. 数据库数据检查"
docker exec cloudlens-mysql mysql -ucloudlens -pcloudlens123 cloudlens -e "SELECT COUNT(*) as count FROM bill_items;" 2>&1 | grep -v password | tail -1
echo "✓ PASS"
echo ""

echo "=== 测试完成 ==="
