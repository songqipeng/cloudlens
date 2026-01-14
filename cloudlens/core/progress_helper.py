# -*- coding: utf-8 -*-
"""
增强的并发查询助手（带进度条）
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

logger = logging.getLogger(__name__)


class ConcurrentQueryWithProgress:
    """带进度条的并发查询"""

    @staticmethod
    def query_accounts(
        accounts: List, query_func: Callable, description: str = "查询中..."
    ) -> List:
        """
        并发查询多个账号（带进度条）

        Args:
            accounts: 账号列表
            query_func: 查询函数
            description: 进度条描述

        Returns:
            所有账号的查询结果合并列表
        """
        all_results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        ) as progress:

            task = progress.add_task(description, total=len(accounts))

            with ThreadPoolExecutor(max_workers=min(len(accounts), 10)) as executor:
                future_to_account = {executor.submit(query_func, acc): acc for acc in accounts}

                for future in as_completed(future_to_account):
                    account = future_to_account[future]
                    try:
                        result = future.result()
                        if result:
                            all_results.extend(result if isinstance(result, list) else [result])
                    except Exception as e:
                        logger.error(f"Query failed for {account.name}: {e}")
                    finally:
                        progress.update(task, advance=1)

        return all_results

    @staticmethod
    def query_regions(
        provider, regions: List[str], query_func_name: str, description: str = "查询区域..."
    ) -> List:
        """
        并发查询多个区域

        Args:
            provider: Provider实例
            regions: 区域列表
            query_func_name: 要调用的方法名 (如 'list_instances')
            description: 进度条描述

        Returns:
            所有区域的查询结果
        """
        all_results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:

            task = progress.add_task(description, total=len(regions))

            with ThreadPoolExecutor(max_workers=min(len(regions), 5)) as executor:
                futures = {}

                for region in regions:
                    # 动态调用provider的方法
                    method = getattr(provider, query_func_name, None)
                    if method:
                        futures[executor.submit(method, region)] = region

                for future in as_completed(futures):
                    region = futures[future]
                    try:
                        result = future.result()
                        if result:
                            all_results.extend(result if isinstance(result, list) else [result])
                    except Exception as e:
                        logger.error(f"Query failed for region {region}: {e}")
                    finally:
                        progress.update(task, advance=1)

        return all_results
