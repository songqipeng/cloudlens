"""
成本分析Service
"""
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from core.config import ConfigManager, CloudAccount
from core.cache import CacheManager
from core.database import DatabaseFactory
from web.backend.repositories.bill_repository import BillRepository
from .base_service import BaseService
import logging

logger = logging.getLogger(__name__)


class CostService(BaseService):
    """成本分析服务"""
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.cache_manager = CacheManager()
        self.bill_repository = BillRepository()
    
    def get_billing_overview(
        self,
        account: Optional[str] = None,
        billing_cycle: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """获取账单概览"""
        try:
            # 获取账号配置
            account_config = self._get_account_config(account)
            
            if billing_cycle is None:
                billing_cycle = datetime.now().strftime("%Y-%m")
            
            # 尝试从数据库获取
            if not force_refresh:
                overview = self.bill_repository.get_billing_overview(
                    account_config, billing_cycle
                )
                if overview:
                    return overview
            
            # 如果数据库没有，从API查询（这里简化，实际应该调用API）
            # TODO: 实现API查询逻辑
            return {
                "billing_cycle": billing_cycle,
                "total_pretax": 0.0,
                "by_product": {},
                "by_product_name": {},
                "by_product_subscription": {},
                "data_source": "api"
            }
        except Exception as e:
            self.handle_error(e, "get_billing_overview")
    
    def get_cost_breakdown(
        self,
        account: Optional[str] = None,
        billing_cycle: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取成本分解"""
        try:
            account_config = self._get_account_config(account)
            
            if billing_cycle is None:
                billing_cycle = datetime.now().strftime("%Y-%m")
            
            # TODO: 实现成本分解逻辑
            return {
                "billing_cycle": billing_cycle,
                "breakdown": {}
            }
        except Exception as e:
            self.handle_error(e, "get_cost_breakdown")
    
    def _get_account_config(self, account: Optional[str] = None) -> CloudAccount:
        """获取账号配置"""
        if not account:
            from core.context import ContextManager
            ctx = ContextManager()
            account = ctx.get_last_account()
        
        if not account:
            accounts = self.config_manager.list_accounts()
            if accounts:
                account = accounts[0].name
            else:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="No accounts configured")
        
        account_config = self.config_manager.get_account(account)
        if not account_config:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Account '{account}' not found")
        
        return account_config
