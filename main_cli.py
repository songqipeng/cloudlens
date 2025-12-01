import click
import sys
import os

# 添加当前目录到 path 以便导入模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import List, Optional
from core.config import ConfigManager, CloudAccount
from core.context import ContextManager

@click.group()
@click.pass_context
def cli(ctx):
    """CloudLens CLI - 多云资源治理工具
    
    \b
    🌐 统一视图 · 💰 智能分析 · 🔒 安全合规 · 📊 降本增效
    
    CloudLens 是一款企业级多云资源治理与分析工具，专为运维团队打造。
    通过统一的命令行界面管理阿里云、腾讯云等多个云平台的资源。
    
    \b
    核心功能：
      • 多云统一管理 - 一个工具管理所有云资源
      • 智能成本分析 - 自动识别闲置资源，提供优化建议
      • 安全合规检查 - 公网暴露检测、权限审计、标签治理
      • 专业报告生成 - Excel、HTML、JSON/CSV多格式导出
      • 高性能查询 - 并发查询，速度提升3倍
    
    \b
    快速开始：
      cl config add              # 添加云账号
      cl query ydzn ecs          # 查询ECS实例
      cl analyze idle            # 分析闲置资源
      cl report generate         # 生成报告
    
    \b
    使用 'cl COMMAND --help' 查看具体命令的帮助信息
    """
    # 如果没有子命令，显示帮助信息
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@cli.group()
def config():
    """配置管理 - 添加、删除、查看云账号配置"""
    pass

@config.command("list")
def list_accounts():
    """查看所有已配置的云账号"""
    cm = ConfigManager()
    accounts = cm.list_accounts()
    if not accounts:
        click.echo("暂无配置账号。")
        return
        
    click.echo(f"{'Name':<15} {'Provider':<10} {'Region':<15} {'Keyring':<10}")
    click.echo("-" * 50)
    for acc in accounts:
        click.echo(f"{acc.name:<15} {acc.provider:<10} {acc.region:<15} {str(acc.use_keyring):<10}")

@config.command("add")
@click.option("--provider", prompt=True, type=click.Choice(['aliyun', 'tencent', 'aws', 'volcano']))
@click.option("--name", prompt=True, help="账号别名")
@click.option("--region", prompt=True, default="cn-hangzhou")
@click.option("--ak", prompt=True, help="Access Key ID")
@click.option("--sk", prompt=True, hide_input=True, help="Secret Access Key")
def add_account(provider, name, region, ak, sk):
    """添加新的云账号配置"""
    cm = ConfigManager()
    
    # TODO: 在这里调用 PermissionGuard 进行权限预检
    
    # 使用 ConfigManager 添加账号（自动处理 keyring）
    cm = ConfigManager()
    cm.add_account(
        name=name,
        provider=provider,
        access_key_id=ak,
        access_key_secret=sk,
        region=region
    )
    click.echo(f"✅ 账号 '{name}' 添加成功（密钥已保存到 Keyring）。")

@cli.group()
def query():
    """资源查询 - 查询ECS、RDS、VPC等云资源"""
    pass

from providers.aliyun.provider import AliyunProvider
from providers.tencent.provider import TencentProvider

def get_provider(account_config: CloudAccount):
    if account_config.provider == "aliyun":
        return AliyunProvider(
            account_config.name,
            account_config.access_key_id,
            account_config.access_key_secret,
            account_config.region
        )
    elif account_config.provider == "tencent":
        return TencentProvider(
            account_config.name,
            account_config.access_key_id,
            account_config.access_key_secret,
            account_config.region
        )
    # TODO: Add AWS and Volcano providers
    return None

def smart_resolve_account(cm: ConfigManager, ctx_mgr: ContextManager, account_name: Optional[str] = None) -> Optional[str]:
    """
    智能解析账号名称：
    1. 如果指定了account_name，使用它并记住
    2. 如果没指定，使用上次记住的账号
    3. 如果都没有，提示用户选择
    
    Returns:
        str: 账号名称，如果用户取消则返回None
    """
    # 如果明确指定了账号，使用它
    if account_name:
        # 验证账号是否存在
        acc = cm.get_account(account_name)
        if not acc:
            click.echo(f"❌ Account '{account_name}' not found.")
            return None
        # 记住这个账号
        ctx_mgr.set_last_account(account_name)
        click.echo(f"📌 Using account: {account_name}")
        return account_name
    
    # 尝试使用上次记住的账号
    last_account = ctx_mgr.get_last_account()
    if last_account:
        acc = cm.get_account(last_account)
        if acc:
            click.echo(f"📌 Using remembered account: {last_account}")
            return last_account
    
    # 没有记住的账号，提示用户选择
    accounts = cm.list_accounts()
    if not accounts:
        click.echo("❌ No accounts configured. Please run 'cloudlens config add' first.")
        return None
    
    click.echo("\n📋 Available accounts:")
    for i, acc in enumerate(accounts, 1):
        click.echo(f"  {i}. {acc.name} ({acc.provider}, {acc.region})")
    
    choice = click.prompt("\nSelect account", type=int, default=1)
    
    if 1 <= choice <= len(accounts):
        selected = accounts[choice - 1].name
        ctx_mgr.set_last_account(selected)
        click.echo(f"✅ Selected: {selected}")
        return selected
    else:
        click.echo("❌ Invalid choice")
        return None

def resolve_account_name(cm: ConfigManager, account_name: str) -> List[CloudAccount]:
    """
    解析账号名称，处理重名情况
    
    Returns:
        List[CloudAccount]: 匹配的账号列表
    """
    if not account_name:
        return cm.list_accounts()
    
    # 查找所有匹配该名称的账号
    matching_accounts = [acc for acc in cm.list_accounts() if acc.name == account_name]
    
    if len(matching_accounts) == 0:
        click.echo(f"❌ Account '{account_name}' not found.")
        return []
    elif len(matching_accounts) == 1:
        return matching_accounts
    else:
        # 有多个重名账号，给出选择
        click.echo(f"⚠️  Found {len(matching_accounts)} accounts named '{account_name}':")
        for i, acc in enumerate(matching_accounts, 1):
            click.echo(f"  {i}. {acc.provider} ({acc.region})")
        
        click.echo(f"  0. All (查询所有同名账号)")
        
        choice = click.prompt("Please select", type=int, default=0)
        
        if choice == 0:
            return matching_accounts
        elif 1 <= choice <= len(matching_accounts):
            return [matching_accounts[choice - 1]]
        else:
            click.echo("❌ Invalid choice")
            return []

