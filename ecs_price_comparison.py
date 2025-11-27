#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECS价格对比分析
对比包年包月无折扣、包年包月4.5折和按量付费的费用
"""

import json
import sys
from datetime import datetime

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from utils.concurrent_helper import process_concurrently
from utils.logger import get_logger


class ECSPriceComparator:
    """ECS价格对比分析器"""

    def __init__(self, access_key_id, access_key_secret, tenant_name):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.tenant_name = tenant_name
        self.logger = get_logger("ecs_price_comparison")

    def get_ecs_instances(self, region="cn-hongkong"):
        """获取ECS实例列表"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain(f"ecs.{region}.aliyuncs.com")
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

                if "Instances" in data and "Instance" in data["Instances"]:
                    instances = data["Instances"]["Instance"]
                    if not isinstance(instances, list):
                        instances = [instances]

                    if len(instances) == 0:
                        break

                    for instance in instances:
                        all_instances.append(
                            {
                                "InstanceId": instance.get("InstanceId", ""),
                                "InstanceName": instance.get("InstanceName", ""),
                                "InstanceType": instance.get("InstanceType", ""),
                                "RegionId": instance.get("RegionId", region),
                                "ZoneId": instance.get("ZoneId", ""),
                                "Status": instance.get("Status", ""),
                                "ChargeType": instance.get("InstanceChargeType", ""),
                                "Cpu": instance.get("Cpu", 0),
                                "Memory": instance.get("Memory", 0) / 1024,  # 转换为GB
                                "CreationTime": instance.get("CreationTime", ""),
                                "ExpiredTime": instance.get("ExpiredTime", ""),
                                "InternetChargeType": instance.get("InternetChargeType", ""),
                                "InternetMaxBandwidthIn": instance.get("InternetMaxBandwidthIn", 0),
                                "InternetMaxBandwidthOut": instance.get(
                                    "InternetMaxBandwidthOut", 0
                                ),
                            }
                        )

                    total_count = data.get("TotalCount", 0)
                    if len(all_instances) >= total_count or len(instances) < 100:
                        break

                    page_number += 1
                else:
                    break

            return all_instances
        except Exception as e:
            self.logger.error(f"获取ECS实例失败: {e}")
            return []

    def get_instance_price(
        self,
        region,
        instance_type,
        charge_type="PrePaid",
        period=1,
        system_disk_category="cloud_essd",
    ):
        """获取实例价格"""
        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)
            request = CommonRequest()
            request.set_domain("ecs.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2014-05-26")
            request.set_action_name("DescribePrice")
            request.add_query_param("RegionId", region)
            request.add_query_param("InstanceType", instance_type)

            # 添加系统盘参数（必需）
            request.add_query_param("SystemDisk.Category", system_disk_category)
            request.add_query_param("SystemDisk.Size", 40)  # 默认40GB

            if charge_type == "PrePaid":
                # 包年包月
                request.add_query_param("PriceUnit", "Month")
                request.add_query_param("Period", period)
                request.add_query_param("PeriodUnit", "Month")
            else:
                # 按量付费 - 不设置PriceUnit，默认返回每小时价格
                pass

            response = client.do_action_with_exception(request)
            data = json.loads(response)

            if "PriceInfo" in data:
                price_info = data["PriceInfo"]
                price = price_info.get("Price", {})

                if charge_type == "PrePaid":
                    # 包年包月价格
                    original_price = price.get("OriginalPrice", 0)
                    trade_price = price.get("TradePrice", 0)
                    return {
                        "original_price": float(original_price),
                        "trade_price": float(trade_price),
                        "discount": (
                            float(trade_price) / float(original_price)
                            if original_price > 0
                            else 1.0
                        ),
                    }
                else:
                    # 按量付费价格（每小时）
                    # 按量付费返回的是PriceInfo.Price结构
                    # Price.OriginalPrice是原价，Price.TradePrice是折扣后价格
                    price_obj = price_info.get("Price", {})

                    # 获取原价（每小时）
                    hourly_original = float(price_obj.get("OriginalPrice", 0))
                    # 获取折扣后价格（每小时）
                    hourly_trade = float(price_obj.get("TradePrice", 0))

                    # 如果没有TradePrice，使用OriginalPrice
                    hourly_price = hourly_trade if hourly_trade > 0 else hourly_original

                    # 计算月度价格（按30天，720小时）
                    monthly_price = hourly_price * 24 * 30 if hourly_price > 0 else 0

                    return {
                        "hourly_price": hourly_price,
                        "hourly_original": hourly_original,
                        "monthly_price": monthly_price,
                    }
        except Exception as e:
            # 如果cloud_essd失败，尝试其他磁盘类型
            if system_disk_category == "cloud_essd":
                return self.get_instance_price(
                    region, instance_type, charge_type, period, "cloud_efficiency"
                )
            elif system_disk_category == "cloud_efficiency":
                return self.get_instance_price(
                    region, instance_type, charge_type, period, "cloud_ssd"
                )
            else:
                self.logger.warning(f"获取价格失败 {instance_type}: {e}")
                return None

    def calculate_costs(self, instances):
        """计算各种计费方式的费用"""
        results = []

        for instance in instances:
            instance_id = instance["InstanceId"]
            instance_type = instance["InstanceType"]
            region = instance["RegionId"]

            # 获取包年包月价格（无折扣）
            prepaid_price = self.get_instance_price(region, instance_type, "PrePaid", 1)

            # 获取按量付费价格
            postpaid_price = self.get_instance_price(region, instance_type, "PostPaid")

            if prepaid_price and postpaid_price:
                # 包年包月无折扣（原价）
                prepaid_original = prepaid_price["original_price"]

                # 包年包月4.5折
                prepaid_45_discount = prepaid_original * 0.45

                # 按量付费一个月（按30天计算）
                postpaid_monthly = postpaid_price["monthly_price"]

                # 计算节省金额
                savings_45_vs_original = prepaid_original - prepaid_45_discount
                savings_45_vs_postpaid = postpaid_monthly - prepaid_45_discount
                savings_prepaid_vs_postpaid = postpaid_monthly - prepaid_original

                results.append(
                    {
                        **instance,
                        "prepaid_original": prepaid_original,
                        "prepaid_45_discount": prepaid_45_discount,
                        "postpaid_monthly": postpaid_monthly,
                        "savings_45_vs_original": savings_45_vs_postpaid,
                        "savings_45_vs_postpaid": savings_45_vs_postpaid,
                        "savings_prepaid_vs_postpaid": savings_prepaid_vs_postpaid,
                        "prepaid_discount_rate": prepaid_price.get("discount", 1.0),
                    }
                )
            else:
                # 如果无法获取价格，使用估算
                results.append(
                    {
                        **instance,
                        "prepaid_original": 0,
                        "prepaid_45_discount": 0,
                        "postpaid_monthly": 0,
                        "savings_45_vs_original": 0,
                        "savings_45_vs_postpaid": 0,
                        "savings_prepaid_vs_postpaid": 0,
                        "prepaid_discount_rate": 1.0,
                        "price_error": True,
                    }
                )

        return results

    def generate_report(self, results):
        """生成对比报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 生成HTML报告
        html_file = f"{self.tenant_name}_ecs_price_comparison_{timestamp}.html"

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ECS价格对比分析 - {self.tenant_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Microsoft YaHei', 'PingFang SC', Arial, sans-serif; 
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{ 
            max-width: 1600px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 10px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2em; margin-bottom: 10px; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .summary-card h3 {{
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 10px;
        }}
        .summary-card p {{
            color: #666;
            font-size: 0.9em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{ background-color: #f8f9fa; }}
        tr:nth-child(even) {{ background-color: #fafafa; }}
        .num {{ text-align: right; font-family: 'Courier New', monospace; }}
        .savings {{ color: #10b981; font-weight: bold; }}
        .cost {{ color: #ef4444; font-weight: bold; }}
        .section {{
            padding: 30px;
        }}
        .section-title {{
            font-size: 1.5em;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💰 ECS价格对比分析</h1>
            <p>租户: {self.tenant_name} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>{len(results)}</h3>
                <p>ECS实例数</p>
            </div>
            <div class="summary-card">
                <h3>¥{sum(r.get('prepaid_original', 0) for r in results):,.2f}</h3>
                <p>包年包月原价(月)</p>
            </div>
            <div class="summary-card">
                <h3>¥{sum(r.get('prepaid_45_discount', 0) for r in results):,.2f}</h3>
                <p>包年包月4.5折(月)</p>
            </div>
            <div class="summary-card">
                <h3>¥{sum(r.get('postpaid_monthly', 0) for r in results):,.2f}</h3>
                <p>按量付费(月)</p>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📊 详细对比</h2>
            <table>
                <thead>
                    <tr>
                        <th>实例ID</th>
                        <th>实例名称</th>
                        <th>实例类型</th>
                        <th>CPU/内存</th>
                        <th>区域</th>
                        <th>计费方式</th>
                        <th>包年包月原价(¥/月)</th>
                        <th>包年包月4.5折(¥/月)</th>
                        <th>按量付费(¥/月)</th>
                        <th>4.5折节省(¥/月)</th>
                    </tr>
                </thead>
                <tbody>
"""

        total_original = 0
        total_45_discount = 0
        total_postpaid = 0
        total_savings = 0

        for result in results:
            instance_id = result.get("InstanceId", "")
            instance_name = result.get("InstanceName", "未命名")
            instance_type = result.get("InstanceType", "")
            cpu = result.get("Cpu", 0)
            memory = result.get("Memory", 0)
            region = result.get("RegionId", "")
            charge_type = result.get("ChargeType", "")

            prepaid_original = result.get("prepaid_original", 0)
            prepaid_45 = result.get("prepaid_45_discount", 0)
            postpaid = result.get("postpaid_monthly", 0)
            savings = result.get("savings_45_vs_postpaid", 0)

            total_original += prepaid_original
            total_45_discount += prepaid_45
            total_postpaid += postpaid
            total_savings += savings

            charge_type_display = {"PrePaid": "包年包月", "PostPaid": "按量付费"}.get(
                charge_type, charge_type
            )

            html_content += f"""
                    <tr>
                        <td><code>{instance_id[:20]}...</code></td>
                        <td>{instance_name}</td>
                        <td>{instance_type}</td>
                        <td>{cpu}核/{memory:.1f}GB</td>
                        <td>{region}</td>
                        <td>{charge_type_display}</td>
                        <td class="num cost">¥{prepaid_original:,.2f}</td>
                        <td class="num">¥{prepaid_45:,.2f}</td>
                        <td class="num cost">¥{postpaid:,.2f}</td>
                        <td class="num savings">¥{savings:,.2f}</td>
                    </tr>
"""

        html_content += f"""
                </tbody>
                <tfoot>
                    <tr style="background: #f8f9fa; font-weight: bold;">
                        <td colspan="6">合计</td>
                        <td class="num cost">¥{total_original:,.2f}</td>
                        <td class="num">¥{total_45_discount:,.2f}</td>
                        <td class="num cost">¥{total_postpaid:,.2f}</td>
                        <td class="num savings">¥{total_savings:,.2f}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">💡 费用分析</h2>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px;">
                <h3 style="margin-bottom: 15px;">费用对比（月度）</h3>
                <p><strong>包年包月原价:</strong> ¥{total_original:,.2f}/月</p>
                <p><strong>包年包月4.5折:</strong> ¥{total_45_discount:,.2f}/月</p>
                <p><strong>按量付费:</strong> ¥{total_postpaid:,.2f}/月</p>
                <hr style="margin: 15px 0; border: none; border-top: 1px solid #ddd;">
                <p><strong>4.5折相比原价节省:</strong> <span class="savings">¥{total_original - total_45_discount:,.2f}/月</span> ({((1 - total_45_discount/total_original)*100) if total_original > 0 else 0:.1f}%)</p>
                <p><strong>4.5折相比按量付费节省:</strong> <span class="savings">¥{total_savings:,.2f}/月</span> ({((total_savings/total_postpaid)*100) if total_postpaid > 0 else 0:.1f}%)</p>
                <p><strong>包年包月相比按量付费节省:</strong> <span class="savings">¥{total_postpaid - total_original:,.2f}/月</span> ({((1 - total_original/total_postpaid)*100) if total_postpaid > 0 else 0:.1f}%)</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"\n📄 HTML报告已生成: {html_file}")

        # 打印汇总信息
        print("\n" + "=" * 80)
        print("💰 ECS价格对比汇总")
        print("=" * 80)
        print(f"实例数量: {len(results)} 个")
        print(f"\n月度费用对比:")
        print(f"  包年包月原价:     ¥{total_original:,.2f}/月")
        print(f"  包年包月4.5折:    ¥{total_45_discount:,.2f}/月")
        print(f"  按量付费:         ¥{total_postpaid:,.2f}/月")
        print(f"\n节省金额:")
        if total_original > 0:
            print(
                f"  4.5折相比原价:    ¥{total_original - total_45_discount:,.2f}/月 ({((1 - total_45_discount/total_original)*100):.1f}%)"
            )
        if total_postpaid > 0:
            print(
                f"  4.5折相比按量:    ¥{total_savings:,.2f}/月 ({((total_savings/total_postpaid)*100):.1f}%)"
            )
            print(
                f"  包年包月相比按量: ¥{total_postpaid - total_original:,.2f}/月 ({((1 - total_original/total_postpaid)*100):.1f}%)"
            )
        print("=" * 80)

        return html_file


def main():
    if len(sys.argv) < 2:
        print("使用方法: python3 ecs_price_comparison.py <租户名称>")
        print("示例: python3 ecs_price_comparison.py cf")
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

    print(f"\n🔍 开始分析 {tenant_name} 租户的ECS价格...")
    print("=" * 80)

    comparator = ECSPriceComparator(access_key_id, access_key_secret, tenant_name)

    # 获取ECS实例（cf租户的资源在cn-hongkong）
    print("📦 获取ECS实例列表...")
    instances = comparator.get_ecs_instances("cn-hongkong")

    if not instances:
        print("❌ 未找到ECS实例")
        sys.exit(1)

    print(f"✅ 找到 {len(instances)} 个ECS实例")

    # 计算价格
    print("\n💰 查询价格信息（这可能需要一些时间）...")
    results = comparator.calculate_costs(instances)

    # 生成报告
    print("\n📊 生成对比报告...")
    comparator.generate_report(results)

    print("\n✅ 分析完成！")


if __name__ == "__main__":
    main()
