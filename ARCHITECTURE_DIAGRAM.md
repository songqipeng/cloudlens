# CloudLens 架构可视化图

> 📅 更新时间: 2025-12-15  
> 🎯 目标: 用图形化方式展示系统架构

---

## 🏗️ 整体架构图

```mermaid
graph TB
    subgraph "Interface Layer 交互层"
        CLI[CLI<br/>Click命令组<br/>query/analyze/config/remediate]
        WebAPI[Web API<br/>FastAPI<br/>/api/resources/cost/security/discounts]
        WebUI[Web Frontend<br/>Next.js + React<br/>Dashboard/Resources/Cost]
    end
    
    subgraph "Business Service Layer 业务服务层"
        AnalysisService[analysis_service.py<br/>闲置分析聚合服务<br/>24h缓存]
    end
    
    subgraph "Configuration Layer 配置层"
        Config[config.py<br/>ConfigManager<br/>多源账号配置]
        Context[context.py<br/>ContextManager<br/>CLI上下文]
        Rules[rules_manager.py<br/>RulesManager<br/>优化规则阈值]
    end
    
    subgraph "Analyzer Layer 分析器层"
        IdleDetector[idle_detector.py<br/>闲置检测<br/>2/4条件判定]
        CostTrend[cost_trend_analyzer.py<br/>成本趋势<br/>快照+环比]
        DiscountAnalyzer[discount_analyzer.py<br/>折扣趋势✨<br/>CSV解析+6月趋势]
        Security[security_compliance.py<br/>安全合规<br/>公网暴露+CIS]
        Optimization[optimization_engine.py<br/>优化引擎<br/>建议生成]
    end
    
    subgraph "Provider Layer 云抽象层"
        BaseProvider[BaseProvider<br/>抽象接口]
        AliyunProvider[AliyunProvider<br/>阿里云实现<br/>17种资源]
        TencentProvider[TencentProvider<br/>腾讯云实现<br/>5种资源]
    end
    
    subgraph "Data Layer 数据层"
        SQLiteCache[SQLite Cache<br/>~/.cloudlens/cache.db<br/>5分钟/24小时TTL]
        CostHistory[Cost History<br/>./data/cost/cost_history.json<br/>365天快照]
        DiscountCache[Discount Cache✨<br/>~/.cloudlens/discount_cache/<br/>24小时TTL]
        BillCSV[账单CSV✨<br/>1844634015852583-ydzn/<br/>143万行×6月]
    end
    
    subgraph "External APIs 外部API"
        AliyunAPI[阿里云API<br/>ECS/RDS/CloudMonitor<br/>BSS账单]
        TencentAPI[腾讯云API<br/>CVM/CDB/Monitor]
    end
    
    CLI --> Config
    CLI --> Context
    WebAPI --> Config
    WebUI --> WebAPI
    
    CLI --> AnalysisService
    WebAPI --> AnalysisService
    
    AnalysisService --> Rules
    AnalysisService --> IdleDetector
    AnalysisService --> SQLiteCache
    
    CLI --> IdleDetector
    CLI --> CostTrend
    CLI --> DiscountAnalyzer
    CLI --> Security
    
    WebAPI --> CostTrend
    WebAPI --> DiscountAnalyzer
    WebAPI --> Security
    WebAPI --> Optimization
    
    IdleDetector --> BaseProvider
    CostTrend --> BaseProvider
    Security --> BaseProvider
    Optimization --> BaseProvider
    
    DiscountAnalyzer --> BillCSV
    DiscountAnalyzer --> DiscountCache
    
    BaseProvider --> AliyunProvider
    BaseProvider --> TencentProvider
    
    AliyunProvider --> AliyunAPI
    TencentProvider --> TencentAPI
    
    AliyunProvider --> SQLiteCache
    TencentProvider --> SQLiteCache
    
    CostTrend --> CostHistory
    
    style CLI fill:#667eea,stroke:#333,stroke-width:2px,color:#fff
    style WebAPI fill:#764ba2,stroke:#333,stroke-width:2px,color:#fff
    style WebUI fill:#f093fb,stroke:#333,stroke-width:2px,color:#fff
    style DiscountAnalyzer fill:#4facfe,stroke:#333,stroke-width:3px,color:#fff
    style DiscountCache fill:#43e97b,stroke:#333,stroke-width:2px,color:#fff
    style BillCSV fill:#fa709a,stroke:#333,stroke-width:2px,color:#fff
    style SQLiteCache fill:#30cfd0,stroke:#333,stroke-width:2px,color:#fff
```

