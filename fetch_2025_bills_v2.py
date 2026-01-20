#!/usr/bin/env python3
"""
Fetch 2025 bill data from Aliyun and save to database
"""

from cloudlens.core.config import ConfigManager
from cloudlens.core.bill_fetcher import BillFetcher
from cloudlens.core.bill_storage import BillStorageManager
from cloudlens.core.database import get_database_adapter
import time

def main():
    print('='*60)
    print('Starting 2025 Bill Data Fetch')
    print('='*60)

    # Initialize - use first available account from config instead of hardcoding
    cm = ConfigManager()
    accounts = cm.list_accounts()
    if not accounts:
        raise Exception("No accounts configured in config.json")
    account = accounts[0]  # Use first account (or could add CLI parameter to select)
    print(f'Using account: {account.name} ({account.alias or "No alias"})')

    # Use BillFetcher with database enabled
    fetcher = BillFetcher(
        access_key_id=account.access_key_id,
        access_key_secret=account.access_key_secret,
        region=account.region,
        use_database=True  # This will use BillStorageManager internally
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

            # Insert using BillStorageManager (use account name from config, not hardcoded)
            inserted, skipped = fetcher._storage.insert_bill_items(
                account_id=account.name,
                billing_cycle=billing_cycle,
                items=bills
            )

            print(f'  ✓ Inserted {inserted} records, skipped {skipped}')
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
        amount = float(row.get('total', 0) or 0)
        total_count += count
        total_amount += amount
        print(f'  {row["billing_cycle"]}: {count:,} records, ¥{amount:,.2f}')

    print(f'\nTotal: {total_count:,} records, ¥{total_amount:,.2f}')
    print('='*60)
    print('✓ Done!')

if __name__ == '__main__':
    main()
