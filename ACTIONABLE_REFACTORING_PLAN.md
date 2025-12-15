# CloudLens 可执行重构计划

> 📅 制定时间: 2025-12-15  
> 🎯 目标: 提供清晰的、可落地的重构任务清单  
> ⏰ 预估总工时: 2-3周（分阶段执行）

---

## 📋 任务总览

| 阶段 | 任务数 | 预估工时 | 优先级 | 状态 |
|------|--------|----------|--------|------|
| Phase 0: 止血修复 | 5个 | 4-6小时 | 🔴 P0 | ⏳ 待开始 |
| Phase 1: 口径统一 | 4个 | 3-5天 | 🟡 P1 | ⏳ 待开始 |
| Phase 2: 缓存重构 | 3个 | 3-5天 | 🟡 P1 | ⏳ 待开始 |
| Phase 3: 功能增强 | 6个 | 1-2周 | 🟢 P2 | ⏳ 待开始 |

---

## 🔴 Phase 0: 止血修复（本周完成）

### 任务0.1: 修复 AliyunProvider.list_nas() bug 🔴

**问题**:
```python
# providers/aliyun/provider.py line 550
def list_nas(self) -> List[Dict]:
    for region in self.regions:  # ❌ self.regions未定义
        client = self._get_client(region)  # ❌ _get_client不接受参数
```

**影响**: NAS资源查询直接失败

**修复方案**:
```python
def list_nas(self) -> List[Dict]:
    """列出NAS文件系统"""
    nas_list = []
    try:
        from aliyunsdknas.request.v20170626 import DescribeFileSystemsRequest
        
        request = DescribeFileSystemsRequest.DescribeFileSystemsRequest()
        request.set_PageSize(100)
        response = self._do_request(request)
        
        for fs in response.get("FileSystems", {}).get("FileSystem", []):
            nas_list.append({
                "id": fs.get("FileSystemId"),
                "description": fs.get("Description", ""),
                "protocol_type": fs.get("ProtocolType"),
                "storage_type": fs.get("StorageType"),
                "status": fs.get("Status"),
                "region": self.region,  # 使用当前region
                "capacity": fs.get("Capacity", 0),
                "metered_size": fs.get("MeteredSize", 0),
            })
    except Exception as e:
        logger.error(f"Failed to list NAS: {e}")
    return nas_list
```

**验证方法**:
```bash
./cl query nas --account prod
```

**预估工时**: 30分钟

**责任人**: 后端开发

---

### 任务0.2: 统一 list_eip/list_eips 命名 🔴

**问题**: 
- AliyunProvider实现: `list_eip()`
- Web代码调用: `list_eips()`
- 导致EIP功能在Web端默默失效

**影响文件**:
- `providers/aliyun/provider.py` (定义)
- `web/backend/api.py` (调用)
- 文档、注释

**修复方案**:
```bash
# Step 1: 重命名函数
def list_eip() -> def list_eips()

# Step 2: 更新所有调用
grep -r "list_eip()" --include="*.py" | grep -v "list_eips"

# Step 3: 运行测试
pytest tests/ -k eip
```

**验证方法**:
```bash
# CLI测试
./cl query eip --account prod

# Web测试
curl "http://127.0.0.1:8000/api/resources?type=eip&account=prod"
```

**预估工时**: 30分钟

**责任人**: 后端开发

---

### 任务0.3: 重命名 cache_manager.py 避免冲突 🔴

**问题**: 
- `core/cache.py` (CacheManager) - SQLite缓存
- `core/cache_manager.py` (CacheManager) - 文件缓存
- 同名导致import混乱

**修复方案**:
```bash
# Step 1: 重命名文件
git mv core/cache_manager.py core/file_cache_manager.py

# Step 2: 更新类名
class CacheManager -> class FileCacheManager

# Step 3: 更新所有import
find . -name "*.py" -exec sed -i '' 's/from core.cache_manager import CacheManager/from core.file_cache_manager import FileCacheManager/g' {} \;

# Step 4: 更新引用
# core/base_analyzer.py
# tests/core/test_cache_manager.py
```

**影响文件**:
- `core/base_analyzer.py`
- `tests/core/test_cache_manager.py`
- 可能的旧脚本

**验证方法**:
```bash
# 检查import
grep -r "from core.cache_manager import" --include="*.py"

# 运行测试
pytest tests/core/test_cache_manager.py
```

**预估工时**: 1小时

