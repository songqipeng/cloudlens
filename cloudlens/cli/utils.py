# -*- coding: utf-8 -*-
"""
CLI工具函数
"""
from cloudlens.core.config import CloudAccount


def get_provider(account_config: CloudAccount):
    """获取Provider实例"""
    if account_config.provider == "aliyun":
        from cloudlens.providers.aliyun.provider import AliyunProvider

        return AliyunProvider(
            account_config.name,
            account_config.access_key_id,
            account_config.access_key_secret,
            account_config.region,
        )
    elif account_config.provider == "tencent":
        from cloudlens.providers.tencent.provider import TencentProvider

        return TencentProvider(
            account_config.name,
            account_config.access_key_id,
            account_config.access_key_secret,
            account_config.region,
        )
    else:
        raise ValueError(
            f"不支持的云厂商: {account_config.provider}。\n"
            f"当前支持的厂商: aliyun (阿里云), tencent (腾讯云)\n"
            f"AWS和火山引擎支持正在开发中。"
        )


def smart_resolve_account(cm, ctx_mgr, account_name=None):
    """智能解析账号名称"""
    if account_name:
        account = cm.get_account(account_name)
        if account:
            ctx_mgr.set_current_account(account_name)
            return account
        else:
            raise ValueError(f"账号 '{account_name}' 不存在")

    # 尝试从上下文获取
    current = ctx_mgr.get_current_account()
    if current:
        return cm.get_account(current)

    # 获取第一个账号
    accounts = cm.list_accounts()
    if accounts:
        return accounts[0]

    raise ValueError("未找到可用账号，请先使用 'cl config add' 添加账号")
