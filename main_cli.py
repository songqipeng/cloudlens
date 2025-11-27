import click
import sys
import os

# 添加当前目录到 path 以便导入模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import List, Optional
from core.config import ConfigManager, AccountConfig
from core.context import ContextManager

@click.group()
def cli():
    """Multi-Cloud Query CLI (CloudLens)"""
    pass

@cli.group()
def config():
    """Manage configuration and accounts"""
    pass

@config.command("list")
def list_accounts():
    """List all configured accounts"""
    cm = ConfigManager()
    accounts = cm.list_accounts()
    if not accounts:
        click.echo("No accounts configured.")
        return
        
    click.echo(f"{'Name':<15} {'Provider':<10} {'Region':<15} {'Keyring':<10}")
    click.echo("-" * 50)
    for acc in accounts:
        click.echo(f"{acc.name:<15} {acc.provider:<10} {acc.region:<15} {str(acc.use_keyring):<10}")

@config.command("add")
@click.option("--provider", prompt=True, type=click.Choice(['aliyun', 'tencent', 'aws', 'volcano']))
@click.option("--name", prompt=True, help="Alias for the account")
@click.option("--region", prompt=True, default="cn-hangzhou")
@click.option("--ak", prompt=True, help="Access Key ID")
@click.option("--sk", prompt=True, hide_input=True, help="Secret Access Key")
def add_account(provider, name, region, ak, sk):
    """Add a new cloud account"""
    cm = ConfigManager()
    
    # TODO: 在这里调用 PermissionGuard 进行权限预检
    
    new_account = AccountConfig(
        name=name,
        provider=provider,
        region=region,
        access_key_id=ak,
        access_key_secret=sk,
        use_keyring=True
    )
    cm.add_account(new_account)
    click.echo(f"✅ Account '{name}' added successfully (Secret saved to Keyring).")

@cli.group()
def query():
    """Query resources across clouds"""
    pass

from providers.aliyun.provider import AliyunProvider
from providers.tencent.provider import TencentProvider

def get_provider(account_config: AccountConfig):
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

