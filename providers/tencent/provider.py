from abc import ABC
from typing import List, Dict
import logging
from datetime import datetime

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.cvm.v20170312 import cvm_client, models as cvm_models
from tencentcloud.vpc.v20170312 import vpc_client, models as vpc_models
from tencentcloud.cdb.v20170320 import cdb_client, models as cdb_models

from core.provider import BaseProvider
from core.security import PermissionGuard
from models.resource import UnifiedResource, ResourceType, ResourceStatus

logger = logging.getLogger("TencentProvider")

class TencentProvider(BaseProvider):
    
    @property
    def provider_name(self) -> str:
        return "tencent"

    def _get_credential(self):
        return credential.Credential(self.access_key, self.secret_key)

    def _get_cvm_client(self):
        cred = self._get_credential()
        httpProfile = HttpProfile()
        httpProfile.endpoint = "cvm.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        return cvm_client.CvmClient(cred, self.region, clientProfile)

    def _get_vpc_client(self):
        cred = self._get_credential()
        httpProfile = HttpProfile()
        httpProfile.endpoint = "vpc.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        return vpc_client.VpcClient(cred, self.region, clientProfile)

    def _get_cdb_client(self):
        cred = self._get_credential()
        httpProfile = HttpProfile()
        httpProfile.endpoint = "cdb.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        return cdb_client.CdbClient(cred, self.region, clientProfile)

    def list_instances(self) -> List[UnifiedResource]:
        """列出CVM实例"""
        resources = []
        try:
            client = self._get_cvm_client()
            req = cvm_models.DescribeInstancesRequest()
            resp = client.DescribeInstances(req)
            
            for inst in resp.InstanceSet:
                # 状态映射
                status_map = {
                    "RUNNING": ResourceStatus.RUNNING,
                    "STOPPED": ResourceStatus.STOPPED,
                    "STARTING": ResourceStatus.STARTING,
                    "STOPPING": ResourceStatus.STOPPING
                }
                
                # 获取IP
                public_ips = list(inst.PublicIpAddresses) if inst.PublicIpAddresses else []
                private_ips = list(inst.PrivateIpAddresses) if inst.PrivateIpAddresses else []
                
                # 时间处理
                created_time = datetime.strptime(inst.CreatedTime, "%Y-%m-%dT%H:%M:%SZ") if inst.CreatedTime else None
                expired_time = datetime.strptime(inst.ExpiredTime, "%Y-%m-%dT%H:%M:%SZ") if inst.ExpiredTime else None
                
                r = UnifiedResource(
                    id=inst.InstanceId,
                    name=inst.InstanceName,
                    provider=self.provider_name,
                    region=self.region,
                    zone=inst.Placement.Zone if inst.Placement else None,
                    resource_type=ResourceType.ECS,
                    status=status_map.get(inst.InstanceState, ResourceStatus.UNKNOWN),
                    private_ips=private_ips,
                    public_ips=public_ips,
                    vpc_id=inst.VirtualPrivateCloud.VpcId if inst.VirtualPrivateCloud else None,
                    spec=inst.InstanceType,
                    cpu=inst.CPU,
                    memory=inst.Memory * 1024,  # GB to MB
                    charge_type="PrePaid" if inst.InstanceChargeType == "PREPAID" else "PostPaid",
                    created_time=created_time,
                    expired_time=expired_time,
                    raw_data=inst.__dict__
                )
                resources.append(r)
                
        except Exception as e:
            logger.error(f"Failed to list CVM instances: {e}")
            
        return resources

    def list_rds(self) -> List[UnifiedResource]:
        """列出CDB (MySQL) 实例"""
        resources = []
        try:
            client = self._get_cdb_client()
            req = cdb_models.DescribeDBInstancesRequest()
            resp = client.DescribeDBInstances(req)
            
            for inst in resp.Items:
                status_map = {
                    "1": ResourceStatus.RUNNING,  # 运行中
                    "0": ResourceStatus.STOPPED   # 已隔离
                }
                
                r = UnifiedResource(
                    id=inst.InstanceId,
                    name=inst.InstanceName,
                    provider=self.provider_name,
                    region=self.region,
                    zone=inst.Zone,
                    resource_type=ResourceType.RDS,
                    status=status_map.get(str(inst.Status), ResourceStatus.UNKNOWN),
                    vpc_id=inst.UniqVpcId,
                    spec=f"{inst.Memory}MB/{inst.Volume}GB",
                    charge_type="PrePaid" if inst.PayType == 0 else "PostPaid",
                    raw_data=inst.__dict__
                )
                resources.append(r)
                
        except Exception as e:
            logger.error(f"Failed to list CDB instances: {e}")
            
        return resources

    def list_vpcs(self) -> List[Dict]:
        """列出VPC"""
        vpcs = []
        try:
            client = self._get_vpc_client()
            req = vpc_models.DescribeVpcsRequest()
            resp = client.DescribeVpcs(req)
            
            for vpc in resp.VpcSet:
                vpcs.append({
                    "id": vpc.VpcId,
                    "name": vpc.VpcName,
                    "cidr": vpc.CidrBlock,
                    "region": self.region,
                    "status": "Available" if vpc.IsDefault else "Available"
                })
        except Exception as e:
            logger.error(f"Failed to list VPCs: {e}")
        return vpcs

    def list_redis(self) -> List[UnifiedResource]:
        """列出Redis实例"""
        from tencentcloud.redis.v20180412 import redis_client, models as redis_models
        
        resources = []
        try:
            cred = self._get_credential()
            client = redis_client.RedisClient(cred, self.region)
            req = redis_models.DescribeInstancesRequest()
            resp = client.DescribeInstances(req)
            
            for inst in resp.InstanceSet:
                status_map = {
                    "1": ResourceStatus.RUNNING,  # 运行中
                    "2": ResourceStatus.STOPPED   # 已隔离
                }
                
                r = UnifiedResource(
                    id=inst.InstanceId,
                    name=inst.InstanceName,
                    provider=self.provider_name,
                    region=self.region,
                    zone=inst.Zone,
                    resource_type=ResourceType.REDIS,
                    status=status_map.get(str(inst.Status), ResourceStatus.UNKNOWN),
                    spec=f"{inst.Type}",
                    charge_type="PrePaid" if inst.BillingMode == 1 else "PostPaid",
                    raw_data=inst.__dict__
                )
                resources.append(r)
                
        except Exception as e:
            logger.error(f"Failed to list Redis instances: {e}")
            
        return resources

    def list_oss(self) -> List[Dict]:
        """列出COS (对象存储) Bucket"""
        buckets = []
        try:
            from qcloud_cos import CosConfig, CosS3Client
            
            config = CosConfig(
                Region=self.region,
                SecretId=self.access_key,
                SecretKey=self.secret_key
            )
            client = CosS3Client(config)
            
            response = client.list_buckets()
            
            for bucket in response.get('Buckets', {}).get('Bucket', []):
                buckets.append({
                    "id": bucket['Name'],
                    "name": bucket['Name'],
                    "region": bucket.get('Location', '').replace('cos.', ''),
                    "created_time": bucket.get('CreationDate'),
                    "storage_class": "-"
                })
        except ImportError:
            logger.warning("qcloud_cos not installed. Run: pip install cos-python-sdk-v5")
        except Exception as e:
            logger.error(f"Failed to list COS buckets: {e}")
        return buckets

    def get_metric(self, resource_id: str, metric_name: str, start_time: int, end_time: int) -> List[Dict]:
        # TODO: Implement Tencent Cloud Monitor integration
        return []

    def check_permissions(self) -> List[str]:
        # TODO: Implement CAM policy check
        return ["cvm:DescribeInstances", "cdb:DescribeDBInstances"]
