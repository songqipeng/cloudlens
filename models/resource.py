from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class ResourceType(Enum):
    ECS = "ecs"
    RDS = "rds"
    REDIS = "redis"
    OSS = "oss"
    VPC = "vpc"
    EIP = "eip"
    SLB = "slb"
    UNKNOWN = "unknown"

class ResourceStatus(Enum):
    RUNNING = "Running"
    STOPPED = "Stopped"
    STARTING = "Starting"
    STOPPING = "Stopping"
    DELETED = "Deleted"
    UNKNOWN = "Unknown"

@dataclass
class UnifiedResource:
    """
    统一资源模型，屏蔽不同云厂商的字段差异
    """
    id: str
    name: str
    provider: str  # aliyun, tencent, aws, volcano
    region: str
    zone: Optional[str] = None
    resource_type: ResourceType = ResourceType.UNKNOWN
    status: ResourceStatus = ResourceStatus.UNKNOWN
    
    # 网络信息
    private_ips: List[str] = field(default_factory=list)
    public_ips: List[str] = field(default_factory=list)
    vpc_id: Optional[str] = None
    
    # 规格与计费
    spec: Optional[str] = None  # e.g., ecs.g6.large
    cpu: int = 0
    memory: int = 0  # MB
    charge_type: str = "PostPaid"  # PrePaid, PostPaid
    
    # 时间信息
    created_time: Optional[datetime] = None
    expired_time: Optional[datetime] = None  # 包年包月到期时间
    
    # 原始数据 (用于调试或特殊字段)
    raw_data: Dict = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "region": self.region,
            "type": self.resource_type.value,
            "status": self.status.value,
            "ip": ", ".join(self.public_ips if self.public_ips else self.private_ips),
            "spec": self.spec,
            "charge_type": self.charge_type,
            "expired_time": self.expired_time.strftime("%Y-%m-%d") if self.expired_time else "N/A"
        }