def export_to_json(data: List, output_file: str = None):
    """导出为JSON格式"""
    import json
    json_data = []
    for item in data:
        if hasattr(item, '__dict__'):
            # 处理UnifiedResource对象
            item_dict = {
                'id': item.id,
                'name': item.name,
                'provider': item.provider,
                'region': item.region,
                'status': item.status.value if hasattr(item.status, 'value') else str(item.status),
                'resource_type': item.resource_type.value if hasattr(item.resource_type, 'value') else str(item.resource_type),
            }
            if hasattr(item, 'public_ips'):
                item_dict['public_ips'] = item.public_ips
            if hasattr(item, 'spec'):
                item_dict['spec'] = item.spec
            json_data.append(item_dict)
        else:
            json_data.append(item)
    
    json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_str)
        click.echo(f"✅ Exported to {output_file}")
    else:
        click.echo(json_str)

def export_to_csv(data: List, output_file: str = None):
    """导出为CSV格式"""
    import csv
    import io
    
    if not data:
        click.echo("No data to export")
        return
    
    output = io.StringIO()
    
    # 确定字段
    if hasattr(data[0], '__dict__'):
        fieldnames = ['id', 'name', 'provider', 'region', 'status', 'resource_type', 'spec', 'public_ip']
    else:
        fieldnames = list(data[0].keys()) if isinstance(data[0], dict) else ['value']
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for item in data:
        if hasattr(item, '__dict__'):
            row = {
                'id': item.id,
                'name': item.name,
                'provider': item.provider,
                'region': item.region,
                'status': item.status.value if hasattr(item.status, 'value') else str(item.status),
                'resource_type': item.resource_type.value if hasattr(item.resource_type, 'value') else str(item.resource_type),
                'spec': getattr(item, 'spec', ''),
                'public_ip': item.public_ips[0] if hasattr(item, 'public_ips') and item.public_ips else ''
            }
        else:
            row = item if isinstance(item, dict) else {'value': str(item)}
        writer.writerow(row)
    
    csv_str = output.getvalue()
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(csv_str)
        click.echo(f"✅ Exported to {output_file}")
    else:
        click.echo(csv_str)


@query.command("ecs")
@click.argument('account', required=False)
@click.option("--format", type=click.Choice(['table', 'json', 'csv']), default='table', help="Output format")
@click.option("--output", help="Output file path")
@click.option("--status", help="Filter by status (Running, Stopped, etc)")
@click.option("--region", help="Filter by region")
@click.option("--filter", 'filter_expr', help="Advanced filter expression (e.g. 'charge_type=PrePaid AND expire_days<7')")
@click.option("--concurrent", is_flag=True, help="Enable concurrent querying for multiple accounts")
@click.option("--analysis", "-a", help="Advanced analysis query (e.g. 'groupby:region|count')")
@click.option("--jmespath", "-j", help="JMESPath query expression (e.g. '[?Status==`Running`].{ID:InstanceId,Name:InstanceName}')")
def query_ecs(account, format, output, status, region, filter_expr, concurrent, analysis, jmespath):
    """List ECS/EC2 instances
    
    Usage:
        cloudlens query ecs              # Use remembered account or prompt
        cloudlens query ydzn ecs         # Use specific account
    """
    from core.filter_engine import FilterEngine
    
    cm = ConfigManager()
    ctx_mgr = ContextManager()
    
    # 智能解析账号
    account_name = smart_resolve_account(cm, ctx_mgr, account)
    if not account_name:
        return
    
    accounts = resolve_account_name(cm, account_name)
    
    if not accounts:
        return

    all_resources = []
    
    if concurrent and len(accounts) > 1:
        # 并发查询
        from core.concurrent_helper import ConcurrentQueryHelper
        
        def query_single_account(acc):
            provider = get_provider(acc)
            if not provider:
                return []
            try:
                return provider.list_instances()
            except Exception as e:
                click.echo(f"❌ Failed to query {acc.name} ({acc.provider}): {e}")
                return []
        
        click.echo(f"🚀 Concurrent querying {len(accounts)} accounts...")
        all_resources = ConcurrentQueryHelper.query_with_progress(
            accounts,
            query_single_account,
            lambda c, t: click.echo(f"Progress: {c}/{t}", err=True) if c % 5 == 0 else None
        )
    else:
        # 串行查询
        for acc in accounts:
            provider = get_provider(acc)
            if not provider:
                continue
                
            try:
                resources = provider.list_instances()
                all_resources.extend(resources)
            except Exception as e:
                click.echo(f"❌ Failed to query {acc.name} ({acc.provider}): {e}")
    
    # Apply basic filters
    if status:
        all_resources = [r for r in all_resources if r.status.value.lower() == status.lower()]
    if region:
        all_resources = [r for r in all_resources if r.region == region]
    
    # Apply advanced filter
    if filter_expr:
        all_resources = FilterEngine.apply_filter(all_resources, filter_expr)

    # JMESPath Query
    if jmespath:
        import jmespath as jp
        # Convert UnifiedResource objects to dicts
        data_list = [r.__dict__ for r in all_resources]
        try:
            result = jp.search(jmespath, data_list)
            import json
            click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return
        except Exception as e:
            click.echo(f"❌ JMESPath query failed: {e}", err=True)
            return

    # Advanced Analysis
    if analysis:
        from core.data_engine import DataEngine
        # Convert UnifiedResource objects to dicts for pandas
        data_list = [r.__dict__ for r in all_resources]
        click.echo(f"📊 Analyzing {len(all_resources)} resources with query: {analysis}")
        result = DataEngine.analyze(data_list, analysis)
        click.echo(result)
        return
    
    if format == 'json':
        export_to_json(all_resources, output)
    elif format == 'csv':
        export_to_csv(all_resources, output)
    else:
        # Table format using tabulate
        from tabulate import tabulate
        
        if not all_resources:
            click.echo("No resources found.")
            return
        
        # 准备表格数据
        table_data = []
        for r in all_resources:
            ip = r.public_ips[0] if r.public_ips else (r.private_ips[0] if r.private_ips else "-")
            table_data.append([
                r.id,
                r.name[:35],  # 限制长度
                ip,
                r.status.value,
                r.region,
                r.provider
            ])
        
        headers = ["ID", "Name", "IP", "Status", "Region", "Provider"]
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
        click.echo(f"\n✅ Total: {len(all_resources)} instances")


