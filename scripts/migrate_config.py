import json
import os
from core.config import ConfigManager, AccountConfig

OLD_CONFIG = "config.json"

def migrate():
    if not os.path.exists(OLD_CONFIG):
        print("No config.json found.")
        return

    with open(OLD_CONFIG, 'r') as f:
        old_data = json.load(f)

    if "accounts" in old_data:
        print("Config already in new format.")
        return

    cm = ConfigManager()
    
    # Import old credential manager
    try:
        from utils.credential_manager import CredentialManager
    except ImportError:
        print("Could not import CredentialManager, skipping keyring migration")
        CredentialManager = None

    tenants = old_data.get("tenants", {})
    for name, data in tenants.items():
        print(f"Migrating tenant: {name}")
        
        ak = data.get("access_key_id")
        sk = data.get("access_key_secret")
        
        # Try to get secret from old keyring if needed
        if data.get("use_keyring") and CredentialManager:
            creds = CredentialManager.get_credentials("aliyun", name)
            if creds:
                sk = creds.get("access_key_secret")
                # Also try to get AK from keyring if not in config
                if not ak:
                    ak = creds.get("access_key_id")
                print(f"  Retrieved credentials from legacy keyring for {name}")

        if not ak:
            print(f"Skipping {name}: No AccessKeyID found.")
            continue

        # Create new account config
        acc = AccountConfig(
            name=name,
            provider="aliyun",
            region="cn-hongkong", # Defaulting to HK as we know CF is there
            access_key_id=ak,
            access_key_secret=sk or "",
            use_keyring=True # Always use keyring for new config
        )
        
        cm.add_account(acc)
        print(f"Migrated {name}")

if __name__ == "__main__":
    migrate()
