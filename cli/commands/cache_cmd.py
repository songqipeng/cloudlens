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
    import sqlite3
    from pathlib import Path

    cache_db = Path.home() / ".cloudlens" / "cache.db"

    if not cache_db.exists():
        console.print("[yellow]缓存数据库不存在[/yellow]")
        return

    conn = sqlite3.connect(cache_db)
    cursor = conn.cursor()

    # 统计信息
    cursor.execute("SELECT COUNT(*) FROM resource_cache")
    total_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM resource_cache WHERE expires_at > datetime('now')")
    valid_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM resource_cache WHERE expires_at <= datetime('now')")
    expired_count = cursor.fetchone()[0]

    # 按资源类型统计
    cursor.execute(
        """
        SELECT resource_type, COUNT(*), account_name
        FROM resource_cache 
        WHERE expires_at > datetime('now')
        GROUP BY resource_type, account_name
    """
    )
    type_stats = cursor.fetchall()

    conn.close()

    # 显示统计信息
    console.print("\n[bold cyan]📊 缓存统计[/bold cyan]")
    console.print(f"总条目数: [bold]{total_count}[/bold]")
    console.print(f"有效条目: [green]{valid_count}[/green]")
    console.print(f"已过期: [yellow]{expired_count}[/yellow]")
    console.print(f"缓存文件: {cache_db}")

    if type_stats:
        console.print("\n[bold]按类型统计（有效缓存）:[/bold]")
        table = Table()
        table.add_column("资源类型", style="cyan")
        table.add_column("账号", style="green")
        table.add_column("条目数", style="yellow")

        for res_type, count, account in type_stats:
            table.add_row(res_type, account, str(count))

        console.print(table)


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
