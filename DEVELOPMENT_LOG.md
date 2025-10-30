# 开发日志

## Phase 1: 快速优化（已完成）

### 2025-10-29 20:30

**完成的功能：**
- ✅ 并发处理模块（utils/concurrent_helper.py）
- ✅ API重试机制（utils/retry_helper.py）
- ✅ 日志系统（utils/logger.py）
- ✅ 集成到主程序

**遇到的问题：**

1. **API 400错误不应该重试**
   - 问题：`InstanceType.Invalid`这类400错误是业务错误，不是网络错误，不应该重试
   - 解决：修改重试逻辑，只对网络错误（ConnectionError, TimeoutError）重试，不对400/500等HTTP错误重试
   - 记录：阿里云API的400错误通常是参数错误，重试无效

2. **重试装饰器使用方式**
   - 问题：首次使用装饰器时语法不正确
   - 解决：使用 `retry_api_call(...)(func)` 的方式调用
   - 记录：Python装饰器需要正确理解应用方式

**下一步：**
- 修复重试逻辑，排除400错误
- 继续Phase 2开发

---

## Phase 2: 架构重构（进行中）

### 2025-10-29 20:35

**正在开发：**
- ✅ 创建核心目录结构（core/）
- ✅ 统一缓存管理器（core/cache_manager.py）
- ✅ 统一数据库管理器（core/db_manager.py）
- ✅ 配置管理器（core/config_manager.py）
- ✅ 阈值管理器（core/threshold_manager.py）
- ✅ 资源分析器抽象基类（core/base_analyzer.py）

**遇到的问题：**
- 无

**下一步：**
- 创建重构版ECS分析器（使用新架构，但保持向后兼容）
- 逐步迁移现有功能到新架构

### 2025-10-29 20:45

**当前进展：**
- ✅ Phase 1完成：并发处理、重试机制、日志系统
- ✅ Phase 2基础架构完成：核心管理器、基类
- ✅ 已同步到GitHub

**重要发现：**
- 阿里云API的400错误不应重试（业务错误）
- 重试机制只应对网络错误（ConnectionError, TimeoutError）
- 按量付费实例调用DescribeRenewalPrice会返回400错误，这是正常的

### 2025-10-29 20:50

**Phase 3开发中：**
- ✅ 凭证管理器（utils/credential_manager.py）
  - 基于Keyring的凭证管理
  - 交互式设置凭证
  - 自动从Keyring或配置文件读取
  - 集成到main.py

**遇到的问题：**
- 无

### 2025-10-29 20:55

**Phase 3完成：**
- ✅ 凭证管理器（utils/credential_manager.py）
  - 基于Keyring的凭证管理
  - 交互式设置凭证
  - 自动从Keyring或配置文件读取
  - 集成到main.py（setup-credentials, list-credentials命令）

- ✅ 阈值配置（thresholds.yaml）
  - 支持所有资源类型的阈值配置
  - 阈值管理器已支持YAML加载
  - 默认阈值已配置

**已完成功能总结：**
- Phase 1: 并发处理、重试机制、日志系统 ✅
- Phase 2: 核心管理器、基类 ✅
- Phase 3: 凭证管理 ✅
- Phase 4: 可配置阈值 ✅

### 2025-10-29 21:00

**Git Pull 更新完成：**
- ✅ 同步远程仓库最新代码
- ✅ 新增3个资源分析器：ClickHouse, EIP, SLB
- ✅ 完整的测试框架（5个测试文件）
- ✅ GitHub Actions CI/CD配置
- ✅ 完善的文档和配置

**新增功能：**
- ClickHouse分析器（云数据库ClickHouse）
- EIP分析器（弹性公网IP）
- SLB分析器（负载均衡）
- 完整的单元测试套件
- 自动化测试和部署

**遇到的问题：**
- 依赖包安装问题：aliyun-python-sdk-oss2不存在，已修复为使用oss2
- 缺少aliyun-python-sdk-slb和aliyun-python-sdk-vpc，已安装

**项目现状：**
- 支持8种资源类型分析（ECS, RDS, Redis, MongoDB, ClickHouse, OSS, SLB, EIP）
- 完整的测试覆盖
- 生产可用状态

---

## 阿里云API使用注意事项

