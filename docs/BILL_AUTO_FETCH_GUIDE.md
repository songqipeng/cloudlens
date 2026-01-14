# 账单数据自动获取指南

> 📅 创建时间: 2025-12-15  
> ✨ 功能: 通过阿里云BSS OpenAPI自动获取账单数据，无需手动下载  
> 🎯 目标: 实现账单数据的自动化、定时获取

---

## 🌟 功能概述

### 为什么需要自动获取？

**手动下载的问题**：
- ❌ 每次都要登录阿里云控制台
- ❌ 下载-解压-整理，步骤繁琐
- ❌ 无法及时获取最新数据
- ❌ 难以实现定时自动分析

**自动获取的优势**：
- ✅ 一键获取多个月份的账单
- ✅ 定时任务自动执行
- ✅ 数据格式与手动下载的CSV完全一致
- ✅ 支持增量更新
- ✅ 产品化的正确方式

---

## 🔧 前置准备

### 1. 安装SDK依赖

```bash
pip install aliyun-python-sdk-core aliyun-python-sdk-bssopenapi python-dateutil
```

### 2. 配置阿里云账号

确保你的账号已在 `config.json` 中配置：

```bash
./cl config account list
```

如果没有配置，先添加：

```bash
./cl config account add
```

### 3. 确认RAM权限

账号需要以下BSS OpenAPI权限：
- `bss:QueryInstanceBill` - 查询实例账单明细
- `bss:QueryBillOverview` - 查询账单概览

**授权方式**：
1. 登录阿里云控制台
2. 进入"访问控制（RAM）"
3. 找到对应的RAM用户
4. 添加"AliyunBSSFullAccess"权限策略

---

## 🚀 快速开始

### 测试API连接

```bash
# 测试连接并获取少量数据（验证权限）
./cl bill test --account my_account

# 指定测试月份
./cl bill test --account my_account --month 2025-12 --limit 5
```

**预期输出**：
```
测试获取账期 2025-12 的前 5 条记录...

✅ 成功获取 5 条记录

┌─────────────────────────────────────────┐
│          📋 样本数据（第1条记录）        │
├─────────────────────────────────────────┤
│ 产品名称: 云服务器 ECS                  │
│ 计费方式: Subscription                  │
│ 官网价: 100.00                          │
│ 折扣: 50.00                             │
│ 应付金额: 50.00                         │
│ 币种: CNY                               │
│ 实例ID: i-bp1234567890abcdef           │
└─────────────────────────────────────────┘

✅ API连接正常，可以执行完整获取
```

### 获取账单数据

```bash
# 获取最近3个月的账单（默认）
./cl bill fetch --account my_account

# 指定时间范围
./cl bill fetch --account my_account --start 2025-01 --end 2025-06

# 指定输出目录
./cl bill fetch --account my_account --output-dir ./my_bills
```

**执行过程**：
```
┌─────────────────────────────────────────┐
│          📥 账单数据获取                │
├─────────────────────────────────────────┤
│ 账号: my_account                        │
│ 时间范围: 2025-10 至 2025-12            │
│ 输出目录: ./bills_data                  │
└─────────────────────────────────────────┘

============================================================
处理账期: 2025-10
============================================================
账期 2025-10 共有 145230 条记录
已获取 300/145230 条记录
已获取 600/145230 条记录
...
已获取 145230/145230 条记录
已保存 145230 条记录到: bills_data/.../2025-10-detail.csv

============================================================
处理账期: 2025-11
============================================================
...

✅ 成功获取 3 个月份的账单数据

┌────────┬──────────────────────────────────┬─────────┐
│ 账期   │ 文件路径                          │ 文件大小│
├────────┼──────────────────────────────────┼─────────┤
│ 2025-10│ bills_data/.../2025-10-detail.csv │ 65.32 MB│
│ 2025-11│ bills_data/.../2025-11-detail.csv │ 67.18 MB│
│ 2025-12│ bills_data/.../2025-12-detail.csv │ 68.45 MB│
└────────┴──────────────────────────────────┴─────────┘

💡 提示:
  1. 账单文件已保存，可用于折扣分析
  2. 运行折扣分析: ./cl analyze discount --bill-dir bills_data/...
  3. 在Web页面刷新即可看到最新数据
```

---

## 📊 数据说明

### CSV文件格式

自动获取的CSV文件与手动下载的**完全一致**，包含所有字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| 账期 | 账单周期 | 2025-12 |
| 产品 | 产品名称 | 云服务器 ECS |
| 计费方式 | Subscription/PayAsYouGo | Subscription |
| 官网价 | 官方价格 | 100.00 |
| 优惠金额 | 折扣金额 | 50.00 |
| 应付金额 | 实际应付 | 50.00 |
| 实例ID | 资源实例ID | i-bp123456 |
| ... | 共76个字段 | ... |

### 数据完整性

- ✅ 包含所有实例级别的明细
- ✅ 支持所有阿里云产品
- ✅ 包含折扣、代金券、储值卡抵扣等信息
- ✅ 数据与控制台下载的CSV完全一致

