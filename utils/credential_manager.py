#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
凭证管理器（基于Keyring）
"""

import getpass
import json
from typing import Dict, Optional


class CredentialManager:
    """基于系统密钥环的凭证管理"""

    SERVICE_NAME = "aliyunidle"

    @staticmethod
    def save_credentials(cloud: str, tenant: str, credentials: Dict[str, str]):
        """
        保存凭证到系统密钥环

        Args:
            cloud: 云厂商（aliyun, tencent等）
            tenant: 租户名称
            credentials: 凭证字典
        """
        try:
            import keyring

            key = f"{cloud}_{tenant}"
            value = json.dumps(credentials)
            keyring.set_password(CredentialManager.SERVICE_NAME, key, value)
            print(f"✅ 凭证已安全保存到系统密钥环: {cloud}/{tenant}")
        except ImportError:
            print("❌ keyring库未安装，无法使用密钥管理功能")
            print("   请运行: pip install keyring")
        except Exception as e:
            print(f"❌ 保存凭证失败: {e}")

    @staticmethod
    def get_credentials(cloud: str, tenant: str) -> Optional[Dict[str, str]]:
        """
        从系统密钥环获取凭证

        Args:
            cloud: 云厂商
            tenant: 租户名称

        Returns:
            凭证字典，如果不存在则返回None
        """
        try:
            import keyring

            key = f"{cloud}_{tenant}"
            value = keyring.get_password(CredentialManager.SERVICE_NAME, key)
            if value:
                return json.loads(value)
            return None
        except ImportError:
            return None
        except Exception as e:
            print(f"⚠️  获取凭证失败: {e}")
            return None

    @staticmethod
    def delete_credentials(cloud: str, tenant: str):
        """删除凭证"""
        try:
            import keyring

            key = f"{cloud}_{tenant}"
            keyring.delete_password(CredentialManager.SERVICE_NAME, key)
            print(f"✅ 凭证已删除: {cloud}/{tenant}")
        except ImportError:
            print("❌ keyring库未安装")
        except Exception as e:
            print(f"⚠️  删除凭证失败: {e}")

    @staticmethod
    def list_credentials() -> Dict[str, list]:
        """列出所有已保存的凭证（仅列出键名，不读取实际值）"""
        try:
            import keyring

            # Keyring没有直接列出所有键的API，需要从config.json推断
            # 这里返回空，实际使用时从config.json读取租户列表
            return {}
        except ImportError:
            return {}


def setup_credentials_interactive():
    """交互式设置凭证"""
    print("🔐 凭证管理器")
    print("=" * 60)

    cloud = input("云厂商 [aliyun/tencent/aws] (默认: aliyun): ").strip() or "aliyun"
    tenant = input("租户名称: ").strip()

    if not tenant:
        print("❌ 租户名称不能为空")
        return

    if cloud == "aliyun":
        ak = input("Access Key ID: ").strip()
        sk = getpass.getpass("Access Key Secret (输入时不显示): ")
        if not ak or not sk:
            print("❌ Access Key ID和Secret不能为空")
            return
        credentials = {"access_key_id": ak, "access_key_secret": sk}
    elif cloud == "tencent":
        secret_id = input("Secret ID: ").strip()
        secret_key = getpass.getpass("Secret Key (输入时不显示): ")
        if not secret_id or not secret_key:
            print("❌ Secret ID和Key不能为空")
            return
        credentials = {"secret_id": secret_id, "secret_key": secret_key}
    else:
        print(f"❌ 不支持的云厂商: {cloud}")
        return

    CredentialManager.save_credentials(cloud, tenant, credentials)

    # 更新config.json标记（可选）
    try:
        import json
        from pathlib import Path

        config_file = Path("config.json")
        if config_file.exists():
            with open(config_file, "r") as f:
                config = json.load(f)

            # 确保tenants结构存在
            if "tenants" not in config:
                config["tenants"] = {}

            # 添加或更新租户配置（标记使用keyring）
            if tenant not in config["tenants"]:
                config["tenants"][tenant] = {}

            config["tenants"][tenant]["use_keyring"] = True
            config["tenants"][tenant]["keyring_key"] = f"{cloud}_{tenant}"
            config["tenants"][tenant]["display_name"] = config["tenants"][tenant].get(
                "display_name", tenant
            )

            with open(config_file, "w") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            print(f"✅ 配置文件已更新")
    except Exception as e:
        print(f"⚠️  更新配置文件失败: {e}")


def get_credentials_from_config_or_keyring(
    cloud: str, tenant: str, config: Dict
) -> Optional[Dict[str, str]]:
    """
    从配置文件或Keyring获取凭证

    Args:
        cloud: 云厂商
        tenant: 租户名称
        config: 配置字典

    Returns:
        凭证字典
    """
    tenant_config = config.get("tenants", {}).get(tenant, {})

    # 检查是否使用keyring
    if tenant_config.get("use_keyring"):
        credentials = CredentialManager.get_credentials(cloud, tenant)
        if credentials:
            return credentials
        else:
            print(f"⚠️  Keyring中未找到凭证 {cloud}/{tenant}，尝试从配置文件读取")

    # 从配置文件读取
    if cloud == "aliyun":
        ak = tenant_config.get("access_key_id")
        sk = tenant_config.get("access_key_secret")
        if ak and sk:
            return {"access_key_id": ak, "access_key_secret": sk}

    return None
