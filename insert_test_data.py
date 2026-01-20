#!/usr/bin/env python3
"""插入测试数据以验证account_id修复"""

import mysql.connector
from datetime import datetime, timedelta
import random

# 连接数据库
conn = mysql.connector.connect(
    host='localhost',
    port=3306,
    user='cloudlens',
    password='cloudlens123',
    database='cloudlens'
)
cursor = conn.cursor()

print("=" * 60)
print("插入测试数据")
print("=" * 60)

# 测试账号
test_accounts = [
    {
        'account_id': 'aliyun-prod',
        'account_name': 'aliyun-prod',
        'products': ['云服务器ECS', '对象存储OSS', 'RDS', '负载均衡SLB']
    },
    {
        'account_id': 'aliyun-test',
        'account_name': 'aliyun-test',
        'products': ['云服务器ECS', '对象存储OSS']
    }
]

# 生成测试数据
total_inserted = 0
base_date = datetime(2024, 1, 1)

for account in test_accounts:
    print(f"\n插入账号数据: {account['account_id']}")

    # 为每个月生成数据
    for month_offset in range(19):  # 19个月的数据
        billing_date = base_date + timedelta(days=30 * month_offset)
        billing_cycle = billing_date.strftime('%Y-%m')

        for product in account['products']:
            # 每个产品生成3-5条账单记录
            num_records = random.randint(3, 5)

            for i in range(num_records):
                # 生成随机金额
                official_price = round(random.uniform(100, 5000), 2)
                discount_rate = random.uniform(0.65, 0.95)  # 65%-95%折扣率
                actual_amount = round(official_price * discount_rate, 2)
                discount_amount = round(official_price - actual_amount, 2)

                item_id = f"{account['account_id']}-{billing_cycle}-{product}-{i+1}"

                cursor.execute("""
                    INSERT INTO bill_items (
                        item_id, account_id, account_name, billing_cycle,
                        product_name, official_price, discount_amount,
                        actual_amount, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON DUPLICATE KEY UPDATE
                        official_price = VALUES(official_price),
                        discount_amount = VALUES(discount_amount),
                        actual_amount = VALUES(actual_amount)
                """, (
                    item_id,
                    account['account_id'],
                    account['account_name'],
                    billing_cycle,
                    product,
                    official_price,
                    discount_amount,
                    actual_amount,
                    datetime.now()
                ))

                total_inserted += 1

        if month_offset % 3 == 0:
            print(f"  ✓ 已插入到 {billing_cycle}")

# 提交
conn.commit()

# 验证数据
cursor.execute("""
    SELECT account_id, COUNT(*) as count,
           MIN(billing_cycle) as first_month,
           MAX(billing_cycle) as last_month,
           ROUND(SUM(official_price), 2) as total_official,
           ROUND(SUM(discount_amount), 2) as total_discount,
           ROUND(SUM(actual_amount), 2) as total_actual
    FROM bill_items
    GROUP BY account_id
""")

print("\n" + "=" * 60)
print("数据插入完成！")
print("=" * 60)
print(f"\n总共插入: {total_inserted} 条记录\n")
print("账号汇总:")
print(f"{'账号ID':<20} {'记录数':<10} {'月份范围':<20} {'总金额':<15}")
print("-" * 80)

for row in cursor.fetchall():
    account_id, count, first, last, official, discount, actual = row
    print(f"{account_id:<20} {count:<10} {first} - {last:<10} ¥{actual:,.2f}")

cursor.close()
conn.close()

print("\n✅ 测试数据已准备就绪！")
print("\n测试命令:")
print("  curl 'http://localhost:8000/api/discounts/trend?account=aliyun-prod&months=19'")