---

## 🤖 定时自动获取

### 方式1: Cron定时任务

**每月1号凌晨自动获取上月账单**：

```bash
# 编辑crontab
crontab -e

# 添加定时任务（每月1号1点执行）
0 1 1 * * cd /path/to/cloudlens && ./cl bill fetch --account my_account >> /var/log/cloudlens_bill.log 2>&1
```

### 方式2: Python脚本

创建 `scripts/auto_fetch_bills.py`：

```python
#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
from core.config import ConfigManager
from core.bill_fetcher import BillFetcher

def main():
    # 获取账号配置
    cm = ConfigManager()
    account = cm.get_account("my_account")
    
    # 创建获取器
    fetcher = BillFetcher(
        access_key_id=account.access_key_id,
        access_key_secret=account.access_key_secret
    )
    
    # 获取上个月的账单
    last_month = datetime.now().replace(day=1) - timedelta(days=1)
    billing_cycle = last_month.strftime("%Y-%m")
    
    # 获取并保存
    records = fetcher.fetch_instance_bill(billing_cycle)
    output_dir = Path("./bills_data/auto")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = output_dir / f"{billing_cycle}-detail.csv"
    fetcher.save_to_csv(records, csv_path, billing_cycle)
    
    print(f"✅ 已自动获取 {billing_cycle} 账单: {csv_path}")

if __name__ == "__main__":
    main()
```

**设置定时任务**：
```bash
chmod +x scripts/auto_fetch_bills.py

# Cron
0 1 1 * * cd /path/to/cloudlens && python3 scripts/auto_fetch_bills.py
```

### 方式3: CloudLens调度器

使用内置的调度器（未来版本）：

```bash
# 添加定时任务
./cl scheduler add "bill_fetch" \
  --schedule "0 1 1 * *" \
  --command "bill fetch --account my_account"
```

---

## 🔗 与折扣分析集成

### 流程图

```
定时任务
  ↓
自动获取账单（BSS API）
  ↓
保存为CSV文件
  ↓
折扣分析自动识别新数据
  ↓
Web页面自动更新
```

### 使用方式

**1. 自动识别账单目录**

折扣分析器会自动查找项目根目录下的账单文件夹：

```python
# core/discount_analyzer.py 自动查找
bill_dirs = analyzer.find_bill_directories()
```

**2. Web页面自动刷新**

- 访问 `/discounts` 页面
- 点击"强制刷新"
- 自动分析最新的账单数据

**3. CLI命令**

```bash
# 自动使用最新的账单数据
./cl analyze discount

# 或指定目录
./cl analyze discount --bill-dir bills_data/auto
```

---

## 💡 最佳实践

### 1. 账单数据管理

**目录结构建议**：
```
cloudlens/
├── bills_data/                    # 账单数据根目录
│   ├── {账号ID}-{账号名}/
│   │   ├── 2025-01-detail.csv
│   │   ├── 2025-02-detail.csv
│   │   └── ...
│   └── auto/                      # 自动获取的数据
│       ├── 2025-11-detail.csv
│       └── 2025-12-detail.csv
└── .gitignore                     # 忽略bills_data/
```

**`.gitignore` 配置**：
```
bills_data/
*.csv
```

### 2. 数据保留策略

```bash
# 保留最近12个月的数据
find bills_data/ -name "*.csv" -mtime +365 -delete
```

### 3. 增量更新

```bash
# 每月只获取新月份的数据
current_month=$(date +"%Y-%m")
./cl bill fetch --account my_account --start $current_month --end $current_month
```

### 4. 监控与告警

```python
# 检查账单获取是否成功
import os
from datetime import datetime
from pathlib import Path

def check_bill_health():
    last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    expected_file = Path(f"bills_data/auto/{last_month}-detail.csv")
    
    if not expected_file.exists():
        # 发送告警（钉钉/邮件）
        send_alert(f"账单获取失败：{last_month} 数据缺失")
```

---

## 🔒 安全建议

### 1. 密钥管理

**不要硬编码密钥**：
```python
# ❌ 错误
access_key_id = "LTAI4xxxxx"

# ✅ 正确：从配置文件读取
from core.config import ConfigManager
cm = ConfigManager()
account = cm.get_account("my_account")
```

### 2. 最小权限原则

只授予必要的BSS权限：
- `bss:QueryInstanceBill` - 查询账单明细
- `bss:QueryBillOverview` - 查询概览

**不要授予**：
- `bss:ModifyInstance` - 修改实例
- `bss:CreateOrder` - 创建订单
- 其他写权限

### 3. 日志脱敏

```python
logger.info(f"账号: {account.access_key_id[:10]}***")  # 只显示前10位
```

---

## 📈 性能优化

### 1. 分页策略

```python
# 默认每页300条（最大值）
records = fetcher.fetch_instance_bill(
    billing_cycle="2025-12",
    page_size=300  # 减少API调用次数
)
```

### 2. 并发获取

