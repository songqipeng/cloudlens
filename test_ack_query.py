#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACK 资源查询测试脚本
用于排查前端显示不出 ACK 资源的问题
"""

import json
import sys
import keyring
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

console = Console()


def load_account_config():
    """加载账号配置"""
    import os

    try:
        with open('/Users/mac/.cloudlens/config.json', 'r') as f:
            config = json.load(f)

        if not config.get('accounts'):
            console.print("[red]错误: 配置文件中没有账号信息[/red]")
            sys.exit(1)

        account = config['accounts'][0]
        access_key_id = account['access_key_id']

        # 尝试多种方式获取密钥
        access_key_secret = None

        # 方法 1: 从环境变量获取
        access_key_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET')
        if access_key_secret:
            console.print("[green]✓ 从环境变量 ALIYUN_ACCESS_KEY_SECRET 获取密钥[/green]")

        # 方法 2: 从 keyring 获取
        if not access_key_secret:
            try:
                access_key_secret = keyring.get_password('cloudlens', f"{account['name']}_secret")
                if access_key_secret:
                    console.print("[green]✓ 从 keyring 获取密钥[/green]")
            except:
                pass

        # 方法 3: 从 .env 文件获取
        if not access_key_secret:
            env_file = '/Users/mac/.cloudlens/.env'
            if os.path.exists(env_file):
                try:
                    with open(env_file, 'r') as f:
                        for line in f:
                            if line.startswith('ALIYUN_ACCESS_KEY_SECRET='):
                                access_key_secret = line.split('=', 1)[1].strip().strip('"').strip("'")
                                console.print("[green]✓ 从 .env 文件获取密钥[/green]")
                                break
                except:
                    pass

        # 方法 4: 提示用户输入
        if not access_key_secret:
            console.print(f"\n[yellow]请输入账号 {account['name']} 的 AccessKeySecret:[/yellow]")
            console.print("[dim](密钥不会显示在屏幕上)[/dim]")
            from getpass import getpass
            access_key_secret = getpass("AccessKeySecret: ")

            if not access_key_secret:
                console.print("[red]错误: 未提供 AccessKeySecret[/red]")
                sys.exit(1)

        return {
            'name': account['name'],
            'access_key_id': access_key_id,
            'access_key_secret': access_key_secret,
            'region': account.get('region', 'cn-hangzhou')
        }

    except FileNotFoundError:
        console.print("[red]错误: 配置文件不存在 (/Users/mac/.cloudlens/config.json)[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]加载配置失败: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


def query_ack_clusters_in_region(access_key_id, access_key_secret, region):
    """查询指定区域的 ACK 集群"""
    try:
        client = AcsClient(access_key_id, access_key_secret, region)

        # 方法 1: 使用 DescribeClusters (POST)
        console.print(f"\n[cyan]方法 1: POST /clusters (DescribeClusters)[/cyan]")
        request = CommonRequest()
        request.set_domain(f"cs.{region}.aliyuncs.com")
        request.set_method("POST")
        request.set_version("2015-12-15")
        request.set_action_name("DescribeClusters")

        response = client.do_action_with_exception(request)
        data = json.loads(response)

        console.print(f"原始响应数据结构: {type(data)}")
        console.print(f"响应键: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")

        clusters_method1 = []
        if isinstance(data, list):
            clusters_method1 = data
        elif isinstance(data, dict) and "clusters" in data:
            clusters_method1 = data["clusters"]

        console.print(f"解析出的集群数量: {len(clusters_method1)}")

        # 方法 2: 使用 GET /clusters
        console.print(f"\n[cyan]方法 2: GET /clusters[/cyan]")
        request2 = CommonRequest()
        request2.set_domain(f"cs.{region}.aliyuncs.com")
        request2.set_method("GET")
        request2.set_version("2015-12-15")
        request2.set_uri_pattern("/clusters")

        try:
            response2 = client.do_action_with_exception(request2)
            data2 = json.loads(response2)

            console.print(f"原始响应数据结构: {type(data2)}")

            clusters_method2 = []
            if isinstance(data2, list):
                clusters_method2 = data2
            elif isinstance(data2, dict) and "clusters" in data2:
                clusters_method2 = data2["clusters"]

            console.print(f"解析出的集群数量: {len(clusters_method2)}")
        except Exception as e:
            console.print(f"[yellow]方法 2 失败: {e}[/yellow]")
            clusters_method2 = []

        # 返回更多数据的方法
        clusters = clusters_method1 if len(clusters_method1) >= len(clusters_method2) else clusters_method2

        return clusters, data

    except Exception as e:
        error_msg = str(e)

        if "Forbidden" in error_msg or "AccessDenied" in error_msg:
            console.print(f"[red]✗ 权限不足: 无法访问 ACK API[/red]")
            console.print(f"[yellow]需要的权限: AliyunCSReadOnlyAccess 或 AliyunCSFullAccess[/yellow]")
        elif "InvalidAction" in error_msg:
            console.print(f"[yellow]API 不支持此操作[/yellow]")
        else:
            console.print(f"[red]查询失败: {error_msg}[/red]")

        import traceback
        console.print(f"\n[dim]详细错误信息:[/dim]")
        console.print(traceback.format_exc())

        return [], None


def display_cluster_info(clusters):
    """展示集群信息"""
    if not clusters:
        console.print("\n[yellow]未发现 ACK 集群[/yellow]")
        return

    console.print(f"\n[green]✓ 发现 {len(clusters)} 个 ACK 集群[/green]\n")

    # 创建表格
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("集群 ID", style="cyan")
    table.add_column("集群名称", style="green")
    table.add_column("类型", style="yellow")
    table.add_column("状态", style="blue")
    table.add_column("K8s 版本", style="magenta")
    table.add_column("节点数", style="red")
    table.add_column("区域", style="cyan")

    for cluster in clusters:
        cluster_id = cluster.get("cluster_id") or cluster.get("ClusterId", "")
        name = cluster.get("name") or cluster.get("Name", "")
        cluster_type = cluster.get("cluster_type") or cluster.get("ClusterType", "")
        state = cluster.get("state") or cluster.get("State", "")
        version = cluster.get("current_version") or cluster.get("KubernetesVersion", "")
        size = cluster.get("size") or cluster.get("NodeCount", 0)
        region = cluster.get("region_id") or cluster.get("RegionId", "")

        table.add_row(
            cluster_id,
            name,
            cluster_type,
            state,
            str(version),
            str(size),
            region
        )

    console.print(table)

    # 打印第一个集群的原始数据结构
    console.print("\n[cyan]第一个集群的原始数据结构:[/cyan]")
    console.print(json.dumps(clusters[0], indent=2, ensure_ascii=False))


def test_api_resources_endpoint(account_name):
    """测试 Web API 端点"""
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]测试 Web API 端点[/bold cyan]")
    console.print("=" * 80)

    import requests

    # 假设后端运行在 8000 端口
    api_url = "http://localhost:8000/api/resources"

    console.print(f"\n[cyan]请求 URL: {api_url}[/cyan]")
    console.print(f"[cyan]参数: type=ack, account={account_name}[/cyan]")

    try:
        response = requests.get(
            api_url,
            params={
                "type": "ack",
                "account": account_name,
                "page": 1,
                "pageSize": 100
            },
            timeout=30
        )

        console.print(f"\n[green]响应状态码: {response.status_code}[/green]")

        if response.status_code == 200:
            data = response.json()
            console.print(f"响应数据结构: {list(data.keys())}")

            resources = data.get("resources", [])
            total = data.get("total", 0)

            console.print(f"[green]✓ 返回资源数量: {total}[/green]")

            if resources:
                console.print("\n[cyan]返回的资源列表:[/cyan]")
                for i, resource in enumerate(resources[:3], 1):
                    console.print(f"\n资源 {i}:")
                    console.print(json.dumps(resource, indent=2, ensure_ascii=False))
            else:
                console.print("[yellow]⚠ API 返回空列表[/yellow]")
        else:
            console.print(f"[red]✗ API 请求失败[/red]")
            console.print(f"响应内容: {response.text}")

    except requests.exceptions.ConnectionError:
        console.print("[red]✗ 无法连接到后端服务 (http://localhost:8000)[/red]")
        console.print("[yellow]提示: 请确保后端服务正在运行[/yellow]")
        console.print("[yellow]启动命令: cd web/backend && uvicorn main:app --reload[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ API 测试失败: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())


def main():
    """主函数"""
    console.print(Panel.fit(
        "[bold cyan]ACK 资源查询测试脚本[/bold cyan]\n"
        "用于排查前端显示不出 ACK 资源的问题",
        border_style="cyan"
    ))

    # 加载配置
    console.print("\n[bold]步骤 1: 加载账号配置[/bold]")
    account = load_account_config()
    console.print(f"[green]✓ 账号: {account['name']}[/green]")
    console.print(f"[green]✓ AccessKeyId: {account['access_key_id'][:10]}...[/green]")
    console.print(f"[green]✓ 默认区域: {account['region']}[/green]")

    # 查询所有区域
    regions = [
        'cn-hangzhou',
        'cn-shanghai',
        'cn-beijing',
        'cn-shenzhen',
        'cn-qingdao',
        'cn-zhangjiakou',
        'cn-huhehaote'
    ]

    console.print(f"\n[bold]步骤 2: 查询 ACK 集群 (共 {len(regions)} 个区域)[/bold]")

    all_clusters = []
    raw_responses = {}

    for region in regions:
        console.print(f"\n[cyan]正在查询区域: {region}[/cyan]")
        clusters, raw_data = query_ack_clusters_in_region(
            account['access_key_id'],
            account['access_key_secret'],
            region
        )

        if clusters:
            console.print(f"[green]✓ 发现 {len(clusters)} 个集群[/green]")
            all_clusters.extend(clusters)
            raw_responses[region] = raw_data
        else:
            console.print(f"[dim]- 无集群[/dim]")

    # 显示结果
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]查询结果汇总[/bold cyan]")
    console.print("=" * 80)

    display_cluster_info(all_clusters)

    # 测试 Web API
    if all_clusters:
        test_api_resources_endpoint(account['name'])

    # 诊断建议
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]诊断建议[/bold cyan]")
    console.print("=" * 80)

    if not all_clusters:
        console.print("\n[yellow]可能的原因:[/yellow]")
        console.print("1. 账号下确实没有 ACK 集群")
        console.print("2. AccessKey 权限不足，需要 AliyunCSReadOnlyAccess")
        console.print("3. API 端点或版本不正确")
        console.print("\n[cyan]建议操作:[/cyan]")
        console.print("1. 登录阿里云控制台确认是否有 ACK 集群")
        console.print("2. 检查 RAM 用户权限策略")
    else:
        console.print("\n[green]✓ 能够成功查询到 ACK 集群[/green]")
        console.print("\n[yellow]前端显示不出的可能原因:[/yellow]")
        console.print("1. Web 后端 API 查询逻辑问题")
        console.print("2. 前端资源类型过滤问题")
        console.print("3. 前端-后端数据字段映射问题")
        console.print("4. 区域过滤导致集群被排除")

        console.print("\n[cyan]下一步调试:[/cyan]")
        console.print("1. 检查后端日志: web/backend/logs/")
        console.print("2. 检查浏览器控制台 Network 标签")
        console.print("3. 确认前端资源类型下拉框是否包含 'ack'")
        console.print("4. 测试 API 端点: curl http://localhost:8000/api/resources?type=ack&account=ydzn")


if __name__ == "__main__":
    main()
