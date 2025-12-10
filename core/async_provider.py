from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class AsyncProvider(ABC):
    """
    异步云服务提供商基类
    
    定义了资源查询和管理的异步标准接口。
    目的是利用AsyncIO提高大量API调用的并发性能。
    """
    
    @abstractmethod
    async def list_instances_async(self) -> List[Any]:
        """异步获取实例列表"""
        pass
        
    @abstractmethod
    async def get_metrics_async(
        self, 
        resource_id: str, 
        metric_name: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict]:
        """
        异步获取监控指标
        
        对于需要大量串行调用的监控数据获取场景,异步化能带来巨大提升。
        """
        pass
