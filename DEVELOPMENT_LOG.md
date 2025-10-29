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

**下一步：**
- 继续完善Phase 2：重构ECS分析器（可选，保持向后兼容）
- 或者直接完善其他功能（密钥管理、可配置阈值等）

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