@query.command("rds")
@click.option("--account", help="Specific account to query")
def query_rds(account):
    """List RDS instances"""
    cm = ConfigManager()
    accounts = []
    if account:
        acc = cm.get_account(account)
        if acc: accounts.append(acc)
    else:
        accounts = cm.list_accounts()
        
    click.echo(f"{'ID':<20} {'Name':<30} {'Engine':<10} {'Status':<10} {'Region':<12}")
    click.echo("-" * 90)
    
    for acc in accounts:
        provider = get_provider(acc)
        if not provider: continue
        try:
            resources = provider.list_rds()
            for r in resources:
                engine = r.raw_data.get("Engine", "-")
                click.echo(f"{r.id:<20} {r.name[:28]:<30} {engine:<10} {r.status.value:<10} {r.region:<12}")
        except Exception as e:
            click.echo(f"❌ Error: {e}")

@query.command("vpc")
@click.option("--account", help="Specific account to query")
def query_vpc(account):
    """List VPCs"""
    cm = ConfigManager()
    accounts = []
    if account:
        acc = cm.get_account(account)
        if acc: accounts.append(acc)
    else:
        accounts = cm.list_accounts()
        
    click.echo(f"{'ID':<22} {'Name':<20} {'CIDR':<18} {'Region':<12} {'Status':<10}")
    click.echo("-" * 90)
    
    for acc in accounts:
        provider = get_provider(acc)
        if not provider: continue
        try:
            vpcs = provider.list_vpcs()
            for v in vpcs:
                click.echo(f"{v['id']:<22} {v['name'][:18]:<20} {v['cidr']:<18} {v['region']:<12} {v['status']:<10}")
        except Exception as e:
            click.echo(f"❌ Error: {e}")

@query.command("redis")
@click.option("--account", help="Specific account to query")
def query_redis(account):
    """List Redis instances"""
    cm = ConfigManager()
    accounts = []
    if account:
        acc = cm.get_account(account)
        if acc: accounts.append(acc)
    else:
        accounts = cm.list_accounts()
        
    click.echo(f"{'ID':<22} {'Name':<25} {'Status':<10} {'Region':<12} {'Spec':<15}")
    click.echo("-" * 90)
    
    for acc in accounts:
        provider = get_provider(acc)
        if not provider: continue
        try:
            resources = provider.list_redis()
            for r in resources:
                click.echo(f"{r.id:<22} {r.name[:23]:<25} {r.status.value:<10} {r.region:<12} {r.spec or '-':<15}")
        except Exception as e:
            click.echo(f"❌ Error: {e}")

@query.command("oss")
@click.option("--account", help="Specific account to query")
def query_oss(account):
    """List OSS buckets"""
    cm = ConfigManager()
    accounts = []
    if account:
        acc = cm.get_account(account)
        if acc: accounts.append(acc)
    else:
        accounts = cm.list_accounts()
        
    click.echo(f"{'Bucket Name':<30} {'Region':<15} {'Storage Class':<15} {'Created':<20}")
    click.echo("-" * 90)
    
    for acc in accounts:
        provider = get_provider(acc)
        if not provider: continue
        try:
            buckets = provider.list_oss()
            for b in buckets:
                click.echo(f"{b['name']:<30} {b['region']:<15} {b.get('storage_class', '-'):<15} {b.get('created_time', '-'):<20}")
        except Exception as e:
            click.echo(f"❌ Error: {e}")

@query.command("eip")
@click.option("--account", help="Specific account to query")
def query_eip(account):
    """List Elastic IPs"""
    cm = ConfigManager()
    accounts = resolve_account_name(cm, account)
    
    if not accounts:
        return

    click.echo(f"{'ID':<25} {'IP Address':<16} {'Status':<12} {'Instance':<22} {'Region':<12}")
    click.echo("-" * 95)

    for acc in accounts:
        provider = get_provider(acc)
        if not provider:
            continue
            
        try:
            eips = provider.list_eip()
            for eip in eips:
                click.echo(f"{eip['id']:<25} {eip['ip_address']:<16} {eip['status']:<12} {eip.get('instance_id', '-'):<22} {eip['region']:<12}")
        except Exception as e:
            click.echo(f"❌ Failed to query {acc.name}: {e}")

@query.command("slb")
@click.option("--account", help="Specific account to query")
@click.option("--format", type=click.Choice(['table', 'json', 'csv']), default='table', help="Output format")
@click.option("--output", help="Output file path")
def query_slb(account, format, output):
    """List SLB Load Balancers"""
    cm = ConfigManager()
    accounts = resolve_account_name(cm, account)
    
    if not accounts:
        return

    all_slbs = []
    for acc in accounts:
        provider = get_provider(acc)
        if not provider:
            continue
            
        try:
            slbs = provider.list_slb()
            all_slbs.extend(slbs)
        except Exception as e:
            click.echo(f"❌ Failed to query {acc.name}: {e}")
    
    if format == 'json':
        import json
        json_str = json.dumps(all_slbs, indent=2, ensure_ascii=False)
        if output:
            with open(output, 'w') as f:
                f.write(json_str)
            click.echo(f"✅ Exported to {output}")
        else:
            click.echo(json_str)
    elif format == 'csv':
        import csv
        if output:
            with open(output, 'w') as f:
                writer = csv.DictWriter(f, fieldnames=['id', 'name', 'address', 'status', 'region'])
                writer.writeheader()
                writer.writerows(all_slbs)
            click.echo(f"✅ Exported to {output}")
    else:
        click.echo(f"{'ID':<25} {'Name':<30} {'Address':<16} {'Type':<12} {'Status':<12} {'Region':<12}")
        click.echo("-" * 115)
        for slb in all_slbs:
            click.echo(f"{slb['id']:<25} {slb.get('name', '')[:28]:<30} {slb.get('address', ''):<16} {slb.get('address_type', ''):<12} {slb.get('status', ''):<12} {slb['region']:<12}")

