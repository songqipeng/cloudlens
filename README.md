# 阿里云资源分析工具

## 🚀 项目简介

这是一个模块化的阿里云资源利用率分析工具，可以帮助您识别和优化各种云资源的闲置情况，降低云成本。

## 📋 支持的资源类型

| 资源类型 | 状态 | 描述 |
|---------|------|------|
| **ECS** | ✅ 已完成 | 弹性计算服务 - 云服务器实例分析 |
| **RDS** | ✅ 已完成 | 云数据库RDS - 关系型数据库分析 |
| **Redis** | ✅ 已完成 | 云数据库Redis - 缓存数据库分析 |
| **MongoDB** | ✅ 已完成 | 云数据库MongoDB - 文档数据库分析 |
| **ClickHouse** | ✅ 已完成 | 云数据库ClickHouse - 分析型数据库分析 |
| **OSS** | 🚧 开发中 | 对象存储服务 - 文件存储分析 |
| **SLB** | 🚧 开发中 | 负载均衡 - 流量分发分析 |
| **EIP** | 🚧 开发中 | 弹性公网IP - 公网访问分析 |
| **NAS** | 📋 计划中 | 文件存储NAS - 共享文件系统分析 |
| **ACK** | 📋 计划中 | 容器服务Kubernetes版 - 容器编排分析 |
| **ECI** | 📋 计划中 | 弹性容器实例 - 无服务器容器分析 |
| **EMR** | 📋 计划中 | 大数据服务 - 大数据计算分析 |
| **ARMS** | 📋 计划中 | 应用监控 - 应用性能监控分析 |
| **SLS** | 📋 计划中 | 日志服务 - 日志收集分析 |

## 🛠️ 安装和使用

### 1. 环境要求

```bash
# Python 3.7+
pip install -r requirements.txt
```

### 2. 配置文件

创建 `config.json` 文件：

```json
{
    "access_key_id": "your_access_key_id",
    "access_key_secret": "your_access_key_secret"
}
```

### 3. 使用方法

```bash
# 分析ECS实例（默认）
python main.py ecs

# 分析RDS数据库
python main.py rds

# 分析Redis缓存
python main.py redis

# 分析MongoDB数据库
python main.py mongodb

# 分析ClickHouse数据库
python main.py clickhouse

# 分析所有资源
python main.py all

# 不使用缓存重新分析
python main.py ecs --no-cache

# 指定输出目录
python main.py rds --output-dir ./reports

# 显示帮助信息
python main.py --help
```

## 📊 分析标准

### ECS实例闲置标准（或关系）
- CPU利用率 < 5%
- 内存利用率 < 20%
- Load Average < vCPU * 5%
- 磁盘IOPS < 100
- EIP带宽使用率 < 峰值 * 10%

### RDS实例闲置标准（或关系）
- CPU利用率 < 10%
- 内存利用率 < 20%
- 连接数使用率 < 20%
- QPS < 100
- TPS < 10
- 连接线程数 < 10
- 运行线程数 < 5

### Redis实例闲置标准（或关系）
- CPU利用率 < 10%
- 内存利用率 < 20%
- 连接数使用率 < 20%
- 内网入流量 < 100KB/s
- 内网出流量 < 100KB/s
- 已使用内存 < 10MB

### MongoDB实例闲置标准（或关系）
- CPU利用率 < 10%
- 内存利用率 < 20%
- 磁盘利用率 < 20%
- 连接数使用率 < 20%
- QPS < 100
- IOPS < 100
- 网络入流量 < 1KB/s
- 网络出流量 < 1KB/s

### ClickHouse实例闲置标准（或关系）
- CPU利用率 < 10%
- 内存利用率 < 20%
- 磁盘利用率 < 20%
- 连接数 < 10
- 查询数 < 100
- 插入数 < 50
- 网络入流量 < 1KB/s
- 网络出流量 < 1KB/s
- 磁盘读IOPS < 100
- 磁盘写IOPS < 100

## 📁 项目结构

```
aliyunidle/
├── main.py                          # 主程序入口
├── check_ecs_idle_fixed.py         # ECS分析模块
├── resource_modules/                # 资源分析模块目录
│   ├── __init__.py
│   ├── rds_analyzer.py             # RDS分析模块
│   ├── redis_analyzer.py           # Redis分析模块
│   ├── mongodb_analyzer.py         # MongoDB分析模块
│   ├── clickhouse_analyzer.py      # ClickHouse分析模块
│   └── ...
├── config.json                     # 配置文件
├── requirements.txt                # 依赖包
└── reports/                        # 报告输出目录
    ├── ecs_idle_report_*.html
    ├── ecs_idle_report_*.xlsx
    ├── rds_idle_report_*.html
    ├── rds_idle_report_*.xlsx
    ├── redis_idle_report_*.html
    ├── redis_idle_report_*.xlsx
    ├── mongodb_idle_report_*.html
    ├── mongodb_idle_report_*.xlsx
    ├── clickhouse_idle_report_*.html
    └── clickhouse_idle_report_*.xlsx
```

## 🔧 开发新模块

### 1. 创建分析器类

```python
class ResourceAnalyzer:
    def __init__(self, access_key_id, access_key_secret):
        # 初始化
    
    def analyze_resources(self):
        # 分析资源
    
    def generate_report(self, idle_instances):
        # 生成报告
```

### 2. 实现标准接口

- `get_all_regions()` - 获取所有区域
- `get_resource_instances(region)` - 获取资源实例
- `get_monitoring_data(region, instance_id)` - 获取监控数据
- `is_resource_idle(metrics)` - 判断是否闲置
- `get_optimization_suggestion(metrics)` - 获取优化建议

### 3. 注册到主程序

在 `main.py` 中添加新的资源类型：

```python
def run_new_resource_analysis(args):
    # 实现分析逻辑
    pass
```

## 📈 报告格式

每个资源分析都会生成：

1. **Excel报告** - 详细的数据表格
2. **HTML报告** - 可视化的网页报告
3. **统计信息** - 成本节省估算

## 🎯 优化建议

工具会根据资源使用情况提供优化建议：

- **降配建议** - 降低实例规格
- **合并建议** - 合并小实例
- **删除建议** - 删除完全闲置的资源
- **配置调整** - 调整资源配置参数

## 📞 技术支持

如有问题或建议，请通过以下方式联系：

- 提交Issue到项目仓库
- 发送邮件到技术支持邮箱

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。
