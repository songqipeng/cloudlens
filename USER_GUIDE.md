# CloudLens CLI - 使用指南

## 目录

1. [快速开始](#快速开始)
2. [安装配置](#安装配置)
3. [基础使用](#基础使用)
4. [高级功能](#高级功能)
5. [命令参考](#命令参考)
6. [最佳实践](#最佳实践)
7. [故障排查](#故障排查)

---

## 快速开始

### 5分钟上手

```bash
# 1. 克隆项目
git clone <repository>
cd aliyunidle

# 2. 安装依赖
pip install -r requirements.txt

# 3. 添加第一个账号
python3 main_cli.py config add \
  --provider aliyun \
  --name my-account \
  --region cn-hangzhou \
  --ak YOUR_ACCESS_KEY \
  --sk YOUR_SECRET_KEY

# 4. 查询资源
python3 main_cli.py query ecs --account my-account

# 5. 生成报告
python3 main_cli.py report generate --account my-account --format excel

# 可选：使用封装命令（记住上次账号，账号可作为位置参数）
./cloudlens query my-account ecs
./cloudlens query ecs
./cl query ecs
```

🎉 完成！您已经成功使用CloudLens CLI！

---

## 安装配置

### 系统要求

- **操作系统**: macOS, Linux, Windows
- **Python版本**: 3.8+
- **依赖**: pip

### 安装步骤

#### 1. 安装核心依赖

```bash
pip install -r requirements.txt
```

- 包含阿里云 ECS/RDS/Redis/OSS/NAS/VPC/EIP/SLB、腾讯云 CVM/CDB/Redis/COS/VPC 所需 SDK。
- PDF 报告需要额外安装 weasyprint，或在本地提供 wkhtmltopdf。

#### 2. 验证安装

```bash
python3 main_cli.py --help
```

如果看到命令帮助信息，说明安装成功！

### 配置账号

#### 添加阿里云账号

```bash
python3 main_cli.py config add \
  --provider aliyun \
  --name prod \
  --region cn-hangzhou \
  --ak LTAI... \
  --sk xxx...
```

#### 添加腾讯云账号

```bash
python3 main_cli.py config add \
  --provider tencent \
  --name prod \
  --region ap-guangzhou \
  --ak AKIDxxx... \
  --sk xxx...
```

#### 查看已配置账号

```bash
python3 main_cli.py config list
```

输出示例：
```
Name       Provider   Region         
-------------------------------------
prod       aliyun     cn-hangzhou    
test       aliyun     cn-hongkong    
tencent-p  tencent    ap-guangzhou   
```

---

## 基础使用

### 资源查询

#### 查询ECS实例

```bash
# 查询指定账号
python3 main_cli.py query ecs --account prod

# 查询所有账号
python3 main_cli.py query ecs
```

输出示例：
```
ID                     Name                           IP               Status     Region       Provider
----------------------------------------------------------------------------------------------------
i-abc123               web-server-01                  47.76.179.137    Running    cn-hangzhou  aliyun  
i-def456               db-server-01                   10.0.0.10        Running    cn-hangzhou  aliyun  
```

#### 查询RDS数据库

```bash
python3 main_cli.py query rds --account prod
```

#### 查询Redis缓存

```bash
python3 main_cli.py query redis --account prod
```

#### 查询OSS存储

```bash
python3 main_cli.py query oss --account prod
```

#### 查询VPC网络

```bash
python3 main_cli.py query vpc --account prod
```

#### 查询弹性公网IP

```bash
python3 main_cli.py query eip --account prod
```

### 基础筛选

#### 按状态筛选

```bash
# 只看运行中的实例
python3 main_cli.py query ecs --account prod --status Running

# 只看已停止的实例
python3 main_cli.py query ecs --account prod --status Stopped
```

#### 按区域筛选

```bash
python3 main_cli.py query ecs --account prod --region cn-hangzhou
```

#### 组合筛选

```bash
python3 main_cli.py query ecs --account prod --status Running --region cn-hangzhou
```

### 数据导出

#### 导出为JSON

```bash
python3 main_cli.py query ecs --account prod --format json --output ecs.json
```

#### 导出为CSV

```bash
python3 main_cli.py query ecs --account prod --format csv --output ecs.csv
```

#### 直接输出（不保存文件）

```bash
# 输出JSON到终端
python3 main_cli.py query ecs --account prod --format json

# 可以配合jq使用
python3 main_cli.py query ecs --format json | jq '.[] | select(.status=="Running")'
```

---

## 高级功能

### 高级筛选

#### 语法说明

支持SQL-like的查询语法：

- 操作符：`=`, `!=`, `>`, `<`, `>=`, `<=`
- 逻辑连接：`AND`, `OR`
- 字段支持：resource的所有字段

#### 示例

**查询包年包月实例**：
```bash
python3 main_cli.py query ecs --filter "charge_type=PrePaid"
```

**查询即将到期的实例（7天内）**：
```bash
python3 main_cli.py query ecs --filter "expire_days<7"
```

**组合条件**：
```bash
python3 main_cli.py query ecs --filter "status=Running AND region=cn-hangzhou"
```

**OR条件**：
```bash
python3 main_cli.py query ecs --filter "charge_type=PrePaid OR expire_days<30"
```

**复杂查询**：
```bash
python3 main_cli.py query ecs --filter "charge_type=PrePaid AND expire_days<7 AND status=Running"
```

### 并发查询

当查询多个账号时，启用并发可以大幅提升速度：

```bash
# 启用并发查询所有账号
python3 main_cli.py query ecs --concurrent

# 对比：
# 串行：5个账号约25秒
# 并发：5个账号约8秒
```

### 资源分析

#### 续费检查

```bash
# 检查30天内到期的资源
python3 main_cli.py analyze renewal --account prod --days 30
```

输出示例：
```
🔍 检查30天内到期的资源...

⚠️  即将到期的资源:
ID                  Name                Type      到期时间              剩余天数
--------------------------------------------------------------------------------
i-abc123            web-server          ECS       2024-12-25 00:00:00   15天    
rm-def456           prod-db             RDS       2024-12-28 00:00:00   18天    
```

#### 闲置资源分析

```bash
# 分析7天内的闲置资源
python3 main_cli.py analyze idle --account prod --days 7
```

> 当前闲置分析仅支持阿里云 ECS，并依赖 CloudMonitor 指标；其他资源类型的闲置检测在规划中。

输出示例：
```
🔍 Analyzing resource usage (last 7 days)...

⚠️  检测到闲置资源:

ID: i-abc123
Name: old-test-server
状态: Running
闲置原因:
  • CPU平均使用率仅2.3%
  • 内存平均使用率仅8.5%
  • 公网入流量极低
建议: 考虑下线或降配

总计: 3 个闲置资源
```

#### 成本分析

```bash
python3 main_cli.py analyze cost --account prod
```

#### 标签治理

```bash
python3 main_cli.py analyze tags --account prod
```

输出示例：
```
📊 标签覆盖率分析
总资源数: 50
已标签: 25
未标签: 25
覆盖率: 50.0%

⚠️  无标签资源 (前10个):
ID                    Name                          Type      
--------------------------------------------------------------
i-abc123              test-server                   ecs       
rm-def456             temp-db                       rds       

💡 优化建议:
  • ⚠️ 标签覆盖率仅50.0%，建议为所有资源添加标签以便管理
  • 发现25个无标签资源，建议至少添加 env, project, owner 标签
```

#### 安全合规检查

```bash
python3 main_cli.py analyze security --account prod
```

> 当前安全分析聚焦公网暴露与未绑定 EIP 统计，安全组/加密等审计项尚未落地。

输出示例：
```
🌐 公网暴露分析
总实例数: 50
公网暴露: 15

⚠️  公网暴露实例 (前10个):
ID                  Name                 Type   Public IPs        Risk    
-------------------------------------------------------------------------
i-abc123            web-server-1         ecs    47.76.179.137     MEDIUM  

📍 弹性公网IP统计
总EIP数: 20
已绑定: 15
未绑定: 5 (25.0%)

💰 未绑定EIP (浪费成本):
  • 47.242.116.255 (ID: eip-abc123)

💡 安全建议:
  • ⚠️ 发现15个实例绑定了公网IP，建议评估是否真的需要公网访问
  • ⚠️ 发现5个未绑定的EIP，建议释放以节省成本
```

### 权限审计

```bash
python3 main_cli.py audit permissions --account prod
```

输出示例：
```
🔍 Auditing permissions for prod (aliyun)...

👤 用户信息:
  note: 使用AccessKey直接调用

✅ 已验证的只读权限:
  • ecs:DescribeInstances: ECS实例查询
  • rds:DescribeDBInstances: RDS实例查询
  • vpc:DescribeVpcs: VPC查询

🚨 检测到高危权限:
  策略: AdministratorAccess
  风险级别: HIGH
  说明: 该策略包含写入/删除权限
  建议: 建议使用只读策略如 AliyunECSReadOnlyAccess
```

### 拓扑生成

```bash
python3 main_cli.py topology generate --account prod --output topology.md
```

生成Mermaid格式的网络拓扑图，包含：
- VPC分组
- 可用区分组（AZ）
- ECS实例
- RDS实例
- 状态标识（🟢运行中 🔴已停止）

### 报告生成

#### HTML报告

```bash
python3 main_cli.py report generate --account prod --format html --output report.html
```

#### Excel报告

```bash
python3 main_cli.py report generate --account prod --format excel --output report.xlsx
```

生成的Excel包含多个Sheet：
- **概览**: 资源统计摘要
- **ECS实例**: 所有ECS实例详情
- **RDS实例**: 所有RDS实例详情
- **闲置资源**: 闲置资源列表（如果使用--include-idle）

#### 包含闲置分析的报告

```bash
python3 main_cli.py report generate --account prod --format excel --include-idle
```

---

## 命令参考

### config命令组

#### config list
```bash
python3 main_cli.py config list
```
列出所有已配置的账号

#### config add
```bash
python3 main_cli.py config add \
  --provider <aliyun|tencent> \
  --name <账号名称> \
  --region <区域> \
  --ak <AccessKey> \
  --sk <SecretKey>
```
添加新账号配置

### query命令组

所有query命令支持的通用选项：
- `--account <name>`: 指定账号（可选，默认查询所有）
- `--format <table|json|csv>`: 输出格式（默认table）
- `--output <file>`: 输出文件路径
- `--status <status>`: 按状态筛选
- `--region <region>`: 按区域筛选
- `--filter <expression>`: 高级筛选表达式
- `--concurrent`: 启用并发查询

#### query ecs
```bash
python3 main_cli.py query ecs [选项]
```
查询ECS/CVM实例

#### query rds
```bash
python3 main_cli.py query rds [选项]
```
查询RDS/CDB数据库

#### query redis
```bash
python3 main_cli.py query redis [选项]
```
查询Redis实例

#### query oss
```bash
python3 main_cli.py query oss [选项]
```
查询OSS/COS对象存储

#### query vpc
```bash
python3 main_cli.py query vpc [选项]
```
查询VPC网络

#### query eip
```bash
python3 main_cli.py query eip [选项]
```
查询弹性公网IP

#### query slb
```bash
python3 main_cli.py query slb [选项]
```
查询SLB负载均衡器

#### query nas
```bash
python3 main_cli.py query nas [选项]
```
查询NAS文件系统

### analyze命令组

#### analyze renewal
```bash
python3 main_cli.py analyze renewal \
  --account <name> \
  --days <天数>
```
检查即将到期的资源

#### analyze idle
```bash
python3 main_cli.py analyze idle \
  --account <name> \
  --days <天数>
```
分析闲置资源

#### analyze cost
```bash
python3 main_cli.py analyze cost --account <name>
```
成本分析

#### analyze tags
```bash
python3 main_cli.py analyze tags --account <name>
```
标签治理分析

#### analyze security
```bash
python3 main_cli.py analyze security --account <name>
```
安全合规检查

### audit命令组

#### audit permissions
```bash
python3 main_cli.py audit permissions --account <name>
```
审计账号权限

### topology命令组

#### topology generate
```bash
python3 main_cli.py topology generate \
  --account <name> \
  --output <file>
```
生成网络拓扑图

### report命令组

#### report generate
```bash
python3 main_cli.py report generate \
  --account <name> \
  --format <html|excel|pdf> \
  [--output <file>] \
  [--include-idle]
```
生成资源报告

---

## 最佳实践

### 1. 账号命名规范

建议使用有意义的账号名称：

```bash
# ✅ 推荐
--name aliyun-prod-hz
--name aliyun-test-hk
--name tencent-prod-gz

# ❌ 不推荐
--name account1
--name test
```

### 2. 定期巡检

建立定期巡检脚本：

```bash
#!/bin/bash
# daily_check.sh

# 1. 检查即将到期资源
python3 main_cli.py analyze renewal --days 7 > renewal_$(date +%Y%m%d).txt

# 2. 检查闲置资源
python3 main_cli.py analyze idle --days 7 > idle_$(date +%Y%m%d).txt

# 3. 安全检查
python3 main_cli.py analyze security > security_$(date +%Y%m%d).txt

# 4. 如果有问题，发送告警
# ...
```

配置Cron：
```bash
# 每天早上8点执行
0 8 * * * /path/to/daily_check.sh
```

### 3. 使用并发查询

当查询多个账号时，务必使用`--concurrent`：

```bash
# ✅ 快速
python3 main_cli.py query ecs --concurrent

# ❌ 慢
python3 main_cli.py query ecs
```

### 4. 高级筛选技巧

**查找高危资源**：
```bash
# 即将到期且仍在运行的包年包月实例
python3 main_cli.py query ecs --filter "charge_type=PrePaid AND expire_days<7 AND status=Running"
```

**查找成本优化机会**：
```bash
# 按量付费的Running实例（可能适合转包年包月）
python3 main_cli.py query ecs --filter "charge_type=PostPaid AND status=Running"
```

### 5. 报告自动化

**每周生成Excel报告**：
```bash
#!/bin/bash
# weekly_report.sh

DATE=$(date +%Y%m%d)

for account in prod test dev; do
    python3 main_cli.py report generate \
        --account $account \
        --format excel \
        --include-idle \
        --output ${account}_${DATE}.xlsx
done

# 发送邮件或上传到共享盘
# ...
```

### 6. 集成到CI/CD

**GitLab CI示例**：
```yaml
cloud_audit:
  stage: audit
  script:
    - python3 main_cli.py audit permissions --account prod
    - python3 main_cli.py analyze security --account prod
  only:
    - schedules
```

---

## 故障排查

### 常见问题

#### 1. 权限错误

**问题**：
```
❌ Failed to query: InvalidAccessKeyId.NotFound
```

**解决方案**：
- 检查AccessKey是否正确
- 确认账号是否有相应权限
- 运行权限审计：`python3 main_cli.py audit permissions --account xxx`

#### 2. 网络超时

**问题**：
```
❌ Failed to query: RequestTimeout
```

**解决方案**：
- 检查网络连接
- 确认防火墙是否允许访问云API
- 如果需要代理，配置环境变量：
  ```bash
  export http_proxy=http://proxy:8080
  export https_proxy=http://proxy:8080
  ```

#### 3. SDK未安装

**问题**：
```
❌ No module named 'aliyunsdkecs'
```

**解决方案**：
```bash
pip install aliyun-python-sdk-ecs
```

#### 4. Keyring访问失败

**问题**：
```
❌ Failed to access keyring
```

**解决方案**（macOS）：
```bash
# 重置Keyring访问权限
security delete-generic-password -s cloudlens_cli -a aliyun:prod
python3 main_cli.py config add ...  # 重新添加
```

#### 5. Excel生成失败

**问题**：
```
❌ openpyxl not installed
```

**解决方案**：
```bash
pip install openpyxl
```

### 日志查看

启用详细日志：

```bash
# 设置日志级别
export LOG_LEVEL=DEBUG
python3 main_cli.py query ecs --account prod
```

### 获取帮助

```bash
# 查看命令帮助
python3 main_cli.py --help
python3 main_cli.py query --help
python3 main_cli.py query ecs --help
```

---

## 附录

### A. 支持的区域

#### 阿里云
- cn-hangzhou（杭州）
- cn-shanghai（上海）
- cn-beijing（北京）
- cn-shenzhen（深圳）
- cn-hongkong（香港）
- 等更多...

#### 腾讯云
- ap-guangzhou（广州）
- ap-shanghai（上海）
- ap-beijing（北京）
- ap-hongkong（香港）
- 等更多...

### B. 输出格式说明

#### Table（表格）
- 适合：人类阅读
- 特点：直观、易读、彩色

#### JSON
- 适合：程序处理、API集成
- 特点：结构化、机器可读

#### CSV
- 适合：Excel导入、数据分析
- 特点：通用性强、易于统计

#### Excel
- 适合：管理层汇报
- 特点：专业、多Sheet、带样式

### C. 快捷命令别名

可以在 `.bashrc` 或 `.zshrc` 中添加别名：

```bash
alias mc='python3 /path/to/main_cli.py'
alias mcq='python3 /path/to/main_cli.py query'
alias mca='python3 /path/to/main_cli.py analyze'
```

使用：
```bash
mc query ecs --account prod
mcq ecs --concurrent
mca idle --account prod
```

---

## 联系支持

- **GitHub Issues**: 提交Bug或功能请求
- **Pull Request**: 欢迎贡献代码
- **文档**: 查看技术架构文档了解更多细节

**祝您使用愉快！🎉**
