#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云资源分析主程序
支持多租户、资源利用率分析和折扣分析
"""

import argparse
import importlib
import json
import os
import pkgutil
import sys
from datetime import datetime
from typing import Any, Dict

# 添加模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), "resource_modules"))

from core.analyzer_registry import AnalyzerRegistry
from core.base_analyzer import BaseResourceAnalyzer


def load_config():
    """加载配置文件"""
    try:
        with open("config.json", "r") as f:
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
        tenant_name = config.get("default_tenant")

    tenants = config.get("tenants", {})
    if tenant_name not in tenants:
        print(f"❌ 未找到租户: {tenant_name}")
        print(f"可用租户: {', '.join(tenants.keys())}")
        sys.exit(1)

    return tenants[tenant_name]


def load_resource_modules():
    """动态加载所有资源分析模块以触发注册"""
    modules_dir = os.path.join(os.path.dirname(__file__), "resource_modules")
    for _, name, _ in pkgutil.iter_modules([modules_dir]):
        try:
            importlib.import_module(f"resource_modules.{name}")
        except ImportError as e:
            # 忽略导入错误，可能是依赖缺失
            pass


def show_help():
    """显示帮助信息"""
    print(
        """
🚀 阿里云资源分析工具 v2.3.0

使用方法:
    python main.py [租户] [操作] [资源类型]

参数说明:
    租户          - 租户名称（如：ydzn），默认为default_tenant
    操作          - 操作类型
    资源类型      - 资源类型：ecs, rds, redis, oss, slb, eip, ... 或 all（全部）

核心功能:
    cru [资源]        - 资源利用率分析
    discount [资源]   - 折扣分析
    cost              - 费用分析
    network           - 网络资源分析

P1新功能 (成本预测与优化):
    predict           - 成本预测
    optimize          - 优化建议分析

凭证管理:
    setup-credentials     - 交互式设置凭证（保存到系统密钥环）
    list-credentials      - 列出所有凭证

示例:
    # 资源利用率分析
    python main.py ydzn cru all
    python main.py ydzn cru ecs
    
    # 成本预测 (P1)
    python main.py ydzn predict
    
    # 优化建议 (P1)
    python main.py ydzn optimize

选项:
    -h, --help      显示帮助信息
    -v, --version   显示版本信息
    --no-cache      不使用缓存，重新获取数据
