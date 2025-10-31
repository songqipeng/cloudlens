# 更新日志

所有重要的变更都会记录在这个文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [2.2.0] - 2025-10-30

### 新增
- ✨ 统一日志系统：所有分析器使用logger替代print
- ✨ 统一错误处理：ErrorHandler类提供智能错误分类
- ✨ 统一报告生成器：ReportGenerator类提取公共报告逻辑
- ✨ 统一数据库管理：DatabaseManager增强统一资源数据存储
- ✨ 结构化日志：StructuredLogger类支持JSON格式日志

### 安全性
- 🔒 **重大安全修复**：修复Pickle缓存安全风险，改用msgpack
  - 消除了代码执行安全漏洞
  - 涉及文件：cache_manager.py, check_ecs_idle_fixed.py, oss_analyzer.py, mongodb_analyzer.py

### 性能优化
- ⚡ 全面启用并发处理：所有8个分析器已使用并发
  - 性能提升：5-10倍
  - 100实例分析时间：从10-15分钟降至1-2分钟

### 架构优化
- 🏗️ 统一缓存策略：支持多租户隔离的缓存路径
- 🏗️ 优化缓存键设计：统一的缓存键生成方法

### 文档
- 📝 更新README：添加优化说明和FAQ章节
- 📝 创建优化建议文档：OPTIMIZATION_RECOMMENDATIONS.md
- 📝 创建优化完成报告：OPTIMIZATION_COMPLETED.md
- 📝 创建剩余优化清单：REMAINING_OPTIMIZATIONS.md

### 修复
- 🐛 修复缓存格式兼容性问题（pickle → msgpack）

---

## [2.1.0] - 2025-10-29

### 新增
- ✨ 支持ClickHouse资源分析
- ✨ 支持SLB资源分析
- ✨ 支持EIP资源分析
- ✨ Redis折扣分析
- ✨ MongoDB折扣分析（部分完成）

### 改进
- 🔧 优化ECS分析器性能（并发处理）
- 🔧 优化RDS分析器性能（并发处理）
- 🔧 优化Redis分析器性能（并发处理）

---

## [2.0.0] - 2025-10-28

### 新增
- ✨ 多租户支持
- ✨ Keyring凭证管理
- ✨ RDS折扣分析
- ✨ ECS折扣分析
- ✨ 统一阈值管理（YAML配置）

### 改进
- 🔧 统一缓存管理
- 🔧 统一数据库管理
- 🔧 并发处理辅助工具

---

## [1.0.0] - 2025-10-27

### 新增
- ✨ 初始版本发布
- ✨ 支持ECS资源分析
- ✨ 支持RDS资源分析
- ✨ 支持Redis资源分析
- ✨ 支持MongoDB资源分析
- ✨ 支持OSS资源分析
- ✨ HTML和Excel报告生成

---

[2.2.0]: https://github.com/songqipeng/aliyunidle/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/songqipeng/aliyunidle/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/songqipeng/aliyunidle/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/songqipeng/aliyunidle/releases/tag/v1.0.0

