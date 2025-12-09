"""
异步Provider基类
支持异步I/O操作,提升查询性能
"""
from abc import ABC, abstractmethod
from typing import List, Dict
import asyncio


class AsyncBaseProvider(ABC):
    """异步云厂商Provider基类"""

    def __init__(self, account_name: str, access_key: str, secret_key: str, region: str):
        self.account_name = account_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """返回厂商名称"""
        pass

    @abstractmethod
    async def list_instances(self) -> List:
        """异步列出ECS实例"""
        pass

    @abstractmethod
    async def list_rds(self) -> List:
        """异步列出RDS实例"""
        pass

    @abstractmethod
    async def list_redis(self) -> List:
        """异步列出Redis实例"""
        pass

    @abstractmethod
    async def get_metric(
        self, resource_id: str, metric_name: str, start_time: int, end_time: int
    ) -> List[Dict]:
        """异步获取监控指标"""
        pass

    async def close(self):
        """清理资源"""
        pass

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()


class AsyncProviderFactory:
    """异步Provider工厂"""

    _providers = {}

    @classmethod
    def register(cls, provider_name: str, provider_class):
        """注册Provider"""
        cls._providers[provider_name] = provider_class

    @classmethod
    def create(cls, provider_name: str, **kwargs) -> AsyncBaseProvider:
        """创建Provider实例"""
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")
        return provider_class(**kwargs)

    @classmethod
    async def create_all(cls, accounts: List) -> List[AsyncBaseProvider]:
        """批量创建Provider"""
        providers = []
        for account in accounts:
            provider = cls.create(
                provider_name=account.provider,
                account_name=account.name,
                access_key=account.access_key,
                secret_key=account.secret_key,
                region=account.region,
            )
            providers.append(provider)
        return providers
