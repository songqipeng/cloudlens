#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudLens Interactive REPL
基于 prompt_toolkit + Rich 实现的交互式命令行界面
"""

import shlex
import subprocess
import sys
import time
from typing import List

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

import resource_modules  # 确保加载所有资源模块
from core.analyzer_registry import AnalyzerRegistry


class CloudLensREPL:
    def __init__(self):
        self.history_file = ".cloudlens_history"
        self.console = Console()
        self.style = Style.from_dict(
            {
                "prompt": "#00aa00 bold",
                "username": "#884444",
                "at": "#00aa00",
                "colon": "#0000aa",
                "pound": "#00aa00",
                "host": "#00ffff bg:#444400",
                "path": "ansicyan underline",
            }
        )
        self.completer = self._build_completer()
        self.session = PromptSession(
            history=FileHistory(self.history_file),
            auto_suggest=AutoSuggestFromHistory(),
            completer=self.completer,
            style=self.style,
        )

    def _build_completer(self) -> NestedCompleter:
        """构建命令补全器"""

        # 获取所有注册的资源类型
        analyzers = AnalyzerRegistry.list_analyzers()
        resource_types = {r: None for r in analyzers.keys()}

        common_options = {
            "--account": None,
            "--region": None,
            "--format": {"table", "json", "csv"},
            "--output": None,
            "--help": None,
            "--analysis": None,
            "-a": None,
        }

        query_completer = {r: common_options for r in resource_types}

        analyze_completer = {r: {"--days": None, "--account": None} for r in resource_types}

        # 添加一些特殊的 analyze 子命令
        analyze_completer.update(
            {
                "idle": None,
                "cost": None,
                "security": None,
                "renewal": None,
                "tags": None,
                "cru": None,
            }
        )

        return NestedCompleter.from_nested_dict(
            {
                "query": query_completer,
                "analyze": analyze_completer,
                "config": {"add": None, "list": None, "remove": None, "import": None},
                "report": {"generate": None, "history": None},
                "dashboard": None,
                "exit": None,
                "quit": None,
                "help": None,
                "clear": None,
            }
        )

    def start(self):
        """启动 REPL 循环"""
        self._print_banner()

        while True:
            try:
                text = self.session.prompt("cloudlens> ")
                text = text.strip()

                if not text:
                    continue

                if text in ("exit", "quit"):
                    self.console.print("[bold green]Bye! 👋[/bold green]")
                    break

                if text == "clear":
                    print("\033c", end="")
                    continue

                if text == "help":
                    self._print_help()
                    continue

                if text == "dashboard":
                    # 特殊处理 dashboard 命令，因为它是 TUI
                    self._launch_dashboard()
                    continue

                # 执行命令
                self._execute_command(text)

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[bold red]Error:[/bold red] {e}")

    def _print_banner(self):
        """打印启动 Banner"""
        banner_text = """
   ________                ____                 
  / ____/ /___  __  ______/ / /   ___  ____  _____
 / /   / / __ \/ / / / __  / /   / _ \/ __ \/ ___/
/ /___/ / /_/ / /_/ / /_/ / /___/  __/ / / (__  ) 
\____/_/\____/\__,_/\__,_/_____/\___/_/ /_/____/  
        """
        panel = Panel(
            f"[bold blue]{banner_text}[/bold blue]\n\n"
            "[bold white]Welcome to CloudLens Interactive Shell[/bold white]\n"
            "[dim]Type 'help' for available commands, 'exit' to quit.[/dim]",
            title="[bold green]v1.0.0[/bold green]",
            border_style="blue",
            box=box.ROUNDED,
        )
        self.console.print(panel)

    def _print_help(self):
        """打印帮助信息"""
        table = Table(title="Available Commands", box=box.SIMPLE)
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")

        table.add_row("query <resource>", "Query cloud resources (ecs, rds, etc.)")
        table.add_row("analyze <resource>", "Analyze resources for idle/cost/security")
        table.add_row("dashboard", "Launch TUI Dashboard (Experimental)")
        table.add_row("config", "Manage cloud accounts")
        table.add_row("report", "Generate and view reports")
        table.add_row("clear", "Clear screen")
        table.add_row("exit", "Exit shell")

        self.console.print(table)

    def _launch_dashboard(self):
        """启动 TUI Dashboard"""
        try:
            # 延迟导入以避免循环依赖或不必要的加载
            from core.dashboard import CloudLensApp

            app = CloudLensApp()
            app.run()
        except ImportError:
            self.console.print("[yellow]Textual not installed. Run 'pip install textual'[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Failed to launch dashboard: {e}[/red]")

    def _execute_command(self, command_str: str):
        """执行命令"""
        try:
            # 使用 subprocess 调用自身 main_cli.py
            args = shlex.split(command_str)
            cmd = [sys.executable, "main_cli.py"] + args

            # 记录开始时间
            start_time = time.time()

            # 执行
            result = subprocess.run(cmd)

            # 耗时统计
            duration = time.time() - start_time
            if result.returncode == 0:
                self.console.print(f"[dim]Done in {duration:.2f}s[/dim]")
            else:
                self.console.print(
                    f"[bold red]Command failed with code {result.returncode}[/bold red]"
                )

        except Exception as e:
            self.console.print(f"[bold red]Execution failed:[/bold red] {e}")


if __name__ == "__main__":
    repl = CloudLensREPL()
    repl.start()