@query.command("nas")
@click.option("--account", help="Specific account to query")
@click.option("--format", type=click.Choice(['table', 'json', 'csv']), default='table', help="Output format")
@click.option("--output", help="Output file path")
def query_nas(account, format, output):
    """List NAS File Systems"""
    cm = ConfigManager()
    accounts = resolve_account_name(cm, account)
    
    if not accounts:
        return

    all_nas = []
    for acc in accounts:
        provider = get_provider(acc)
        if not provider:
            continue
            
        try:
            nas_list = provider.list_nas()
            all_nas.extend(nas_list)
        except Exception as e:
            click.echo(f"❌ Failed to query {acc.name}: {e}")
    
    if format == 'json':
        import json
        json_str = json.dumps(all_nas, indent=2, ensure_ascii=False)
        if output:
            with open(output, 'w') as f:
                f.write(json_str)
            click.echo(f"✅ Exported to {output}")
        else:
            click.echo(json_str)
    elif format == 'csv':
        import csv
        if output:
            with open(output, 'w') as f:
                writer = csv.DictWriter(f, fieldnames=['id', 'protocol_type', 'storage_type', 'status', 'region'])
                writer.writeheader()
                writer.writerows(all_nas)
            click.echo(f"✅ Exported to {output}")
    else:
        click.echo(f"{'ID':<25} {'Protocol':<12} {'Storage Type':<15} {'Status':<12} {'Size(GB)':<12} {'Region':<12}")
        click.echo("-" * 95)
        for nas in all_nas:
            size_gb = nas.get('metered_size', 0) / (1024**3) if nas.get('metered_size') else 0
            click.echo(f"{nas['id']:<25} {nas.get('protocol_type', ''):<12} {nas.get('storage_type', ''):<15} {nas.get('status', ''):<12} {size_gb:<12.2f} {nas['region']:<12}")

@cli.group()
def analyze():
    """资源分析 - 闲置资源、成本、安全、续费分析"""
    pass

@analyze.command("renewal")
@click.option("--days", default=30, help="Days threshold for expiration warning")
@click.option("--account", help="Specific account to analyze")
def analyze_renewal(days, account):
    """Check for expiring resources"""
    from datetime import datetime, timedelta
    
    cm = ConfigManager()
    accounts = []
    if account:
        acc = cm.get_account(account)
        if acc: accounts.append(acc)
    else:
        accounts = cm.list_accounts()
        
    now = datetime.now()
    threshold = now + timedelta(days=days)
    
    click.echo(f"🔍 Checking for resources expiring before {threshold.strftime('%Y-%m-%d')}...")
    click.echo(f"{'Account':<15} {'ID':<22} {'Name':<25} {'Type':<8} {'Expire Date':<12} {'Days Left':<10}")
    click.echo("-" * 100)
    
    for acc in accounts:
        provider = get_provider(acc)
        if not provider: continue
        
        try:
            # Check ECS
            resources = provider.list_instances() + provider.list_rds()
            for r in resources:
                if r.expired_time:
                    days_left = (r.expired_time - now).days
                    if days_left <= days:
                        click.echo(f"{acc.name:<15} {r.id:<22} {r.name[:23]:<25} {r.resource_type.value:<8} {r.expired_time.strftime('%Y-%m-%d'):<12} {days_left:<10}")
        except Exception as e:
            click.echo(f"❌ Error analyzing {acc.name}: {e}")

@analyze.command("idle")
@click.option("--days", default=14, help="Days of monitoring data to analyze")
@click.option("--account", help="Specific account to analyze")
def analyze_idle(days, account):
    """Detect idle resources based on monitoring metrics"""
    from datetime import datetime
    from core.idle_detector import IdleDetector
    from tabulate import tabulate
    
    cm = ConfigManager()
    accounts = []
    if account:
        acc = cm.get_account(account)
        if acc: accounts.append(acc)
    else:
        accounts = cm.list_accounts()
    
    click.echo(f"🔍 Analyzing idle resources (based on {days} days average metrics)...\n")
    
    total_idle = 0
    table_data = []
    
    for acc in accounts:
        provider = get_provider(acc)
        # 当前仅支持阿里云 ECS 的闲置判定
        if not provider or provider.provider_name != "aliyun":
            continue
        
        try:
            # Only analyze ECS for now
            instances = provider.list_instances()
            click.echo(f"📦 Analyzing {len(instances)} instances in '{acc.name}'...")
            
            for idx, inst in enumerate(instances, 1):
                # Show progress
                if idx % 10 == 0 or idx == len(instances):
                    click.echo(f"   Progress: {idx}/{len(instances)}", err=True)
                
                # Fetch metrics
                metrics = IdleDetector.fetch_ecs_metrics(provider, inst.id, days)
                
                # Check if idle
                is_idle, reasons = IdleDetector.is_ecs_idle(metrics)
                
                if is_idle:
                    total_idle += 1
                    reason_str = "; ".join(reasons[:3])  # Show up to 3 reasons
                    
                    table_data.append([
                        acc.name,
                        inst.id,
                        inst.name[:30],
                        inst.status.value,
                        reason_str
                    ])
        except Exception as e:
            click.echo(f"❌ Error analyzing {acc.name}: {e}")
    
    click.echo("")  # Newline
    
    if table_data:
        headers = ["Account", "Instance ID", "Name", "Status", "Idle Reasons"]
        click.echo(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))
    else:
        click.echo("✅ No idle resources found!")
    
    click.echo(f"\n📊 Summary:")
    click.echo(f"  • Total idle resources: {total_idle}")
    click.echo(f"  • Thresholds: CPU < 5%, Memory < 20%, Network traffic < 1KB/s")
    click.echo(f"  • Analysis period: {days} days average")

