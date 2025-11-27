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

            migrated_to_keyring = False
                
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
                    # 兼容明文存储(不推荐)，自动迁移到 keyring
                    plaintext_secret = acc_data.get("access_key_secret", "")
                    if plaintext_secret:
                        keyring.set_password(
                            KEYRING_SERVICE,
                            f"{account.provider}:{account.name}",
                            plaintext_secret
                        )
                        account.access_key_secret = plaintext_secret
                        account.use_keyring = True
                        migrated_to_keyring = True
                        print(f"⚠️ 检测到账号 {account.name} 的明文密钥，已迁移到系统 Keyring。")
                    else:
                        print(f"⚠️ 账号 {account.name} 未配置密钥，建议重新添加并存储到 Keyring。")
                
                # 使用 provider:name 作为key，支持跨provider重名
                key = f"{account.provider}:{account.name}"
                self.accounts[key] = account

            # 如发生迁移，回写配置以移除明文
            if migrated_to_keyring:
                self.save_config()
                
        except Exception as e:
            print(f"Failed to load config: {e}")

    def add_account(self, account: AccountConfig):
        """添加或更新账号"""
        # 强制使用 Keyring 存储密钥，避免明文
        if not account.use_keyring:
            print(f"⚠️ 账号 {account.name} 未启用 Keyring，已自动开启以避免明文存储。")
            account.use_keyring = True

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
        """保存配置文件(不含Secret；强制Keyring)"""
        data = {"accounts": []}
        for acc in self.accounts.values():
            acc_dict = {
                "name": acc.name,
                "provider": acc.provider,
                "region": acc.region,
                "access_key_id": acc.access_key_id,
                "use_keyring": True  # 强制 Keyring
            }
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
