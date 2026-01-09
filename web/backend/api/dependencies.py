"""
API依赖注入
"""
from typing import Optional
from fastapi import Depends, HTTPException
from core.config import ConfigManager, CloudAccount
from core.context import ContextManager


def get_config_manager() -> ConfigManager:
    """获取配置管理器"""
    return ConfigManager()


def get_account(account_name: Optional[str] = None) -> CloudAccount:
    """获取账号配置"""
    cm = ConfigManager()
    
    if not account_name:
        ctx = ContextManager()
        account_name = ctx.get_last_account()
    
    if not account_name:
        accounts = cm.list_accounts()
        if accounts:
            account_name = accounts[0].name
        else:
            raise HTTPException(status_code=404, detail="No accounts configured")
    
    account_config = cm.get_account(account_name)
    if not account_config:
        raise HTTPException(status_code=404, detail=f"Account '{account_name}' not found")
    
    return account_config


def get_provider_for_account(account_name: Optional[str] = None):
    """获取云服务提供商实例"""
    account_config = get_account(account_name)
    from cli.utils import get_provider
    return get_provider(account_config), account_config.name
