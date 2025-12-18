# -*- coding: utf-8 -*-
"""
缓存管理命令模块
"""
import click
from rich.console import Console
from rich.table import Table

from core.cache import CacheManager

console = Console()


@click.group()
def cache():
    """缓存管理命令"""
    pass


@cache.command("status")
def cache_status():
    """查看缓存状态"""
    from core.cache import CacheManager

    cache_mgr = CacheManager()
    
    # 使用CacheManager的查询方法
    try:
        # 统计信息
        total_result = cache_mgr.db.query_one("SELECT COUNT(*) as count FROM resource_cache")
        total_count = total_result.get("count", 0) if total_result else 0

        valid_result = cache_mgr.db.query_one(
            "SELECT COUNT(*) as count FROM resource_cache WHERE expires_at > NOW()" if cache_mgr.db_type == "mysql" 
            else "SELECT COUNT(*) as count FROM resource_cache WHERE expires_at > datetime('now')"
        )
        valid_count = valid_result.get("count", 0) if valid_result else 0

        expired_result = cache_mgr.db.query_one(
            "SELECT COUNT(*) as count FROM resource_cache WHERE expires_at <= NOW()" if cache_mgr.db_type == "mysql"
            else "SELECT COUNT(*) as count FROM resource_cache WHERE expires_at <= datetime('now')"
        )
        expired_count = expired_result.get("count", 0) if expired_result else 0

        # 按资源类型统计
        type_stats_query = (
            """
            SELECT resource_type, COUNT(*) as count, account_name
            FROM resource_cache 
            WHERE expires_at > NOW()
            GROUP BY resource_type, account_name
            """
            if cache_mgr.db_type == "mysql"
            else
            """
            SELECT resource_type, COUNT(*) as count, account_name
            FROM resource_cache 
            WHERE expires_at > datetime('now')
            GROUP BY resource_type, account_name
            """
        )
        type_stats = cache_mgr.db.query(type_stats_query)

        # 显示统计信息
        console.print("\n[bold cyan]📊 缓存统计[/bold cyan]")
        console.print(f"总条目数: [bold]{total_count}[/bold]")
        console.print(f"有效条目: [green]{valid_count}[/green]")
        console.print(f"已过期: [yellow]{expired_count}[/yellow]")
        console.print(f"数据库类型: {cache_mgr.db_type}")

        if type_stats:
            console.print("\n[bold]按类型统计（有效缓存）:[/bold]")
            table = Table()
            table.add_column("资源类型", style="cyan")
            table.add_column("账号", style="green")
            table.add_column("条目数", style="yellow")

            for row in type_stats:
                res_type = row.get("resource_type") if isinstance(row, dict) else row[0]
                count = row.get("count") if isinstance(row, dict) else row[1]
                account = row.get("account_name") if isinstance(row, dict) else row[2]
                table.add_row(res_type, account, str(count))

            console.print(table)
    except Exception as e:
        console.print(f"[red]获取缓存状态失败: {e}[/red]")


@cache.command("clear")
@click.option("--resource-type", help="只清除指定资源类型")
@click.option("--account", help="只清除指定账号")
@click.option("--all", "clear_all", is_flag=True, help="清除所有缓存")
def cache_clear(resource_type, account, clear_all):
    """清除缓存"""
    cache_mgr = CacheManager()

    if clear_all:
        if click.confirm("确定要清除所有缓存吗?"):
            cache_mgr.clear()
            console.print("[green]✓ 所有缓存已清除[/green]")
    elif resource_type or account:
        cache_mgr.clear(resource_type=resource_type, account_name=account)
        msg = f"✓ 已清除"
        if resource_type:
            msg += f" {resource_type}"
        if account:
            msg += f" ({account})"
        msg += " 的缓存"
        console.print(f"[green]{msg}[/green]")
    else:
        console.print("[yellow]请指定 --resource-type, --account 或 --all[/yellow]")


@cache.command("cleanup")
def cache_cleanup():
    """清理过期缓存"""
    cache_mgr = CacheManager()

    with console.status("[cyan]正在清理过期缓存...[/cyan]"):
        deleted = cache_mgr.cleanup_expired()

    if deleted > 0:
        console.print(f"[green]✓ 已清理 {deleted} 条过期缓存[/green]")
    else:
        console.print("[yellow]没有需要清理的过期缓存[/yellow]")
