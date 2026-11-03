#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出成本行动清单：折扣差 + 低利用率降配（可读 Excel）

用法:
  python scripts/export_cost_action_lists.py --account cf
  # 本地 JSON:
  python scripts/export_cost_action_lists.py --account cf \\
    --opts-json /tmp/opts.json --products-json /tmp/products.json --idle-json /tmp/idle2.json
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPCookieProcessor
from http.cookiejar import CookieJar

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:  # pragma: no cover
    Workbook = None  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("export_cost_action_lists")

DEFAULT_USER = "admin"
DEFAULT_PASSWORD = "CloudLensAdmin2024!"

# 与优化建议算法一致：假设转包年可额外拿到约 13 个百分点折扣
ASSUMED_RATE_LIFT = 0.13

# 配色
C_NAVY = "1B3A5C"
C_TEAL = "0F766E"
C_AMBER = "B45309"
C_RED = "B91C1C"
C_SLATE = "334155"
C_MUTED = "64748B"
C_BG_HEADER = "1B3A5C"
C_BG_KPI = "F0FDFA"
C_BG_WARN = "FFFBEB"
C_BG_P1 = "FEF2F2"
C_BG_P2 = "FFFBEB"
C_BG_ALT = "F8FAFC"
C_BG_TITLE = "0F172A"
C_BORDER = "E2E8F0"
C_GREEN = "047857"


def estimate_monthly_cost_from_spec(spec: str, resource_type: str = "ecs") -> float:
    """与 web/backend/api/v1/resources.py 保持一致的粗估月费（目录价量级，偏上限）"""
    cost_map = {
        "ecs.t5-lc1m1.small": 50,
        "ecs.t5-lc1m2.small": 80,
        "ecs.g6.large": 400,
        "ecs.g6.xlarge": 800,
        "rds.mysql.s1.small": 200,
        "rds.mysql.s2.large": 500,
        "redis.master.small.default": 150,
        "redis.master.mid.default": 300,
    }
    if spec in cost_map:
        return float(cost_map[spec])
    if resource_type == "ecs" and isinstance(spec, str) and spec.startswith("ecs."):
        parts = spec.split(".")
        if len(parts) >= 3:
            size = parts[-1].lower()
            size_mul = 1.0
            if size == "small":
                size_mul = 0.25
            elif size == "medium":
                size_mul = 0.5
            elif size == "large":
                size_mul = 1.0
            elif size == "xlarge":
                size_mul = 2.0
            else:
                m = re.match(r"^(\d+)xlarge$", size)
                if m:
                    size_mul = max(1.0, float(m.group(1)) * 2.0)
            return round(320.0 * size_mul, 2)
    return 300.0 if resource_type == "ecs" else (400.0 if resource_type == "rds" else 200.0)


def downsize_hint(spec: str, metrics: Dict[str, Any]) -> Tuple[str, float, str]:
    """返回 (降配说明, 粗估月省, 风险提示)"""
    cpu = metrics.get("avg_cpu")
    mem = metrics.get("avg_memory")
    monthly = estimate_monthly_cost_from_spec(spec or "", "ecs")
    risk = ""
    if mem is not None and mem >= 70:
        risk = "内存偏高，不宜只按 CPU 降配"
        ratio = 0.15
        hint = "CPU 低但内存高：优先换同代内存型更小档，或拆业务后再降"
    elif cpu is not None and cpu < 1 and (mem is None or mem < 50):
        ratio = 0.45
        hint = "CPU 极低，可评估降 1~2 档或合并后释放"
    elif cpu is not None and cpu < 5:
        ratio = 0.30
        hint = "CPU 很低，优先降 1 档（如 2xlarge→xlarge）"
    else:
        ratio = 0.20
        hint = "低利用率，评估降 1 档"
    return hint, round(monthly * ratio, 2), risk


