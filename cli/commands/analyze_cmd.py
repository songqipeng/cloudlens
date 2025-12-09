"""资源分析命令模块"""
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from core.config import ConfigManager
from core.context import ContextManager
from core.error_handler import handle_exceptions

console = Console()


@click.group()
def analyze():
    """资源分析 - 闲置资源、成本、安全、续费分析"""
    pass


@analyze.command("idle")
@click.option("--account", "-a", help="账号名称")
@click.option("--days", "-d", default=7, type=int, help="分析天数")
@handle_exceptions
def analyze_idle(account, days):
    """检测闲置资源 - 基于监控指标分析"""
    from core.idle_detector import IdleDetector
    from providers.aliyun.provider import AliyunProvider

    console.print(f"[cyan]🔍 分析最近 {days} 天的闲置资源...[/cyan]")

    # 智能解析账号
    cm = ConfigManager()
    ctx_mgr = ContextManager()

    if not account:
        account = ctx_mgr.get_last_account()
        if not account:
            console.print("[yellow]⚠️  请指定账号: --account <name>[/yellow]")
            console.print("提示: cl config list 查看可用账号")
            return

    # 获取账号配置
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

    # 获取ECS实例
    with Progress() as progress:
        task = progress.add_task("[cyan]正在查询ECS实例...", total=100)
        instances = provider.list_instances()
        progress.update(task, advance=100)

    if not instances:
        console.print("[yellow]未找到ECS实例[/yellow]")
        return

    # 分析闲置资源
    idle_instances = []
    with Progress() as progress:
        task = progress.add_task("[cyan]正在分析闲置状态...", total=len(instances))

        for inst in instances:
            # 获取监控指标
            metrics = IdleDetector.fetch_ecs_metrics(provider, inst.id, days)

            # 判断是否闲置
            is_idle, reasons = IdleDetector.is_ecs_idle(metrics)

            if is_idle:
                idle_instances.append(
                    {
                        "instance_id": inst.id,
                        "name": inst.name or "-",
                        "region": inst.region,
                        "spec": inst.spec,
                        "reasons": reasons,
                    }
                )

            progress.update(task, advance=1)

    # 展示结果
    if not idle_instances:
        console.print("[green]✅ 未发现闲置资源[/green]")
        return

    table = Table(title=f"闲置ECS实例 ({len(idle_instances)})")
    table.add_column("实例ID", style="cyan", no_wrap=True)
    table.add_column("名称", style="white")
    table.add_column("区域", style="blue")
    table.add_column("规格", style="magenta")
    table.add_column("闲置原因", style="yellow")

    for inst in idle_instances:
        table.add_row(
            inst["instance_id"],
            inst["name"],
            inst["region"],
            inst["spec"],
            "\n".join(inst["reasons"][:2]),  # 只显示前2个原因
        )

    console.print(table)
    console.print(f"\n[bold]💡 建议: 考虑释放或降配这些实例以节省成本[/bold]")


@analyze.command("renewal")
@click.option("--account", "-a", help="账号名称")
@click.option("--days", "-d", default=30, type=int, help="未来天数")
@handle_exceptions
def analyze_renewal(account, days):
    """续费提醒 - 检查即将到期的包年包月资源"""
    from datetime import datetime, timedelta
    from providers.aliyun.provider import AliyunProvider

    console.print(f"[cyan]⏰ 检查未来 {days} 天内到期的资源...[/cyan]")

    # 获取账号配置
    cm = ConfigManager()
    ctx_mgr = ContextManager()

    if not account:
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
    instances = provider.list_instances()

    # 筛选即将到期的
    expiring = []
    cutoff_date = datetime.now() + timedelta(days=days)

    for inst in instances:
        if inst.charge_type == "PrePaid" and inst.expired_time:
            if inst.expired_time <= cutoff_date:
                remaining = (inst.expired_time - datetime.now()).days
                expiring.append(
                    {
                        "id": inst.id,
                        "name": inst.name or "-",
                        "type": "ECS",
                        "expire_time": inst.expired_time,
                        "remaining_days": remaining,
                    }
                )

    if not expiring:
        console.print("[green]✅ 无即将到期资源[/green]")
        return

    # 排序：剩余天数从少到多
    expiring.sort(key=lambda x: x["remaining_days"])

    # 展示
    table = Table(title=f"即将到期资源 ({len(expiring)})")
    table.add_column("资源ID", style="cyan")
    table.add_column("名称", style="white")
    table.add_column("类型", style="blue")
    table.add_column("到期时间", style="red")
    table.add_column("剩余天数", style="yellow")

    for item in expiring:
        # 根据剩余天数设置颜色
        if item["remaining_days"] <= 7:
            days_style = "[bold red]"
        elif item["remaining_days"] <= 15:
            days_style = "[yellow]"
        else:
            days_style = "[white]"

        table.add_row(
            item["id"],
            item["name"],
            item["type"],
            item["expire_time"].strftime("%Y-%m-%d"),
            f"{days_style}{item['remaining_days']} 天[/]",
        )

    console.print(table)
    console.print(f"\n[bold]💡 建议: 及时续费或释放资源[/bold]")