**责任人**: 后端开发

---

### 任务0.4: 补全 config show 命令输出 🟡

**问题**:
```python
# cli/commands/config_cmd.py line 152
def show_account(name):
    ...
    info = f"""..."""  # 构造了info但未输出
    # ❌ 缺少: console.print(Panel.fit(info, title=...))
```

**修复方案**:
```python
def show_account(name):
    """显示账号详细信息"""
    cm = ConfigManager()
    account = cm.get_account(name)

    if not account:
        console.print(f"[red]错误: 账号 '{name}' 不存在[/red]")
        return

    from rich.panel import Panel

    info = f"""
[bold cyan]账号名称:[/bold cyan] {account.name}
[bold cyan]云厂商:[/bold cyan] {account.provider}
[bold cyan]默认区域:[/bold cyan] {account.region}
[bold cyan]Access Key:[/bold cyan] {account.access_key_id[:8]}...{account.access_key_id[-4:]}
    """
    
    # ✅ 添加输出
    console.print(Panel.fit(info.strip(), title=f"☁️ 账号信息: {name}", border_style="cyan"))
```

**验证方法**:
```bash
./cl config show prod
```

**预估工时**: 15分钟

**责任人**: 前端开发/文档

---

### 任务0.5: 运行完整测试套件 🟡

**目标**: 确保当前代码质量基线

**执行步骤**:
```bash
# 1. 运行所有单元测试
pytest tests/ -v --cov=core --cov=providers --cov-report=html

# 2. 代码质量检查
flake8 core/ cli/ providers/ --max-line-length=120

# 3. 类型检查
mypy core/ --ignore-missing-imports

# 4. 安全检查
bandit -r core/ providers/ -ll
```

**预期结果**:
- 测试覆盖率 > 70%
- 无Critical级别的lint错误
- 无Security风险

**问题修复**:
- 补充缺失的单元测试
- 修复lint错误
- 更新类型注解

**预估工时**: 2-3小时

**责任人**: QA + 开发

---

## 🟡 Phase 1: 数据口径统一（下周完成）

### 任务1.1: 统一成本数据来源优先级 🟡

**目标**: 所有成本数据优先使用BSS账单，降级到估算

**修改点**:

**1. 定义统一的成本获取函数**:
```python
# core/cost_service.py (新建)

class CostService:
    @staticmethod
    def get_resource_cost(
        resource_id: str,
        resource_type: str,
        account_config: CloudAccount,
        billing_cycle: Optional[str] = None
    ) -> Dict:
        """
        统一的成本获取接口
        
        返回:
        {
            "cost": 1234.56,
            "source": "bss_billing",  # 或 "csv_bill" 或 "estimated"
            "confidence": 0.95,  # 准确度
            "billing_cycle": "2025-12"
        }
        """
        # 优先级1: BSS账单API
        try:
            cost = _get_cost_from_bss(resource_id, resource_type, account_config)
            if cost:
                return {"cost": cost, "source": "bss_billing", "confidence": 0.95}
        except:
            pass
        
        # 优先级2: 账单CSV（如果有）
        try:
            cost = _get_cost_from_csv(resource_id, resource_type)
            if cost:
                return {"cost": cost, "source": "csv_bill", "confidence": 0.90}
        except:
            pass
        
        # 优先级3: 规格估算
        cost = _estimate_cost_from_spec(resource_type, spec)
        return {"cost": cost, "source": "estimated", "confidence": 0.60}
```

**2. 更新所有调用点**:
- `web/backend/api.py` - 资源列表、详情
- `core/cost_trend_analyzer.py` - 快照记录
- `core/optimization_engine.py` - 建议计算

**3. 前端显示数据来源**:
```typescript
// 在成本卡片上显示数据源标识
<Badge variant={costSource === 'bss_billing' ? 'success' : 'warning'}>
  {costSource === 'bss_billing' ? '账单' : '估算'}
</Badge>
```

**验证方法**:
```bash
# CLI显示数据来源
./cl query ecs --account prod --show-cost-source

# Web检查响应
curl "http://127.0.0.1:8000/api/resources/i-xxx"
# 响应应包含 "cost_source" 字段
```

**预估工时**: 2-3天

**责任人**: 后端开发 + 前端开发

---

### 任务1.2: 折扣数据融入成本分析 ✨

**目标**: 在成本分析中展示折扣信息

**实现点**:

