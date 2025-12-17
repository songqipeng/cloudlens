import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import ConfigManager
from cli.utils import get_provider

def check_public_endpoints(account_name: str = None):
    """
    检查数据库公网暴露情况
    
    Args:
        account_name: 账号名称，如果不提供则使用第一个可用账号
    """
    cm = ConfigManager()
    
    if not account_name:
        accounts = cm.list_accounts()
        if not accounts:
            print("No accounts found")
            return
        account_name = accounts[0].name
    
    acc = cm.get_account(account_name)
    if not acc:
        print(f"Account '{account_name}' not found")
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
    import sys
    account_name = sys.argv[1] if len(sys.argv) > 1 else None
    check_public_endpoints(account_name)
