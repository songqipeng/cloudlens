#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudLens CLI - 新版入口 (模块化架构)
"""
import click
import sys
import os

# 添加当前目录到 path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cli.commands.config_cmd import config
from cli.commands.query_cmd import query
from cli.commands.cache_cmd import cache
from cli.commands.misc_cmd import dashboard, repl, scheduler
from cli.commands.analyze_cmd import analyze
from cli.commands.remediate_cmd import remediate  # 新增


@click.group()
@click.version_option(version="2.1.0", prog_name="CloudLens CLI")
@click.pass_context
def cli(ctx):
    """
    CloudLens CLI - 多云资源治理工具
    
    \b
    🌐 统一视图 · 💰 智能分析 · 🔒 安全合规 · 📊 降本增效
    
    快速开始:
      cl config add                 # 添加云账号
      cl query ecs                  # 查询ECS实例
      cl analyze idle               # 分析闲置资源
      cl analyze forecast           # AI成本预测
      cl remediate tags             # 自动打标签
      cl dashboard                  # 打开仪表盘
    
    运行 'cl COMMAND --help' 查看具体命令的帮助信息
    """
    # 如果没有子命令，显示帮助信息
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# 注册命令组
cli.add_command(config)
cli.add_command(query)
cli.add_command(cache)
cli.add_command(analyze)
cli.add_command(remediate)  # 新增

# 注册单个命令
cli.add_command(dashboard)
cli.add_command(repl)
cli.add_command(scheduler)


# 为了兼容性，保留一些快捷别名
@cli.command('dash', hidden=True)
def dash_alias():
    """dashboard的快捷别名"""
    from cli.commands.misc_cmd import dashboard
    ctx = click.get_current_context()
    ctx.invoke(dashboard)


if __name__ == '__main__':
    cli()
