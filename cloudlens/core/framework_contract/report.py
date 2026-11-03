# -*- coding: utf-8 -*-
"""省钱机会 HTML 报告生成"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any, Dict, List


TYPE_LABELS = {
    "framework_out_of_scope": "框外产品",
    "framework_wrong_purchase": "未按约采购",
    "idle_low_util": "低利用率",
    "weak_subscription": "弱建议·转包年",
}


def render_savings_report_html(
    account: str,
    payload: Dict[str, Any],
) -> str:
    """生成结构化易读 HTML 报告。"""
    contract = payload.get("contract") or {}
    summary = payload.get("summary") or {}
    ops: List[Dict[str, Any]] = payload.get("opportunities") or []
    by_type = summary.get("by_type_annual_savings") or {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    def esc(x: Any) -> str:
        return html.escape("" if x is None else str(x))

    def yen(n: Any) -> str:
        try:
            return f"¥{int(round(float(n))):,}"
        except Exception:
            return "—"

    rows = []
    for o in ops:
        rows.append(
            f"""<tr>
            <td><span class="tag">{esc(TYPE_LABELS.get(o.get('type'), o.get('type')))}</span></td>
            <td>{esc(o.get('priority'))}</td>
            <td>{esc(o.get('title'))}</td>
            <td class="num">{yen(o.get('annual_savings'))}</td>
            <td>{esc(o.get('description'))}</td>
            <td>{esc(o.get('recommendation'))}</td>
            </tr>"""
        )

    configured = "是" if contract.get("configured") else "否"
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>省钱机会报告 · {esc(account)}</title>
<style>
body{{font-family:"PingFang SC","Microsoft YaHei",sans-serif;background:#f1f5f9;color:#0f172a;margin:0;padding:24px;font-size:14px}}
.wrap{{max-width:1080px;margin:0 auto}}
.hero{{background:linear-gradient(135deg,#0f172a,#1e3a5f 55%,#0f766e);color:#fff;border-radius:14px;padding:28px 32px;margin-bottom:18px}}
.hero h1{{margin:6px 0 8px;font-size:24px}}
.meta{{opacity:.85;font-size:12px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}}
.kpi{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px}}
.kpi .v{{font-size:22px;font-weight:700;color:#0f766e}}
.kpi .l{{font-size:12px;color:#64748b}}
section{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px 20px;margin-bottom:14px}}
h2{{margin:0 0 10px;font-size:16px;color:#1e3a5f}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th,td{{border-bottom:1px solid #e2e8f0;padding:8px 6px;text-align:left;vertical-align:top}}
th{{background:#f8fafc;color:#64748b}}
.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.tag{{display:inline-block;padding:2px 8px;border-radius:999px;background:#ecfdf5;color:#047857;font-size:11px}}
.note{{color:#64748b;font-size:12px}}
@media print{{body{{background:#fff}} .hero{{box-shadow:none}}}}
</style></head><body><div class="wrap">
<header class="hero">
  <div class="meta">CloudLens · 省钱机会报告</div>
  <h1>账号 {esc(account)}</h1>
  <div class="meta">生成 {esc(now)} · 合同已配置：{configured}
  · {esc(contract.get('title') or '')} {esc(contract.get('contract_no') or '')}
  · 有效期 {esc(contract.get('effective_from') or '—')} ~ {esc(contract.get('effective_to') or '—')}
  </div>
</header>
<div class="grid">
  <div class="kpi"><div class="l">年化可省合计</div><div class="v">{yen(summary.get('annual_savings_total'))}</div></div>
  <div class="kpi"><div class="l">框外 + 未按约</div><div class="v">{yen((by_type.get('framework_out_of_scope') or 0)+(by_type.get('framework_wrong_purchase') or 0))}</div></div>
  <div class="kpi"><div class="l">低利用率</div><div class="v">{yen(by_type.get('idle_low_util') or 0)}</div></div>
</div>
<section>
  <h2>说明</h2>
  <p class="note">{esc(summary.get('note') or '金额为年化可省估算；类型间可能重叠。')}</p>
  <p class="note">框架资格与账单折扣已拆开计算：未按约/框外看合同规则；利用率按规格粗估。</p>
</section>
<section>
  <h2>机会清单（{len(ops)}）</h2>
  <table>
    <thead><tr><th>类型</th><th>优先级</th><th>标题</th><th class="num">年化可省</th><th>原因</th><th>建议</th></tr></thead>
    <tbody>
    {''.join(rows) if rows else '<tr><td colspan="6">暂无机会</td></tr>'}
    </tbody>
  </table>
</section>
</div></body></html>"""
