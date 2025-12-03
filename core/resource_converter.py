"""
Helper functions to convert dict resources to UnifiedResource
"""
from models.resource import UnifiedResource, ResourceType, ResourceStatus
from typing import Dict, List

def slb_to_unified_resource(slb: Dict, provider_name: str) -> UnifiedResource:
    """Convert SLB dict to UnifiedResource"""
    # 公网SLB才添加 public_ips
    public_ips = [slb['Address']] if slb.get('AddressType') == 'internet' else []
    private_ips = [slb['Address']] if slb.get('AddressType') == 'intranet' else []
    
    return UnifiedResource(
        id=slb['LoadBalancerId'],
        name=slb.get('LoadBalancerName', slb['LoadBalancerId']),
        provider=provider_name,
        region=slb.get('RegionId', ''),
        resource_type=ResourceType.SLB,
        status=ResourceStatus.RUNNING if slb.get('LoadBalancerStatus') == 'active' else ResourceStatus.UNKNOWN,
        public_ips=public_ips,
        private_ips=private_ips,
        vpc_id=slb.get('VpcId'),
        raw_data=slb
    )

def nat_gateway_to_unified_resource(nat: Dict, provider_name: str, region: str) -> UnifiedResource:
    """Convert NAT Gateway dict to UnifiedResource"""
    # 提取所有公网IP
    public_ips = []
    if nat.get('IpLists', {}).get('IpList'):
        for ip_info in nat['IpLists']['IpList']:
            if ip_info.get('IpAddress'):
                public_ips.append(ip_info['IpAddress'])
    
    return UnifiedResource(
        id=nat.get('NatGatewayId', ''),
        name=nat.get('Name', nat.get('NatGatewayId', '')),
        provider=provider_name,
        region=region,
        resource_type=ResourceType.NAT,
        status=ResourceStatus.RUNNING if nat.get('Status') == 'Available' else ResourceStatus.UNKNOWN,
        public_ips=public_ips,
        vpc_id=nat.get('VpcId'),
        raw_data=nat
    )

def mongodb_to_unified_resource(mongo: Dict, provider_name: str, region: str) -> UnifiedResource:
    """Convert MongoDB dict to UnifiedResource"""
    # 提取公网连接串
    public_ips = []
    private_ips = []
    
    if mongo.get('PublicConnectionString'):
        public_ips.append(mongo['PublicConnectionString'])
    if mongo.get('ConnectionString'):
        private_ips.append(mongo['ConnectionString'])
    
    status_map = {
        "Running": ResourceStatus.RUNNING,
        "Creating": ResourceStatus.STARTING,
        "Deleting": ResourceStatus.STOPPING,
    }
    
    return UnifiedResource(
        id=mongo.get('DBInstanceId', ''),
        name=mongo.get('DBInstanceDescription', mongo.get('DBInstanceId', '')),
        provider=provider_name,
        region=region,
        resource_type=ResourceType.MONGODB,
        status=status_map.get(mongo.get('DBInstanceStatus'), ResourceStatus.UNKNOWN),
        public_ips=public_ips,
        private_ips=private_ips,
        spec=mongo.get('DBInstanceClass'),
        raw_data=mongo
    )
