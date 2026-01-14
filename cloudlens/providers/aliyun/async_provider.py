import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from datetime import datetime

from cloudlens.core.async_provider import AsyncProvider
from cloudlens.providers.aliyun.provider import AliyunProvider

logger = logging.getLogger(__name__)

class AsyncAliyunProvider(AliyunProvider, AsyncProvider):
    """
    阿里云异步Provider实现
    
    使用 asyncio + ThreadPoolExecutor 包装同步SDK调用。
    虽然底层仍是同步IO，但通过线程池避免了阻塞主事件循环，
    允许同时处理多个账号/区域的请求。
    """
    
    def __init__(self, account_name: str, access_key: str, secret_key: str, region: str, max_workers: int = 10):
        super().__init__(account_name, access_key, secret_key, region)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
    async def list_instances_async(self) -> List[Any]:
        """异步获取实例列表"""
        loop = asyncio.get_running_loop()
        # 将同步的 list_instances 放入线程池执行
        return await loop.run_in_executor(
            self.executor, 
            self.list_instances
        )
        
    async def get_metrics_async(
        self, 
        resource_id: str, 
        metric_name: str, 
        start_time: int, 
        end_time: int
    ) -> List[Dict]:
        """
        异步获取监控指标
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.executor,
            lambda: self.get_metric(resource_id, metric_name, start_time, end_time)
        )
        
    async def list_resources_parallel(self, resource_types: List[str]) -> Dict[str, List[Any]]:
        """
        并行获取多种资源
        
        示例: 同时获取 ECS, RDS, Redis
        """
        loop = asyncio.get_running_loop()
        tasks = {}
        
        if "ecs" in resource_types:
            tasks["ecs"] = loop.run_in_executor(self.executor, self.list_instances)
        if "rds" in resource_types:
            tasks["rds"] = loop.run_in_executor(self.executor, self.list_rds)
        if "redis" in resource_types:
            tasks["redis"] = loop.run_in_executor(self.executor, self.list_redis)
        if "slb" in resource_types:
            tasks["slb"] = loop.run_in_executor(self.executor, self.list_slb)
            
        results = {}
        # 等待所有任务完成
        for r_type, future in tasks.items():
            try:
                results[r_type] = await future
            except Exception as e:
                logger.error(f"Async fetch failed for {r_type}: {e}")
                results[r_type] = []
                
        return results
