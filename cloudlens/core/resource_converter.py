"""
Helper functions to convert dict resources to UnifiedResource
"""

from typing import Dict, List

from cloudlens.models.resource import ResourceStatus, ResourceType, UnifiedResource

def oss_bucket_to_unified_resource(bucket_data: dict, region_id: str) -> UnifiedResource:
    """
    将OSS Bucket转换为UnifiedResource
    """
    # 提取基本信息
    name = bucket_data.get("Name", "unknown-bucket")
    creation_date = bucket_data.get("CreationDate", "")
    storage_class = bucket_data.get("StorageClass", "Standard")
    location = bucket_data.get("Location", region_id)
    
    # 提取额外信息 (ACL, Owner)
    acl = bucket_data.get("AccessControlList", {}).get("Grant", "private") # 默认private较为安全
    owner = bucket_data.get("Owner", {}).get("DisplayName", "")
    
    # Merge extra info into raw_data
    raw_data = bucket_data.copy()
    raw_data.update({
        "acl": acl,
        "owner": owner,
        "endpoint": bucket_data.get("ExtranetEndpoint", "")
    })

    return UnifiedResource(
        id=name, # Bucket Name is unique globally
        name=name,
        provider="aliyun",
        resource_type=ResourceType.OSS_BUCKET,
        status=ResourceStatus.RUNNING,  # OSS bucket 默认状态为运行中
        region=location,
        zone="", # OSS is regional
        created_time=creation_date,
        tags={}, 
        spec=storage_class,
        public_ips=[],
        private_ips=[],
        vpc_id="",
        raw_data=raw_data
    )


def slb_to_unified_resource(slb: Dict, provider_name: str) -> UnifiedResource:
    """Convert SLB dict to UnifiedResource"""
    # 公网SLB才添加 public_ips
    public_ips = [slb["Address"]] if slb.get("AddressType") == "internet" else []
    private_ips = [slb["Address"]] if slb.get("AddressType") == "intranet" else []

    return UnifiedResource(
        id=slb["LoadBalancerId"],
        name=slb.get("LoadBalancerName", slb["LoadBalancerId"]),
        provider=provider_name,
        region=slb.get("RegionId", ""),
        resource_type=ResourceType.SLB,
        status=(
            ResourceStatus.RUNNING
            if slb.get("LoadBalancerStatus") == "active"
            else ResourceStatus.UNKNOWN
        ),
        public_ips=public_ips,
        private_ips=private_ips,
        vpc_id=slb.get("VpcId"),
        raw_data=slb,
    )


def nat_gateway_to_unified_resource(nat: Dict, provider_name: str, region: str) -> UnifiedResource:
    """Convert NAT Gateway dict to UnifiedResource"""
    # 提取所有公网IP
    public_ips = []
    if nat.get("IpLists", {}).get("IpList"):
        for ip_info in nat["IpLists"]["IpList"]:
            if ip_info.get("IpAddress"):
                public_ips.append(ip_info["IpAddress"])

    return UnifiedResource(
        id=nat.get("NatGatewayId", ""),
        name=nat.get("Name", nat.get("NatGatewayId", "")),
        provider=provider_name,
        region=region,
        resource_type=ResourceType.NAT,
        status=(
            ResourceStatus.RUNNING if nat.get("Status") == "Available" else ResourceStatus.UNKNOWN
        ),
        public_ips=public_ips,
        vpc_id=nat.get("VpcId"),
        raw_data=nat,
    )


def mongodb_to_unified_resource(mongo: Dict, provider_name: str, region: str) -> UnifiedResource:
    """Convert MongoDB dict to UnifiedResource"""
    # 提取公网连接串
    public_ips = []
    private_ips = []

    if mongo.get("PublicConnectionString"):
        public_ips.append(mongo["PublicConnectionString"])
    if mongo.get("ConnectionString"):
        private_ips.append(mongo["ConnectionString"])

    status_map = {
        "Running": ResourceStatus.RUNNING,
        "Creating": ResourceStatus.STARTING,
        "Deleting": ResourceStatus.STOPPING,
    }

    return UnifiedResource(
        id=mongo.get("DBInstanceId", ""),
        name=mongo.get("DBInstanceDescription", mongo.get("DBInstanceId", "")),
        provider=provider_name,
        region=region,
        resource_type=ResourceType.MONGODB,
        status=status_map.get(mongo.get("DBInstanceStatus"), ResourceStatus.UNKNOWN),
        public_ips=public_ips,
        private_ips=private_ips,
        spec=mongo.get("DBInstanceClass"),
        raw_data=mongo,
    )
