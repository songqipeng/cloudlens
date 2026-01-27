# -*- coding: utf-8 -*-
"""
Mock Provider - 模拟中型互联网公司的云资源数据

规模设定：
- 月均云支出：约500万人民币
- 总资源数：1000+ 个
- ECS 实例：约 800 台
- RDS 实例：约 120 个
- Redis 实例：约 80 个
- 其他资源：SLB, NAT, OSS, EIP, Disk等
"""

import json
import logging
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cloudlens.core.provider import BaseProvider
from cloudlens.models.resource import ResourceStatus, ResourceType, UnifiedResource

logger = logging.getLogger("MockProvider")

# 使用固定种子确保数据一致性
random.seed(42)


class MockProvider(BaseProvider):
    """Mock Provider - 模拟云资源数据"""

    # 区域列表
    MOCK_REGIONS = [
        "cn-hangzhou", "cn-shanghai", "cn-beijing", "cn-shenzhen",
        "cn-hongkong", "ap-southeast-1", "us-west-1"
    ]

    # 项目名称
    MOCK_PROJECTS = [
        "frontend", "backend", "data-platform", "ai-service",
        "monitoring", "devops", "mobile-api", "admin-panel"
    ]

    # 环境
    MOCK_ENVS = ["prod", "staging", "dev", "test"]

    # 负责人
    MOCK_OWNERS = ["team-a", "team-b", "team-c", "infra", "ops"]

    # ECS 规格列表（更多样化）
    ECS_SPECS = [
        ("ecs.t6-c1m1.large", 2, 4), ("ecs.t6-c1m2.large", 2, 8),
        ("ecs.c6.large", 2, 4), ("ecs.c6.xlarge", 4, 8),
        ("ecs.c6.2xlarge", 8, 16), ("ecs.c6.4xlarge", 16, 32),
        ("ecs.g6.large", 2, 8), ("ecs.g6.xlarge", 4, 16),
        ("ecs.g6.2xlarge", 8, 32), ("ecs.g6.4xlarge", 16, 64),
        ("ecs.r6.large", 2, 16), ("ecs.r6.xlarge", 4, 32),
        ("ecs.r6.2xlarge", 8, 64), ("ecs.r6.4xlarge", 16, 128),
        ("ecs.c7.large", 2, 4), ("ecs.c7.xlarge", 4, 8),
        ("ecs.c7.2xlarge", 8, 16), ("ecs.c7.4xlarge", 16, 32),
    ]

    # RDS 规格
    RDS_SPECS = [
        "mysql.n2.medium.1", "mysql.n2.large.1", "mysql.n2.xlarge.1",
        "mysql.n2.2xlarge.1", "mysql.n4.medium.1", "mysql.n4.large.1",
        "mysql.n4.xlarge.1", "mysql.n4.2xlarge.1",
    ]

    # Redis 规格
    REDIS_SPECS = [
        "redis.master.small.default", "redis.master.mid.default",
        "redis.master.large.default", "redis.master.xlarge.default",
    ]

    def __init__(self, account_name: str, access_key: str, secret_key: str, region: str):
        super().__init__(account_name, access_key, secret_key, region)
        # 根据账号名称生成固定种子，确保同一账号数据一致
        seed = int(hashlib.md5(account_name.encode()).hexdigest()[:8], 16)
        random.seed(seed)

    @property
    def provider_name(self) -> str:
        return "mock"

    def _get_client(self):
        """Mock 不需要真实客户端"""
        return None

    def _generate_id(self, prefix: str) -> str:
        """生成模拟资源ID"""
        return f"{prefix}-mock-{random.randint(100000, 999999)}"

    def _generate_tags(self) -> Dict[str, str]:
        """生成模拟标签"""
        return {
            "project": random.choice(self.MOCK_PROJECTS),
            "env": random.choice(self.MOCK_ENVS),
            "owner": random.choice(self.MOCK_OWNERS),
        }

    def _generate_ip(self, public: bool = False) -> str:
        """生成模拟 IP 地址"""
        if public:
            return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        else:
            return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

    def check_instances_count(self) -> int:
        """返回该区域的ECS实例数量"""
        # 根据区域分配不同数量的实例
        region_weights = {
            "cn-hangzhou": 200,  # 杭州最多
            "cn-shanghai": 180,
            "cn-beijing": 150,
            "cn-shenzhen": 120,
            "cn-hongkong": 80,
            "ap-southeast-1": 50,
            "us-west-1": 20,
        }
        return region_weights.get(self.region, 50)

    def list_instances(self) -> List[UnifiedResource]:
        """返回模拟的 ECS 实例列表"""
        resources = []
        count = self.check_instances_count()

        for i in range(count):
            spec, cpu, memory = random.choice(self.ECS_SPECS)
            status = random.choices(
                [ResourceStatus.RUNNING, ResourceStatus.STOPPED],
                weights=[0.85, 0.15]
            )[0]
            charge_type = random.choices(
                ["PrePaid", "PostPaid"],
                weights=[0.7, 0.3]
            )[0]

            created_time = datetime.now() - timedelta(days=random.randint(30, 1095))
            expired_time = None
            if charge_type == "PrePaid":
                expired_time = created_time + timedelta(days=random.choice([365, 730, 1095]))

            instance_id = self._generate_id("i")
            project = random.choice(self.MOCK_PROJECTS)
            env = random.choice(self.MOCK_ENVS)
            name = f"{project}-{env}-{i+1:02d}"

            # 计算月度成本（根据规格）
            base_cost = {
                "ecs.t6-c1m1.large": 50, "ecs.t6-c1m2.large": 80,
                "ecs.c6.large": 320, "ecs.c6.xlarge": 640,
                "ecs.c6.2xlarge": 1280, "ecs.c6.4xlarge": 2560,
                "ecs.g6.large": 400, "ecs.g6.xlarge": 800,
                "ecs.g6.2xlarge": 1600, "ecs.g6.4xlarge": 3200,
                "ecs.r6.large": 500, "ecs.r6.xlarge": 1000,
                "ecs.r6.2xlarge": 2000, "ecs.r6.4xlarge": 4000,
                "ecs.c7.large": 350, "ecs.c7.xlarge": 700,
                "ecs.c7.2xlarge": 1400, "ecs.c7.4xlarge": 2800,
            }.get(spec, 320)

            # 应用折扣（3折左右，有波动）
            discount = random.uniform(0.25, 0.35)
            monthly_cost = base_cost * discount

            resources.append(UnifiedResource(
                id=instance_id,
                name=name,
                type=ResourceType.ECS,
                region=self.region,
                status=status,
                spec=spec,
                cost=monthly_cost,
                tags=self._generate_tags(),
                created_time=created_time.isoformat(),
                expired_time=expired_time.isoformat() if expired_time else None,
                vpc_id=self._generate_id("vpc"),
                public_ips=[self._generate_ip(True)] if random.random() > 0.3 else [],
                private_ips=[self._generate_ip(False)],
            ))

        return resources

    def list_rds(self) -> List[UnifiedResource]:
        """返回模拟的 RDS 实例列表"""
        resources = []
        # 根据区域分配RDS数量
        region_counts = {
            "cn-hangzhou": 25, "cn-shanghai": 20, "cn-beijing": 18,
            "cn-shenzhen": 15, "cn-hongkong": 10, "ap-southeast-1": 8,
            "us-west-1": 4,
        }
        count = region_counts.get(self.region, 5)

        for i in range(count):
            spec = random.choice(self.RDS_SPECS)
            status = ResourceStatus.RUNNING
            charge_type = random.choices(
                ["PrePaid", "PostPaid"],
                weights=[0.8, 0.2]
            )[0]

            created_time = datetime.now() - timedelta(days=random.randint(60, 800))
            expired_time = None
            if charge_type == "PrePaid":
                expired_time = created_time + timedelta(days=random.choice([365, 730]))

            instance_id = self._generate_id("rm")
            project = random.choice(["data-platform", "backend", "ai-service"])
            env = random.choice(self.MOCK_ENVS)
            name = f"rds-{project}-{env}-{i+1:02d}"

            # RDS 成本（应用折扣）
            base_cost = random.uniform(800, 5000)
            discount = random.uniform(0.25, 0.35)
            monthly_cost = base_cost * discount

            resources.append(UnifiedResource(
                id=instance_id,
                name=name,
                type=ResourceType.RDS,
                region=self.region,
                status=status,
                spec=spec,
                cost=monthly_cost,
                tags=self._generate_tags(),
                created_time=created_time.isoformat(),
                expired_time=expired_time.isoformat() if expired_time else None,
            ))

        return resources

    def list_redis(self) -> List[UnifiedResource]:
        """返回模拟的 Redis 实例列表"""
        resources = []
        region_counts = {
            "cn-hangzhou": 15, "cn-shanghai": 12, "cn-beijing": 10,
            "cn-shenzhen": 8, "cn-hongkong": 6, "ap-southeast-1": 4,
            "us-west-1": 2,
        }
        count = region_counts.get(self.region, 3)

        for i in range(count):
            spec = random.choice(self.REDIS_SPECS)
            status = ResourceStatus.RUNNING
            charge_type = random.choices(
                ["PrePaid", "PostPaid"],
                weights=[0.6, 0.4]
            )[0]

            created_time = datetime.now() - timedelta(days=random.randint(30, 500))
            expired_time = None
            if charge_type == "PrePaid":
                expired_time = created_time + timedelta(days=random.choice([365, 730]))

            instance_id = self._generate_id("r-kv")
            name = f"redis-{random.choice(self.MOCK_PROJECTS)}-{random.choice(self.MOCK_ENVS)}-{i+1:02d}"

            # Redis 成本（应用折扣）
            base_cost = random.uniform(200, 2000)
            discount = random.uniform(0.25, 0.35)
            monthly_cost = base_cost * discount

            resources.append(UnifiedResource(
                id=instance_id,
                name=name,
                type=ResourceType.REDIS,
                region=self.region,
                status=status,
                spec=spec,
                cost=monthly_cost,
                tags=self._generate_tags(),
                created_time=created_time.isoformat(),
                expired_time=expired_time.isoformat() if expired_time else None,
            ))

        return resources

    def list_vpcs(self) -> List[Dict]:
        """返回模拟的 VPC 列表"""
        vpcs = []
        count = random.randint(2, 5) if self.region in self.MOCK_REGIONS[:4] else 1

        cidrs = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]

        for i in range(count):
            vpc_id = self._generate_id("vpc")
            vpcs.append({
                "id": vpc_id,
                "name": f"vpc-{random.choice(self.MOCK_ENVS)}-{i+1:02d}",
                "cidr": cidrs[i % len(cidrs)],
                "region": self.region,
                "status": "Available",
            })

        return vpcs

    def get_metric(
        self, resource_id: str, metric_name: str, start_time: int, end_time: int
    ) -> List[Dict]:
        """返回模拟的监控指标数据"""
        datapoints = []

        # 生成模拟的时间序列数据
        current = datetime.fromtimestamp(start_time / 1000)
        end = datetime.fromtimestamp(end_time / 1000)
        interval = 300000  # 5分钟间隔（毫秒）

        # 根据指标类型生成合理范围的数据
        if "cpu" in metric_name.lower():
            base_value = random.uniform(20, 60)
            variance = 15
        elif "memory" in metric_name.lower():
            base_value = random.uniform(40, 70)
            variance = 10
        elif "disk" in metric_name.lower():
            base_value = random.uniform(30, 60)
            variance = 5
        else:
            base_value = random.uniform(0, 100)
            variance = 20

        while current <= end:
            value = max(0, min(100, base_value + random.uniform(-variance, variance)))
            datapoints.append({
                "timestamp": int(current.timestamp() * 1000),
                "value": round(value, 2),
            })
            current += timedelta(seconds=300)

        return datapoints

    def check_permissions(self) -> List[str]:
        """返回模拟的权限列表"""
        return [
            "AliyunECSReadOnlyAccess",
            "AliyunRDSReadOnlyAccess",
            "AliyunRedisReadOnlyAccess",
            "AliyunVPCReadOnlyAccess",
        ]
