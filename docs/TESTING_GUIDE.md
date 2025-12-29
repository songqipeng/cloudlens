# 测试指南

> CloudLens 测试编写与执行指南  
> 最后更新：2025-12-23

---

## 📋 目录

- [测试概述](#测试概述)
- [运行测试](#运行测试)
- [编写单元测试](#编写单元测试)
- [编写集成测试](#编写集成测试)
- [Mock 数据使用](#mock-数据使用)
- [测试覆盖率](#测试覆盖率)
- [测试最佳实践](#测试最佳实践)
- [常见问题](#常见问题)

---

## 测试概述

### 测试类型

CloudLens 项目包含以下类型的测试：

1. **单元测试**：测试单个函数/类
2. **集成测试**：测试模块间交互
3. **API 测试**：测试 Web API 端点（计划中）

### 测试框架

- **pytest**: Python 测试框架
- **pytest-cov**: 测试覆盖率
- **pytest-asyncio**: 异步测试支持
- **pytest-mock**: Mock 支持

### 测试目录结构

```
tests/
├── core/                    # 核心模块测试
│   ├── test_cache.py        # 缓存测试
│   ├── test_idle_detector.py # 闲置检测测试
│   ├── test_filter_engine.py # 筛选引擎测试
│   └── ...
├── providers/               # Provider 测试
│   ├── test_aliyun_provider.py
│   └── test_tencent_provider.py
└── web/                     # Web API 测试（计划中）
    ├── test_api_budgets.py
    └── ...
```

---

## 运行测试

### 运行所有测试

```bash
# 运行所有测试
pytest

# 运行并显示详细输出
pytest -v

# 运行并显示打印输出
pytest -s
```

### 运行特定测试

```bash
# 运行特定文件
pytest tests/core/test_cache.py

# 运行特定测试类
pytest tests/core/test_cache.py::TestCacheManager

# 运行特定测试方法
pytest tests/core/test_cache.py::TestCacheManager::test_save_and_get_data
```

### 运行测试并查看覆盖率

```bash
# 查看覆盖率报告
pytest --cov=core --cov=providers --cov-report=html

# 查看终端覆盖率
pytest --cov=core --cov=providers --cov-report=term

# 生成 HTML 报告
pytest --cov=core --cov=providers --cov-report=html
# 然后打开 htmlcov/index.html
```

### 运行测试并停止在第一个失败

```bash
pytest -x
```

### 运行测试并显示失败详情

```bash
pytest -v --tb=short
```

---

## 编写单元测试

### 基本结构

```python
"""测试模块文档"""
import pytest
from core.cache import CacheManager


class TestCacheManager:
    """CacheManager 测试类"""

    def test_save_and_get_data(self):
        """测试：保存和获取数据"""
        cache = CacheManager(ttl_seconds=3600)
        
        # 准备数据
        test_data = {"key": "value"}
        
        # 执行操作
        cache.set(resource_type="test", account_name="test", data=test_data)
        result = cache.get(resource_type="test", account_name="test")
        
        # 断言
        assert result == test_data
```

### 使用 Fixtures

```python
import pytest
from core.idle_detector import IdleDetector


class TestIdleDetector:
    """IdleDetector 测试类"""

    @pytest.fixture
    def detector(self):
        """创建 IdleDetector 实例"""
        return IdleDetector()

    def test_is_ecs_idle_with_low_cpu(self, detector):
        """测试：低 CPU 使用率应判定为闲置"""
        metrics = {
            "CPU利用率": 2.5,
            "内存利用率": 15.0,
            "公网入流量": 500,
            "公网出流量": 500,
            "磁盘读IOPS": 50,
            "磁盘写IOPS": 50
        }
        
        is_idle, reasons = detector.is_ecs_idle(metrics)
        
        assert is_idle is True
        assert len(reasons) >= 2
```

### 参数化测试

```python
import pytest


@pytest.mark.parametrize("cpu,memory,expected", [
    (2.5, 15.0, True),   # 低使用率，应判定为闲置
    (75.0, 80.0, False), # 高使用率，不应判定为闲置
    (5.0, 20.0, True),   # 边界值
])
def test_is_ecs_idle(cpu, memory, expected, detector):
    """测试：不同使用率组合"""
    metrics = {
        "CPU利用率": cpu,
        "内存利用率": memory,
        "公网入流量": 1000,
        "公网出流量": 1000,
        "磁盘读IOPS": 100,
        "磁盘写IOPS": 100
    }
    
    is_idle, _ = detector.is_ecs_idle(metrics)
    assert is_idle == expected
```

### 异常测试

```python
import pytest
from core.cache import CacheManager


def test_cache_miss():
    """测试：缓存未命中应返回 None"""
    cache = CacheManager()
    
    result = cache.get(resource_type="nonexistent", account_name="test")
    
    assert result is None


def test_invalid_input():
    """测试：无效输入应抛出异常"""
    cache = CacheManager()
    
    with pytest.raises(ValueError):
        cache.set(resource_type="", account_name="test", data={})
```

---

## 编写集成测试

### 测试模块间交互

```python
import pytest
from core.cache import CacheManager
from core.idle_detector import IdleDetector
from core.config import ConfigManager


class TestIntegration:
    """集成测试"""

    def test_cache_and_detector_integration(self):
        """测试：缓存和检测器集成"""
        # 初始化组件
        cache = CacheManager()
        detector = IdleDetector()
        config = ConfigManager()
        
        # 获取账号
        accounts = config.list_accounts()
        assert len(accounts) > 0
        
        # 测试缓存
        test_data = {"test": "data"}
        cache.set(resource_type="test", account_name=accounts[0].name, data=test_data)
        
        # 验证缓存
        result = cache.get(resource_type="test", account_name=accounts[0].name)
        assert result == test_data
```

---

## Mock 数据使用

### 使用 pytest-mock

```python
import pytest
from unittest.mock import Mock, patch
from core.provider import AliyunProvider


class TestProvider:
    """Provider 测试类"""

    def test_list_ecs_instances(self, mocker):
        """测试：列出 ECS 实例"""
        # Mock 云服务 API 响应
        mock_response = {
            "Instances": {
                "Instance": [
                    {
                        "InstanceId": "i-xxx",
                        "InstanceName": "test-instance",
                        "Status": "Running"
                    }
                ]
            }
        }
        
        # Mock API 调用
        mocker.patch(
            "aliyunsdkecs.request.v20140526.DescribeInstancesRequest",
            return_value=mock_response
        )
        
        # 执行测试
        provider = AliyunProvider(...)
        instances = provider.list_ecs_instances()
        
        assert len(instances) == 1
        assert instances[0]["InstanceId"] == "i-xxx"
```

### 使用 patch 装饰器

```python
from unittest.mock import patch
import pytest


@patch("core.provider.AliyunProvider._call_api")
def test_list_resources(mock_call_api):
    """测试：列出资源"""
    # 设置 Mock 返回值
    mock_call_api.return_value = {
        "Instances": {"Instance": []}
    }
    
    provider = AliyunProvider(...)
    resources = provider.list_resources("ecs")
    
    # 验证 Mock 被调用
    mock_call_api.assert_called_once()
    assert resources == []
```

---

## 测试覆盖率

### 查看覆盖率

```bash
# 生成覆盖率报告
pytest --cov=core --cov=providers --cov-report=html

# 查看覆盖率统计
pytest --cov=core --cov=providers --cov-report=term-missing
```

### 覆盖率目标

- **核心模块**：80%+
- **Provider 模块**：70%+
- **资源分析器**：60%+
- **整体覆盖率**：50%+

### 排除文件

在 `pytest.ini` 中配置：

```ini
[tool:pytest]
addopts = --cov=core --cov=providers --cov-report=html
[coverage:run]
omit = 
    */tests/*
    */venv/*
    */__pycache__/*
```

---

## 测试最佳实践

### 1. 测试命名

- 测试文件：`test_*.py`
- 测试类：`Test*`
- 测试方法：`test_*`

```python
# ✅ 好的命名
def test_is_ecs_idle_with_low_cpu():
    pass

# ❌ 不好的命名
def test1():
    pass
```

### 2. 测试结构

遵循 AAA 模式：

- **Arrange**：准备测试数据
- **Act**：执行被测试的操作
- **Assert**：验证结果

```python
def test_save_and_get_data(self):
    # Arrange: 准备数据
    cache = CacheManager()
    test_data = {"key": "value"}
    
    # Act: 执行操作
    cache.set(resource_type="test", account_name="test", data=test_data)
    result = cache.get(resource_type="test", account_name="test")
    
    # Assert: 验证结果
    assert result == test_data
```

### 3. 测试隔离

每个测试应该是独立的，不依赖其他测试：

```python
# ✅ 好的：每个测试独立
def test_save_data(self):
    cache = CacheManager()
    cache.set(...)
    assert cache.get(...) is not None

def test_get_data(self):
    cache = CacheManager()
    assert cache.get(...) is None

# ❌ 不好的：测试之间有依赖
def test_save_data(self):
    self.cache.set(...)

def test_get_data(self):
    # 依赖 test_save_data 先执行
    assert self.cache.get(...) is not None
```

### 4. 使用 Fixtures

对于重复的初始化代码，使用 fixtures：

```python
@pytest.fixture
def cache_manager():
    """创建 CacheManager 实例"""
    return CacheManager(ttl_seconds=3600)

def test_save_data(cache_manager):
    cache_manager.set(...)
    assert cache_manager.get(...) is not None
```

### 5. 测试边界条件

```python
def test_edge_cases(self, detector):
    """测试边界条件"""
    # 空数据
    is_idle, _ = detector.is_ecs_idle({})
    assert isinstance(is_idle, bool)
    
    # 边界值
    metrics = {
        "CPU利用率": 5.0,  # 恰好等于阈值
        "内存利用率": 20.0,
        ...
    }
    is_idle, reasons = detector.is_ecs_idle(metrics)
    # 验证边界值处理
```

### 6. 测试异常情况

```python
def test_exceptions(self):
    """测试异常处理"""
    cache = CacheManager()
    
    # 测试无效输入
    with pytest.raises(ValueError):
        cache.set(resource_type="", account_name="test", data={})
    
    # 测试 None 值
    with pytest.raises(TypeError):
        cache.set(resource_type="test", account_name="test", data=None)
```

---

## 常见问题

### 1. 测试失败：ModuleNotFoundError

**问题**：`ModuleNotFoundError: No module named 'core'`

**解决方案**：

```bash
# 确保在项目根目录运行测试
cd /path/to/aliyunidle

# 确保虚拟环境已激活
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 测试失败：数据库连接错误

**问题**：`OperationalError: unable to open database file`

**解决方案**：

```python
# 在测试中使用临时数据库
import tempfile
import pytest

@pytest.fixture
def temp_db():
    """创建临时数据库"""
    db_path = tempfile.mktemp(suffix=".db")
    yield db_path
    # 清理
    import os
    if os.path.exists(db_path):
        os.remove(db_path)
```

### 3. 测试失败：异步函数测试

**问题**：异步函数测试失败

**解决方案**：

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """测试异步函数"""
    result = await async_function()
    assert result is not None
```

### 4. 测试覆盖率不准确

**问题**：覆盖率报告不准确

**解决方案**：

```bash
# 确保排除测试文件
pytest --cov=core --cov=providers \
  --cov-report=html \
  --ignore=tests
```

---

## 测试检查清单

编写测试时，请确认：

- [ ] 测试覆盖了正常流程
- [ ] 测试覆盖了边界条件
- [ ] 测试覆盖了异常情况
- [ ] 测试是独立的（不依赖其他测试）
- [ ] 测试使用了有意义的命名
- [ ] 测试包含了清晰的断言
- [ ] 测试使用了适当的 fixtures
- [ ] 测试运行速度快（< 1 秒）

---

## 相关文档

- [开发指南](DEVELOPMENT_GUIDE.md)
- [API 参考](API_REFERENCE.md)
- [贡献指南](CONTRIBUTING.md)

---

**Happy Testing! 🧪**

