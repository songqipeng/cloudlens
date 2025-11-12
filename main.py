#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云资源分析主程序
支持多租户、资源利用率分析和折扣分析
"""

import sys
import os
import argparse
import json
from datetime import datetime

# 添加模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'resource_modules'))


def load_config():
    """加载配置文件"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print("❌ 配置文件 config.json 不存在")
        sys.exit(1)
    except json.JSONDecodeError:
        print("❌ 配置文件格式错误")
        sys.exit(1)


def get_tenant_config(config, tenant_name=None):
    """获取租户配置"""
    if tenant_name is None:
        tenant_name = config.get('default_tenant')
    
    tenants = config.get('tenants', {})
    if tenant_name not in tenants:
        print(f"❌ 未找到租户: {tenant_name}")
        print(f"可用租户: {', '.join(tenants.keys())}")
        sys.exit(1)
    
    return tenants[tenant_name]


def show_help():
    """显示帮助信息"""
    print("""
🚀 阿里云资源分析工具

使用方法:
    python main.py [租户] [操作] [资源类型]

参数说明:
    租户          - 租户名称（如：ydzn），默认为default_tenant
    操作          - 操作类型：cru（资源利用率）、discount（折扣分析）、cost（费用分析）
    资源类型      - 资源类型：ecs、rds、redis、mongodb、clickhouse、oss、slb、eip、nas、ack、eci、polardb、all（全部）

凭证管理:
    python main.py setup-credentials     - 交互式设置凭证（保存到系统密钥环）
    python main.py list-credentials      - 列出所有凭证

示例:
    资源利用率分析:
    python main.py ydzn cru              # ydzn租户所有资源利用率
    python main.py cru                    # 默认租户所有资源利用率
    python main.py ydzn cru ecs           # ydzn租户ECS利用率
    python main.py cru ecs                # 默认租户ECS利用率
    
    折扣分析:
    python main.py ydzn discount          # ydzn租户所有资源折扣
    python main.py discount               # 默认租户所有资源折扣
    python main.py ydzn discount ecs      # ydzn租户ECS折扣
    python main.py discount ecs          # 默认租户ECS折扣

选项:
    -h, --help      显示帮助信息
    -v, --version   显示版本信息
    --no-cache      不使用缓存，重新获取数据
""")


# ECS分析函数（支持新旧两种方式）
def run_ecs_analysis(args, tenant_name=None, tenant_config=None):
    """运行ECS分析（优先使用新的统一架构）"""
    print("🖥️ 启动ECS实例分析...")
    try:
        # 优先使用新的基于BaseResourceAnalyzer的ECS分析器
        try:
            from resource_modules.ecs_analyzer import ECSAnalyzer
            analyzer = ECSAnalyzer(
                tenant_config['access_key_id'],
                tenant_config['access_key_secret'],
                tenant_name
            )
            idle_instances = analyzer.analyze_ecs_resources()
            analyzer.generate_ecs_report(idle_instances, output_dir=".")
            return True
        except ImportError:
            # 如果新分析器不存在，回退到旧版本
            from check_ecs_idle_fixed import main as ecs_main
            ecs_main(tenant_name=tenant_name, output_base_dir=".", tenant_config=tenant_config)
            return True
    except ImportError as e:
        print(f"❌ ECS分析模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ ECS分析失败: {e}")
        return False


def run_rds_analysis(args, tenant_config=None):
    """运行RDS分析"""
    print("🗄️ 启动RDS数据库分析...")
    try:
        from rds_analyzer import main as rds_main
        rds_main()
    except ImportError as e:
        print(f"❌ RDS分析模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ RDS分析失败: {e}")
        return False
    return True


def run_redis_analysis(args, tenant_config=None):
    """运行Redis分析"""
    print("🔴 启动Redis缓存分析...")
    try:
        from redis_analyzer import main as redis_main
        redis_main()
    except ImportError as e:
        print(f"❌ Redis分析模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ Redis分析失败: {e}")
        return False
    return True


def run_mongodb_analysis(args, tenant_config=None):
    """运行MongoDB分析"""
    print("🍃 启动MongoDB数据库分析...")
    try:
        from mongodb_analyzer import main as mongodb_main
        mongodb_main()
    except ImportError as e:
        print(f"❌ MongoDB分析模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ MongoDB分析失败: {e}")
        return False
    return True


