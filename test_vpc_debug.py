#!/usr/bin/env python3
"""
测试VPC数据获取和转换的调试脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import ConfigManager
from cli.utils import get_provider
from models.resource import UnifiedResource, ResourceType, ResourceStatus
import json

def test_vpc_data():
    """测试VPC数据的获取和转换"""
    print("=" * 60)
    print("开始测试VPC数据获取和转换")
    print("=" * 60)
    
    try:
        # 获取provider（使用默认账号或第一个可用账号）
        cm = ConfigManager()
        accounts = cm.list_accounts()
        
        if not accounts:
            print("❌ 没有找到可用的账号配置")
            return
        
        account_name = accounts[0].name
        print(f"\n📋 使用账号: {account_name}")
        
        account_config = cm.get_account(account_name)
        if not account_config:
            print(f"❌ 账号 '{account_name}' 配置不存在")
            return
        
        provider = get_provider(account_config)
        print(f"✅ Provider类型: {provider.provider_name}")
        
        # 获取VPC列表
        print("\n🔍 正在获取VPC列表...")
        vpcs = provider.list_vpcs()
        print(f"✅ 获取到 {len(vpcs)} 个VPC")
        
        if not vpcs:
            print("⚠️  没有VPC数据，无法继续测试")
            return
        
        # 打印原始VPC数据
        print("\n" + "=" * 60)
        print("原始VPC数据（前3个）:")
        print("=" * 60)
        for i, vpc in enumerate(vpcs[:3], 1):
            print(f"\nVPC #{i}:")
            print(json.dumps(vpc, indent=2, ensure_ascii=False))
            print(f"  类型: {type(vpc)}")
            print(f"  键: {list(vpc.keys()) if isinstance(vpc, dict) else 'N/A'}")
        
        # 模拟API中的转换逻辑
        print("\n" + "=" * 60)
        print("模拟API转换逻辑:")
        print("=" * 60)
        
        resources = []
        for idx, vpc in enumerate(vpcs[:3], 1):  # 只处理前3个
            print(f"\n处理VPC #{idx}:")
            print(f"  原始数据: {vpc}")
            
            # 获取VPC ID和名称
            vpc_id = vpc.get("id") or vpc.get("VpcId") or ""
            vpc_name = vpc.get("name") or vpc.get("VpcName") or ""
            
            print(f"  提取的ID: '{vpc_id}' (类型: {type(vpc_id)}, 长度: {len(vpc_id) if vpc_id else 0})")
            print(f"  提取的名称: '{vpc_name}'")
            
            # 检查ID是否为空
            if not vpc_id:
                print(f"  ⚠️  VPC ID为空，跳过")
                continue
            
            # 创建UnifiedResource
            resource = UnifiedResource(
                id=vpc_id,
                name=vpc_name if vpc_name else vpc_id,
                resource_type=ResourceType.VPC,
                status=ResourceStatus.RUNNING,
                provider=provider.provider_name,
                region=vpc.get("region") or vpc.get("RegionId", account_name),
            )
            
            print(f"  ✅ 创建UnifiedResource:")
            print(f"     id: '{resource.id}'")
            print(f"     name: '{resource.name}'")
            print(f"     region: '{resource.region}'")
            print(f"     vpc_id属性: {getattr(resource, 'vpc_id', 'N/A')}")
            
            resources.append(resource)
        
        # 模拟API中的最终转换
        print("\n" + "=" * 60)
        print("模拟API最终转换（转换为前端格式）:")
        print("=" * 60)
        
        type_str = "vpc"
        result = []
        for r in resources:
            print(f"\n转换资源: id={r.id}, name={r.name}")
            
            # 模拟API中的逻辑
            display_name = r.name or r.id or "-"
            if type_str == "vpc" and not r.name:
                display_name = r.id or "-"
            
            # 关键部分：VPC资源的vpc_id设置
            if type_str == "vpc":
                # 原始代码: vpc_id_value = r.id or None
                # 修复后代码
                vpc_id_value = r.id if (hasattr(r, "id") and r.id and str(r.id).strip()) else None
                print(f"  VPC ID检查:")
                print(f"    hasattr(r, 'id'): {hasattr(r, 'id')}")
                print(f"    r.id: '{r.id}'")
                print(f"    r.id and str(r.id).strip(): {r.id and str(r.id).strip() if r.id else False}")
                print(f"    最终vpc_id_value: {vpc_id_value}")
            else:
                vpc_id_value = r.vpc_id if hasattr(r, "vpc_id") and r.vpc_id else None
            
            result_item = {
                "id": r.id or "-",
                "name": display_name,
                "type": type_str,
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "region": r.region,
                "spec": r.spec or "-",
                "cost": 0.0,
                "tags": r.tags if hasattr(r, "tags") and r.tags else {},
                "created_time": r.created_time.isoformat() if hasattr(r, "created_time") and r.created_time else None,
                "public_ips": r.public_ips if hasattr(r, "public_ips") else [],
                "private_ips": r.private_ips if hasattr(r, "private_ips") else [],
                "vpc_id": vpc_id_value,
            }
            
            print(f"  ✅ 最终结果:")
            print(f"    id: '{result_item['id']}'")
            print(f"    name: '{result_item['name']}'")
            print(f"    vpc_id: {result_item['vpc_id']} (类型: {type(result_item['vpc_id'])})")
            
            result.append(result_item)
        
        # 打印最终结果
        print("\n" + "=" * 60)
        print("最终转换结果（JSON格式）:")
        print("=" * 60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 检查问题
        print("\n" + "=" * 60)
        print("问题诊断:")
        print("=" * 60)
        for item in result:
            if item.get("vpc_id") is None or item.get("vpc_id") == "":
                print(f"❌ 发现问题: VPC ID为空")
                print(f"   资源ID: {item.get('id')}")
                print(f"   资源名称: {item.get('name')}")
                print(f"   vpc_id值: {item.get('vpc_id')}")
            else:
                print(f"✅ VPC ID正常: {item.get('vpc_id')}")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vpc_data()
