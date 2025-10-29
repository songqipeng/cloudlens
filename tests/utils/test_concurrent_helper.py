#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
concurrent_helper 单元测试
"""

import pytest
import time
from utils.concurrent_helper import process_concurrently


class TestConcurrentHelper:
    """并发处理工具测试类"""

    def test_process_empty_list(self):
        """测试处理空列表"""
        def dummy_func(item):
            return item * 2

        results = process_concurrently([], dummy_func)
        assert results == []

    def test_process_single_item(self):
        """测试处理单个项目"""
        def double(item):
            return item * 2

        results = process_concurrently([5], double)
        assert results == [10]

    def test_process_multiple_items(self):
        """测试处理多个项目"""
        def square(item):
            return item ** 2

        items = [1, 2, 3, 4, 5]
        results = process_concurrently(items, square)
        assert results == [1, 4, 9, 16, 25]

    def test_preserve_order(self):
        """测试结果顺序与输入一致"""
        def slow_process(item):
            # 让索引较大的项更快完成，测试顺序保持
            time.sleep(0.01 * (10 - item))
            return item * 2

        items = list(range(10))
        results = process_concurrently(items, slow_process, max_workers=5)
        expected = [i * 2 for i in items]
        assert results == expected

    def test_max_workers_parameter(self):
        """测试max_workers参数"""
        def count_concurrent(item):
            time.sleep(0.1)
            return item + 1

        # 测试不同的max_workers设置
        items = list(range(5))

        # max_workers=1 应该串行执行
        start = time.time()
        results = process_concurrently(items, count_concurrent, max_workers=1)
        duration_serial = time.time() - start

        # max_workers=5 应该并行执行
        start = time.time()
        results = process_concurrently(items, count_concurrent, max_workers=5)
        duration_parallel = time.time() - start

        # 并行应该明显更快（至少快40%）
        assert duration_parallel < duration_serial * 0.6

    def test_exception_handling(self):
        """测试异常处理"""
        def may_fail(item):
            if item == 3:
                raise ValueError("Intentional error")
            return item * 2

        items = [1, 2, 3, 4, 5]
        results = process_concurrently(items, may_fail)

        # 检查非错误项正常处理
        assert results[0] == 2
        assert results[1] == 4
        assert results[2] is None  # 错误项应该是None
        assert results[3] == 8
        assert results[4] == 10

    def test_multiple_exceptions(self):
        """测试多个异常"""
        def fail_on_even(item):
            if item % 2 == 0:
                raise ValueError(f"Item {item} is even")
            return item * 2

        items = [1, 2, 3, 4, 5]
        results = process_concurrently(items, fail_on_even)

        assert results[0] == 2   # 1 * 2
        assert results[1] is None  # 2 failed
        assert results[2] == 6   # 3 * 2
        assert results[3] is None  # 4 failed
        assert results[4] == 10  # 5 * 2

    def test_with_progress_callback(self):
        """测试进度回调"""
        progress_data = {'completed': 0, 'total': 0}

        def progress_callback(completed, total):
            progress_data['completed'] = completed
            progress_data['total'] = total

        def simple_func(item):
            return item + 1

        items = [1, 2, 3, 4, 5]
        results = process_concurrently(
            items,
            simple_func,
            progress_callback=progress_callback
        )

        # 验证进度回调被调用
        assert progress_data['completed'] == 5
        assert progress_data['total'] == 5
        assert results == [2, 3, 4, 5, 6]

    def test_with_complex_objects(self):
        """测试处理复杂对象"""
        def process_dict(item):
            return {
                'id': item['id'],
                'value': item['value'] * 2,
                'processed': True
            }

        items = [
            {'id': 1, 'value': 10},
            {'id': 2, 'value': 20},
            {'id': 3, 'value': 30}
        ]

        results = process_concurrently(items, process_dict)

        assert len(results) == 3
        assert results[0] == {'id': 1, 'value': 20, 'processed': True}
        assert results[1] == {'id': 2, 'value': 40, 'processed': True}
        assert results[2] == {'id': 3, 'value': 60, 'processed': True}

    def test_with_none_values(self):
        """测试处理None值"""
        def handle_none(item):
            if item is None:
                return 0
            return item * 2

        items = [1, None, 3, None, 5]
        results = process_concurrently(items, handle_none)
        assert results == [2, 0, 6, 0, 10]

    def test_performance_improvement(self):
        """测试性能提升"""
        def slow_task(item):
            time.sleep(0.05)  # 模拟耗时操作
            return item * 2

        items = list(range(10))

        # 串行执行
        start = time.time()
        results_serial = process_concurrently(items, slow_task, max_workers=1)
        time_serial = time.time() - start

        # 并行执行
        start = time.time()
        results_parallel = process_concurrently(items, slow_task, max_workers=5)
        time_parallel = time.time() - start

        # 结果应该相同
        assert results_serial == results_parallel

        # 并行应该至少快2倍
        assert time_parallel < time_serial * 0.6

    def test_large_dataset(self):
        """测试大数据集处理"""
        def simple_calc(item):
            return item ** 2 + item + 1

        items = list(range(100))
        results = process_concurrently(items, simple_calc, max_workers=10)

        expected = [i ** 2 + i + 1 for i in items]
        assert results == expected

    def test_return_types(self):
        """测试不同返回类型"""
        # 返回字符串
        def to_string(item):
            return f"item_{item}"

        results = process_concurrently([1, 2, 3], to_string)
        assert results == ["item_1", "item_2", "item_3"]

        # 返回布尔值
        def is_even(item):
            return item % 2 == 0

        results = process_concurrently([1, 2, 3, 4], is_even)
        assert results == [False, True, False, True]

        # 返回列表
        def to_list(item):
            return [item, item * 2]

        results = process_concurrently([1, 2], to_list)
        assert results == [[1, 2], [2, 4]]

    def test_description_parameter(self):
        """测试description参数"""
        def dummy(item):
            return item

        # 不应该抛出异常
        results = process_concurrently(
            [1, 2, 3],
            dummy,
            description="Custom processing"
        )
        assert results == [1, 2, 3]