**1. Dashboard增强**:
```typescript
// 添加折扣卡片
<Card>
  <h3>月度折扣</h3>
  <p className="text-3xl">52.68%</p>
  <p className="text-sm">
    <TrendingUp className="inline" />
    环比 +2.5%
  </p>
</Card>
```

**2. 资源详情页**:
```typescript
// 显示实例级折扣
<div className="cost-breakdown">
  <div>官网价: ¥1,000.00</div>
  <div>折扣: -¥500.00 (50%)</div>
  <div>实付: ¥500.00</div>
</div>
```

**3. 成本分析页**:
```typescript
// 折扣趋势集成到成本图表
<ComposedChart>
  <Line dataKey="cost" stroke="#8884d8" />
  <Line dataKey="savings" stroke="#82ca9d" />  // 新增
  <Bar dataKey="discount_rate" fill="#ffc658" />  // 新增
</ComposedChart>
```

**预估工时**: 2天

**责任人**: 前端开发

---

### 任务1.3: 创建折扣分析前端页面 ✨

**目标**: 在Web端展示折扣趋势分析

**页面路由**: `app/discounts/page.tsx`

**页面结构**:
```typescript
// web/frontend/app/discounts/page.tsx

export default function DiscountsPage() {
  return (
    <div>
      {/* 核心指标卡片 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="最新折扣率" value="57.43%" trend="+6.85%" />
        <StatCard title="平均折扣率" value="52.68%" />
        <StatCard title="折扣趋势" value="上升" />
        <StatCard title="累计节省" value="¥258万" />
      </div>
      
      {/* 折扣率趋势图 */}
      <Card>
        <h2>折扣率变化趋势</h2>
        <LineChart data={discountTrendData} />
      </Card>
      
      {/* 产品折扣对比表格 */}
      <Card>
        <h2>产品折扣分析 (TOP 20)</h2>
        <Table
          columns={['产品', '累计折扣', '平均折扣率', '趋势']}
          data={productDiscounts}
          sortable
        />
      </Card>
      
      {/* 合同效果分析 */}
      <Card>
        <h2>合同折扣效果 (TOP 10)</h2>
        <Table
          columns={['合同编号', '优惠名称', '累计节省', '平均折扣率']}
          data={contractDiscounts}
        />
      </Card>
      
      {/* TOP实例折扣 */}
      <Card>
        <h2>高折扣实例 (TOP 50)</h2>
        <Table
          columns={['实例ID', '产品', '官网价', '折扣金额', '折扣率']}
          data={topInstanceDiscounts}
          pagination
        />
      </Card>
    </div>
  )
}
```

**API集成**:
```typescript
// lib/api.ts

export async function getDiscountTrend(months = 6) {
  const response = await fetch(
    `/api/discounts/trend?months=${months}`
  )
  return response.json()
}

export async function getProductDiscounts(product?: string) {
  const url = product 
    ? `/api/discounts/products?product=${product}`
    : `/api/discounts/products`
  const response = await fetch(url)
  return response.json()
}
```

**组件需求**:
- StatCard（已有）
- LineChart（基于Recharts）
- Table（已有，需增强排序）

**预估工时**: 1-2天

**责任人**: 前端开发

---

### 任务1.4: 补充折扣分析单元测试 🟢

**目标**: 确保折扣分析模块稳定性

**测试文件**: `tests/core/test_discount_analyzer.py`

**测试用例**:
```python
# tests/core/test_discount_analyzer.py

import pytest
from core.discount_analyzer import DiscountTrendAnalyzer
from pathlib import Path

class TestDiscountTrendAnalyzer:
    
    def test_parse_bill_csv(self):
        """测试CSV解析"""
        analyzer = DiscountTrendAnalyzer()
        csv_path = Path("./1844634015852583-ydzn/xxx.csv")
        records = analyzer.parse_bill_csv(csv_path)
        assert len(records) > 0
        assert "billing_period" in records[0]
    
    def test_aggregate_monthly(self):
        """测试按月聚合"""
        # ...
    
    def test_trend_analysis(self):
        """测试趋势分析"""
        # ...
    
    def test_cache_mechanism(self):
        """测试缓存机制"""
        # ...
```

**覆盖率目标**: > 80%

**预估工时**: 1天

**责任人**: QA + 开发

---

## 🟡 Phase 1: 数据口径统一（第2周）

### 任务1.5: 成本趋势切换到BSS口径 🟡

**目标**: `cost_trend_analyzer.py` 使用真实账单而非估算

