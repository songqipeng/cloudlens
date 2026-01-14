"""
API重构后的单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from web.backend.services.account_service import AccountService
from web.backend.repositories.bill_repository import BillRepository


class TestAccountService:
    """AccountService测试"""
    
    def test_list_accounts(self):
        """测试列出账号"""
        service = AccountService()
        
        with patch.object(service.config_manager, 'list_accounts') as mock_list:
            from cloudlens.core.config import CloudAccount
            mock_account = CloudAccount(
                name="test-account",
                provider="aliyun",
                access_key_id="test-key",
                access_key_secret="test-secret",
                region="cn-hangzhou"
            )
            mock_list.return_value = [mock_account]
            
            result = service.list_accounts()
            
            assert len(result) == 1
            assert result[0]["name"] == "test-account"
            assert result[0]["region"] == "cn-hangzhou"
    
    def test_get_rules(self):
        """测试获取规则"""
        service = AccountService()
        
        with patch.object(service.rules_manager, 'get_rules') as mock_get:
            mock_get.return_value = {"rule1": "value1"}
            
            result = service.get_rules()
            
            assert result == {"rule1": "value1"}


class TestBillRepository:
    """BillRepository测试"""
    
    def test_get_billing_overview_no_data(self):
        """测试获取账单概览（无数据）"""
        repo = BillRepository()
        
        with patch.object(repo.db, 'query_one') as mock_query:
            mock_query.return_value = None
            
            from cloudlens.core.config import CloudAccount
            account = CloudAccount(
                name="test",
                provider="aliyun",
                access_key_id="test-key",
                access_key_secret="test-secret",
                region="cn-hangzhou"
            )
            
            result = repo.get_billing_overview(account, "2026-01")
            
            assert result is None
