# CloudLens Web - 实施计划

> **版本**: v1.0  
> **基于**: WEB_PRODUCT_DESIGN.md  
> **目标**: 详细的技术实施计划

---

## 📋 目录

1. [Phase 1: 基础增强](#phase-1-基础增强)
2. [Phase 2: 核心功能](#phase-2-核心功能)
3. [Phase 3: 高级功能](#phase-3-高级功能)
4. [代码示例](#代码示例)
5. [测试计划](#测试计划)

---

## Phase 1: 基础增强（2-3周）

### 1.1 Dashboard增强

#### 任务1.1.1: 添加更多摘要卡片

**前端实现** (`web/frontend/components/summary-cards.tsx`):

```typescript
// 扩展SummaryCards组件
interface SummaryProps {
    totalCost: number
    idleCount: number
    trend: string
    trendPct: number
    totalResources: number        // 新增
    resourceBreakdown: {          // 新增
        ecs: number
        rds: number
        redis: number
        // ...
    }
    alertCount: number            // 新增
    tagCoverage: number           // 新增
    savingsPotential: number      // 新增
}

export function SummaryCards({ ... }: SummaryProps) {
    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
            {/* 现有卡片 */}
            <Card>总成本</Card>
            <Card>成本趋势</Card>
            <Card>闲置资源</Card>
            
            {/* 新增卡片 */}
            <Card>
                <CardTitle>资源总数</CardTitle>
                <div className="text-2xl font-bold">{totalResources}</div>
                <div className="text-xs text-muted-foreground">
                    ECS: {resourceBreakdown.ecs} | RDS: {resourceBreakdown.rds}
                </div>
            </Card>
            
            <Card>
                <CardTitle>告警数量</CardTitle>
                <div className="text-2xl font-bold text-orange-500">{alertCount}</div>
            </Card>
            
            <Card>
                <CardTitle>标签覆盖率</CardTitle>
                <div className="text-2xl font-bold">{tagCoverage}%</div>
            </Card>
        </div>
    )
}
```

**后端实现** (`web/backend/api.py`):

```python
@router.get("/dashboard/summary")
def get_summary(account: Optional[str] = None):
    # ... 现有代码 ...
    
    # 新增：资源统计
    provider = get_provider(account_config)
    instances = provider.list_instances()
    rds_list = provider.list_rds()
    redis_list = provider.list_redis()
    
    resource_breakdown = {
        "ecs": len(instances),
        "rds": len(rds_list),
        "redis": len(redis_list),
    }
    total_resources = sum(resource_breakdown.values())
    
    # 新增：告警数量（简化实现）
    alert_count = 0  # TODO: 实现告警统计
    
    # 新增：标签覆盖率
    tagged_count = sum(1 for inst in instances if inst.tags)
    tag_coverage = (tagged_count / len(instances) * 100) if instances else 0
    
    # 新增：节省潜力（基于闲置资源估算）
    savings_potential = idle_count * 500  # 简化估算
    
    return {
        "account": account,
        "total_cost": total_cost,
        "idle_count": idle_count,
        "cost_trend": trend,
        "trend_pct": trend_pct,
        "total_resources": total_resources,        # 新增
        "resource_breakdown": resource_breakdown,   # 新增
        "alert_count": alert_count,                # 新增
        "tag_coverage": round(tag_coverage, 2),    # 新增
        "savings_potential": savings_potential,   # 新增
    }
```

#### 任务1.1.2: 成本图表时间范围选择

**前端实现** (`web/frontend/components/cost-chart.tsx`):

```typescript
export function CostChart({ data }: { data: ChartData }) {
    const [days, setDays] = useState(30)
    
    useEffect(() => {
        // 重新获取数据
        fetch(`/api/dashboard/trend?account=${account}&days=${days}`)
            .then(res => res.json())
            .then(data => setChartData(data.chart_data))
    }, [days])
    
    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle>成本趋势</CardTitle>
                        <CardDescription>过去 {days} 天的日成本变化</CardDescription>
                    </div>
                    <div className="flex gap-2">
                        {[7, 30, 90].map(d => (
                            <button
                                key={d}
                                onClick={() => setDays(d)}
                                className={`px-3 py-1 rounded text-sm ${
                                    days === d 
                                        ? 'bg-primary text-primary-foreground' 
                                        : 'bg-muted text-muted-foreground'
                                }`}
                            >
                                {d}天
                            </button>
                        ))}
                    </div>
                </div>
            </CardHeader>
            {/* 图表内容 */}
        </Card>
    )
}
```

#### 任务1.1.3: 闲置资源表格增强

**前端实现** (`web/frontend/components/idle-table.tsx`):

```typescript
export function IdleTable({ data }: { data: IdleInstance[] }) {
    const [search, setSearch] = useState("")
    const [sortBy, setSortBy] = useState<"name" | "region" | "spec">("name")
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc")
    
    const filtered = data
        .filter(item => 
            item.name.toLowerCase().includes(search.toLowerCase()) ||
            item.instance_id.toLowerCase().includes(search.toLowerCase())
        )
        .sort((a, b) => {
            const aVal = a[sortBy]
            const bVal = b[sortBy]
            return sortOrder === "asc" 
                ? aVal.localeCompare(bVal)
                : bVal.localeCompare(aVal)
        })
    
    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle>闲置资源</CardTitle>
                        <CardDescription>共发现 {data.length} 个闲置实例</CardDescription>
                    </div>
                    <input
                        type="text"
                        placeholder="搜索..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="px-3 py-1 rounded border border-input bg-transparent"
                    />
                </div>
            </CardHeader>
            <CardContent>
                <table>
                    <thead>
                        <tr>
                            <th 
                                onClick={() => {
                                    setSortBy("name")
                                    setSortOrder(sortOrder === "asc" ? "desc" : "asc")
                                }}
                                className="cursor-pointer"
                            >
                                ID / Name {sortBy === "name" && (sortOrder === "asc" ? "↑" : "↓")}
                            </th>
                            {/* 其他列 */}
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map(item => (
                            <tr key={item.instance_id}>
                                <td>
                                    <a 
                                        href={`/resources/${item.instance_id}`}
                                        className="text-primary hover:underline"
                                    >
                                        {item.name}
                                    </a>
                                </td>
                                {/* 其他列 */}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </CardContent>
        </Card>
    )
}
```

### 1.2 资源管理基础

#### 任务1.2.1: 资源列表页面

**前端实现** (`web/frontend/app/resources/page.tsx`):

```typescript
export default function ResourcesPage() {
    const [resources, setResources] = useState([])
    const [loading, setLoading] = useState(true)
    const [resourceType, setResourceType] = useState("ecs")
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(20)
    
    useEffect(() => {
        fetch(`/api/resources?type=${resourceType}&page=${page}&pageSize=${pageSize}`)
            .then(res => res.json())
            .then(data => {
                setResources(data.data)
                setLoading(false)
            })
    }, [resourceType, page, pageSize])
    
    return (
        <div>
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-3xl font-bold">资源管理</h1>
                <div className="flex gap-2">
                    {["ecs", "rds", "redis", "oss", "vpc"].map(type => (
                        <button
                            key={type}
                            onClick={() => setResourceType(type)}
                            className={`px-4 py-2 rounded ${
                                resourceType === type 
                                    ? 'bg-primary text-primary-foreground' 
                                    : 'bg-muted'
                            }`}
                        >
                            {type.toUpperCase()}
                        </button>
                    ))}
                </div>
            </div>
            
            {loading ? (
                <div>Loading...</div>
            ) : (
                <ResourceTable 
                    resources={resources} 
                    resourceType={resourceType}
                />
            )}
        </div>
    )
}
```

**后端实现** (`web/backend/api.py`):

```python
@router.get("/resources")
def list_resources(
    type: str = Query("ecs", description="资源类型"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    account: Optional[str] = None,
):
    """获取资源列表"""
    cm = ConfigManager()
    account_config = cm.get_account(account or get_default_account())
    provider = get_provider(account_config)
    
    # 根据类型获取资源
    if type == "ecs":
        resources = provider.list_instances()
    elif type == "rds":
        resources = provider.list_rds()
    elif type == "redis":
        resources = provider.list_redis()
    else:
        raise HTTPException(400, f"不支持的资源类型: {type}")
    
    # 分页
    total = len(resources)
    start = (page - 1) * pageSize
    end = start + pageSize
    paginated_resources = resources[start:end]
    
    # 转换为统一格式
    result = [
        {
            "id": r.id,
            "name": r.name,
            "type": type,
            "status": r.status.value,
            "region": r.region,
            "spec": r.spec,
            "cost": estimate_monthly_cost(r),  # 估算成本
            "tags": r.tags or {},
            "created_time": r.created_time.isoformat() if r.created_time else None,
        }
        for r in paginated_resources
    ]
    
    return {
        "success": True,
        "data": result,
        "pagination": {
            "page": page,
            "pageSize": pageSize,
            "total": total,
            "totalPages": (total + pageSize - 1) // pageSize,
        }
    }
```

#### 任务1.2.2: 资源详情页面

**前端实现** (`web/frontend/app/resources/[id]/page.tsx`):

```typescript
export default function ResourceDetailPage({ params }: { params: { id: string } }) {
    const [resource, setResource] = useState(null)
    const [metrics, setMetrics] = useState(null)
    const [loading, setLoading] = useState(true)
    
    useEffect(() => {
        Promise.all([
            fetch(`/api/resources/${params.id}`).then(r => r.json()),
            fetch(`/api/resources/${params.id}/metrics`).then(r => r.json()),
        ]).then(([resourceData, metricsData]) => {
            setResource(resourceData.data)
            setMetrics(metricsData.data)
            setLoading(false)
        })
    }, [params.id])
    
    if (loading) return <div>Loading...</div>
    
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold">{resource.name}</h1>
                <p className="text-muted-foreground">{resource.id}</p>
            </div>
            
            <div className="grid gap-6 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>基本信息</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <dl className="space-y-2">
                            <div>
                                <dt className="text-sm text-muted-foreground">类型</dt>
                                <dd>{resource.type}</dd>
                            </div>
                            <div>
                                <dt className="text-sm text-muted-foreground">状态</dt>
                                <dd>{resource.status}</dd>
                            </div>
                            <div>
                                <dt className="text-sm text-muted-foreground">区域</dt>
                                <dd>{resource.region}</dd>
                            </div>
                            <div>
                                <dt className="text-sm text-muted-foreground">规格</dt>
                                <dd>{resource.spec}</dd>
                            </div>
                        </dl>
                    </CardContent>
                </Card>
                
                <Card>
                    <CardHeader>
                        <CardTitle>监控数据</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {metrics && <MetricsChart data={metrics} />}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
```

**后端实现** (`web/backend/api.py`):

```python
@router.get("/resources/{resource_id}")
def get_resource(resource_id: str, account: Optional[str] = None):
    """获取资源详情"""
    cm = ConfigManager()
    account_config = cm.get_account(account or get_default_account())
    provider = get_provider(account_config)
    
    # 尝试从各种资源类型中查找
    resources = []
    resources.extend(provider.list_instances())
    resources.extend(provider.list_rds())
    resources.extend(provider.list_redis())
    
    resource = next((r for r in resources if r.id == resource_id), None)
    if not resource:
        raise HTTPException(404, "资源不存在")
    
    return {
        "success": True,
        "data": {
            "id": resource.id,
            "name": resource.name,
            "type": get_resource_type(resource),
            "status": resource.status.value,
            "region": resource.region,
            "spec": resource.spec,
            "cost": estimate_monthly_cost(resource),
            "tags": resource.tags or {},
            "created_time": resource.created_time.isoformat() if resource.created_time else None,
            "public_ips": resource.public_ips,
            "private_ips": resource.private_ips,
        }
    }

@router.get("/resources/{resource_id}/metrics")
def get_resource_metrics(
    resource_id: str, 
    days: int = Query(7, ge=1, le=30),
    account: Optional[str] = None,
):
    """获取资源监控数据"""
    # 实现监控数据获取
    # 调用 IdleDetector.fetch_ecs_metrics 或类似方法
    pass
```

### 1.3 UI组件完善

#### 任务1.3.1: Table组件

**前端实现** (`web/frontend/components/ui/table.tsx`):

```typescript
interface TableColumn<T> {
    key: string
    label: string
    sortable?: boolean
    render?: (value: any, row: T) => React.ReactNode
}

interface TableProps<T> {
    data: T[]
    columns: TableColumn<T>[]
    onSort?: (key: string, order: "asc" | "desc") => void
    onRowClick?: (row: T) => void
}

export function Table<T>({ data, columns, onSort, onRowClick }: TableProps<T>) {
    const [sortKey, setSortKey] = useState<string | null>(null)
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc")
    
    const handleSort = (key: string) => {
        if (sortKey === key) {
            setSortOrder(sortOrder === "asc" ? "desc" : "asc")
        } else {
            setSortKey(key)
            setSortOrder("asc")
        }
        onSort?.(key, sortOrder)
    }
    
    return (
        <div className="rounded-md border">
            <table className="w-full">
                <thead>
                    <tr>
                        {columns.map(col => (
                            <th
                                key={col.key}
                                className={col.sortable ? "cursor-pointer" : ""}
                                onClick={() => col.sortable && handleSort(col.key)}
                            >
                                <div className="flex items-center gap-2">
                                    {col.label}
                                    {col.sortable && sortKey === col.key && (
                                        <span>{sortOrder === "asc" ? "↑" : "↓"}</span>
                                    )}
                                </div>
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.map((row, idx) => (
                        <tr
                            key={idx}
                            onClick={() => onRowClick?.(row)}
                            className={onRowClick ? "cursor-pointer hover:bg-muted/50" : ""}
                        >
                            {columns.map(col => (
                                <td key={col.key}>
                                    {col.render
                                        ? col.render((row as any)[col.key], row)
                                        : (row as any)[col.key]}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
```

---

## Phase 2: 核心功能（3-4周）

### 2.1 成本分析

#### 任务2.1.1: 成本概览页面

**前端实现** (`web/frontend/app/cost/page.tsx`):

```typescript
export default function CostPage() {
    const [overview, setOverview] = useState(null)
    const [trend, setTrend] = useState(null)
    const [breakdown, setBreakdown] = useState(null)
    
    useEffect(() => {
        Promise.all([
            fetch("/api/cost/overview").then(r => r.json()),
            fetch("/api/cost/trend?days=30").then(r => r.json()),
            fetch("/api/cost/breakdown").then(r => r.json()),
        ]).then(([overviewData, trendData, breakdownData]) => {
            setOverview(overviewData.data)
            setTrend(trendData.data)
            setBreakdown(breakdownData.data)
        })
    }, [])
    
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold">成本分析</h1>
            
            {/* 成本概览卡片 */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardTitle>本月成本</CardTitle>
                    <div className="text-2xl font-bold">
                        ¥{overview?.current_month.toLocaleString()}
                    </div>
                </Card>
                <Card>
                    <CardTitle>上月成本</CardTitle>
                    <div className="text-2xl font-bold">
                        ¥{overview?.last_month.toLocaleString()}
                    </div>
                </Card>
                <Card>
                    <CardTitle>同比增长</CardTitle>
                    <div className="text-2xl font-bold">
                        {overview?.yoy > 0 ? "+" : ""}{overview?.yoy}%
                    </div>
                </Card>
                <Card>
                    <CardTitle>环比增长</CardTitle>
                    <div className="text-2xl font-bold">
                        {overview?.mom > 0 ? "+" : ""}{overview?.mom}%
                    </div>
                </Card>
            </div>
            
            {/* 成本趋势图 */}
            {trend && <CostTrendChart data={trend} />}
            
            {/* 成本构成饼图 */}
            {breakdown && <CostBreakdownChart data={breakdown} />}
        </div>
    )
}
```

**后端实现** (`web/backend/api.py`):

```python
@router.get("/cost/overview")
def get_cost_overview(account: Optional[str] = None):
    """获取成本概览"""
    analyzer = CostTrendAnalyzer()
    account = account or get_default_account()
    
    # 获取成本数据
    history, analysis = analyzer.get_cost_trend(account, days=90)
    
    # 计算本月、上月成本
    now = datetime.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    
    current_month_cost = sum(
        c["cost"] for c in history 
        if datetime.fromisoformat(c["date"]) >= current_month_start
    )
    last_month_cost = sum(
        c["cost"] for c in history 
        if last_month_start <= datetime.fromisoformat(c["date"]) < current_month_start
    )
    
    # 计算同比（简化，需要历史数据）
    yoy = 0  # TODO: 实现同比计算
    mom = ((current_month_cost - last_month_cost) / last_month_cost * 100) if last_month_cost > 0 else 0
    
    return {
        "success": True,
        "data": {
            "current_month": round(current_month_cost, 2),
            "last_month": round(last_month_cost, 2),
            "yoy": round(yoy, 2),
            "mom": round(mom, 2),
        }
    }

@router.get("/cost/breakdown")
def get_cost_breakdown(account: Optional[str] = None):
    """获取成本构成"""
    # 按资源类型统计成本
    # 实现逻辑...
    pass
```

---

## 测试计划

### 单元测试

**前端测试** (使用Jest + React Testing Library):

```typescript
// web/frontend/components/__tests__/summary-cards.test.tsx
import { render, screen } from '@testing-library/react'
import { SummaryCards } from '../summary-cards'

describe('SummaryCards', () => {
    it('renders all summary cards', () => {
        render(<SummaryCards 
            totalCost={10000}
            idleCount={5}
            trend="上升"
            trendPct={10}
            totalResources={100}
            resourceBreakdown={{ ecs: 50, rds: 30, redis: 20 }}
            alertCount={3}
            tagCoverage={80}
            savingsPotential={2500}
        />)
        
        expect(screen.getByText('总预估成本')).toBeInTheDocument()
        expect(screen.getByText('¥10,000.00')).toBeInTheDocument()
        expect(screen.getByText('资源总数')).toBeInTheDocument()
        expect(screen.getByText('100')).toBeInTheDocument()
    })
})
```

**后端测试** (使用pytest):

```python
# web/backend/tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from web.backend.main import app

client = TestClient(app)

def test_get_dashboard_summary():
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_cost" in data
    assert "idle_count" in data
```

### 集成测试

```python
# web/backend/tests/test_integration.py
def test_resource_list_flow():
    # 1. 获取资源列表
    response = client.get("/api/resources?type=ecs")
    assert response.status_code == 200
    resources = response.json()["data"]
    assert len(resources) > 0
    
    # 2. 获取资源详情
    resource_id = resources[0]["id"]
    response = client.get(f"/api/resources/{resource_id}")
    assert response.status_code == 200
    resource = response.json()["data"]
    assert resource["id"] == resource_id
```

---

## 总结

### 实施优先级

1. **Phase 1** - 基础增强（2-3周）
   - Dashboard增强
   - 资源列表和详情
   - UI组件完善

2. **Phase 2** - 核心功能（3-4周）
   - 成本分析
   - 安全合规
   - 优化建议

3. **Phase 3** - 高级功能（2-3周）
   - 报告生成
   - 资源拓扑
   - 实时刷新

### 关键里程碑

- **Week 1-2**: Phase 1完成，Dashboard和资源管理基础功能上线
- **Week 5-6**: Phase 2完成，成本分析和安全合规功能上线
- **Week 8-9**: Phase 3完成，报告生成和拓扑图功能上线

### 预期成果

- ✅ 功能完整的Web平台
- ✅ 良好的用户体验
- ✅ 完善的文档
- ✅ 可维护的代码结构





