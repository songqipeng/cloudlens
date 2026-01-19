# -*- coding: utf-8 -*-
import configparser
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import keyring


class CloudAccount:
    """云账号配置"""

    def __init__(
        self,
        name: str,
        provider: str,
        access_key_id: str,
        access_key_secret: str = None,
        region: str = None,
        alias: str = None,
    ):
        self.name = name  # 原始账号名称（用于数据关联，不可变）
        self.provider = provider
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region = region or "cn-hangzhou"
        self.alias = alias  # 显示别名（可选，用于前端显示）


class ConfigManager:
    """配置管理器 - 支持多源配置加载"""

    CONFIG_DIR = Path.home() / ".cloudlens"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    CREDENTIALS_FILE = CONFIG_DIR / "credentials"

    def __init__(self):
        self.config_dir = self.CONFIG_DIR
        self.config_file = self.CONFIG_FILE
        self.credentials_file = self.CREDENTIALS_FILE
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def add_account(
        self,
        name: str,
        provider: str,
        access_key_id: str,
        access_key_secret: str,
        region: str = None,
        alias: str = None,
    ):
        """
        添加账号配置
        密钥优先存储在系统 keyring 中，如果 keyring 不可用则存储在 JSON 文件中
        配置元数据存储在 JSON 文件
        """
        # 尝试保存密钥到 keyring，如果失败则存储在配置文件中
        try:
            # 检查 keyring 是否可用（不是 fail backend）
            keyring_backend = keyring.get_keyring()
            if hasattr(keyring_backend, '__class__') and 'fail' not in str(keyring_backend.__class__).lower():
                keyring.set_password("cloudlens", f"{name}_access_key_secret", access_key_secret)
                use_keyring = True
            else:
                use_keyring = False
        except Exception:
            # keyring 不可用，使用配置文件存储
            use_keyring = False

        # 保存配置元数据
        config = self._load_config()

        if "accounts" not in config:
            config["accounts"] = []

        # 检查账号是否已存在
        existing = next((acc for acc in config["accounts"] if acc["name"] == name), None)
        if existing:
            existing["provider"] = provider
            existing["access_key_id"] = access_key_id
            existing["region"] = region or "cn-hangzhou"
            if alias is not None:
                existing["alias"] = alias
            # 如果 keyring 不可用，将密钥存储在配置文件中
            if not use_keyring:
                existing["access_key_secret"] = access_key_secret
        else:
            account_data = {
                "name": name,
                "provider": provider,
                "access_key_id": access_key_id,
                "region": region or "cn-hangzhou",
            }
            if alias:
                account_data["alias"] = alias
            # 如果 keyring 不可用，将密钥存储在配置文件中
            if not use_keyring:
                account_data["access_key_secret"] = access_key_secret
            config["accounts"].append(account_data)

        self._save_config(config)
        print(f"✅ Account '{name}' saved successfully!")

    def list_accounts(self) -> List[CloudAccount]:
        """
        列出所有账号，支持多源加载
        优先级：环境变量 > credentials 文件 > config.json + keyring
        """
        accounts = []

        # 1. 从环境变量加载
        env_account = self._load_from_env()
        if env_account:
            accounts.append(env_account)

        # 2. 从 credentials 文件加载
        cred_accounts = self._load_from_credentials_file()
        accounts.extend(cred_accounts)

        # 3. 从 config.json + keyring 加载
        config_accounts = self._load_from_config_file()
        # 去重：如果名称已存在，则跳过
        existing_names = {acc.name for acc in accounts}
        for acc in config_accounts:
            if acc.name not in existing_names:
                accounts.append(acc)

        return accounts

    def get_account(self, name: str) -> Optional[CloudAccount]:
        """获取指定账号"""
        accounts = self.list_accounts()
        return next((acc for acc in accounts if acc.name == name), None)

    def remove_account(self, name: str):
        """删除账号"""
        config = self._load_config()

        if "accounts" in config:
            config["accounts"] = [acc for acc in config["accounts"] if acc["name"] != name]
            self._save_config(config)

            # 同时删除 keyring 中的密钥
            try:
                keyring.delete_password("cloudlens", f"{name}_access_key_secret")
            except:
                pass

    def _load_from_env(self) -> Optional[CloudAccount]:
        """从环境变量加载配置"""
        access_key_id = os.getenv("CLOUDLENS_ACCESS_KEY_ID")
        access_key_secret = os.getenv("CLOUDLENS_ACCESS_KEY_SECRET")
        provider = os.getenv("CLOUDLENS_PROVIDER", "aliyun")
        profile = os.getenv("CLOUDLENS_PROFILE", "env")

        if access_key_id and access_key_secret:
            return CloudAccount(
                name=profile,
                provider=provider,
                access_key_id=access_key_id,
                access_key_secret=access_key_secret,
                region=os.getenv("CLOUDLENS_REGION", "cn-hangzhou"),
            )
        return None

    def _load_from_credentials_file(self) -> List[CloudAccount]:
        """从 ~/.cloudlens/credentials 文件加载"""
        if not self.credentials_file.exists():
            return []

        accounts = []
        config = configparser.ConfigParser()
        config.read(self.credentials_file)

        for section in config.sections():
            try:
                accounts.append(
                    CloudAccount(
                        name=section,
                        provider=config.get(section, "provider", fallback="aliyun"),
                        access_key_id=config.get(section, "access_key_id"),
                        access_key_secret=config.get(section, "access_key_secret"),
                        region=config.get(section, "region", fallback="cn-hangzhou"),
                    )
                )
            except:
                pass

        return accounts

    def _load_from_config_file(self) -> List[CloudAccount]:
        """从 config.json + keyring 加载"""
        config = self._load_config()
        accounts = []

        for acc_config in config.get("accounts", []):
            try:
                secret = None
                if acc_config.get("use_keyring", True):
                    secret = keyring.get_password(
                        "cloudlens", f"{acc_config['name']}_access_key_secret"
                    )

                # Fallback to config file if not in keyring
                if not secret:
                    secret = acc_config.get("access_key_secret")

                if secret:
                    accounts.append(
                        CloudAccount(
                            name=acc_config["name"],
                            provider=acc_config["provider"],
                            access_key_id=acc_config["access_key_id"],
                            access_key_secret=secret,
                            region=acc_config.get("region", "cn-hangzhou"),
                            alias=acc_config.get("alias"),
                        )
                    )
            except:
                pass

        return accounts

    def _load_config(self) -> dict:
        """加载配置文件"""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def _save_config(self, config: dict):
        """保存配置文件"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