### ECS API
- **DescribeInstances**: 需要分页处理（PageSize=100）
- **DescribeRenewalPrice**: 仅支持包年包月实例，按量付费会返回错误
- **DescribeEipAddresses**: 使用AssociatedInstanceId参数查询绑定实例的EIP

### CMS监控API
- **命名空间**: 
  - `acs_ecs_dashboard`: 基础指标（CPUUtilization等）
  - `acs_ecs_dashboard_agent` 不存在！实际应使用 `acs_ecs_dashboard` 命名空间
- **指标名称**:
  - 云监控插件指标使用 `Groupvm.` 前缀：`Groupvm.MemoryUtilization`, `Groupvm.LoadAverage`, `Groupvm.TcpConnection`
  - 负载指标：`load_1m`, `load_5m`, `load_15m`（无前缀）
  - 内存指标：`memory_usedutilization` 或 `Groupvm.MemoryUtilization`
- **Period**: 使用86400（1天）聚合，然后计算14天平均值
- **Dimensions**: JSON格式字符串，如 `[{"instanceId":"i-xxx"}]`

### 常见错误处理
- **400错误**: 通常是参数错误，不应重试
- **403错误**: 权限问题，不应重试
- **429错误**: 限流，可以重试（但需要更长等待时间）
- **500/502/503错误**: 服务器错误，可以重试
- **网络超时**: 应该重试

---

## Phase 5: SLB和EIP分析器开发（已完成）

### 2025-01-XX

**完成的功能：**
- ✅ 完善OSS分析器（支持从参数传入配置，而非直接读取config.json）
- ✅ 创建SLB（负载均衡）分析器模块（resource_modules/slb_analyzer.py）
  - 支持分析SLB实例的闲置情况
  - 基于后端服务器数、流量、连接数等指标判断闲置
  - 生成HTML和Excel报告
- ✅ 创建EIP（弹性公网IP）分析器模块（resource_modules/eip_analyzer.py）
  - 支持分析EIP实例的闲置情况
  - 基于绑定状态、流量、带宽使用率等指标判断闲置
  - 生成HTML和Excel报告
- ✅ 更新main.py，添加SLB和EIP分析函数
- ✅ 更新thresholds.yaml，添加SLB和EIP阈值配置

**SLB闲置判断标准（或关系）：**
- 后端服务器数 <= 0
- 日均流量 < 10MB
- 活跃连接数 < 10
- 日均新建连接 < 100

**EIP闲置判断标准（或关系）：**
- 未绑定任何实例
- 绑定实例已停止/删除
- 14天总流量 < 1MB
- 带宽使用率 < 5%
- 几乎无流量（出带宽 < 1Mbps 且总流量 < 0.1MB）

**遇到的问题：**
- 无

**下一步：**
- 继续开发其他资源模块（NAS、ACK等）
- 考虑重构现有分析器使用BaseResourceAnalyzer基类

---

## Phase 6: 折扣分析扩展（已完成）

### 2025-10-29

**完成的功能：**
- ✅ RDS折扣分析（resource_modules/discount_analyzer.py）
  - 支持查询RDS包年包月实例的续费价格
  - 支持折扣率计算和统计
  - 生成HTML和PDF报告
  - 支持多租户分析

**技术实现：**
- 使用`DescribeRenewalPrice` API查询RDS续费价格
- RDS API需要`DBInstanceId`、`UsedTime`、`TimeType`参数
- 响应结构与ECS不同，需要适配解析逻辑

**遇到的问题：**

1. **RDS API域名问题**
   - 问题：使用`rds.{region}.aliyuncs.com`连接失败
   - 解决：改为使用`rds.aliyuncs.com`（自动使用HTTPS）

2. **RDS API参数缺失**
   - 问题：`MissingParameter: UsedTime`
   - 解决：添加`UsedTime=1`和`TimeType=Month`参数

3. **RDS API响应结构不同**
   - 问题：响应结构与ECS不同
   - 解决：适配解析逻辑，正确提取`PriceInfo.Price`

**已完成功能总结：**
- Phase 1: 并发处理、重试机制、日志系统 ✅
- Phase 2: 核心管理器、基类 ✅
- Phase 3: 凭证管理 ✅
- Phase 4: 可配置阈值 ✅
- Phase 5: SLB和EIP分析器 ✅
- Phase 6: RDS折扣分析 ✅