@analyze.command("forecast")
@click.option("--account", "-a", help="账号名称")
@click.option("--days", "-d", default=90, type=int, help="预测天数")
@handle_exceptions
def analyze_forecast(account, days):
    """AI成本预测 - 预测未来成本趋势(需要历史数据)"""
    from core.cost_predictor import CostPredictor
    from rich.panel import Panel

    console.print(f"[cyan]🔮 AI成本预测 (未来{days}天)[/cyan]\n")

    # 获取账号配置
    cm = ConfigManager()
    if not account:
        ctx_mgr = ContextManager()
        account = ctx_mgr.get_last_account()

    account_config = cm.get_account(account)
    if not account_config:
        console.print(f"[red]❌ 账号 '{account}' 不存在[/red]")
        return

    # 创建预测器
    predictor = CostPredictor()

    # 生成预测报告
    report = predictor.generate_forecast_report(account_config.name, days)

    if not report:
        console.print("[red]❌ 预测失败[/red]")
        return

    if "error" in report:
        console.print(f"[yellow]⚠️  {report['error']}[/yellow]")
        console.print("\n提示:")
        console.print("  • 需要至少30天的历史数据才能进行预测")
        console.print("  • 请多次运行 'cl analyze cost' 积累数据")
        console.print("  • 建议设置定时任务每天记录成本")
        return

    # 显示预测结果
    console.print(Panel.fit(
        f"[bold cyan]账号:[/bold cyan] {report['account']}\n"
        f"[bold yellow]预测周期:[/bold yellow] {report['forecast_period']}\n"
        f"[bold green]预测总成本:[/bold green] ¥{report['predicted_total_cost']:,.2f}\n"
        f"[bold blue]日均成本:[/bold blue] ¥{report['predicted_avg_daily_cost']:,.2f}\n"
        f"[bold]增长率:[/bold] {report['growth_rate']:+.2f}%",
        title=f"📈 {report['model_type'].upper()}模型预测结果"
    ))

    # 显示趋势提示
    if report['growth_rate'] > 20:
        console.print("\n[bold red]⚠️  警告: 成本增长率较高 (+{:.1f}%)[/bold red]".format(report['growth_rate']))
        console.print("建议:")
        console.print("  • 检查是否有闲置资源")
        console.print("  • 考虑使用预留实例降低成本")
        console.print("  • 优化资源规格配置")
    elif report['growth_rate'] > 10:
        console.print("\n[yellow]提示: 成本呈上升趋势 (+{:.1f}%)[/yellow]".format(report['growth_rate']))
    else:
        console.print("\n[green]✓ 成本增长在可控范围内[/green]")

    console.print(f"\n[dim]模型类型: {report['model_type']}[/dim]")
    if report['model_type'] == 'simple':
        console.print("[dim]提示: 安装Prophet可获得更准确的预测[/dim]")
        console.print("[dim]  pip install prophet[/dim]")


