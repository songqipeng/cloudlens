#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retry_helper 单元测试
"""

import pytest
import time
from utils.retry_helper import retry_api_call, call_with_retry


class TestRetryHelper:
    """API重试机制测试类"""

    def test_successful_call_no_retry(self):
        """测试成功调用（无需重试）"""
        call_count = {'count': 0}

        @retry_api_call(max_attempts=3)
        def successful_func():
            call_count['count'] += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count['count'] == 1  # 只调用一次

    def test_retry_on_connection_error(self):
        """测试ConnectionError会重试"""
        call_count = {'count': 0}

        @retry_api_call(max_attempts=3, min_wait=0.1, max_wait=0.5)
        def fail_twice_then_succeed():
            call_count['count'] += 1
            if call_count['count'] < 3:
                raise ConnectionError("Network error")
            return "success"

        result = fail_twice_then_succeed()
        assert result == "success"
        assert call_count['count'] == 3  # 失败2次，第3次成功

    def test_retry_on_timeout_error(self):
        """测试TimeoutError会重试"""
        call_count = {'count': 0}

        @retry_api_call(max_attempts=3, min_wait=0.1, max_wait=0.5)
        def timeout_then_succeed():
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise TimeoutError("Request timeout")
            return "success"

        result = timeout_then_succeed()
        assert result == "success"
        assert call_count['count'] == 2  # 失败1次，第2次成功

    def test_retry_on_os_error(self):
        """测试OSError会重试"""
        call_count = {'count': 0}

        @retry_api_call(max_attempts=3, min_wait=0.1, max_wait=0.5)
        def os_error_then_succeed():
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise OSError("OS error")
            return "success"

        result = os_error_then_succeed()
        assert result == "success"
        assert call_count['count'] == 2

    def test_no_retry_on_400_error(self):
        """测试400错误不重试"""
        call_count = {'count': 0}

        @retry_api_call(max_attempts=3, min_wait=0.1, max_wait=0.5)
        def bad_request():
            call_count['count'] += 1
            raise Exception("HTTP 400 Bad Request")

        with pytest.raises(Exception, match="400"):
            bad_request()

        assert call_count['count'] == 1  # 不应该重试

    def test_no_retry_on_403_error(self):
        """测试403错误不重试"""
        call_count = {'count': 0}

        @retry_api_call(max_attempts=3, min_wait=0.1, max_wait=0.5)
        def forbidden():
            call_count['count'] += 1
            raise Exception("HTTP 403 Forbidden")

        with pytest.raises(Exception, match="403"):
            forbidden()

        assert call_count['count'] == 1  # 不应该重试

    def test_no_retry_on_404_error(self):
        """测试404错误不重试"""
        call_count = {'count': 0}

        @retry_api_call(max_attempts=3, min_wait=0.1, max_wait=0.5)
        def not_found():
            call_count['count'] += 1
            raise Exception("HTTP 404 Not Found")

        with pytest.raises(Exception, match="404"):
            not_found()

        assert call_count['count'] == 1  # 不应该重试

    def test_no_retry_on_invalid_error(self):
        """测试Invalid错误不重试"""
        call_count = {'count': 0}

        @retry_api_call(max_attempts=3, min_wait=0.1, max_wait=0.5)
        def invalid_param():
            call_count['count'] += 1
            raise Exception("InvalidParameter.Foo")

        with pytest.raises(Exception, match="Invalid"):
            invalid_param()

        assert call_count['count'] == 1  # 不应该重试

    def test_max_attempts_reached(self):
        """测试达到最大重试次数"""
        call_count = {'count': 0}

        @retry_api_call(max_attempts=3, min_wait=0.1, max_wait=0.5)
        def always_fail():
            call_count['count'] += 1
            raise ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            always_fail()

        assert call_count['count'] == 3  # 尝试3次后放弃

    def test_exponential_backoff(self):
        """测试指数退避"""
        timestamps = []

        @retry_api_call(max_attempts=4, min_wait=0.1, max_wait=1)
        def fail_with_timing():
            timestamps.append(time.time())
            if len(timestamps) < 4:
                raise ConnectionError("Network error")
            return "success"

        result = fail_with_timing()
        assert result == "success"

        # 验证等待时间递增
        if len(timestamps) >= 3:
            wait1 = timestamps[1] - timestamps[0]
            wait2 = timestamps[2] - timestamps[1]
            # 第二次等待应该比第一次长（指数退避）
            assert wait2 >= wait1 * 0.9  # 允许一些误差

    def test_custom_retry_exceptions(self):
        """测试自定义重试异常"""
        call_count = {'count': 0}

        @retry_api_call(
            max_attempts=3,
            min_wait=0.1,
            max_wait=0.5,
            retry_exceptions=(ValueError,)
        )
        def custom_exception():
            call_count['count'] += 1
            if call_count['count'] < 3:
                raise ValueError("Custom error")
            return "success"

        result = custom_exception()
        assert result == "success"
        assert call_count['count'] == 3

    def test_custom_retry_does_not_retry_other_exceptions(self):
        """测试自定义异常不重试其他类型"""
        call_count = {'count': 0}

        @retry_api_call(
            max_attempts=3,
            min_wait=0.1,
            max_wait=0.5,
            retry_exceptions=(ValueError,)
        )
        def type_error():
            call_count['count'] += 1
            raise TypeError("Type error")

        with pytest.raises(TypeError):
            type_error()

        assert call_count['count'] == 1  # 不应该重试TypeError

    def test_call_with_retry_success(self):
        """测试call_with_retry成功调用"""
        def simple_func(a, b):
            return a + b

        result = call_with_retry(simple_func, 2, 3)
        assert result == 5

    def test_call_with_retry_with_kwargs(self):
        """测试call_with_retry使用关键字参数"""
        def func_with_kwargs(x, y=10):
            return x * y

        result = call_with_retry(func_with_kwargs, 5, y=3)
        assert result == 15

    def test_call_with_retry_retries_on_error(self):
        """测试call_with_retry会重试"""
        call_count = {'count': 0}

        def fail_once():
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise ConnectionError("Network error")
            return "success"

        result = call_with_retry(fail_once)
        assert result == "success"
        assert call_count['count'] == 2

    def test_retry_with_return_value(self):
        """测试返回不同类型的值"""
        @retry_api_call(max_attempts=2)
        def return_dict():
            return {'status': 'ok', 'data': [1, 2, 3]}

        result = return_dict()
        assert isinstance(result, dict)
        assert result['status'] == 'ok'

    def test_retry_with_none_return(self):
        """测试返回None"""
        @retry_api_call(max_attempts=2)
        def return_none():
            return None

        result = return_none()
        assert result is None

    def test_multiple_decorators(self):
        """测试多次装饰"""
        call_count = {'count': 0}

        @retry_api_call(max_attempts=2, min_wait=0.1, max_wait=0.5)
        @retry_api_call(max_attempts=2, min_wait=0.1, max_wait=0.5)
        def double_decorated():
            call_count['count'] += 1
            if call_count['count'] < 3:
                raise ConnectionError("Network error")
            return "success"

        # 注意：双重装饰可能导致重试次数增加
        result = double_decorated()
        assert result == "success"
        # 验证至少进行了重试
        assert call_count['count'] >= 2
