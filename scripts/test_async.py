import asyncio
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

from core.config import ConfigManager
from providers.aliyun.async_provider import AsyncAliyunProvider

async def main():
    print("🚀 Starting Async Provider Test...")
    
    cm = ConfigManager()
    accounts = cm.list_accounts()
    if not accounts:
        print("❌ No accounts found")
        return
        
    account = accounts[0]
    print(f"Using account: {account.name}")
    
    provider = AsyncAliyunProvider(
        account_name=account.name,
        access_key=account.access_key_id,
        secret_key=account.access_key_secret,
        region=account.region
    )
    
    start_time = time.time()
    
    # Test parallel fetching
    print("\n📦 Fetching ECS, RDS, Redis, SLB in parallel...")
    results = await provider.list_resources_parallel(["ecs", "rds", "redis", "slb"])
    
    duration = time.time() - start_time
    
    print(f"\n✅ Done in {duration:.2f} seconds")
    for r_type, resources in results.items():
        print(f"  - {r_type.upper()}: {len(resources)} resources")

if __name__ == "__main__":
    asyncio.run(main())
