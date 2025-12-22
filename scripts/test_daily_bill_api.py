#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试费用中心API按天查询功能
检查账号是否有权限调用QueryInstanceBill API的按天查询
"""

import json
import sys
import os
from datetime import datetime, timedelta

# 添加父目录到sys.path以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import ConfigManager
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest


def test_daily_bill_api(account_name: str):
    """测试按天查询账单API"""
    cm = ConfigManager()
    account_config = cm.get_account(account_name)
    
    if not account_config:
        print(f"❌ 未找到账号配置: {account_name}")
        return False
    
    print(f"🔍 测试账号: {account_name}")
    print(f"   AccessKeyId: {account_config.access_key_id[:10]}...")
    print("=" * 80)
    
    client = AcsClient(
        account_config.access_key_id,
        account_config.access_key_secret,
        "cn-hangzhou"
    )
    
    # 测试1: 使用Granularity=DAILY参数按天查询
    print("\n📅 测试1: QueryInstanceBill API (Granularity=DAILY)")
    print("-" * 80)
    
    try:
        # 获取昨天的日期
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        billing_cycle = datetime.now().strftime("%Y-%m")
        
        request = CommonRequest()
        request.set_domain("business.aliyuncs.com")
        request.set_version("2017-12-14")
        request.set_action_name("QueryInstanceBill")
        request.set_method("POST")
        
        request.add_query_param("BillingCycle", billing_cycle)
        request.add_query_param("Granularity", "DAILY")  # 按天查询
        request.add_query_param("BillingDate", yesterday)  # 查询昨天的数据
        request.add_query_param("PageNum", 1)
        request.add_query_param("PageSize", 10)  # 只查询10条用于测试
        
        response = client.do_action_with_exception(request)
        data = json.loads(response)
        
        if data.get("Success"):
            items = data.get("Data", {}).get("Items", {}).get("Item", [])
            if not isinstance(items, list):
                items = [items] if items else []
            
            print(f"✅ API调用成功!")
            print(f"   返回记录数: {len(items)}")
            if items:
                print(f"   示例数据:")
                sample = items[0]
                print(f"     - 产品: {sample.get('ProductName', 'N/A')}")
                print(f"     - 实例ID: {sample.get('InstanceID', 'N/A')}")
                print(f"     - 成本: ¥{sample.get('PretaxAmount', 0)}")
                print(f"     - 账单日期: {sample.get('BillingDate', 'N/A')}")
            return True
        else:
            error_code = data.get("Code", "Unknown")
            error_msg = data.get("Message", "Unknown error")
            print(f"❌ API调用失败:")
            print(f"   错误代码: {error_code}")
            print(f"   错误信息: {error_msg}")
            
            # 检查是否是权限问题
            if "Permission" in error_msg or "Forbidden" in error_msg or "denied" in error_msg.lower():
                print(f"\n⚠️  可能是权限问题，请检查:")
                print(f"   1. AccessKey是否有BSS OpenAPI的查询权限")
                print(f"   2. 是否开通了费用中心API权限")
                print(f"   3. 是否支持按天查询（Granularity=DAILY）")
            
            return False
            
    except Exception as e:
        print(f"❌ API调用异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试2: 尝试使用DescribeInstanceBill API（新版本）
    print("\n📅 测试2: DescribeInstanceBill API (按天查询)")
    print("-" * 80)
    
    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        billing_cycle = datetime.now().strftime("%Y-%m")
        
        request = CommonRequest()
        request.set_domain("business.aliyuncs.com")
        request.set_version("2017-12-14")
        request.set_action_name("DescribeInstanceBill")
        request.set_method("POST")
        
        request.add_query_param("BillingCycle", billing_cycle)
        request.add_query_param("BillingDate", yesterday)
        request.add_query_param("PageNum", 1)
        request.add_query_param("PageSize", 10)
        
        response = client.do_action_with_exception(request)
        data = json.loads(response)
        
        if data.get("Success") or "Data" in data:
            items = data.get("Data", {}).get("Items", {}).get("Item", [])
            if not isinstance(items, list):
                items = [items] if items else []
            
            print(f"✅ DescribeInstanceBill API调用成功!")
            print(f"   返回记录数: {len(items)}")
            return True
        else:
            error_code = data.get("Code", "Unknown")
            error_msg = data.get("Message", "Unknown error")
            print(f"❌ DescribeInstanceBill API调用失败:")
            print(f"   错误代码: {error_code}")
            print(f"   错误信息: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ DescribeInstanceBill API调用异常: {str(e)}")
        return False


if __name__ == "__main__":
    # 从命令行参数获取账号名，如果没有则使用第一个可用账号
    account_name = sys.argv[1] if len(sys.argv) > 1 else None
    if not account_name:
        cm = ConfigManager()
        accounts = cm.list_accounts()
        if accounts:
            account_name = accounts[0].name
        else:
            print("❌ 未找到可用账号，请先配置账号")
            sys.exit(1)
    success = test_daily_bill_api(account_name)
    sys.exit(0 if success else 1)