---

## 🔄 关键数据流图

### 数据流1: CLI资源查询

```mermaid
sequenceDiagram
    participant User as 用户
    participant CLI as CLI<br/>query_cmd.py
    participant Config as ConfigManager
    participant Cache as SQLite Cache
    participant Provider as AliyunProvider
    participant CloudAPI as 阿里云API
    
    User->>CLI: ./cl query ecs --account prod
    CLI->>Config: 解析账号配置
    Config-->>CLI: CloudAccount
    CLI->>Cache: 查询缓存（key=ecs:prod）
    
    alt 缓存命中（TTL=5分钟）
        Cache-->>CLI: 返回缓存数据
        CLI->>User: 显示结果（✨标注"使用缓存"）
    else 缓存未命中
        CLI->>Provider: list_instances()
        Provider->>CloudAPI: DescribeInstances（分页）
        CloudAPI-->>Provider: JSON响应
        Provider-->>CLI: List[UnifiedResource]
        CLI->>Cache: 存入缓存（TTL=5分钟）
        CLI->>User: 显示结果
    end
```

---

### 数据流2: CLI闲置分析

```mermaid
sequenceDiagram
    participant User as 用户
    participant CLI as CLI<br/>analyze_cmd.py
    participant Service as AnalysisService
    participant Cache as SQLite Cache
    participant Rules as RulesManager
    participant Provider as AliyunProvider
    participant Monitor as CloudMonitor API
    participant Detector as IdleDetector
    
    User->>CLI: ./cl analyze idle --account prod --days 7
    CLI->>Service: analyze_idle_resources()
    Service->>Cache: 查询idle_result（TTL=24h）
    
    alt 缓存命中
        Cache-->>Service: 返回闲置列表
        Service-->>CLI: (idle_instances, is_cached=True)
    else 缓存未命中
        Service->>Rules: 加载规则（CPU阈值、白名单）
        Rules-->>Service: {cpu_threshold: 5%, exclude_tags: [k8s.io]}
        Service->>Provider: list_instances()
        Provider-->>Service: List[UnifiedResource]
        
        loop 每个实例
            Service->>Detector: fetch_ecs_metrics(instance_id, 7天)
            Detector->>Monitor: get_metric(CPU/内存/网络/磁盘×6)
            Monitor-->>Detector: 监控数据平均值
            Detector-->>Service: {CPU: 3%, 内存: 15%, ...}
            Service->>Detector: is_ecs_idle(metrics, tags)
            Detector-->>Service: (is_idle=True, reasons=[CPU低,内存低])
        end
        
        Service->>Cache: 存入idle_result（TTL=24h）
        Service-->>CLI: (idle_instances, is_cached=False)
    end
    
    CLI->>User: 显示闲置实例表格
```

---

### 数据流3: 折扣趋势分析 ✨

```mermaid
sequenceDiagram
    participant User as 用户
    participant CLI as CLI<br/>analyze_cmd.py
    participant Analyzer as DiscountTrendAnalyzer
    participant Cache as 折扣缓存<br/>discount_cache/
    participant CSV as 账单CSV<br/>143万行×6月
    
    User->>CLI: ./cl analyze discount --export
    CLI->>Analyzer: analyze_discount_trend()
    Analyzer->>Analyzer: find_bill_directories()
    Analyzer-->>CLI: 找到: 1844634015852583-ydzn/
    
    Analyzer->>Cache: 检查缓存（TTL=24h）
    
    alt 缓存命中
        Cache-->>Analyzer: 返回聚合数据
    else 缓存未命中
        loop 5个CSV文件
            Analyzer->>CSV: parse_bill_csv()
            CSV-->>Analyzer: 30万条记录
        end
        
        Analyzer->>Analyzer: aggregate_monthly_discounts()
        Note over Analyzer: 按月/产品/合同/实例聚合
        
        Analyzer->>Analyzer: _analyze_trends()
        Note over Analyzer: 计算折扣率变化<br/>趋势方向<br/>累计节省
        
        Analyzer->>Cache: 保存聚合结果（TTL=24h）
    end
    
    Analyzer->>Analyzer: generate_discount_report(html)
    Note over Analyzer: ECharts图表<br/>产品/合同表格
    Analyzer-->>User: ~/cloudlens_reports/discount_trend.html
    User->>User: 打开HTML报告（自动）
```

