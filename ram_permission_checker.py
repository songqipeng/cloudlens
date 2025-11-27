#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAM权限检查脚本
查看指定租户的RAM账户、用户、权限策略等信息
"""

import json
import sys
from datetime import datetime

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from utils.logger import get_logger


class RAMPermissionChecker:
    """RAM权限检查器"""

    def __init__(self, access_key_id, access_key_secret, tenant_name):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.tenant_name = tenant_name
        self.logger = get_logger("ram_checker")
        # RAM API使用全局endpoint，需要HTTPS
        self.client = AcsClient(access_key_id, access_key_secret, "cn-hangzhou")
        # 确保使用HTTPS
        import ssl

        ssl._create_default_https_context = ssl._create_unverified_context

    def get_users(self):
        """获取所有RAM用户"""
        try:
            request = CommonRequest()
            request.set_domain("ram.aliyuncs.com")
            request.set_protocol_type("https")  # 强制使用HTTPS
            request.set_method("POST")
            request.set_version("2015-05-01")
            request.set_action_name("ListUsers")

            response = self.client.do_action_with_exception(request)
            data = json.loads(response)

            users = []
            if "Users" in data and "User" in data["Users"]:
                user_list = data["Users"]["User"]
                if not isinstance(user_list, list):
                    user_list = [user_list]

                for user in user_list:
                    users.append(
                        {
                            "UserName": user.get("UserName", ""),
                            "UserId": user.get("UserId", ""),
                            "DisplayName": user.get("DisplayName", ""),
                            "CreateDate": user.get("CreateDate", ""),
                            "UpdateDate": user.get("UpdateDate", ""),
                            "Comments": user.get("Comments", ""),
                        }
                    )

            return users
        except Exception as e:
            self.logger.error(f"获取用户列表失败: {e}")
            return []

    def get_user_policies(self, user_name):
        """获取用户的权限策略"""
        policies = {"attached": [], "inline": []}

        # 获取附加的策略
        try:
            request = CommonRequest()
            request.set_domain("ram.aliyuncs.com")
            request.set_protocol_type("https")  # 强制使用HTTPS
            request.set_method("POST")
            request.set_version("2015-05-01")
            request.set_action_name("ListPoliciesForUser")
            request.add_query_param("UserName", user_name)

            response = self.client.do_action_with_exception(request)
            data = json.loads(response)

            if "Policies" in data and "Policy" in data["Policies"]:
                policy_list = data["Policies"]["Policy"]
                if not isinstance(policy_list, list):
                    policy_list = [policy_list]

                for policy in policy_list:
                    policies["attached"].append(
                        {
                            "PolicyName": policy.get("PolicyName", ""),
                            "PolicyType": policy.get("PolicyType", ""),
                            "Description": policy.get("Description", ""),
                            "DefaultVersion": policy.get("DefaultVersion", ""),
                            "AttachDate": policy.get("AttachDate", ""),
                        }
                    )
        except Exception as e:
            self.logger.warning(f"获取用户 {user_name} 附加策略失败: {e}")

        # 获取内联策略
        try:
            request = CommonRequest()
            request.set_domain("ram.aliyuncs.com")
            request.set_protocol_type("https")  # 强制使用HTTPS
            request.set_method("POST")
            request.set_version("2015-05-01")
            request.set_action_name("ListUserPolicies")
            request.add_query_param("UserName", user_name)

            response = self.client.do_action_with_exception(request)
            data = json.loads(response)

            if "Policies" in data and "Policy" in data["Policies"]:
                policy_list = data["Policies"]["Policy"]
                if not isinstance(policy_list, list):
                    policy_list = [policy_list] if policy_list else []

                for policy in policy_list:
                    policies["inline"].append(
                        {
                            "PolicyName": policy.get("PolicyName", ""),
                            "CreateDate": policy.get("CreateDate", ""),
                            "UpdateDate": policy.get("UpdateDate", ""),
                        }
                    )
        except Exception as e:
            self.logger.warning(f"获取用户 {user_name} 内联策略失败: {e}")

        return policies

    def get_policy_version(self, policy_name, policy_type="System"):
        """获取策略版本内容"""
        try:
            request = CommonRequest()
            request.set_domain("ram.aliyuncs.com")
            request.set_protocol_type("https")  # 强制使用HTTPS
            request.set_method("POST")
            request.set_version("2015-05-01")
            request.set_action_name("GetPolicyVersion")
            request.add_query_param("PolicyName", policy_name)
            request.add_query_param("PolicyType", policy_type)
            request.add_query_param("VersionId", "v1")  # 获取默认版本

            response = self.client.do_action_with_exception(request)
            data = json.loads(response)

            if "PolicyVersion" in data:
                policy_version = data["PolicyVersion"]
                policy_document = policy_version.get("PolicyDocument", "")
                if isinstance(policy_document, str):
                    try:
                        policy_document = json.loads(policy_document)
                    except:
                        pass
                return {
                    "VersionId": policy_version.get("VersionId", ""),
                    "IsDefaultVersion": policy_version.get("IsDefaultVersion", False),
                    "CreateDate": policy_version.get("CreateDate", ""),
                    "PolicyDocument": policy_document,
                }
        except Exception as e:
            self.logger.warning(f"获取策略 {policy_name} 版本失败: {e}")

        return None

    def get_user_groups(self, user_name):
        """获取用户所属的用户组"""
        try:
            request = CommonRequest()
            request.set_domain("ram.aliyuncs.com")
            request.set_protocol_type("https")  # 强制使用HTTPS
            request.set_method("POST")
            request.set_version("2015-05-01")
            request.set_action_name("ListGroupsForUser")
            request.add_query_param("UserName", user_name)

            response = self.client.do_action_with_exception(request)
            data = json.loads(response)

            groups = []
            if "Groups" in data and "Group" in data["Groups"]:
                group_list = data["Groups"]["Group"]
                if not isinstance(group_list, list):
                    group_list = [group_list]

                for group in group_list:
                    groups.append(
                        {
                            "GroupName": group.get("GroupName", ""),
                            "Comments": group.get("Comments", ""),
                            "JoinDate": group.get("JoinDate", ""),
                        }
                    )

            return groups
        except Exception as e:
            self.logger.warning(f"获取用户 {user_name} 的用户组失败: {e}")
            return []

    def get_groups(self):
        """获取所有用户组"""
        try:
            request = CommonRequest()
            request.set_domain("ram.aliyuncs.com")
            request.set_protocol_type("https")  # 强制使用HTTPS
            request.set_method("POST")
            request.set_version("2015-05-01")
            request.set_action_name("ListGroups")

            response = self.client.do_action_with_exception(request)
            data = json.loads(response)

            groups = []
            if "Groups" in data and "Group" in data["Groups"]:
                group_list = data["Groups"]["Group"]
                if not isinstance(group_list, list):
                    group_list = [group_list]

                for group in group_list:
                    groups.append(
                        {
                            "GroupName": group.get("GroupName", ""),
                            "Comments": group.get("Comments", ""),
                            "CreateDate": group.get("CreateDate", ""),
                            "UpdateDate": group.get("UpdateDate", ""),
                        }
                    )

            return groups
        except Exception as e:
            self.logger.error(f"获取用户组列表失败: {e}")
            return []

    def get_group_policies(self, group_name):
        """获取用户组的权限策略"""
        try:
            request = CommonRequest()
            request.set_domain("ram.aliyuncs.com")
            request.set_protocol_type("https")  # 强制使用HTTPS
            request.set_method("POST")
            request.set_version("2015-05-01")
            request.set_action_name("ListPoliciesForGroup")
            request.add_query_param("GroupName", group_name)

            response = self.client.do_action_with_exception(request)
            data = json.loads(response)

            policies = []
            if "Policies" in data and "Policy" in data["Policies"]:
                policy_list = data["Policies"]["Policy"]
                if not isinstance(policy_list, list):
                    policy_list = [policy_list]

                for policy in policy_list:
                    policies.append(
                        {
                            "PolicyName": policy.get("PolicyName", ""),
                            "PolicyType": policy.get("PolicyType", ""),
                            "Description": policy.get("Description", ""),
                            "AttachDate": policy.get("AttachDate", ""),
                        }
                    )

            return policies
        except Exception as e:
            self.logger.warning(f"获取用户组 {group_name} 策略失败: {e}")
            return []

    def get_roles(self):
        """获取所有角色"""
        try:
            request = CommonRequest()
            request.set_domain("ram.aliyuncs.com")
            request.set_protocol_type("https")  # 强制使用HTTPS
            request.set_method("POST")
            request.set_version("2015-05-01")
            request.set_action_name("ListRoles")

            response = self.client.do_action_with_exception(request)
            data = json.loads(response)

            roles = []
            if "Roles" in data and "Role" in data["Roles"]:
                role_list = data["Roles"]["Role"]
                if not isinstance(role_list, list):
                    role_list = [role_list]

                for role in role_list:
                    roles.append(
                        {
                            "RoleName": role.get("RoleName", ""),
                            "RoleId": role.get("RoleId", ""),
                            "Arn": role.get("Arn", ""),
                            "Description": role.get("Description", ""),
                            "CreateDate": role.get("CreateDate", ""),
                            "UpdateDate": role.get("UpdateDate", ""),
                        }
                    )

            return roles
        except Exception as e:
            self.logger.error(f"获取角色列表失败: {e}")
            return []

    def get_account_summary(self):
        """获取账户摘要信息"""
        try:
            request = CommonRequest()
            request.set_domain("ram.aliyuncs.com")
            request.set_protocol_type("https")  # 强制使用HTTPS
            request.set_method("POST")
            request.set_version("2015-05-01")
            request.set_action_name("GetAccountSummary")

            response = self.client.do_action_with_exception(request)
            data = json.loads(response)

            if "SummaryMap" in data:
                return data["SummaryMap"]
            return {}
        except Exception as e:
            self.logger.warning(f"获取账户摘要失败: {e}")
            return {}

    def generate_permission_report(self):
        """生成权限报告"""
        print(f"\n🔐 开始检查 {self.tenant_name} 租户的RAM权限...")
        print("=" * 80)

        # 获取账户摘要
        summary = self.get_account_summary()
        if summary:
            print("\n📊 账户摘要:")
            print("-" * 80)
            users_quota = summary.get("Users", {})
            if isinstance(users_quota, dict):
                print(f"  RAM用户数: {users_quota.get('Quota', 0)}")
            else:
                print(f"  RAM用户数: {users_quota}")

            groups_quota = summary.get("Groups", {})
            if isinstance(groups_quota, dict):
                print(f"  用户组数: {groups_quota.get('Quota', 0)}")
            else:
                print(f"  用户组数: {groups_quota}")

            roles_quota = summary.get("Roles", {})
            if isinstance(roles_quota, dict):
                print(f"  角色数: {roles_quota.get('Quota', 0)}")
            else:
                print(f"  角色数: {roles_quota}")

            policies_quota = summary.get("Policies", {})
            if isinstance(policies_quota, dict):
                print(f"  策略数: {policies_quota.get('Quota', 0)}")
            else:
                print(f"  策略数: {policies_quota}")

        # 获取所有用户
        print("\n👥 RAM用户列表:")
        print("-" * 80)
        users = self.get_users()

        if not users:
            print("  ❌ 未找到RAM用户")
        else:
            print(f"  共找到 {len(users)} 个用户:\n")

            for i, user in enumerate(users, 1):
                user_name = user.get("UserName", "")
                print(f"  {i}. {user_name}")
                print(f"     用户ID: {user.get('UserId', '')}")
                print(f"     显示名称: {user.get('DisplayName', '')}")
                print(f"     创建时间: {user.get('CreateDate', '')}")
                if user.get("Comments"):
                    print(f"     备注: {user.get('Comments', '')}")

                # 获取用户权限
                policies = self.get_user_policies(user_name)
                groups = self.get_user_groups(user_name)

                if policies["attached"] or policies["inline"]:
                    print(f"     权限策略:")
                    for policy in policies["attached"]:
                        policy_type = policy.get("PolicyType", "")
                        policy_name = policy.get("PolicyName", "")
                        print(f"       • {policy_name} ({policy_type})")
                    for policy in policies["inline"]:
                        print(f"       • {policy.get('PolicyName', '')} (内联策略)")

                if groups:
                    print(f"     所属用户组:")
                    for group in groups:
                        print(f"       • {group.get('GroupName', '')}")

                print()

        # 获取所有用户组
        print("\n👥 用户组列表:")
        print("-" * 80)
        groups = self.get_groups()

        if not groups:
            print("  ❌ 未找到用户组")
        else:
            print(f"  共找到 {len(groups)} 个用户组:\n")

            for i, group in enumerate(groups, 1):
                group_name = group.get("GroupName", "")
                print(f"  {i}. {group_name}")
                print(f"     创建时间: {group.get('CreateDate', '')}")
                if group.get("Comments"):
                    print(f"     备注: {group.get('Comments', '')}")

                # 获取用户组权限
                policies = self.get_group_policies(group_name)
                if policies:
                    print(f"     权限策略:")
                    for policy in policies:
                        policy_type = policy.get("PolicyType", "")
                        policy_name = policy.get("PolicyName", "")
                        print(f"       • {policy_name} ({policy_type})")

                print()

        # 获取所有角色
        print("\n🎭 角色列表:")
        print("-" * 80)
        roles = self.get_roles()

        if not roles:
            print("  ❌ 未找到角色")
        else:
            print(f"  共找到 {len(roles)} 个角色:\n")

            for i, role in enumerate(roles, 1):
                print(f"  {i}. {role.get('RoleName', '')}")
                print(f"     角色ID: {role.get('RoleId', '')}")
                print(f"     ARN: {role.get('Arn', '')}")
                if role.get("Description"):
                    print(f"     描述: {role.get('Description', '')}")
                print(f"     创建时间: {role.get('CreateDate', '')}")
                print()

        # 生成详细报告文件
        self.save_detailed_report(users, groups, roles)

        print("=" * 80)
        print(f"✅ 权限检查完成！详细报告已保存")
        print("=" * 80)

    def save_detailed_report(self, users, groups, roles):
        """保存详细报告到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{self.tenant_name}_ram_permissions_{timestamp}.json"

        report_data = {
            "tenant_name": self.tenant_name,
            "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": self.get_account_summary(),
            "users": [],
            "groups": [],
            "roles": roles,
        }

        # 获取用户详细信息
        for user in users:
            user_name = user.get("UserName", "")
            user_detail = {
                **user,
                "policies": self.get_user_policies(user_name),
                "groups": self.get_user_groups(user_name),
            }
            report_data["users"].append(user_detail)

        # 获取用户组详细信息
        for group in groups:
            group_name = group.get("GroupName", "")
            group_detail = {**group, "policies": self.get_group_policies(group_name)}
            report_data["groups"].append(group_detail)

        # 保存JSON报告
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存: {report_file}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python3 ram_permission_checker.py <租户名称>")
        print("示例: python3 ram_permission_checker.py cf")
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
        print(f"可用租户: {', '.join(tenants.keys())}")
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

    # 创建权限检查器
    checker = RAMPermissionChecker(access_key_id, access_key_secret, tenant_name)
    checker.generate_permission_report()


if __name__ == "__main__":
    main()
