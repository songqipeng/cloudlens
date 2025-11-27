#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查当前AccessKey对应的身份和权限
"""

import json
import sys
import os

# 添加父目录到sys.path以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest


def check_current_identity(access_key_id, access_key_secret):
    """检查当前AccessKey的身份"""
    client = AcsClient(access_key_id, access_key_secret, "cn-hangzhou")

    print("🔍 检查当前AccessKey的身份和权限...")
    print("=" * 80)

    # 1. 获取当前用户信息
    try:
        request = CommonRequest()
        request.set_domain("ram.aliyuncs.com")
        request.set_protocol_type("https")
        request.set_method("POST")
        request.set_version("2015-05-01")
        request.set_action_name("GetUser")

        response = client.do_action_with_exception(request)
        data = json.loads(response)

        if "User" in data:
            user = data["User"]
            print("\n✅ 当前AccessKey对应的身份:")
            print("-" * 80)
            print(f"  用户类型: RAM用户")
            print(f"  用户名: {user.get('UserName', '')}")
            print(f"  用户ID: {user.get('UserId', '')}")
            print(f"  显示名称: {user.get('DisplayName', '')}")
            print(f"  创建时间: {user.get('CreateDate', '')}")

            # 获取该用户的权限
            user_name = user.get("UserName", "")
            check_user_permissions(client, user_name)
            return
    except Exception as e:
        # 如果不是RAM用户，可能是主账号
        pass

    # 2. 尝试获取账户别名（主账号）
    try:
        request = CommonRequest()
        request.set_domain("ram.aliyuncs.com")
        request.set_protocol_type("https")
        request.set_method("POST")
        request.set_version("2015-05-01")
        request.set_action_name("GetAccountAlias")

        response = client.do_action_with_exception(request)
        data = json.loads(response)

        if "AccountAlias" in data:
            print("\n✅ 当前AccessKey对应的身份:")
            print("-" * 80)
            print(f"  用户类型: 主账号")
            print(f"  账户别名: {data.get('AccountAlias', '')}")
            print(f"\n⚠️  主账号默认拥有所有权限，包括：")
            print("  • 查看所有RAM用户、用户组、角色")
            print("  • 管理所有资源")
            print("  • 授予和撤销权限")
            return
    except Exception as e:
        pass

    # 3. 尝试通过STS获取身份信息
    try:
        from aliyunsdksts.request.v20150401 import GetCallerIdentityRequest

        sts_client = AcsClient(access_key_id, access_key_secret, "cn-hangzhou")
        request = GetCallerIdentityRequest.GetCallerIdentityRequest()

        response = sts_client.do_action_with_exception(request)
        data = json.loads(response)

        print("\n✅ 当前AccessKey对应的身份:")
        print("-" * 80)
        print(f"  账户ID: {data.get('AccountId', '')}")
        print(f"  ARN: {data.get('Arn', '')}")
        print(f"  用户ID: {data.get('UserId', '')}")

        arn = data.get("Arn", "")
        if ":root" in arn or ":user/" not in arn:
            print(f"\n⚠️  这是主账号的AccessKey")
            print("  主账号默认拥有所有权限")
        else:
            # 提取用户名
            if ":user/" in arn:
                user_name = arn.split(":user/")[-1]
                print(f"  用户名: {user_name}")
                check_user_permissions(client, user_name)
    except Exception as e:
        print(f"\n❌ 无法确定身份: {e}")
        print("\n可能的原因:")
        print("  1. 这是主账号的AccessKey（主账号默认有所有权限）")
        print("  2. 这是RAM用户的AccessKey，且被授予了RAM读取权限")
        print("  3. 权限策略中包含了RAM相关的权限")


def check_user_permissions(client, user_name):
    """检查用户的权限"""
    print(f"\n📋 用户 {user_name} 的权限策略:")
    print("-" * 80)

    # 获取用户附加的策略
    try:
        request = CommonRequest()
        request.set_domain("ram.aliyuncs.com")
        request.set_protocol_type("https")
        request.set_method("POST")
        request.set_version("2015-05-01")
        request.set_action_name("ListPoliciesForUser")
        request.add_query_param("UserName", user_name)

        response = client.do_action_with_exception(request)
        data = json.loads(response)

        if "Policies" in data and "Policy" in data["Policies"]:
            policies = data["Policies"]["Policy"]
            if not isinstance(policies, list):
                policies = [policies]

            ram_permissions = []
            admin_permissions = []
            other_permissions = []

            for policy in policies:
                policy_name = policy.get("PolicyName", "")
                policy_type = policy.get("PolicyType", "")

                if "RAM" in policy_name.upper() or "ram" in policy_name.lower():
                    ram_permissions.append(f"{policy_name} ({policy_type})")
                elif "Admin" in policy_name or "Administrator" in policy_name:
                    admin_permissions.append(f"{policy_name} ({policy_type})")
                else:
                    other_permissions.append(f"{policy_name} ({policy_type})")

            if admin_permissions:
                print("  🔴 管理员权限:")
                for perm in admin_permissions:
                    print(f"     • {perm}")
                print("\n  ⚠️  管理员权限可以查看和管理所有资源，包括其他用户的权限")

            if ram_permissions:
                print("  🔵 RAM相关权限:")
                for perm in ram_permissions:
                    print(f"     • {perm}")
                print("\n  ✅ 这些权限允许查看RAM用户、用户组、角色等信息")

            if other_permissions:
                print("  📦 其他权限:")
                for perm in other_permissions[:10]:  # 只显示前10个
                    print(f"     • {perm}")
                if len(other_permissions) > 10:
                    print(f"     ... 还有 {len(other_permissions) - 10} 个权限")
    except Exception as e:
        print(f"  ⚠️  获取权限失败: {e}")

    # 检查用户所属的用户组
    try:
        request = CommonRequest()
        request.set_domain("ram.aliyuncs.com")
        request.set_protocol_type("https")
        request.set_method("POST")
        request.set_version("2015-05-01")
        request.set_action_name("ListGroupsForUser")
        request.add_query_param("UserName", user_name)

        response = client.do_action_with_exception(request)
        data = json.loads(response)

        if "Groups" in data and "Group" in data["Groups"]:
            groups = data["Groups"]["Group"]
            if not isinstance(groups, list):
                groups = [groups]

            if groups:
                print(f"\n  👥 所属用户组:")
                for group in groups:
                    print(f"     • {group.get('GroupName', '')}")
    except Exception as e:
        pass


def main():
    if len(sys.argv) < 2:
        print("使用方法: python3 check_current_identity.py <租户名称>")
        print("示例: python3 check_current_identity.py cf")
        sys.exit(1)

    tenant_name = sys.argv[1]

    # 加载配置
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ 配置文件 config.json 不存在")
        sys.exit(1)

    # 获取租户配置
    tenants = config.get("tenants", {})
    if tenant_name not in tenants:
        print(f"❌ 未找到租户: {tenant_name}")
        sys.exit(1)

    tenant_config = tenants[tenant_name]
    access_key_id = tenant_config.get("access_key_id")
    access_key_secret = tenant_config.get("access_key_secret")

    if not access_key_id or not access_key_secret:
        print(f"❌ 租户 {tenant_name} 的AK/SK未配置")
        sys.exit(1)

    # 尝试从Keyring获取凭证
    try:
        from utils.credential_manager import get_credentials_from_config_or_keyring

        cloud_credentials = get_credentials_from_config_or_keyring("aliyun", tenant_name, config)
        if cloud_credentials:
            access_key_id = cloud_credentials.get("access_key_id", access_key_id)
            access_key_secret = cloud_credentials.get("access_key_secret", access_key_secret)
    except:
        pass

    check_current_identity(access_key_id, access_key_secret)

    print("\n" + "=" * 80)
    print("💡 总结:")
    print("=" * 80)
    print("能够查看其他用户权限的原因可能是：")
    print("  1. 使用的是主账号的AccessKey（主账号默认拥有所有权限）")
    print("  2. RAM用户被授予了以下权限之一：")
    print("     • AdministratorAccess（管理员权限）")
    print("     • AliyunRAMFullAccess（RAM完全访问权限）")
    print("     • AliyunRAMReadOnlyAccess（RAM只读权限）")
    print("     • 包含RAM相关操作的自定义策略")
    print("=" * 80)


if __name__ == "__main__":
    main()