---

### 数据流4: Web Dashboard加载

```mermaid
sequenceDiagram
    participant Browser as 浏览器
    participant Frontend as Next.js<br/>Dashboard
    participant API as FastAPI<br/>/api/dashboard/summary
    participant Cache as SQLite Cache
    participant BSS as BSS API<br/>QueryBillOverview
    participant Provider as AliyunProvider
    participant Analyzer as CostTrendAnalyzer
    
    Browser->>Frontend: 访问 http://localhost:3000
    Frontend->>API: GET /api/dashboard/summary?account=prod
    API->>Cache: 查询dashboard_summary（TTL=24h）
    
    alt 缓存命中
        Cache-->>API: 返回摘要数据
    else 缓存未命中
        par 并行获取数据
            API->>BSS: QueryBillOverview（当月）
            BSS-->>API: {total_pretax: 12345.67, by_product: {...}}
        and
            API->>Analyzer: generate_trend_report(30天)
            Analyzer-->>API: {latest_cost, mom_change_pct, ...}
        and
            API->>Cache: 查询idle_result
            Cache-->>API: 闲置实例列表
        and
            API->>Provider: list_instances() + list_rds() + list_redis()
            Provider-->>API: 资源列表（计算标签覆盖率）
        end
        
        API->>API: 计算节省潜力<br/>（闲置实例成本汇总）
        API->>Cache: 存入dashboard_summary（TTL=24h）
    end
    
    API-->>Frontend: JSON响应
    Frontend->>Browser: 渲染Dashboard（卡片+图表）
```

---

## 🗂️ 模块依赖关系图

```mermaid
graph LR
    subgraph "CLI层"
        A[analyze_cmd.py]
        B[query_cmd.py]
        C[config_cmd.py]
    end
    
    subgraph "Core核心"
        D[analysis_service]
        E[idle_detector]
        F[cost_trend_analyzer]
        G[discount_analyzer ✨]
        H[security_compliance]
        I[config]
        J[rules_manager]
        K[cache SQLite]
    end
    
    subgraph "Provider层"
        L[BaseProvider]
        M[AliyunProvider]
        N[TencentProvider]
    end
    
    A --> D
    A --> E
    A --> F
    A --> G
    A --> H
    B --> I
    B --> K
    C --> I
    
    D --> J
    D --> K
    D --> M
    
    E --> M
    F --> M
    G --> K
    H --> M
    
    M --> L
    N --> L
    
    style G fill:#4facfe,stroke:#333,stroke-width:3px
    style K fill:#30cfd0,stroke:#333,stroke-width:2px
```

---

## 💾 数据存储拓扑图

```mermaid
graph TB
    subgraph "配置存储 ~/.cloudlens/"
        A1[config.json<br/>账号元数据]
        A2[credentials<br/>AWS兼容格式]
        A3[context.json<br/>CLI上下文]
        A4[rules.json<br/>优化规则]
        A5[cache.db<br/>SQLite缓存✅]
        A6[discount_cache/<br/>折扣缓存✨]
        A7[logs/<br/>结构化日志]
    end
    
    subgraph "项目数据 ./data/"
        B1[cost/cost_history.json<br/>成本快照历史]
        B2[cache/*.pkl<br/>旧文件缓存⚠️]
    end
    
    subgraph "外部数据源"
        C1[账单CSV✨<br/>1844634015852583-ydzn/<br/>143万行×6月]
        C2[*_monitoring_data.db⚠️<br/>旧SQLite数据库]
    end
    
    subgraph "系统存储"
        D1[Keyring<br/>密钥安全存储]
    end
    
    style A5 fill:#30cfd0,stroke:#333,stroke-width:2px
    style A6 fill:#43e97b,stroke:#333,stroke-width:2px
    style C1 fill:#fa709a,stroke:#333,stroke-width:2px
    style B2 fill:#ff6b6b,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style C2 fill:#ff6b6b,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
```

**图例**:
- 🟦 正常使用
- 🟩 新增功能
- 🟥 虚线框 = 待废弃/重构

---

## 🔄 折扣分析处理流程图

