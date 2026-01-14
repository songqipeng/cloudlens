"""资源分析命令模块"""
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich import box
from pathlib import Path

from cloudlens.core.config import ConfigManager
from cloudlens.core.context import ContextManager
from cloudlens.core.error_handler import handle_exceptions

console = Console()


@click.group()
def analyze():
    """资源分析 - 闲置资源、成本、安全、续费分析"""
    pass


@analyze.command("idle")
@click.option("--account", "-a", help="账号名称")
@click.option("--days", "-d", default=7, type=int, help="分析天数")
@click.option("--no-cache", is_flag=True, help="强制刷新缓存")
@handle_exceptions
def analyze_idle(account, days, no_cache):
    """检测闲置资源 - 基于监控指标分析"""
    from cloudlens.core.services.analysis_service import AnalysisService
    from cloudlens.core.rules_manager import RulesManager
    
    # 智能解析账号
    cm = ConfigManager()
    ctx_mgr = ContextManager()

    if not account:
        account = ctx_mgr.get_last_account()
        if not account:
            console.print("[yellow]⚠️  请指定账号: --account <name>[/yellow]")
            console.print("提示: cl config list 查看可用账号")
            return
            
    # 加载优化规则 (用于显示阈值)
    rm = RulesManager()
    rules = rm.get_rules()
    cpu_threshold = rules["idle_rules"]["ecs"].get("cpu_threshold_percent", 5)
    
    console.print(f"[cyan]🔍 分析最近 {days} 天的闲置资源 (CPU < {cpu_threshold}%)...[/cyan]")

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]正在分析资源...", total=None) 
            # Note: We can't easily track granular progress inside the service without passing a callback.
            # For simplicity, we use an indeterminate progress bar here.
            
            idle_instances, is_cached = AnalysisService.analyze_idle_resources(account, days, no_cache)
            progress.update(task, completed=100)
            
        if is_cached:
            console.print(f"[green]⚡ 使用缓存数据 (上次分析于24小时内)[/green]")
            console.print("[dim]提示: 使用 --no-cache 可强制刷新[/dim]")
            
        display_idle_results(idle_instances)
        
    except Exception as e:
        console.print(f"[red]分析失败: {str(e)}[/red]")


