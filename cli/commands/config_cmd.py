# -*- coding: utf-8 -*-
"""
配置管理命令模块
"""
import click
from rich.console import Console
from rich.table import Table

from core.cache import CacheManager
from core.config import CloudAccount, ConfigManager

console = Console()


@click.group()
def config():
    """配置管理 - 添加、删除、查看云账号配置"""
    pass


@config.command("list")
@click.option("--format", type=click.Choice(["table", "json"]), default="table", help="输出格式")
def list_accounts(format):
    """查看所有已配置的云账号"""
    cm = ConfigManager()
    accounts = cm.list_accounts()

    if not accounts:
        console.print("[yellow]暂无配置账号[/yellow]")
        return

    if format == "json":
        import json

        data = [
            {"name": acc.name, "provider": acc.provider, "region": acc.region} for acc in accounts
        ]
        console.print_json(data=data)
    else:
        # 使用Rich Table
        table = Table(title="☁️  云账号配置", show_header=True, header_style="bold magenta")
        table.add_column("账号名称", style="cyan", no_wrap=True)
        table.add_column("云厂商", style="green")
        table.add_column("默认区域", style="blue")
        table.add_column("状态", style="yellow")

        for acc in accounts:
            # 简单的状态检查（可以改进）
            status = "✓ 正常" if acc.access_key_id else "✗ 未配置"
            table.add_row(acc.name, acc.provider, acc.region, status)

        console.print(table)
        console.print(f"\n共 [bold]{len(accounts)}[/bold] 个账号")


@config.command("add")
@click.option("--provider", prompt=True, type=click.Choice(["aliyun", "tencent", "aws", "volcano"]))
@click.option("--name", prompt=True, help="账号别名")
@click.option("--region", prompt=True, default="cn-hangzhou")
@click.option("--ak", prompt=True, help="Access Key ID")
@click.option("--sk", prompt=True, hide_input=True, help="Secret Access Key")
def add_account(provider, name, region, ak, sk):
    """添加新的云账号配置"""
    cm = ConfigManager()

    # 权限预检
    console.print("🔍 [cyan]正在验证凭证...[/cyan]")

    try:
        from cli.utils import get_provider
        from models.resource import CloudAccount as TempAccount

        temp_account = TempAccount(
            name=name, provider=provider, access_key_id=ak, access_key_secret=sk, region=region
        )

        test_provider = get_provider(temp_account)

        # 测试API调用
        if provider in ["aliyun", "tencent"]:
            test_provider.list_instances()
            console.print("✅ [green]凭证验证成功[/green]")

        # 检查权限
        try:
            permissions = test_provider.check_permissions()
            if hasattr(permissions, "__iter__") and not isinstance(permissions, str):
                console.print(f"📋 检测到权限项: [bold]{len(permissions)}[/bold] 个")

            if isinstance(permissions, dict) and permissions.get("high_risk_permissions"):
                high_risk = permissions["high_risk_permissions"]
                if high_risk:
                    console.print(f"⚠️  [yellow]警告: 检测到 {len(high_risk)} 个高危权限[/yellow]")
        except Exception as e:
            console.print(f"⚠️  [yellow]权限检查跳过: {e}[/yellow]")

    except Exception as e:
        console.print(f"❌ [red]凭证验证失败: {e}[/red]")
        if not click.confirm("\n是否仍要添加该账号?", default=False):
            console.print("[yellow]已取消添加账号[/yellow]")
            return
        console.print("⚠️  [yellow]警告: 该账号可能无法正常使用[/yellow]")

    # 添加账号
    cm.add_account(
        name=name, provider=provider, access_key_id=ak, access_key_secret=sk, region=region
    )
    console.print(f"✅ [green]账号 '{name}' 添加成功（密钥已保存到 Keyring）[/green]")


@config.command("remove")
@click.argument("name")
@click.option("--force", is_flag=True, help="强制删除，不确认")
def remove_account(name, force):
    """删除云账号配置"""
    cm = ConfigManager()

    # 检查账号是否存在
    accounts = cm.list_accounts()
    if not any(acc.name == name for acc in accounts):
        console.print(f"[red]错误: 账号 '{name}' 不存在[/red]")
        return

    # 确认删除
    if not force:
        if not click.confirm(f"确定要删除账号 '{name}' 吗?"):
            console.print("[yellow]已取消删除[/yellow]")
            return

    cm.remove_account(name)

    # 清理缓存
    cache = CacheManager()
    cache.clear(account_name=name)

    console.print(f"✅ [green]账号 '{name}' 已删除（缓存已清理）[/green]")


@config.command("show")
@click.argument("name")
def show_account(name):
    """显示账号详细信息"""
    cm = ConfigManager()
    account = cm.get_account(name)

    if not account:
        console.print(f"[red]错误: 账号 '{name}' 不存在[/red]")
        return

    from rich.panel import Panel

    info = f"""
[bold cyan]账号名称:[/bold cyan] {account.name}
[bold cyan]云厂商:[/bold cyan] {account.provider}
[bold cyan]默认区域:[/bold cyan] {account.region}
[bold cyan]Access Key:[/bold cyan] {account.access_key_id[:8]}...{account.access_key_id[-4:]}
    """

    panel = Panel(info.strip(), title=f"☁️  账号信息: {name}", border_style="green")
    console.print(panel)
