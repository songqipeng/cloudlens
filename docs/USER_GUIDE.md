# CloudLens 用户指南

**版本**: v2.1.0  
**最后更新**: 2025-12-22

---

## 目录

1. [快速开始](#快速开始)
2. [配置管理](#配置管理)
3. [资源查询](#资源查询)
4. [智能分析](#智能分析)
5. [成本管理](#成本管理)
6. [安全合规](#安全合规)
7. [自动修复](#自动修复)
8. [报告生成](#报告生成)
9. [Web 界面使用](#web-界面使用)
10. [高级功能](#高级功能)
11. [常见问题](#常见问题)

---

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/songqipeng/cloudlens.git
cd cloudlens

# 安装依赖
pip install -r requirements.txt

# 可选：安装 AI 预测依赖
pip install prophet
```

### 配置 MySQL 数据库

1. 创建数据库和用户
2. 初始化表结构：`mysql -u cloudlens -p cloudlens < sql/init_mysql_schema.sql`
3. 配置环境变量：创建 `~/.cloudlens/.env` 文件

### 第一次使用

```bash
# 1. 添加云账号
./cl config add \
  --provider aliyun \
  --name prod \
  --region cn-hangzhou \
  --ak YOUR_ACCESS_KEY \
  --sk YOUR_SECRET_KEY

# 2. 查询资源
./cl query ecs --account prod

# 3. 分析闲置资源
./cl analyze idle --account prod
```

---

## 配置管理

### 添加账号

```bash
# 交互式添加
./cl config add

# 命令行参数
./cl config add \
  --provider aliyun \
  --name staging \
  --region cn-beijing \
  --ak <YOUR_AK> \
  --sk <YOUR_SK>
```

### 查看账号

```bash
# 列出所有账号
./cl config list
```

### 删除账号

```bash
./cl config remove --name staging
```

---

## 资源查询

### 基础查询

```bash
# 查询ECS实例
./cl query ecs --account prod

# 查询RDS数据库
./cl query rds --account prod

# 查询Redis实例
./cl query redis --account prod

# 查询VPC网络
./cl query vpc --account prod

# 查询弹性公网IP
./cl query eip --account prod

# 查询负载均衡
./cl query slb --account prod
```

### 数据导出

```bash
# 导出为JSON
./cl query ecs --account prod --format json --output ecs.json

# 导出为CSV
./cl query ecs --account prod --format csv --output ecs.csv
```

### 并发查询

```bash
# 并发查询所有账号
./cl query ecs --concurrent
```

---

## 智能分析

### 闲置资源分析

```bash
# 分析最近7天的闲置资源
./cl analyze idle --account prod --days 7

# 强制刷新缓存
./cl analyze idle --account prod --days 7 --no-cache
```

**闲置判定标准**（满足任意2个条件）：
- CPU 平均使用率 < 5%
- 内存平均使用率 < 20%
- 公网入流量极低
- 磁盘 IOPS < 100

### 续费提醒

```bash
# 检查30天内到期的资源
./cl analyze renewal --account prod --days 30
```

### 成本分析

```bash
# 当前成本快照
./cl analyze cost --account prod

# 成本趋势分析
./cl analyze cost --account prod --trend
```

### AI 成本预测

```bash
# 预测未来90天成本
./cl analyze forecast --account prod --days 90
```

### 折扣趋势分析

```bash
# 分析折扣趋势并导出HTML报告
./cl analyze discount --export

# 指定账单目录
./cl analyze discount --bill-dir ./bills --export
```

### 安全合规检查

```bash
# 基础安全检查
./cl analyze security --account prod

# CIS Benchmark 合规检查
./cl analyze security --account prod --cis
```

### 标签治理

```bash
./cl analyze tags --account prod
```

---

## 成本管理

### 账单自动获取

```bash
# 测试账单API连接
./cl bill test --account prod

# 获取最近3个月账单（存储到MySQL）
./cl bill fetch --account prod --use-db

# 获取指定时间范围账单
./cl bill fetch --account prod --start 2025-01 --end 2025-06 --use-db
```

### 成本趋势分析

通过 Web 界面访问 `/cost` 页面，查看：
- 成本概览（本月/上月、环比/同比增长）
- 成本趋势图
- 成本构成饼图

---

## 安全合规

### CIS Benchmark 检查

通过 Web 界面访问 `/security/cis` 页面，查看：
- CIS 合规检查结果
- 合规度统计
- 详细检查项

### 公网暴露检测

通过 Web 界面访问 `/security` 页面，查看：
- 公网暴露资源列表
- 安全评分
- 风险统计

---

## 自动修复

### 批量打标签

```bash
# 干运行模式（默认，不会实际修改）
./cl remediate tags --account prod

# 指定标签
./cl remediate tags --account prod --env production --owner devops

# 实际执行修复
./cl remediate tags --account prod --confirm
```

### 查看修复历史

```bash
./cl remediate history --limit 50
```

---

## 报告生成

### Excel 报告

```bash
./cl report generate --account prod --format excel --include-idle
```

### HTML 报告

```bash
./cl report generate --account prod --format html
```

---

## Web 界面使用

### 启动服务

```bash
# 启动后端（终端1）
cd web/backend
python -m uvicorn main:app --reload --port 8000

# 启动前端（终端2）
cd web/frontend
npm run dev
```

### 主要功能页面

- **Dashboard** (`/`): 成本概览、资源统计、闲置资源
- **资源管理** (`/resources`): 多类型资源查询和筛选
- **成本分析** (`/cost`): 成本趋势和构成分析
- **折扣分析** (`/discounts`): 折扣趋势和高级分析
- **预算管理** (`/budgets`): 预算创建和管理
- **虚拟标签** (`/virtual-tags`): 虚拟标签创建和管理
- **告警管理** (`/alerts`): 告警规则和通知配置
- **安全合规** (`/security`): 安全评分和检查结果
- **优化建议** (`/optimization`): 资源优化建议
- **报告生成** (`/reports`): 生成和下载报告

详细说明请参考 [Web 快速开始指南](docs/WEB_QUICKSTART.md)

---

## 高级功能

### 高级筛选

支持 SQL-like 语法：

```bash
# 查询包年包月实例
./cl query ecs --filter "charge_type=PrePaid"

# 查询即将到期的实例
./cl query ecs --filter "expire_days<7"

# 组合条件
./cl query ecs --filter "status=Running AND region=cn-hangzhou"
```

### 缓存管理

```bash
# 查看缓存状态
./cl cache status

# 清除所有缓存
./cl cache clear --all

# 清理过期缓存
./cl cache cleanup
```

---

## 常见问题

### 1. 权限错误

**问题**：`InvalidAccessKeyId.NotFound`

**解决方案**：
- 检查 AccessKey 是否正确
- 运行权限审计：`./cl audit permissions --account prod`

### 2. MySQL 连接失败

**问题**：`Access denied for user`

**解决方案**：
1. 检查 `~/.cloudlens/.env` 文件
2. 测试连接：`mysql -u cloudlens -p cloudlens`
3. 确认 MySQL 服务运行：`mysqladmin ping`

### 3. Web 界面无法访问

**问题**：页面显示错误

**解决方案**：
1. 检查后端：`curl http://127.0.0.1:8000/health`
2. 检查前端：访问 http://localhost:3000
3. 查看浏览器控制台错误

### 4. 数据为空

**问题**：某些页面显示无数据

**解决方案**：
1. 检查数据库是否有数据
2. 运行账单获取：`./cl bill fetch --account prod --use-db`
3. 检查账号配置是否正确

---

## 最佳实践

### 1. 定期巡检

建立定时任务：

```bash
# 每天运行
./cl analyze idle --account prod
./cl analyze cost --account prod
```

### 2. 使用缓存

充分利用缓存机制，避免重复查询：

```bash
# 首次查询会缓存24小时
./cl query ecs --account prod

# 后续查询使用缓存，速度极快
./cl query ecs --account prod
```

### 3. 并发查询

查询多个账号时使用并发：

```bash
./cl query ecs --concurrent
```

---

**更多信息请参考 [产品能力总览](PRODUCT_CAPABILITIES.md) 和 [技术架构文档](TECHNICAL_ARCHITECTURE.md)**
