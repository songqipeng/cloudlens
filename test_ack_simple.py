#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACK 资源查询简化测试脚本
直接在脚本中填写密钥进行测试
"""

import json
from rich.console import Console
from rich.table import Table
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

console = Console()

# ==================== 在这里填写您的凭证 ====================
ACCESS_KEY_ID = "LTAI5tECY4ZKX9cQYnpJwS9b"
ACCESS_KEY_SECRET = ""  # 请填写您的 AccessKeySecret
# ==========================================================

# 要查询的区域列表
REGIONS = [
    'cn-hangzhou',
    'cn-shanghai',
    'cn-beijing',
    'cn-shenzhen',
]


def query_ack_clusters(region):
    """查询指定区域的 ACK 集群"""
    console.print(f"\n[cyan]正在查询区域: {region}[/cyan]")

    try:
        client = AcsClient(ACCESS_KEY_ID, ACCESS_KEY_SECRET, region)
        request = CommonRequest()
        request.set_domain(f"cs.{region}.aliyuncs.com")
        request.set_method("POST")
        request.set_version("2015-12-15")
        request.set_action_name("DescribeClusters")

        response = client.do_action_with_exception(request)
        data = json.loads(response)

        console.print(f"  响应数据类型: {type(data)}")

        clusters = []
        if isinstance(data, list):
            clusters = data
        elif isinstance(data, dict) and "clusters" in data:
            clusters = data["clusters"]

        if clusters:
            console.print(f"  [green]✓ 发现 {len(clusters)} 个集群[/green]")
        else:
            console.print(f"  [dim]- 无集群[/dim]")

        return clusters

    except Exception as e:
        error_msg = str(e)
        if "Forbidden" in error_msg or "AccessDenied" in error_msg:
            console.print(f"  [red]✗ 权限不足[/red]")
        elif "InvalidAccessKeyId" in error_msg:
            console.print(f"  [red]✗ AccessKeyId 无效[/red]")
        elif "SignatureDoesNotMatch" in error_msg:
            console.print(f"  [red]✗ AccessKeySecret 错误[/red]")
        else:
            console.print(f"  [red]✗ 查询失败: {error_msg}[/red]")

        return []


def main():
    """主函数"""
    console.print("[bold cyan]ACK 资源查询测试[/bold cyan]\n")

    # 验证凭证
    if not ACCESS_KEY_SECRET:
        console.print("[red]错误: 请在脚本中填写 ACCESS_KEY_SECRET[/red]")
        console.print("[yellow]编辑文件: test_ack_simple.py[/yellow]")
        console.print("[yellow]找到第 17 行，填写您的 AccessKeySecret[/yellow]")
        return

    console.print(f"[green]✓ AccessKeyId: {ACCESS_KEY_ID[:10]}...[/green]")
    console.print(f"[green]✓ AccessKeySecret: {'*' * 20}[/green]")

    # 查询所有区域
    all_clusters = []
    for region in REGIONS:
        clusters = query_ack_clusters(region)
        all_clusters.extend(clusters)

    # 显示结果
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]查询结果汇总[/bold cyan]")
    console.print("=" * 80)

    if not all_clusters:
        console.print("\n[yellow]未发现 ACK 集群[/yellow]")
        console.print("\n[cyan]可能的原因:[/cyan]")
        console.print("1. 账号下确实没有 ACK 集群")
        console.print("2. AccessKey 权限不足")
        console.print("3. AccessKeySecret 填写错误")
        return

    console.print(f"\n[green]✓ 总共发现 {len(all_clusters)} 个 ACK 集群[/green]\n")

    # 创建表格
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("集群 ID", style="cyan", width=30)
    table.add_column("集群名称", style="green")
    table.add_column("类型", style="yellow")
    table.add_column("状态", style="blue")
    table.add_column("区域", style="cyan")

    for cluster in all_clusters:
        cluster_id = cluster.get("cluster_id", "")
        name = cluster.get("name", "")
        cluster_type = cluster.get("cluster_type", "")
        state = cluster.get("state", "")
        region = cluster.get("region_id", "")

        table.add_row(cluster_id, name, cluster_type, state, region)

    console.print(table)

    # 打印第一个集群的详细信息
    console.print("\n[cyan]第一个集群的详细信息:[/cyan]")
    console.print(json.dumps(all_clusters[0], indent=2, ensure_ascii=False))

    # 后续排查建议
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]排查建议[/bold cyan]")
    console.print("=" * 80)
    console.print("\n[green]✓ API 能够成功查询到 ACK 集群[/green]")
    console.print("\n[yellow]前端显示不出的可能原因:[/yellow]")
    console.print("1. Web 后端服务未启动")
    console.print("2. 后端 API 区域过滤问题")
    console.print("3. 前端资源类型选择器未包含 'ack'")
    console.print("4. 数据字段映射问题")

    console.print("\n[cyan]下一步调试步骤:[/cyan]")
    console.print("1. 启动后端服务: cd web/backend && uvicorn main:app --reload")
    console.print("2. 测试 API: curl 'http://localhost:8000/api/resources?type=ack&account=ydzn'")
    console.print("3. 检查浏览器控制台 Network 标签")
    console.print("4. 查看后端日志输出")


if __name__ == "__main__":
    main()