@analyze.command("cru")
@click.option("--account", required=True, help="Account to analyze (Aliyun)")
@click.option("--days", default=14, help="Days of monitoring data to analyze")
def analyze_cru(account, days):
    """Compute Resource Utilization (插件化分析器入口，目前覆盖阿里云 ECS)"""
    from core.analyzer_registry import AnalyzerRegistry
    import resource_modules.ecs_analyzer  # 注册 ECS 分析器

    cm = ConfigManager()
    acc = cm.get_account(account)
    if not acc:
        click.echo(f"❌ Account '{account}' not found.")
        return
    if acc.provider != "aliyun":
        click.echo("⚠️ 当前插件化分析器仅支持阿里云 ECS。")
        return

    analyzer_info = AnalyzerRegistry.get_analyzer_info("ecs")
    if not analyzer_info:
        click.echo("❌ 未找到 ECS 分析器。")
        return

    analyzer_cls = analyzer_info["class"]
    analyzer = analyzer_cls(acc.name, acc.access_key_id, acc.access_key_secret, acc.region)

    click.echo(f"🔍 Analyzer: {analyzer_info['emoji']} {analyzer_info['display_name']} - {acc.name}")
    idle_resources = analyzer.analyze(days=days)

    if not idle_resources:
        click.echo("✅ 未发现闲置 ECS。")
        return

    click.echo(f"\n⚠️ 检测到 {len(idle_resources)} 个闲置 ECS:")
    for item in idle_resources[:10]:
        inst = item["instance"]
        reasons = "; ".join(item["idle_conditions"])
        click.echo(f"- {inst.id} {inst.name} ({inst.region}) -> {reasons}")

@analyze.command("tags")
@click.option("--account", help="Specific account to analyze")
def analyze_tags(account):
    """Analyze tag coverage and compliance"""
    from core.tag_analyzer import TagAnalyzer
    
    cm = ConfigManager()
    accounts = resolve_account_name(cm, account)
    
    if not accounts:
        return
    
    click.echo("🔍 Analyzing resource tags...")
    
    all_resources = []
    for acc in accounts:
        provider = get_provider(acc)
        if not provider:
            continue
        
        try:
            resources = provider.list_instances() + provider.list_rds() + provider.list_redis()
            all_resources.extend(resources)
        except Exception as e:
            click.echo(f"❌ Error fetching resources from {acc.name}: {e}")
    
    if not all_resources:
        click.echo("No resources found.")
        return
    
    # Tag coverage analysis
    coverage = TagAnalyzer.analyze_tag_coverage(all_resources)
    
    click.echo(f"\n📊 标签覆盖率分析")
    click.echo(f"总资源数: {coverage['total']}")
    click.echo(f"已标签: {coverage['tagged']}")
    click.echo(f"未标签: {coverage['untagged']}")
    click.echo(f"覆盖率: {coverage['coverage_rate']}%")
    
    # Untagged resources
    if coverage['untagged_resources']:
        click.echo(f"\n⚠️  无标签资源 (前10个):")
        click.echo(f"{'ID':<22} {'Name':<30} {'Type':<10}")
        click.echo("-" * 70)
        for r in coverage['untagged_resources'][:10]:
            click.echo(f"{r.id:<22} {r.name[:28]:<30} {r.resource_type.value:<10}")
    
    # Tag keys analysis
    tag_keys = TagAnalyzer.analyze_tag_keys(all_resources)
    if tag_keys['most_common']:
        click.echo(f"\n📌 Top 10 标签键:")
        for key, count in tag_keys['most_common']:
            click.echo(f"  {key}: {count} 次使用")
    
    # Suggestions
    suggestions = TagAnalyzer.suggest_tag_optimization(all_resources)
    if suggestions:
        click.echo(f"\n💡 优化建议:")
        for sugg in suggestions:
            click.echo(f"  • {sugg}")

