# 项目重构与优化指南

> 本文档基于对当前代码库的深入分析，提供系统化的重构方案和扩展建议

---

## 📋 文档导航

1. [项目现状评估](#1-项目现状评估)
2. [架构优化方案](#2-架构优化方案)
3. [性能提升策略](#3-性能提升策略)
4. [多云架构设计](#4-多云架构设计)
5. [命令行接口规范](#5-命令行接口规范)
6. [密钥安全方案](#6-密钥安全方案)
7. [产品扩展规划](#7-产品扩展规划)
8. [实施路线图](#8-实施路线图)

---

## 1. 项目现状评估

### 1.1 核心功能模块

| 模块 | 文件 | 功能范围 | 完成度 |
|------|------|---------|--------|
| 主程序 | `main.py` | 统一入口，多租户支持 | ✅ 100% |
| ECS分析 | `check_ecs_idle_fixed.py` | ECS实例闲置分析 | ✅ 100% |
| RDS分析 | `resource_modules/rds_analyzer.py` | RDS数据库分析 | ✅ 100% |
| Redis分析 | `resource_modules/redis_analyzer.py` | Redis缓存分析 | ✅ 100% |
| MongoDB分析 | `resource_modules/mongodb_analyzer.py` | MongoDB分析 | ✅ 100% |
| OSS分析 | `resource_modules/oss_analyzer.py` | OSS存储分析 | ✅ 100% |
| 折扣分析 | `resource_modules/discount_analyzer.py` | ECS折扣分析 | ✅ 100% |

### 1.2 技术栈分析

**当前技术选型**:
- Python 3.x + 阿里云SDK
- SQLite (数据持久化)
- Pickle (缓存层)
- Pandas + openpyxl (报告生成)

**架构特点**:
```
阿里云API → 数据采集 → 缓存层(24h) → SQLite → 分析引擎 → 报告输出(HTML/Excel)
```

### 1.3 代码质量评估

**优势**:
- ✅ 功能完整度高
- ✅ 代码可读性好
- ✅ 报告可视化友好
- ✅ 多租户支持完善

**改进空间**:
- ⚠️ 代码重复率约40%（各分析器重复逻辑多）
- ⚠️ 串行处理导致性能瓶颈（100实例需10-15分钟）
- ⚠️ 硬编码阈值缺乏灵活性
- ⚠️ 错误处理不够健壮（无重试机制）
- ⚠️ 缺少单元测试
- ⚠️ 敏感信息明文存储

---

## 2. 架构优化方案

### 2.1 推荐目录结构

```
multicloud-analyzer/              # 建议项目重命名
├── main.py                       # 统一CLI入口
├── config.json                   # 多云配置
├── thresholds.yaml               # 可配置阈值
├── requirements.txt
├── README.md
│
├── core/                         # 核心框架层
│   ├── __init__.py
│   ├── base_analyzer.py         # 抽象基类
│   ├── base_reporter.py         # 报告生成基类
│   ├── cache_manager.py         # 统一缓存管理
│   ├── db_manager.py            # 统一数据库管理
│   ├── config_manager.py        # 配置管理
│   └── threshold_manager.py     # 阈值管理
│
├── clouds/                       # 云厂商实现层
│   ├── __init__.py
│   │
│   ├── aliyun/                  # 阿里云
│   │   ├── __init__.py
│   │   ├── client.py            # 客户端封装
│   │   ├── resources/           # 资源分析器
│   │   │   ├── __init__.py
│   │   │   ├── ecs_analyzer.py
│   │   │   ├── rds_analyzer.py
│   │   │   ├── redis_analyzer.py
│   │   │   ├── mongodb_analyzer.py
│   │   │   ├── oss_analyzer.py
│   │   │   ├── slb_analyzer.py      # 新增
│   │   │   ├── eip_analyzer.py      # 新增
│   │   │   ├── nat_analyzer.py      # 新增
│   │   │   ├── disk_analyzer.py     # 新增
│   │   │   └── snapshot_analyzer.py # 新增
│   │   └── discount_analyzer.py
│   │
│   ├── tencent/                 # 腾讯云（Phase 3）
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── resources/
│   │       ├── cvm_analyzer.py  # 对应ECS
│   │       ├── cdb_analyzer.py  # 对应RDS
│   │       ├── cos_analyzer.py  # 对应OSS
│   │       └── clb_analyzer.py  # 对应SLB
│   │
│   ├── aws/                     # AWS（Phase 5）
│   └── huawei/                  # 华为云（Phase 5）
│
├── utils/                        # 工具层
│   ├── __init__.py
│   ├── logger.py                # 日志管理
│   ├── metrics_helper.py        # 指标计算
│   ├── report_generator.py      # 报告生成
│   ├── validator.py             # 数据验证
│   └── credential_manager.py    # 凭证管理
│
├── templates/                    # 报告模板
│   ├── html/
│   └── excel/
│
├── output/                       # 输出目录
│   ├── aliyun/
│   │   └── {tenant}/
│   │       ├── cru/
│   │       └── discount/
│   └── tencent/
│
├── data/                         # 数据目录
│   ├── cache/
│   └── db/
│
├── logs/                         # 日志目录
│
└── tests/                        # 单元测试
    ├── test_aliyun/
    ├── test_tencent/
    └── test_core/
```

### 2.2 基础抽象类设计

```python
# core/base_analyzer.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseCloudAnalyzer(ABC):
    """云资源分析器抽象基类"""

    def __init__(self, tenant_config: Dict[str, Any]):
        self.tenant_config = tenant_config
        self.client = self.init_client()
        self.db_manager = self._init_db_manager()
        self.cache_manager = self._init_cache_manager()

    @abstractmethod
    def init_client(self):
        """初始化云厂商客户端"""
        pass

    @abstractmethod
    def get_all_regions(self) -> List[str]:
        """获取所有可用区域"""
        pass

    @abstractmethod
    def get_instances(self, region: str, resource_type: str) -> List[Dict]:
        """获取资源实例列表"""
        pass

    def get_metrics(self, instance_id: str, metric_names: List[str],
                   start_time: int, end_time: int) -> Dict[str, float]:
        """
        获取监控指标（通用实现，子类可重写）

        Args:
            instance_id: 实例ID
            metric_names: 指标名称列表
            start_time: 开始时间戳
            end_time: 结束时间戳

        Returns:
            Dict[metric_name, metric_value]
        """
        # 通用监控数据获取逻辑
        pass

    def get_cost(self, instance_id: str, period: str = 'Month') -> float:
        """获取成本信息（通用接口）"""
        pass

    def is_idle(self, instance: Dict, metrics: Dict, thresholds: Dict) -> tuple:
        """
        判断是否闲置

        Returns:
            (is_idle: bool, conditions: List[str])
        """
        pass

    def _init_db_manager(self):
        """初始化数据库管理器"""
        from core.db_manager import DatabaseManager
        return DatabaseManager(self.get_db_name())

    def _init_cache_manager(self):
        """初始化缓存管理器"""
        from core.cache_manager import CacheManager
        return CacheManager(self.get_cache_file())

    @abstractmethod
    def get_db_name(self) -> str:
        """获取数据库文件名"""
        pass

    @abstractmethod
    def get_cache_file(self) -> str:
        """获取缓存文件名"""
        pass


class BaseResourceAnalyzer(ABC):
    """资源分析器抽象基类"""

    def __init__(self, cloud_analyzer: BaseCloudAnalyzer,
                 threshold_manager, logger):
        self.cloud_analyzer = cloud_analyzer
        self.threshold_manager = threshold_manager
        self.logger = logger

    @abstractmethod
    def analyze(self) -> List[Dict]:
        """执行分析，返回闲置资源列表"""
        pass

    @abstractmethod
    def is_idle(self, instance: Dict, metrics: Dict) -> tuple:
        """判断资源是否闲置"""
        pass

    @abstractmethod
    def get_optimization_suggestions(self, instance: Dict,
                                    metrics: Dict) -> str:
        """获取优化建议"""
        pass
```

### 2.3 统一配置管理

```python
# core/config_manager.py
import os
import json
from typing import Dict, Any

class ConfigManager:
    """统一配置管理器"""

    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置（支持环境变量替换）"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return self._replace_env_vars(config)

    def _replace_env_vars(self, obj: Any) -> Any:
        """递归替换环境变量 ${VAR_NAME}"""
        if isinstance(obj, dict):
            return {k: self._replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            var_name = obj[2:-1]
            value = os.getenv(var_name)
            if value is None:
                raise ValueError(f"环境变量未设置: {var_name}")
            return value
        return obj

    def get_tenant_config(self, cloud: str, tenant: str) -> Dict[str, Any]:
        """获取租户配置"""
        try:
            return self.config['clouds'][cloud]['tenants'][tenant]
        except KeyError:
            raise ValueError(f"未找到配置: {cloud}/{tenant}")

    def validate(self):
        """验证配置完整性"""
        required_fields = ['clouds', 'default_cloud', 'default_tenant']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"配置缺少必需字段: {field}")
```

### 2.4 统一数据库管理

```python
# core/db_manager.py
import sqlite3
from typing import List, Dict, Any
from pathlib import Path

class DatabaseManager:
    """统一数据库管理器"""

    def __init__(self, db_name: str, db_dir: str = './data/db'):
        self.db_path = Path(db_dir) / db_name
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None

    def connect(self):
        """建立连接"""
        if not self.conn:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, sql: str, params: tuple = None):
        """执行SQL"""
        conn = self.connect()
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        conn.commit()
        return cursor

    def query(self, sql: str, params: tuple = None) -> List[Dict]:
        """查询并返回字典列表"""
        cursor = self.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def init_schema(self, schema_sql: str):
        """初始化数据库schema"""
        self.execute(schema_sql)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

### 2.5 统一缓存管理

```python
# core/cache_manager.py
import pickle
import time
from pathlib import Path
from typing import Any, Optional

class CacheManager:
    """统一缓存管理器"""

    def __init__(self, cache_file: str, ttl_hours: int = 24,
                 cache_dir: str = './data/cache'):
        self.cache_path = Path(cache_dir) / cache_file
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600

    def is_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.cache_path.exists():
            return False

        cache_time = self.cache_path.stat().st_mtime
        current_time = time.time()
        return (current_time - cache_time) < self.ttl_seconds

    def save(self, data: Any):
        """保存缓存"""
        cache_data = {
            'timestamp': time.time(),
            'data': data
        }
        with open(self.cache_path, 'wb') as f:
            pickle.dump(cache_data, f)

    def load(self) -> Optional[Any]:
        """加载缓存"""
        if not self.is_valid():
            return None

        try:
            with open(self.cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            return cache_data['data']
        except Exception:
            return None

    def clear(self):
        """清除缓存"""
        if self.cache_path.exists():
            self.cache_path.unlink()
```

---

## 3. 性能提升策略

### 3.1 问题分析

**当前性能瓶颈**:
- 串行处理100个ECS实例耗时10-15分钟
- 每个实例需要：
  - 获取基本信息: 0.5s
  - 获取18个监控指标: 18 × 0.2s = 3.6s
  - 获取EIP信息: 0.3s
  - 获取成本信息: 0.5s
  - 总计约5秒/实例

**理论执行时间**:
- 100实例 × 5秒 = 500秒 ≈ 8.3分钟
- 实际10-15分钟（包含数据库操作）

### 3.2 并发优化方案

**方案A: 线程池（推荐，实现简单）**

```python
# utils/concurrent_helper.py
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Any
import logging

logger = logging.getLogger(__name__)

def process_concurrently(items: List[Any],
                        process_func: Callable,
                        max_workers: int = 10,
                        description: str = "Processing") -> List[Any]:
    """
    并发处理列表项

    Args:
        items: 待处理的项目列表
        process_func: 处理函数
        max_workers: 最大并发数
        description: 描述（用于日志）

    Returns:
        处理结果列表
    """
    results = []
    total = len(items)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_item = {
            executor.submit(process_func, item): item
            for item in items
        }

        # 收集结果
        completed = 0
        for future in as_completed(future_to_item):
            completed += 1
            item = future_to_item[future]

            try:
                result = future.result()
                results.append(result)
                logger.info(f"{description}: {completed}/{total} completed")
            except Exception as e:
                logger.error(f"{description} failed for {item}: {e}")
                results.append(None)

    return results


# 使用示例
def process_single_instance(instance):
    """处理单个实例"""
    instance_id = instance['InstanceId']

    # 获取监控数据
    metrics = get_metrics(instance_id)

    # 获取EIP信息
    eip_info = get_eip_info(instance_id)

    # 获取成本
    cost = get_cost(instance_id)

    return {
        'instance': instance,
        'metrics': metrics,
        'eip_info': eip_info,
        'cost': cost
    }

# 并发处理所有实例
results = process_concurrently(
    instances,
    process_single_instance,
    max_workers=10,
    description="ECS实例分析"
)
```

**方案B: 异步IO（性能最优，实现复杂）**

```python
import asyncio
import aiohttp
from typing import List, Dict

async def get_metrics_async(session: aiohttp.ClientSession,
                           instance_id: str) -> Dict:
    """异步获取监控数据"""
    # 使用aiohttp异步调用API
    async with session.get(api_url) as response:
        return await response.json()

async def process_instance_async(session: aiohttp.ClientSession,
                                 instance: Dict) -> Dict:
    """异步处理单个实例"""
    instance_id = instance['InstanceId']

    # 并发获取所有数据
    metrics_task = get_metrics_async(session, instance_id)
    eip_task = get_eip_async(session, instance_id)
    cost_task = get_cost_async(session, instance_id)

    metrics, eip_info, cost = await asyncio.gather(
        metrics_task, eip_task, cost_task
    )

    return {
        'instance': instance,
        'metrics': metrics,
        'eip_info': eip_info,
        'cost': cost
    }

async def analyze_all_instances_async(instances: List[Dict]) -> List[Dict]:
    """异步分析所有实例"""
    async with aiohttp.ClientSession() as session:
        tasks = [
            process_instance_async(session, inst)
            for inst in instances
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    return results

# 使用
results = asyncio.run(analyze_all_instances_async(instances))
```

**性能对比**:
| 方案 | 100实例耗时 | 实现难度 | 推荐度 |
|------|------------|---------|--------|
| 串行 | 10-15分钟 | 简单 | ❌ |
| 线程池(10并发) | 1-2分钟 | 简单 | ✅ 推荐 |
| 异步IO(50并发) | 30-60秒 | 中等 | ⭐⭐⭐ |

### 3.3 API限流控制

```python
import time
from functools import wraps

class RateLimiter:
    """API速率限制器"""

    def __init__(self, calls_per_second: int = 10):
        self.interval = 1.0 / calls_per_second
        self.last_call = 0

    def wait(self):
        """等待直到可以调用"""
        now = time.time()
        elapsed = now - self.last_call

        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)

        self.last_call = time.time()

def rate_limit(calls_per_second: int = 10):
    """速率限制装饰器"""
    limiter = RateLimiter(calls_per_second)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter.wait()
            return func(*args, **kwargs)
        return wrapper
    return decorator

# 使用
@rate_limit(calls_per_second=20)
def call_aliyun_api(request):
    return client.do_action_with_exception(request)
```

### 3.4 错误重试机制

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import logging

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=lambda retry_state: logger.warning(
        f"API调用失败，{retry_state.attempt_number}次重试..."
    )
)
def call_api_with_retry(request):
    """带重试的API调用"""
    try:
        return client.do_action_with_exception(request)
    except Exception as e:
        logger.error(f"API调用异常: {e}")
        raise
```

---

## 4. 多云架构设计

### 4.1 云厂商资源对应关系

| 资源类型 | 阿里云 | 腾讯云 | AWS | 华为云 |
|---------|--------|--------|-----|--------|
| 虚拟机 | ECS | CVM | EC2 | ECS |
| 关系数据库 | RDS | CDB | RDS | RDS |
| 缓存数据库 | Redis | Redis | ElastiCache | DCS |
| 对象存储 | OSS | COS | S3 | OBS |
| 负载均衡 | SLB/ALB | CLB | ALB/NLB | ELB |
| 公网IP | EIP | EIP | Elastic IP | EIP |
| NAT网关 | NAT Gateway | NAT Gateway | NAT Gateway | NAT Gateway |
| 云盘 | Cloud Disk | CBS | EBS | EVS |
| 快照 | Snapshot | Snapshot | Snapshot | Snapshot |
| VPN | VPN Gateway | VPN Gateway | VPN | VPN |
| CDN | CDN | CDN | CloudFront | CDN |
| 容器服务 | ACK | TKE | EKS | CCE |

### 4.2 标准化数据模型

```python
# core/models.py
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime

@dataclass
class StandardInstance:
    """标准化资源实例模型"""
    # 基本信息
    id: str
    name: str
    cloud: str                    # aliyun/tencent/aws/huawei
    region: str
    resource_type: str            # ecs/cvm/ec2

    # 规格信息
    instance_type: str
    cpu: int
    memory: int                   # GB

    # 状态信息
    status: str
    creation_time: str

    # 监控数据
    metrics: Dict[str, float] = field(default_factory=dict)

    # 成本信息
    cost: Optional[float] = None
    cost_unit: str = 'CNY'       # CNY/USD

    # 标签
    tags: Dict[str, str] = field(default_factory=dict)

    # 扩展信息
    extra: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'cloud': self.cloud,
            'region': self.region,
            'resource_type': self.resource_type,
            'instance_type': self.instance_type,
            'cpu': self.cpu,
            'memory': self.memory,
            'status': self.status,
            'creation_time': self.creation_time,
            'metrics': self.metrics,
            'cost': self.cost,
            'cost_unit': self.cost_unit,
            'tags': self.tags,
            'extra': self.extra
        }

    @classmethod
    def from_aliyun_ecs(cls, ecs_instance: Dict, metrics: Dict) -> 'StandardInstance':
        """从阿里云ECS实例创建"""
        return cls(
            id=ecs_instance['InstanceId'],
            name=ecs_instance.get('InstanceName', ''),
            cloud='aliyun',
            region=ecs_instance['RegionId'],
            resource_type='ecs',
            instance_type=ecs_instance['InstanceType'],
            cpu=ecs_instance['Cpu'],
            memory=ecs_instance['Memory'] // 1024,
            status=ecs_instance['Status'],
            creation_time=ecs_instance['CreationTime'],
            metrics=metrics,
            tags=ecs_instance.get('Tags', {})
        )

    @classmethod
    def from_tencent_cvm(cls, cvm_instance: Dict, metrics: Dict) -> 'StandardInstance':
        """从腾讯云CVM实例创建"""
        return cls(
            id=cvm_instance['InstanceId'],
            name=cvm_instance.get('InstanceName', ''),
            cloud='tencent',
            region=cvm_instance['Placement']['Zone'],
            resource_type='cvm',
            instance_type=cvm_instance['InstanceType'],
            cpu=cvm_instance['CPU'],
            memory=cvm_instance['Memory'],
            status=cvm_instance['InstanceState'],
            creation_time=cvm_instance['CreatedTime'],
            metrics=metrics,
            tags={tag['Key']: tag['Value'] for tag in cvm_instance.get('Tags', [])}
        )


@dataclass
class AnalysisResult:
    """分析结果模型"""
    instance: StandardInstance
    is_idle: bool
    idle_conditions: List[str]
    optimization_suggestions: str
    potential_savings: Optional[float] = None
```

### 4.3 插件化架构

```python
# core/plugin_manager.py
from typing import Dict, Type
from abc import ABC

class CloudPlugin(ABC):
    """云厂商插件接口"""

    @property
    def name(self) -> str:
        """云厂商名称"""
        pass

    @property
    def supported_resources(self) -> List[str]:
        """支持的资源类型"""
        pass

    def get_analyzer(self, resource_type: str):
        """获取资源分析器"""
        pass


class PluginManager:
    """插件管理器"""

    def __init__(self):
        self.plugins: Dict[str, CloudPlugin] = {}

    def register(self, plugin: CloudPlugin):
        """注册插件"""
        self.plugins[plugin.name] = plugin

    def get_plugin(self, cloud: str) -> CloudPlugin:
        """获取插件"""
        if cloud not in self.plugins:
            raise ValueError(f"不支持的云厂商: {cloud}")
        return self.plugins[cloud]

    def list_clouds(self) -> List[str]:
        """列出所有支持的云厂商"""
        return list(self.plugins.keys())


# 使用示例
from clouds.aliyun import AliyunPlugin
from clouds.tencent import TencentPlugin

plugin_manager = PluginManager()
plugin_manager.register(AliyunPlugin())
plugin_manager.register(TencentPlugin())

# 获取阿里云ECS分析器
aliyun_plugin = plugin_manager.get_plugin('aliyun')
ecs_analyzer = aliyun_plugin.get_analyzer('ecs')
```

### 4.4 多云配置文件设计

```json
{
  "version": "2.0",
  "default_cloud": "aliyun",
  "default_tenant": "ydzn",

  "clouds": {
    "aliyun": {
      "enabled": true,
      "tenants": {
        "ydzn": {
          "display_name": "运达智能",
          "access_key_id": "${ALIYUN_YDZN_AK}",
          "access_key_secret": "${ALIYUN_YDZN_SK}",
          "regions": ["cn-beijing", "cn-hangzhou"],
          "default_region": "cn-beijing",
          "tags": {
            "department": "ops",
            "env": "production"
          }
        }
      }
    },

    "tencent": {
      "enabled": true,
      "tenants": {
        "prod": {
          "display_name": "生产环境",
          "secret_id": "${TENCENT_PROD_ID}",
          "secret_key": "${TENCENT_PROD_KEY}",
          "regions": ["ap-beijing", "ap-shanghai"],
          "default_region": "ap-beijing"
        }
      }
    },

    "aws": {
      "enabled": false,
      "tenants": {}
    }
  },

  "analysis": {
    "default_days": 14,
    "cache_ttl_hours": 24,
    "concurrent_requests": 10,
    "retry_times": 3,
    "timeout_seconds": 30
  },

  "output": {
    "base_dir": "./output",
    "formats": ["html", "excel"],
    "auto_open": false
  },

  "logging": {
    "level": "INFO",
    "file": "./logs/analyzer.log",
    "max_bytes": 10485760,
    "backup_count": 5
  }
}
```

---

## 5. 命令行接口规范

### 5.1 统一命令格式

```bash
# 基础格式
python main.py [CLOUD] [TENANT] [ACTION] [RESOURCE] [OPTIONS]
```

### 5.2 完整参数定义

```
用法: main.py [OPTIONS] CLOUD TENANT ACTION [RESOURCE]

位置参数:
  CLOUD                 云厂商 (aliyun|tencent|aws|huawei|all)
  TENANT                租户名称
  ACTION                操作类型 (cru|discount|cost|trend|compare)
  RESOURCE              资源类型 (ecs|rds|redis|all) [默认: all]

基础选项:
  -h, --help            显示帮助信息
  -v, --version         显示版本信息
  -c, --config FILE     配置文件路径 [默认: config.json]
  -t, --tenant NAME     租户名称（覆盖位置参数）
  -r, --region REGION   指定区域 [默认: all]

分析选项:
  --threshold FILE      自定义阈值配置
  --days N              分析天数 [默认: 14]
  --no-cache            强制重新获取数据
  --cache-ttl HOURS     缓存有效期 [默认: 24]

输出选项:
  -o, --output DIR      输出目录 [默认: ./output]
  -f, --format FORMAT   输出格式 (html|excel|pdf|json|csv)
  --no-report           不生成报告，只分析
  --open                生成后自动打开报告

过滤选项:
  --include-tags TAGS   只分析包含这些标签的资源
  --exclude-tags TAGS   排除包含这些标签的资源
  --min-cost AMOUNT     只分析成本大于此金额的资源
  --idle-only           只显示闲置资源

通知选项:
  --email EMAIL         发送报告到邮箱
  --webhook URL         Webhook通知URL
  --slack-webhook URL   Slack通知
  --dingtalk-webhook    钉钉通知

调试选项:
  --debug               调试模式
  --verbose             详细输出
  --dry-run             模拟运行
  --profile             性能分析

凭证管理子命令:
  setup-credentials     设置凭证
  list-credentials      列出凭证
  delete-credentials    删除凭证
  test-credentials      测试凭证

多云对比:
  --compare             启用多云对比
  --baseline CLOUD      对比基准云
```

### 5.3 使用示例

```bash
# 1. 基础分析
python main.py aliyun ydzn cru ecs

# 2. 腾讯云分析
python main.py tencent prod cru cvm

# 3. 多格式输出
python main.py aliyun ydzn cru all -f html,excel,pdf

# 4. 指定区域
python main.py aliyun ydzn cru ecs -r cn-beijing

# 5. 自定义阈值
python main.py aliyun ydzn cru ecs --threshold custom.yaml

# 6. 高成本闲置资源
python main.py aliyun ydzn cru all --min-cost 1000 --idle-only

# 7. 多云对比
python main.py all ydzn cru ecs --compare

# 8. 凭证管理
python main.py setup-credentials
python main.py list-credentials
python main.py test-credentials aliyun ydzn

# 9. 向后兼容（老命令仍可用）
python main.py ydzn cru ecs
# 自动映射为: python main.py aliyun ydzn cru ecs
```

### 5.4 CLI框架实现

使用 **Click** 框架：

```python
# main.py
import click
from core.config_manager import ConfigManager
from core.plugin_manager import PluginManager
from utils.logger import setup_logger

@click.group(invoke_without_command=True)
@click.version_option(version='2.0.0')
@click.pass_context
def cli(ctx):
    """多云资源分析工具"""
    ctx.ensure_object(dict)

    # 如果没有子命令，进入交互模式
    if ctx.invoked_subcommand is None:
        interactive_mode()

@cli.command()
@click.argument('cloud', type=click.Choice(['aliyun', 'tencent', 'aws', 'all']))
@click.argument('tenant')
@click.argument('action', type=click.Choice(['cru', 'discount', 'cost', 'trend']))
@click.argument('resource', default='all')
@click.option('--region', '-r', default='all')
@click.option('--days', default=14)
@click.option('--format', '-f', default='html,excel')
@click.option('--no-cache', is_flag=True)
@click.option('--verbose', is_flag=True)
@click.option('--min-cost', type=float)
@click.option('--idle-only', is_flag=True)
def analyze(cloud, tenant, action, resource, **options):
    """分析云资源"""
    logger = setup_logger(verbose=options['verbose'])
    logger.info(f"分析 {cloud} {tenant} {resource}...")

    # 加载配置
    config_mgr = ConfigManager()
    tenant_config = config_mgr.get_tenant_config(cloud, tenant)

    # 执行分析
    # ...

@cli.command('setup-credentials')
def setup_credentials():
    """交互式设置凭证"""
    from utils.credential_manager import setup_credentials_interactive
    setup_credentials_interactive()

@cli.command('list-credentials')
def list_credentials():
    """列出所有凭证"""
    from utils.credential_manager import list_all_credentials
    list_all_credentials()

if __name__ == '__main__':
    cli()
```

---

## 6. 密钥安全方案

### 6.1 推荐方案：系统密钥环（Keyring）

**核心优势**:
- ✅ 操作系统级安全（macOS Keychain / Windows Credential Manager / Linux Secret Service）
- ✅ 无需实现加密逻辑
- ✅ 跨平台统一接口
- ✅ 用户体验最佳

**安装**:
```bash
pip install keyring
```

**核心实现**:

```python
# utils/credential_manager.py
import keyring
import json
import getpass
from typing import Dict, Optional

class CredentialManager:
    """基于系统密钥环的凭证管理"""

    SERVICE_NAME = "multicloud-analyzer"

    @staticmethod
    def save_credentials(cloud: str, tenant: str, credentials: Dict[str, str]):
        """保存凭证到系统密钥环"""
        key = f"{cloud}_{tenant}"
        value = json.dumps(credentials)
        keyring.set_password(CredentialManager.SERVICE_NAME, key, value)
        print(f"✅ 凭证已安全保存到系统密钥环: {cloud}/{tenant}")

    @staticmethod
    def get_credentials(cloud: str, tenant: str) -> Optional[Dict[str, str]]:
        """从系统密钥环获取凭证"""
        key = f"{cloud}_{tenant}"
        value = keyring.get_password(CredentialManager.SERVICE_NAME, key)
        return json.loads(value) if value else None

    @staticmethod
    def delete_credentials(cloud: str, tenant: str):
        """删除凭证"""
        key = f"{cloud}_{tenant}"
        try:
            keyring.delete_password(CredentialManager.SERVICE_NAME, key)
            print(f"✅ 凭证已删除: {cloud}/{tenant}")
        except keyring.errors.PasswordDeleteError:
            print(f"⚠️  凭证不存在: {cloud}/{tenant}")


def setup_credentials_interactive():
    """交互式设置凭证"""
    print("🔐 凭证管理器")
    print("=" * 60)

    cloud = input("云厂商 [aliyun/tencent/aws]: ").strip()
    tenant = input("租户名称: ").strip()

    if cloud == 'aliyun':
        ak = input("Access Key ID: ").strip()
        sk = getpass.getpass("Access Key Secret (输入时不显示): ")
        credentials = {
            'access_key_id': ak,
            'access_key_secret': sk
        }
    elif cloud == 'tencent':
        secret_id = input("Secret ID: ").strip()
        secret_key = getpass.getpass("Secret Key (输入时不显示): ")
        credentials = {
            'secret_id': secret_id,
            'secret_key': secret_key
        }
    else:
        print("❌ 不支持的云厂商")
        return

    CredentialManager.save_credentials(cloud, tenant, credentials)

    # 更新config.json标记
    update_config_for_keyring(cloud, tenant)


def update_config_for_keyring(cloud: str, tenant: str):
    """更新配置文件标记使用keyring"""
    import json

    config_file = 'config.json'
    with open(config_file, 'r') as f:
        config = json.load(f)

    if cloud not in config.get('clouds', {}):
        config.setdefault('clouds', {})[cloud] = {'tenants': {}}

    config['clouds'][cloud]['tenants'][tenant] = {
        'display_name': tenant,
        'use_keyring': True,
        'keyring_key': f"{cloud}_{tenant}"
    }

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_cloud_client(cloud: str, tenant: str):
    """获取云厂商客户端（自动从keyring读取）"""
    credentials = CredentialManager.get_credentials(cloud, tenant)

    if not credentials:
        print(f"❌ 未找到凭证: {cloud}/{tenant}")
        print("请先运行: python main.py setup-credentials")
        raise ValueError("凭证未设置")

    if cloud == 'aliyun':
        from aliyunsdkcore.client import AcsClient
        return AcsClient(
            credentials['access_key_id'],
            credentials['access_key_secret'],
            'cn-beijing'
        )
    elif cloud == 'tencent':
        from tencentcloud.common import credential
        return credential.Credential(
            credentials['secret_id'],
            credentials['secret_key']
        )
```

**使用流程**:

```bash
# 1. 首次设置（只需一次）
$ python main.py setup-credentials
🔐 凭证管理器
============================================================
云厂商 [aliyun/tencent/aws]: aliyun
租户名称: ydzn
Access Key ID: LTAI5t...
Access Key Secret (输入时不显示):
✅ 凭证已安全保存到系统密钥环: aliyun/ydzn

# 2. 之后使用（无需输入密码）
$ python main.py aliyun ydzn cru ecs
🔍 开始分析...

# macOS首次读取时会弹出系统授权对话框
# 选择 "Always Allow" 后，以后都不会再提示
```

### 6.2 备选方案：主密码加密

```python
# utils/secure_storage.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import json
import os
from pathlib import Path

class SecureCredentialStorage:
    """基于主密码的加密凭证存储"""

    def __init__(self):
        self.storage_file = Path.home() / '.multicloud' / '.credentials.enc'
        self.storage_file.parent.mkdir(exist_ok=True)

    def _derive_key(self, master_password: str) -> bytes:
        """从主密码派生加密密钥（PBKDF2）"""
        salt = b'multicloud-analyzer-salt-v1'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

    def save_credentials(self, cloud: str, tenant: str,
                        credentials: dict, master_password: str):
        """加密保存凭证"""
        key = self._derive_key(master_password)
        fernet = Fernet(key)

        # 读取现有数据
        all_credentials = {}
        if self.storage_file.exists():
            with open(self.storage_file, 'rb') as f:
                encrypted = f.read()
                decrypted = fernet.decrypt(encrypted)
                all_credentials = json.loads(decrypted)

        # 添加新凭证
        all_credentials[f"{cloud}_{tenant}"] = credentials

        # 加密保存
        encrypted = fernet.encrypt(json.dumps(all_credentials).encode())
        with open(self.storage_file, 'wb') as f:
            f.write(encrypted)

        os.chmod(self.storage_file, 0o600)
        print(f"✅ 凭证已加密保存: {cloud}/{tenant}")
```

---

## 7. 产品扩展规划

### 7.1 高优先级产品（立即支持）

#### 7.1.1 EIP（弹性公网IP）⭐⭐⭐⭐⭐

**闲置判定标准**:
```yaml
aliyun:
  eip:
    unbound: true                    # 未绑定实例
    instance_stopped: true           # 绑定的实例已停止
    traffic_mb_per_day: 1           # 流量 < 1MB/天
    bandwidth_usage_percent: 5       # 带宽使用率 < 5%
```

**实现要点**:
```python
class EIPAnalyzer(BaseResourceAnalyzer):
    def is_idle(self, eip, metrics):
        conditions = []

        # 1. 未绑定
        if not eip.get('instance_id'):
            conditions.append("未绑定任何实例")

        # 2. 实例已停止
        if eip.get('instance_status') in ['Stopped', 'Deleted']:
            conditions.append(f"绑定实例状态: {eip['instance_status']}")

        # 3. 流量低
        total_traffic = metrics.get('入流量', 0) + metrics.get('出流量', 0)
        if total_traffic < 1024 * 1024:  # 1MB
            conditions.append(f"流量过低({total_traffic/1024/1024:.2f}MB/天)")

        # 4. 带宽使用率低
        bandwidth_usage = metrics.get('带宽使用率', 0)
        if bandwidth_usage < 5:
            conditions.append(f"带宽使用率({bandwidth_usage:.1f}%) < 5%")

        return len(conditions) > 0, conditions

    def get_optimization_suggestions(self, eip, metrics):
        suggestions = []

        if not eip.get('instance_id'):
            suggestions.append("建议释放未绑定的EIP")

        bandwidth = eip.get('bandwidth', 0)
        usage = metrics.get('带宽使用率', 0)

        if eip.get('charge_type') == 'PayByBandwidth' and usage < 20:
            suggestions.append("建议改为按流量计费")

        if bandwidth > 5 and usage < 10:
            suggestions.append(f"建议降低带宽（当前{bandwidth}Mbps，使用率仅{usage:.1f}%）")

        return "; ".join(suggestions)
```

#### 7.1.2 SLB/ALB（负载均衡）⭐⭐⭐⭐⭐

**闲置判定标准**:
```yaml
aliyun:
  slb:
    backend_server_count: 0          # 后端服务器数 = 0
    traffic_mb_per_day: 10          # 流量 < 10MB/天
    active_connections: 10           # 活跃连接数 < 10
    new_connections_per_day: 100     # 新建连接 < 100/天
```

#### 7.1.3 NAT网关 ⭐⭐⭐⭐⭐

**闲置判定标准**:
```yaml
aliyun:
  nat:
    snat_rule_count: 0               # 无SNAT规则
    dnat_rule_count: 0               # 无DNAT规则
    traffic_mb_per_day: 100         # 流量 < 100MB/天
    concurrent_connections: 100      # 并发连接 < 100
```

#### 7.1.4 云盘（独立云盘）⭐⭐⭐⭐

**闲置判定标准**:
```yaml
aliyun:
  disk:
    status: "Available"              # 未挂载
    read_iops: 10                   # 读IOPS < 10
    write_iops: 10                  # 写IOPS < 10
    read_bps_mb: 1                  # 读速度 < 1MB/s
    write_bps_mb: 1                 # 写速度 < 1MB/s
```

#### 7.1.5 快照 ⭐⭐⭐⭐

**闲置判定标准**:
```yaml
aliyun:
  snapshot:
    source_disk_deleted: true        # 源盘已删除
    source_instance_deleted: true    # 源实例已删除
    age_days: 30                    # 创建超过30天未使用
    snapshot_chain_length: 10        # 快照链过长
```

### 7.2 中优先级产品

| 产品 | 优先级 | 关键指标 |
|------|--------|---------|
| VPN网关 | ⭐⭐⭐⭐ | 无活跃连接、流量低 |
| ACK容器 | ⭐⭐⭐ | 无Pod运行、节点利用率低 |
| ACR镜像 | ⭐⭐⭐ | 镜像长期未拉取 |
| 消息队列 | ⭐⭐⭐ | Topic无生产/消费 |
| 表格存储 | ⭐⭐⭐ | 预留吞吐利用率低 |

### 7.3 折扣分析扩展

**当前**: 仅支持ECS折扣分析
**目标**: 扩展到所有包年包月资源

```python
# 折扣分析优先级
DISCOUNT_ANALYSIS_ROADMAP = {
    'Phase 1': ['ecs'],              # 已完成
    'Phase 2': ['rds', 'redis'],     # 高优先级
    'Phase 3': ['mongodb', 'slb'],   # 中优先级
    'Phase 4': ['nat', 'vpn'],       # 中优先级
}
```

---

## 8. 实施路线图

### Phase 1: 代码重构与性能优化（1-2周）

**目标**: 提升代码质量和执行效率

**任务清单**:
- [ ] 提取基础抽象类
  - [ ] `core/base_analyzer.py`
  - [ ] `core/base_reporter.py`
  - [ ] `core/models.py`
- [ ] 实现统一管理器
  - [ ] `core/config_manager.py`
  - [ ] `core/db_manager.py`
  - [ ] `core/cache_manager.py`
  - [ ] `core/threshold_manager.py`
- [ ] 添加日志系统
  - [ ] `utils/logger.py`
- [ ] 实现并发处理
  - [ ] `utils/concurrent_helper.py`（线程池方案）
- [ ] 添加错误重试
  - [ ] 安装 `tenacity`
  - [ ] 封装 `call_api_with_retry()`
- [ ] 实现可配置阈值
  - [ ] 创建 `thresholds.yaml`
  - [ ] 实现 `ThresholdManager`
- [ ] 重构现有分析器
  - [ ] 使用基础类重写各分析器
  - [ ] 保持向后兼容

**验收标准**:
- ✅ 执行时间减少60%以上
- ✅ 代码重复率降低30%以上
- ✅ 所有现有功能正常

---

### Phase 2: 安全增强与产品扩展（2-3周）

**目标**: 密钥安全 + 新产品支持

**任务清单**:
- [ ] 密钥管理
  - [ ] 实现 `CredentialManager`（基于Keyring）
  - [ ] 添加凭证管理命令
    - [ ] `setup-credentials`
    - [ ] `list-credentials`
    - [ ] `delete-credentials`
    - [ ] `test-credentials`
  - [ ] 更新配置文件支持keyring标记
- [ ] 新产品支持
  - [ ] EIP分析器 (`clouds/aliyun/resources/eip_analyzer.py`)
  - [ ] SLB分析器 (`clouds/aliyun/resources/slb_analyzer.py`)
  - [ ] NAT分析器 (`clouds/aliyun/resources/nat_analyzer.py`)
  - [ ] 云盘分析器 (`clouds/aliyun/resources/disk_analyzer.py`)
  - [ ] 快照分析器 (`clouds/aliyun/resources/snapshot_analyzer.py`)
- [ ] 折扣分析扩展
  - [ ] RDS折扣分析
  - [ ] Redis折扣分析
  - [ ] MongoDB折扣分析
- [ ] 更新阈值配置
  - [ ] 添加新产品阈值到 `thresholds.yaml`

**验收标准**:
- ✅ 凭证不再明文存储
- ✅ 新增5个资源类型
- ✅ 折扣分析支持3个产品

---

### Phase 3: 多云支持（2-3周）

**目标**: 支持腾讯云

**任务清单**:
- [ ] 架构调整
  - [ ] 实现插件管理器 (`core/plugin_manager.py`)
  - [ ] 标准化数据模型 (`core/models.py`)
  - [ ] 更新配置文件支持多云
- [ ] 腾讯云实现
  - [ ] 创建 `clouds/tencent/` 目录
  - [ ] 实现腾讯云客户端封装
  - [ ] CVM分析器（对应ECS）
  - [ ] CDB分析器（对应RDS）
  - [ ] Redis分析器
  - [ ] COS分析器（对应OSS）
  - [ ] CLB分析器（对应SLB）
  - [ ] EIP分析器
- [ ] CLI更新
  - [ ] 支持 `python main.py tencent ...`
  - [ ] 保持向后兼容

**验收标准**:
- ✅ 腾讯云4个核心产品可分析
- ✅ 报告明确标识云厂商
- ✅ 老命令仍然可用

---

### Phase 4: 高级功能（3-4周）

**目标**: 多云对比 + 智能分析

**任务清单**:
- [ ] 多云对比分析
  - [ ] 实现 `--compare` 选项
  - [ ] 对比报告模板
  - [ ] 成本对比分析
- [ ] 趋势分析
  - [ ] 历史数据对比
  - [ ] 趋势图表生成
  - [ ] 成本预测
- [ ] 报告增强
  - [ ] 优化优先级评分
  - [ ] 潜在节省预测
  - [ ] 交互式HTML报告
- [ ] 自动化通知
  - [ ] 邮件通知
  - [ ] Webhook通知
  - [ ] Slack/钉钉集成
- [ ] 测试完善
  - [ ] 单元测试（覆盖率>60%）
  - [ ] 集成测试
  - [ ] 性能测试

**验收标准**:
- ✅ 可对比阿里云和腾讯云
- ✅ 趋势分析可用
- ✅ 自动化通知可用
- ✅ 测试覆盖率>60%

---

### Phase 5: 生态完善（按需）

**目标**: AWS/华为云 + 高级特性

**任务清单**:
- [ ] AWS支持
  - [ ] EC2、RDS、S3等
- [ ] 华为云支持
  - [ ] ECS、RDS、OBS等
- [ ] Web界面（可选）
  - [ ] Flask/FastAPI后端
  - [ ] Vue.js前端
- [ ] API接口（可选）
  - [ ] RESTful API
  - [ ] OpenAPI文档

---

## 9. 技术债务与注意事项

### 9.1 关键决策

| 决策点 | 推荐方案 | 理由 |
|--------|---------|------|
| CLI框架 | **Click** | 功能完善、易用性好 |
| 密钥管理 | **Keyring** | 系统级安全、用户体验佳 |
| 并发方式 | **ThreadPoolExecutor** | 实现简单、效果明显 |
| 配置格式 | **JSON + YAML** | JSON主配置、YAML阈值 |
| 数据库 | **SQLite** | 轻量级、无需额外部署 |
| 日志 | **logging** | Python标准库 |
| 测试 | **pytest** | 功能强大、生态完善 |

### 9.2 API限流注意

各云厂商API调用限制：
- **阿里云**:
  - ECS API: 20次/秒
  - 监控API: 600次/分钟
- **腾讯云**:
  - CVM API: 20次/秒
  - 监控API: 20次/秒

**建议**:
- 并发数不超过10
- 添加速率限制器
- 监控API调用次数

### 9.3 成本控制

**监控API费用**:
- 阿里云: ¥0.022/1000次
- 100实例 × 18指标 × 14天数据点 = 约25200次 ≈ ¥0.55

**建议**:
- 合理设置缓存时间（24小时）
- 避免频繁全量扫描
- 生产环境每天1次即可

### 9.4 兼容性要求

- **Python版本**: 3.7+
- **操作系统**: macOS / Windows / Linux
- **依赖隔离**: 使用虚拟环境

### 9.5 数据一致性

多云对比时注意：
- 不同云的时间戳格式
- 不同云的指标单位（MB/GB/TB）
- 货币单位统一（CNY/USD）

---

## 10. 依赖包清单

```txt
# requirements.txt

# ===== 阿里云SDK =====
aliyun-python-sdk-core>=2.16.0
aliyun-python-sdk-ecs>=4.24.0
aliyun-python-sdk-cms>=7.0.0
aliyun-python-sdk-rds>=2.3.0
aliyun-python-sdk-r-kvstore>=2.20.0
aliyun-python-sdk-dds>=2.0.0
aliyun-python-sdk-vpc>=3.0.0        # VPC相关（EIP、NAT等）
aliyun-python-sdk-slb>=3.3.0        # SLB负载均衡

# ===== 腾讯云SDK（Phase 3）=====
# tencentcloud-sdk-python>=3.0.0

# ===== AWS SDK（Phase 5）=====
# boto3>=1.26.0

# ===== 数据处理 =====
pandas>=1.3.0
openpyxl>=3.0.0

# ===== 密钥管理 =====
keyring>=23.0.0
cryptography>=41.0.0                # 备用加密方案

# ===== CLI框架 =====
click>=8.1.0

# ===== 配置管理 =====
PyYAML>=6.0

# ===== 重试机制 =====
tenacity>=8.2.0

# ===== 异步支持（可选）=====
# aiohttp>=3.8.0

# ===== 日志 =====
# python-json-logger>=2.0.0

# ===== 测试 =====
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0

# ===== 代码质量（可选）=====
# black>=23.0.0
# flake8>=6.0.0
# mypy>=1.0.0
```

---

## 11. 核心原则

1. **向后兼容优先**: 老命令必须继续可用
2. **渐进式重构**: 分阶段进行，避免大规模改动
3. **插件化架构**: 云厂商作为独立插件，便于扩展
4. **配置驱动**: 阈值、区域等都可外部配置
5. **安全第一**: 密钥绝不明文存储
6. **用户友好**: 命令简洁、提示清晰、自动化程度高
7. **性能优先**: 并发处理、缓存机制、避免重复调用

---

## 12. 快速开始

### 12.1 立即可以做的事

1. **创建基础目录结构**
```bash
mkdir -p core clouds/aliyun/resources clouds/tencent/resources utils templates data/cache data/db logs tests
```

2. **安装新依赖**
```bash
pip install keyring click tenacity PyYAML pytest
```

3. **创建配置文件**
```bash
# 创建 thresholds.yaml
# 参考本文档第3.4节
```

4. **实现第一个优化**
```python
# 实现 utils/concurrent_helper.py
# 参考本文档第3.2节
```

### 12.2 验证环境

```bash
# 测试Keyring
python -c "import keyring; print(keyring.get_keyring())"

# 测试Click
python -c "import click; print(click.__version__)"

# 测试Tenacity
python -c "import tenacity; print(tenacity.__version__)"
```

---

## 附录

### A. 术语表

| 术语 | 说明 |
|------|------|
| CRU | Capacity Resource Utilization（资源利用率） |
| EIP | Elastic IP（弹性公网IP） |
| SLB | Server Load Balancer（负载均衡） |
| ALB | Application Load Balancer（应用负载均衡） |
| NAT | Network Address Translation（网络地址转换） |
| VPN | Virtual Private Network（虚拟专用网络） |
| ACK | Alibaba Cloud Container Service for Kubernetes |
| ACR | Alibaba Cloud Container Registry |
| Keyring | 操作系统密钥环服务 |
| PBKDF2 | Password-Based Key Derivation Function 2 |

### B. 参考资源

- [阿里云API文档](https://help.aliyun.com/product/25365.html)
- [腾讯云API文档](https://cloud.tencent.com/document/api)
- [Click框架文档](https://click.palletsprojects.com/)
- [Keyring库文档](https://pypi.org/project/keyring/)
- [Tenacity重试库](https://tenacity.readthedocs.io/)

---

**文档版本**: v1.0
**最后更新**: 2025年
**适用项目**: aliyunidle → multicloud-analyzer
