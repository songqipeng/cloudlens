"""自动修复命令模块"""
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

from core.config import ConfigManager
from core.context import ContextManager
from core.error_handler import handle_exceptions

console = Console()


@click.group()
def remediate():
    """自动修复 - 批量修复资源问题(支持干运行)"""
    pass


@remediate.command("tags")
@click.option("--account", "-a", help="账号名称")
@click.option("--env", default="production", help="环境标签(默认:production)")
@click.option("--owner", default="cloudlens", help="所有者标签(默认:cloudlens)")
@click.option("--confirm", is_flag=True, help="确认执行(不加此标志为干运行)")
@handle_exceptions
def remediate_tags(account, env, owner, confirm):
    """为无标签资源自动打标签"""
    from core.remediation_engine import RemediationEngine
    from providers.aliyun.provider import AliyunProvider

    dry_run = not confirm
    mode_text = "[yellow]干运行模式[/yellow]" if dry_run else "[red]实际执行[/red]"
    console.print(f"[cyan]🏷️  自动打标签 ({mode_text})[/cyan]\n")

    # 获取账号配置
    cm = ConfigManager()
    if not account:
        ctx_mgr = ContextManager()
        account = ctx_mgr.get_last_account()

    account_config = cm.get_account(account)
    if not account_config:
        console.print(f"[red]❌ 账号 '{account}' 不存在[/red]")
        return

    # 创建Provider
    provider = AliyunProvider(
        account_name=account_config.name,
        access_key=account_config.access_key_id,
        secret_key=account_config.access_key_secret,
        region=account_config.region,
    )

    # 获取资源
    with Progress() as progress:
        task = progress.add_task("[cyan]查询资源...", total=3)
        
        instances = provider.list_instances()
        progress.update(task, advance=1)
        
        rds_list = provider.list_rds()
        progress.update(task, advance=1)
        
        redis_list = provider.list_redis()
        progress.update(task, advance=1)

    all_resources = instances + rds_list + redis_list

    # 执行修复
    engine = RemediationEngine()
    default_tags = {
        "env": env,
        "owner": owner,
        "managed-by": "cloudlens",
        "auto-tagged": "true",
    }

    result = engine.remediate_tags(
        resources=all_resources,
        default_tags=default_tags,
        dry_run=dry_run,
        provider=provider,
    )

    # 显示结果
    if dry_run:
        console.print(Panel.fit(
            f"[bold yellow]总资源数:[/bold yellow] {len(all_resources)}\n"
            f"[bold cyan]需要打标签:[/bold cyan] {result['total']}",
            title="预览结果"
        ))

        if result.get("preview"):
            console.print("\n[yellow]将添加标签的资源 (前10个):[/yellow]")
            table = Table()
            table.add_column("资源ID", style="cyan")
            table.add_column("资源类型", style="blue")
            table.add_column("标签", style="green")

            for item in result["preview"]:
                tags_str = ", ".join(f"{k}={v}" for k, v in item["tags"].items())
                table.add_row(item["resource_id"], item["resource_type"], tags_str)

            console.print(table)

        console.print(
            f"\n[bold yellow]⚠️  这是干运行模式,未实际执行修改[/bold yellow]\n"
            f"要实际执行,请添加 --confirm 标志"
        )
    else:
        console.print(Panel.fit(
            f"[bold green]成功:[/bold green] {result['success']}\n"
            f"[bold red]失败:[/bold red] {result.get('failed', 0)}",
            title="执行结果"
        ))

        if result.get("failed_details"):
            console.print("\n[red]失败的资源:[/red]")
            for item in result["failed_details"]:
                console.print(f"  • {item['resource_id']}: {item['error']}")


@remediate.command("security")
@click.option("--account", "-a", help="账号名称")
@click.option("--confirm", is_flag=True, help="确认执行")
@handle_exceptions
def remediate_security(account, confirm):
    """修复安全组风险(开发中)"""
    dry_run = not confirm
    
    console.print(f"[cyan]🔐 修复安全组风险...[/cyan]\n")
    console.print("[yellow]⚠️  此功能正在开发中[/yellow]")
    console.print("\n建议:")
    console.print("  • 手动检查安全组规则")
    console.print("  • 移除0.0.0.0/0访问")
    console.print("  • 使用企业IP白名单")


@remediate.command("history")
@click.option("--limit", default=20, type=int, help="显示数量")
@handle_exceptions
def remediate_history(limit):
    """查看自动修复历史"""
    from core.remediation_engine import RemediationEngine

    console.print("[cyan]📜 自动修复历史[/cyan]\n")

    engine = RemediationEngine()
    history = engine.get_audit_history(limit=limit)

    if not history:
        console.print("[yellow]暂无修复历史[/yellow]")
        return

    table = Table()
    table.add_column("时间", style="cyan")
    table.add_column("操作", style="blue")
    table.add_column("资源ID", style="white")
    table.add_column("状态", style="green")

    for entry in history:
        status_icon = "✓" if entry["status"] == "success" else "✗"
        status_color = "green" if entry["status"] == "success" else "red"
        
        table.add_row(
            entry["timestamp"][:19],
            entry["action"],
            entry["resource_id"][:30],
            f"[{status_color}]{status_icon} {entry['status']}[/{status_color}]"
        )

    console.print(table)
