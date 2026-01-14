# -*- coding: utf-8 -*-
"""
Dashboard和其他子命令
"""
import click
from rich.console import Console

console = Console()


@click.command()
def dashboard():
    """
    启动TUI仪表板

    交互式资源监控界面，支持：
    - 实时资源查看
    - 树形导航
    - 快捷键操作

    快捷键:
        q - 退出
        r - 刷新
    """
    try:
        from cloudlens.core.dashboard import CloudLensApp

        console.print("[cyan]正在启动CloudLens仪表板...[/cyan]")
        console.print("[dim]提示: 按 'q' 退出, 按 'r' 刷新[/dim]\n")

        app = CloudLensApp()
        app.run()

    except ImportError as e:
        console.print(f"[red]错误: 无法加载仪表板模块 - {e}[/red]")
        console.print("[yellow]提示: 请确保已安装 textual 库[/yellow]")
    except Exception as e:
        console.print(f"[red]仪表板启动失败: {e}[/red]")


@click.command()
def repl():
    """
    启动交互式REPL模式

    提供类似IPython的交互式命令行界面
    """
    try:
        from cloudlens.core.repl import CloudLensREPL

        console.print("[cyan]正在启动CloudLens REPL...[/cyan]")
        console.print("[dim]提示: 输入 'help' 查看帮助, 输入 'exit' 退出[/dim]\n")

        repl = CloudLensREPL()
        repl.run()

    except ImportError:
        console.print("[red]错误: 无法加载REPL模块[/red]")
    except Exception as e:
        console.print(f"[red]REPL启动失败: {e}[/red]")


@click.command()
@click.option("--config", help="调度配置文件路径", default="schedules.yaml")
def scheduler(config):
    """
    启动任务调度器

    根据 schedules.yaml 配置定时执行任务
    """
    try:
        from cloudlens.core.scheduler import TaskScheduler

        console.print(f"[cyan]正在启动调度器（配置: {config}）...[/cyan]")
        console.print("[dim]提示: 按 Ctrl+C 停止[/dim]\n")

        scheduler = TaskScheduler(config)
        scheduler.start()

    except FileNotFoundError:
        console.print(f"[red]错误: 配置文件 {config} 不存在[/red]")
        console.print(f"[yellow]提示: 请参考 schedules.yaml.example 创建配置文件[/yellow]")
    except KeyboardInterrupt:
        console.print("\n[yellow]调度器已停止[/yellow]")
    except Exception as e:
        console.print(f"[red]调度器启动失败: {e}[/red]")
