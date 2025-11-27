import json
import os
import keyring
from typing import Dict, Optional, List
from dataclasses import dataclass

CONFIG_FILE = "config.json"
KEYRING_SERVICE = "cloudlens_cli"

@dataclass
class AccountConfig:
    name: str
    provider: str
    region: str
    access_key_id: str
    access_key_secret: str = ""  # 运行时从keyring加载
    use_keyring: bool = True

class ConfigManager:
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.accounts: Dict[str, AccountConfig] = {}  # key: "provider:name"
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                
            # 解析新版配置结构
            # { "accounts": [ { "name": "prod", "provider": "aliyun", ... } ] }
            for acc_data in data.get("accounts", []):
                account = AccountConfig(
                    name=acc_data["name"],
                    provider=acc_data["provider"],
                    region=acc_data.get("region", "cn-hangzhou"),
                    access_key_id=acc_data["access_key_id"],
                    use_keyring=acc_data.get("use_keyring", True)
                )
                
                # 尝试从Keyring加载Secret
                if account.use_keyring:
                    secret = keyring.get_password(KEYRING_SERVICE, f"{account.provider}:{account.name}")
                    if secret:
                        account.access_key_secret = secret
                else:
                    # 兼容明文存储(不推荐)
                    account.access_key_secret = acc_data.get("access_key_secret", "")
                
                # 使用 provider:name 作为key，支持跨provider重名
                key = f"{account.provider}:{account.name}"
                self.accounts[key] = account
                
        except Exception as e:
            print(f"Failed to load config: {e}")

    def add_account(self, account: AccountConfig):
        """添加或更新账号"""
        key = f"{account.provider}:{account.name}"
        self.accounts[key] = account
        
        # 保存Secret到Keyring
        if account.use_keyring and account.access_key_secret:
            keyring.set_password(
                KEYRING_SERVICE, 
                f"{account.provider}:{account.name}", 
                account.access_key_secret
            )
        
        self.save_config()

    def save_config(self):
        """保存配置文件(不含Secret)"""
        data = {"accounts": []}
        for acc in self.accounts.values():
            acc_dict = {
                "name": acc.name,
                "provider": acc.provider,
                "region": acc.region,
                "access_key_id": acc.access_key_id,
                "use_keyring": acc.use_keyring
            }
            if not acc.use_keyring:
                acc_dict["access_key_secret"] = acc.access_key_secret
            data["accounts"].append(acc_dict)
            
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_account(self, name: str, provider: str = None) -> Optional[AccountConfig]:
        """
        获取账号配置
        如果指定provider，则返回该provider下的账号
        如果不指定provider，则返回第一个匹配name的账号
        """
        if provider:
            key = f"{provider}:{name}"
            return self.accounts.get(key)
        else:
            # 不指定provider时，返回第一个匹配的
            for key, acc in self.accounts.items():
                if acc.name == name:
                    return acc
            return None

    def list_accounts(self) -> List[AccountConfig]:
        return list(self.accounts.values())
