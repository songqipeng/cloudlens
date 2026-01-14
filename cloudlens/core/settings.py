#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudLens 配置管理系统
使用pydantic-settings管理所有配置
支持环境变量、配置文件、默认值
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheSettings(BaseSettings):
    """缓存配置"""

    # TTL配置（秒）
    default_ttl: int = Field(3600, description="默认缓存TTL")
    resource_ttl: int = Field(3600, description="资源缓存TTL")
    monitoring_ttl: int = Field(1800, description="监控数据TTL")
    bill_ttl: int = Field(86400, description="账单缓存TTL")

    # 清理配置
    cleanup_interval: int = Field(3600, description="缓存清理间隔")
    max_size_mb: int = Field(1024, description="最大缓存大小(MB)")


class DatabaseSettings(BaseSettings):
    """数据库配置"""

    # 数据库类型
    db_type: str = Field("mysql", description="数据库类型(mysql/sqlite)")

    # MySQL配置
    mysql_host: str = Field("localhost", description="MySQL主机")
    mysql_port: int = Field(3306, description="MySQL端口")
    mysql_user: str = Field("cloudlens", description="MySQL用户名")
    mysql_password: str = Field("", description="MySQL密码")
    mysql_database: str = Field("cloudlens", description="MySQL数据库名")

    # 连接池配置
    pool_size: int = Field(20, description="连接池大小")
    pool_max_overflow: int = Field(40, description="连接池最大溢出")

    # 超时配置（秒）
    connect_timeout: int = Field(10, description="连接超时")
    query_timeout: int = Field(30, description="查询超时")

    # SQLite配置
    sqlite_path: str = Field("~/.cloudlens/cloudlens.db", description="SQLite数据库路径")

    @field_validator('pool_size')
    @classmethod
    def validate_pool_size(cls, v):
        if v < 1 or v > 100:
            raise ValueError("pool_size必须在1-100之间")
        return v


class APISettings(BaseSettings):
    """API调用配置"""

    # 超时配置（秒）
    default_timeout: int = Field(30, description="默认API超时")
    long_timeout: int = Field(60, description="长API超时")
    short_timeout: int = Field(10, description="短API超时")

    # 重试配置
    max_retries: int = Field(3, description="最大重试次数")
    retry_delay: float = Field(1.0, description="重试延迟(秒)")
    retry_backoff: float = Field(2.0, description="重试退避因子")

    # 并发配置
    max_workers: int = Field(10, description="最大并发worker数")
    max_concurrent_requests: int = Field(20, description="最大并发请求数")

    # 速率限制
    rate_limit_per_second: int = Field(10, description="每秒速率限制")
    rate_limit_per_minute: int = Field(600, description="每分钟速率限制")

    @field_validator('max_workers')
    @classmethod
    def validate_max_workers(cls, v):
        if v < 1 or v > 100:
            raise ValueError("max_workers必须在1-100之间")
        return v


class PerformanceSettings(BaseSettings):
    """性能配置"""

    # 慢查询阈值（秒）
    slow_query_threshold: float = Field(1.0, description="慢查询阈值")
    slow_db_query: float = Field(0.5, description="慢数据库查询")
    slow_api_call: float = Field(2.0, description="慢API调用")
    slow_analysis: float = Field(5.0, description="慢分析任务")

    # 内存限制
    max_memory_mb: int = Field(2048, description="最大内存使用(MB)")

    # 批处理大小
    batch_size: int = Field(1000, description="批处理大小")
    max_batch_size: int = Field(5000, description="最大批处理大小")


