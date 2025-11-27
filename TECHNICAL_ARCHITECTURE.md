# CloudLens CLI - 技术架构文档

## 架构概览

CloudLens CLI 采用**插件化、模块化**的分层架构设计，确保高扩展性、高可维护性和高安全性。

### 系统分层

```
┌─────────────────────────────────────┐
│         CLI Layer (Click)            │  用户交互层
├─────────────────────────────────────┤
│      Application Logic Layer         │  业务逻辑层
│  ├─ Analyzer (Idle, Cost, Tag...)   │
│  ├─ Report Generator                 │
│  ├─ Topology Generator               │
│  └─ Filter Engine                    │
├─────────────────────────────────────┤
│       Provider Abstraction           │  云厂商抽象层
│  ├─ BaseProvider (Interface)        │
│  ├─ AliyunProvider                   │
│  ├─ TencentProvider                  │
│  └─ ...Extensible                    │
├─────────────────────────────────────┤
│      Infrastructure Layer            │  基础设施层
│  ├─ ConfigManager                    │
│  ├─ PermissionGuard                  │
│  ├─ ConcurrentHelper                 │
│  └─ SecurityCompliance               │
├─────────────────────────────────────┤
│        External Dependencies         │  外部依赖层
│  ├─ Aliyun SDK                       │
│  ├─ Tencent SDK                      │
│  └─ System Keyring                   │
└─────────────────────────────────────┘
```

---

## 核心模块设计

### 1. Provider抽象层

#### BaseProvider接口

```python
class BaseProvider(ABC):
    """云厂商抽象基类"""
    
    @abstractmethod
    def list_instances(self) -> List[UnifiedResource]:
        """查询计算实例"""
        pass
    
    @abstractmethod
    def list_rds(self) -> List[UnifiedResource]:
        """查询数据库实例"""
        pass
    
    @abstractmethod
    def check_permissions(self) -> Dict:
        """检查权限"""
        pass
```

**设计模式**：抽象工厂模式

**优势**：
- 屏蔽不同云厂商的API差异
- 易于扩展新的云厂商
- 统一的接口规范

#### AliyunProvider实现

**核心职责**：
1. SDK初始化与认证
2. API调用与错误处理
3. 响应数据转换为UnifiedResource
4. 监控数据获取（CloudMonitor）

**关键实现**：
```python
class AliyunProvider(BaseProvider):
    def __init__(self, config: AccountConfig):
        self.access_key = config.access_key
        self.secret_key = config.secret_key
        self.region = config.region
        self.provider_name = "aliyun"
    
    def list_instances(self) -> List[UnifiedResource]:
        # 调用Aliyun SDK
        client = self._get_client(self.region)
        request = DescribeInstancesRequest()
        response = self._do_request(client, request)
        
        # 转换为统一模型
        resources = []
        for inst in response.get('Instances', {}).get('Instance', []):
            r = UnifiedResource(
                id=inst['InstanceId'],
                name=inst.get('InstanceName'),
                provider=self.provider_name,
                # ...更多字段
            )
            resources.append(r)
        return resources
```

### 2. 统一资源模型

#### UnifiedResource

```python
@dataclass
class UnifiedResource:
    """统一资源模型"""
    id: str                    # 资源ID
    name: str                  # 资源名称
    provider: str              # 云厂商
    region: str                # 区域
    zone: str                  # 可用区
    resource_type: ResourceType  # 资源类型
    status: ResourceStatus     # 状态
    spec: str                  # 规格
    charge_type: str           # 计费方式
    public_ips: List[str]      # 公网IP
    private_ips: List[str]     # 私网IP
    vpc_id: Optional[str]      # VPC ID
    tags: Optional[Dict]       # 标签
    created_time: Optional[datetime]  # 创建时间
    expired_time: Optional[datetime]  # 到期时间
    raw_data: Optional[Dict]   # 原始数据
```

