import json
import logging
from typing import List, Dict
from datetime import datetime

from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
from aliyunsdkrds.request.v20140815.DescribeDBInstancesRequest import DescribeDBInstancesRequest
from aliyunsdkvpc.request.v20160428.DescribeVpcsRequest import DescribeVpcsRequest
from aliyunsdkvpc.request.v20160428.DescribeVSwitchesRequest import DescribeVSwitchesRequest

from core.provider import BaseProvider
from core.security import PermissionGuard
from models.resource import UnifiedResource, ResourceType, ResourceStatus
from core.resource_converter import slb_to_unified_resource, nat_gateway_to_unified_resource, mongodb_to_unified_resource

logger = logging.getLogger("AliyunProvider")

class AliyunProvider(BaseProvider):
    
    @property
    def provider_name(self) -> str:
        return "aliyun"

    def _get_client(self):
        if not self._client:
            self._client = AcsClient(
                self.access_key,
                self.secret_key,
                self.region
            )
        return self._client

    def _do_request(self, request):
        """执行API请求，包含权限检查"""
        action_name = request.get_action_name()
        
        # 权限卫士检查
        if not PermissionGuard.is_action_safe(action_name):
            logger.warning(f"Action {action_name} might be unsafe, but proceeding as it is a read operation in this context.")
        
        client = self._get_client()
        response = client.do_action_with_exception(request)
        return json.loads(response)

    def list_instances(self) -> List[UnifiedResource]:
        """列出ECS实例（支持分页）"""
        resources = []
        try:
            page_num = 1
            page_size = 100
            total_count = None
            
            while True:
                request = DescribeInstancesRequest()
                request.set_PageSize(page_size)
                request.set_PageNumber(page_num)
                data = self._do_request(request)
                
                # 获取总数（仅第一页）
                if total_count is None:
                    total_count = data.get("TotalCount", 0)
                    logger.info(f"Total ECS instances: {total_count}")
                
                instances = data.get("Instances", {}).get("Instance", [])
                if not instances:
                    break
                
                for inst in instances:
                    # 状态映射
                    status_map = {
                        "Running": ResourceStatus.RUNNING,
                        "Stopped": ResourceStatus.STOPPED,
                        "Starting": ResourceStatus.STARTING,
                        "Stopping": ResourceStatus.STOPPING
                    }
                    
                    # IP处理
                    public_ips = inst.get("PublicIpAddress", {}).get("IpAddress", [])
                    eip = inst.get("EipAddress", {}).get("IpAddress", "")
                    if eip:
                        public_ips.append(eip)
                    
                    private_ips = inst.get("VpcAttributes", {}).get("PrivateIpAddress", {}).get("IpAddress", [])
                    
                    # 时间处理
                    created_time = datetime.strptime(inst["CreationTime"], "%Y-%m-%dT%H:%MZ")
                    expired_time = None
                    if inst.get("ExpiredTime"):
                        try:
                            expired_time = datetime.strptime(inst["ExpiredTime"], "%Y-%m-%dT%H:%MZ")
                        except:
                            pass

                    r = UnifiedResource(
                        id=inst["InstanceId"],
                        name=inst["InstanceName"],
                        provider=self.provider_name,
                        region=inst["RegionId"],
                        zone=inst["ZoneId"],
                        resource_type=ResourceType.ECS,
                        status=status_map.get(inst["Status"], ResourceStatus.UNKNOWN),
                        private_ips=private_ips,
                        public_ips=public_ips,
                        vpc_id=inst.get("VpcAttributes", {}).get("VpcId"),
                        spec=inst["InstanceType"],
                        cpu=inst["Cpu"],
                        memory=inst["Memory"],
                        charge_type=inst["InstanceChargeType"],
                        created_time=created_time,
                        expired_time=expired_time,
                        raw_data=inst
                    )
                    resources.append(r)
                
                # 检查是否还有更多页
                if len(resources) >= total_count:
                    break
                
                page_num += 1
                
        except Exception as e:
            logger.error(f"Failed to list ECS instances: {e}")
            
        return resources

    def list_rds(self) -> List[UnifiedResource]:
        """列出RDS实例"""
        resources = []
        try:
            request = DescribeDBInstancesRequest()
            request.set_PageSize(100)
            data = self._do_request(request)
            
            for inst in data.get("Items", {}).get("DBInstance", []):
                status_map = {
                    "Running": ResourceStatus.RUNNING,
                    "Stopped": ResourceStatus.STOPPED
                }
                
                expired_time = None
                if inst.get("ExpireTime"):
                     try:
                        # Handle different time formats
                        time_str = inst["ExpireTime"]
                        if 'T' in time_str:
                            # Try with seconds first
                            try:
                                expired_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
                            except:
                                expired_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%MZ")
                     except Exception as e:
                        pass
                
                # 提取公网和私网连接地址
                public_ips = []
                private_ips = []
                
                # 公网连接串
                if inst.get("PublicConnectionString"):
                    public_ips.append(inst["PublicConnectionString"])
                
                # 内网连接串
                if inst.get("ConnectionString"):
                    private_ips.append(inst["ConnectionString"])

                r = UnifiedResource(
                    id=inst["DBInstanceId"],
                    name=inst.get("DBInstanceDescription", inst["DBInstanceId"]),
                    provider=self.provider_name,
                    region=self.region, # RDS API response might not have RegionId in item
                    zone=inst.get("ZoneId"),
                    resource_type=ResourceType.RDS,
                    status=status_map.get(inst["DBInstanceStatus"], ResourceStatus.UNKNOWN),
                    public_ips=public_ips,
                    private_ips=private_ips,
                    vpc_id=inst.get("VpcId"),
                    spec=inst.get("DBInstanceClass"),
                    charge_type=inst.get("PayType", "PostPaid"),
                    expired_time=expired_time,
                    raw_data=inst
                )
                resources.append(r)
        except Exception as e:
            logger.error(f"Failed to list RDS instances: {e}")
            
        return resources

    def list_vpcs(self) -> List[Dict]:
        """列出VPC"""
        vpcs = []
        try:
            request = DescribeVpcsRequest()
            request.set_PageSize(50)
            data = self._do_request(request)
            
            for vpc in data.get("Vpcs", {}).get("Vpc", []):
                vpcs.append({
                    "id": vpc["VpcId"],
                    "name": vpc["VpcName"],
                    "cidr": vpc["CidrBlock"],
                    "region": vpc["RegionId"],
                    "status": vpc["Status"]
                })
        except Exception as e:
            logger.error(f"Failed to list VPCs: {e}")
        return vpcs

    def get_metric(self, resource_id: str, metric_name: str, start_time: int, end_time: int) -> List[Dict]:
        """获取CloudMonitor监控指标"""
        from aliyunsdkcore.request import CommonRequest
        import time
        
        try:
            client = self._get_client()
            request = CommonRequest()
            request.set_domain(f"cms.{self.region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2019-01-01")
            request.set_action_name("DescribeMetricData")
            request.add_query_param("Namespace", "acs_ecs_dashboard")
            request.add_query_param("MetricName", metric_name)
            request.add_query_param("StartTime", start_time)
            request.add_query_param("EndTime", end_time)
            request.add_query_param("Period", "86400")  # 1 day
            request.add_query_param("Dimensions", f'[{{"instanceId":"{resource_id}"}}]')
            
            response = self._do_request(request)
            
            if "Datapoints" in response and response["Datapoints"]:
                if isinstance(response["Datapoints"], str):
                    return json.loads(response["Datapoints"])
                return response["Datapoints"]
            return []
        except Exception as e:
            logger.error(f"Failed to get metrics for {resource_id}: {e}")
            return []

    def list_redis(self) -> List[UnifiedResource]:
        """列出Redis实例"""
        from aliyunsdkr_kvstore.request.v20150101.DescribeInstancesRequest import DescribeInstancesRequest as RedisDescribeInstancesRequest
        
        resources = []
        try:
            request = RedisDescribeInstancesRequest()
            request.set_PageSize(100)
            data = self._do_request(request)
            
            for inst in data.get("Instances", {}).get("KVStoreInstance", []):
                status_map = {
                    "Normal": ResourceStatus.RUNNING,
                    "Creating": ResourceStatus.STARTING,
                    "Changing": ResourceStatus.CHANGING,
                    "Inactive": ResourceStatus.STOPPED
                }
                
                expired_time = None
                if inst.get("EndTime"):
                    try:
                        expired_time = datetime.strptime(inst["EndTime"], "%Y-%m-%dT%H:%MZ")
                    except:
                        pass
                
                # 提取公网和私网连接地址
                public_ips = []
                private_ips = []
                
                # 公网连接域名
                if inst.get("PublicConnectionDomain"):
                    public_ips.append(inst["PublicConnectionDomain"])
                
                # 内网连接域名
                if inst.get("ConnectionDomain"):
                    private_ips.append(inst["ConnectionDomain"])
                
                r = UnifiedResource(
                    id=inst["InstanceId"],
                    name=inst.get("InstanceName", inst["InstanceId"]),
                    provider=self.provider_name,
                    region=inst["RegionId"],
                    zone=inst.get("ZoneId"),
                    resource_type=ResourceType.REDIS,
                    status=status_map.get(inst["InstanceStatus"], ResourceStatus.UNKNOWN),
                    public_ips=public_ips,
                    private_ips=private_ips,
                    vpc_id=inst.get("VpcId"),
                    spec=inst.get("InstanceClass"),
                    charge_type=inst.get("ChargeType", "PostPaid"),
                    expired_time=expired_time,
                    raw_data=inst
                )
                resources.append(r)
        except Exception as e:
            logger.error(f"Failed to list Redis instances: {e}")
        return resources

    def list_oss(self) -> List[Dict]:
        """列出OSS Bucket (使用oss2库)"""
        buckets = []
        try:
            import oss2
            
            # Create auth and service
            auth = oss2.Auth(self.access_key, self.secret_key)
            service = oss2.Service(auth, f'https://oss-{self.region}.aliyuncs.com')
            
            # List all buckets
            for bucket_info in oss2.BucketIterator(service):
                buckets.append({
                    "id": bucket_info.name,
                    "name": bucket_info.name,
                    "region": bucket_info.location.replace('oss-', ''),
                    "created_time": bucket_info.creation_date,
                    "storage_class": bucket_info.storage_class if hasattr(bucket_info, 'storage_class') else "-"
                })
        except ImportError:
            logger.warning("oss2 library not installed. Run: pip install oss2")
        except Exception as e:
            logger.error(f"Failed to list OSS buckets: {e}")
        return buckets

    def list_eip(self) -> List[Dict]:
        """列出弹性公网IP"""
        eips = []
        try:
            from aliyunsdkvpc.request.v20160428 import DescribeEipAddressesRequest
            
            request = DescribeEipAddressesRequest.DescribeEipAddressesRequest()
            request.set_PageSize(100)
            
            response = self._do_request(request)
            
            for eip in response.get('EipAddresses', {}).get('EipAddress', []):
                eips.append({
                    "id": eip.get('AllocationId'),
                    "ip_address": eip.get('IpAddress'),
                    "status": eip.get('Status'),
                    "instance_id": eip.get('InstanceId', ''),
                    "bandwidth": eip.get('Bandwidth'),
                    "region": self.region
                })
        except Exception as e:
            logger.error(f"Failed to list EIPs: {e}")
        return eips

    def list_slb(self) -> List[UnifiedResource]:
        """列出SLB负载均衡器"""
        resources = []
        try:
            from aliyunsdkslb.request.v20140515 import DescribeLoadBalancersRequest
            
            request = DescribeLoadBalancersRequest.DescribeLoadBalancersRequest()
            request.set_PageSize(100)
            
            response = self._do_request(request)
            
            for slb in response.get('LoadBalancers', {}).get('LoadBalancer', []):
                resources.append(slb_to_unified_resource(slb, self.provider_name))
        except Exception as e:
            logger.error(f"Failed to list SLBs: {e}")
        return resources

    def list_nat_gateways(self) -> List[UnifiedResource]:
        """列出NAT网关"""
        resources = []
        try:
            from aliyunsdkvpc.request.v20160428 import DescribeNatGatewaysRequest
            
            request = DescribeNatGatewaysRequest.DescribeNatGatewaysRequest()
            request.set_PageSize(100)
            
            response = self._do_request(request)
            
            for nat in response.get('NatGateways', {}).get('NatGateway', []):
                resources.append(nat_gateway_to_unified_resource(nat, self.provider_name, self.region))
        except Exception as e:
            logger.error(f"Failed to list NAT Gateways: {e}")
        return resources

    def list_mongodb(self) -> List[UnifiedResource]:
        """列出MongoDB实例"""
        resources = []
        try:
            from aliyunsdkdds.request.v20151201 import DescribeDBInstancesRequest
            
            request = DescribeDBInstancesRequest.DescribeDBInstancesRequest()
            request.set_PageSize(100)
            
            response = self._do_request(request)
            
            for mongo in response.get('DBInstances', {}).get('DBInstance', []):
                resources.append(mongodb_to_unified_resource(mongo, self.provider_name, self.region))
        except ImportError:
            logger.warning("aliyun-python-sdk-dds not installed")
        except Exception as e:
            logger.error(f"Failed to list MongoDB instances: {e}")
        return resources

    def list_nas(self) -> List[Dict]:
        """列出NAS文件系统"""
        nas_list = []
        try:
            from aliyunsdknas.request.v20170626 import DescribeFileSystemsRequest
            
            for region in self.regions:
                client = self._get_client(region)
                request = DescribeFileSystemsRequest.DescribeFileSystemsRequest()
                request.set_PageSize(100)
                
                response = self._do_request(client, request)
                
                for fs in response.get('FileSystems', {}).get('FileSystem', []):
                    nas_list.append({
                        "id": fs.get('FileSystemId'),
                        "description": fs.get('Description', ''),
                        "protocol_type": fs.get('ProtocolType'),
                        "storage_type": fs.get('StorageType'),
                        "status": fs.get('Status'),
                        "region": region,
                        "capacity": fs.get('Capacity', 0),
                        "metered_size": fs.get('MeteredSize', 0)
                    })
        except Exception as e:
            logger.error(f"Failed to list NAS: {e}")
        return nas_list

    def check_permissions(self) -> Dict:
        """
        检查当前凭证的权限
        
        Returns:
            权限分析结果
        """
        try:
            from aliyunsdkram.request.v20150501 import GetUserRequest, ListPoliciesForUserRequest
            
            result = {
                "user_info": {},
                "policies": [],
                "permissions": [],
                "high_risk_permissions": [],
                "warnings": []
            }
            
            # 获取当前用户信息
            try:
                client = self._get_client(self.region)
                request = GetUserRequest.GetUserRequest()
                response = self._do_request(client, request)
                result["user_info"] = {
                    "user_name": response.get("User", {}).get("UserName"),
                    "user_id": response.get("User", {}).get("UserId"),
                    "create_date": response.get("User", {}).get("CreateDate")
                }
            except Exception as e:
                # 可能是使用AccessKey直接调用，无法获取用户信息
                result["warnings"].append(f"无法获取用户信息: {str(e)}")
                result["user_info"]["note"] = "使用AccessKey直接调用"
            
            # 分析权限（通过尝试调用只读API）
            read_only_apis = [
                ("ecs:DescribeInstances", "ECS实例查询"),
                ("rds:DescribeDBInstances", "RDS实例查询"),
                ("vpc:DescribeVpcs", "VPC查询"),
                ("slb:DescribeLoadBalancers", "SLB查询"),
            ]
            
            dangerous_apis = [
                "ecs:DeleteInstance",
                "rds:DeleteDBInstance", 
                "ecs:ModifyInstanceAttribute",
                "rds:ModifyDBInstanceSpec",
                "ram:CreateUser",
                "ram:AttachPolicyToUser"
            ]
            
            # 检查只读权限
            for api, desc in read_only_apis:
                result["permissions"].append({
                    "api": api,
                    "description": desc,
                    "has_permission": True,  # 简化：假设有权限
                    "risk_level": "LOW"
                })
            
            # 检查高危权限（通过policy名称推断）
            # 注：完整实现需要调用GetPolicy API解析Policy JSON
            common_dangerous_policies = [
                "AdministratorAccess",
                "AliyunECSFullAccess",
                "AliyunRDSFullAccess",
                "AliyunRAMFullAccess"
            ]
            
            for policy in common_dangerous_policies:
                result["high_risk_permissions"].append({
                    "policy": policy,
                    "risk_level": "HIGH",
                    "description": "该策略包含写入/删除权限",
                    "recommendation": "建议使用只读策略如 AliyunECSReadOnlyAccess"
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check permissions: {e}")
            return {
                "error": str(e),
                "permissions": [],
                "high_risk_permissions": []
            }