**修改方案**:
```python
# core/cost_trend_analyzer.py

def record_cost_snapshot(self, account_name, resources, timestamp=None):
    """记录成本快照（优先使用BSS账单）"""
    
    # 优先级1: BSS账单（最准确）
    try:
        from web.backend.api import _get_billing_overview_totals
        account_config = ConfigManager().get_account(account_name)
        totals = _get_billing_overview_totals(account_config)
        
        total_cost = totals.get("total_pretax", 0)
        cost_by_type = totals.get("by_product", {})
        
        # 区域分布需要单独查询或从资源列表聚合
        cost_by_region = self._aggregate_cost_by_region(resources, account_config)
        
    except Exception as e:
        logger.warning(f"Failed to get BSS billing, falling back to estimation: {e}")
        # 降级到估算
        total_cost = sum(self._estimate_resource_cost(r) for r in resources)
        cost_by_type = self._aggregate_by_type(resources)
        cost_by_region = self._aggregate_by_region(resources)
    
    snapshot = {
        "timestamp": timestamp.isoformat(),
        "account": account_name,
        "total_cost": round(total_cost, 2),
        "cost_by_type": cost_by_type,
        "cost_by_region": cost_by_region,
        "resource_count": len(resources),
        "cost_source": "bss_billing" if "BSS" in locals() else "estimated",  # 新增
    }
    
    self._append_snapshot(snapshot)
    return snapshot
```

**影响范围**:
- CLI `analyze cost` 命令
- Web Dashboard趋势图
- AI成本预测（训练数据更准确）

**验证方法**:
```bash
# 记录快照
./cl analyze cost --account prod

# 查看历史
cat ./data/cost/cost_history.json | jq '.[-1]'
# 应包含 "cost_source": "bss_billing"
```

**预估工时**: 1-2天

**责任人**: 后端开发

---

## 🟢 Phase 2: 缓存体系重构（第3周）

### 任务2.1: 废弃旧文件缓存 🟢

**目标**: 完全移除 `core/cache_manager.py` 依赖

**步骤**:
```bash
# 1. 确认无遗漏引用
grep -r "from core.cache_manager import\|from core.file_cache_manager import" --include="*.py"

# 2. 迁移 base_analyzer.py
# 将 FileCacheManager 替换为 SQLite CacheManager

# 3. 移动到legacy
mkdir -p legacy/
git mv core/file_cache_manager.py legacy/
git mv core/base_analyzer.py legacy/  # 如果不再使用

# 4. 更新文档
# 在README中标注旧缓存已废弃
```

**清理文件**:
```bash
# 删除旧缓存文件
rm -rf ./data/cache/*.pkl
```

**预估工时**: 半天

**责任人**: 后端开发

---

### 任务2.2: SQLite缓存增强 🟢

**功能增强**:

**1. 添加缓存统计API**:
```python
# core/cache.py

class CacheManager:
    def get_statistics(self) -> Dict:
        """获取缓存统计信息"""
        return {
            "total_entries": ...,
            "valid_entries": ...,
            "expired_entries": ...,
            "total_size_mb": ...,
            "hit_rate": ...,  # 需要记录命中/未命中次数
            "by_resource_type": {...},
        }
```

**2. 添加自动清理任务**:
```python
# 定时清理过期缓存（每天凌晨）
# 可以集成到 scheduler_daemon.py
def cleanup_expired_cache():
    cache = CacheManager()
    deleted = cache.cleanup_expired()
    logger.info(f"Cleaned up {deleted} expired cache entries")
```

**3. 添加缓存预热**:
```python
def warm_up_cache(account_name: str):
    """预热常用资源的缓存"""
    provider = get_provider(account_name)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            'ecs': executor.submit(provider.list_instances),
            'rds': executor.submit(provider.list_rds),
            'redis': executor.submit(provider.list_redis),
        }
        
        for res_type, future in futures.items():
            try:
                data = future.result()
                cache.set(res_type, account_name, data)
            except:
                pass
```

**预估工时**: 1-2天

**责任人**: 后端开发

---

## 🟢 Phase 3: 功能增强（第4周起）

### 任务3.1: 折扣分析增强 ✨

**目标**: 增强折扣分析功能

**功能点**:

**1. 折扣率预警**:
```python
# core/discount_analyzer.py

def check_discount_alerts(self, analysis: Dict) -> List[Dict]:
    """检查折扣异常（预警）"""
    alerts = []
    
    trend = analysis['trend_analysis']
    
    # 预警1: 折扣率下降 > 5%
    if trend['discount_rate_change'] < -0.05:
        alerts.append({
            "level": "WARNING",
            "type": "discount_decrease",
            "message": f"折扣率下降 {trend['discount_rate_change_pct']:.2f}%",
            "recommendation": "建议与商务沟通合同续签事宜"
        })
    
    # 预警2: 产品折扣率异常低
    for product, data in analysis['product_analysis'].items():
        if data['latest_discount_rate'] < 0.3 and data['total_discount'] > 10000:
            alerts.append({
                "level": "INFO",
                "type": "low_discount_product",
                "message": f"{product} 折扣率仅 {data['latest_discount_rate']*100:.1f}%",
                "recommendation": "考虑优化采购策略或与商务协商"
            })
    
    return alerts
```

**2. 折扣优化建议**:
```python
def suggest_discount_optimization(self, analysis: Dict) -> List[str]:
    """折扣优化建议"""
    suggestions = []
    
    # 建议1: 批量续费
    # 建议2: 合同续签
    # 建议3: 采购策略调整
    
    return suggestions
```

**预估工时**: 1-2天

**责任人**: 后端开发

---

### 任务3.2: 监控数据批量获取优化 🟢

**目标**: 闲置分析性能提升10倍

**当前问题**:
- 逐个实例调用 `get_metric()`（6次/实例）
- 100实例 = 600次API调用
- 耗时: 60秒+

**优化方案**:
```python
# providers/aliyun/provider.py

def get_metrics_batch(
    self,
    instance_ids: List[str],
    metric_names: List[str],
    start_time: int,
    end_time: int
) -> Dict[str, Dict[str, float]]:
    """
    批量获取监控指标
    
    CloudMonitor支持一次查询最多200个维度
    
    Returns:
        {
            'i-001': {'CPUUtilization': 3.5, 'memory_usedutilization': 15.2},
            'i-002': {...}
        }
    """
    results = {}
    
    # 分批处理（每批50个实例×6指标=300维度）
    batch_size = 50
    for i in range(0, len(instance_ids), batch_size):
        batch_ids = instance_ids[i:i+batch_size]
        
        for metric_name in metric_names:
            # 构造批量Dimensions
            dimensions = [
                {"instanceId": inst_id}
                for inst_id in batch_ids
            ]
            
            # 调用批量API
            response = self._batch_describe_metric_data(
                metric_name, dimensions, start_time, end_time
            )
            
            # 解析结果
            for dp in response:
                inst_id = dp['instanceId']
                if inst_id not in results:
                    results[inst_id] = {}
                results[inst_id][metric_name] = dp['Average']
    
    return results
```

**更新调用**:
```python
# core/idle_detector.py

@staticmethod
def fetch_ecs_metrics_batch(provider, instance_ids, days=14):
    """批量获取监控指标"""
    end_time = int(time.time() * 1000)
    start_time = end_time - (days * 24 * 60 * 60 * 1000)
    
    metric_names = [
        "CPUUtilization",
        "memory_usedutilization",
        "InternetInRate",
        "InternetOutRate",
        "disk_readiops",
        "disk_writeiops",
    ]
    
    return provider.get_metrics_batch(instance_ids, metric_names, start_time, end_time)
```

**预期效果**:
- API调用次数: 600次 → 12次（50倍减少）
- 耗时: 60秒 → 5-10秒（6-12倍提升）

**预估工时**: 2-3天

**责任人**: 后端开发

---

### 任务3.3: 优化引擎切换到实时模式 🟢

**目标**: 移除本地DB依赖

**修改方案**:
```python
# core/optimization_engine.py

class OptimizationEngine:
    def __init__(self, mode='realtime'):
        """
        初始化优化引擎
        
        Args:
            mode: 'realtime' 从Provider实时获取（推荐）
                  'offline' 从本地DB读取（需要提前采集）
        """
        self.mode = mode
    
    def analyze_optimization_opportunities(self, account_name: str):
        if self.mode == 'realtime':
            return self._analyze_realtime(account_name)
        else:
            return self._analyze_offline(account_name)
    
    def _analyze_realtime(self, account_name: str):
        """实时分析（从Provider API）"""
        # 1. 获取闲置资源（从缓存）
        idle_data = CacheManager(ttl_seconds=86400).get("idle_result", account_name)
        
        # 2. 获取停止实例
        provider = get_provider(account_name)
        instances = provider.list_instances()
        stopped = [i for i in instances if i.status == ResourceStatus.STOPPED]
        
        # 3. 获取未绑定EIP
        eips = provider.list_eips()
        unbound_eips = [e for e in eips if not e.get("instance_id")]
        
        # 4. 生成优化建议
        opportunities = []
        # ... 基于上述数据生成建议
        
        return opportunities
```

