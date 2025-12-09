"""
Concurrent Query Helper
使用asyncio实现并发查询
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, List

logger = logging.getLogger("ConcurrentHelper")


class ConcurrentQueryHelper:
    """并发查询助手"""

    @staticmethod
    async def query_accounts_async(accounts: List, query_func: Callable, *args, **kwargs) -> List:
        """
        并发查询多个账号

        Args:
            accounts: 账号列表
            query_func: 查询函数
            *args, **kwargs: 传递给查询函数的参数

        Returns:
            所有账号的查询结果合并列表
        """
        loop = asyncio.get_event_loop()

        # 使用线程池执行同步的SDK调用
        with ThreadPoolExecutor(max_workers=min(len(accounts), 10)) as executor:
            tasks = []
            for account in accounts:
                task = loop.run_in_executor(executor, query_func, account, *args)
                tasks.append(task)

            # 并发执行所有任务
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果，过滤异常
        all_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Query failed for account {accounts[i].name}: {result}")
            elif result:
                all_results.extend(result if isinstance(result, list) else [result])

        return all_results

    @staticmethod
    def query_accounts_concurrent(accounts: List, query_func: Callable, *args, **kwargs) -> List:
        """
        并发查询多个账号（同步包装）

        这是query_accounts_async的同步版本，用于在非async上下文中调用
        """
        try:
            # 尝试获取现有事件循环
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在运行中的循环里，创建新循环
                import nest_asyncio

                nest_asyncio.apply()
        except RuntimeError:
            # 没有事件循环，创建新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 运行异步查询
        return loop.run_until_complete(
            ConcurrentQueryHelper.query_accounts_async(accounts, query_func, *args, **kwargs)
        )

    @staticmethod
    def query_with_progress(
        accounts: List, query_func: Callable, progress_callback: Callable = None
    ) -> List:
        """
        带进度回调的并发查询

        Args:
            accounts: 账号列表
            query_func: 查询函数
            progress_callback: 进度回调函数 (completed, total)

        Returns:
            查询结果列表
        """
        all_results = []
        total = len(accounts)
        completed = 0

        # 使用线程池并发查询
        with ThreadPoolExecutor(max_workers=min(total, 10)) as executor:
            futures = {executor.submit(query_func, acc): acc for acc in accounts}

            for future in futures:
                try:
                    result = future.result()
                    if result:
                        all_results.extend(result if isinstance(result, list) else [result])
                except Exception as e:
                    acc = futures[future]
                    logger.error(f"Query failed for {acc.name}: {e}")
                finally:
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total)

        return all_results
