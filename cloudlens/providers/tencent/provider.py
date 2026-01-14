import logging
from abc import ABC
from datetime import datetime
from typing import Dict, List

from tencentcloud.cdb.v20170320 import cdb_client
from tencentcloud.cdb.v20170320 from cloudlens import models as cdb_models
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.cvm.v20170312 import cvm_client
from tencentcloud.cvm.v20170312 from cloudlens import models as cvm_models
from tencentcloud.vpc.v20170312 from cloudlens import models as vpc_models
from tencentcloud.vpc.v20170312 import vpc_client

from cloudlens.core.provider import BaseProvider
from cloudlens.core.security import PermissionGuard
from cloudlens.models.resource import ResourceStatus, ResourceType, UnifiedResource

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
                    "STOPPING": ResourceStatus.STOPPING,
                }

                # 获取IP
                public_ips = list(inst.PublicIpAddresses) if inst.PublicIpAddresses else []
                private_ips = list(inst.PrivateIpAddresses) if inst.PrivateIpAddresses else []

                # 时间处理
                created_time = (
                    datetime.strptime(inst.CreatedTime, "%Y-%m-%dT%H:%M:%SZ")
                    if inst.CreatedTime
                    else None
                )
                expired_time = (
                    datetime.strptime(inst.ExpiredTime, "%Y-%m-%dT%H:%M:%SZ")
                    if inst.ExpiredTime
                    else None
                )

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
                    raw_data=inst.__dict__,
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
                    "0": ResourceStatus.STOPPED,  # 已隔离
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
                    raw_data=inst.__dict__,
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
                vpcs.append(
                    {
                        "id": vpc.VpcId,
                        "name": vpc.VpcName,
                        "cidr": vpc.CidrBlock,
                        "region": self.region,
                        "status": "Available" if vpc.IsDefault else "Available",
                    }
                )
        except Exception as e:
            logger.error(f"Failed to list VPCs: {e}")
        return vpcs

    def list_redis(self) -> List[UnifiedResource]:
        """列出Redis实例"""
        from tencentcloud.redis.v20180412 from cloudlens import models as redis_models
        from tencentcloud.redis.v20180412 import redis_client

        resources = []
        try:
            cred = self._get_credential()
            client = redis_client.RedisClient(cred, self.region)
            req = redis_models.DescribeInstancesRequest()
            resp = client.DescribeInstances(req)

            for inst in resp.InstanceSet:
                status_map = {
                    "1": ResourceStatus.RUNNING,  # 运行中
                    "2": ResourceStatus.STOPPED,  # 已隔离
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
                    raw_data=inst.__dict__,
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
                Region=self.region, SecretId=self.access_key, SecretKey=self.secret_key
            )
            client = CosS3Client(config)

            response = client.list_buckets()

            for bucket in response.get("Buckets", {}).get("Bucket", []):
                buckets.append(
                    {
                        "id": bucket["Name"],
                        "name": bucket["Name"],
                        "region": bucket.get("Location", "").replace("cos.", ""),
                        "created_time": bucket.get("CreationDate"),
                        "storage_class": "-",
                    }
                )
        except ImportError:
            logger.warning("qcloud_cos not installed. Run: pip install cos-python-sdk-v5")
        except Exception as e:
            logger.error(f"Failed to list COS buckets: {e}")
        return buckets

    def get_metric(
        self, resource_id: str, metric_name: str, start_time: int, end_time: int
    ) -> List[Dict]:
        """获取腾讯云监控指标"""
        try:
            from datetime import datetime

            from tencentcloud.monitor.v20180724 from cloudlens import models as monitor_models
            from tencentcloud.monitor.v20180724 import monitor_client

            cred = self._get_credential()
            client = monitor_client.MonitorClient(cred, self.region)

            request = monitor_models.GetMonitorDataRequest()
            request.Namespace = "QCE/CVM"  # 云服务器命名空间
            request.MetricName = metric_name

            # 设置实例维度
            dimension = monitor_models.Dimension()
            dimension.Name = "InstanceId"
            dimension.Value = resource_id
            request.Instances = [dimension]

            # 时间范围
            request.StartTime = datetime.fromtimestamp(start_time).strftime(
                "%Y-%m-%dT%H:%M:%S+08:00"
            )
            request.EndTime = datetime.fromtimestamp(end_time).strftime("%Y-%m-%dT%H:%M:%S+08:00")
            request.Period = 86400  # 1天

            response = client.GetMonitorData(request)

            # 解析返回数据
            datapoints = []
            if response.DataPoints:
                for point in response.DataPoints:
                    datapoints.append({"timestamp": point.Timestamp, "value": point.Value})

            return datapoints
        except Exception as e:
            logger.error(f"Failed to get metrics for {resource_id}: {e}")
            return []

    def check_permissions(self) -> Dict:
        """检查当前凭证的CAM权限"""
        result = {"user_info": {}, "permissions": [], "high_risk_permissions": [], "warnings": []}

        try:
            from tencentcloud.cam.v20190116 import cam_client
            from tencentcloud.cam.v20190116 from cloudlens import models as cam_models
            from tencentcloud.sts.v20180813 from cloudlens import models as sts_models
            from tencentcloud.sts.v20180813 import sts_client

            # 1. 获取当前身份信息
            try:
                cred = self._get_credential()
                sts = sts_client.StsClien(cred, "ap-guangzhou")
                req = sts_models.GetCallerIdentityRequest()
                resp = sts.GetCallerIdentity(req)

                result["user_info"] = {
                    "account_id": resp.AccountId,
                    "user_id": resp.UserId,
                    "arn": resp.Arn,
                    "type": resp.Type,
                }
            except Exception as e:
                result["warnings"].append(f"无法获取身份信息: {str(e)}")

            # 2. 基础只读权限
            read_only_permissions = [
                {"api": "cvm:DescribeInstances", "description": "查询CVM实例", "risk_level": "LOW"},
                {
                    "api": "cdb:DescribeDBInstances",
                    "description": "查询CDB实例",
                    "risk_level": "LOW",
                },
                {"api": "vpc:DescribeVpcs", "description": "查询VPC", "risk_level": "LOW"},
                {
                    "api": "redis:DescribeInstances",
                    "description": "查询Redis实例",
                    "risk_level": "LOW",
                },
            ]

            result["permissions"] = read_only_permissions

            # 3. 检查是否有高危权限（简化版，实际需要调用CAM API）
            result["warnings"].append("⚠️  腾讯云CAM策略检查功能有限，建议在控制台手动审查")

        except Exception as e:
            logger.error(f"Failed to check permissions: {e}")
            result["error"] = str(e)

        return result
