#!/bin/bash
# 修复和测试脚本

echo "=========================================="
echo "CloudLens 数据修复和测试"
echo "=========================================="

# 1. 重启后端服务
echo ""
echo "1. 重启后端服务..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
sleep 2
cd web/backend
nohup python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /tmp/cloudlens_backend.log 2>&1 &
BACKEND_PID=$!
echo "   ✅ 后端服务已启动 (PID: $BACKEND_PID)"
cd ../..
sleep 5

# 2. 等待服务就绪
echo ""
echo "2. 等待服务就绪..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:8000/api/accounts > /dev/null 2>&1; then
        echo "   ✅ 服务已就绪"
        break
    fi
    echo "   等待中... ($i/10)"
    sleep 1
done

# 3. 测试资源查询（强制刷新）
echo ""
echo "3. 测试资源查询（强制刷新）..."
sleep 3
python3 -c "
import requests
import time

account = 'ydzn'
base_url = 'http://127.0.0.1:8000'

print('   正在查询资源（这可能需要1-2分钟）...')
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
        print(f'   ✅ 成功！找到 {total} 个资源')
        print(f'   ✅ 返回 {len(items)} 条数据')
    else:
        print(f'   ⚠️  资源数为 0，检查后端日志...')
else:
    print(f'   ❌ 请求失败: {response.status_code}')
" 2>&1

# 4. 测试 Dashboard Summary
echo ""
echo "4. 测试 Dashboard Summary（强制刷新）..."
python3 -c "
import requests
import time

account = 'ydzn'
base_url = 'http://127.0.0.1:8000'

print('   正在查询 Summary（这可能需要1-2分钟）...')
response = requests.get(
    f'{base_url}/api/dashboard/summary',
    params={'account': account, 'force_refresh': True},
    timeout=180
)

if response.status_code == 200:
    data = response.json()
    total_resources = data.get('total_resources', 0)
    resource_breakdown = data.get('resource_breakdown', {})
    
    if total_resources > 0:
        print(f'   ✅ 成功！资源总数: {total_resources}')
        print(f'   ✅ 资源分布: {resource_breakdown}')
    else:
        print(f'   ⚠️  资源总数为 0，后台任务可能还在运行...')
        print(f'   ⚠️  请等待1-2分钟后刷新页面')
else:
    print(f'   ❌ 请求失败: {response.status_code}')
" 2>&1

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "如果资源查询成功，请："
echo "1. 在前端刷新页面"
echo "2. 检查各个功能页面是否显示数据"
echo ""
echo "如果仍有问题，请检查："
echo "- 后端日志: tail -f /tmp/cloudlens_backend.log"
echo "- 权限配置: 查看 PERMISSION_CHECK.md"
echo ""