**迁移策略**:
- 默认使用 `realtime` 模式
- 保留 `offline` 模式（向后兼容）
- 在文档中明确说明

**预估工时**: 2-3天

**责任人**: 后端开发

---

## 📊 执行时间表

```
第1周（12.16-12.22）
├── Day 1-2: Phase 0 止血修复（任务0.1-0.5）
├── Day 3-4: Phase 1 口径统一（任务1.1-1.2）
└── Day 5: 折扣前端页面（任务1.3开始）

第2周（12.23-12.29）
├── Day 1-2: 折扣前端页面完成（任务1.3）
├── Day 3: 补充测试（任务1.4）
└── Day 4-5: 成本口径重构（任务1.5）

第3周（12.30-01.05）
├── Day 1-2: 缓存体系重构（任务2.1-2.2）
└── Day 3-5: 功能增强（任务3.1-3.3开始）

第4周（01.06-01.12）
└── 功能增强完成 + 集成测试 + 文档更新
```

---

## ✅ 验收标准

### Phase 0 验收

- [ ] `./cl query nas` 能正常查询NAS资源
- [ ] `./cl query eip` Web端和CLI端均可用
- [ ] `grep "from core.cache_manager import"` 无结果
- [ ] `pytest tests/` 通过率 > 95%
- [ ] `./cl config show prod` 能正常显示账号信息

### Phase 1 验收

- [ ] Dashboard显示成本时标注数据来源（账单/估算）
- [ ] 折扣分析前端页面上线（`/discounts`）
- [ ] 成本数据与BSS账单差异 < 5%
- [ ] 单元测试覆盖率 > 80%

### Phase 2 验收

- [ ] 无 `./data/cache/*.pkl` 文件引用
- [ ] 缓存命中率统计可查（`./cl cache status --detailed`）
- [ ] 过期缓存自动清理（定时任务）

### Phase 3 验收

- [ ] 闲置分析耗时 < 10秒（100实例）
- [ ] 优化引擎默认使用实时模式
- [ ] 折扣率预警功能可用

---

## 📝 执行检查清单

### 开始前

- [ ] 备份当前代码（git tag v2.1.0-before-refactor）
- [ ] 创建开发分支（`git checkout -b refactor/phase-0`）
- [ ] 通知团队成员重构计划

### 每个任务完成后

- [ ] 运行相关单元测试
- [ ] 更新文档（如果有API变化）
- [ ] 提交代码（commit message遵循约定）
- [ ] Code Review（至少1人审查）

### Phase完成后

- [ ] 运行完整测试套件
- [ ] 更新CHANGELOG.md
- [ ] 合并到主分支
- [ ] 发布新版本（如果需要）

---

## 🚨 风险与应对

### 风险1: 重构影响生产环境

**应对**:
- 使用feature flag控制新功能
- 保留旧代码路径（向后兼容）
- 充分测试后再部署

### 风险2: BSS API权限不足

**应对**:
- 检测API权限，优雅降级到估算
- 在UI明确提示数据来源
- 提供配置指南

### 风险3: 性能回归

**应对**:
- 重构前后性能对比测试
- 保留性能基准数据
- 如有回归，回滚代码

---

## 📞 负责人与联系方式

| 角色 | 负责任务 | 联系方式 |
|------|----------|----------|
| 后端开发 | Phase 0-2 | - |
| 前端开发 | 折扣页面、UI增强 | - |
| QA | 测试、验收 | - |
| DevOps | 部署、监控 | - |

---

## 📚 参考文档

- [深度分析报告](PROJECT_DEEP_ANALYSIS.md)
- [架构图谱](ARCHITECTURE_DIAGRAM.md)
- [折扣分析指南](docs/DISCOUNT_ANALYSIS_GUIDE.md) ✨
- [产品概览](PRODUCT_OVERVIEW.md)

---

**计划制定时间**: 2025-12-15  
**状态**: ✅ 可执行  
**建议**: 按优先级顺序执行，Phase 0 本周必须完成