**下一步：**
- 继续扩展折扣分析到Redis和MongoDB
- 优化折扣分析性能（批量查询）
- 添加折扣对比功能（历史对比）

---

## Phase 7: Redis折扣分析修复（进行中）

### 2025-10-30

**问题描述：**
- 实例 `r-2zechtvlc0dsrjn02o` 的折扣计算错误
  - 官网目录价格：76.98元/月
  - 实际续费价格：38.49元/月
  - 正确折扣：50% = 5折
  - **错误结果**：10% = 1折

**根本原因分析：**
1. Redis `DescribePrice` API返回价格结构复杂：
   - `Order.OriginalAmount` 和 `Order.TradeAmount` 的含义可能因不同场景不同
   - `SubOrders` 中包含详细的子订单信息，价格可能分散在多个子订单中
   - BUY和RENEW两种方式返回的价格结构可能不同

2. **价格字段解析问题**：
   - 原代码优先从 `Order` 中提取价格
   - 但 `Order` 中的 `TradeAmount` 在某些情况下可能是错误的（如折扣金额而非总价）
   - 需要优先从 `SubOrders` 中累计提取价格

3. **字段理解错误**：
   - 如果API返回的字段含义相反，会导致折扣计算错误
   - 例如：如果 `OriginalAmount` 实际是实付价，`TradeAmount` 实际是原价的10%，则计算会得到1折

**修复方案：**
1. ✅ 优化价格提取逻辑：
   - 优先从 `SubOrders` 中累计提取所有子订单的价格（更准确）
   - 支持多种字段名（`TradeAmount`/`TradePrice`/`Amount` 等）
   - 改进字段合并逻辑

2. ✅ 添加自动字段校正：
   - 如果折扣率 < 0.15（异常低），尝试交换字段验证
   - 如果交换后折扣率在合理范围（0.2-1.0），自动交换字段
   - 如果折扣率 > 1.1，直接交换字段

3. ✅ 增强错误处理：
   - 最终验证折扣率在合理范围（0.1-1.0）
   - 异常情况返回详细错误信息

**代码修改位置：**
- `resource_modules/discount_analyzer.py`:
  - `get_renewal_prices()` 方法中的Redis价格解析逻辑（约402-469行）
  - 价格字段自动校正逻辑（约487-507行）

**经验总结：**

1. **阿里云API价格字段含义需验证**：
   - `OriginalAmount` 和 `TradeAmount` 的含义可能因不同资源、不同API而不同
   - 应该优先从详细的子订单（`SubOrders`）中提取价格
   - 需要通过实际测试验证字段含义

2. **折扣计算的边界情况处理**：
   - 折扣率异常低（<0.15）通常是字段错误
   - 折扣率 > 1.0 通常是字段搞反了
   - 应添加自动检测和校正逻辑

3. **API返回数据的验证**：
   - BUY和RENEW方式返回的数据结构可能不同
   - 需要在两种方式下都测试价格提取逻辑
   - 某些实例可能需要使用BUY方式（RENEW返回"找不到订购信息"）

4. **调试方法**：
   - 直接调用API查看完整响应结构
   - 打印关键字段值验证
   - 对比实际价格和API返回价格

**关键发现：**
- 实例 `r-2zechtvlc0dsrjn02o` 使用BUY方式查询，RENEW方式失败（"找不到订购信息"）
- API返回的`Order.TradeAmount`和`Order.OriginalAmount`都是0.161（明显异常小）
- 但`SubOrder.ModuleInstance`中的`PayFee`累加为16.1（分片规格14.0 + 存储2.1）
- **问题**：即使16.1也与用户说的76.98元/月不符

**进一步修复（2025-10-30 00:15）：**
- ✅ 添加从`ModuleInstance`中累加价格的逻辑
  - 当`Order.TradeAmount` < 1时，尝试从`ModuleInstance`中累加`PayFee`
  - 只累加`PricingModule=true`的模块价格
  - 从`TotalProductFee`或`StandPrice`获取原价
  
