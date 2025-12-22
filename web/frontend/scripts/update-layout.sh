#!/bin/bash
# 批量更新所有页面使用DashboardLayout

# 需要更新的文件列表
FILES=(
    "app/security/page.tsx"
    "app/security/cis/page.tsx"
    "app/optimization/page.tsx"
    "app/reports/page.tsx"
    "app/settings/page.tsx"
    "app/settings/accounts/page.tsx"
    "app/cost/budget/page.tsx"
    "app/resources/[id]/page.tsx"
)

echo "开始更新页面布局..."

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "处理: $file"
        # 这里可以添加sed命令来批量替换
    else
        echo "文件不存在: $file"
    fi
done

echo "完成!"