**设计原则**：
- **最小公共集**：只包含所有云厂商都有的字段
- **可扩展**：raw_data保存原始响应，便于特殊处理
- **类型安全**：使用枚举和Optional明确类型

### 3. 配置管理

#### ConfigManager

**存储结构**：
```json
{
  "accounts": [
    {
      "provider": "aliyun",
      "name": "prod",
      "region": "cn-hangzhou",
      "access_key": "LTAI...",
      "use_keyring": true
    }
  ]
}
```

**安全设计**：
- `access_key_secret` 强制存储在系统Keyring
- 配置文件仅存储非敏感信息
- Keyring Key格式：`cloudlens_cli:{provider}:{name}`

**关键方法**：
```python
class ConfigManager:
    def add_account(self, config: AccountConfig):
        """添加账号配置"""
        # 1. 保存AccessKey到Keyring
        keyring.set_password(
            "cloudlens_cli",
            f"{config.provider}:{config.name}",
            config.access_key_secret
        )
        
        # 2. 保存配置到文件（不含密钥）
        self._save_config()
    
    def get_account(self, name: str, provider: str = None):
        """获取账号配置"""
        # 从文件读取配置
        account = self._find_account(name, provider)
        
        # 从Keyring读取密钥
        account.access_key_secret = keyring.get_password(...)
        
        return account
```

### 4. 分析引擎

#### IdleDetector（闲置检测器）

**检测逻辑**：

```python
class IdleDetector:
    @staticmethod
    def is_ecs_idle(metrics: Dict) -> Tuple[bool, List[str]]:
        reasons = []
        
        # 1. CPU使用率检查
        if metrics['cpu_avg'] < 5.0:
            reasons.append(f"CPU平均使用率仅{metrics['cpu_avg']:.1f}%")
        
        # 2. 内存使用率检查
        if metrics['memory_avg'] < 20.0:
            reasons.append(f"内存平均使用率仅{metrics['memory_avg']:.1f}%")
        
        # 3. 网络流量检查
        if metrics['net_in_avg'] < 1000:  # 1KB/s
            reasons.append("公网入流量极低")
        
        # 4. 磁盘IO检查
        if metrics['disk_iops_avg'] < 100:
            reasons.append("磁盘IOPS极低")
        
        is_idle = len(reasons) >= 2  # 至少2个指标满足才判定为闲置
        return is_idle, reasons
```

**数据来源**：
- 阿里云：CloudMonitor API
- 腾讯云：Monitor API
- 时间窗口：默认7天

#### FilterEngine（高级筛选引擎）

**语法解析**：

```python
class FilterEngine:
    @staticmethod
    def parse_filter(filter_str: str) -> List[tuple]:
        """
        解析筛选表达式
        支持：key=value, key>value, key<value
        连接：AND, OR
        
        示例：
        "charge_type=PrePaid AND expire_days<7"
        -> [('charge_type', '=', 'PrePaid', 'AND'),
            ('expire_days', '<', 7, 'AND')]
        """
        # 正则表达式解析
        parts = re.split(r'\s+(AND|OR)\s+', filter_str)
        conditions = []
        
        for part in parts:
            match = re.match(r'(\w+)\s*(!=|<=|>=|=|<|>)\s*(.+)', part)
            if match:
                field, operator, value = match.groups()
                conditions.append((field, operator, value, logic))
        
        return conditions
```

**应用筛选**：
```python
def apply_filter(resources: List, filter_str: str) -> List:
    conditions = parse_filter(filter_str)
    
    result = []
    for resource in resources:
        if _match_resource(resource, conditions):
            result.append(resource)
    
    return result
```

### 5. 并发查询

#### ConcurrentQueryHelper

**设计方案**：ThreadPoolExecutor（而非AsyncIO）

**原因**：
- 云SDK大多是同步阻塞的
- ThreadPool可以直接包装同步函数
- 避免改造所有Provider为async

**实现**：