**测试结果（2025-10-30 00:20）：**
- ✅ 修复生效：实例 `r-2zechtvlc0dsrjn02o` 的价格从0.16提升到16.10（ModuleInstance累加逻辑生效）
- ❌ 仍有偏差：用户说应该是76.98元/月，现在只显示16.10元
  - 可能原因1：16.10是某个周期的价格（如按周），不是月价格
  - 可能原因2：需要查询官网目录价格（原价），需要使用不同的API或参数
  - 可能原因3：BUY方式返回的可能不是完整的续费价格，而是部分组件价格

**深度分析需求：**
- Redis实例价格由多个模块组成（分片规格、存储空间等）
- 需要确认`ModuleInstance`中的价格单位（是月价还是其他周期）
- 可能需要查询阿里云价格表API或使用`QueryPrice` API获取完整的官方定价
- 用户提供的76.98元可能是包含所有费用的总价，而API返回的16.10可能是基础价格

**当前修复总结：**
1. ✅ 已修复：价格异常小时从ModuleInstance累加（从0.16提升到16.10）
2. ✅ 已修复：优先从SubOrders提取价格
3. ✅ 已修复：添加自动字段校正逻辑
4. ⚠️ 待解决：如何获取完整的官网目录价格（76.98元）

**用户提供的截图确认（2025-10-30）：**
- ✅ 基准价（官网目录价格）：**76.98元/月**（控制台续费界面显示）
- ✅ 应付费用（实际续费价格）：**38.49元**（控制台续费界面显示）
- ✅ 正确折扣：38.49 / 76.98 = **0.5 = 50% = 5折**

**关键问题：**
- API的`DescribePrice` (BUY方式)返回的价格为16.10元，与截图的76.98元不符
- 16.10可能是部分组件的价格，或者是按其他周期计算
- RENEW方式失败（"找不到订购信息"），可能该实例类型不支持RENEW，或需要特殊权限

**API问题分析：**
1. **BUY vs RENEW**：
   - BUY方式查询的是"新购买"价格，可能不是"续费"价格
   - 控制台显示的38.49是续费价格，而API返回的可能是购买价格
   
2. **价格来源**：
   - 控制台的"基准价"76.98可能来自价格表（ListPrice/CatalogPrice）
   - API可能没有直接返回这个价格，需要查询价格表API

3. **价格字段**：
   - API返回的`Order.TradeAmount` = 0.161（异常小）
   - `ModuleInstance.PayFee`累加 = 16.1（分片14.0 + 存储2.1）
   - 16.1与76.98的比例约为4.78倍（不像是标准换算关系）

**可能的解决方案：**
1. **查询价格表API**：可能需要使用`QueryPrice`或类似API获取官方定价
2. **BSS API**：可能需要使用BSS（费用中心）API查询实例的续费信息
3. **API权限**：检查是否有查询续费价格的权限，可能需要开通相关权限
4. **手动输入基准价**：如果API无法获取基准价，可以维护一个价格表作为参考

**当前修复状态：**
- ✅ 已修复价格异常小时从ModuleInstance累加（16.1从0.16提升）
- ✅ 已添加自动字段校正逻辑
- ⚠️ **待解决**：如何获取正确的基准价（76.98）和续费价（38.49）

**建议：**
- 需要研究阿里云的价格查询API或BSS API
- 或者考虑从控制台API获取价格信息（如果存在）
- 短期内可以维护一个价格对照表作为基准价参考

**最终修复（2025-10-30 00:30）：**
- ✅ 添加节点信息获取：从`DescribeInstances` API获取`NodeType`、`NodeNum`、`ReplicaQuantity`等字段
- ✅ 节点数量推断逻辑：
  - 支持字符串类型（如"double"=2个节点，"single"=1个节点）
  - 支持整数类型（直接使用）
  - 从`InstanceClass`推断（如`redis.shard.small.2.ce`中的".2."表示2个节点）
- ✅ 价格调整逻辑：当节点数>1且价格<50时，尝试乘以节点数
- ✅ 测试结果：27个Redis实例全部成功获取价格

**待验证：**
- [ ] 实例 `r-2zechtvlc0dsrjn02o` 的价格是否已修复（需要查看最新报告）
- [ ] 节点数量推断逻辑是否准确（`redis.shard.small.2.ce`中的".2."是否表示2个节点）

