"""
Summary of Aliyun products with potential public IP exposure
"""

# 已实现公网检测的产品
IMPLEMENTED = [
    "ECS - 云服务器",
    "RDS - 关系型数据库",
    "Redis - 缓存数据库",
]

# 需要添加检测的产品（已发现有实例）
TODO_HIGH_PRIORITY = [
    "NAT Gateway - NAT网关 (8个实例, 都有公网IP)",
    "SLB - 负载均衡器 (需要修复API bug)",
    "MongoDB - 文档数据库 (8个实例)",
]

# 需要安装SDK才能检测
TODO_NEED_SDK = [
    "PolarDB - 云原生数据库 (需要 aliyunsdkpolardb)",
    "Elasticsearch - 搜索服务 (需要 aliyunsdkelasticsearch)",
]

# 其他可能有公网IP的产品
TODO_LOW_PRIORITY = [
    "OSS - 对象存储 (bucket可能有公网访问)",
    "API Gateway - API网关",
    "AnalyticDB - 分析型数据库",
    "HBase - NoSQL数据库",
    "ClickHouse - 列式数据库",
]
