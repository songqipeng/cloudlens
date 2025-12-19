#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单管理命令
"""

import click
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

console = Console()


@click.group()
def bill():
    """账单管理命令"""
    pass


@bill.command("fetch")
@click.option("--account", required=True, help="账号名称（config.json中配置的账号）")
@click.option("--start", help="开始月份，格式：YYYY-MM，默认3个月前")
@click.option("--end", help="结束月份，格式：YYYY-MM，默认当前月")
@click.option("--output-dir", default="./bills_data", help="输出目录（CSV模式）")
@click.option("--use-db", is_flag=True, help="使用数据库存储（推荐）")
@click.option("--db-path", help="数据库路径（默认~/.cloudlens/bills.db）")
@click.option("--max-records", type=int, help="每个月最大记录数（用于测试）")
def fetch_bills(account, start, end, output_dir, use_db, db_path, max_records):
    """
    从阿里云BSS OpenAPI自动获取账单数据
    
    示例：
      ./cl bill fetch --account my_account --use-db
      ./cl bill fetch --account my_account --start 2025-01 --end 2025-06 --use-db
      ./cl bill fetch --account my_account --start 2020-01  # CSV模式
    """
    from core.config import ConfigManager
    from core.bill_fetcher import BillFetcher
    
    try:
        # 获取账号配置
        cm = ConfigManager()
        account_config = cm.get_account(account)
        
        if not account_config:
            console.print(f"[red]❌ 账号 '{account}' 不存在，请先配置[/red]")
            console.print("\n提示: ./cl config account add")
            return
        
        # 设置默认时间范围（最近3个月）
        if not end:
            end = datetime.now().strftime("%Y-%m")
        if not start:
            start = (datetime.now() - timedelta(days=90)).strftime("%Y-%m")
        
        storage_mode = "数据库" if use_db else "CSV文件"
        
        console.print(Panel.fit(
            f"[cyan]账号:[/cyan] {account}\n"
            f"[cyan]时间范围:[/cyan] {start} 至 {end}\n"
            f"[cyan]存储模式:[/cyan] {storage_mode}\n"
            f"[cyan]{'数据库路径' if use_db else '输出目录'}:[/cyan] {db_path or output_dir}",
            title="📥 账单数据获取",
            border_style="cyan"
        ))
        
        # 创建获取器
        fetcher = BillFetcher(
            access_key_id=account_config.access_key_id,
            access_key_secret=account_config.access_key_secret,
            region=account_config.region,
            use_database=use_db,
            db_path=db_path
        )
        
        # 批量获取账单
        output_path = Path(output_dir) if not use_db else None
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        with Progress() as progress:
            task = progress.add_task("[cyan]获取账单数据...", total=None)
            
            result = fetcher.fetch_and_save_bills(
                start_month=start,
                end_month=end,
                output_dir=output_path,
                account_name=account_id,
                account_id=account_id
            )
        
        # 显示结果
        if result:
            console.print(f"\n[green]✅ 成功获取 {len(result)} 个月份的账单数据[/green]\n")
            
            if use_db:
                # 数据库模式
                table = Table(title="账单数据统计")
                table.add_column("账期", style="cyan")
                table.add_column("新增记录", style="green")
                table.add_column("跳过记录", style="yellow")
                
                total_inserted = 0
                total_skipped = 0
                
                for billing_cycle, stats in sorted(result.items()):
                    if isinstance(stats, dict):
                        inserted = stats.get('inserted', 0)
                        skipped = stats.get('skipped', 0)
                        total_inserted += inserted
                        total_skipped += skipped
                        table.add_row(
                            billing_cycle,
                            f"{inserted:,}",
                            f"{skipped:,}"
                        )
                
                console.print(table)
                console.print(f"\n[cyan]总计:[/cyan] 新增 [green]{total_inserted:,}[/green] 条，跳过 [yellow]{total_skipped:,}[/yellow] 条")
                
                # 显示数据库统计
                from core.bill_storage import BillStorageManager
                storage = BillStorageManager(db_path)
                stats = storage.get_storage_stats()
                
                console.print(f"\n[cyan]📊 数据库统计:[/cyan]")
                console.print(f"  总记录数: [green]{stats['total_records']:,}[/green]")
                console.print(f"  账期范围: [cyan]{stats['min_cycle']} 至 {stats['max_cycle']}[/cyan]")
                console.print(f"  数据库大小: [yellow]{stats['db_size_mb']:.2f} MB[/yellow]")
                console.print(f"  数据库路径: {stats['db_path']}")
            
            else:
                # CSV模式
                table = Table(title="账单文件列表")
                table.add_column("账期", style="cyan")
                table.add_column("文件路径", style="green")
                table.add_column("文件大小", style="yellow")
                
                for billing_cycle, csv_path in sorted(result.items()):
                    file_size = csv_path.stat().st_size if csv_path.exists() else 0
                    size_mb = file_size / 1024 / 1024
                    table.add_row(
                        billing_cycle,
                        str(csv_path),
                        f"{size_mb:.2f} MB"
                    )
                
                console.print(table)
            
            console.print(f"\n[cyan]💡 提示:[/cyan]")
            if use_db:
                console.print(f"  1. 数据已存储在数据库，可用于全量折扣分析")
                console.print(f"  2. 运行折扣分析: [yellow]./cl analyze discount --use-db[/yellow]")
                console.print(f"  3. 在Web页面自动使用数据库数据")
            else:
                console.print(f"  1. 账单文件已保存，可用于折扣分析")
                console.print(f"  2. 运行折扣分析: [yellow]./cl analyze discount --bill-dir {output_path / account_id}[/yellow]")
                console.print(f"  3. 在Web页面刷新即可看到最新数据")
        else:
            console.print("[yellow]⚠️  没有获取到任何数据[/yellow]")
        
    except ImportError as e:
        console.print("[red]❌ 缺少必要的SDK依赖[/red]\n")
        console.print("请安装：")
        console.print("  [yellow]pip install aliyun-python-sdk-core aliyun-python-sdk-bssopenapi python-dateutil[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 获取失败: {str(e)}[/red]")
        import traceback
        if console.is_terminal:
            traceback.print_exc()


@bill.command("test")
@click.option("--account", required=True, help="账号名称")
@click.option("--month", help="测试月份，格式：YYYY-MM，默认当前月")
@click.option("--limit", default=10, help="获取记录数限制")
def test_fetch(account, month, limit):
    """
    测试账单API连接（只获取少量数据）
    
    示例：
      ./cl bill test --account my_account
      ./cl bill test --account my_account --month 2025-12 --limit 5
    """
    from core.config import ConfigManager
    from core.bill_fetcher import BillFetcher
    
    try:
        cm = ConfigManager()
        account_config = cm.get_account(account)
        
        if not account_config:
            console.print(f"[red]❌ 账号 '{account}' 不存在[/red]")
            return
        
        if not month:
            month = datetime.now().strftime("%Y-%m")
        
        console.print(f"[cyan]测试获取账期 {month} 的前 {limit} 条记录...[/cyan]\n")
        
        fetcher = BillFetcher(
            access_key_id=account_config.access_key_id,
            access_key_secret=account_config.access_key_secret,
            region=account_config.region
        )
        
        records = fetcher.fetch_instance_bill(
            billing_cycle=month,
            max_records=limit
        )
        
        if records:
            console.print(f"[green]✅ 成功获取 {len(records)} 条记录[/green]\n")
            
            # 显示第一条记录的关键字段
            first_record = records[0]
            
            panel_content = []
            key_fields = [
                ('ProductName', '产品名称'),
                ('SubscriptionType', '计费方式'),
                ('ListPrice', '官网价'),
                ('InvoiceDiscount', '折扣'),
                ('PretaxAmount', '应付金额'),
                ('Currency', '币种'),
                ('InstanceID', '实例ID'),
            ]
            
            for api_field, label in key_fields:
                value = first_record.get(api_field, 'N/A')
                panel_content.append(f"[cyan]{label}:[/cyan] {value}")
            
            console.print(Panel(
                "\n".join(panel_content),
                title="📋 样本数据（第1条记录）",
                border_style="green"
            ))
            
            console.print(f"\n[green]✅ API连接正常，可以执行完整获取[/green]")
        else:
            console.print(f"[yellow]⚠️  账期 {month} 没有数据[/yellow]")
    
    except ImportError:
        console.print("[red]❌ 缺少SDK依赖，请安装:[/red]")
        console.print("  [yellow]pip install aliyun-python-sdk-core aliyun-python-sdk-bssopenapi[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 测试失败: {str(e)}[/red]")


if __name__ == "__main__":
    bill()

@bill.command("fetch-all")
@click.option("--account", required=True, help="账号名称")
@click.option("--earliest-year", default=2020, help="最早年份，默认2020")
@click.option("--db-path", help="数据库路径（默认~/.cloudlens/bills.db）")
def fetch_all_bills(account, earliest_year, db_path):
    """
    获取历史所有账单数据（自动尝试尽可能早的数据）
    
    示例：
      ./cl bill fetch-all --account ydzn
      ./cl bill fetch-all --account ydzn --earliest-year 2018
    """
    from core.config import ConfigManager
    from core.bill_fetcher import BillFetcher
    
    try:
        cm = ConfigManager()
        account_config = cm.get_account(account)
        
        if not account_config:
            console.print(f"[red]❌ 账号 '{account}' 不存在[/red]")
            return
        
        account_id = f"{account_config.access_key_id[:10]}-{account}"
        
        console.print(Panel.fit(
            f"[cyan]账号:[/cyan] {account}\n"
            f"[cyan]最早年份:[/cyan] {earliest_year}\n"
            f"[cyan]账号ID:[/cyan] {account_id}\n"
            f"[yellow]⚠️  这将获取尽可能多的历史数据，可能需要1-2小时[/yellow]",
            title="📥 获取历史所有账单",
            border_style="cyan"
        ))
        
        console.print("\n[yellow]按Ctrl+C可随时中断[/yellow]\n")
        
        # 创建获取器（数据库模式）
        fetcher = BillFetcher(
            access_key_id=account_config.access_key_id,
            access_key_secret=account_config.access_key_secret,
            region=account_config.region,
            use_database=True,
            db_path=db_path
        )
        
        # 获取历史账单
        with Progress() as progress:
            task = progress.add_task("[cyan]获取历史账单...", total=None)
            
            inserted, skipped = fetcher.fetch_historical_bills(
                account_id=account_id,
                earliest_year=earliest_year
            )
        
        # 显示结果
        console.print(f"\n[green]✅ 历史账单获取完成[/green]\n")
        console.print(f"  新增记录: [green]{inserted:,}[/green]")
        console.print(f"  跳过记录: [yellow]{skipped:,}[/yellow]（已存在）")
        
        # 显示数据库统计
        from core.bill_storage import BillStorageManager
        storage = BillStorageManager(db_path)
        stats = storage.get_storage_stats()
        
        console.print(f"\n[cyan]📊 数据库统计:[/cyan]")
        console.print(f"  总记录数: [green]{stats['total_records']:,}[/green]")
        console.print(f"  账期范围: [cyan]{stats['min_cycle']} 至 {stats['max_cycle']}[/cyan]")
        console.print(f"  数据库大小: [yellow]{stats['db_size_mb']:.2f} MB[/yellow]")
        console.print(f"  数据库路径: {stats['db_path']}")
        
        console.print(f"\n[cyan]💡 下一步:[/cyan]")
        console.print(f"  运行折扣分析: [yellow]./cl analyze discount --use-db --months 12[/yellow]")
        console.print(f"  查看数据库: [yellow]./cl bill stats[/yellow]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  用户中断[/yellow]")
    except ImportError:
        console.print("[red]❌ 缺少SDK依赖，请安装:[/red]")
        console.print("  [yellow]pip install aliyun-python-sdk-core aliyun-python-sdk-bssopenapi python-dateutil[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 获取失败: {str(e)}[/red]")
        import traceback
        if console.is_terminal:
            traceback.print_exc()


@bill.command("stats")
@click.option("--db-path", help="数据库路径（默认~/.cloudlens/bills.db）")
def show_stats(db_path):
    """
    显示账单数据库统计信息
    
    示例：
      ./cl bill stats
    """
    from core.bill_storage import BillStorageManager
    
    try:
        storage = BillStorageManager(db_path)
        stats = storage.get_storage_stats()
        
        console.print(Panel.fit(
            f"[cyan]总记录数:[/cyan] {stats['total_records']:,}\n"
            f"[cyan]账号数:[/cyan] {stats['account_count']}\n"
            f"[cyan]账期数:[/cyan] {stats['cycle_count']}\n"
            f"[cyan]账期范围:[/cyan] {stats['min_cycle'] or 'N/A'} 至 {stats['max_cycle'] or 'N/A'}\n"
            f"[cyan]数据库大小:[/cyan] {stats['db_size_mb']:.2f} MB\n"
            f"[cyan]数据库路径:[/cyan] {stats['db_path']}",
            title="📊 账单数据库统计",
            border_style="cyan"
        ))
        
        # 显示各账号的账期列表
        accounts_result = storage.db.query("SELECT DISTINCT account_id FROM bill_items")
        accounts = [row.get("account_id") if isinstance(row, dict) else row[0] for row in accounts_result]
        
        if accounts:
            console.print("\n[cyan]📅 各账号账期统计:[/cyan]\n")
            
            for account_id in accounts:
                cycles = storage.get_billing_cycles(account_id)
                if cycles:
                    console.print(f"  [green]{account_id}[/green]:")
                    console.print(f"    账期范围: {cycles[-1]['billing_cycle']} 至 {cycles[0]['billing_cycle']}")
                    console.print(f"    账期数: {len(cycles)}")
                    console.print(f"    总记录数: {sum(c['record_count'] for c in cycles):,}")
                    console.print()
    
    except Exception as e:
        console.print(f"[red]❌ 查询失败: {str(e)}[/red]")


