# 常见问题解答（FAQ）

## 📋 目录

- [安装和配置](#安装和配置)
- [凭证管理](#凭证管理)
- [资源分析](#资源分析)
- [折扣分析](#折扣分析)
- [性能和优化](#性能和优化)
- [错误排查](#错误排查)
- [最佳实践](#最佳实践)

## 安装和配置

### Q1: 支持哪些Python版本？

**A**: 本工具支持Python 3.7及以上版本。推荐使用Python 3.11或3.12以获得最佳性能。

```bash
# 检查Python版本
python3 --version

# 推荐使用3.11+
Python 3.11.5
```

### Q2: 如何安装依赖？

**A**: 使用pip安装requirements.txt中的所有依赖：

```bash
# 基础安装
pip install -r requirements.txt

# 如果遇到权限问题
pip install --user -r requirements.txt

# 升级所有依赖到最新版本
pip install --upgrade -r requirements.txt
```

### Q3: config.json文件在哪里？

**A**: 配置文件应该放在项目根目录下。可以从示例文件创建：

```bash
# 复制示例配置
cp config.json.example config.json

# 编辑配置
vim config.json
```

### Q4: 如何配置多个租户？

**A**: 在config.json中添加多个租户配置：

```json
{
  "default_tenant": "tenant1",
  "tenants": {
    "tenant1": {
      "access_key_id": "key1",
      "access_key_secret": "secret1",
      "display_name": "租户1"
    },
    "tenant2": {
      "access_key_id": "key2",
      "access_key_secret": "secret2",
      "display_name": "租户2"
    }
  }
}
```

然后使用时指定租户：

```bash
python main.py tenant1 cru ecs
python main.py tenant2 cru rds
```

## 凭证管理

### Q5: 什么是Keyring？为什么推荐使用？

**A**: Keyring是系统级的密钥管理服务，可以安全地存储敏感信息。

**优势**：
- 🔐 凭证不会明文存储在配置文件中
- 🔐 使用操作系统的加密机制
- 🔐 防止配置文件泄露导致的安全问题

**使用方法**：

```bash
# 交互式设置凭证
python main.py setup-credentials

# 配置文件只需标记使用Keyring
{
  "default_tenant": "my_tenant",
  "tenants": {
    "my_tenant": {
      "use_keyring": true,
      "keyring_key": "aliyun_my_tenant",
      "display_name": "My Tenant"
    }
  }
}
```

### Q6: 如何查看已配置的凭证？

**A**: 使用list-credentials命令：

```bash
python main.py list-credentials
```

输出示例：

```
已配置的租户：
- tenant1 (Tenant 1) - 使用Keyring
- tenant2 (Tenant 2) - 使用配置文件
```

### Q7: AccessKey需要哪些权限？

**A**: 建议使用RAM策略授予以下权限：

**资源分析所需权限**：
- `ecs:DescribeInstances`
- `ecs:DescribeRegions`
- `cms:DescribeMetricData`
- `rds:DescribeDBInstances`
- `r-kvstore:DescribeInstances`
- `dds:DescribeDBInstances`
- `oss:ListBuckets`
- `slb:DescribeLoadBalancers`
- `vpc:DescribeEipAddresses`

**折扣分析所需权限**：
- `ecs:DescribeRenewalPrice`
- `rds:DescribeRenewalPrice`
- `r-kvstore:DescribePrice`
- `dds:DescribePrice`

**最小权限策略示例**：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:Describe*",
        "rds:Describe*",
        "r-kvstore:Describe*",
        "dds:Describe*",
        "oss:List*",
        "slb:Describe*",
        "vpc:Describe*",
        "cms:Describe*"
      ],
      "Resource": "*"
    }
  ]
}
```

## 资源分析

### Q8: 支持哪些资源类型？

**A**: 当前支持8种主要资源类型：

| 资源类型 | 状态 | 命令 |
|---------|------|------|
| ECS | ✅ 完成 | `python main.py cru ecs` |
| RDS | ✅ 完成 | `python main.py cru rds` |
| Redis | ✅ 完成 | `python main.py cru redis` |
| MongoDB | ✅ 完成 | `python main.py cru mongodb` |
| ClickHouse | ✅ 完成 | `python main.py cru clickhouse` |
| OSS | ✅ 完成 | `python main.py cru oss` |
| SLB | ✅ 完成 | `python main.py cru slb` |
| EIP | ✅ 完成 | `python main.py cru eip` |

### Q9: 分析需要多长时间？

**A**: 分析时间取决于资源数量和网络状况：

- **小规模**（<50个实例）：2-5分钟
- **中规模**（50-200个实例）：5-15分钟
- **大规模**（>200个实例）：15-30分钟

**性能优化**：
- 工具已使用并发处理，性能提升60-83%
- 缓存机制减少重复API调用
- 智能重试避免网络抖动

### Q10: 如何只分析特定区域？

**A**: 当前版本自动分析所有区域。如需限制区域，可以：

**临时方案**：修改代码中的`get_all_regions()`方法：

```python
def get_all_regions(self):
    # 只返回指定区域
    return ['cn-hangzhou', 'cn-beijing']
```

**未来版本**：将支持命令行参数指定区域：

```bash
# 规划中的功能
python main.py cru ecs --regions cn-hangzhou,cn-beijing
```

### Q11: 闲置判断标准是什么？

**A**: 不同资源有不同的闲置标准，采用"OR"关系（满足任一条件即认为闲置）：

**ECS示例**：
- CPU利用率 < 5%
- 内存利用率 < 20%
- 磁盘IOPS < 100
- Load Average < vCPU * 5%

**调整阈值**：编辑`thresholds.yaml`文件：

```yaml
ecs:
  with_agent:
    cpu_utilization: 5      # 改为10
    memory_utilization: 20  # 改为30
```

## 折扣分析

### Q12: 哪些资源支持折扣分析？

**A**: 目前支持包年包月实例的折扣分析：

- ✅ **ECS**：支持DescribeRenewalPrice
- ✅ **RDS**：支持DescribeRenewalPrice
- ✅ **Redis**：支持DescribePrice（RENEW/BUY）
- ✅ **MongoDB**：支持DescribePrice（RENEW/BUY）

**注意**：按量付费实例不支持折扣分析。

### Q13: 为什么有些实例无法查询折扣？

**A**: 常见原因：

1. **计费模式不支持**：只有包年包月实例支持
2. **实例状态异常**：已停止或已删除的实例
3. **API权限不足**：缺少Price相关权限
4. **API限流**：调用过于频繁

**解决方法**：

```bash
# 检查实例计费模式
# 在阿里云控制台查看实例详情

# 检查RAM权限
# 确保有DescribeRenewalPrice或DescribePrice权限

# 减少并发数（如果遇到限流）
# 修改concurrent_helper.py中的max_workers
```

### Q14: 折扣率如何计算？

**A**: 折扣率 = (实际续费价格 / 基准价格) * 100%

**示例**：
- 基准价格：1000元/月
- 续费价格：700元/月
- 折扣率：70%（即7折）

**报告中的指标**：
- **平均折扣率**：所有实例的平均折扣
- **最低折扣率**：折扣力度最大的实例
- **最高折扣率**：折扣力度最小的实例
- **成本节省**：基准价格 - 续费价格

## 性能和优化

### Q15: 如何提高分析速度？

**A**: 多种优化方法：

**1. 调整并发数**：

```python
# utils/concurrent_helper.py
def process_concurrently(
    items,
    process_func,
    max_workers=10  # 增加到15-20（根据网络带宽）
):
```

**2. 使用缓存**：

```bash
# 默认24小时缓存，避免重复查询
# 查看缓存状态
ls -lh data/cache/

# 清除缓存强制刷新
rm -rf data/cache/*
```

**3. 限制分析范围**：

```bash
# 只分析特定资源类型
python main.py cru ecs  # 而不是 cru all

# 避免频繁的全量分析
# 使用定时任务（如每天一次）
```

### Q16: 缓存数据存储在哪里？

**A**: 缓存和数据文件位置：

```
data/
├── cache/                    # 缓存文件（24小时TTL）
│   ├── ecs_instances.cache
│   ├── rds_instances.cache
│   └── ...
├── ecs_monitoring_data.db    # ECS监控数据库
├── rds_monitoring_data.db    # RDS监控数据库
└── ...
```

**缓存管理**：

```bash
# 查看缓存大小
du -sh data/cache/

# 清理过期缓存（自动）
# 工具会自动检查TTL

# 手动清理所有缓存
rm -rf data/cache/*

# 清理特定资源缓存
rm data/cache/ecs_*.cache
```

### Q17: 报告文件很大，如何优化？

**A**: 报告大小优化方法：

**1. 定期清理旧报告**：

```bash
# 删除30天前的报告
find reports/ -name "*.html" -mtime +30 -delete
find reports/ -name "*.xlsx" -mtime +30 -delete
```

**2. 压缩归档**：

```bash
# 压缩旧报告
tar -czf reports_archive_$(date +%Y%m).tar.gz reports/*.html
# 然后删除原文件
```

**3. 只生成需要的报告格式**：

在代码中选择性生成HTML或Excel：

```python
# 只生成HTML（更小）
generate_html_report(data)

# 或只生成Excel（更详细）
generate_excel_report(data)
```

## 错误排查

### Q18: 提示"配置文件不存在"怎么办？

**A**: 检查并创建配置文件：

```bash
# 1. 检查文件是否存在
ls -la config.json

# 2. 如果不存在，从示例复制
cp config.json.example config.json

# 3. 检查当前目录
pwd  # 确保在项目根目录

# 4. 检查文件权限
chmod 600 config.json
```

### Q19: API调用失败（403 Forbidden）

**A**: 权限问题排查步骤：

**1. 检查AccessKey是否正确**：

```bash
# 重新设置凭证
python main.py setup-credentials
```

**2. 检查RAM权限**：

登录阿里云控制台 → RAM访问控制 → 用户 → 查看权限策略

需要的权限：
- AliyunECSReadOnlyAccess
- AliyunRDSReadOnlyAccess
- AliyunOSSReadOnlyAccess
- AliyunCMSReadOnlyAccess

**3. 检查STS token是否过期**（如果使用STS）：

```bash
# STS token有效期通常是1小时
# 需要定期刷新
```

### Q20: MongoDB/Redis折扣分析失败

**A**: 常见原因和解决方法：

**1. 实例计费模式检查**：

```bash
# 只有"包年包月"实例支持折扣分析
# 在控制台查看：实例列表 → 计费方式列

# 过滤包年包月实例
# 工具会自动过滤，但确保实例确实是包年包月
```

**2. API版本问题**：

MongoDB使用`DescribePrice` API（不是`DescribeRenewalPrice`）

```python
# resource_modules/discount_analyzer.py
# MongoDB部分已修复使用正确的API
request.set_action_name('DescribePrice')
request.add_query_param('OrderType', 'RENEW')
```

**3. 网络连接问题**：

```bash
# 测试连接
ping dds.aliyuncs.com
ping r-kvstore.aliyuncs.com

# 检查DNS
nslookup dds.aliyuncs.com
```

### Q21: 测试失败怎么办？

**A**: 测试失败排查：

**1. 检查测试依赖**：

```bash
# 安装测试依赖
pip install pytest pytest-cov pytest-mock pytest-asyncio

# 查看已安装版本
pip list | grep pytest
```

**2. 运行特定测试**：

```bash
# 运行单个测试文件
pytest tests/core/test_cache_manager.py -v

# 运行单个测试函数
pytest tests/core/test_cache_manager.py::TestCacheManager::test_init -v
```

**3. 查看详细错误**：

```bash
# 显示详细错误信息
pytest tests/ -v --tb=long

# 显示print输出
pytest tests/ -v -s
```

## 最佳实践

### Q22: 生产环境如何部署？

**A**: 推荐的生产环境部署方案：

**1. 使用专用服务器**：

```bash
# 创建专用用户
sudo useradd -m aliyun-analyzer

# 部署到/opt目录
sudo cp -r aliyunidle /opt/
sudo chown -R aliyun-analyzer:aliyun-analyzer /opt/aliyunidle
```

**2. 使用Systemd管理**：

```bash
# 创建service文件
sudo vim /etc/systemd/system/aliyun-analyzer.service

# 内容参考DEPLOYMENT.md

# 启用服务
sudo systemctl enable aliyun-analyzer.timer
sudo systemctl start aliyun-analyzer.timer
```

**3. 配置日志轮转**：

```bash
# 使用logrotate管理日志
sudo vim /etc/logrotate.d/aliyun-analyzer

# 详细配置参考DEPLOYMENT.md
```

**详细部署指南请参考**：[DEPLOYMENT.md](DEPLOYMENT.md)

### Q23: 如何定期自动分析？

**A**: 使用Cron或Systemd Timer：

**Cron方式**：

```bash
# 编辑crontab
crontab -e

# 每天凌晨2点执行
0 2 * * * cd /opt/aliyunidle && /opt/aliyunidle/venv/bin/python main.py cru all >> /var/log/aliyun-analyzer.log 2>&1

# 每周一执行折扣分析
0 3 * * 1 cd /opt/aliyunidle && /opt/aliyunidle/venv/bin/python main.py discount all >> /var/log/discount.log 2>&1
```

**Systemd Timer方式**（推荐）：

参考[DEPLOYMENT.md](DEPLOYMENT.md)中的详细配置。

### Q24: 如何保护AccessKey安全？

**A**: AccessKey安全最佳实践：

**1. 使用Keyring存储**：

```bash
# 不要在config.json中明文存储
python main.py setup-credentials
```

**2. 使用环境变量**：

```bash
export ALIYUN_ACCESS_KEY_ID="your_id"
export ALIYUN_ACCESS_KEY_SECRET="your_secret"

# 在代码中读取环境变量
# 而不是硬编码
```

**3. 限制文件权限**：

```bash
# 配置文件只有所有者可读
chmod 600 config.json

# 检查权限
ls -la config.json
# 应该显示：-rw------- 1 user user
```

**4. 使用RAM子账号**：

- 不要使用主账号AccessKey
- 创建专用RAM用户
- 授予最小必要权限
- 定期轮换AccessKey

**5. 启用MFA**：

在RAM控制台为用户启用多因素认证。

**6. 定期审计**：

```bash
# 查看AccessKey使用日志
# 在阿里云控制台 → 操作审计
```

### Q25: 如何优化成本？

**A**: 基于分析结果的成本优化建议：

**1. 处理闲置资源**：

根据报告中的"优化建议"：
- **降配**：降低实例规格
- **合并**：合并多个小实例
- **删除**：删除完全闲置的资源

**2. 利用折扣**：

```bash
# 运行折扣分析
python main.py discount all

# 查看报告中的折扣率
# 选择折扣力度大的时期续费
```

**3. 切换计费模式**：

- 低使用率实例：包年包月 → 按量付费
- 高使用率实例：按量付费 → 包年包月（享受折扣）

**4. 定期清理**：

```bash
# 每月运行一次全量分析
python main.py cru all

# 审查所有闲置资源
# 制定清理计划
```

## 更多帮助

找不到答案？

1. 查看完整文档：[README.md](README.md)
2. 查看开发日志：[DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md)
3. 查看部署指南：[DEPLOYMENT.md](DEPLOYMENT.md)
4. 提交Issue：[GitHub Issues](https://github.com/yourorg/aliyunidle/issues)
5. 联系技术支持
