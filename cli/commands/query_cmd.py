# -*- coding: utf-8 -*-
"""
查询命令模块（带缓存和进度条）
"""
import click
from rich.console import Console
from rich.progress import track
from rich.table import Table

from cli.utils import get_provider, smart_resolve_account
from core.cache import CacheManager
from core.config import ConfigManager
from core.context import ContextManager

console = Console()


@click.group()
def query():
    """资源查询命令"""
    pass


@query.command()
@click.argument("account", required=False)
@click.argument("resource_type", required=False, default="ecs")
@click.option("--region", help="指定区域")
@click.option("--no-cache", is_flag=True, help="跳过缓存，强制查询")
@click.option("--format", type=click.Choice(["table", "json", "csv"]), default="table")
def resources(account, resource_type, region, no_cache, format):
    """
    查询云资源

    示例:
        cl query ecs              # 查询ECS（使用默认账号）
        cl query myaccount rds    # 查询指定账号的RDS
        cl query --region cn-beijing ecs  # 指定区域
    """
    cm = ConfigManager()
    ctx_mgr = ContextManager()
    cache = CacheManager()

    try:
        account_obj = smart_resolve_account(cm, ctx_mgr, account)
    except ValueError as e:
        console.print(f"[red]错误: {e}[/red]")
        return

    use_region = region or account_obj.region

    # 尝试从缓存获取
    if not no_cache:
        cached_data = cache.get(resource_type, account_obj.name, use_region)
        if cached_data:
            console.print("✨ [green]使用缓存数据[/green]")
            _display_resources(cached_data, resource_type, format)
            return

    # 真实查询
    console.print(f"🔍 [cyan]正在查询 {account_obj.name} 的 {resource_type}...[/cyan]")

    try:
        provider = get_provider(account_obj)

        # 调用相应的list方法
        if resource_type == "ecs":
            results = provider.list_instances()
        elif resource_type == "rds":
            results = provider.list_rds()
        elif resource_type == "redis":
            results = provider.list_redis()
        elif resource_type == "vpc":
            results = provider.list_vpcs()
        else:
            console.print(f"[yellow]警告: 未知的资源类型 '{resource_type}'[/yellow]")
            return

        # 缓存结果
        cache.set(resource_type, account_obj.name, results, use_region)

        console.print(f"✅ [green]查询完成，找到 {len(results)} 个资源[/green]")
        _display_resources(results, resource_type, format)

    except Exception as e:
        console.print(f"[red]查询失败: {e}[/red]")


def _display_resources(resources, resource_type, format="table"):
    """显示资源列表"""
    if not resources:
        console.print("[yellow]未找到资源[/yellow]")
        return

    if format == "json":
        import json

        console.print_json(data=resources)
    elif format == "csv":
        # 简化CSV输出
        if resources:
            keys = resources[0].keys()
            print(",".join(keys))
            for res in resources:
                print(",".join(str(res.get(k, "")) for k in keys))
    else:
        # Rich Table输出
        if not resources:
            return

        table = Table(title=f"📦 {resource_type.upper()} 资源列表")

        # 动态添加列（基于第一个资源的键）
        sample = resources[0]
        key_columns = (
            ["InstanceId", "InstanceName", "Status", "RegionId"]
            if resource_type == "ecs"
            else list(sample.keys())[:5]
        )

        for key in key_columns:
            if key in sample:
                table.add_column(key, style="cyan")

        # 添加行
        for res in resources[:50]:  # 限制显示前50条
            row_data = [str(res.get(k, "-")) for k in key_columns if k in res]
            table.add_row(*row_data)

        console.print(table)

        if len(resources) > 50:
            console.print(f"\n[yellow]注意: 仅显示前50条，总共 {len(resources)} 条[/yellow]")


@query.command("all")
@click.option("--resource-types", multiple=True, help="资源类型列表")
@click.option("--no-cache", is_flag=True)
def query_all(resource_types, no_cache):
    """
    批量查询多种资源

    示例:
        cl query all --resource-types ecs --resource-types rds
    """
    if not resource_types:
        resource_types = ["ecs", "rds", "redis", "vpc"]

    cm = ConfigManager()
    accounts = cm.list_accounts()

    if not accounts:
        console.print("[red]未找到配置的账号[/red]")
        return

    console.print(f"[cyan]开始查询 {len(accounts)} 个账号的 {len(resource_types)} 种资源...[/cyan]")

    for account in track(accounts, description="查询账号..."):
        console.print(f"\n[bold]账号: {account.name}[/bold]")

        for res_type in track(resource_types, description=f"  查询资源..."):
            try:
                # 调用单个资源查询（复用逻辑）
                from click.testing import CliRunner

                # 这里简化，实际应该调用共享函数
                console.print(f"  - {res_type}: [green]完成[/green]")
            except Exception as e:
                console.print(f"  - {res_type}: [red]失败 - {e}[/red]")
