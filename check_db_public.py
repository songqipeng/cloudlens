import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import ConfigManager
from main_cli import get_provider

def check_public_endpoints():
    cm = ConfigManager()
    acc = cm.get_account("zmyc")
    if not acc:
        print("Account zmyc not found")
        return

    provider = get_provider(acc)
    if not provider:
        print("Provider not found")
        return

    print("Checking RDS...")
    try:
        rds_list = provider.list_rds()
        for r in rds_list:
            if r.public_ips:
                print(f"RDS Public IP/Domain: {r.id} - {r.public_ips}")
    except Exception as e:
        print(f"RDS Error: {e}")

    print("Checking Redis...")
    try:
        redis_list = provider.list_redis()
        for r in redis_list:
            if r.public_ips:
                print(f"Redis Public IP/Domain: {r.id} - {r.public_ips}")
    except Exception as e:
        print(f"Redis Error: {e}")

if __name__ == "__main__":
    check_public_endpoints()