@analyze.command("cost")
@click.option("--account", "-a", help="账号名称")
@click.option("--days", "-d", default=30, type=int, help="分析天数")
@click.option("--trend", is_flag=True, help="显示成本趋势")
@handle_exceptions
def analyze_cost(account, days, trend):
    """成本分析 - 当前成本、趋势分析与优化建议"""
    from core.cost_trend_analyzer import CostTrendAnalyzer
    from providers.aliyun.provider import AliyunProvider
    from rich.table import Table
    from rich.panel import Panel

    console.print("[cyan]💰 分析成本与优化机会...[/cyan]\n")

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
        task = progress.add_task("[cyan]正在查询资源...", total=3)
        
        instances = provider.list_instances()
        progress.update(task, advance=1)
        
        rds_list = provider.list_rds()
        progress.update(task, advance=1)
        
        redis_list = provider.list_redis()
        progress.update(task, advance=1)

    all_resources = instances + rds_list + redis_list
    
    if not all_resources:
        console.print("[yellow]未找到资源[/yellow]")
        return

    # 记录成本快照
    analyzer = CostTrendAnalyzer()
    snapshot = analyzer.record_cost_snapshot(account_config.name, all_resources)

    # 显示当前成本
    console.print(Panel.fit(
        f"[bold cyan]账号:[/bold cyan] {account_config.name}\n"
        f"[bold green]总资源数:[/bold green] {snapshot['resource_count']}\n"
        f"[bold yellow]预估月成本:[/bold yellow] ¥{snapshot['total_cost']:,.2f}",
        title="📊 当前成本概览"
    ))

    # 按类型展示
    console.print("\n[bold]按资源类型分布:[/bold]")
    type_table = Table()
    type_table.add_column("资源类型", style="cyan")
    type_table.add_column("月成本", style="green", justify="right")
    type_table.add_column("占比", style="yellow", justify="right")

    for rtype, cost in sorted(snapshot['cost_by_type'].items(), key=lambda x: x[1], reverse=True):
        pct = (cost / snapshot['total_cost'] * 100) if snapshot['total_cost'] > 0 else 0
        type_table.add_row(rtype, f"¥{cost:,.2f}", f"{pct:.1f}%")

    console.print(type_table)

    # 按区域展示
    if len(snapshot['cost_by_region']) > 1:
        console.print("\n[bold]按区域分布:[/bold]")
        region_table = Table()
        region_table.add_column("区域", style="cyan")
        region_table.add_column("月成本", style="green", justify="right")

        for region, cost in sorted(snapshot['cost_by_region'].items(), key=lambda x: x[1], reverse=True):
            region_table.add_row(region, f"¥{cost:,.2f}")

        console.print(region_table)

    # 趋势分析
    if trend:
        console.print(f"\n[bold cyan]📈 成本趋势分析 (最近{days}天)[/bold cyan]")
        report = analyzer.generate_trend_report(account_config.name, days)

        if "error" in report:
            console.print(f"[yellow]⚠️  {report['error']}[/yellow]")
            console.print("提示: 需要多次运行 'cl analyze cost' 积累数据后才能分析趋势")
        else:
            analysis = report['analysis']
            
            # 展示趋势指标
            trend_table = Table(title="趋势指标")
            trend_table.add_column("指标", style="cyan")
            trend_table.add_column("数值", style="green")

            trend_table.add_row("分析周期", f"{analysis['period_days']} 天")
            trend_table.add_row("最新成本", f"¥{analysis['latest_cost']:,.2f}")
            trend_table.add_row("平均成本", f"¥{analysis['avg_cost']:,.2f}")
            
            # 总变化
            change_color = "red" if analysis['total_change'] > 0 else "green"
            trend_table.add_row(
                "总变化",
                f"[{change_color}]{analysis['total_change']:+,.2f} ({analysis['total_change_pct']:+.1f}%)[/{change_color}]"
            )
            
            # 环比
            mom_color = "red" if analysis['mom_change'] > 0 else "green"
            trend_table.add_row(
                "环比(MoM)",
                f"[{mom_color}]{analysis['mom_change']:+,.2f} ({analysis['mom_change_pct']:+.1f}%)[/{mom_color}]"
            )

            console.print(trend_table)
            console.print(f"\n[bold]趋势: {analysis['trend']}[/bold]")

    # 优化建议
    console.print("\n[bold cyan]💡 优化建议:[/bold cyan]")
    suggestions = [
        "• 运行 'cl analyze idle' 检查闲置资源",
        "• 考虑使用预留实例降低10-30%成本",
        "• 定期检查并清理未使用的磁盘和快照",
        "• 使用标签管理,实现成本分摊"
    ]
    for sugg in suggestions:
        console.print(sugg)


@analyze.command("tags")
@click.option("--account", "-a", help="账号名称")
@handle_exceptions
def analyze_tags(account):
    """标签治理 - 检查资源标签合规性"""
    from core.tag_analyzer import TagAnalyzer
    from providers.aliyun.provider import AliyunProvider

    console.print("[cyan]🏷️  分析资源标签合规性...[/cyan]")

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
    instances = provider.list_instances()

    # 分析标签
    analyzer = TagAnalyzer()
    untagged = []
    incomplete_tags = []

    for inst in instances:
        if not inst.tags or len(inst.tags) == 0:
            untagged.append({"id": inst.id, "name": inst.name or "-"})
        elif not all(k in inst.tags for k in ["env", "project"]):
            incomplete_tags.append({"id": inst.id, "name": inst.name or "-", "tags": inst.tags})

    # 展示结果
    console.print(f"\n[bold]总资源数:[/bold] {len(instances)}")
    console.print(f"[bold]未打标签:[/bold] {len(untagged)} ({len(untagged)/len(instances)*100:.1f}%)")
    console.print(
        f"[bold]标签不完整:[/bold] {len(incomplete_tags)} ({len(incomplete_tags)/len(instances)*100:.1f}%)"
    )

    if untagged:
        console.print("\n[yellow]⚠️  未打标签的资源 (前10个):[/yellow]")
        for item in untagged[:10]:
            console.print(f"  • {item['id']} ({item['name']})")

    console.print("\n[bold]💡 建议: 为所有资源添加 env、project 等标签以便管理[/bold]")


