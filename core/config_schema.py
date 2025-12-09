# -*- coding: utf-8 -*-
"""
配置文件Schema定义

使用Pydantic进行配置验证
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ProviderType(str, Enum):
    """支持的云厂商类型"""

    ALIYUN = "aliyun"
    TENCENT = "tencent"
    AWS = "aws"
    VOLCANO = "volcano"


class CloudAccountSchema(BaseModel):
    """云账号配置Schema"""

    name: str = Field(..., description="账号别名", min_length=1, max_length=50)
    provider: ProviderType = Field(..., description="云厂商")
    region: str = Field(..., description="默认区域", min_length=1)
    access_key_id: str = Field(..., description="AccessKey ID", min_length=10)
    access_key_secret: Optional[str] = Field(None, description="Secret Key (可选，从Keyring获取)")

    @validator("name")
    def validate_name(cls, v):
        """验证账号名称"""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("账号名称只能包含字母、数字、横线和下划线")
        return v

    @validator("region")
    def validate_region(cls, v, values):
        """验证region格式"""
        provider = values.get("provider")

        if provider == ProviderType.ALIYUN:
            # 阿里云region格式: cn-hangzhou, us-west-1等
            if not (v.startswith("cn-") or v.startswith("us-") or v.startswith("ap-")):
                raise ValueError(f"无效的阿里云region: {v}")
        elif provider == ProviderType.TENCENT:
            # 腾讯云region格式: ap-guangzhou等
            if not v.startswith("ap-"):
                raise ValueError(f"无效的腾讯云region: {v}")

        return v

    class Config:
        use_enum_values = True


class CacheConfig(BaseModel):
    """缓存配置Schema"""

    enabled: bool = Field(True, description="是否启用缓存")
    ttl: int = Field(3600, description="缓存过期时间（秒）", gt=0)
    max_size: int = Field(1000, description="最大缓存条目数", gt=0)


class MonitoringConfig(BaseModel):
    """监控配置Schema"""

    default_days: int = Field(14, description="默认监控天数", gt=0, le=90)
    metrics_interval: int = Field(300, description="指标采集间隔（秒）", gt=0)


class ReportConfig(BaseModel):
    """报告配置Schema"""

    output_format: List[str] = Field(["json", "html"], description="输出格式")
    output_dir: str = Field("reports", description="报告输出目录")

    @validator("output_format")
    def validate_format(cls, v):
        """验证输出格式"""
        valid_formats = ["json", "csv", "html", "pdf", "xlsx"]
        for fmt in v:
            if fmt not in valid_formats:
                raise ValueError(f"不支持的格式: {fmt}. 支持: {valid_formats}")
        return v


class ConfigFileSchema(BaseModel):
    """完整配置文件Schema"""

    accounts: List[CloudAccountSchema] = Field([], description="云账号列表")
    cache: Optional[CacheConfig] = Field(default_factory=CacheConfig, description="缓存配置")
    monitoring: Optional[MonitoringConfig] = Field(
        default_factory=MonitoringConfig, description="监控配置"
    )
    report: Optional[ReportConfig] = Field(default_factory=ReportConfig, description="报告配置")

    @validator("accounts")
    def validate_unique_names(cls, v):
        """验证账号名称唯一性"""
        names = [acc.name for acc in v]
        if len(names) != len(set(names)):
            raise ValueError("账号名称必须唯一")
        return v

    class Config:
        schema_extra = {
            "example": {
                "accounts": [
                    {
                        "name": "my-aliyun",
                        "provider": "aliyun",
                        "region": "cn-hangzhou",
                        "access_key_id": "LTAI****************",
                    }
                ],
                "cache": {"enabled": True, "ttl": 3600},
                "monitoring": {"default_days": 14},
                "report": {"output_format": ["json", "html"], "output_dir": "reports"},
            }
        }
