"""
账号管理Service
"""
from typing import List, Dict, Optional, Any
from cloudlens.core.config import ConfigManager, CloudAccount
from cloudlens.core.rules_manager import RulesManager
from .base_service import BaseService
import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class AccountService(BaseService):
    """账号管理服务"""
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.rules_manager = RulesManager()
    
    def list_accounts(self) -> List[Dict[str, Any]]:
        """列出所有账号"""
        try:
            accounts = self.config_manager.list_accounts()
            result = []
            for account in accounts:
                if isinstance(account, CloudAccount):
                    result.append({
                        "name": account.name,
                        "region": account.region,
                        "access_key_id": account.access_key_id,
                    })
            return result
        except Exception as e:
            self.handle_error(e, "list_accounts")
    
    def list_accounts_for_settings(self) -> Dict[str, Any]:
        """获取账号列表（用于设置页面）"""
        try:
            accounts = self.config_manager.list_accounts()
            result = []
            for account in accounts:
                if isinstance(account, CloudAccount):
                    result.append({
                        "name": account.name,
                        "alias": getattr(account, 'alias', None),
                        "region": account.region,
                        "provider": account.provider,
                        "access_key_id": account.access_key_id,
                    })
            return {"success": True, "data": result}
        except Exception as e:
            self.handle_error(e, "list_accounts_for_settings")
    
    def add_account(
        self,
        name: str,
        provider: str,
        access_key_id: str,
        access_key_secret: str,
        region: str,
        alias: Optional[str] = None
    ) -> Dict[str, Any]:
        """添加账号"""
        try:
            self.config_manager.add_account(
                name=name,
                provider=provider,
                access_key_id=access_key_id,
                access_key_secret=access_key_secret,
                region=region,
                alias=alias,
            )
            return {"success": True, "message": "账号添加成功"}
        except Exception as e:
            self.handle_error(e, "add_account")
    
    def update_account(
        self,
        account_name: str,
        alias: Optional[str] = None,
        provider: Optional[str] = None,
        access_key_id: Optional[str] = None,
        access_key_secret: Optional[str] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """更新账号"""
        import keyring
        
        try:
            # 检查账号是否存在
            existing_account = self.config_manager.get_account(account_name)
            if not existing_account:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail=f"账号 '{account_name}' 不存在")
            
            # 获取新密钥，如果没有提供则使用现有密钥
            new_secret = access_key_secret
            if not new_secret:
                try:
                    existing_secret = keyring.get_password(
                        "cloudlens",
                        f"{account_name}_access_key_secret"
                    )
                    if existing_secret:
                        new_secret = existing_secret
                    else:
                        from fastapi import HTTPException
                        raise HTTPException(
                            status_code=400,
                            detail="无法获取现有密钥，请提供新密钥"
                        )
                except Exception:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=400,
                        detail="无法获取现有密钥，请提供新密钥"
                    )
            
            # 更新账号配置
            self.config_manager.add_account(
                name=account_name,
                provider=provider or existing_account.provider,
                access_key_id=access_key_id or existing_account.access_key_id,
                access_key_secret=new_secret,
                region=region or existing_account.region,
                alias=alias.strip() if alias else None,
            )
            
            return {"success": True, "message": "账号更新成功"}
        except Exception as e:
            self.handle_error(e, "update_account")
    
    def delete_account(self, account_name: str) -> Dict[str, Any]:
        """删除账号"""
        try:
            self.config_manager.remove_account(account_name)
            return {"success": True, "message": "账号删除成功"}
        except Exception as e:
            self.handle_error(e, "delete_account")
    
    def get_rules(self) -> Dict[str, Any]:
        """获取优化规则"""
        try:
            return self.rules_manager.get_rules()
        except Exception as e:
            self.handle_error(e, "get_rules")
    
    def set_rules(self, rules: Dict[str, Any]) -> Dict[str, Any]:
        """更新优化规则"""
        try:
            self.rules_manager.set_rules(rules)
            return {"status": "success", "message": "规则已更新"}
        except Exception as e:
            self.handle_error(e, "set_rules")
    
    def get_notification_config(self) -> Dict[str, Any]:
        """获取通知配置"""
        try:
            config_dir = Path(os.path.expanduser("~/.cloudlens"))
            config_file = config_dir / "notifications.json"
            
            default_config = {
                "email": "",
                "auth_code": "",
                "default_receiver_email": "",
                "smtp_host": "",
                "smtp_port": 587,
                "smtp_user": "",
                "smtp_password": "",
                "smtp_from": ""
            }
            
            if not config_file.exists():
                return default_config
            
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                result = {**default_config, **config}
                
                # 转换旧格式配置
                if result.get("smtp_user") and not result.get("email"):
                    result["email"] = result.get("smtp_user", "")
                if result.get("smtp_password") and not result.get("auth_code"):
                    result["auth_code"] = result.get("smtp_password", "")
                
                return result
        except Exception as e:
            logger.error(f"读取通知配置失败: {e}")
            return default_config
    
    def set_notification_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """保存通知配置"""
        try:
            config_dir = Path(os.path.expanduser("~/.cloudlens"))
            config_file = config_dir / "notifications.json"
            
            if not config_dir.exists():
                config_dir.mkdir(parents=True, exist_ok=True)
            
            # 获取用户输入
            email = config.get("email", "").strip()
            auth_code = config.get("auth_code", "").strip()
            default_receiver_email = config.get("default_receiver_email", "").strip()
            
            # 根据邮箱自动配置SMTP
            smtp_config = self._get_smtp_config_by_email(email)
            if email:
                smtp_config["smtp_user"] = email
                smtp_config["smtp_from"] = email
                smtp_config["smtp_password"] = auth_code
            
            # 保存完整配置
            full_config = {
                "email": email,
                "auth_code": auth_code,
                "default_receiver_email": default_receiver_email,
                **smtp_config
            }
            
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(full_config, f, indent=2, ensure_ascii=False)
            
            return {"status": "success", "message": "通知配置已更新"}
        except Exception as e:
            logger.error(f"保存通知配置失败: {e}")
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail=f"保存通知配置失败: {str(e)}"
            )
    
    def _get_smtp_config_by_email(self, email: str) -> Dict[str, Any]:
        """根据邮箱地址自动获取SMTP配置"""
        email_lower = email.lower().strip() if email else ""
        
        # QQ邮箱
        if email_lower.endswith("@qq.com"):
            return {
                "smtp_host": "smtp.qq.com",
                "smtp_port": 587,
                "smtp_use_tls": True
            }
        # Gmail
        elif email_lower.endswith("@gmail.com"):
            return {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_use_tls": True
            }
        # 163邮箱
        elif email_lower.endswith("@163.com"):
            return {
                "smtp_host": "smtp.163.com",
                "smtp_port": 465,
                "smtp_use_tls": False,
                "smtp_use_ssl": True
            }
        # 126邮箱
        elif email_lower.endswith("@126.com"):
            return {
                "smtp_host": "smtp.126.com",
                "smtp_port": 465,
                "smtp_use_tls": False,
                "smtp_use_ssl": True
            }
        # 默认配置
        else:
            return {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_use_tls": True
            }
