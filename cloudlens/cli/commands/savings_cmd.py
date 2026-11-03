# -*- coding: utf-8 -*-
"""省钱机会 / 框架合同 CLI"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich import box

from cloudlens.core.config import ConfigManager
from cloudlens.core.context import ContextManager
from cloudlens.core.error_handler import handle_exceptions

console = Console()


@click.group()
def savings():
    """省钱机会 - 框架合同与年化可省扫描"""
    pass


def _resolve_account(account: Optional[str]) -> str:
    cm = ConfigManager()
    ctx = ContextManager()
    name = account or ctx.get_last_account()
    if not name:
        raise click.ClickException("请指定账号: --account <name>（可用 cl config list）")
    if not cm.get_account(name):
        raise click.ClickException(f"账号不存在: {name}")
    return name


def _bill_account_id(account_name: str) -> str:
    cm = ConfigManager()
    acc = cm.get_account(account_name)
    assert acc is not None
    return f"{acc.access_key_id[:10]}-{account_name}"


@savings.command("scan")
@click.option("--account", "-a", help="账号名称")
@click.option("--billing-cycle", "-c", default=None, help="账期 YYYY-MM")
@click.option("--include-legacy/--no-legacy", default=True, help="是否合并旧优化缓存")
@click.option("--json-out", "json_out", is_flag=True, help="输出 JSON")
@handle_exceptions
def savings_scan(account, billing_cycle, include_legacy, json_out):
    """扫描省钱机会（框外 / 未按约 / 闲置 / 弱建议）"""
    from cloudlens.core.cache import CacheManager
    from cloudlens.core.framework_contract import SavingsOpportunityScanner
    from cloudlens.core.services.analysis_service import AnalysisService

    account_name = _resolve_account(account)
    console.print(f"[cyan]扫描省钱机会: {account_name}"
                  f"{f' @ {billing_cycle}' if billing_cycle else ''}...[/cyan]")

    idle_items = []
    try:
        cache = CacheManager(ttl_seconds=86400)
        cache_hit = False
        for key in ("dashboard_idle", "idle_result"):
            data = cache.get(resource_type=key, account_name=account_name)
            if isinstance(data, list):
                idle_items = data
                cache_hit = True
                break
        if not cache_hit:
            idle_items, _ = AnalysisService.analyze_idle_resources(
                account_name, days=7, force_refresh=False
            )
    except Exception as e:
        console.print(f"[yellow]闲置数据加载失败（继续扫描）: {e}[/yellow]")

    scanner = SavingsOpportunityScanner()
    result = scanner.scan(
        account_name=account_name,
        bill_account_id=_bill_account_id(account_name),
        idle_items=idle_items or [],
        billing_cycle=billing_cycle,
    )

    if include_legacy:
        try:
            cache = CacheManager(ttl_seconds=86400)
            legacy = cache.get(
                resource_type="optimization_suggestions", account_name=account_name
            )
            if isinstance(legacy, dict):
                ops = list(result.get("opportunities") or [])
                skip = {
                    "idle_resources",
                    "idle_low_util",
                    "framework_out_of_scope",
                    "framework_wrong_purchase",
                    "weak_subscription",
                }
                for s in legacy.get("suggestions") or []:
                    typ = s.get("type") or "legacy"
                    if typ in skip:
                        continue
                    monthly = float(s.get("savings_potential") or 0)
                    ops.append(
                        {
                            "type": typ,
                            "priority": s.get("priority") or "low",
                            "title": s.get("title") or typ,
                            "description": s.get("description") or "",
                            "annual_savings": round(monthly * 12, 2),
                        }
                    )
                result["opportunities"] = ops
                result["summary"]["annual_savings_total"] = round(
                    sum(float(o.get("annual_savings") or 0) for o in ops), 2
                )
                result["summary"]["total_opportunities"] = len(ops)
        except Exception as e:
            logger = __import__("logging").getLogger(__name__)
            logger.warning("合并旧优化建议失败: %s", e)
            console.print(f"[yellow]合并旧优化建议失败（已忽略）: {e}[/yellow]")

    if json_out:
        console.print_json(json.dumps(result, ensure_ascii=False, default=str))
        return

    contract = result.get("contract") or {}
    summary = result.get("summary") or {}
    console.print(
        f"合同: {'已配置' if contract.get('configured') else '未配置'} "
        f"{contract.get('contract_no') or contract.get('title') or ''}"
    )
    if summary.get("note"):
        console.print(f"[dim]{summary['note']}[/dim]")
    console.print(
        f"[green]年化可省合计: ¥{summary.get('annual_savings_total', 0):,.0f}[/green] "
        f"/ {summary.get('total_opportunities', 0)} 条"
    )

    table = Table(title="省钱机会 Top 30", box=box.SIMPLE_HEAVY)
    table.add_column("类型", style="cyan")
    table.add_column("优先级")
    table.add_column("标题")
    table.add_column("年化可省", justify="right", style="green")
    for o in (result.get("opportunities") or [])[:30]:
        table.add_row(
            str(o.get("type") or ""),
            str(o.get("priority") or ""),
            str(o.get("title") or "")[:48],
            f"¥{float(o.get('annual_savings') or 0):,.0f}",
        )
    console.print(table)


@savings.command("contracts")
@click.option("--account", "-a", help="账号名称")
@click.option("--billing-cycle", "-c", default=None, help="账期 YYYY-MM")
@handle_exceptions
def savings_contracts(account, billing_cycle):
    """列出框架合同"""
    from cloudlens.core.framework_contract import FrameworkContractStore

    account_name = _resolve_account(account)
    store = FrameworkContractStore()
    items = store.list_contracts(account_name)
    active = store.get_active_for_period(account_name, billing_cycle)

    table = Table(title=f"框架合同 · {account_name}", box=box.SIMPLE_HEAVY)
    table.add_column("ID")
    table.add_column("状态")
    table.add_column("标题")
    table.add_column("合同号")
    table.add_column("有效期")
    table.add_column("扫描用")
    for c in items:
        table.add_row(
            str(c.get("id") or "")[:12],
            str(c.get("status") or ""),
            str(c.get("title") or "")[:24],
            str(c.get("contract_no") or "")[:28],
            f"{(c.get('effective_from') or '?')[:10]}~{(c.get('effective_to') or '?')[:10]}",
            "✓" if active and active.get("id") == c.get("id") else "",
        )
    console.print(table)
    if not items:
        console.print("[yellow]暂无合同。可用 Web「导入 PDF」或 API /contracts/parse-pdf[/yellow]")


@savings.command("parse-pdf")
@click.option("--account", "-a", required=True, help="账号名称")
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--publish", is_flag=True, help="解析后直接发布为 active")
@handle_exceptions
def savings_parse_pdf(account, pdf_path, publish):
    """解析框架合同 PDF 为草稿（可选发布）"""
    from cloudlens.core.framework_contract import (
        FrameworkContractStore,
        parse_framework_contract_pdf,
    )

    account_name = _resolve_account(account)
    raw = Path(pdf_path).read_bytes()
    parsed = parse_framework_contract_pdf(raw)
    store = FrameworkContractStore()
    draft = store.create_draft_from_parse(
        account_name=account_name,
        parsed=parsed,
        pdf_bytes=raw,
        pdf_name=Path(pdf_path).name,
    )
    console.print(f"[green]已创建草稿[/green] id={draft.get('id')} no={draft.get('contract_no')}")
    for w in (parsed.get("warnings") or [])[:8]:
        console.print(f"[yellow]· {w}[/yellow]")
    if publish:
        rules = draft.get("rules") or {}
        if not (rules.get("products") or []):
            raise click.ClickException("规则无产品，无法发布；请先在 Web 补全")
        published = store.publish(draft["id"])
        console.print(f"[green]已发布[/green] id={published.get('id')}（其它 active 已归档）")