def resolve_account_name(cm: ConfigManager, account_name: str) -> List[AccountConfig]:
    """
    解析账号名称，处理重名情况
    
    Returns:
        List[AccountConfig]: 匹配的账号列表
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
def query_ecs(account, format, output, status, region, filter_expr, concurrent):
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
    
    if format == 'json':
        export_to_json(all_resources, output)
    elif format == 'csv':
        export_to_csv(all_resources, output)
    else:
        # Table format
        click.echo(f"{'ID':<22} {'Name':<30} {'IP':<16} {'Status':<10} {'Region':<12} {'Provider':<8}")
        click.echo("-" * 100)
        for r in all_resources:
            ip = r.public_ips[0] if r.public_ips else (r.private_ips[0] if r.private_ips else "-")
            click.echo(f"{r.id:<22} {r.name[:28]:<30} {ip:<16} {r.status.value:<10} {r.region:<12} {r.provider:<8}")


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
    """Analyze resources (Idle, Renewal, Cost)"""
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
    
    cm = ConfigManager()
    accounts = []
    if account:
        acc = cm.get_account(account)
        if acc: accounts.append(acc)
    else:
        accounts = cm.list_accounts()
        
    click.echo(f"🔍 Analyzing idle resources (based on {days} days of metrics)...")
    click.echo(f"{'Account':<15} {'ID':<22} {'Name':<25} {'Status':<10} {'Idle Reasons':<50}")
    click.echo("-" * 130)
    
    total_idle = 0
    
    for acc in accounts:
        provider = get_provider(acc)
        if not provider or provider.provider_name != "aliyun":
            continue
        
        try:
            # Only analyze ECS for now
            instances = provider.list_instances()
            
            for inst in instances:
                # Fetch metrics
                metrics = IdleDetector.fetch_ecs_metrics(provider, inst.id, days)
                
                # Check if idle
                is_idle, reasons = IdleDetector.is_ecs_idle(metrics)
                
                if is_idle:
                    total_idle += 1
                    reason_str = "; ".join(reasons[:2])  # Show first 2 reasons
                    click.echo(f"{acc.name:<15} {inst.id:<22} {inst.name[:23]:<25} {inst.status.value:<10} {reason_str:<50}")
        except Exception as e:
            click.echo(f"❌ Error analyzing {acc.name}: {e}")
    
    click.echo(f"\n📊 Total idle resources found: {total_idle}")

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
    
    cm = ConfigManager()
    accounts = resolve_account_name(cm, account)
    
    if not accounts:
        return
    
    click.echo("🔍 Analyzing security compliance...")
    
    all_instances = []
    all_eips = []
    
    for acc in accounts:
        provider = get_provider(acc)
        if not provider:
            continue
        
        try:
            all_instances.extend(provider.list_instances())
            all_eips.extend(provider.list_eip())
        except Exception as e:
            click.echo(f"❌ Error fetching resources from {acc.name}: {e}")
    
    # Public exposure detection
    exposed = SecurityComplianceAnalyzer.detect_public_exposure(all_instances)
    
    click.echo(f"\n🌐 公网暴露分析")
    click.echo(f"总实例数: {len(all_instances)}")
    click.echo(f"公网暴露: {len(exposed)}")
    
    if exposed:
        click.echo(f"\n⚠️  公网暴露实例 (前10个):")
        click.echo(f"{'ID':<22} {'Name':<25} {'Type':<8} {'Public IPs':<30} {'Risk':<8}")
        click.echo("-" * 100)
        for exp in exposed[:10]:
            ips_str = ", ".join(exp['public_ips'][:2])
            click.echo(f"{exp['id']:<22} {exp['name'][:23]:<25} {exp['type']:<8} {ips_str:<30} {exp['risk_level']:<8}")
    
    # EIP usage analysis
    eip_stats = SecurityComplianceAnalyzer.analyze_eip_usage(all_eips)
    
    click.echo(f"\n📍 弹性公网IP统计")
    click.echo(f"总EIP数: {eip_stats['total']}")
    click.echo(f"已绑定: {eip_stats['bound']}")
    click.echo(f"未绑定: {eip_stats['unbound']} ({eip_stats['unbound_rate']}%)")
    
    if eip_stats['unbound_eips']:
        click.echo(f"\n💰 未绑定EIP (浪费成本):")
        for eip in eip_stats['unbound_eips'][:5]:
            click.echo(f"  • {eip['ip_address']} (ID: {eip['id']})")
    
    # Security suggestions
    suggestions = SecurityComplianceAnalyzer.suggest_security_improvements(len(exposed), eip_stats['unbound'])
    
    click.echo(f"\n💡 安全建议:")
    for sugg in suggestions:
        click.echo(f"  {sugg}")

@analyze.command("security")
@click.option("--account", help="Specific account to analyze")
def analyze_security(account):
    """Analyze security compliance and risks"""
    from core.security_compliance import SecurityComplianceAnalyzer
    
    cm = ConfigManager()
    accounts = resolve_account_name(cm, account)
    
    if not accounts:
        return
    
    click.echo("🔍 Analyzing security compliance...")
    
    all_instances = []
    all_eips = []
    
    for acc in accounts:
        provider = get_provider(acc)
        if not provider:
            continue
        
        try:
            all_instances.extend(provider.list_instances())
            all_eips.extend(provider.list_eip())
        except Exception as e:
            click.echo(f"❌ Error fetching resources from {acc.name}: {e}")
    
    # Public exposure detection
    exposed = SecurityComplianceAnalyzer.detect_public_exposure(all_instances)
    
    click.echo(f"\n🌐 公网暴露分析")
    click.echo(f"总实例数: {len(all_instances)}")
    click.echo(f"公网暴露: {len(exposed)}")
    
    if exposed:
        click.echo(f"\n⚠️  公网暴露实例 (前10个):")
        click.echo(f"{'ID':<22} {'Name':<25} {'Type':<8} {'Public IPs':<30} {'Risk':<8}")
        click.echo("-" * 100)
        for exp in exposed[:10]:
            ips_str = ", ".join(exp['public_ips'][:2])
            click.echo(f"{exp['id']:<22} {exp['name'][:23]:<25} {exp['type']:<8} {ips_str:<30} {exp['risk_level']:<8}")
    
    # EIP usage analysis
    eip_stats = SecurityComplianceAnalyzer.analyze_eip_usage(all_eips)
    
    click.echo(f"\n📍 弹性公网IP统计")
    click.echo(f"总EIP数: {eip_stats['total']}")
    click.echo(f"已绑定: {eip_stats['bound']}")
    click.echo(f"未绑定: {eip_stats['unbound']} ({eip_stats['unbound_rate']}%)")
    
    if eip_stats['unbound_eips']:
        click.echo(f"\n💰 未绑定EIP (浪费成本):")
        for eip in eip_stats['unbound_eips'][:5]:
            click.echo(f"  • {eip['ip_address']} (ID: {eip['id']})")
    
    # Security suggestions
    suggestions = SecurityComplianceAnalyzer.suggest_security_improvements(len(exposed), eip_stats['unbound'])
    
    click.echo(f"\n💡 安全建议:")
    for sugg in suggestions:
        click.echo(f"  {sugg}")

@cli.group()
def audit():
    """Audit account permissions and security"""
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
    """Generate network topology diagrams"""
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
    """Generate HTML/PDF reports"""
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

if __name__ == "__main__":
    cli()