class ApiClient:
    def __init__(self, base: str, username: str, password: str):
        self.base = base.rstrip("/")
        self.cj = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cj))
        self._login(username, password)

    def _login(self, username: str, password: str) -> None:
        body = json.dumps({"username": username, "password": password}).encode()
        last_err: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                req = Request(
                    f"{self.base}/api/auth/login",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.opener.open(req, timeout=30) as resp:
                    if resp.status >= 400:
                        raise RuntimeError(f"登录失败 HTTP {resp.status}")
                logger.info("已登录 %s", self.base)
                return
            except Exception as e:  # noqa: BLE001
                last_err = e
                logger.warning("登录重试 %s/3: %s", attempt, e)
                import time

                time.sleep(1.5 * attempt)
        raise RuntimeError(f"登录失败: {last_err}")

    def get_json(self, path: str) -> Any:
        req = Request(f"{self.base}{path}", method="GET")
        try:
            with self.opener.open(req, timeout=120) as resp:
                return json.load(resp)
        except HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")[:300]
            raise RuntimeError(f"GET {path} -> HTTP {e.code}: {detail}") from e
        except URLError as e:
            raise RuntimeError(f"GET {path} 网络错误: {e}") from e


def _money(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def build_discount_rows(suggestions: List[Dict], products: List[Dict]) -> List[Dict]:
    """实例级折扣行动行（修正月均 = 区间总花费 / 运行月数）"""
    rows: List[Dict] = []
    for s in sorted(suggestions, key=lambda x: -float(x.get("annual_potential_savings") or 0)):
        rate = float(s.get("current_discount_rate") or 0)
        months = int(s.get("running_months") or 0) or 1
        total = float(s.get("total_cost") or 0)
        # API 的 avg_monthly_cost 常是日明细 AVG，不可用；用总花费/月数
        monthly = total / months
        window_save = float(s.get("annual_potential_savings") or 0)  # 实为窗口期×固定 lift
        # 年化：按月均 ×12 × lift
        lift = float(s.get("estimated_subscription_rate") or 0) - rate
        if lift <= 0:
            lift = ASSUMED_RATE_LIFT
        annualized = monthly * 12 * lift

        if rate < 0.05 and monthly >= 200:
            cross = "高花费·几乎无折扣"
            priority = "P1"
        elif rate < 0.05 and monthly >= 50:
            cross = "中花费·几乎无折扣"
            priority = "P1" if annualized >= 400 else "P2"
        elif rate < 0.05:
            cross = "几乎无折扣"
            priority = "P1" if annualized >= 500 else "P2"
        elif rate < 0.15 and monthly >= 100:
            cross = "花费高且折扣偏低"
            priority = "P2"
        else:
            cross = ""
            priority = "P2"

        rows.append(
            {
                "优先级": priority,
                "标记": cross,
                "产品": s.get("product_name") or "",
                "实例ID": s.get("instance_id") or "",
                "区域": s.get("region_name") or s.get("region") or "",
                "运行月数": months,
                "分析窗口": f"{s.get('first_month') or ''} ~ {s.get('last_month') or ''}",
                "窗口总花费¥": round(total, 2),
                "真实月均¥": round(monthly, 2),
                "当前折扣%": round(rate * 100, 1),
                "假设包年折扣%": round(float(s.get("estimated_subscription_rate") or rate + ASSUMED_RATE_LIFT) * 100, 1),
                "窗口期可省¥": round(window_save, 2),
                "年化可省¥": round(annualized, 2),
                "建议": "评估转包年包月 / 企业折扣 / 预留",
            }
        )
    return rows


def build_product_opportunity_rows(products: List[Dict]) -> List[Dict]:
    """产品级机会：高消费低折扣（补实例清单盲区）"""
    rows: List[Dict] = []
    for p in sorted(products, key=lambda x: -float(x.get("total_consumption") or 0)):
        rate = float(p.get("avg_discount_rate") or 0)
        spend = float(p.get("total_consumption") or 0)
        if spend < 2000:
            continue
        trends = p.get("trends") or []
        n_months = len(trends) if trends else 12
        monthly = spend / max(n_months, 1)
        # 机会：若折扣能提到 max(当前+13%, 行业常见 20%)，相对现状的空间
        # 已有 ≥20% 折扣的大盘（如 ECS 包年）边际空间小，不进「谈价机会」
        if rate >= 0.20:
            continue
        target = min(max(rate + ASSUMED_RATE_LIFT, 0.20), 0.70)
        lift = max(0.0, target - rate)
        if lift < 0.05:
            continue
        window_opp = spend * lift
        annual_opp = monthly * 12 * lift
        if annual_opp < 200:
            continue
        if rate < 0.05:
            note = "窗口内几乎无账单折扣，优先谈企业折扣/包年/预留"
        elif rate < 0.15:
            note = "折扣偏低，核对是否该走预留或包年"
        else:
            note = "仍有一定谈价/预留空间"
        rows.append(
            {
                "优先级": "P1" if annual_opp >= 3000 or (rate < 0.05 and spend >= 10000) else "P2",
                "产品": p.get("product_name") or "",
                "窗口消费¥": round(spend, 2),
                "覆盖月数": n_months,
                "月均消费¥": round(monthly, 2),
                "平均折扣%": round(rate * 100, 1),
                "目标折扣%": round(target * 100, 1),
                "窗口机会¥": round(window_opp, 2),
                "年化机会¥": round(annual_opp, 2),
                "说明": note,
            }
        )
    return rows


def build_idle_rows(idle_items: List[Dict]) -> List[Dict]:
    rows: List[Dict] = []
    for item in idle_items:
        metrics = item.get("metrics") or {}
        spec = item.get("spec") or ""
        monthly = estimate_monthly_cost_from_spec(spec, "ecs")
        hint, save_mo, risk = downsize_hint(spec, metrics)
        reasons = item.get("reasons") or []
        if isinstance(reasons, list):
            reason_text = "；".join(str(r) for r in reasons)
        else:
            reason_text = str(item.get("reason") or "")
        rows.append(
            {
                "优先级": item.get("priority") or "",
                "等级": item.get("level_label") or item.get("level") or "",
                "名称": item.get("name") or "",
                "实例ID": item.get("instance_id") or item.get("id") or "",
                "区域": item.get("region") or "",
                "规格": spec,
                "计费": item.get("charge_type") or "",
                "CPU%": round(float(metrics["avg_cpu"]), 2) if metrics.get("avg_cpu") is not None else None,
                "内存%": round(float(metrics["avg_memory"]), 2) if metrics.get("avg_memory") is not None else None,
                "闲置原因": reason_text,
                "规格粗估月费¥": monthly,
                "粗估月省¥": save_mo,
                "粗估年省¥": round(save_mo * 12, 2),
                "降配建议": hint,
                "风险": risk,
            }
        )
    rows.sort(key=lambda r: (-float(r.get("粗估年省¥") or 0), r.get("优先级") or "P9"))
    return rows


def write_csv(path: Path, rows: List[Dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _thin() -> Border:
    s = Side(style="thin", color=C_BORDER)
    return Border(left=s, right=s, top=s, bottom=s)


def _fill(hex_color: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex_color)


def _set_col_widths(ws, widths: Dict[str, float]) -> None:
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def _style_table_header(ws, row: int, start_col: int, end_col: int) -> None:
    for col in range(start_col, end_col + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = _fill(C_BG_HEADER)
        cell.font = Font(name="Microsoft YaHei", color="FFFFFF", bold=True, size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _thin()
    ws.row_dimensions[row].height = 28


def _style_data_row(
    ws,
    row: int,
    start_col: int,
    end_col: int,
    *,
    priority: Optional[str] = None,
    alt: bool = False,
    money_cols: Optional[List[int]] = None,
    pct_cols: Optional[List[int]] = None,
) -> None:
    bg = None
    if priority == "P1":
        bg = C_BG_P1
    elif priority == "P2":
        bg = C_BG_P2
    elif alt:
        bg = C_BG_ALT
    money_cols = money_cols or []
    pct_cols = pct_cols or []
    for col in range(start_col, end_col + 1):
        cell = ws.cell(row=row, column=col)
        cell.border = _thin()
        cell.font = Font(name="Microsoft YaHei", size=10, color=C_SLATE)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        if bg:
            cell.fill = _fill(bg)
        if col in money_cols and isinstance(cell.value, (int, float)):
            cell.number_format = '¥#,##0.00'
            cell.alignment = Alignment(horizontal="right", vertical="center")
        if col in pct_cols and isinstance(cell.value, (int, float)):
            cell.number_format = '0.0"%"'
            cell.alignment = Alignment(horizontal="right", vertical="center")
        if col == start_col and priority == "P1":
            cell.font = Font(name="Microsoft YaHei", size=10, color=C_RED, bold=True)
        elif col == start_col and priority == "P2":
            cell.font = Font(name="Microsoft YaHei", size=10, color=C_AMBER, bold=True)


def write_excel(
    path: Path,
    discount_rows: List[Dict],
    product_rows: List[Dict],
    idle_rows: List[Dict],
    summary: Dict[str, Any],
) -> None:
    if Workbook is None:
        raise RuntimeError("需要 openpyxl：pip install openpyxl")

    wb = Workbook()

    # ========== 1. 总览 ==========
    ws = wb.active
    ws.title = "总览"
    ws.sheet_view.showGridLines = False
    _set_col_widths(ws, {"A": 3, "B": 22, "C": 18, "D": 18, "E": 18, "F": 18, "G": 42})

    ws.merge_cells("B2:G2")
    title = ws["B2"]
    title.value = "CloudLens 成本行动清单"
    title.font = Font(name="Microsoft YaHei", size=22, bold=True, color=C_BG_TITLE)
    title.alignment = Alignment(vertical="center")
    ws.row_dimensions[2].height = 36

    ws.merge_cells("B3:G3")
    ws["B3"].value = (
        f"账号 {summary['account']}  ·  生成于 {summary['generated_at']}  ·  "
        f"账单窗口合计约 ¥{summary['bill_window_total']:,.0f}"
    )
    ws["B3"].font = Font(name="Microsoft YaHei", size=11, color=C_MUTED)

    # KPI 区
    kpis = [
        ("B5", "C5", "折扣实例·年化可省", summary["discount_annualized"], "按月均×12×约13%折扣提升"),
        ("D5", "E5", "产品级·年化机会", summary["product_annualized"], "低折扣高消费产品谈价空间"),
        ("F5", "G5", "闲置降配·粗估年省", summary["idle_annual_savings"], "规格目录价粗估，偏上限"),
    ]
    for c1, c2, label, value, note in kpis:
        ws.merge_cells(f"{c1}:{c2}")
        cell = ws[c1]
        cell.value = f"¥{value:,.0f}"
        cell.font = Font(name="Microsoft YaHei", size=20, bold=True, color=C_TEAL)
        cell.fill = _fill(C_BG_KPI)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _thin()
        ws.row_dimensions[5].height = 40

        r = 6
        ws.merge_cells(f"{c1[0]}{r}:{c2[0]}{r}")
        lab = ws[f"{c1[0]}{r}"]
        lab.value = label
        lab.font = Font(name="Microsoft YaHei", size=10, bold=True, color=C_SLATE)
        lab.fill = _fill(C_BG_KPI)
        lab.alignment = Alignment(horizontal="center")
        lab.border = _thin()

        r = 7
        ws.merge_cells(f"{c1[0]}{r}:{c2[0]}{r}")
        n = ws[f"{c1[0]}{r}"]
        n.value = note
        n.font = Font(name="Microsoft YaHei", size=8, color=C_MUTED)
        n.fill = _fill(C_BG_KPI)
        n.alignment = Alignment(horizontal="center", wrap_text=True)
        n.border = _thin()
        ws.row_dimensions[7].height = 32

    # 合计条
    ws.merge_cells("B9:G9")
    total_opp = (
        float(summary["discount_annualized"])
        + float(summary["product_annualized"])
        + float(summary["idle_annual_savings"])
    )
    # 产品与实例有重叠，提示勿简单相加
    ws["B9"].value = (
        f"三块加总名义约 ¥{total_opp:,.0f}/年（产品级与实例级有重叠，勿直接相加当承诺金额）"
        f"  ·  相对账单窗口 ¥{summary['bill_window_total']:,.0f}，"
        f"实例折扣清单年化约占 {summary['discount_vs_bill_pct']:.1f}%"
    )
    ws["B9"].font = Font(name="Microsoft YaHei", size=10, color=C_AMBER)
    ws["B9"].fill = _fill(C_BG_WARN)
    ws["B9"].alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[9].height = 36

    # 为什么看起来省得少
    ws["B11"].value = "为什么「看起来省得少」？"
    ws["B11"].font = Font(name="Microsoft YaHei", size=13, bold=True, color=C_NAVY)
    ws.merge_cells("B12:G16")
    why = ws["B12"]
    why.value = summary["why_small_text"]
    why.font = Font(name="Microsoft YaHei", size=10, color=C_SLATE)
    why.alignment = Alignment(wrap_text=True, vertical="top")
    why.fill = _fill("F8FAFC")
    why.border = _thin()
    ws.row_dimensions[12].height = 20
    for r in range(13, 17):
        ws.row_dimensions[r].height = 18

    # 结构表
    ws["B18"].value = "账户消费结构（产品窗口 Top）"
    ws["B18"].font = Font(name="Microsoft YaHei", size=12, bold=True, color=C_NAVY)
    headers = ["产品", "窗口消费¥", "平均折扣%", "年化谈价机会¥", "解读"]
    for i, h in enumerate(headers, 2):
        ws.cell(row=19, column=i, value=h)
    _style_table_header(ws, 19, 2, 6)

    for idx, pr in enumerate(summary["top_products_brief"][:8]):
        r = 20 + idx
        vals = [pr["产品"], pr["窗口消费¥"], pr["平均折扣%"], pr["年化机会¥"], pr["说明"]]
        for i, v in enumerate(vals, 2):
            ws.cell(row=r, column=i, value=v)
        _style_data_row(
            ws,
            r,
            2,
            6,
            priority=pr.get("优先级"),
            alt=idx % 2 == 1,
            money_cols=[3, 5],
            pct_cols=[4],
        )

    # 优先动作
    tip_start = 20 + len(summary["top_products_brief"][:8]) + 2
    ws.cell(row=tip_start, column=2, value="建议优先动作（Top）")
    ws.cell(row=tip_start, column=2).font = Font(name="Microsoft YaHei", size=12, bold=True, color=C_NAVY)
    for i, line in enumerate(summary["priority_tips"][:10]):
        cell = ws.cell(row=tip_start + 1 + i, column=2, value=line)
        ws.merge_cells(start_row=tip_start + 1 + i, start_column=2, end_row=tip_start + 1 + i, end_column=7)
        cell.font = Font(name="Microsoft YaHei", size=10, color=C_SLATE)
        cell.alignment = Alignment(wrap_text=True)
        ws.row_dimensions[tip_start + 1 + i].height = 22

    # ========== 2. 口径说明 ==========
    ws2 = wb.create_sheet("口径说明")
    ws2.sheet_view.showGridLines = False
    _set_col_widths(ws2, {"A": 3, "B": 22, "C": 70})
    ws2["B2"] = "数字怎么读"
    ws2["B2"].font = Font(name="Microsoft YaHei", size=16, bold=True, color=C_NAVY)
    explain_rows = [
        ("折扣率定义", "账单里 invoice_discount / (实付+折扣)。0% = 这段时间几乎没拿到折扣，不是「免费」。"),
        ("原「年节省」问题", "后端字段 annual_potential_savings 实际是：窗口总花费 × 固定 +13% 折扣提升，不是严格年化。"),
        ("本表「真实月均」", "窗口总花费 ÷ 运行月数（修正了 API 里对日明细做 AVG 导致的假月均）。"),
        ("本表「年化可省」", "真实月均 × 12 × 折扣提升幅度（默认约 13 个百分点）。"),
        ("为何只有 ~13%", "优化建议算法写死 estimated = min(当前折扣+0.13, 0.70)，不会按产品给到 3~5 折那种激进假设。"),
        ("为何清单偏「小单」", "只扫长期按量付费(PayAsYouGo)实例。ECS 大头多半已是包年/预付，不进该清单。"),
        ("产品级机会", "按产品汇总的低折扣高消费，用来补「实例清单看不到的大盘」。与实例行有重叠。"),
        ("闲置年省", "按规格目录价粗估 × 降配比例，且未扣已有包年折扣，通常偏高，只适合排序。"),
        ("真正大空间在哪", "① 低折扣大盘产品谈企业折扣；② 低利用率大规格降配/合并；③ 已包年但规格过大的 ECS。"),
    ]
    ws2["B4"] = "主题"
    ws2["C4"] = "说明"
    _style_table_header(ws2, 4, 2, 3)
    for i, (k, v) in enumerate(explain_rows):
        r = 5 + i
        ws2.cell(row=r, column=2, value=k)
        ws2.cell(row=r, column=3, value=v)
        _style_data_row(ws2, r, 2, 3, alt=i % 2 == 1)
        ws2.row_dimensions[r].height = 36
        ws2.cell(row=r, column=2).font = Font(name="Microsoft YaHei", size=10, bold=True, color=C_TEAL)

    # ========== 3. 折扣实例 ==========
    def add_sheet(title: str, rows: List[Dict], money_keys: List[str], pct_keys: List[str], freeze: str = "A2") -> None:
        w = wb.create_sheet(title)
        if not rows:
            w["A1"] = "暂无数据"
            return
        headers = list(rows[0].keys())
        money_idx = [headers.index(k) + 1 for k in money_keys if k in headers]
        pct_idx = [headers.index(k) + 1 for k in pct_keys if k in headers]

        for c, h in enumerate(headers, 1):
            w.cell(row=1, column=c, value=h)
        _style_table_header(w, 1, 1, len(headers))

        for ri, row in enumerate(rows):
            r = ri + 2
            for c, h in enumerate(headers, 1):
                w.cell(row=r, column=c, value=row.get(h))
            _style_data_row(
                w,
                r,
                1,
                len(headers),
                priority=str(row.get("优先级") or ""),
                alt=ri % 2 == 1,
                money_cols=money_idx,
                pct_cols=pct_idx,
            )
            w.row_dimensions[r].height = 22

        for idx, h in enumerate(headers, 1):
            # 中文列宽启发式
            base = max(10, min(42, len(str(h)) * 2 + 4))
            if h in ("实例ID", "闲置原因", "建议", "说明", "降配建议", "标记"):
                base = min(48, base + 12)
            if h in ("名称", "分析窗口", "产品"):
                base = max(base, 18)
            w.column_dimensions[get_column_letter(idx)].width = base

        w.auto_filter.ref = w.dimensions
        w.freeze_panes = freeze
        w.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(rows)+1}"

    add_sheet(
        "①折扣实例清单",
        discount_rows,
        money_keys=["窗口总花费¥", "真实月均¥", "窗口期可省¥", "年化可省¥"],
        pct_keys=["当前折扣%", "假设包年折扣%"],
    )
    add_sheet(
        "②产品谈价机会",
        product_rows,
        money_keys=["窗口消费¥", "月均消费¥", "窗口机会¥", "年化机会¥"],
        pct_keys=["平均折扣%", "目标折扣%"],
    )
    add_sheet(
        "③低利用率降配",
        idle_rows,
        money_keys=["规格粗估月费¥", "粗估月省¥", "粗估年省¥"],
        pct_keys=["CPU%", "内存%"],
    )

    wb.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="导出折扣差 + 低利用率成本行动清单")
    parser.add_argument("--account", "-a", default="cf")
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--username", default=DEFAULT_USER)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parents[1] / "artifacts" / "exports"),
    )
    parser.add_argument("--opts-json", help="本地 optimization-suggestions JSON（跳过 API）")
    parser.add_argument("--products-json", help="本地 product-trends JSON（跳过 API）")
    parser.add_argument("--idle-json", help="本地 dashboard/idle JSON（跳过 API）")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    prefix = out_dir / f"cost-action-{args.account}-{stamp}"

    if args.opts_json and args.products_json and args.idle_json:
        logger.info("使用本地 JSON 文件生成...")
        opts = json.loads(Path(args.opts_json).read_text(encoding="utf-8"))
        products_resp = json.loads(Path(args.products_json).read_text(encoding="utf-8"))
        idle_resp = json.loads(Path(args.idle_json).read_text(encoding="utf-8"))
        suggestions = (opts.get("data") or {}).get("suggestions") or []
        products = (products_resp.get("data") or {}).get("products") or []
        idle_items = idle_resp.get("data") or []
    else:
        client = ApiClient(args.api_base, args.username, args.password)
        account_q = f"account={args.account}"

        logger.info("拉取折扣优化建议...")
        opts = client.get_json(f"/api/discounts/optimization-suggestions?{account_q}")
        suggestions = (opts.get("data") or {}).get("suggestions") or []

        logger.info("拉取产品折扣趋势...")
        products_resp = client.get_json(f"/api/discounts/product-trends?{account_q}&months=19&top_n=30")
        products = (products_resp.get("data") or {}).get("products") or []

        logger.info("拉取闲置资源...")
        idle_resp = client.get_json(f"/api/dashboard/idle?{account_q}")
        idle_items = idle_resp.get("data") or []
    if not isinstance(idle_items, list):
        idle_items = []

    discount_rows = build_discount_rows(suggestions, products)
    product_rows = build_product_opportunity_rows(products)
    idle_rows = build_idle_rows(idle_items)

    discount_annualized = sum(float(r["年化可省¥"] or 0) for r in discount_rows)
    discount_window = sum(float(r["窗口期可省¥"] or 0) for r in discount_rows)
    product_annualized = sum(float(r["年化机会¥"] or 0) for r in product_rows)
    idle_annual = sum(float(r["粗估年省¥"] or 0) for r in idle_rows)
    bill_total = sum(float(p.get("total_consumption") or 0) for p in products)

    # 为何省得少：用数据说话
    ecs = next((p for p in products if "ECS" in str(p.get("product_name") or "")), None)
    ecs_spend = float(ecs.get("total_consumption") or 0) if ecs else 0
    ecs_rate = float(ecs.get("avg_discount_rate") or 0) * 100 if ecs else 0
    zero_spend = sum(
        float(p.get("total_consumption") or 0)
        for p in products
        if float(p.get("avg_discount_rate") or 0) < 0.05 and float(p.get("total_consumption") or 0) >= 1000
    )
    why_small_text = (
        f"1) 算法保守：优化建议把「转包年」一律按 +{ASSUMED_RATE_LIFT*100:.0f} 个百分点估算，"
        f"50 条按量实例窗口花费合计约 ¥{sum(float(r['窗口总花费¥']) for r in discount_rows):,.0f}，"
        f"乘 13% 只有约 ¥{discount_window:,.0f}（年化约 ¥{discount_annualized:,.0f}）。\n"
        f"2) 大头不在清单里：产品窗口总消费约 ¥{bill_total:,.0f}，其中 ECS 约 ¥{ecs_spend:,.0f}"
        f"（平均折扣已约 {ecs_rate:.0f}%），多为包年/预付，不会出现在「按量转包年」列表。\n"
        f"3) 低折扣大盘在产品层：折扣≈0 且消费≥¥1k 的产品合计约 ¥{zero_spend:,.0f}"
        f"（负载均衡/块存储/ARMS/日志等）——单实例很碎，要靠企业折扣或产品级治理，"
        f"本表「②产品谈价机会」年化约 ¥{product_annualized:,.0f}。\n"
        f"4) 闲置只有 {len(idle_rows)} 台 P2（无完全闲置 P1），且部分内存已高，"
        f"可降空间有限；粗估年省 ¥{idle_annual:,.0f} 用的是目录价，实付通常更低。\n"
        f"结论：不是「云不贵」，而是「已包年的 ECS 占大头 + 估算故意保守 + 可挖的是分散小单与谈价」。"
    )

    tips: List[str] = []
    if product_rows:
        tips.append("【产品谈价】")
        for r in product_rows[:4]:
            tips.append(
                f"  · [{r['优先级']}] {r['产品']} 月均¥{r['月均消费¥']:,.0f} 折扣{r['平均折扣%']}% "
                f"→ 年化机会约¥{r['年化机会¥']:,.0f}"
            )
    if discount_rows:
        tips.append("【按量实例转包年】")
        for r in discount_rows[:4]:
            tips.append(
                f"  · [{r['优先级']}] {r['产品']} {r['实例ID'][:22]} 月均¥{r['真实月均¥']:,.0f} "
                f"→ 年化约¥{r['年化可省¥']:,.0f}"
            )
    if idle_rows:
        tips.append("【低利用率降配】")
        for r in idle_rows[:4]:
            risk = f"（{r['风险']}）" if r.get("风险") else ""
            tips.append(
                f"  · [{r['优先级']}] {r['名称']} {r['规格']} CPU{r['CPU%']}% "
                f"→ 粗估年省¥{r['粗估年省¥']:,.0f}{risk}"
            )

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "account": args.account,
        "discount_count": len(discount_rows),
        "discount_annualized": round(discount_annualized, 2),
        "discount_window_savings": round(discount_window, 2),
        "product_annualized": round(product_annualized, 2),
        "idle_count": len(idle_rows),
        "idle_annual_savings": round(idle_annual, 2),
        "bill_window_total": round(bill_total, 2),
        "discount_vs_bill_pct": (discount_annualized / bill_total * 100) if bill_total else 0,
        "priority_tips": tips or ["暂无优先项"],
        "why_small_text": why_small_text,
        "top_products_brief": product_rows[:8],
    }

    csv_discount = Path(str(prefix) + "-折扣实例.csv")
    csv_product = Path(str(prefix) + "-产品机会.csv")
    csv_idle = Path(str(prefix) + "-低利用率.csv")
    xlsx_path = Path(str(prefix) + ".xlsx")

    write_csv(csv_discount, discount_rows)
    write_csv(csv_product, product_rows)
    write_csv(csv_idle, idle_rows)
    write_excel(xlsx_path, discount_rows, product_rows, idle_rows, summary)

    latest = out_dir / f"cost-action-{args.account}-latest.xlsx"
    write_excel(latest, discount_rows, product_rows, idle_rows, summary)

    print("\n========== 成本行动清单已生成 ==========")
    print(f"Excel: {xlsx_path}")
    print(f"Latest: {latest}")
    print(f"账单窗口合计: ¥{summary['bill_window_total']:,.0f}")
    print(f"折扣实例年化: ¥{summary['discount_annualized']:,.0f}  （原窗口×13%字段合计 ¥{summary['discount_window_savings']:,.0f}）")
    print(f"产品谈价年化: ¥{summary['product_annualized']:,.0f}")
    print(f"闲置粗估年省: ¥{summary['idle_annual_savings']:,.0f}")
    print("----------------------------------------")
    for line in tips[:14]:
        print(line)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.exception("导出失败: %s", e)
        sys.exit(1)
