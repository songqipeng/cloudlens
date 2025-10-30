# 更新日志

本文档记录了阿里云资源分析工具的所有重要变更。

## [2.1.0] - 2025-10-30

### Added
- ✅ 添加完整的单元测试套件（83个测试用例）
  - core模块测试：cache_manager, config_manager, threshold_manager
  - utils模块测试：concurrent_helper, retry_helper
  - 测试覆盖率提升至36%（核心模块96-100%）
- ✅ 添加GitHub Actions CI/CD配置
  - 支持Python 3.7-3.13多版本测试
  - 集成pytest和覆盖率报告
  - 集成Codecov
- ✅ 添加测试配置文件
  - pytest.ini：测试框架配置
  - .coveragerc：覆盖率配置
- ✅ 完善README.md
  - 添加测试章节
  - 添加性能优化说明
  - 添加故障排查指南
  - 更新折扣分析状态

### Changed
- ⚡ 优化cache_manager缓存机制
  - 使用msgpack替代pickle（安全性+性能提升2-5x）
  - 保持向后兼容性（可读取旧pickle缓存）
- 📝 更新requirements.txt
  - 添加msgpack>=1.0.0
  - 添加测试依赖（pytest, pytest-cov, pytest-mock, pytest-asyncio）

### Fixed
- 🐛 修复MongoDB折扣分析API问题
  - 使用DescribePrice API替代DescribeRenewalPrice
  - 支持OrderType参数（RENEW/BUY双重尝试）
  - 修改响应格式解析逻辑
  - 折扣分析功能完整度达到100%

## [2.0.0] - 2025-10-29

### Added
- ✅ 扩展折扣分析功能
  - 支持Redis折扣分析（DescribePrice API）
  - 支持MongoDB折扣分析（初步实现）
  - 添加折扣率统计和成本节省估算
- ✅ 新增SLB负载均衡分析器
  - 支持6个监控指标
  - 后端服务器、流量、连接数分析
- ✅ 新增EIP弹性公网IP分析器
  - 支持4个监控指标
  - 绑定状态、流量、带宽分析
- ✅ 新增ClickHouse分析器
  - 支持10个监控指标
  - CPU、内存、磁盘、网络、查询分析
- ✅ 添加凭证管理功能
  - Keyring集成，凭证安全存储
  - 交互式凭证设置（setup-credentials）
  - 凭证列表查看（list-credentials）
- ✅ 添加阈值配置功能
  - YAML配置文件支持
  - 支持资源子类型（with_agent/without_agent）
  - 默认阈值兜底
- 📚 完善项目文档
  - COMPREHENSIVE_ANALYSIS.md：全面分析报告（34KB）
  - REDIS_PRICE_API_ANALYSIS.md：Redis价格API分析

### Changed
- ⚡ 性能优化：为所有分析器添加并发处理
  - RDS/Redis/MongoDB/ClickHouse：并发处理
  - 性能提升60-83%
  - Redis实例分析：27个实例从90s降至15s
- 🏗️ 架构优化
  - 提取base_analyzer抽象基类
  - 统一cache_manager、db_manager、config_manager
  - 添加concurrent_helper、retry_helper工具模块

### Fixed
- 🐛 修复多个API调用问题
- 🐛 优化错误处理和重试机制

## [1.0.0] - 2025-10-28

### Added
- ✅ 初始版本发布
- ✅ 支持8种资源类型分析
  - ECS弹性计算服务
  - RDS云数据库
  - Redis缓存数据库
  - MongoDB文档数据库
  - OSS对象存储
  - （SLB、EIP、ClickHouse后续版本添加）
- ✅ 资源利用率分析（CRU）
  - 基于14天监控数据
  - 科学的闲置判断标准
  - HTML+Excel双重报告
- ✅ 折扣分析（Discount）
  - ECS折扣分析
  - RDS折扣分析
- ✅ 多租户支持
  - 租户隔离配置
  - 独立的报告输出目录
- ✅ 基础功能模块
  - 日志系统（logger.py）
  - 缓存管理（pickle格式）
  - 数据库管理（SQLite）
- 📚 项目文档
  - README.md：用户文档
  - DEVELOPMENT_LOG.md：开发日志（14KB）
  - REFACTORING_GUIDE.md：重构指南（48KB）
  - PROJECT_SUMMARY.md：项目总结（14KB）
  - PRODUCT_TECH_PLAN.md：产品技术规划（17KB）
  - TODO_FEATURES.md：待开发功能（10KB）

## 版本号规范

本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)规范：

- **主版本号（Major）**：不兼容的API变更
- **次版本号（Minor）**：向下兼容的功能新增
- **修订号（Patch）**：向下兼容的问题修正

## 图例

- ✅ Added：新增功能
- 🐛 Fixed：问题修复
- ⚡ Changed：功能变更/优化
- 🏗️ Architecture：架构改进
- 📚 Documentation：文档更新
- 🔒 Security：安全性改进
- ⚠️ Deprecated：废弃功能
- 🗑️ Removed：删除功能