```mermaid
flowchart TD
    Start([用户执行命令]) --> FindDir{查找账单目录}
    FindDir -->|未找到| Error1[返回错误提示]
    FindDir -->|找到| CheckCache{检查缓存<br/>TTL=24h}
    
    CheckCache -->|命中| ReturnCached[返回缓存数据]
    CheckCache -->|未命中| ParseCSV[解析CSV文件]
    
    ParseCSV --> Loop1{遍历5个CSV}
    Loop1 -->|每个文件| ReadCSV[读取30万行]
    ReadCSV --> ExtractFields[提取关键字段<br/>账期/产品/实例ID<br/>官网价/优惠金额/合同]
    ExtractFields --> Loop1
    Loop1 -->|完成| Aggregate[按月聚合]
    
    Aggregate --> Agg1[总体聚合<br/>total_official_price<br/>total_discount_amount]
    Aggregate --> Agg2[按产品聚合<br/>by_product]
    Aggregate --> Agg3[按合同聚合<br/>by_contract]
    Aggregate --> Agg4[按实例聚合<br/>by_instance]
    
    Agg1 --> CalcRate[计算折扣率]
    Agg2 --> CalcRate
    Agg3 --> CalcRate
    Agg4 --> CalcRate
    
    CalcRate --> Trend[趋势分析<br/>折扣率变化<br/>趋势方向<br/>累计节省]
    CalcRate --> Product[产品分析<br/>TOP20产品折扣<br/>各产品趋势]
    CalcRate --> Contract[合同分析<br/>TOP10合同效果<br/>合同覆盖月份]
    CalcRate --> Instance[实例分析<br/>TOP50高折扣实例]
    
    Trend --> SaveCache[保存缓存<br/>24小时TTL]
    Product --> SaveCache
    Contract --> SaveCache
    Instance --> SaveCache
    
    SaveCache --> Export{导出报告？}
    Export -->|是| GenHTML[生成HTML<br/>ECharts图表]
    Export -->|是| GenExcel[生成Excel<br/>多Sheet]
    Export -->|否| Display[CLI显示<br/>Rich Table]
    
    GenHTML --> Output[~/cloudlens_reports/<br/>discount_trend.html]
    GenExcel --> Output
    Display --> End([完成])
    Output --> End
    ReturnCached --> Display
    
    style Start fill:#667eea,stroke:#333,stroke-width:2px,color:#fff
    style Aggregate fill:#4facfe,stroke:#333,stroke-width:2px,color:#fff
    style SaveCache fill:#43e97b,stroke:#333,stroke-width:2px,color:#fff
    style Output fill:#fa709a,stroke:#333,stroke-width:2px,color:#fff
```

---

## 🎯 缓存策略图

```mermaid
graph TB
    subgraph "缓存层次"
        L1[Level 1: 内存缓存<br/>Provider SDK内部<br/>无显式管理]
        L2[Level 2: SQLite缓存✅<br/>资源查询: 5分钟<br/>分析结果: 24小时]
        L3[Level 3: 文件缓存<br/>成本历史: 永久<br/>折扣分析: 24小时✨]
        L4[Level 4: 外部数据源<br/>账单CSV: 手动更新<br/>本地DB⚠️: 旧架构]
    end
    
    Query[资源查询] --> L2
    L2 -->|5分钟过期| Query
    
    Analyze[分析服务] --> L2
    L2 -->|24小时过期| Analyze
    
    CostTrend[成本趋势] --> L3
    L3 --> CostTrend
    
    Discount[折扣分析✨] --> L3
    Discount --> L4
    L3 --> Discount
    
    Optimization[优化引擎⚠️] --> L4
    
    style L2 fill:#30cfd0,stroke:#333,stroke-width:2px
    style L3 fill:#43e97b,stroke:#333,stroke-width:2px
    style L4 fill:#ff6b6b,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
```

---

## 🔧 技术栈拓扑图

```mermaid
mindmap
  root((CloudLens))
    CLI
      Click命令框架
      Rich终端美化
      Textual TUI
      prompt_toolkit REPL
    Web后端
      FastAPI异步框架
      Uvicorn ASGI服务器
      Pydantic数据验证
      结构化日志structlog
    Web前端
      Next.js 16 App Router
      React 19
      TypeScript
      Tailwind CSS 4
      Recharts图表
      Lucide图标
    数据处理
      Pandas数据分析
      NumPy科学计算
      Prophet时序预测
      openpyxl Excel
      msgpack序列化
    云SDK
      aliyun-python-sdk
      tencentcloud-sdk
      oss2对象存储
      qcloud_cos
    存储
      SQLite缓存
      JSON配置
      Keyring密钥
      CSV账单✨
    安全
      PermissionGuard
      Keyring加密
      只读设计
```

