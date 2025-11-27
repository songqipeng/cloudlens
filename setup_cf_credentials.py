#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CF租户凭证配置脚本
"""

import getpass
import json
import sys
from pathlib import Path


def setup_cf_credentials():
    """配置CF租户的AK/SK"""
    config_file = Path("config.json")

    if not config_file.exists():
        print("❌ 配置文件 config.json 不存在")
        return False

    # 读取现有配置
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 检查cf租户是否存在
    if "cf" not in config.get("tenants", {}):
        print("❌ cf租户配置不存在，请先添加")
        return False

    print("🔐 配置CF租户凭证")
    print("=" * 60)

    # 获取AccessKey ID
    access_key_id = input("请输入 AccessKey ID: ").strip()
    if not access_key_id:
        print("❌ AccessKey ID 不能为空")
        return False

    # 获取AccessKey Secret（隐藏输入）
    access_key_secret = getpass.getpass("请输入 AccessKey Secret: ").strip()
    if not access_key_secret:
        print("❌ AccessKey Secret 不能为空")
        return False

    # 可选：显示名称
    display_name = input("请输入显示名称 (默认: CF租户): ").strip() or "CF租户"

    # 更新配置
    config["tenants"]["cf"]["access_key_id"] = access_key_id
    config["tenants"]["cf"]["access_key_secret"] = access_key_secret
    config["tenants"]["cf"]["display_name"] = display_name

    # 保存配置
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    print("\n✅ CF租户凭证配置成功！")
    print(f"   租户名称: cf")
    print(f"   显示名称: {display_name}")
    print(f"   AccessKey ID: {access_key_id[:8]}...")

    # 询问是否使用Keyring存储（更安全）
    use_keyring = input("\n是否使用系统密钥环存储Secret（更安全）? [y/N]: ").strip().lower()
    if use_keyring == "y":
        try:
            import keyring

            keyring.set_password(
                "aliyunidle",
                "aliyun_cf",
                json.dumps(
                    {"access_key_id": access_key_id, "access_key_secret": access_key_secret}
                ),
            )
            # 更新配置使用keyring
            config["tenants"]["cf"]["use_keyring"] = True
            config["tenants"]["cf"]["keyring_key"] = "aliyun_cf"
            # 清空配置文件中的secret
            config["tenants"]["cf"]["access_key_secret"] = ""
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print("✅ 凭证已安全保存到系统密钥环")
        except ImportError:
            print("⚠️  keyring库未安装，跳过密钥环存储")
            print("   可以运行: pip install keyring")
        except Exception as e:
            print(f"⚠️  保存到密钥环失败: {e}")

    return True


if __name__ == "__main__":
    try:
        success = setup_cf_credentials()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ 用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 配置失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