"""
    )


def run_cru_analysis(tenant_name: str, tenant_config: Dict[str, Any], resource_type: str) -> bool:
    """运行资源利用率分析"""
    analyzer_info = AnalyzerRegistry.get_analyzer_info(resource_type)
    if not analyzer_info:
        print(f"❌ 不支持的资源类型: {resource_type}")
        return False

    display_name = analyzer_info["display_name"]
    emoji = analyzer_info["emoji"]
    analyzer_class = analyzer_info["class"]

    print(f"{emoji} 启动{display_name}分析...")

    try:
        # 实例化分析器
        analyzer = analyzer_class(
            tenant_config.get("access_key_id"), tenant_config.get("access_key_secret"), tenant_name
        )

        # 执行分析
        idle_resources = analyzer.analyze()

        # 生成报告 (假设所有分析器都实现了generate_report，或者我们需要统一报告生成)
        # 这里暂时假设分析器有generate_report方法，或者我们需要在BaseResourceAnalyzer中统一
        if hasattr(analyzer, "generate_report"):
            analyzer.generate_report(idle_resources)
        elif hasattr(analyzer, f"generate_{resource_type}_report"):
            getattr(analyzer, f"generate_{resource_type}_report")(idle_resources)
        else:
            # 尝试使用通用的报告生成逻辑（如果有）
            pass

        return True
    except Exception as e:
        print(f"❌ {display_name}分析失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_all_cru_analysis(tenant_name: str, tenant_config: Dict[str, Any]) -> bool:
    """运行所有已注册资源的分析"""
    print("🌍 启动全资源利用率分析...")

    analyzers = AnalyzerRegistry.list_analyzers()
    results = {}

    for resource_type, info in analyzers.items():
        print(f"\n{'='*50}")
        success = run_cru_analysis(tenant_name, tenant_config, resource_type)
        results[info["display_name"]] = "✅ 成功" if success else "❌ 失败"

    # 显示分析结果汇总
    print(f"\n{'='*50}")
    print("📊 全资源利用率分析结果汇总:")
    for name, result in results.items():
        print(f"  {name}: {result}")

    return True


def run_discount_analysis(args, tenant_name, tenant_config, resource_type="all"):
    """运行折扣分析（保持原有逻辑，后续也可重构）"""
    print("💰 启动折扣分析...")
    try:
        from resource_modules.discount_analyzer import DiscountAnalyzer

        analyzer = DiscountAnalyzer(
            tenant_name, tenant_config["access_key_id"], tenant_config["access_key_secret"]
        )

        if resource_type == "all" or resource_type == "all-products":
            analyzer.analyze_all_products_discounts(output_base_dir=".")
        elif hasattr(analyzer, f"analyze_{resource_type}_discounts"):
            getattr(analyzer, f"analyze_{resource_type}_discounts")(output_base_dir=".")
        else:
            print(f"❌ 不支持的折扣分析类型: {resource_type}")
            return False
        return True
    except Exception as e:
        print(f"❌ 折扣分析失败: {e}")
        return False


def run_cost_analysis(tenant_name, tenant_config):
    """运行费用分析"""
    print("💰 启动费用分布分析...")
    try:
        from resource_modules.cost_analyzer import CostAnalyzer

        analyzer = CostAnalyzer(
            tenant_name, tenant_config["access_key_id"], tenant_config["access_key_secret"]
        )
        analyzer.generate_cost_report()
        return True
    except ImportError:
        print("❌ 费用分析模块未找到")
        return False
    except Exception as e:
        print(f"❌ 费用分析失败: {e}")
        return False


def run_network_analysis(tenant_name, tenant_config):
    """运行网络资源分析"""
    print("🌐 启动网络资源分析...")
    try:
        from resource_modules.network_analyzer import NetworkAnalyzer

        analyzer = NetworkAnalyzer(
            tenant_config.get("access_key_id"),
            tenant_config.get("access_key_secret"),
            tenant_name or "default",
        )
        analyzer.analyze_network_resources()
        return True
    except Exception as e:
        print(f"❌ 网络资源分析失败: {e}")
        return False


def run_cost_prediction(tenant_name, tenant_config):
    """运行成本预测(P1)"""
    print("🔮 启动成本预测分析...")
    try:
        from utils.cost_predictor import CostPredictor

        predictor = CostPredictor()
        
        # 1. 收集历史数据
        print("📊 收集历史成本数据...")
        predictor.collect_historical_cost(
            tenant_name,
            tenant_config["access_key_id"],
            tenant_config["access_key_secret"],
            days=90
        )
        
        # 2. 线性回归预测
        print("🔮 生成预测(线性回归)...")
        linear_predictions = predictor.predict_cost_linear(tenant_name, future_days=30)
        
        # 3. 移动平均预测
        print("📈 生成预测(移动平均)...")
        ma_predictions = predictor.predict_cost_moving_average(tenant_name, future_days=30)
        
        # 4. 生成预测报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"cost_prediction_{tenant_name}_{timestamp}.xlsx"
        predictor.generate_prediction_report(tenant_name, output_file)
        
        print(f"✅ 成本预测完成")
        print(f"📄 报告: {output_file}")
        return True
    except Exception as e:
        print(f"❌ 成本预测失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_optimization(tenant_name, tenant_config):
    """运行优化建议分析(P1)"""
    print("⚡ 启动优化建议分析...")
    try:
        from core.optimization_engine import OptimizationEngine

        engine = OptimizationEngine()
        
        # 1. 分析优化机会
        print("📊 分析优化机会...")
        opportunities = engine.analyze_optimization_opportunities(tenant_name)
        
        if not opportunities:
            print("✨ 未发现优化机会,资源使用良好!")
            return True
        
        # 2. 计算ROI
        roi = engine.calculate_roi(opportunities)
        
        print(f"\n💰 优化收益统计:")
        print(f"  总机会数: {roi['total_opportunities']}")
        print(f"  月度节省: ¥{roi['monthly_savings']:.2f}")
        print(f"  年度节省: ¥{roi['yearly_savings']:.2f}")
        
        # 3. 生成CLI脚本
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_file = f"optimization_scripts_{tenant_name}_{timestamp}.sh"
        engine.generate_aliyun_cli_scripts(opportunities, script_file)
        
        # 4. 生成优化报告
        report_file = f"optimization_report_{tenant_name}_{timestamp}.xlsx"
        engine.generate_optimization_report(tenant_name, opportunities, report_file)
        
        print(f"\n✅ 优化分析完成")
        print(f"📄 报告: {report_file}")
        print(f"📜 脚本: {script_file}")
        print(f"⚠️  警告: 执行脚本前请仔细检查!")
        return True
    except Exception as e:
        print(f"❌ 优化分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 初始化日志
    from utils.logger import setup_logger
    setup_logger(log_file="logs/aliyunidle.log")

    # 加载所有资源模块
    load_resource_modules()

    args_list = sys.argv[1:]

    if "--help" in args_list or "-h" in args_list or len(args_list) == 0:
        show_help()
        return

    if "--version" in args_list or "-v" in args_list:
        print("阿里云资源分析工具 v2.3.0")
        return

    # 处理凭证管理命令
    if args_list[0] == "setup-credentials":
        try:
            from utils.credential_manager import setup_credentials_interactive

            setup_credentials_interactive()
        except ImportError:
            print("❌ 凭证管理功能需要安装keyring库")
        return

    if args_list[0] == "list-credentials":
        try:
            from utils.credential_manager import CredentialManager

            config = load_config()
            tenants = config.get("tenants", {})
            print("📋 已配置的租户:")
            for tenant, tenant_config in tenants.items():
                use_keyring = tenant_config.get("use_keyring", False)
                status = "🔐 Keyring" if use_keyring else "📄 配置文件"
                print(f"  - {tenant}: {status}")
        except Exception as e:
            print(f"❌ 列出凭证失败: {e}")
        return

    if args_list[0] == "migrate-credentials":
        try:
            from utils.credential_manager import CredentialManager

            config = load_config()
            tenants = config.get("tenants", {})
            migrated_count = 0

            print("🔐 开始迁移凭证到Keyring...")

            for tenant_name, tenant_config in tenants.items():
                if tenant_config.get("use_keyring"):
                    print(f"  - {tenant_name}: 已经是Keyring模式，跳过")
                    continue

                ak = tenant_config.get("access_key_id")
                sk = tenant_config.get("access_key_secret")

                if ak and sk:
                    print(f"  - {tenant_name}: 发现明文凭证，正在迁移...")
                    credentials = {"access_key_id": ak, "access_key_secret": sk}
                    # 保存到Keyring
                    CredentialManager.save_credentials("aliyun", tenant_name, credentials)

                    # 更新配置
                    tenant_config["use_keyring"] = True
                    tenant_config["keyring_key"] = f"aliyun_{tenant_name}"
                    # 删除明文凭证
                    del tenant_config["access_key_id"]
                    del tenant_config["access_key_secret"]

                    migrated_count += 1
                else:
                    print(f"  - {tenant_name}: 未找到完整凭证，跳过")

            if migrated_count > 0:
                # 保存更新后的配置
                with open("config.json", "w") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                print(f"✅ 成功迁移 {migrated_count} 个租户的凭证到Keyring")
                print("⚠️  注意: config.json已被更新，明文凭证已移除")
            else:
                print("✨ 没有需要迁移的凭证")

        except ImportError:
            print("❌ 迁移失败: 需要安装keyring库")
        except Exception as e:
            print(f"❌ 迁移失败: {e}")
        return

    # 加载配置
    config = load_config()
    default_tenant = config.get("default_tenant")

    # 解析参数
    if len(args_list) == 1:
        # python main.py cru
        action = args_list[0]
        tenant_name = default_tenant
        resource_type = "all"
    elif len(args_list) == 2:
        if args_list[0] in config.get("tenants", {}):
            tenant_name = args_list[0]
            action = args_list[1]
            resource_type = "all"
        else:
            action = args_list[0]
            tenant_name = default_tenant
            resource_type = args_list[1]
    elif len(args_list) == 3:
        tenant_name = args_list[0]
        action = args_list[1]
        resource_type = args_list[2]
    else:
        print("❌ 参数错误")
        show_help()
        return

    tenant_config = get_tenant_config(config, tenant_name)

    # 检查凭证安全性
    if not tenant_config.get("use_keyring") and tenant_config.get("access_key_id"):
        print("⚠️  警告: 检测到明文凭证存储在config.json中")
        print("   建议运行 'python main.py migrate-credentials' 将凭证迁移到系统安全存储")

    # 尝试从Keyring获取凭证
    try:
        from utils.credential_manager import get_credentials_from_config_or_keyring

        cloud_credentials = get_credentials_from_config_or_keyring("aliyun", tenant_name, config)
        if cloud_credentials:
            tenant_config.update(cloud_credentials)
    except ImportError:
        pass
    except Exception as e:
        print(f"⚠️  从Keyring获取凭证失败: {e}")

    tenant_display_name = tenant_config.get("display_name", tenant_name)

    print("🚀 阿里云资源分析工具 v2.3.0")
    print("=" * 80)
    print(f"🏢 租户: {tenant_name} ({tenant_config.get('tenant_id', '')})")
    print(f"🎯 操作: {action.upper()}")
    if action in ["cru", "discount"]:
        print(f"📦 资源: {resource_type.upper()}")
    print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    success = False

    if action == "cru":
        if resource_type == "all":
            success = run_all_cru_analysis(tenant_name, tenant_config)
        # The original code had a special handling for network here, but the instruction removes it.
        # Keeping faithful to the instruction, the `elif resource_type == "network"` block is removed.
        else:
            success = run_cru_analysis(tenant_name, tenant_config, resource_type)

    elif action == "discount":
        # The instruction changes the first argument from `None` to `args`.
        # Assuming `args` refers to `args_list` or a parsed version of it.
        # To maintain syntactic correctness, `args_list` is used here as `args` is not defined.
        success = run_discount_analysis(args_list, tenant_name, tenant_config, resource_type)
    elif action == "cost":
        success = run_cost_analysis(tenant_name, tenant_config)
    elif action == "network":
        success = run_network_analysis(tenant_name, tenant_config)
    elif action == "predict":  # P1: 成本预测
        success = run_cost_prediction(tenant_name, tenant_config)
    elif action == "optimize":  # P1: 优化建议
        success = run_optimization(tenant_name, tenant_config)
    else:
        print(f"❌ 不支持的操作类型: {action}")
        show_help()
        return

    print("\n" + "=" * 80)
    if success:
        print("🎉 分析完成！")
    else:
        print("❌ 分析失败！")
    print(f"📅 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