class LoggingSettings(BaseSettings):
    """日志配置"""

    # 日志级别
    log_level: str = Field("INFO", description="日志级别")
    console_log_level: str = Field("INFO", description="控制台日志级别")
    file_log_level: str = Field("DEBUG", description="文件日志级别")

    # 日志文件配置
    log_dir: str = Field("logs", description="日志目录")
    log_file: str = Field("cloudlens.log", description="日志文件名")
    max_log_size_mb: int = Field(10, description="单个日志文件最大大小(MB)")
    backup_count: int = Field(5, description="日志备份数量")

    # 日志格式
    log_format: str = Field(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        description="日志格式"
    )

    @field_validator('log_level', 'console_log_level', 'file_log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level必须是{valid_levels}之一")
        return v.upper()


class SecuritySettings(BaseSettings):
    """安全配置"""

    # 凭证存储
    use_keyring: bool = Field(True, description="使用Keyring存储凭证")

    # 输入验证
    max_input_length: int = Field(10000, description="最大输入长度")
    sanitize_input: bool = Field(True, description="清理用户输入")

    # API密钥
    api_key_min_length: int = Field(16, description="API密钥最小长度")
    api_key_max_length: int = Field(128, description="API密钥最大长度")


class Settings(BaseSettings):
    """CloudLens 全局配置"""

    # 应用基本信息
    app_name: str = Field("CloudLens", description="应用名称")
    app_version: str = Field("2.1.0", description="应用版本")
    environment: str = Field("production", description="运行环境")
    debug: bool = Field(False, description="调试模式")

    # 数据目录
    data_dir: str = Field("~/.cloudlens", description="数据目录")

    # 子配置
    cache: CacheSettings = Field(default_factory=CacheSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: APISettings = Field(default_factory=APISettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_prefix='CLOUDLENS_',
        env_nested_delimiter='__',
        case_sensitive=False
    )

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        valid_envs = ['development', 'staging', 'production']
        if v not in valid_envs:
            raise ValueError(f"environment必须是{valid_envs}之一")
        return v

    def get_data_dir(self) -> Path:
        """获取数据目录路径"""
        return Path(self.data_dir).expanduser()

    def ensure_data_dir(self) -> Path:
        """确保数据目录存在"""
        data_dir = self.get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置实例（单例模式）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings():
    """重新加载配置"""
    global _settings
    _settings = Settings()
    return _settings


# 便捷访问函数
def get_cache_settings() -> CacheSettings:
    """获取缓存配置"""
    return get_settings().cache


def get_database_settings() -> DatabaseSettings:
    """获取数据库配置"""
    return get_settings().database


def get_api_settings() -> APISettings:
    """获取API配置"""
    return get_settings().api


def get_performance_settings() -> PerformanceSettings:
    """获取性能配置"""
    return get_settings().performance


def get_logging_settings() -> LoggingSettings:
    """获取日志配置"""
    return get_settings().logging


def get_security_settings() -> SecuritySettings:
    """获取安全配置"""
    return get_settings().security


# 导出配置示例（用于生成.env.example文件）
def generate_env_example():
    """生成.env.example文件"""
    example_content = """# CloudLens 环境配置示例
# 复制此文件为.env并修改配置值

# 应用配置
CLOUDLENS_APP_NAME=CloudLens
CLOUDLENS_APP_VERSION=2.1.0
CLOUDLENS_ENVIRONMENT=production
CLOUDLENS_DEBUG=false

# 数据库配置
CLOUDLENS_DATABASE__DB_TYPE=mysql
CLOUDLENS_DATABASE__MYSQL_HOST=localhost
CLOUDLENS_DATABASE__MYSQL_PORT=3306
CLOUDLENS_DATABASE__MYSQL_USER=cloudlens
CLOUDLENS_DATABASE__MYSQL_PASSWORD=your_password_here
CLOUDLENS_DATABASE__MYSQL_DATABASE=cloudlens
CLOUDLENS_DATABASE__POOL_SIZE=20

# 缓存配置
CLOUDLENS_CACHE__DEFAULT_TTL=3600
CLOUDLENS_CACHE__RESOURCE_TTL=3600
CLOUDLENS_CACHE__MONITORING_TTL=1800

# API配置
CLOUDLENS_API__DEFAULT_TIMEOUT=30
CLOUDLENS_API__MAX_WORKERS=10
CLOUDLENS_API__MAX_RETRIES=3

# 性能配置
CLOUDLENS_PERFORMANCE__SLOW_QUERY_THRESHOLD=1.0
CLOUDLENS_PERFORMANCE__BATCH_SIZE=1000

# 日志配置
CLOUDLENS_LOGGING__LOG_LEVEL=INFO
CLOUDLENS_LOGGING__LOG_DIR=logs
CLOUDLENS_LOGGING__MAX_LOG_SIZE_MB=10

# 安全配置
CLOUDLENS_SECURITY__USE_KEYRING=true
CLOUDLENS_SECURITY__SANITIZE_INPUT=true
"""

    with open('.env.example', 'w') as f:
        f.write(example_content)

    print("✅ 已生成.env.example文件")


if __name__ == "__main__":
    # 测试配置
    settings = get_settings()
    print(f"应用名称: {settings.app_name}")
    print(f"环境: {settings.environment}")
    print(f"数据库类型: {settings.database.db_type}")
    print(f"连接池大小: {settings.database.pool_size}")
    print(f"缓存TTL: {settings.cache.default_ttl}")

    # 生成配置示例
    generate_env_example()
