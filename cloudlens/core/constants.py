#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudLens 常量定义
集中管理所有魔法数字和字符串常量
"""

from enum import Enum


# ===========================================
# 1. 闲置资源检测阈值
# ===========================================

class IdleThresholds:
    """闲置资源检测阈值"""

    # CPU利用率阈值（百分比）
    CPU_UTILIZATION = 5.0

    # 内存利用率阈值（百分比）
    MEMORY_UTILIZATION = 20.0

    # 网络流量阈值（字节/秒）
    NETWORK_BYTES_PER_SEC = 1000

    # 磁盘IOPS阈值
    DISK_READ_IOPS = 100
    DISK_WRITE_IOPS = 100

    # 监控数据查询天数
    MONITORING_DAYS = 14

    # 判定闲置的最小满足条件数
    MIN_IDLE_CONDITIONS = 2


# ===========================================
# 2. 续费紧急程度
# ===========================================

class RenewalUrgency:
    """续费紧急程度定义"""

    # 天数阈值
    CRITICAL_DAYS = 7      # 7天内到期：紧急
    IMPORTANT_DAYS = 14    # 14天内到期：重要
    NORMAL_DAYS = 30       # 30天内到期：关注

    # 标签
    CRITICAL_LABEL = "🔴 紧急"
    IMPORTANT_LABEL = "🟠 重要"
    NORMAL_LABEL = "🟡 关注"

    # 颜色代码
    CRITICAL_COLOR = "#FF0000"
    IMPORTANT_COLOR = "#FF8C00"
    NORMAL_COLOR = "#FFD700"


# ===========================================
# 3. 缓存配置
# ===========================================

class CacheConfig:
    """缓存配置常量"""

    # TTL（秒）
    DEFAULT_TTL = 3600              # 1小时
    SHORT_TTL = 300                 # 5分钟
    LONG_TTL = 86400                # 24小时

    # 资源缓存TTL
    RESOURCE_CACHE_TTL = 3600       # 1小时
    MONITORING_CACHE_TTL = 1800     # 30分钟
    BILL_CACHE_TTL = 86400          # 24小时

    # 清理间隔
    CLEANUP_INTERVAL = 3600         # 1小时清理一次过期缓存


# ===========================================
# 4. 数据库配置
# ===========================================

class DatabaseConfig:
    """数据库配置常量"""

    # 连接池大小
    POOL_SIZE = 10
    POOL_MAX_OVERFLOW = 20

    # 连接超时（秒）
    CONNECT_TIMEOUT = 10
    QUERY_TIMEOUT = 30

    # 批量操作大小
    BATCH_SIZE = 1000
    MAX_BATCH_SIZE = 5000


# ===========================================
# 5. API配置
# ===========================================

class APIConfig:
    """API调用配置"""

    # 超时时间（秒）
    DEFAULT_TIMEOUT = 30
    LONG_TIMEOUT = 60
    SHORT_TIMEOUT = 10

    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    RETRY_BACKOFF = 2.0

    # 并发配置
    MAX_WORKERS = 10
    MAX_CONCURRENT_REQUESTS = 20

    # 速率限制
    RATE_LIMIT_PER_SECOND = 10
    RATE_LIMIT_PER_MINUTE = 600


# ===========================================
# 6. 文件大小限制
# ===========================================

class FileSizeLimit:
    """文件大小限制"""

    # 报告文件大小限制（字节）
    MAX_REPORT_SIZE = 100 * 1024 * 1024      # 100MB
    MAX_EXCEL_SIZE = 50 * 1024 * 1024        # 50MB
    MAX_JSON_SIZE = 20 * 1024 * 1024         # 20MB

    # 日志文件大小
    MAX_LOG_SIZE = 10 * 1024 * 1024          # 10MB
    LOG_BACKUP_COUNT = 5


# ===========================================
# 7. 性能阈值
# ===========================================

class PerformanceThresholds:
    """性能阈值定义"""

    # 慢查询阈值（秒）
    SLOW_QUERY_THRESHOLD = 1.0
    SLOW_DB_QUERY = 0.5
    SLOW_API_CALL = 2.0
    SLOW_ANALYSIS = 5.0

    # 内存使用阈值
    MAX_MEMORY_MB = 2048


# ===========================================
# 8. 资源类型枚举
# ===========================================

class ResourceType(str, Enum):
    """支持的资源类型"""

    # 计算资源
    ECS = "ecs"
    ECI = "eci"
    ACK = "ack"

    # 数据库
    RDS = "rds"
    REDIS = "redis"
    MONGODB = "mongodb"
    CLICKHOUSE = "clickhouse"
    POLARDB = "polardb"

    # 存储
    OSS = "oss"
    NAS = "nas"
    DISK = "disk"

    # 网络
    VPC = "vpc"
    EIP = "eip"
    SLB = "slb"
    NAT = "nat"
    VPN = "vpn"

    # 其他
    CDN = "cdn"
    DNS = "dns"


# ===========================================
# 9. 云平台类型
# ===========================================

class CloudProvider(str, Enum):
    """支持的云平台"""

    ALIYUN = "aliyun"
    TENCENT = "tencent"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    HUAWEI = "huawei"


# ===========================================
# 10. 告警级别
# ===========================================

class AlertSeverity(str, Enum):
    """告警严重程度"""

    CRITICAL = "critical"    # 严重
    HIGH = "high"            # 高
    MEDIUM = "medium"        # 中
    LOW = "low"              # 低
    INFO = "info"            # 信息


class AlertStatus(str, Enum):
    """告警状态"""

    PENDING = "pending"      # 待处理
    ACKNOWLEDGED = "acknowledged"  # 已确认
    RESOLVED = "resolved"    # 已解决
    IGNORED = "ignored"      # 已忽略


# ===========================================
# 11. 报告格式
# ===========================================

class ReportFormat(str, Enum):
    """报告输出格式"""

    EXCEL = "excel"
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"


# ===========================================
# 12. 费用类型
# ===========================================

class ChargeType(str, Enum):
    """计费类型"""

    PREPAID = "PrePaid"      # 包年包月
    POSTPAID = "PostPaid"    # 按量付费


# ===========================================
# 13. 时间格式
# ===========================================

class DateFormat:
    """日期时间格式"""

    # 日期格式
    DATE = "%Y-%m-%d"
    MONTH = "%Y-%m"
    YEAR = "%Y"

    # 时间格式
    TIME = "%H:%M:%S"
    DATETIME = "%Y-%m-%d %H:%M:%S"

    # ISO格式
    ISO8601 = "%Y-%m-%dT%H:%M:%SZ"
    ISO8601_MS = "%Y-%m-%dT%H:%M:%S.%fZ"

    # 文件名安全格式
    FILENAME = "%Y%m%d_%H%M%S"


# ===========================================
# 14. HTTP状态码
# ===========================================

class HTTPStatus:
    """HTTP状态码"""

    # 2xx 成功
    OK = 200
    CREATED = 201
    NO_CONTENT = 204

    # 4xx 客户端错误
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422

    # 5xx 服务器错误
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


# ===========================================
# 15. 正则表达式模式
# ===========================================

class RegexPattern:
    """常用正则表达式"""

    # 邮箱
    EMAIL = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    # IP地址
    IPV4 = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

    # 账号名称
    ACCOUNT_NAME = r'^[a-zA-Z0-9_-]{1,128}$'

    # 实例ID
    INSTANCE_ID = r'^[a-z]+-[a-z0-9]+$'


# ===========================================
# 16. 错误消息
# ===========================================

class ErrorMessage:
    """标准错误消息"""

    # 通用错误
    INVALID_INPUT = "输入参数无效"
    MISSING_REQUIRED_FIELD = "缺少必需字段: {field}"
    OPERATION_FAILED = "操作失败: {reason}"

    # 账号相关
    ACCOUNT_NOT_FOUND = "账号不存在: {account}"
    ACCOUNT_ALREADY_EXISTS = "账号已存在: {account}"
    INVALID_CREDENTIALS = "凭证验证失败"

    # 资源相关
    RESOURCE_NOT_FOUND = "资源不存在: {resource_id}"
    RESOURCE_TYPE_NOT_SUPPORTED = "不支持的资源类型: {resource_type}"

    # 数据库相关
    DB_CONNECTION_FAILED = "数据库连接失败"
    DB_QUERY_FAILED = "数据库查询失败: {error}"
    DB_TRANSACTION_FAILED = "事务执行失败"

    # API相关
    API_CALL_FAILED = "API调用失败: {error}"
    API_TIMEOUT = "API调用超时"
    API_RATE_LIMIT = "API调用频率超限"


# ===========================================
# 17. 成功消息
# ===========================================

class SuccessMessage:
    """标准成功消息"""

    CREATED = "创建成功"
    UPDATED = "更新成功"
    DELETED = "删除成功"
    SAVED = "保存成功"
    IMPORTED = "导入成功"
    EXPORTED = "导出成功"
