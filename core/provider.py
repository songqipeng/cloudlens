from abc import ABC, abstractmethod
from typing import List, Dict, Any
from models.resource import UnifiedResource, ResourceType

class BaseProvider(ABC):
    """
    云厂商适配器基类
    所有具体的云厂商实现(AliyunProvider, TencentProvider等)都必须继承此类
    """
    
    def __init__(self, account_name: str, access_key: str, secret_key: str, region: str):
        self.account_name = account_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self._client = None

    @property
    def provider_name(self) -> str:
        """返回厂商名称 (aliyun, tencent, aws, volcano)"""
        raise NotImplementedError

    @abstractmethod
    def list_instances(self) -> List[UnifiedResource]:
        """列出计算实例 (ECS/EC2/CVM)"""
        pass

    @abstractmethod
    def list_rds(self) -> List[UnifiedResource]:
        """列出关系型数据库实例"""
        pass
        
    @abstractmethod
    def list_vpcs(self) -> List[Dict]:
        """列出VPC及网络拓扑信息"""
        pass

    @abstractmethod
    def get_metric(self, resource_id: str, metric_name: str, start_time: int, end_time: int) -> List[Dict]:
        """获取监控指标数据"""
        pass
    
    @abstractmethod
    def check_permissions(self) -> List[str]:
        """
        权限自检
        返回当前凭证拥有的关键权限列表，或检测到的高危权限警告
        """
        pass
