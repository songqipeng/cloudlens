
import sys
import os
import logging
sys.path.append(os.getcwd())

from core.config import ConfigManager
from providers.aliyun.provider import AliyunProvider

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VerifyOSS")

def verify_oss():
    account_name = "ydzn"
    cm = ConfigManager()
    account_config = cm.get_account(account_name)
    
    if not account_config:
        print(f"Error: Account {account_name} not found.")
        return

    print(f"Checking OSS for account: {account_name}")
    
    # OSS listing is global, but our implementation is bound to a provider instance.
    # We use cn-hangzhou as the entry point.
    provider = AliyunProvider(account_config.name, account_config.access_key_id, account_config.access_key_secret, "cn-hangzhou")
    
    try:
        buckets = provider.list_buckets()
        print(f"\nFound {len(buckets)} buckets:")
        
        for b in buckets:
            print(f"- Name: {b.name}")
            print(f"  Region: {b.region}")
            print(f"  StorageClass: {b.spec}")
            # Check ACL
            acl = b.raw_data.get("acl", {}).get("Grant", "unknown")
            print(f"  ACL: {acl}")
            
            if acl in ["public-read", "public-read-write"]:
                print(f"  [WARNING] Public Bucket Detected!")
            print("-" * 30)
            
    except Exception as e:
        print(f"Failed to list buckets: {e}")

if __name__ == "__main__":
    verify_oss()
