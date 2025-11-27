#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取所有ECS实例的云盘信息（类型和大小）
"""

import json
import os
import sys
from datetime import datetime

import pandas as pd
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

# 添加模块路径
sys.path.append(os.path.join(os.path.dirname(__file__)))


def load_config():
    """加载配置文件"""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print("❌ 配置文件 config.json 不存在")
        sys.exit(1)


def get_tenant_config(config, tenant_name=None):
    """获取租户配置"""
    if tenant_name is None:
        tenant_name = config.get("default_tenant")

    tenants = config.get("tenants", {})
    if tenant_name not in tenants:
        print(f"❌ 未找到租户: {tenant_name}")
        print(f"可用租户: {', '.join(tenants.keys())}")
        sys.exit(1)

    return tenants[tenant_name]


def get_all_regions(client):
    """获取所有可用区域"""
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


def get_all_instances(client, region_id):
    """获取指定区域的所有ECS实例"""
    request = CommonRequest()
    request.set_domain(f"ecs.{region_id}.aliyuncs.com")
    request.set_method("POST")
    request.set_version("2014-05-26")
    request.set_action_name("DescribeInstances")
    request.add_query_param("PageSize", 100)

    all_instances = []
    page_number = 1

    while True:
        request.add_query_param("PageNumber", page_number)
        response = client.do_action_with_exception(request)
        data = json.loads(response)

        if "Instances" not in data or "Instance" not in data["Instances"]:
            break

        instances = data["Instances"]["Instance"]
        if not isinstance(instances, list):
            instances = [instances]

        for instance in instances:
            all_instances.append(
                {
                    "InstanceId": instance["InstanceId"],
                    "InstanceName": instance.get("InstanceName", "未命名"),
                    "Status": instance.get("Status", "未知"),
                    "InstanceType": instance.get("InstanceType", "未知"),
                    "RegionId": region_id,
                    "ZoneId": instance.get("ZoneId", "未知"),
                }
            )

        if len(instances) < 100:
            break
        page_number += 1

    return all_instances


def get_instance_disks(client, region_id, instance_id):
    """获取实例的所有磁盘信息"""
    request = CommonRequest()
    request.set_domain(f"ecs.{region_id}.aliyuncs.com")
    request.set_method("POST")
    request.set_version("2014-05-26")
    request.set_action_name("DescribeDisks")
    request.add_query_param("InstanceId", instance_id)
    request.add_query_param("PageSize", 100)

    disks = []
    page_number = 1

    while True:
        request.add_query_param("PageNumber", page_number)
        try:
            response = client.do_action_with_exception(request)
            data = json.loads(response)

            if "Disks" not in data or "Disk" not in data["Disks"]:
                break

            disk_list = data["Disks"]["Disk"]
            if not isinstance(disk_list, list):
                disk_list = [disk_list]

            for disk in disk_list:
                disks.append(
                    {
                        "DiskId": disk.get("DiskId", ""),
                        "DiskName": disk.get("DiskName", ""),
                        "Category": disk.get(
                            "Category", "未知"
                        ),  # 云盘类型：cloud、cloud_essd、cloud_ssd等
                        "Size": disk.get("Size", 0),  # 容量（GB）
                        "Device": disk.get("Device", ""),  # 挂载点，如/dev/xvda
                        "DiskChargeType": disk.get(
                            "DiskChargeType", ""
                        ),  # 付费类型：PrePaid/PostPaid
                        "Status": disk.get("Status", ""),
                        "Type": disk.get("Type", ""),  # 磁盘类型：system/data
                        "Portable": disk.get("Portable", False),  # 是否可卸载
                        "PerformanceLevel": disk.get("PerformanceLevel", ""),  # ESSD性能级别
                    }
                )

            if len(disk_list) < 100:
                break
            page_number += 1
        except Exception as e:
            print(f"  ⚠️ 获取实例 {instance_id} 磁盘信息失败: {e}")
            break

    return disks


def main(tenant_name=None):
    """主函数"""
    print("🚀 开始获取ECS实例云盘信息...")
    print("=" * 80)

    # 加载配置
    config = load_config()

    # 获取租户配置
    if tenant_name is None:
        tenant_name = config.get("default_tenant")

    tenant_config = get_tenant_config(config, tenant_name)
    access_key_id = tenant_config["access_key_id"]
    access_key_secret = tenant_config["access_key_secret"]

    print(f"🏢 租户: {tenant_name} ({tenant_config.get('display_name', tenant_name)})")
    print("=" * 80)

    # 创建客户端
    client = AcsClient(access_key_id, access_key_secret, "cn-hangzhou")

    # 获取所有区域
    print("📡 获取所有区域...")
    regions = get_all_regions(client)
    print(f"✅ 找到 {len(regions)} 个区域")

    # 获取所有实例
    print("\n📦 获取所有ECS实例...")
    all_instances = []
    for region in regions:
        try:
            region_client = AcsClient(access_key_id, access_key_secret, region)
            instances = get_all_instances(region_client, region)
            all_instances.extend(instances)
            if instances:
                print(f"  ✅ {region}: {len(instances)} 个实例")
        except Exception as e:
            print(f"  ⚠️ {region}: 获取失败 - {e}")
            continue

    print(f"\n✅ 总共找到 {len(all_instances)} 个ECS实例")

    # 获取每个实例的磁盘信息
    print("\n💾 获取实例磁盘信息...")
    all_disk_data = []

    for i, instance in enumerate(all_instances, 1):
        instance_id = instance["InstanceId"]
        instance_name = instance["InstanceName"]
        region_id = instance["RegionId"]

        print(
            f"  [{i}/{len(all_instances)}] {instance_name} ({instance_id})...", end="", flush=True
        )

        try:
            region_client = AcsClient(access_key_id, access_key_secret, region_id)
            disks = get_instance_disks(region_client, region_id, instance_id)

            if disks:
                for disk in disks:
                    all_disk_data.append(
                        {
                            "实例名称": instance_name,
                            "实例ID": instance_id,
                            "区域": region_id,
                            "可用区": instance["ZoneId"],
                            "实例状态": instance["Status"],
                            "实例规格": instance["InstanceType"],
                            "磁盘ID": disk["DiskId"],
                            "磁盘名称": disk["DiskName"],
                            "磁盘类型": disk["Category"],
                            "磁盘大小(GB)": disk["Size"],
                            "挂载点": disk["Device"],
                            "磁盘角色": disk["Type"],  # system/data
                            "付费类型": disk["DiskChargeType"],
                            "磁盘状态": disk["Status"],
                            "是否可卸载": "是" if disk["Portable"] else "否",
                            "性能级别": (
                                disk["PerformanceLevel"] if disk["PerformanceLevel"] else "N/A"
                            ),
                        }
                    )
                print(f" ✅ ({len(disks)} 个磁盘)")
            else:
                print(" ⚠️ (无磁盘信息)")
        except Exception as e:
            print(f" ❌ 失败: {e}")

    if not all_disk_data:
        print("\n⚠️ 未找到任何磁盘信息")
        return

    # 生成报告
    print("\n📊 生成报告...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 创建输出目录
    output_dir = os.path.join(".", tenant_name, "reports")
    os.makedirs(output_dir, exist_ok=True)

    # Excel报告
    df = pd.DataFrame(all_disk_data)
    excel_file = os.path.join(output_dir, f"{tenant_name}_ecs_disks_{timestamp}.xlsx")
    df.to_excel(excel_file, index=False)
    print(f"✅ Excel报告已生成: {excel_file}")

    # 统计信息
    print("\n📊 统计信息:")
    print(f"  总实例数: {len(set(d['实例ID'] for d in all_disk_data))} 个")
    print(f"  总磁盘数: {len(all_disk_data)} 个")
    print(f"  总磁盘容量: {sum(d['磁盘大小(GB)'] for d in all_disk_data):,.0f} GB")

    # 按磁盘类型统计
    print("\n📋 按磁盘类型统计:")
    category_stats = {}
    for disk in all_disk_data:
        category = disk["磁盘类型"]
        if category not in category_stats:
            category_stats[category] = {"count": 0, "size": 0}
        category_stats[category]["count"] += 1
        category_stats[category]["size"] += disk["磁盘大小(GB)"]

    for category, stats in sorted(category_stats.items()):
        print(f"  {category}: {stats['count']} 个磁盘, {stats['size']:,.0f} GB")

    # 按磁盘大小范围统计
    print("\n📋 按磁盘大小范围统计:")
    size_ranges = {
        "0-20GB": (0, 20),
        "21-40GB": (21, 40),
        "41-100GB": (41, 100),
        "101-500GB": (101, 500),
        "501-1000GB": (501, 1000),
        "1000GB+": (1001, float("inf")),
    }

    for range_name, (min_size, max_size) in size_ranges.items():
        count = sum(1 for d in all_disk_data if min_size <= d["磁盘大小(GB)"] <= max_size)
        if count > 0:
            total_size = sum(
                d["磁盘大小(GB)"]
                for d in all_disk_data
                if min_size <= d["磁盘大小(GB)"] <= max_size
            )
            print(f"  {range_name}: {count} 个磁盘, {total_size:,.0f} GB")

    print("\n" + "=" * 80)
    print("🎉 完成！")
    print("=" * 80)


if __name__ == "__main__":
    tenant_name = sys.argv[1] if len(sys.argv) > 1 else None
    main(tenant_name)