def display_idle_results(idle_instances):
    """展示闲置资源结果"""

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
    from cloudlens.providers.aliyun.provider import AliyunProvider

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
@click.option("--days", default=90, help="预测天数")
@click.option("--export", is_flag=True, help="导出HTML预测报告")
@handle_exceptions
def analyze_forecast(account, days, export):
    """AI成本预测 - 基于历史数据预测未来成本"""
    from cloudlens.core.cost_predictor import CostPredictor
    from rich.table import Table
    from rich.panel import Panel
    import os
    import json
    from datetime import datetime

    console.print(f"[cyan]🤖 正在进行AI成本预测 (未来{days}天)...[/cyan]")

    # 获取账号配置
    cm = ConfigManager()
    if not account:
        ctx_mgr = ContextManager()
        account = ctx_mgr.get_last_account()

    account_config = cm.get_account(account)
    if not account_config:
        console.print(f"[red]❌ 账号 '{account}' 不存在[/red]")
        return

    predictor = CostPredictor()
    result = predictor.train_and_predict(days)

    if "error" in result:
        console.print(f"[red]预测失败: {result['error']}[/red]")
        if "scikit-learn" in result['error']:
             console.print("[yellow]提示: 请运行 'pip install scikit-learn numpy' 安装必要的依赖库[/yellow]")
        return

    # 展示预测结果
    console.print("\n[bold cyan]📊 预测结果:[/bold cyan]")
    
    # 核心指标
    console.print(Panel.fit(
        f"[bold]模型类型:[/bold] {result['model_type']}\n"
        f"[bold]拟合度(R²):[/bold] {result['confidence_score']:.4f}\n"
        f"[bold]日均增长:[/bold] ¥{result['daily_increase']:.2f}\n"
        f"[bold]预计增加:[/bold] ¥{result['predicted_total_increase']:.2f}",
        title="AI 预测摘要"
    ))

    # 导出HTML报告
    if export:
        report_dir = os.path.expanduser("~/cloudlens_reports")
        os.makedirs(report_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"forecast_report_{timestamp}.html"
        filepath = os.path.join(report_dir, filename)

        # 准备数据
        history_dates = result['history']['dates']
        history_costs = result['history']['costs']
        forecast_dates = result['forecast']['dates']
        forecast_costs = result['forecast']['costs']
        
        # 合并日期轴
        all_dates = history_dates + forecast_dates
        
        # 对应的数据系列 (历史部分后面补null, 预测部分前面补null)
        history_series = history_costs + [None] * len(forecast_dates)
        # 为了让线条连贯，预测数据的第一点应该是历史的最后一点
        if history_costs:
            forecast_series = [None] * (len(history_dates)-1) + [history_costs[-1]] + forecast_costs
        else:
            forecast_series = forecast_costs

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>CloudLens AI 成本预测报告</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .card {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ margin: 0 0 10px 0; color: #333; }}
        #forecastChart {{ width: 100%; height: 500px; }}
        .stats {{ display: flex; gap: 20px; margin-top: 10px; }}
        .stat-item {{ background: #f8f9fa; padding: 10px 20px; border-radius: 4px; }}
        .stat-val {{ font-weight: bold; color: #1890ff; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI 成本预测分析</h1>
            <div class="stats">
                <div class="stat-item">模型: <span class="stat-val">{result['model_type']}</span></div>
                <div class="stat-item">拟合度(R²): <span class="stat-val">{result['confidence_score']:.4f}</span></div>
                <div class="stat-item">日均增长: <span class="stat-val">¥{result['daily_increase']:.2f}</span></div>
                <div class="stat-item">未来{days}天预计增加: <span class="stat-val">¥{result['predicted_total_increase']:.2f}</span></div>
            </div>
        </div>

        <div class="card">
            <div id="forecastChart"></div>
        </div>
    </div>

    <script>
        var chart = echarts.init(document.getElementById('forecastChart'));
        chart.setOption({{
            title: {{ text: '成本预测趋势 (未来{days}天)' }},
            tooltip: {{ trigger: 'axis' }},
            legend: {{ data: ['历史成本', 'AI预测'] }},
            xAxis: {{ 
                type: 'category', 
                boundaryGap: false,
                data: {json.dumps(all_dates)} 
            }},
            yAxis: {{ type: 'value', name: '成本 (CNY)' }},
            series: [
                {{
                    name: '历史成本',
                    type: 'line',
                    data: {json.dumps(history_series)},
                    itemStyle: {{ color: '#52c41a' }},
                    areaStyle: {{ opacity: 0.1 }}
                }},
                {{
                    name: 'AI预测',
                    type: 'line',
                    data: {json.dumps(forecast_series)},
                    lineStyle: {{ type: 'dashed' }},
                    itemStyle: {{ color: '#1890ff' }}
                }}
            ]
        }});
        window.onresize = function() {{ chart.resize(); }};
    </script>
</body>
</html>
        """
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        console.print(f"\n[bold green]✓ 预测报告已导出:[/bold green] {filepath}")
        if os.name == 'posix':
            os.system(f"open '{filepath}'")
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
@click.option("--days", default=30, help="分析周期(天)")
@click.option("--trend", is_flag=True, help="显示趋势分析")
@click.option("--export", is_flag=True, help="导出HTML分析报告")
@handle_exceptions
def analyze_cost(account, days, trend, export):
    """成本分析 - 分析资源成本结构和趋势"""
    from cloudlens.core.cost_analyzer import CostAnalyzer
    from cloudlens.core.cost_trend_analyzer import CostTrendAnalyzer
    from cloudlens.providers.aliyun.provider import AliyunProvider
    from rich.table import Table
    from rich.panel import Panel
    import os
    import json
    from datetime import datetime

    console.print(f"[cyan]💰 分析资源成本 (过去{days}天)...[/cyan]")

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
        task = progress.add_task("[cyan]查询资源...", total=4)
        instances = provider.list_instances()
        progress.update(task, advance=1)
        rds_list = provider.list_rds()
        progress.update(task, advance=1)
        redis_list = provider.list_redis()
        progress.update(task, advance=1)
        slb_list = provider.list_slb()
        progress.update(task, advance=1)

    all_resources = instances + rds_list + redis_list + slb_list
    
    # 记录成本快照
    analyzer = CostTrendAnalyzer()
    snapshot = analyzer.record_cost_snapshot(account_config.name, all_resources)

    # 基础展示
    console.print(Panel.fit(
        f"[bold green]总月估算成本:[/bold green] ¥{snapshot['total_cost']:,.2f}\n"
        f"[bold]资源总数:[/bold] {len(all_resources)}",
        title="💰 成本概览"
    ))

    # 按类型展示
    if snapshot['cost_by_type']:
        console.print("\n[bold]按资源类型分布:[/bold]")
        type_table = Table(show_header=True, header_style="bold magenta")
        type_table.add_column("资源类型", style="cyan")
        type_table.add_column("月成本", style="green", justify="right")
        type_table.add_column("占比", style="yellow", justify="right")

        total = snapshot['total_cost']
        for r_type, cost in sorted(snapshot['cost_by_type'].items(), key=lambda x: x[1], reverse=True):
            pct = (cost / total * 100) if total > 0 else 0
            type_table.add_row(r_type, f"¥{cost:,.2f}", f"{pct:.1f}%")

        console.print(type_table)

    # 趋势分析
    report_data = None
    if trend or export:
        report_data = analyzer.generate_trend_report(account_config.name, days)

    if trend and report_data:
        if "error" in report_data:
             console.print(f"\n[yellow]⚠️  无法生成趋势分析: {report_data['error']}[/yellow]")
             console.print("[dim]提示: 趋势分析至少需要2个历史快照。请明天再运行一次即可看到趋势。[/dim]")
        else:
            console.print(f"\n[bold cyan]📈 成本趋势分析 (最近{days}天)[/bold cyan]")
            analysis = report_data['analysis']
            
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

    # 导出HTML报告
    if export and report_data and "error" not in report_data:
        report_dir = os.path.expanduser("~/cloudlens_reports")
        os.makedirs(report_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cost_report_{account}_{timestamp}.html"
        filepath = os.path.join(report_dir, filename)

        # 准备ECharts数据
        chart_dates = report_data['chart_data']['dates']
        chart_costs = report_data['chart_data']['costs']
        type_data = [{"name": k, "value": v} for k, v in report_data['cost_by_type'].items()]
        region_data = [{"name": k, "value": v} for k, v in report_data['cost_by_region'].items()]
        
        analysis = report_data['analysis']

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>CloudLens 成本分析报告 - {account}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .card {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .row {{ display: flex; gap: 20px; }}
        .col {{ flex: 1; }}
        h1, h2 {{ margin: 0 0 15px 0; color: #333; }}
        .stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }}
        .stat-item {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #1890ff; margin: 10px 0; }}
        .stat-label {{ color: #666; font-size: 14px; }}
        .trend-up {{ color: #cf1322; }}
        .trend-down {{ color: #3f8600; }}
        #trendChart, #typeChart, #regionChart {{ width: 100%; height: 400px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💰 CloudLens 成本分析报告</h1>
            <p>账号: <strong>{account}</strong> | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="card">
            <h2>📊 核心指标</h2>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-label">最新月成本</div>
                    <div class="stat-value">¥{analysis['latest_cost']:,.2f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">总变化</div>
                    <div class="stat-value {'trend-up' if analysis['total_change'] > 0 else 'trend-down'}">
                        {analysis['total_change']:+,.2f} ({analysis['total_change_pct']:+.1f}%)
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">平均成本</div>
                    <div class="stat-value">¥{analysis['avg_cost']:,.2f}</div>
                </div>
                 <div class="stat-item">
                    <div class="stat-label">预测趋势</div>
                    <div class="stat-value">{analysis['trend']}</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>📈 成本趋势 (30天)</h2>
            <div id="trendChart"></div>
        </div>

        <div class="row">
            <div class="col card">
                <h2>资源类型分布</h2>
                <div id="typeChart"></div>
            </div>
            <div class="col card">
                <h2>区域分布</h2>
                <div id="regionChart"></div>
            </div>
        </div>
    </div>

    <script>
        // 趋势图
        var trendChart = echarts.init(document.getElementById('trendChart'));
        trendChart.setOption({{
            tooltip: {{ trigger: 'axis' }},
            xAxis: {{ type: 'category', data: {json.dumps(chart_dates)} }},
            yAxis: {{ type: 'value', name: '成本 (CNY)' }},
            series: [{{
                data: {json.dumps(chart_costs)},
                type: 'line',
                smooth: true,
                areaStyle: {{ opacity: 0.1 }},
                itemStyle: {{ color: '#1890ff' }}
            }}]
        }});

        // 类型饼图
        var typeChart = echarts.init(document.getElementById('typeChart'));
        typeChart.setOption({{
            tooltip: {{ trigger: 'item' }},
            legend: {{ orient: 'vertical', left: 'left' }},
            series: [{{
                type: 'pie',
                radius: '70%',
                data: {json.dumps(type_data)},
                emphasis: {{ itemStyle: {{ shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }} }}
            }}]
        }});

        // 区域饼图
        var regionChart = echarts.init(document.getElementById('regionChart'));
        regionChart.setOption({{
            tooltip: {{ trigger: 'item' }},
            series: [{{
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: {{ borderRadius: 10, borderColor: '#fff', borderWidth: 2 }},
                label: {{ show: false, position: 'center' }},
                emphasis: {{ label: {{ show: true, fontSize: '20', fontWeight: 'bold' }} }},
                data: {json.dumps(region_data)}
            }}]
        }});

        window.onresize = function() {{
            trendChart.resize();
            typeChart.resize();
            regionChart.resize();
        }};
    </script>
</body>
</html>
        """
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        console.print(f"\n[bold green]✓ 成本分析报告已导出:[/bold green] {filepath}")
        if os.name == 'posix':
            os.system(f"open '{filepath}'")

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
    from cloudlens.core.tag_analyzer import TagAnalyzer
    from cloudlens.providers.aliyun.provider import AliyunProvider

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


@analyze.command("discount")
@click.option("--bill-dir", help="账单CSV目录路径")
@click.option("--months", default=6, type=int, help="分析月数")
@click.option("--export", is_flag=True, help="导出HTML报告")
@click.option("--format", type=click.Choice(["html", "json", "excel"]), default="html", help="报告格式")
@handle_exceptions
def analyze_discount(bill_dir, months, export, format):
    """折扣趋势分析 - 基于账单CSV分析最近6个月折扣变化"""
    from cloudlens.core.discount_analyzer import DiscountTrendAnalyzer
    from rich.panel import Panel
    
    console.print("[cyan]📊 分析账单折扣趋势...[/cyan]\n")
    
    analyzer = DiscountTrendAnalyzer()
    
    # 查找账单目录
    if bill_dir:
        bill_dirs = [Path(bill_dir)]
    else:
        bill_dirs = analyzer.find_bill_directories()
    
    if not bill_dirs:
        console.print("[red]❌ 未找到账单CSV目录[/red]")
        console.print("\n提示:")
        console.print("  1. 请从阿里云控制台下载账单CSV文件（消费明细）")
        console.print("  2. 将CSV文件放在以账号ID命名的目录中")
        console.print("  3. 或使用 --bill-dir 参数指定目录路径")
        return
    
    # 分析第一个目录（或指定目录）
    target_dir = bill_dirs[0]
    console.print(f"[cyan]📁 分析账单目录: {target_dir}[/cyan]\n")
    
    with Progress() as progress:
        task = progress.add_task("[cyan]解析账单数据...", total=None)
        result = analyzer.analyze_discount_trend(target_dir, months=months)
        progress.update(task, completed=100)
    
    if 'error' in result:
        console.print(f"[red]❌ 分析失败: {result['error']}[/red]")
        return
    
    # 显示核心指标
    trend = result['trend_analysis']
    
    console.print(Panel.fit(
        f"[bold cyan]分析账号:[/bold cyan] {result['account_name']}\n"
        f"[bold cyan]分析周期:[/bold cyan] {', '.join(result['analysis_periods'])}\n\n"
        f"[bold green]最新折扣率:[/bold green] {trend['latest_discount_rate']*100:.2f}%\n"
        f"[bold yellow]平均折扣率:[/bold yellow] {trend['average_discount_rate']*100:.2f}%\n"
        f"[bold blue]折扣率变化:[/bold blue] {trend['discount_rate_change_pct']:+.2f}% (vs 首月)\n"
        f"[bold magenta]趋势方向:[/bold magenta] {trend['trend_direction']}\n"
        f"[bold]累计节省:[/bold] ¥{trend['total_savings_6m']:,.2f}",
        title="💰 折扣趋势摘要"
    ))
    
    # 产品折扣TOP 10
    product_analysis = result['product_analysis']
    if product_analysis:
        console.print("\n[bold cyan]📦 产品折扣 TOP 10:[/bold cyan]")
        table = Table()
        table.add_column("产品", style="cyan")
        table.add_column("累计折扣", style="green", justify="right")
        table.add_column("平均折扣率", style="yellow", justify="right")
        table.add_column("趋势", style="magenta")
        
        for product, data in list(product_analysis.items())[:10]:
            trend_icon = "📈" if data['trend'] == '上升' else ("📉" if data['trend'] == '下降' else "➡️")
            table.add_row(
                product,
                f"¥{data['total_discount']:,.2f}",
                f"{data['avg_discount_rate']*100:.2f}%",
                f"{trend_icon} {data['trend']}"
            )
        
        console.print(table)
    
    # 合同折扣
    contract_analysis = result['contract_analysis']
    if contract_analysis:
        console.print("\n[bold cyan]📄 合同折扣 TOP 5:[/bold cyan]")
        for idx, (contract, data) in enumerate(list(contract_analysis.items())[:5], 1):
            console.print(f"  {idx}. [bold]{data['discount_name']}[/bold]")
            console.print(f"     合同: {contract}")
            console.print(f"     累计节省: ¥{data['total_discount']:,.2f}")
            console.print(f"     平均折扣率: {data['avg_discount_rate']*100:.2f}%")
    
    # 导出报告
    if export:
        console.print(f"\n[cyan]正在生成{format.upper()}报告...[/cyan]")
        report_path = analyzer.generate_discount_report(target_dir, output_format=format)
        console.print(f"[green]✅ 报告已生成: {report_path}[/green]")
        
        # 尝试打开报告
        if format == 'html':
            import os
            if os.name == 'posix':
                os.system(f"open '{report_path}'")
    
    console.print("\n[bold]💡 建议:[/bold]")
    console.print("  • 定期下载账单CSV文件以跟踪折扣变化")
    console.print("  • 关注折扣率下降的产品，及时与商务沟通续签")
    console.print("  • 使用 --export 导出详细报告供团队分享")


@analyze.command("security")
@click.option("--account", "-a", help="账号名称")
@click.option("--cis", is_flag=True, help="执行CIS Benchmark合规检查")
@click.option("--export", is_flag=True, help="导出HTML详细报告")
@handle_exceptions
def analyze_security(account, cis, export):
    """安全合规 - 检查公网暴露、安全组、CIS Benchmark等"""
    from cloudlens.core.cis_compliance import CISBenchmark
    from cloudlens.core.services.analysis_service import AnalysisService
    from cloudlens.providers.aliyun.provider import AliyunProvider
    from rich.table import Table
    from rich.panel import Panel
    import os
    from datetime import datetime

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

    # 获取所有区域
    all_regions = AnalysisService._get_all_regions(
        account_config.access_key_id,
        account_config.access_key_secret
    )
    
    all_instances = []
    all_rds = []
    all_redis = []
    all_slb = []
    all_nat = []

    # 获取资源
    with Progress() as progress:
        task = progress.add_task("[cyan]全区域资源扫描...", total=len(all_regions))
        for region in all_regions:
            try:
                region_provider = AliyunProvider(
                    account_name=account_config.name,
                    access_key=account_config.access_key_id,
                    secret_key=account_config.access_key_secret,
                    region=region,
                )
                
                # 快速检查
                if region_provider.check_instances_count() > 0:
                    all_instances.extend(region_provider.list_instances())
                
                all_rds.extend(region_provider.list_rds())
                all_redis.extend(region_provider.list_redis())
                
                if hasattr(region_provider, 'list_slb'):
                    all_slb.extend(region_provider.list_slb())
                if hasattr(region_provider, 'list_nat_gateways'):
                    all_nat.extend(region_provider.list_nat_gateways())
            except:
                pass
            progress.update(task, advance=1)

    all_resources = all_instances + all_rds + all_redis + all_slb + all_nat
    
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
        console.print("\n" + "=" * 80)
        console.print("[bold cyan]🛡️  CIS Benchmark 安全基线合规检查报告[/bold cyan]", justify="center")
        console.print("=" * 80 + "\n")
        
        # 生成检查说明
        console.print("[bold]📋 检查说明:[/bold]")
        console.print("基于 CIS (Center for Internet Security) 国际安全基准,对您的云环境进行全面安全")
        console.print("合规性检查。本次检查涵盖 5 大类别、40 个安全检查项,帮助您:")
        console.print("  • 发现安全隐患和配置缺陷")
        console.print("  • 提升整体安全合规水平")
        console.print("  • 降低数据泄露和攻击风险")
        console.print("  • 满足行业安全规范要求\n")
        
        checker = CISBenchmark()
        results = checker.run_all_checks(all_resources, provider)

        # ============ 第一部分: 总览 ============
        console.print("[bold cyan]📊 检查总览[/bold cyan]")
        console.print("─" * 80)
        
        score = results["compliance_score"]
        score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
        
        # 使用Panel显示总体评分
        from rich.panel import Panel
        score_panel = Panel.fit(
            f"[bold {score_color}]合规评分: {score}%[/bold {score_color}]\n"
            f"[green]✓ 通过: {results['passed']}项[/green]  "
            f"[red]✗ 失败: {results['failed']}项[/red]  "
            f"[dim]总计: {results['total_checks']}项[/dim]",
            title="[bold]总体评分[/bold]",
            border_style=score_color
        )
        console.print(score_panel)
        console.print("")

        # 分类统计表格
        console.print("[bold]各类别合规情况:[/bold]")
        summary_table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        summary_table.add_column("类别", style="cyan", width=15)
        summary_table.add_column("说明", style="white", width=30)
        summary_table.add_column("合规率", justify="right", width=10)
        summary_table.add_column("通过/总数", justify="right", width=12)
        summary_table.add_column("状态", justify="center", width=10)

        category_desc = {
            "IAM": "身份与访问管理",
            "Network": "网络安全配置",
            "Data": "数据安全保护",
            "Audit": "审计与监控",
            "Config": "配置管理规范"
        }
        
        for category, stats in results["summary"].items():
            rate = stats.get("compliance_rate", 0)
            rate_color = "green" if rate >= 80 else "yellow" if rate >= 60 else "red"
            status_icon = "✓" if rate >= 80 else "⚠" if rate >= 60 else "✗"
            
            summary_table.add_row(
                category,
                category_desc.get(category, ""),
                f"[{rate_color}]{rate:.1f}%[/{rate_color}]",
                f"{stats['passed']}/{stats['total']}",
                f"[{rate_color}]{status_icon}[/{rate_color}]"
            )

        console.print(summary_table)
        console.print("")

        # ============ 第二部分: 通过的检查项 ============
        passed_checks = [r for r in results["results"] if r["status"] == "PASS"]
        if passed_checks:
            console.print("\n[bold green]" + "=" * 80 + "[/bold green]")
            console.print(f"[bold green]✓ 通过的检查项 ({len(passed_checks)}项)[/bold green]")
            console.print("[bold green]" + "=" * 80 + "[/bold green]\n")
            console.print("[dim]以下检查项符合CIS安全基准要求,请继续保持:[/dim]\n")
            
            # 按类别分组显示
            from collections import defaultdict
            passed_by_category = defaultdict(list)
            for check in passed_checks:
                passed_by_category[check['category']].append(check)
            
            for category in ["IAM", "Network", "Data", "Audit", "Config"]:
                if category not in passed_by_category:
                    continue
                    
                checks = passed_by_category[category]
                console.print(f"[bold cyan]├─ {category_desc.get(category, category)} ({len(checks)}项)[/bold cyan]")
                
                for check in checks:
                    severity_color = {
                        "CRITICAL": "red",
                        "HIGH": "yellow", 
                        "MEDIUM": "blue",
                        "LOW": "white"
                    }.get(check["severity"], "white")
                    
                    console.print(
                        f"[green]│  ✓[/green] [{check['id']}] {check['title']} "
                        f"[{severity_color}][{check['severity']}][/{severity_color}]"
                    )
                    console.print(f"[dim]│     └─ {check['details']}[/dim]")
                console.print("")

        # ============ 第三部分: 未通过的检查项 ============
        failed_checks = [r for r in results["results"] if r["status"] == "FAIL"]
        if failed_checks:
            console.print("\n[bold red]" + "=" * 80 + "[/bold red]")
            console.print(f"[bold red]✗ 未通过的检查项 ({len(failed_checks)}项)[/bold red]")
            console.print("[bold red]" + "=" * 80 + "[/bold red]\n")
            console.print("[dim]以下检查项未达标,建议按优先级进行整改:[/dim]\n")
            
            # 按严重程度排序
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            failed_checks.sort(key=lambda x: severity_order.get(x["severity"], 4))
            
            for idx, check in enumerate(failed_checks, 1):
                severity_color = {
                    "CRITICAL": "red",
                    "HIGH": "yellow",
                    "MEDIUM": "blue",
                    "LOW": "white"
                }.get(check["severity"], "white")
                
                # 严重程度图标
                severity_icon = {
                    "CRITICAL": "🔴",
                    "HIGH": "🟡",
                    "MEDIUM": "🔵",
                    "LOW": "⚪"
                }.get(check["severity"], "⚪")
                
                console.print(
                    f"[{severity_color}]{severity_icon} [{idx}] [{check['id']}] {check['title']} "
                    f"[{check['severity']}][/{severity_color}]"
                )
                console.print(f"[dim]类别: {category_desc.get(check['category'], check['category'])}[/dim]")
                console.print(f"[yellow]原因:[/yellow] {check['details']}")
                
                # 显示修复建议
                if check.get("remediation"):
                    console.print(f"[cyan]修复建议:[/cyan]")
                    for line in check["remediation"].split('\n'):
                        if line.strip():
                            console.print(f"  {line}")
                
                console.print("")  # 空行分隔

        # ============ 第四部分: 改进建议 ============
        console.print("\n[bold cyan]" + "=" * 80 + "[/bold cyan]")
        console.print("[bold cyan]💡 综合改进建议[/bold cyan]")
        console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]\n")
        
        if score >= 80:
            console.print("[green]✓ 您的环境安全合规性良好![/green]")
            console.print("  建议: 继续保持现有安全措施,定期进行安全检查\n")
        elif score >= 60:
            console.print("[yellow]⚠ 您的环境存在一些安全隐患[/yellow]")
            console.print("  建议: 优先处理HIGH和CRITICAL级别的问题\n")
        else:
            console.print("[red]✗ 您的环境存在较多安全风险[/red]")
            console.print("  建议: 立即处理CRITICAL级别问题,制定整改计划\n")
        
        # 优先级建议
        critical_count = sum(1 for c in failed_checks if c["severity"] == "CRITICAL")
        high_count = sum(1 for c in failed_checks if c["severity"] == "HIGH")
        
        if critical_count > 0:
            console.print(f"[bold red]🔴 紧急 ({critical_count}项):[/bold red] 立即处理CRITICAL级别问题")
        if high_count > 0:
            console.print(f"[bold yellow]🟡 重要 ({high_count}项):[/bold yellow] 7天内处理HIGH级别问题")
        
        if export:
            # 导出HTML报告
            report_dir = os.path.expanduser("~/cloudlens_reports")
            os.makedirs(report_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"security_report_{account}_{timestamp}.html"
            filepath = os.path.join(report_dir, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>CloudLens 安全合规报告 - {account}</title>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; }}
                        h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
                        h2 {{ color: #34495e; margin-top: 30px; }}
                        .score-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid {score_color}; }}
                        .score {{ font-size: 24px; font-weight: bold; color: {score_color}; }}
                        .stats {{ display: flex; gap: 20px; margin-top: 10px; }}
                        .stat-item {{ background: white; padding: 10px 20px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                        th {{ background-color: #f8f9fa; }}
                        .status-pass {{ color: green; font-weight: bold; }}
                        .status-fail {{ color: red; font-weight: bold; }}
                        .severity-CRITICAL {{ color: red; font-weight: bold; }}
                        .severity-HIGH {{ color: #d35400; font-weight: bold; }}
                        .severity-MEDIUM {{ color: #f39c12; }}
                        .severity-LOW {{ color: #27ae60; }}
                        .pass-section {{ margin-top: 30px; }}
                        .fail-section {{ margin-top: 30px; }}
                        .check-item {{ margin-bottom: 15px; border: 1px solid #eee; padding: 15px; border-radius: 4px; }}
                        .check-pass {{ border-left: 4px solid green; }}
                        .check-fail {{ border-left: 4px solid red; }}
                        .remediation {{ background: #fcf8e3; padding: 10px; margin-top: 10px; border-radius: 4px; }}
                        pre {{ background: #f8f9fa; padding: 10px; overflow-x: auto; }}
                    </style>
                </head>
                <body>
                    <h1>🛡️ CloudLens 安全合规报告</h1>
                    <div class="score-card">
                        <div class="score">合规评分: {score}%</div>
                        <div class="stats">
                            <div class="stat-item">✅ 通过: {results['passed']}</div>
                            <div class="stat-item">❌ 失败: {results['failed']}</div>
                            <div class="stat-item">📊 总计: {results['total_checks']}</div>
                            <div class="stat-item">🕒 生成时间: {timestamp}</div>
                        </div>
                    </div>

                    <h2>📈 各类别合规情况</h2>
                    <table>
                        <thead><tr><th>类别</th><th>说明</th><th>合规率</th><th>通过/总数</th><th>状态</th></tr></thead>
                        <tbody>
                """)
                
                # 分类统计行
                for category, stats in results["summary"].items():
                    rate = stats.get("compliance_rate", 0)
                    status_class = "status-pass" if rate >= 80 else "status-fail"
                    f.write(f"""
                        <tr>
                            <td>{category}</td>
                            <td>{category_desc.get(category, "")}</td>
                            <td class="{status_class}">{rate:.1f}%</td>
                            <td>{stats['passed']}/{stats['total']}</td>
                            <td class="{status_class}">{'✓' if rate >= 80 else '⚠' if rate >= 60 else '✗'}</td>
                        </tr>
                    """)
                
                f.write("""
                        </tbody>
                    </table>

                    <h2 style="color: red;">❌ 未通过检查项 (建议优先修复)</h2>
                """)
                
                # 失败的检查项
                for check in failed_checks:
                    f.write(f"""
                    <div class="check-item check-fail">
                        <h3 class="severity-{check['severity']}">
                             [{check['severity']}] {check['id']} {check['title']}
                        </h3>
                        <p><strong>类别:</strong> {category_desc.get(check['category'], check['category'])}</p>
                        <p><strong>原因:</strong> {check['details']}</p>
                        <div class="remediation">
                            <strong>🔧 修复建议:</strong>
                            <pre>{check.get('remediation', '无修复建议')}</pre>
                        </div>
                    </div>
                    """)
                
                f.write("""
                    <h2 style="color: green;">✅ 通过检查项</h2>
                """)
                
                # 通过的检查项
                for check in passed_checks:
                    f.write(f"""
                    <div class="check-item check-pass">
                        <div>
                            <span class="severity-{check['severity']}">[{check['severity']}]</span>
                            <strong>{check['id']} {check['title']}</strong>
                        </div>
                        <div style="color: #666; margin-top: 5px;">└─ {check['details']}</div>
                    </div>
                    """)
                
                f.write("""
                </body>
                </html>
                """)
            
            console.print(f"\n[bold green]✓ 详细报告已导出:[/bold green] {filepath}")
            # 尝试自动打开
            if os.name == 'posix':
                os.system(f"open '{filepath}'")
        else:
            console.print(f"\n[dim]💾 完整报告已保存,运行 'cl analyze security --export' 可导出详细报告[/dim]")
        
        console.print("[dim]📅 建议每月运行一次安全检查,持续改进安全态势[/dim]")

    console.print("\n[bold]💡 建议: 定期运行安全检查,及时发现并修复安全隐患[/bold]")