def run_clickhouse_analysis(args, tenant_config=None, tenant_name=None):
    """运行ClickHouse分析"""
    print("📊 启动ClickHouse数据库分析...")
    try:
        from resource_modules.clickhouse_analyzer import ClickHouseAnalyzer
        if not tenant_config:
            print("❌ 缺少租户配置")
            return False
        
        analyzer = ClickHouseAnalyzer(
            tenant_config.get('access_key_id'),
            tenant_config.get('access_key_secret')
        )
        idle_instances = analyzer.analyze_clickhouse_resources()
        
        analyzer.generate_clickhouse_report(idle_instances, tenant_name=tenant_name)
        return True
    except ImportError as e:
        print(f"❌ ClickHouse分析模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ ClickHouse分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    return True


def run_oss_analysis(args, tenant_config=None):
    """运行OSS分析"""
    print("☁️ 启动OSS对象存储分析...")
    try:
        from resource_modules.oss_analyzer import main as oss_main
        if tenant_config:
            oss_main(
                access_key_id=tenant_config.get('access_key_id'),
                access_key_secret=tenant_config.get('access_key_secret')
            )
        else:
            oss_main()
    except ImportError as e:
        print(f"❌ OSS分析模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ OSS分析失败: {e}")
        return False
    return True


def run_slb_analysis(args, tenant_config=None):
    """运行SLB分析"""
    print("⚖️ 启动SLB负载均衡分析...")
    try:
        from resource_modules.slb_analyzer import main as slb_main
        if tenant_config:
            slb_main(
                access_key_id=tenant_config.get('access_key_id'),
                access_key_secret=tenant_config.get('access_key_secret')
            )
        else:
            slb_main()
    except ImportError as e:
        print(f"❌ SLB分析模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ SLB分析失败: {e}")
        return False
    return True


def run_eip_analysis(args, tenant_config=None):
    """运行EIP分析"""
    print("🌐 启动EIP弹性公网IP分析...")
    try:
        from resource_modules.eip_analyzer import main as eip_main
        if tenant_config:
            eip_main(
                access_key_id=tenant_config.get('access_key_id'),
                access_key_secret=tenant_config.get('access_key_secret')
            )
        else:
            eip_main()
    except ImportError as e:
        print(f"❌ EIP分析模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ EIP分析失败: {e}")
        return False
    return True


def run_all_cru_analysis(args, tenant_name, tenant_config):
    """运行所有资源利用率分析"""
    print("🌍 启动全资源利用率分析...")
    
    analyzers = [
        ("ECS", lambda a, tc, tn: run_ecs_analysis(a, tn, tc)),
        ("RDS", lambda a, tc, tn: run_rds_analysis(a, tc)),
        ("Redis", lambda a, tc, tn: run_redis_analysis(a, tc)),
        ("MongoDB", lambda a, tc, tn: run_mongodb_analysis(a, tc)),
        ("ClickHouse", lambda a, tc, tn: run_clickhouse_analysis(a, tc, tn)),
        ("OSS", lambda a, tc, tn: run_oss_analysis(a, tc)),
        ("SLB", lambda a, tc, tn: run_slb_analysis(a, tc)),
        ("EIP", lambda a, tc, tn: run_eip_analysis(a, tc)),
        ("NAS", lambda a, tc, tn: run_nas_analysis(a, tc, tn)),
        ("ACK", lambda a, tc, tn: run_ack_analysis(a, tc, tn)),
        ("ECI", lambda a, tc, tn: run_eci_analysis(a, tc, tn)),
        ("PolarDB", lambda a, tc, tn: run_polardb_analysis(a, tc, tn)),
    ]
    
    results = {}
    for name, analyzer_func in analyzers:
        print(f"\n{'='*50}")
        print(f"开始分析 {name} 资源...")
        try:
            success = analyzer_func(args, tenant_config, tenant_name)
            results[name] = "✅ 成功" if success else "❌ 失败"
        except Exception as e:
            print(f"❌ {name} 分析异常: {e}")
            results[name] = "❌ 异常"
    
    # 显示分析结果汇总
    print(f"\n{'='*50}")
    print("📊 全资源利用率分析结果汇总:")
    for name, result in results.items():
        print(f"  {name}: {result}")
    
    return True


def run_cost_analysis(tenant_name, tenant_config):
    """运行费用分析"""
    print("💰 启动费用分布分析...")
    try:
        from resource_modules.cost_analyzer import CostAnalyzer
        
        analyzer = CostAnalyzer(
            tenant_name,
            tenant_config['access_key_id'],
            tenant_config['access_key_secret']
        )
        
        result = analyzer.generate_cost_report()
        return True
    except ImportError as e:
        print(f"❌ 费用分析模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 费用分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_discount_analysis(args, tenant_name, tenant_config, resource_type='all'):
    """运行折扣分析"""
    print("💰 启动折扣分析...")
    
    try:
        from resource_modules.discount_analyzer import DiscountAnalyzer
        
        analyzer = DiscountAnalyzer(
            tenant_name,
            tenant_config['access_key_id'],
            tenant_config['access_key_secret']
        )
        
        if resource_type == 'ecs':
            analyzer.analyze_ecs_discounts(output_base_dir=".")
        elif resource_type == 'rds':
            analyzer.analyze_rds_discounts(output_base_dir=".")
        elif resource_type == 'redis':
            analyzer.analyze_redis_discounts(output_base_dir=".")
        elif resource_type == 'mongodb':
            analyzer.analyze_mongodb_discounts(output_base_dir=".")
        elif resource_type == 'clickhouse':
            analyzer.analyze_clickhouse_discounts(output_base_dir=".")
        elif resource_type == 'nas':
            analyzer.analyze_nas_discounts(output_base_dir=".")
        elif resource_type == 'polardb':
            analyzer.analyze_polardb_discounts(output_base_dir=".")
        elif resource_type == 'ack':
            analyzer.analyze_ack_discounts(output_base_dir=".")
        elif resource_type == 'eci':
            analyzer.analyze_eci_discounts(output_base_dir=".")
        elif resource_type == 'slb':
            analyzer.analyze_slb_discounts(output_base_dir=".")
        elif resource_type == 'disk':
            analyzer.analyze_disk_discounts(output_base_dir=".")
        elif resource_type == 'vpn':
            analyzer.analyze_vpn_discounts(output_base_dir=".")
        elif resource_type == 'nat':
            analyzer.analyze_nat_discounts(output_base_dir=".")
        elif resource_type == 'elasticsearch':
            analyzer.analyze_elasticsearch_discounts(output_base_dir=".")
        elif resource_type == 'all-products':
            # 分析所有支持的产品
            analyzer.analyze_all_products_discounts(output_base_dir=".")
        elif resource_type in ['oss', 'eip', 'sls', 'cdn', 'datav', 'dns', 'ots', 'vpc', 'pvtz', 'green', 'dypnsapi']:
            print(f"⚠️ {resource_type.upper()}暂不支持包年包月模式，无法进行折扣分析")
            print(f"   这些服务通常采用按量付费模式")
        else:
            print(f"⚠️ 支持的折扣分析类型: ECS, RDS, Redis, MongoDB, ClickHouse, NAS, PolarDB, SLB, Disk, VPN, NAT, Elasticsearch")
            print(f"   使用 'all-products' 分析所有支持的产品")
            if resource_type == 'all':
                print("分析ECS折扣...")
                analyzer.analyze_ecs_discounts(output_base_dir=".")
                print("\n分析RDS折扣...")
                analyzer.analyze_rds_discounts(output_base_dir=".")
                print("\n分析Redis折扣...")
                analyzer.analyze_redis_discounts(output_base_dir=".")
                print("\n分析MongoDB折扣...")
                analyzer.analyze_mongodb_discounts(output_base_dir=".")
                print("\n分析ClickHouse折扣...")
                analyzer.analyze_clickhouse_discounts(output_base_dir=".")
                print("\n分析NAS折扣...")
                analyzer.analyze_nas_discounts(output_base_dir=".")
                print("\n分析PolarDB折扣...")
                analyzer.analyze_polardb_discounts(output_base_dir=".")
                print("\n分析SLB折扣...")
                analyzer.analyze_slb_discounts(output_base_dir=".")
            else:
                print(f"不支持的资源类型: {resource_type}")
        
        return True
    except ImportError as e:
        print(f"❌ 折扣分析模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 折扣分析失败: {e}")
        return False


def main():
    """主函数"""
    # 解析命令行参数
    args_list = sys.argv[1:]
    
    # 处理帮助和版本
    if '--help' in args_list or '-h' in args_list or len(args_list) == 0:
        show_help()
        return
    
    if '--version' in args_list or '-v' in args_list:
        print("阿里云资源分析工具 v2.0.0")
        print("支持多租户、资源利用率分析、折扣分析")
        return
    
    # 处理凭证管理命令
    if args_list[0] == 'setup-credentials':
        try:
            from utils.credential_manager import setup_credentials_interactive
            setup_credentials_interactive()
        except ImportError:
            print("❌ 凭证管理功能需要安装keyring库: pip install keyring")
        return
    
    if args_list[0] == 'list-credentials':
        try:
            from utils.credential_manager import CredentialManager
            config = load_config()
            tenants = config.get('tenants', {})
            print("📋 已配置的租户:")
            for tenant, tenant_config in tenants.items():
                use_keyring = tenant_config.get('use_keyring', False)
                status = "🔐 Keyring" if use_keyring else "📄 配置文件"
                print(f"  - {tenant}: {status}")
        except Exception as e:
            print(f"❌ 列出凭证失败: {e}")
        return
    
    # 加载配置
    config = load_config()
    default_tenant = config.get('default_tenant')
    
    # 解析参数：python main.py [tenant] [action] [resource_type]
    if len(args_list) == 1:
        # python main.py cru
        action = args_list[0]
        tenant_name = default_tenant
        resource_type = 'all'
    elif len(args_list) == 2:
        # python main.py ydzn cru 或 python main.py cru ecs
        if args_list[0] in config.get('tenants', {}):
            # python main.py ydzn cru
            tenant_name = args_list[0]
            action = args_list[1]
            resource_type = 'all'
        else:
            # python main.py cru ecs
            action = args_list[0]
            tenant_name = default_tenant
            resource_type = args_list[1]
    elif len(args_list) == 3:
        # python main.py ydzn cru ecs
        tenant_name = args_list[0]
        action = args_list[1]
        resource_type = args_list[2]
    else:
        print("❌ 参数错误")
        show_help()
        return
    
    # 获取租户配置
    tenant_config = get_tenant_config(config, tenant_name)
    
    # 尝试从Keyring获取凭证（如果配置了use_keyring）
    try:
        from utils.credential_manager import get_credentials_from_config_or_keyring
        cloud_credentials = get_credentials_from_config_or_keyring('aliyun', tenant_name, config)
        if cloud_credentials:
            # 使用Keyring中的凭证更新tenant_config
            tenant_config.update(cloud_credentials)
    except ImportError:
        # keyring未安装，使用配置文件中的凭证
        pass
    except Exception as e:
        print(f"⚠️  从Keyring获取凭证失败，使用配置文件: {e}")
    
    tenant_display_name = tenant_config.get('display_name', tenant_name)
    
    # 显示开始信息
    print("🚀 阿里云资源分析工具 v2.0.0")
    print("=" * 80)
    print(f"🏢 租户: {tenant_display_name} ({tenant_name})")
    print(f"🎯 操作: {action.upper()}")
    print(f"📦 资源: {resource_type.upper()}")
    print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    success = False
    
    # 根据操作类型执行相应分析
    if action == 'cru':
        # 资源利用率分析
        if resource_type == 'ecs':
            success = run_ecs_analysis(None, tenant_name, tenant_config)
        elif resource_type == 'rds':
            success = run_rds_analysis(None, tenant_config)
        elif resource_type == 'redis':
            success = run_redis_analysis(None, tenant_config)
        elif resource_type == 'mongodb':
            success = run_mongodb_analysis(None, tenant_config)
        elif resource_type == 'clickhouse':
            success = run_clickhouse_analysis(None, tenant_config, tenant_name)
        elif resource_type == 'oss':
            success = run_oss_analysis(None, tenant_config)
        elif resource_type == 'slb':
            success = run_slb_analysis(None, tenant_config)
        elif resource_type == 'eip':
            success = run_eip_analysis(None, tenant_config)
        elif resource_type == 'nas':
            success = run_nas_analysis(None, tenant_config, tenant_name)
        elif resource_type == 'ack':
            success = run_ack_analysis(None, tenant_config, tenant_name)
        elif resource_type == 'eci':
            success = run_eci_analysis(None, tenant_config, tenant_name)
        elif resource_type == 'polardb':
            success = run_polardb_analysis(None, tenant_config, tenant_name)
        elif resource_type == 'all':
            success = run_all_cru_analysis(None, tenant_name, tenant_config)
        else:
            print(f"❌ 不支持的资源类型: {resource_type}")
            show_help()
            return
    
    elif action == 'discount':
        # 折扣分析
        success = run_discount_analysis(None, tenant_name, tenant_config, resource_type)
    
    elif action == 'cost':
        # 费用分析
        success = run_cost_analysis(tenant_name, tenant_config)
    
    else:
        print(f"❌ 不支持的操作类型: {action}")
        print(f"支持的操作: cru（资源利用率）、discount（折扣分析）、cost（费用分析）")
        show_help()
        return
    
    # 显示结束信息
    print("\n" + "=" * 80)
    if success:
        print("🎉 分析完成！")
    else:
        print("❌ 分析失败！")
    print(f"📅 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    main()