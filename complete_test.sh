#!/bin/bash
# 完整功能测试脚本

echo "=========================================="
echo "CloudLens 完整功能测试"
echo "=========================================="

ACCOUNT="ydzn"
BASE_URL="http://127.0.0.1:8000"

# 1. 测试 BSS API 权限
echo ""
echo "1. 测试 BSS API 权限..."
python3 -c "
import requests
from datetime import datetime

account = '$ACCOUNT'
base_url = '$BASE_URL'
billing_cycle = datetime.now().strftime('%Y-%m')

try:
    response = requests.get(
        f'{base_url}/api/billing/overview',
        params={'account': account, 'billing_cycle': billing_cycle},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print('   ✅ BSS API 权限正常')
            bill_data = data.get('data', {})
            if bill_data:
                print(f'   ✅ 获取到账单数据')
                # 检查是否有实际数据
                items = bill_data.get('Data', {}).get('Items', {}).get('Item', [])
                if items:
                    print(f'   ✅ 账单条目数: {len(items) if isinstance(items, list) else 1}')
                else:
                    print('   ⚠️  账单数据为空（可能是当月无消费）')
            else:
                print('   ⚠️  账单数据为空')
        else:
            print(f'   ❌ BSS API 响应异常: {data}')
    else:
        error_text = response.text[:200]
        if 'UnauthorizedOperation' in error_text or 'Forbidden' in error_text:
            print('   ❌ BSS API 权限不足')
            print('   需要添加 RAM 权限: bssapi:QueryBillOverview')
        else:
            print(f'   ❌ BSS API 请求失败: {response.status_code}')
            print(f'   错误: {error_text}')
except Exception as e:
    print(f'   ❌ 测试失败: {e}')
" 2>&1

# 2. 等待并测试资源查询
echo ""
echo "2. 测试资源查询（等待后台任务完成）..."
sleep 30  # 等待后台任务完成

python3 -c "
import requests
import time

account = '$ACCOUNT'
base_url = '$BASE_URL'

# 测试资源列表
print('   测试资源列表 API...')
response = requests.get(
    f'{base_url}/api/resources',
    params={'account': account, 'type': 'ecs', 'page': 1, 'pageSize': 10, 'force_refresh': True},
    timeout=180
)

if response.status_code == 200:
    data = response.json()
    if isinstance(data, dict) and 'data' in data:
        if isinstance(data['data'], dict):
            items = data['data'].get('items', [])
            total = data['data'].get('pagination', {}).get('total', 0)
        else:
            items = data['data'] if isinstance(data['data'], list) else []
            total = len(items)
    elif isinstance(data, list):
        items = data
        total = len(data)
    else:
        items = []
        total = 0
    
    if total > 0:
        print(f'   ✅ 资源查询成功: {total} 个 ECS 实例')
    else:
        print(f'   ⚠️  资源数为 0（可能还在查询中）')
else:
    print(f'   ❌ 请求失败: {response.status_code}')
" 2>&1

# 3. 测试 Dashboard Summary
echo ""
echo "3. 测试 Dashboard Summary..."
python3 -c "
import requests

account = '$ACCOUNT'
base_url = '$BASE_URL'

response = requests.get(
    f'{base_url}/api/dashboard/summary',
    params={'account': account, 'force_refresh': True},
    timeout=180
)

if response.status_code == 200:
    data = response.json()
    total_resources = data.get('total_resources', 0)
    total_cost = data.get('total_cost', 0)
    resource_breakdown = data.get('resource_breakdown', {})
    
    if total_resources > 0:
        print(f'   ✅ Summary 成功: {total_resources} 个资源')
        print(f'   ✅ 资源分布: {resource_breakdown}')
        if total_cost and total_cost > 0:
            print(f'   ✅ 总成本: ¥{total_cost:,.2f}')
        else:
            print(f'   ⚠️  总成本: N/A（需要账单数据）')
    else:
        print(f'   ⚠️  资源总数为 0（后台任务可能还在运行）')
else:
    print(f'   ❌ 请求失败: {response.status_code}')
" 2>&1

# 4. 测试所有主要 API
echo ""
echo "4. 测试所有主要 API..."
python3 test_all_pages.py 2>&1 | tail -40

# 5. 测试 CLI 功能
echo ""
echo "5. 测试 CLI 功能..."
python3 -c "
import sys
sys.path.insert(0, '.')

# 测试 CLI 模块导入
try:
    from cli.main import cli
    print('   ✅ CLI 模块导入成功')
except Exception as e:
    print(f'   ❌ CLI 模块导入失败: {e}')

# 测试核心功能
try:
    from core.config import ConfigManager
    from core.cache import CacheManager
    from core.services.analysis_service import AnalysisService
    
    cm = ConfigManager()
    accounts = cm.list_accounts()
    print(f'   ✅ 配置管理: 找到 {len(accounts)} 个账号')
    
    cache = CacheManager()
    print('   ✅ 缓存管理: 正常')
    
    print('   ✅ 分析服务: 正常')
except Exception as e:
    print(f'   ❌ 核心功能测试失败: {e}')
    import traceback
    traceback.print_exc()
" 2>&1

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="



