
import sys
import os
sys.path.append(os.getcwd())
import logging

from cloudlens.core.cache import CacheManager
from cloudlens.core.config import ConfigManager

logging.basicConfig(level=logging.INFO)

def inspect_cache():
    cm = ConfigManager()
    account = cm.list_accounts()[0].name
    
    print(f"Checking cache for account: {account}")
    
    # Check cost_overview cache (used by Cost Analysis page)
    cache_manager = CacheManager(ttl_seconds=86400)
    cost_overview = cache_manager.get(resource_type="cost_overview", account_name=account)
    
    if cost_overview:
        print("\n[Cost Analysis Cache (cost_overview)]")
        print(f"Total Cost: {cost_overview.get('total_cost')}")
        print(f"Billing Cycle: {cost_overview.get('billing_cycle')}")
    else:
        print("\n[Cost Analysis Cache (cost_overview)]")
        print("MISSING")

    # Check dashboard cache? Dashboard usually calls _get_billing_overview_totals directly which caches differently?
    # Let's check _get_billing_overview_totals cache key if possible, but it uses internal logic.
    # It caches to DB (bill_items), not CacheManager usually, or it might?
    
    # Check if there is a 'dashboard_summary' cache
    dashboard_cache = cache_manager.get(resource_type="dashboard_summary", account_name=account)
    if dashboard_cache:
         print("\n[Dashboard Cache (dashboard_summary)]")
         print(f"Total Cost: {dashboard_cache.get('total_cost')}")
    else:
         print("\n[Dashboard Cache (dashboard_summary)]")
         print("MISSING")

if __name__ == "__main__":
    inspect_cache()
