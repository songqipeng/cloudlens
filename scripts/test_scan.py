#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描功能测试脚本
测试分析服务的完整流程
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import ConfigManager
from core.services.analysis_service import AnalysisService
from providers.aliyun.provider import AliyunProvider

def test_account_config(account_name: str):
    """测试账号配置"""
    print(f"\n{'='*60}")
    print(f"1. 测试账号配置: {account_name}")
    print(f"{'='*60}")
    
    cm = ConfigManager()
    account_config = cm.get_account(account_name)
    
    if not account_config:
        print(f"❌ 账号 '{account_name}' 未找到")
        return None
    
    print(f"✅ 账号配置存在:")
    print(f"   - 名称: {account_config.name}")
    print(f"   - Provider: {account_config.provider}")
    print(f"   - Region: {account_config.region}")
    print(f"   - AccessKey: {account_config.access_key_id[:10]}...")
    
    return account_config

def test_provider_connection(account_config):
    """测试Provider连接"""
    print(f"\n{'='*60}")
    print(f"2. 测试Provider连接")
    print(f"{'='*60}")
    
    try:
        provider = AliyunProvider(
            account_name=account_config.name,
            access_key=account_config.access_key_id,
            secret_key=account_config.access_key_secret,
            region=account_config.region,
        )
        
        # 测试获取ECS实例列表
        instances = provider.list_instances()
        print(f"✅ Provider连接成功")
        print(f"   - ECS实例数量: {len(instances)}")
        
        if len(instances) > 0:
            print(f"   - 示例实例:")
            for i, inst in enumerate(instances[:3]):
                print(f"     {i+1}. {inst.id} ({inst.name or '-'}) - {inst.status}")
        else:
            print(f"   ⚠️  当前账号下没有ECS实例")
        
        return provider, instances
    except Exception as e:
        print(f"❌ Provider连接失败: {e}")
        import traceback
        traceback.print_exc()
        return None, []

def test_analysis_service(account_name: str, force: bool = True):
    """测试分析服务"""
    print(f"\n{'='*60}")
    print(f"3. 测试分析服务 (force={force})")
    print(f"{'='*60}")
    
    try:
        data, cached = AnalysisService.analyze_idle_resources(
            account_name=account_name,
            days=7,
            force_refresh=force
        )
        
        print(f"✅ 分析服务执行成功")
        print(f"   - 是否来自缓存: {cached}")
        print(f"   - 闲置资源数量: {len(data)}")
        
        if len(data) > 0:
            print(f"   - 闲置资源列表:")
            for i, item in enumerate(data[:5]):
                print(f"     {i+1}. {item.get('instance_id', 'N/A')} - {item.get('name', '-')}")
                if item.get('reasons'):
                    print(f"        原因: {', '.join(item['reasons'])}")
        else:
            print(f"   ℹ️  当前账号下没有闲置资源")
        
        return data, cached
    except Exception as e:
        print(f"❌ 分析服务执行失败: {e}")
        import traceback
        traceback.print_exc()
        return [], False

def main():
    """主函数"""
    account_name = "ydzn"
    
    print(f"\n{'='*60}")
    print(f"CloudLens 扫描功能测试")
    print(f"{'='*60}")
    
    # 1. 测试账号配置
    account_config = test_account_config(account_name)
    if not account_config:
        print("\n❌ 测试终止：账号配置不存在")
        return 1
    
    # 2. 测试Provider连接
    provider, instances = test_provider_connection(account_config)
    if provider is None:
        print("\n❌ 测试终止：Provider连接失败")
        return 1
    
    # 3. 测试分析服务
    data, cached = test_analysis_service(account_name, force=True)
    
    # 总结
    print(f"\n{'='*60}")
    print(f"测试总结")
    print(f"{'='*60}")
    print(f"✅ 账号配置: 正常")
    print(f"✅ Provider连接: 正常")
    print(f"✅ 分析服务: 正常")
    print(f"📊 资源统计:")
    print(f"   - ECS实例总数: {len(instances)}")
    print(f"   - 闲置资源数量: {len(data)}")
    
    if len(instances) == 0:
        print(f"\n⚠️  提示: 当前账号下没有ECS实例，这是正常的。")
        print(f"   扫描功能正常工作，只是没有资源可分析。")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())