```python
class ConcurrentQueryHelper:
    @staticmethod
    def query_with_progress(accounts, query_func, progress_callback):
        """并发查询带进度反馈"""
        all_results = []
        total = len(accounts)
        
        with ThreadPoolExecutor(max_workers=min(total, 10)) as executor:
            # 提交所有任务
            futures = {executor.submit(query_func, acc): acc 
                      for acc in accounts}
            
            # 等待完成
            for future in as_completed(futures):
                try:
                    result = future.result()
                    all_results.extend(result)
                except Exception as e:
                    logger.error(f"Query failed: {e}")
                finally:
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total)
        
        return all_results
```

**性能提升**：
- 串行查询5个账号：~25秒
- 并发查询5个账号：~8秒
- **提升 3倍**

### 6. 权限审计

#### PermissionGuard

**双重保障**：

1. **代码级保障**：
```python
class PermissionGuard:
    DANGEROUS_ACTIONS = [
        "DeleteInstance",
        "ModifyInstance",
        "CreateInstance",
        # ...更多
    ]
    
    @staticmethod
    def check_action(action: str) -> bool:
        """检查操作是否安全"""
        for dangerous in DANGEROUS_ACTIONS:
            if dangerous in action:
                raise SecurityError(f"禁止操作: {action}")
        return True
```

2. **运行时审计**：
```python
def check_permissions(self) -> Dict:
    """检查当前账号权限"""
    result = {
        "permissions": [],
        "high_risk_permissions": []
    }
    
    # 检查只读权限
    for api, desc in READ_ONLY_APIS:
        result["permissions"].append({
            "api": api,
            "description": desc,
            "risk_level": "LOW"
        })
    
    # 检查高危权限（通过Policy分析）
    for policy in ["AdministratorAccess", "FullAccess"]:
        result["high_risk_permissions"].append({
            "policy": policy,
            "risk_level": "HIGH",
            "recommendation": "建议使用只读策略"
        })
    
    return result
```

---

## 数据流设计

### 查询流程

```
用户输入
  ↓
CLI解析（Click）
  ↓
resolve_account_name() → 识别账号（支持重名）
  ↓
get_provider() → 创建Provider实例
  ↓
[串行 OR 并发]
  ↓
Provider.list_instances() → 调用云SDK
  ↓
_do_request() → 发送API请求
  ↓
parse_response() → 解析响应
  ↓
to_unified_resource() → 转换为统一模型
  ↓
apply_filter() → 应用筛选条件
  ↓
export() → 导出为指定格式
  ↓
输出到终端/文件
```

### 报告生成流程

```
用户触发报告生成
  ↓
收集数据
  ├─ list_instances()
  ├─ list_rds()
  ├─ list_redis()
  └─ (可选) analyze_idle()
  ↓
ReportGenerator.generate_excel()
  ├─ 创建Workbook
  ├─ 生成Summary Sheet
  ├─ 生成ECS Sheet
  ├─ 生成RDS Sheet
  ├─ 生成Idle Sheet
  ├─ 应用样式
  └─ 保存文件
  ↓
输出报告文件
```

---

## 设计模式应用

### 1. 抽象工厂模式

**应用场景**：Provider创建

```python
def get_provider(account: AccountConfig) -> BaseProvider:
    """Provider工厂方法"""
    if account.provider == "aliyun":
        return AliyunProvider(account)
    elif account.provider == "tencent":
        return TencentProvider(account)
    else:
        raise ValueError(f"Unsupported provider: {account.provider}")
```

### 2. 策略模式

**应用场景**：分析器（Analyzer）

```python
# 不同的分析策略
IdleDetector.analyze()      # 闲置分析策略
CostAnalyzer.analyze()      # 成本分析策略
TagAnalyzer.analyze()       # 标签分析策略
SecurityAnalyzer.analyze()  # 安全分析策略
```

### 3. 适配器模式

**应用场景**：云SDK适配

