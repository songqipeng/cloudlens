#!/usr/bin/env python3
"""
Fetch 2025 bill data from Aliyun and save to database
"""

from cloudlens.core.config import ConfigManager
from cloudlens.core.bill_fetcher import BillFetcher
from cloudlens.core.database import get_database_adapter
import time

def main():
    print('='*60)
    print('Starting 2025 Bill Data Fetch')
    print('='*60)

    # Initialize
    cm = ConfigManager()
    account = cm.get_account('prod')

    fetcher = BillFetcher(
        access_key_id=account.access_key_id,
        access_key_secret=account.access_key_secret,
        region=account.region,
        use_database=False
    )

    db = get_database_adapter()

    # Fetch all 12 months
    total_fetched = 0
    total_inserted = 0

    for month in range(1, 13):
        billing_cycle = f'2025-{month:02d}'
        print(f'\n[{month}/12] Processing {billing_cycle}...')

        try:
            # Fetch bills
            bills = fetcher.fetch_instance_bill(
                billing_cycle=billing_cycle,
                max_records=100000
            )

            if not bills:
                print(f'  ✗ No data returned')
                continue

            print(f'  ✓ Fetched {len(bills)} records')
            total_fetched += len(bills)

            # Insert into database
            inserted = 0
            for bill in bills:
                try:
                    query = """
                        INSERT IGNORE INTO bill_items (
                            account_id, billing_cycle, billing_date,
                            product_name, product_code, product_type,
                            subscription_type, instance_id, instance_config,
                            region, zone, `usage`, usage_unit,
                            list_price, list_price_unit, pretax_gross_amount,
                            invoice_discount, deducted_by_coupons, deducted_by_cash_coupons,
                            deducted_by_prepaid_card, payment_amount, outstanding_amount,
                            currency, owner_id, cost_unit, resource_group
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """

                    params = (
                        'prod',
                        billing_cycle,
                        bill.get('BillingDate', ''),
                        bill.get('ProductName', ''),
                        bill.get('ProductCode', ''),
                        bill.get('ProductType', ''),
                        bill.get('SubscriptionType', ''),
                        bill.get('InstanceID', ''),
                        bill.get('InstanceConfig', ''),
                        bill.get('Region', ''),
                        bill.get('Zone', ''),
                        float(bill.get('Usage', 0) or 0),
                        bill.get('UsageUnit', ''),
                        float(bill.get('ListPrice', 0) or 0),
                        bill.get('ListPriceUnit', ''),
                        float(bill.get('PretaxGrossAmount', 0) or 0),
                        float(bill.get('InvoiceDiscount', 0) or 0),
                        float(bill.get('DeductedByCoupons', 0) or 0),
                        float(bill.get('DeductedByCashCoupons', 0) or 0),
                        float(bill.get('DeductedByPrepaidCard', 0) or 0),
                        float(bill.get('PaymentAmount', 0) or 0),
                        float(bill.get('OutstandingAmount', 0) or 0),
                        bill.get('Currency', 'CNY'),
                        bill.get('OwnerID', ''),
                        bill.get('CostUnit', ''),
                        bill.get('ResourceGroup', '')
                    )

                    db.execute(query, params)
                    inserted += 1

                except Exception as e:
                    # Skip duplicates and continue
                    if 'Duplicate entry' not in str(e):
                        print(f'    Warning: {e}')

            print(f'  ✓ Inserted {inserted} records')
            total_inserted += inserted

            # Rate limiting
            time.sleep(1)

        except Exception as e:
            print(f'  ✗ Error: {e}')
            import traceback
            traceback.print_exc()

    print('\n' + '='*60)
    print('Summary')
    print('='*60)
    print(f'Total fetched: {total_fetched:,} records')
    print(f'Total inserted: {total_inserted:,} records')

    # Verify database
    print('\nDatabase verification:')
    result = db.query("""
        SELECT
            billing_cycle,
            COUNT(*) as count,
            SUM(payment_amount) as total
        FROM bill_items
        WHERE billing_cycle LIKE '2025-%'
        GROUP BY billing_cycle
        ORDER BY billing_cycle
    """)

    total_count = 0
    total_amount = 0.0

    for row in result:
        count = row.get('count', 0)
        amount = row.get('total', 0) or 0
        total_count += count
        total_amount += amount
        print(f'  {row["billing_cycle"]}: {count:,} records, ¥{amount:,.2f}')

    print(f'\nTotal: {total_count:,} records, ¥{total_amount:,.2f}')
    print('='*60)
    print('✓ Done!')

if __name__ == '__main__':
    main()