@analyze.command("security")
@click.option("--account", "-a", help="账号名称")
@click.option("--cis", is_flag=True, help="执行CIS Benchmark合规检查")
@handle_exceptions
def analyze_security(account, cis):
    """安全合规 - 检查公网暴露、安全组、CIS Benchmark等"""
    from core.cis_compliance import CISBenchmark
    from providers.aliyun.provider import AliyunProvider
    from rich.table import Table
    from rich.panel import Panel

    console.print("[cyan]🔒 扫描安全风险...[/cyan]\n")

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
    
    # 基础安全检查
    public_exposed = []
    for resource in all_resources:
        if hasattr(resource, "public_ips") and resource.public_ips:
            public_exposed.append(resource)

    console.print(Panel.fit(
        f"[bold cyan]总资源数:[/bold cyan] {len(all_resources)}\n"
        f"[bold yellow]公网暴露:[/bold yellow] {len(public_exposed)} ({len(public_exposed)/len(all_resources)*100:.1f}%)",
        title="📊 基础安全统计"
    ))

    if public_exposed:
        console.print("\n[yellow]⚠️  公网暴露的资源 (前10个):[/yellow]")
        table = Table()
        table.add_column("资源ID", style="cyan")
        table.add_column("名称", style="white")
        table.add_column("公网IP", style="red")
        table.add_column("区域", style="blue")

        for item in public_exposed[:10]:
            table.add_row(
                item.id,
                item.name or "-",
                ", ".join(item.public_ips),
                item.region
            )

        console.print(table)

    # CIS Benchmark合规检查
    if cis:
        console.print("\n[bold cyan]🛡️  CIS Benchmark合规检查[/bold cyan]\n")
        
        checker = CISBenchmark()
        results = checker.run_all_checks(all_resources, provider)

        # 显示合规分数
        score = results["compliance_score"]
        score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
        
        console.print(Panel.fit(
            f"[bold {score_color}]合规分数: {score}%[/bold {score_color}]\n"
            f"[green]通过: {results['passed']}[/green] | "
            f"[red]失败: {results['failed']}[/red]",
            title="CIS合规评分"
        ))

        # 按类别展示
        console.print("\n[bold]分类汇总:[/bold]")
        summary_table = Table()
        summary_table.add_column("类别", style="cyan")
        summary_table.add_column("合规率", style="green", justify="right")
        summary_table.add_column("通过/总数", style="white", justify="right")

        for category, stats in results["summary"].items():
            rate = stats.get("compliance_rate", 0)
            rate_color = "green" if rate >= 80 else "yellow" if rate >= 60 else "red"
            summary_table.add_row(
                category,
                f"[{rate_color}]{rate:.1f}%[/{rate_color}]",
                f"{stats['passed']}/{stats['total']}"
            )

        console.print(summary_table)

        # 显示通过的检查项
        passed_checks = [r for r in results["results"] if r["status"] == "PASS"]
        if passed_checks:
            console.print(f"\n[bold green]✓ 通过的检查项 ({len(passed_checks)}个):[/bold green]")
            for check in passed_checks[:10]:  # 只显示前10个
                severity_color = {
                    "CRITICAL": "red",
                    "HIGH": "yellow",
                    "MEDIUM": "blue",
                    "LOW": "white"
                }.get(check["severity"], "white")
                
                console.print(
                    f"[{severity_color}]✓[/{severity_color}] "
                    f"[{check['id']}] {check['title']} [{check['severity']}]"
                )
                console.print(f"  └─ {check['details']}")

        # 显示失败的检查项
        failed_checks = [r for r in results["results"] if r["status"] == "FAIL"]
        if failed_checks:
            console.print(f"\n[bold red]❌ 未通过的检查项 ({len(failed_checks)}个):[/bold red]")
            for check in failed_checks:  # 显示所有失败项
                severity_color = {
                    "CRITICAL": "red",
                    "HIGH": "yellow",
                    "MEDIUM": "blue",
                    "LOW": "white"
                }.get(check["severity"], "white")
                
                console.print(
                    f"[{severity_color}]✗[/{severity_color}] "
                    f"[{check['id']}] {check['title']} [{check['severity']}]"
                )
                console.print(f"  └─ 原因: {check['details']}")
                
                # 显示修复建议
                if check.get("remediation"):
                    console.print(f"  └─ [cyan]修复建议:[/cyan]")
                    for line in check["remediation"].split('\n'):
                        console.print(f"     {line}")
                console.print("")  # 空行分隔

    console.print("\n[bold]💡 建议: 定期运行安全检查,及时发现并修复安全隐患[/bold]")
