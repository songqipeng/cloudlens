# CloudLens 快速参考

> 📖 一页纸了解全部核心命令和功能

---

## 🎯 核心命令速查

### 配置管理
```bash
./cl config add --provider aliyun --name prod --ak xxx --sk xxx    # 添加账号
./cl config list                                                    # 查看账号
./cl config rules                                                   # 配置规则（交互式）
```

### 资源查询
```bash
./cl query ecs --account prod              # 查询ECS
./cl query rds --account prod              # 查询RDS
./cl query ecs --format json > ecs.json    # 导出JSON
./cl query ecs --concurrent                # 并发查询多账号
```

### 分析功能
```bash
./cl analyze idle --account prod           # 闲置资源分析
./cl analyze cost --account prod --trend   # 成本趋势分析
./cl analyze forecast --account prod       # AI成本预测
./cl analyze discount --export             # 折扣趋势分析
./cl analyze security --account prod --cis # CIS安全合规
./cl analyze tags --account prod           # 标签治理
```

### 账单管理
```bash
./cl bill test --account prod              # 测试账单API连接
./cl bill fetch --account prod             # 获取账单数据
```

### 自动修复
```bash
./cl remediate tags --account prod         # 批量打标签（干运行）
./cl remediate tags --account prod --confirm  # 实际执行
./cl remediate history                     # 查看修复历史
```

### 缓存管理
```bash
./cl cache status                          # 查看缓存状态
./cl cache clear --all                     # 清除所有缓存
./cl cache cleanup                         # 清理过期缓存
```

---

## 📊 核心模块速查

| 模块 | 文件 | 核心功能 |
|------|------|----------|
| 配置管理 | `core/config.py` | 多源账号加载+Keyring |
| 缓存系统 | `core/cache.py` | MySQL缓存表，24小时TTL |
| 数据库抽象 | `core/database.py` | MySQL/SQLite兼容 |
| 闲置检测 | `core/idle_detector.py` | 多条件判定+白名单 |
| 成本趋势 | `core/cost_trend_analyzer.py` | 快照+环比MoM |
| 折扣分析 | `core/discount_analyzer_advanced.py` | 账单分析+趋势 |
| 安全合规 | `core/security_compliance.py` | 公网暴露+CIS |
| 云抽象 | `core/provider.py` | BaseProvider接口 |
| 阿里云 | `providers/aliyun/provider.py` | 20+种资源 |

---

## 🔄 核心数据流

### 流程1: 资源查询（24小时缓存）
```
CLI/Web → ConfigManager → CacheManager → Provider → 云平台API → MySQL → 统一资源模型 → 返回结果
```

### 流程2: 闲置分析（24小时缓存）
```
CLI/Web → IdleDetector → Provider → CloudMonitor API → 规则匹配 → 判定结果 → MySQL → 返回
```

### 流程3: 折扣分析（24小时缓存）
```
CLI/Web → DiscountAnalyzer → BillStorage → MySQL → 趋势分析 → 返回结果
```

---

## 💾 数据存储位置

```
~/.cloudlens/
├── config.json              # 账号配置
├── .env                     # 环境变量（MySQL配置等）
├── notifications.json       # 通知配置
└── logs/                    # 日志文件

MySQL数据库 (cloudlens)
├── resource_cache           # 资源查询缓存（24小时TTL）
├── bill_items              # 账单明细数据
├── dashboards              # 仪表盘配置
├── budgets                 # 预算数据
├── virtual_tags            # 虚拟标签
├── alert_rules             # 告警规则
└── ...                     # 其他业务表
```

---

## 📈 性能基准

| 操作 | 无缓存 | 有缓存 | 提升倍数 |
|------|--------|--------|----------|
| 单账号ECS查询（100实例） | 3-5秒 | <100ms | 50x |
| 闲置分析（含监控） | 30-60秒 | <1秒 | 60x |
| 折扣分析（账单数据） | 60-90秒 | <1秒 | 90x |
| 5账号并发查询 | 8秒 | <500ms | 16x |

---

## 🚀 快速开始（3步）

### 1️⃣ 配置账号
```bash
./cl config add --provider aliyun --name prod --ak YOUR_AK --sk YOUR_SK
```

### 2️⃣ 查询资源
```bash
./cl query ecs --account prod
```

### 3️⃣ 分析优化
```bash
./cl analyze idle --account prod      # 闲置分析
./cl analyze discount --export        # 折扣分析
```

---

## 📚 文档导航

| 文档 | 用途 | 适合人群 |
|------|------|----------|
| `README.md` | 项目主文档 | 所有人 |
| `PRODUCT_CAPABILITIES.md` | 产品能力总览 | 产品、技术 |
| `PRODUCT_INTRODUCTION.md` | 产品介绍 | 产品、业务 |
| `TECHNICAL_ARCHITECTURE.md` | 技术架构 | 开发者、架构师 |
| `PROJECT_STRUCTURE.md` | 项目结构 | 开发者 |
| `USER_GUIDE.md` | 用户手册 | 用户、运维 |
| `QUICKSTART.md` | 快速开始 | 新用户 |
| `IMPROVEMENT_PLAN.md` | 改进计划 | 开发者、产品 |

---

## 🔗 关键链接

- **CLI入口**: `cli/main.py`
- **Web API**: `web/backend/api.py`
- **折扣分析器**: `core/discount_analyzer_advanced.py`
- **配置示例**: `~/.cloudlens/config.json`

---

## 💡 一句话记住

**CloudLens = 多云资源治理（CLI+Web） = 闲置识别 + 成本/折扣分析 + 安全合规 + 自动优化**

---

**最后更新**: 2025-12-22  
**版本**: v2.1.0