---

## 📦 资源类型支持矩阵

```mermaid
graph LR
    subgraph "阿里云 17种"
        A1[ECS✅]
        A2[RDS✅]
        A3[Redis✅]
        A4[MongoDB✅]
        A5[OSS✅]
        A6[NAS⚠️]
        A7[VPC✅]
        A8[EIP✅]
        A9[SLB✅]
        A10[NAT✅]
        A11[Disk✅]
        A12[Snapshot✅]
        A13[其他...]
    end
    
    subgraph "腾讯云 5种"
        T1[CVM✅]
        T2[CDB✅]
        T3[Redis✅]
        T4[COS✅]
        T5[VPC✅]
    end
    
    subgraph "规划中"
        P1[AWS EC2]
        P2[AWS RDS]
        P3[火山引擎]
    end
    
    style A1 fill:#52c41a,stroke:#333,stroke-width:2px,color:#fff
    style A6 fill:#ff6b6b,stroke:#333,stroke-width:2px,color:#fff
    style T1 fill:#52c41a,stroke:#333,stroke-width:2px,color:#fff
    style P1 fill:#d9d9d9,stroke:#333,stroke-width:1px
```

---

## 🎨 Web前端页面结构图

```mermaid
graph TB
    Root[/根路由<br/>Dashboard]
    
    Root --> Resources[/resources<br/>资源管理]
    Root --> Cost[/cost<br/>成本分析]
    Root --> Security[/security<br/>安全合规]
    Root --> Discounts[/discounts✨<br/>折扣分析]
    Root --> Optimization[/optimization<br/>优化建议]
    Root --> Reports[/reports<br/>报告生成]
    Root --> Settings[/settings<br/>设置]
    
    Resources --> ResDetail[/resources/[id]<br/>资源详情]
    
    Cost --> Budget[/cost/budget<br/>预算管理]
    
    Security --> CIS[/security/cis<br/>CIS合规]
    
    Discounts --> DiscountTrend[折扣率趋势图]
    Discounts --> ProductDiscount[产品折扣对比]
    Discounts --> ContractDiscount[合同效果分析]
    
    Settings --> Accounts[/settings/accounts<br/>账号管理]
    
    style Root fill:#667eea,stroke:#333,stroke-width:2px,color:#fff
    style Discounts fill:#4facfe,stroke:#333,stroke-width:3px,color:#fff
    style DiscountTrend fill:#43e97b,stroke:#333,stroke-width:2px
    style ProductDiscount fill:#43e97b,stroke:#333,stroke-width:2px
    style ContractDiscount fill:#43e97b,stroke:#333,stroke-width:2px
```

---

## 🔍 成本数据来源决策树

```mermaid
flowchart TD
    Start([需要成本数据]) --> HasBSS{有BSS权限？}
    
    HasBSS -->|是| UseBSS[✅ 优先使用BSS API<br/>QueryBillOverview<br/>QueryInstanceBill]
    HasBSS -->|否| HasCSV{有账单CSV？}
    
    UseBSS --> HasCSV2{同时有CSV？}
    HasCSV2 -->|是| Combine[✅ 最佳方案<br/>BSS实时+CSV历史✨]
    HasCSV2 -->|否| OnlyBSS[仅BSS<br/>当月准确，无历史趋势]
    
    HasCSV -->|是| UseCSV[✅ 使用CSV解析<br/>discount_analyzer✨<br/>6个月历史]
    HasCSV -->|否| HasDB{有本地DB？}
    
    HasDB -->|是| UseDB[⚠️ 使用本地DB<br/>resource_modules<br/>需要提前采集]
    HasDB -->|否| Estimate[兜底方案<br/>规格估算<br/>准确度60-70%]
    
    Combine --> Best[🎯 推荐路径]
    UseCSV --> Good[✅ 可用路径]
    UseBSS --> Good
    UseDB --> Legacy[⚠️ 旧架构路径]
    Estimate --> Fallback[兜底路径]
    
    style Best fill:#52c41a,stroke:#333,stroke-width:3px,color:#fff
    style Good fill:#43e97b,stroke:#333,stroke-width:2px
    style Legacy fill:#ffa940,stroke:#333,stroke-width:2px
    style Fallback fill:#ff6b6b,stroke:#333,stroke-width:2px
```

