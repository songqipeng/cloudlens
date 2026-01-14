#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudLens基础使用示例

演示如何使用CloudLens进行基本的云资源查询和分析
"""

from cloudlens.core.config import ConfigManager
from cloudlens.providers.aliyun.provider import AliyunProvider


def example_1_list_ecs_instances():
    """示例1: 查询ECS实例"""
    print("=" * 60)
    print("示例1: 查询ECS实例")
    print("=" * 60)
    
    # 1. 初始化配置管理器
    cm = ConfigManager()
    accounts = cm.list_accounts()
    
    if not accounts:
        print("❌ 未找到配置的账号，请先添加账号")
        print("   运行: python3 main_cli.py config add")
        return
    
    # 2. 使用第一个账号
    account = accounts[0]
    print(f"✅ 使用账号: {account.name} ({account.provider})")
    
    # 3. 创建Provider
    provider = AliyunProvider(
        account_name=account.name,
        access_key_id=account.access_key_id,
        access_key_secret=account.access_key_secret,
        region=account.region
    )
    
    # 4. 查询ECS实例
    print("\n正在查询ECS实例...")
    instances = provider.list_instances()
    
    print(f"\n找到 {len(instances)} 个ECS实例:\n")
    for inst in instances[:5]:  # 只显示前5个
        print(f"  • {inst.name} ({inst.id})")
        print(f"    状态: {inst.status.value}")
        print(f"    区域: {inst.region}")
        if inst.public_ips:
            print(f"    公网IP: {', '.join(inst.public_ips)}")
        print()


def example_2_filter_resources():
    """示例2: 筛选资源"""
    print("=" * 60)
    print("示例2: 筛选运行中的实例")
    print("=" * 60)
    
    from cloudlens.core.filter_engine import FilterEngine
    from cloudlens.models.resource import ResourceStatus
    
    cm = ConfigManager()
    account = cm.list_accounts()[0]
    
    provider = AliyunProvider(
        account_name=account.name,
        access_key_id=account.access_key_id,
        access_key_secret=account.access_key_secret,
        region=account.region
    )
    
    # 获取所有实例
    all_instances = provider.list_instances()
    
    # 筛选运行中的实例
    running_instances = FilterEngine.apply_filter(
        all_instances, 
        "status=Running"
    )
    
    print(f"\n总实例数: {len(all_instances)}")
    print(f"运行中的实例: {len(running_instances)}\n")
    
    for inst in running_instances[:3]:
        print(f"  • {inst.name} - {inst.status.value}")


def example_3_check_idle_resources():
    """示例3: 检查闲置资源"""
    print("=" * 60)
    print("示例3: 检查闲置ECS实例")
    print("=" * 60)
    
    from cloudlens.core.idle_detector import IdleDetector
    import time
    
    cm = ConfigManager()
    account = cm.list_accounts()[0]
    
    provider = AliyunProvider(
        account_name=account.name,
        access_key_id=account.access_key_id,
        access_key_secret=account.access_key_secret,
        region=account.region
    )
    
    instances = provider.list_instances()
    
    print(f"\n检查 {len(instances)} 个实例的闲置情况...\n")
    
    # 获取最近14天的监控数据
    end_time = int(time.time())
    start_time = end_time - 14 * 24 * 3600  # 14天前
    
    idle_count = 0
    
    for inst in instances[:3]:  # 只检查前3个作为示例
        print(f"检查: {inst.name}")
        
        # 获取监控指标
        metrics = provider.get_metric(
            inst.id,
            "CPUUtilization",
            start_time,
            end_time
        )
        
        # 简化：假设获取到了指标数据
        sample_metrics = {
            'cpu_avg': 3.0,
            'memory_avg': 15.0,
            'net_in_avg': 500,
            'disk_iops_avg': 50
        }
        
        is_idle, reasons = IdleDetector.is_ecs_idle(sample_metrics)
        
        if is_idle:
            idle_count += 1
            print(f"  ❌ 闲置")
            for reason in reasons:
                print(f"     - {reason}")
        else:
            print(f"  ✅ 正常使用")
        print()
    
    print(f"闲置实例数: {idle_count}/{len(instances)}")


def main():
    """主函数"""
    print("\n🚀 CloudLens 基础使用示例\n")
    
    try:
        # 运行示例
        example_1_list_ecs_instances()
        print("\n" + "=" * 60 + "\n")
        
        example_2_filter_resources()
        print("\n" + "=" * 60 + "\n")
        
        example_3_check_idle_resources()
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
