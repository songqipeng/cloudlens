#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源概览脚本
快速扫描指定租户的所有资源，显示资源类型和区域分布
"""

import json
import sys
from datetime import datetime

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from utils.concurrent_helper import process_concurrently
from utils.logger import get_logger


class ResourceOverview:
    """资源概览扫描器"""

    def __init__(self, access_key_id, access_key_secret, tenant_name):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.tenant_name = tenant_name
        self.logger = get_logger("resource_overview")
        self.resources = {}

    def get_all_regions(self):
        """获取所有可用区域"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, "cn-hangzhou")
            request = CommonRequest()
            request.set_domain("ecs.cn-hangzhou.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2014-05-26")
            request.set_action_name("DescribeRegions")

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            regions = []
            for region in data["Regions"]["Region"]:
                regions.append(region["RegionId"])

            return regions
        except Exception as e:
            self.logger.error(f"获取区域列表失败: {e}")
            return []

    def scan_ecs(self, region):
        """扫描ECS实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"ecs.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2014-05-26")
            request.set_action_name("DescribeInstances")
            request.add_query_param("PageSize", 1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            total = data.get("TotalCount", 0)
            return total
        except Exception as e:
            return 0

    def scan_rds(self, region):
        """扫描RDS实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"rds.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2014-08-15")
            request.set_action_name("DescribeDBInstances")
            request.add_query_param("PageSize", 1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            total = data.get("TotalRecordCount", 0)
            return total
        except Exception as e:
            return 0

    def scan_redis(self, region):
        """扫描Redis实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"r-kvstore.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2015-01-01")
            request.set_action_name("DescribeInstances")
            request.add_query_param("PageSize", 1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            total = data.get("TotalCount", 0)
            return total
        except Exception as e:
            return 0

    def scan_oss(self, region):
        """扫描OSS Bucket（OSS是全局的，不需要按区域）"""
        if region != "cn-hangzhou":  # OSS只需要查询一次
            return None

        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, "cn-hangzhou")
            request = CommonRequest()
            request.set_domain("oss.cn-hangzhou.aliyuncs.com")
            request.set_method("GET")
            request.set_uri_pattern("/")

            # 使用OSS API获取bucket列表
            from aliyunsdkoss.request.v20190517 import ListBucketsRequest

            # 简化处理，使用通用请求
            request = CommonRequest()
            request.set_domain("oss.cn-hangzhou.aliyuncs.com")
            request.set_method("GET")
            request.set_uri_pattern("/")

            # OSS需要特殊处理，这里返回-1表示需要单独处理
            return -1
        except Exception as e:
            return 0

    def scan_slb(self, region):
        """扫描SLB实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"slb.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2014-05-15")
            request.set_action_name("DescribeLoadBalancers")
            request.add_query_param("PageSize", 1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            total = data.get("TotalCount", 0)
            return total
        except Exception as e:
            return 0

    def scan_eip(self, region):
        """扫描EIP实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"ecs.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2014-05-26")
            request.set_action_name("DescribeEipAddresses")
            request.add_query_param("PageSize", 1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            total = data.get("TotalCount", 0)
            return total
        except Exception as e:
            return 0

    def scan_vpc(self, region):
        """扫描VPC"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"vpc.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2016-04-28")
            request.set_action_name("DescribeVpcs")
            request.add_query_param("PageSize", 1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            total = data.get("TotalCount", 0)
            return total
        except Exception as e:
            return 0

    def scan_nas(self, region):
        """扫描NAS文件系统"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"nas.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2017-06-26")
            request.set_action_name("DescribeFileSystems")
            request.add_query_param("PageSize", 1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            total = data.get("TotalCount", 0)
            return total
        except Exception as e:
            return 0

    def scan_polardb(self, region):
        """扫描PolarDB实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"polardb.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2017-08-01")
            request.set_action_name("DescribeDBClusters")
            request.add_query_param("PageSize", 1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            total = data.get("TotalRecordCount", 0)
            return total
        except Exception as e:
            return 0

    def scan_mongodb(self, region):
        """扫描MongoDB实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"dds.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2015-12-01")
            request.set_action_name("DescribeDBInstances")
            request.add_query_param("PageSize", 1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            total = data.get("TotalCount", 0)
            return total
        except Exception as e:
            return 0

    def scan_clickhouse(self, region):
        """扫描ClickHouse实例"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"clickhouse.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2019-11-11")
            request.set_action_name("DescribeDBClusters")
            request.add_query_param("PageSize", 1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            total = data.get("TotalCount", 0)
            return total
        except Exception as e:
            return 0

    def scan_ack(self, region):
        """扫描ACK集群"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"cs.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2015-12-15")
            request.set_action_name("DescribeClusters")

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            if "clusters" in data:
                clusters = data["clusters"]
                if isinstance(clusters, list):
                    return len(clusters)
                elif clusters:
                    return 1
            return 0
        except Exception as e:
            return 0

    def scan_eci(self, region):
        """扫描ECI容器组"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"eci.{region}.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2018-08-28")
            request.set_action_name("DescribeContainerGroups")
            request.add_query_param("PageSize", 1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            total = data.get("TotalCount", 0)
            return total
        except Exception as e:
            return 0

    def scan_cdn(self):
        """扫描CDN域名（全局）"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, "cn-hangzhou")
            request = CommonRequest()
            request.set_domain("cdn.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2018-05-10")
            request.set_action_name("DescribeUserDomains")
            request.add_query_param("PageSize", 1)

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            total = data.get("TotalCount", 0)
            return total
        except Exception as e:
            return 0

    def scan_region_resources(self, region):
        """扫描单个区域的所有资源"""
        result = {"region": region, "resources": {}}

        # 定义要扫描的资源类型
        scanners = {
            "ECS": self.scan_ecs,
            "RDS": self.scan_rds,
            "Redis": self.scan_redis,
            "SLB": self.scan_slb,
            "EIP": self.scan_eip,
            "VPC": self.scan_vpc,
            "NAS": self.scan_nas,
            "PolarDB": self.scan_polardb,
            "MongoDB": self.scan_mongodb,
            "ClickHouse": self.scan_clickhouse,
            "ACK": self.scan_ack,
            "ECI": self.scan_eci,
        }

        for resource_type, scanner_func in scanners.items():
            try:
                count = scanner_func(region)
                if count is not None and count > 0:
                    result["resources"][resource_type] = count
            except Exception as e:
                pass  # 忽略单个资源类型的错误

        return result

    def generate_overview(self):
        """生成资源概览"""
        print(f"\n🔍 开始扫描 {self.tenant_name} 租户的资源...")
        print("=" * 80)

        # 获取所有区域
        regions = self.get_all_regions()
        print(f"📡 找到 {len(regions)} 个区域\n")

        # 并发扫描所有区域
        print("正在扫描各区域资源...")
        results = process_concurrently(
            regions, self.scan_region_resources, max_workers=10, description="资源扫描"
        )

        # 整理结果
        resource_summary = {}  # {resource_type: {region: count}}
        region_summary = {}  # {region: {resource_type: count}}

        for result in results:
            if result:
                region = result["region"]
                region_resources = result.get("resources", {})

                if region_resources:
                    region_summary[region] = region_resources

                    for resource_type, count in region_resources.items():
                        if resource_type not in resource_summary:
                            resource_summary[resource_type] = {}
                        resource_summary[resource_type][region] = count

        # 扫描全局资源（CDN）
        cdn_count = self.scan_cdn()
        if cdn_count > 0:
            if "CDN" not in resource_summary:
                resource_summary["CDN"] = {}
            resource_summary["CDN"]["全局"] = cdn_count

        # 打印结果
        print("\n" + "=" * 80)
        print(f"📊 {self.tenant_name} 租户资源概览")
        print("=" * 80)

        if not resource_summary:
            print("\n❌ 未发现任何资源")
            return

        # 按资源类型汇总
        print("\n📦 按资源类型汇总:")
        print("-" * 80)
        total_resources = 0
        for resource_type in sorted(resource_summary.keys()):
            regions_with_resource = resource_summary[resource_type]
            total_count = sum(regions_with_resource.values())
            total_resources += total_count
            print(f"\n{resource_type}: 共 {total_count} 个")
            for region, count in sorted(regions_with_resource.items()):
                print(f"  └─ {region}: {count} 个")

        # 按区域汇总
        print("\n\n🌍 按区域汇总:")
        print("-" * 80)
        for region in sorted(region_summary.keys()):
            resources = region_summary[region]
            total = sum(resources.values())
            print(f"\n{region}: 共 {total} 个资源")
            for resource_type, count in sorted(resources.items()):
                print(f"  └─ {resource_type}: {count} 个")

        # 统计信息
        print("\n\n📈 统计信息:")
        print("-" * 80)
        print(f"总资源数量: {total_resources} 个")
        print(f"资源类型数: {len(resource_summary)} 种")
        print(f"有资源的区域数: {len(region_summary)} 个")
        print(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        return {
            "resource_summary": resource_summary,
            "region_summary": region_summary,
            "total_resources": total_resources,
        }


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python3 resource_overview.py <租户名称>")
        print("示例: python3 resource_overview.py cf")
        sys.exit(1)

    tenant_name = sys.argv[1]

    # 加载配置
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ 配置文件 config.json 不存在")
        sys.exit(1)

    # 获取租户配置
    tenants = config.get("tenants", {})
    if tenant_name not in tenants:
        print(f"❌ 未找到租户: {tenant_name}")
        print(f"可用租户: {', '.join(tenants.keys())}")
        sys.exit(1)

    tenant_config = tenants[tenant_name]
    access_key_id = tenant_config.get("access_key_id")
    access_key_secret = tenant_config.get("access_key_secret")

    if not access_key_id or not access_key_secret:
        print(f"❌ 租户 {tenant_name} 的AK/SK未配置")
        sys.exit(1)

    # 尝试从Keyring获取凭证
    try:
        from utils.credential_manager import get_credentials_from_config_or_keyring

        cloud_credentials = get_credentials_from_config_or_keyring("aliyun", tenant_name, config)
        if cloud_credentials:
            access_key_id = cloud_credentials.get("access_key_id", access_key_id)
            access_key_secret = cloud_credentials.get("access_key_secret", access_key_secret)
    except:
        pass

    # 创建概览扫描器
    overview = ResourceOverview(access_key_id, access_key_secret, tenant_name)
    overview.generate_overview()


if __name__ == "__main__":
    main()
