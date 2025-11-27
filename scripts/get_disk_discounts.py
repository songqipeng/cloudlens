#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取所有ECS云盘的折扣信息
"""

import json
import os
import sys
import time
from datetime import datetime

import pandas as pd
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from utils.concurrent_helper import process_concurrently

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


def get_disk_renewal_price(
    client,
    region_id,
    disk_id,
    disk_category,
    disk_size,
    instance_id=None,
    disk_role="",
    all_disks_for_instance=None,
):
    """获取云盘的续费价格

    方法：通过查询挂载该磁盘的实例的续费价格，从DetailInfo中提取磁盘价格
    如果同一实例有多个数据盘，按大小比例分摊价格
    """
    if not instance_id:
        # 如果未提供实例ID，先查询磁盘信息获取实例ID
        try:
            req_disk = CommonRequest()
            req_disk.set_domain(f"ecs.{region_id}.aliyuncs.com")
            req_disk.set_method("POST")
            req_disk.set_version("2014-05-26")
            req_disk.set_action_name("DescribeDisks")
            req_disk.add_query_param("DiskIds", f'["{disk_id}"]')
            resp_disk = client.do_action_with_exception(req_disk)
            data_disk = json.loads(resp_disk)
            if "Disks" in data_disk and "Disk" in data_disk["Disks"]:
                disks = data_disk["Disks"]["Disk"]
                if not isinstance(disks, list):
                    disks = [disks]
                if disks:
                    instance_id = disks[0].get("InstanceId", "")
                    if not disk_role:
                        disk_role = disks[0].get("Type", "data")
        except Exception as e:
            return {
                "original_price": 0,
                "trade_price": 0,
                "estimated": False,
                "error": f"获取磁盘信息失败: {str(e)[:80]}",
            }

    if not instance_id:
        return {
            "original_price": 0,
            "trade_price": 0,
            "estimated": False,
            "error": "磁盘未挂载到实例",
        }

    # 查询实例续费价格
    try:
        req = CommonRequest()
        req.set_domain(f"ecs.{region_id}.aliyuncs.com")
        req.set_method("POST")
        req.set_version("2014-05-26")
        req.set_action_name("DescribeRenewalPrice")
        req.add_query_param("RegionId", region_id)
        req.add_query_param("ResourceId", instance_id)
        req.add_query_param("Period", 1)
        req.add_query_param("PriceUnit", "Month")

        response = client.do_action_with_exception(req)
        data = json.loads(response)

        # 解析价格信息
        price_info = data.get("PriceInfo", {}).get("Price", {})
        detail_infos = price_info.get("DetailInfos", {}).get("DetailInfo", [])

        if not isinstance(detail_infos, list):
            detail_infos = [detail_infos]

        # 根据磁盘角色确定价格类型
        # disk_role: 'system' 或 'data' (来自磁盘的Type字段)
        if disk_role and disk_role.lower() == "system":
            disk_type = "systemDisk"
        else:
            disk_type = "dataDisk"

        # 查找对应类型的价格
        for detail in detail_infos:
            if detail.get("Resource") == disk_type:
                total_original_price = float(detail.get("OriginalPrice", 0))
                total_trade_price = float(detail.get("TradePrice", 0)) or float(
                    detail.get("DiscountPrice", 0)
                )

                # 如果找到价格信息
                if total_original_price > 0 or total_trade_price > 0:
                    # 如果是数据盘，且同一实例有多个数据盘，需要按大小比例分摊
                    if disk_type == "dataDisk" and all_disks_for_instance:
                        # 计算该实例所有数据盘的总大小
                        total_data_disk_size = sum(
                            d.get("磁盘大小(GB)", 0)
                            for d in all_disks_for_instance
                            if d.get("实例ID") == instance_id
                            and d.get("磁盘角色", "").lower() != "system"
                        )

                        if total_data_disk_size > 0 and disk_size > 0:
                            # 按大小比例分摊价格
                            ratio = disk_size / total_data_disk_size
                            original_price = total_original_price * ratio
                            trade_price = (
                                total_trade_price * ratio
                                if total_trade_price > 0
                                else original_price
                            )
                        else:
                            # 如果无法计算，返回总价格（标记为估算）
                            original_price = total_original_price
                            trade_price = (
                                total_trade_price if total_trade_price > 0 else original_price
                            )
                    else:
                        # 系统盘或单个数据盘，直接使用总价格
                        original_price = total_original_price
                        trade_price = total_trade_price if total_trade_price > 0 else original_price

                    return {
                        "original_price": round(original_price, 2),
                        "trade_price": round(trade_price, 2),
                        "estimated": False,
                        "error": None,
                    }

        # 如果没有找到对应的磁盘价格
        return {
            "original_price": 0,
            "trade_price": 0,
            "estimated": False,
            "error": f"未在实例续费价格中找到{disk_type}价格信息",
        }

    except Exception as e:
        error_str = str(e)
        # 检查是否是业务错误
        if "ChargeTypeViolation" in error_str or "PostPaid" in error_str:
            return {
                "original_price": 0,
                "trade_price": 0,
                "estimated": False,
                "error": "实例为按量付费",
            }
        return {"original_price": 0, "trade_price": 0, "estimated": False, "error": error_str[:100]}


def process_disk_price(disk_item):
    """处理单个磁盘的价格查询（用于并发）"""
    disk_data, access_key_id, access_key_secret, all_disks_for_instance = disk_item

    disk_id = disk_data["磁盘ID"]
    region_id = disk_data["区域"]
    disk_category = disk_data["磁盘类型"]
    disk_size = disk_data["磁盘大小(GB)"]
    instance_id = disk_data.get("实例ID", "")
    disk_role = disk_data.get("磁盘角色", "")  # system/data

    try:
        client = AcsClient(access_key_id, access_key_secret, region_id)
        price_info = get_disk_renewal_price(
            client,
            region_id,
            disk_id,
            disk_category,
            disk_size,
            instance_id=instance_id,
            disk_role=disk_role,
            all_disks_for_instance=all_disks_for_instance,
        )

        return {"success": True, "disk_id": disk_id, "price_info": price_info}
    except Exception as e:
        return {
            "success": False,
            "disk_id": disk_id,
            "price_info": {
                "original_price": 0,
                "trade_price": 0,
                "estimated": False,
                "error": str(e)[:100],
            },
        }


def main(tenant_name=None):
    """主函数"""
    print("💰 开始获取ECS云盘折扣信息...")
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

    # 读取云盘信息Excel文件
    reports_dir = os.path.join(".", tenant_name, "reports")
    disk_files = [
        f
        for f in os.listdir(reports_dir)
        if f.startswith(f"{tenant_name}_ecs_disks_") and f.endswith(".xlsx")
    ]

    if not disk_files:
        print("❌ 未找到云盘信息文件，请先运行 get_ecs_disks.py")
        return

    # 使用最新的文件
    latest_file = sorted(disk_files)[-1]
    disk_file_path = os.path.join(reports_dir, latest_file)

    print(f"📂 读取云盘信息文件: {latest_file}")
    df = pd.read_excel(disk_file_path)

    print(f"✅ 找到 {len(df)} 个云盘")

    # 只查询包年包月的磁盘
    prepaid_disks = df[df["付费类型"] == "PrePaid"].copy()

    if prepaid_disks.empty:
        print("⚠️ 未找到包年包月的磁盘")
        return

    print(f"📦 包年包月磁盘: {len(prepaid_disks)} 个")
    print(f"📦 按量付费磁盘: {len(df) - len(prepaid_disks)} 个")
    print("\n💾 开始查询折扣信息（并发处理）...")

    # 准备并发处理的数据
    # 将prepaid_disks转换为字典列表，用于按实例分组
    prepaid_disks_dict = prepaid_disks.to_dict("records")

    disk_items = [
        (row, access_key_id, access_key_secret, prepaid_disks_dict) for row in prepaid_disks_dict
    ]

    # 并发查询价格
    def progress_callback(completed, total):
        progress_pct = completed / total * 100
        sys.stdout.write(f"\r📊 查询进度: {completed}/{total} ({progress_pct:.1f}%)")
        sys.stdout.flush()

    results = process_concurrently(
        disk_items,
        process_disk_price,
        max_workers=10,
        description="查询云盘折扣",
        progress_callback=progress_callback,
    )

    print()  # 换行

    # 整理结果
    price_dict = {}
    for result in results:
        if result and result.get("success"):
            price_dict[result["disk_id"]] = result["price_info"]

    print(f"✅ 成功查询 {len(price_dict)} 个磁盘的价格信息")

    # 合并数据并计算折扣
    discount_data = []
    for _, row in prepaid_disks.iterrows():
        disk_id = row["磁盘ID"]
        price_info = price_dict.get(
            disk_id,
            {"original_price": 0, "trade_price": 0, "estimated": False, "error": "未查询到"},
        )

        original_price = price_info["original_price"]
        trade_price = price_info["trade_price"]

        # 计算折扣率
        if original_price > 0:
            discount_rate = (1 - trade_price / original_price) * 100
            discount_ratio = trade_price / original_price
        else:
            discount_rate = 0
            discount_ratio = 1

        discount_data.append(
            {
                "实例名称": row["实例名称"],
                "实例ID": row["实例ID"],
                "区域": row["区域"],
                "磁盘ID": disk_id,
                "磁盘名称": row["磁盘名称"],
                "磁盘类型": row["磁盘类型"],
                "磁盘大小(GB)": row["磁盘大小(GB)"],
                "磁盘角色": row["磁盘角色"],
                "基准价格(¥/月)": original_price,
                "续费价格(¥/月)": trade_price,
                "折扣率(%)": round(discount_rate, 2),
                "折扣": f"{discount_ratio:.1f}折" if discount_ratio < 1 else "1.0折",
                "是否估算": "是" if price_info.get("estimated") else "否",
                "错误信息": price_info.get("error", "") if price_info.get("error") else "",
            }
        )

    if not discount_data:
        print("⚠️ 未获取到任何折扣信息")
        return

    # 生成报告
    print("\n📊 生成折扣分析报告...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 创建输出目录
    output_dir = os.path.join(".", tenant_name, "discount")
    os.makedirs(output_dir, exist_ok=True)

    # 按折扣率排序
    discount_df = pd.DataFrame(discount_data)
    discount_df = discount_df.sort_values("折扣率(%)", ascending=False)

    # Excel报告
    excel_file = os.path.join(output_dir, f"{tenant_name}_disk_discount_{timestamp}.xlsx")
    discount_df.to_excel(excel_file, index=False)
    print(f"✅ Excel报告已生成: {excel_file}")

    # 统计信息
    valid_discounts = discount_df[discount_df["是否估算"] == "否"]
    if len(valid_discounts) > 0:
        avg_discount = valid_discounts["折扣率(%)"].mean()
        min_discount = valid_discounts["折扣率(%)"].min()
        max_discount = valid_discounts["折扣率(%)"].max()
        total_monthly_cost = valid_discounts["续费价格(¥/月)"].sum()

        print("\n📊 折扣统计:")
        print(f"  包年包月磁盘数: {len(discount_data)} 个")
        print(f"  有效折扣数据: {len(valid_discounts)} 个")
        print(f"  平均折扣: {avg_discount:.1f}% ({1 - avg_discount/100:.1f}折)")
        print(f"  最低折扣: {min_discount:.1f}% ({1 - min_discount/100:.1f}折)")
        print(f"  最高折扣: {max_discount:.1f}% ({1 - max_discount/100:.1f}折)")
        print(f"  当前月总成本: ¥{total_monthly_cost:,.2f}")
        print(f"  预计年成本: ¥{total_monthly_cost * 12:,.2f}")

    # 按折扣范围统计
    print("\n📋 按折扣范围统计:")
    discount_ranges = [
        (90, 100, "90-100%"),
        (70, 90, "70-90%"),
        (50, 70, "50-70%"),
        (38, 50, "38-50%"),
        (0, 38, "0-38%"),
    ]

    for min_d, max_d, label in discount_ranges:
        if len(valid_discounts) > 0:
            count = len(
                valid_discounts[
                    (valid_discounts["折扣率(%)"] >= min_d) & (valid_discounts["折扣率(%)"] < max_d)
                ]
            )
            if count > 0:
                total_cost = valid_discounts[
                    (valid_discounts["折扣率(%)"] >= min_d) & (valid_discounts["折扣率(%)"] < max_d)
                ]["续费价格(¥/月)"].sum()
                print(f"  {label}: {count} 个磁盘, 月成本: ¥{total_cost:,.2f}")

    print("\n" + "=" * 80)
    print("🎉 完成！")
    print("=" * 80)


if __name__ == "__main__":
    tenant_name = sys.argv[1] if len(sys.argv) > 1 else None
    main(tenant_name)