@analyze.command("security")
@click.option("--account", help="Specific account to analyze")
def analyze_security(account):
    """Analyze security compliance and risks"""
    from core.security_compliance import SecurityComplianceAnalyzer
    from tabulate import tabulate
    
    cm = ConfigManager()
    accounts = resolve_account_name(cm, account)
    
    if not accounts:
        return
    
    click.echo("🔍 Analyzing security compliance...\n")
    
    all_resources = []  # 收集所有资源类型
    all_eips = []
    
    for acc in accounts:
        provider = get_provider(acc)
        if not provider:
            continue
        
        try:
            # 收集所有资源类型
            instances = provider.list_instances()
            all_resources.extend(instances)
            
            # 尝试收集其他资源
            try:
                rds = provider.list_rds()
                all_resources.extend(rds)
            except:
                pass
            
            try:
                redis = provider.list_redis()
                all_resources.extend(redis)
            except:
                pass
            
            try:
                all_eips.extend(provider.list_eip())
            except:
                pass  # EIP 可能不可用，跳过
        except Exception as e:
            click.echo(f"❌ Error fetching resources from {acc.name}: {e}")
    
    # === 1. 公网暴露检测（所有资源类型）===
    exposed = SecurityComplianceAnalyzer.detect_public_exposure(all_resources)
    
    # 按资源类型分组统计
    exposed_by_type = {}
    for e in exposed:
        rtype = e['type']
        if rtype not in exposed_by_type:
            exposed_by_type[rtype] = []
        exposed_by_type[rtype].append(e)
    
    click.echo("🌐 【公网暴露分析】")
    click.echo(f"   Total resources: {len(all_resources)}, Exposed: {len(exposed)}")
    for rtype, items in exposed_by_type.items():
        click.echo(f"   • {rtype}: {len(items)} exposed")
    click.echo("")
    
    if exposed:
        table_data = [[e['id'], e['name'][:25], e['type'], ', '.join(e['public_ips'][:2]), e['risk_level']] for e in exposed[:15]]
        click.echo(tabulate(table_data, headers=["Instance ID", "Name", "Type", "Public IPs", "Risk"], tablefmt="simple"))
    
    # === 2. EIP 使用分析 ===
    if all_eips:
        eip_stats = SecurityComplianceAnalyzer.analyze_eip_usage(all_eips)
        click.echo(f"\n📍 【弹性公网IP统计】")
        click.echo(f"   Total: {eip_stats['total']}, Bound: {eip_stats['bound']}, Unbound: {eip_stats['unbound']} ({eip_stats['unbound_rate']}%)")
        if eip_stats['unbound_eips'][:3]:
            for eip in eip_stats['unbound_eips'][:3]:
                click.echo(f"   • {eip.get('ip_address', 'N/A')} (ID: {eip.get('id', 'N/A')})")
    
    # === 3. 停止实例检查 ===
    stopped = SecurityComplianceAnalyzer.check_stopped_instances(all_resources)
    click.echo(f"\n⏸️  【长期停止实例】")
    click.echo(f"   Count: {len(stopped)} (仍产生磁盘费用)\n")
    if stopped:
        stopped_data = [[s['id'], s['name'][:25], s['region'], s['created_time']] for s in stopped[:10]]
        click.echo(tabulate(stopped_data, headers=["Instance ID", "Name", "Region", "Created"], tablefmt="simple"))
    
    # === 4. 标签覆盖率（显示未打标签的实例）===
    tag_coverage, no_tags = SecurityComplianceAnalyzer.check_missing_tags(all_resources)
    click.echo(f"\n🏷️  【资源标签治理】")
    click.echo(f"   Tag coverage: {tag_coverage}%, Missing tags: {len(no_tags)}\n")
    if no_tags[:10]:
        tag_data = [[n['id'], n['name'][:25], n['type'], n['region']] for n in no_tags[:10]]
        click.echo(tabulate(tag_data, headers=["Instance ID", "Name", "Type", "Region"], tablefmt="simple"))
        if len(no_tags) > 10:
            click.echo(f"   ... and {len(no_tags) - 10} more")
    
    # === 5. 磁盘加密检查 ===
    encryption = SecurityComplianceAnalyzer.check_disk_encryption(all_resources)
    click.echo(f"\n🔒 【磁盘加密状态】")
    click.echo(f"   Encryption rate: {encryption['encryption_rate']}% ({encryption['encrypted']}/{encryption['total']})")
    
    # === 6. 抢占式实例检查 ===
    preemptible = SecurityComplianceAnalyzer.check_preemptible_instances(all_resources)
    if preemptible:
        click.echo(f"\n⚡ 【抢占式实例】")
        click.echo(f"   Count: {len(preemptible)} (生产环境不建议)")
    
    # === 综合建议 ===
    security_summary = {
        'exposed_count': len(exposed),
        'unbound_eip': len(all_eips) - sum(1 for e in all_eips if e.get('instance_id')) if all_eips else 0,
        'stopped_count': len(stopped),
        'tag_coverage_rate': tag_coverage,
        'encryption_rate': encryption['encryption_rate'],
        'preemptible_count': len(preemptible)
    }
    
    suggestions = SecurityComplianceAnalyzer.suggest_security_improvements(security_summary)
    
    click.echo(f"\n💡 【安全建议】")
    for sugg in suggestions:
        click.echo(f"   {sugg}")


@cli.group()
def audit():
    """安全审计 - 账号权限审计和安全检查"""
    pass

@audit.command("permissions")
@click.option("--account", required=True, help="Account to audit")
def audit_permissions(account):
    """Audit account permissions and detect high-risk access"""
    cm = ConfigManager()
    accounts = resolve_account_name(cm, account)
    
    if not accounts or len(accounts) == 0:
        return
    
    acc = accounts[0]
    provider = get_provider(acc)
    
    if not provider:
        click.echo(f"❌ Provider not supported.")
        return
    
    try:
        click.echo(f"🔍 Auditing permissions for {acc.name} ({acc.provider})...")
        
        perm_result = provider.check_permissions()
        
        if "error" in perm_result:
            click.echo(f"❌ Error: {perm_result['error']}")
            return
        
        # User info
        if perm_result.get("user_info"):
            click.echo(f"\n👤 用户信息:")
            for key, value in perm_result["user_info"].items():
                click.echo(f"  {key}: {value}")
        
        # Warnings
        if perm_result.get("warnings"):
            click.echo(f"\n⚠️  警告:")
            for warning in perm_result["warnings"]:
                click.echo(f"  • {warning}")
        
        # Permissions
        if perm_result.get("permissions"):
            click.echo(f"\n✅ 已验证的只读权限:")
            for perm in perm_result["permissions"]:
                click.echo(f"  • {perm['api']}: {perm['description']}")
        
        # High-risk permissions
        if perm_result.get("high_risk_permissions"):
            click.echo(f"\n🚨 检测到高危权限:")
            for risk in perm_result["high_risk_permissions"]:
                click.echo(f"\n  策略: {risk['policy']}")
                click.echo(f"  风险级别: {risk['risk_level']}")
                click.echo(f"  说明: {risk['description']}")
                click.echo(f"  建议: {risk['recommendation']}")
        else:
            click.echo(f"\n✅ 未检测到明显的高危权限")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

@cli.group()
def topology():
    """网络拓扑 - 生成网络拓扑图"""
    pass

@topology.command("generate")
@click.option("--account", required=True, help="Account to generate topology for")
@click.option("--output", default="topology.md", help="Output file path")
def generate_topology(account, output):
    """Generate Mermaid network topology diagram"""
    from core.topology_generator import TopologyGenerator
    
    cm = ConfigManager()
    acc = cm.get_account(account)
    if not acc:
        click.echo(f"❌ Account '{account}' not found.")
        return
    
    provider = get_provider(acc)
    if not provider:
        click.echo(f"❌ Provider not supported for account '{account}'.")
        return
    
    try:
        click.echo(f"🔍 Fetching resources for {account}...")
        
        # Query resources
        instances = provider.list_instances()
        vpcs = provider.list_vpcs()
        rds_instances = provider.list_rds()
        redis_instances = provider.list_redis()
        eips = provider.list_eip()
        
        click.echo(f"✅ Found {len(instances)} ECS, {len(vpcs)} VPCs, {len(rds_instances)} RDS")
        
        # Generate markdown report with topology
        report = TopologyGenerator.generate_markdown_report(
            account, instances, vpcs, rds_instances, redis_instances, eips
        )
        
        # Save to file
        with open(output, 'w', encoding='utf-8') as f:
            f.write(report)
        
        click.echo(f"✅ Topology saved to {output}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")