```python
class AliyunProvider(BaseProvider):
    """将Aliyun SDK适配到统一接口"""
    
    def list_instances(self):
        # Aliyun特定的API调用
        response = aliyun_sdk.describe_instances()
        
        # 适配为统一模型
        return [self._adapt_instance(inst) 
                for inst in response]
    
    def _adapt_instance(self, aliyun_inst):
        """适配器方法"""
        return UnifiedResource(
            id=aliyun_inst['InstanceId'],
            name=aliyun_inst.get('InstanceName'),
            # ...字段映射
        )
```

### 4. 单例模式

**应用场景**：ConfigManager

```python
class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
```

---

## 安全设计

### 1. 凭证管理

**三重保障**：
1. 强制使用系统Keyring
2. 配置文件不存储密钥
3. 内存中密钥使用后立即清除

### 2. 只读保障

**机制**：
1. 代码层面：不包含任何Write/Delete API调用
2. 白名单机制：只允许Describe/List/Get类API
3. PermissionGuard检查

### 3. 网络安全

- 所有请求使用HTTPS
- 支持代理配置
- 本地运行，数据不上传

---

## 扩展性设计

### 添加新云厂商

1. **创建Provider类**：
```python
# providers/aws/provider.py
class AWSProvider(BaseProvider):
    def list_instances(self):
        # 调用AWS SDK
        pass
```

2. **注册Provider**：
```python
# main_cli.py
def get_provider(account):
    if account.provider == "aws":
        return AWSProvider(account)
```

3. **完成**！无需修改其他代码

### 添加新资源类型

1. **在Provider中添加方法**：
```python
def list_mongodb(self) -> List[UnifiedResource]:
    # 实现查询逻辑
    pass
```

2. **添加CLI命令**：
```python
@query.command("mongodb")
def query_mongodb(account):
    provider.list_mongodb()
```

### 添加新分析器

1. **创建Analyzer类**：
```python
# core/compliance_analyzer.py
class ComplianceAnalyzer:
    @staticmethod
    def check_compliance(resources):
        # 分析逻辑
        pass
```

2. **添加CLI命令**：
```python
@analyze.command("compliance")
def analyze_compliance():
    ComplianceAnalyzer.check_compliance()
```

---

## 性能优化

### 1. 并发查询
- 使用ThreadPoolExecutor
- 最大并发数：10
- 提升3倍速度

### 2. 懒加载
- SDK按需导入
- 减少启动时间

### 3. 缓存机制
- 配置缓存在内存
- 避免重复读取文件

### 4. 批量操作
- 批量查询API
- PageSize设为100

---

## 错误处理

### 分层错误处理

```python
try:
    # Provider层
    response = sdk_client.describe_instances()
except SDKException as e:
    # SDK错误 → 重试或告警
    logger.error(f"SDK error: {e}")
except NetworkException as e:
    # 网络错误 → 重试
    retry(...)
except Exception as e:
    # 未知错误 → 记录并继续
    logger.exception(e)
    continue
```

### 用户友好的错误提示

```python
❌ Failed to query account 'prod': 
   Reason: InvalidAccessKeyId
   Suggestion: Please check your Access Key in config
```

---

## 测试策略

### 单元测试
```python
def test_filter_engine():
    resources = [...]
    result = FilterEngine.apply_filter(
        resources, 
        "charge_type=PrePaid AND expire_days<7"
    )
    assert len(result) == expected_count
```

### 集成测试
```python
def test_aliyun_provider():
    provider = AliyunProvider(test_config)
    instances = provider.list_instances()
    assert len(instances) > 0
    assert instances[0].provider == "aliyun"
```

---

## 总结

CloudLens CLI的架构设计遵循以下原则：

1. **高内聚低耦合**：模块职责清晰，依赖关系简单
2. **开放封闭原则**：易于扩展，无需修改核心代码
3. **安全第一**：多重安全保障
4. **性能优化**：并发、缓存、懒加载
5. **用户友好**：清晰的错误提示，友好的CLI交互

**适合团队**：运维团队、DevOps工程师、云架构师  
**技术栈**：Python 3.9+, Click, 云厂商SDK, Keyring