```python
from concurrent.futures import ThreadPoolExecutor

def fetch_month(billing_cycle):
    return fetcher.fetch_instance_bill(billing_cycle)

months = ["2025-01", "2025-02", "2025-03"]
with ThreadPoolExecutor(max_workers=3) as executor:
    results = executor.map(fetch_month, months)
```

### 3. 增量缓存

```python
# 只获取本地不存在的月份
existing_months = set(f.stem.split("-")[1:3] for f in output_dir.glob("*.csv"))
to_fetch = [m for m in all_months if m not in existing_months]
```

---

## 🛠️ 故障排查

### 问题1: SDK未安装

**症状**：
```
❌ 缺少必要的SDK依赖
```

**解决**：
```bash
pip install aliyun-python-sdk-core aliyun-python-sdk-bssopenapi python-dateutil
```

### 问题2: 权限不足

**症状**：
```
The user does not have permission to operate
```

**解决**：
1. 登录阿里云控制台
2. RAM访问控制 → 用户 → 权限管理
3. 添加"AliyunBSSFullAccess"权限策略

### 问题3: API限流

**症状**：
```
Throttling.User: Request was denied due to user flow control
```

**解决**：
- 减少并发请求
- 增加请求间隔时间（默认0.5秒）
- 分批次获取数据

### 问题4: 数据量过大

**症状**：
获取时间过长或内存不足

**解决**：
```python
# 分页写入CSV，边获取边保存
with open(csv_path, 'a', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    for page in fetcher.fetch_pages(billing_cycle):
        writer.writerows(page)
```

---

## 🔄 迁移指南

### 从手动CSV迁移到自动获取

**步骤1: 验证数据一致性**

```bash
# 使用手动下载的CSV分析
./cl analyze discount --bill-dir ./manual_bills

# 使用API获取的CSV分析
./cl bill fetch --account my_account
./cl analyze discount --bill-dir ./bills_data/...

# 对比结果是否一致
```

**步骤2: 混合使用（过渡期）**

```
cloudlens/
├── 1844634015852583-ydzn/        # 手动下载的历史数据（2025-07至2025-12）
└── bills_data/
    └── auto/                      # API自动获取（2025-12起）
```

**步骤3: 完全自动化**

设置定时任务后，删除手动下载的CSV文件。

---

## 🎯 实际案例

### 案例1: 月度成本分析自动化

**需求**：每月1号自动生成上月的折扣分析报告

**实现**：
```bash
#!/bin/bash
# scripts/monthly_report.sh

# 1. 获取上月账单
last_month=$(date -d "last month" +"%Y-%m")
./cl bill fetch --account my_account --start $last_month --end $last_month

# 2. 生成折扣分析报告
./cl analyze discount --export --format excel

# 3. 发送邮件（或钉钉通知）
python3 scripts/send_report.py --month $last_month
```

**Cron**：
```
0 2 1 * * /path/to/scripts/monthly_report.sh
```

### 案例2: 实时折扣监控

**需求**：每天检查折扣率变化，异常时告警

**实现**：
```python
# scripts/discount_monitor.py
from core.discount_analyzer import DiscountTrendAnalyzer

def monitor():
    analyzer = DiscountTrendAnalyzer()
    result = analyzer.analyze_discount_trend(bill_dir, months=6)
    
    # 检查折扣率下降
    if result['trend_analysis']['discount_rate_change_pct'] < -5:
        send_alert(f"⚠️ 折扣率下降 {abs(change)}%，请关注！")
```

---

## 📚 API参考

### BillFetcher 类

```python
from core.bill_fetcher import BillFetcher

fetcher = BillFetcher(
    access_key_id="LTAI4...",
    access_key_secret="xxx",
    region="cn-hangzhou"
)
```

**主要方法**：

| 方法 | 说明 | 参数 |
|------|------|------|
| `fetch_instance_bill()` | 获取实例账单明细 | `billing_cycle`, `max_records`, `page_size` |
| `fetch_bill_overview()` | 获取账单概览 | `billing_cycle` |
| `save_to_csv()` | 保存为CSV | `records`, `output_path`, `billing_cycle` |
| `fetch_and_save_bills()` | 批量获取并保存 | `start_month`, `end_month`, `output_dir` |

---

## 🎉 总结

### 核心价值

- ✅ **自动化**：无需手动下载，定时自动获取
- ✅ **产品化**：符合SaaS产品的设计理念
- ✅ **实时性**：可随时获取最新数据
- ✅ **完整性**：数据与手动下载完全一致
- ✅ **可靠性**：支持重试、增量更新

### 推荐workflow

1. **初次使用**：手动下载历史6个月CSV
2. **测试连接**：`./cl bill test --account my_account`
3. **验证数据**：获取最近1个月数据对比
4. **设置定时**：配置Cron每月自动获取
5. **持续监控**：定期检查任务执行状态

---

**文档更新**: 2025-12-15  
**功能状态**: ✅ 完整实现并测试通过  
**相关文档**: 
- docs/DISCOUNT_ANALYSIS_GUIDE.md
- WEB_DISCOUNT_INTEGRATION.md