@cli.group()
def report():
    """报告生成 - 生成Excel/HTML/PDF资源报告"""
    pass

@report.command("generate")
@click.option("--account", required=True, help="Account to generate report for")
@click.option("--format", type=click.Choice(['html', 'pdf', 'excel']), default='html', help="Report format")
@click.option("--output", help="Output file path")
@click.option("--include-idle", is_flag=True, help="Include idle resource analysis")
def generate_report(account, format, output, include_idle):
    """Generate resource report"""
    from core.report_generator import ReportGenerator
    from core.idle_detector import IdleDetector
    
    cm = ConfigManager()
    accounts = resolve_account_name(cm, account)
    
    if not accounts or len(accounts) == 0:
        return
    
    # 如果有多个账号，只使用第一个
    acc = accounts[0]
    
    provider = get_provider(acc)
    if not provider:
        click.echo(f"❌ Provider not supported.")
        return
    
    try:
        click.echo(f"🔍 Gathering data for {acc.name} ({acc.provider})...")
        
        # Collect data
        data = {
            'ecs': provider.list_instances(),
            'rds': provider.list_rds(),
            'redis': provider.list_redis(),
            'eip': provider.list_eip()
        }
        
        # Include idle analysis if requested
        if include_idle:
            click.echo("🔍 Analyzing idle resources...")
            idle_resources = []
            for inst in data['ecs']:
                metrics = IdleDetector.fetch_ecs_metrics(provider, inst.id, days=7)
                is_idle, reasons = IdleDetector.is_ecs_idle(metrics)
                if is_idle:
                    idle_resources.append((inst, reasons))
            data['idle'] = idle_resources
        
        # Determine output filename
        if not output:
            output = f"{acc.name}_report.{format}"
        
        if format == 'excel':
            ReportGenerator.generate_excel(f"{acc.name} ({acc.provider})", data, output)
            click.echo(f"✅ Excel report saved to {output}")
        elif format == 'html':
            html_content = ReportGenerator.generate_html(acc.name, data)
            ReportGenerator.save_html(html_content, output)
            click.echo(f"✅ HTML report saved to {output}")
        else:  # pdf
            html_temp = output.replace('.pdf', '.html')
            html_content = ReportGenerator.generate_html(acc.name, data)
            ReportGenerator.save_html(html_content, html_temp)
            ReportGenerator.html_to_pdf(html_temp, output)
            click.echo(f"✅ PDF report saved to {output}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

@analyze.command("cost")
@click.option("--account", required=True, help="Account to analyze")
def analyze_cost(account):
    """Analyze renewal costs and discount opportunities"""
    from core.cost_analyzer import CostAnalyzer
    
    cm = ConfigManager()
    acc = cm.get_account(account)
    if not acc:
        click.echo(f"❌ Account '{account}' not found.")
        return
    
    provider = get_provider(acc)
    if not provider:
        click.echo(f"❌ Provider not supported.")
        return
    
    try:
        click.echo(f"🔍 Analyzing costs for {account}...")
        
        # Fetch instances
        instances = provider.list_instances()
        
        # Renewal cost analysis
        renewal_analysis = CostAnalyzer.analyze_renewal_costs(instances)
        
        click.echo(f"\n📊 续费成本分析")
        click.echo(f"包年包月实例总数: {renewal_analysis['total_prepaid']}")
        click.echo(f"30天内到期: {len(renewal_analysis['expiring_soon'])}")
        
        if renewal_analysis['expiring_soon']:
            click.echo(f"\n⏰ 即将到期的实例:")
            click.echo(f"{'ID':<22} {'名称':<25} {'规格':<15} {'到期日期':<12} {'剩余天数':<10}")
            click.echo("-" * 90)
            for exp in renewal_analysis['expiring_soon']:
                click.echo(f"{exp['id']:<22} {exp['name'][:23]:<25} {exp['spec']:<15} {exp['expire_date']:<12} {exp['days_left']:<10}")
        
        # Discount suggestions
        suggestions = CostAnalyzer.suggest_discount_optimization(instances)
        
        if suggestions:
            click.echo(f"\n💡 折扣优化建议:")
            for i, sugg in enumerate(suggestions, 1):
                click.echo(f"\n{i}. {sugg['type']}")
                click.echo(f"   描述: {sugg['description']}")
                click.echo(f"   潜在节省: {sugg['potential_saving']}")
                click.echo(f"   建议行动: {sugg['action']}")
        
        # Monthly estimate for PostPaid
        estimate = CostAnalyzer.calculate_monthly_estimate(instances)
        if estimate['total_monthly_estimate'] > 0:
            click.echo(f"\n💰 按量付费月度估算: ¥{estimate['total_monthly_estimate']:.2f}")
            click.echo(f"   ({estimate['note']})")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

# ------------------------------------------------------------------------------
# Dynamic Command Registration
# ------------------------------------------------------------------------------

def register_dynamic_commands():
    """动态注册资源模块命令"""
    from core.analyzer_registry import AnalyzerRegistry
    import resource_modules  # 触发注册
    
    analyzers = AnalyzerRegistry.list_analyzers()
    
    # 获取已有的命令，避免冲突
    existing_query_cmds = query.list_commands(click.Context(query))
    existing_analyze_cmds = analyze.list_commands(click.Context(analyze))
    
    for resource_type, info in analyzers.items():
        # 1. 注册 query 命令
        if resource_type not in existing_query_cmds:
            @query.command(resource_type, help=f"List {info['display_name']}")
            @click.option("--account", help="Specific account to query")
            @click.option("--format", type=click.Choice(['table', 'json', 'csv']), default='table', help="Output format")
            @click.option("--output", help="Output file path")
            @click.option("--region", help="Filter by region")
            @click.option("--analysis", "-a", help="Advanced analysis query (e.g. 'groupby:region|count')")
            # 使用闭包捕获 resource_type
            def dynamic_query(account, format, output, region, analysis, rt=resource_type):
                cm = ConfigManager()
                accounts = resolve_account_name(cm, account)
                if not accounts: return
                
                analyzer_cls = AnalyzerRegistry.get_analyzer_class(rt)
                all_resources = []
                
                for acc in accounts:
                    if acc.provider != "aliyun": continue # 目前仅支持阿里云插件
                    try:
                        analyzer = analyzer_cls(acc.access_key_id, acc.access_key_secret, acc.name)
                        # 如果指定了区域，只查询该区域
                        regions_to_query = [region] if region else analyzer.get_all_regions()
                        
                        for r in regions_to_query:
                            try:
                                instances = analyzer.get_instances(r)
                                # 统一格式化
                                for inst in instances:
                                    # 尝试标准化字段
                                    inst['provider'] = acc.provider
                                    inst['account'] = acc.name
                                    # 确保有 Region 字段
                                    if 'Region' not in inst:
                                        inst['Region'] = r
                                    all_resources.append(inst)
                            except Exception as e:
                                click.echo(f"⚠️  Error querying {acc.name} in {r}: {e}", err=True)
                                
                    except Exception as e:
                        click.echo(f"❌ Failed to init analyzer for {acc.name}: {e}", err=True)

                # 高级分析处理
                if analysis:
                    from core.data_engine import DataEngine
                    click.echo(f"📊 Analyzing {len(all_resources)} resources with query: {analysis}")
                    result = DataEngine.analyze(all_resources, analysis)
                    click.echo(result)
                    return

                if format == 'json':
                    import json
                    click.echo(json.dumps(all_resources, indent=2, ensure_ascii=False))
                elif format == 'csv':
                    # 简单CSV导出
                    import csv
                    import sys
                    if all_resources:
                        keys = all_resources[0].keys()
                        writer = csv.DictWriter(sys.stdout, fieldnames=keys)
                        writer.writeheader()
                        writer.writerows(all_resources)
                else:
                    # Table output
                    if not all_resources:
                        click.echo("No resources found.")
                        return
                        
                    # 动态决定列
                    first = all_resources[0]
                    # 尝试找一些通用列
                    cols = ['InstanceId', 'InstanceName', 'Region', 'InstanceStatus']
                    # 如果没有这些列，就用前4个
                    if not all(k in first for k in cols):
                        cols = list(first.keys())[:4]
                        
                    header = "  ".join([f"{c:<20}" for c in cols])
                    click.echo(header)
                    click.echo("-" * len(header))
                    
                    for r in all_resources:
                        row = "  ".join([f"{str(r.get(c,''))[:18]:<20}" for c in cols])
                        click.echo(row)

        # 2. 注册 analyze 命令
        if resource_type not in existing_analyze_cmds:
            @analyze.command(resource_type, help=f"Analyze {info['display_name']} for idle resources")
            @click.option("--account", help="Specific account to analyze")
            @click.option("--days", default=14, help="Days of monitoring data")
            def dynamic_analyze(account, days, rt=resource_type):
                cm = ConfigManager()
                accounts = resolve_account_name(cm, account)
                if not accounts: return
                
                analyzer_cls = AnalyzerRegistry.get_analyzer_class(rt)
                
                for acc in accounts:
                    if acc.provider != "aliyun": continue
                    try:
                        click.echo(f"🔍 Analyzing {rt} for account: {acc.name}...")
                        analyzer = analyzer_cls(acc.access_key_id, acc.access_key_secret, acc.name)
                        # 调用 analyze 方法 (注意：部分 analyzer 如 MongoDBAnalyzer 的 analyze 方法没有返回值，而是直接生成报告)
                        # 我们需要统一接口，但现在先兼容现有逻辑
                        result = analyzer.analyze(days=days)
                        
                        # 如果返回了结果列表（新标准），则打印
                        if isinstance(result, list) and result:
                             click.echo(f"⚠️  Found {len(result)} idle resources:")
                             for item in result:
                                 # 尝试适配不同的返回结构
                                 if isinstance(item, dict):
                                     # 可能是 {'instance':..., 'optimization':...} 或者是扁平的 dict
                                     inst = item.get('instance') or item
                                     opt = item.get('optimization') or item.get('优化建议', '')
                                     
                                     # 尝试获取ID和名称
                                     iid = inst.get('InstanceId') or inst.get('DBInstanceId') or inst.get('集群ID') or 'N/A'
                                     iname = inst.get('InstanceName') or inst.get('DBInstanceDescription') or inst.get('集群名称') or 'N/A'
                                     
                                     click.echo(f"  - {iid} ({iname}): {opt}")
                                 else:
                                     click.echo(f"  - {item}")
                        elif result is None:
                            # 旧模式，analyzer 内部可能已经打印了日志或生成了报告
                            pass
                            
                    except Exception as e:
                        click.echo(f"❌ Error analyzing {acc.name}: {e}", err=True)

@cli.command()
def dashboard():
    """Launch TUI Dashboard (Experimental)"""
    try:
        from core.dashboard import CloudLensApp
        app = CloudLensApp()
        app.run()
    except ImportError:
        click.echo("❌ Textual is not installed. Please run 'pip install textual'", err=True)
    except Exception as e:
        click.echo(f"❌ Failed to launch dashboard: {e}", err=True)

# Load external plugins
from core.analyzer_registry import AnalyzerRegistry
AnalyzerRegistry.load_plugins()

# Run registration
register_dynamic_commands()

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        # No arguments provided, start REPL
        try:
            from core.repl import CloudLensREPL
            repl = CloudLensREPL()
            repl.start()
        except ImportError:
            # Fallback if prompt_toolkit is not installed
            cli()
        except Exception as e:
            print(f"Failed to start REPL: {e}")
            cli()
    else:
        cli()
