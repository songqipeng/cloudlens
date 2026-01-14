#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并发处理工具
使用线程池实现并发处理，大幅提升性能
"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, List, Optional


def process_concurrently(
    items: List[Any],
    process_func: Callable,
    max_workers: int = 10,
    description: str = "Processing",
    progress_callback: Optional[Callable] = None,
) -> List[Any]:
    """
    并发处理列表项

    Args:
        items: 待处理的项目列表
        process_func: 处理函数，接收单个item作为参数，返回处理结果
        max_workers: 最大并发数（默认10，避免API限流）
        description: 描述（用于日志）
        progress_callback: 进度回调函数，接收(completed, total)参数

    Returns:
        处理结果列表（顺序与输入顺序一致）
    """
    results = []
    total = len(items)

    if total == 0:
        return results

    # 创建结果字典，保持顺序
    results_dict = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_index = {
            executor.submit(process_func, item): idx for idx, item in enumerate(items)
        }

        # 收集结果
        completed = 0
        for future in as_completed(future_to_index):
            completed += 1
            idx = future_to_index[future]

            try:
                result = future.result()
                results_dict[idx] = result

                # 调用进度回调
                if progress_callback:
                    progress_callback(completed, total)
                else:
                    # 默认进度输出
                    progress_pct = completed / total * 100
                    sys.stdout.write(f"\r{description}: {completed}/{total} ({progress_pct:.1f}%)")
                    sys.stdout.flush()
            except Exception as e:
                # 记录错误但继续处理
                print(f"\n❌ {description} 处理失败 [{idx}]: {e}")
                results_dict[idx] = None

    # 按原始顺序整理结果
    results = [results_dict.get(i) for i in range(total)]

    if not progress_callback:
        sys.stdout.write("\n")  # 换行
        sys.stdout.flush()

    return results