---

## 📋 技术债务分布图

```mermaid
pie title 技术债务分布（按影响范围）
    "缓存体系双轨" : 30
    "成本口径不统一" : 25
    "Provider命名不一致" : 15
    "优化引擎依赖DB" : 15
    "代码未完成片段" : 10
    "文档缺失" : 5
```

---

## 🎯 重构优先级象限图

```
高价值
  │
  │  🔴 P0              🟡 P1
  │  ┌──────────────────┬──────────────────┐
  │  │ • 修复list_nas   │ • 统一成本口径   │
  │  │ • 统一缓存命名   │ • 批量查询优化   │
  │  │ • 修复命名冲突   │ • 折扣数据集成   │
  │  └──────────────────┴──────────────────┘
  │  🟢 P3              🟢 P2
  │  ┌──────────────────┬──────────────────┐
  │  │ • 代码风格统一   │ • Web功能补全    │
  │  │ • 日志优化       │ • 文档完善       │
  │  │ • 性能监控       │ • 监控批量获取   │
  │  └──────────────────┴──────────────────┘
  │
  └──────────────────────────────────── 实现难度
     低                              高
```

---

## 🌟 产品演进路线图

```mermaid
timeline
    title CloudLens 版本演进
    
    section v1.0 基础版
        多云资源管理 : 阿里云、腾讯云
        资源查询 : ECS、RDS、Redis
        闲置分析 : 基于监控指标
        报告生成 : Excel、HTML
    
    section v2.0 增强版
        交互式REPL : prompt_toolkit
        TUI仪表盘 : textual
        高级查询 : Pandas+JMESPath
        智能缓存 : SQLite
    
    section v2.1 当前版
        成本趋势 : 环比、同比
        AI预测 : Prophet模型
        折扣分析✨ : CSV+6月趋势
        CIS合规 : 安全基线
        自动修复 : 批量打标签
    
    section v2.2 计划
        账单自动下载 : BSS API
        折扣预警 : 钉钉/邮件
        优化引擎重构 : 实时模式
        AWS支持 : EC2/RDS/S3
```

---

## 🎓 架构设计亮点

### 1. Provider抽象模式 ⭐⭐⭐⭐⭐

**优点**: 完美屏蔽云厂商差异，易于扩展

```python
# 添加新云厂商只需3步：
1. class AWSProvider(BaseProvider)
2. 实现必需接口
3. 注册到 get_provider()
```

### 2. 统一资源模型 ⭐⭐⭐⭐⭐

**优点**: 跨云资源可统一查询、分析、报告

```python
UnifiedResource:
  - 最小公共集（所有云都有的字段）
  - raw_data保存原始数据（扩展性）
  - 枚举类型（类型安全）
```

### 3. 多源配置加载 ⭐⭐⭐⭐

**优点**: 灵活适配不同环境（本地/CI/生产）

```
优先级: 环境变量 > credentials文件 > config.json + Keyring
```

### 4. 24小时智能缓存 ⭐⭐⭐⭐

**优点**: 平衡实时性和性能

```
资源查询: 5分钟（变化较快）
分析结果: 24小时（变化较慢）
```

### 5. CSV离线分析 ⭐⭐⭐⭐⭐ ✨

**优点**: 
- 无API权限依赖
- 支持6个月+历史
- 包含完整折扣明细

---

## 📞 快速导航

- **完整报告**: [PROJECT_DEEP_ANALYSIS.md](PROJECT_DEEP_ANALYSIS.md)
- **产品概览**: [PRODUCT_OVERVIEW.md](PRODUCT_OVERVIEW.md)
- **折扣指南**: [docs/DISCOUNT_ANALYSIS_GUIDE.md](docs/DISCOUNT_ANALYSIS_GUIDE.md) ✨
- **Web设计**: [WEB_PRODUCT_DESIGN.md](WEB_PRODUCT_DESIGN.md)

---

**最后更新**: 2025-12-15  
**梳理状态**: ✅ 完成  
**新增功能**: ✨ 折扣趋势分析已集成
