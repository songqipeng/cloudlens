# -*- coding: utf-8 -*-
"""报告生成与历史存储。

报告文件落在本地目录（默认 ~/.cloudlens/reports），不依赖云 API。
有账单库或资源缓存时写入真实汇总；没有数据时仍生成可下载的空报告。
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

REPORT_TYPES = ("comprehensive", "resources", "cost", "security")
REPORT_FORMATS = ("excel", "html", "pdf")
TYPE_TITLES = {
    "comprehensive": "综合报告",
    "resources": "资源报告",
    "cost": "成本报告",
    "security": "安全报告",
}
_LOCK = threading.Lock()
_FONT_NAME: Optional[str] = None

_FONT_CANDIDATES = (
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
)


def report_root() -> Path:
    """报告根目录，测试可通过 CLOUDLENS_REPORT_DIR 覆盖。"""
    configured = os.environ.get("CLOUDLENS_REPORT_DIR", "").strip()
    root = Path(configured) if configured else Path.home() / ".cloudlens" / "reports"
    (root / "files").mkdir(parents=True, exist_ok=True)
    return root


def _index_path() -> Path:
    return report_root() / "index.json"


def _load_index() -> List[Dict[str, Any]]:
    path = _index_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("读取报告索引失败: %s", exc)
        return []
    return data if isinstance(data, list) else []


def _save_index(rows: List[Dict[str, Any]]) -> None:
    path = _index_path()
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value") and not isinstance(value, (str, int, float)):
        return str(value.value)
    return str(value)


def _money(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _normalize_resource(item: Any, resource_type: str) -> Dict[str, str]:
    if isinstance(item, dict):
        data = item
    else:
        data = {
            "id": getattr(item, "id", ""),
            "name": getattr(item, "name", ""),
            "spec": getattr(item, "spec", ""),
            "status": getattr(item, "status", ""),
            "region": getattr(item, "region", ""),
            "public_ip": getattr(item, "public_ip", "") or getattr(item, "public_ip_address", ""),
        }
    return {
        "type": _text(data.get("resource_type") or data.get("type") or resource_type),
        "id": _text(data.get("id") or data.get("instance_id")),
        "name": _text(data.get("name") or data.get("instance_name")),
        "spec": _text(data.get("spec") or data.get("instance_type")),
        "status": _text(data.get("status")),
        "region": _text(data.get("region")),
        "public_ip": _text(data.get("public_ip") or data.get("public_ip_address") or data.get("eip")),
    }


def collect_snapshot(account: Optional[str]) -> Dict[str, Any]:
    """从本地缓存和账单库收集报告素材。任何数据源失败都不中断生成。"""
    account_name = (account or "").strip() or "未指定账号"
    resources: List[Dict[str, str]] = []
    bills: List[Dict[str, Any]] = []
    notes: List[str] = []

    if account:
        try:
            from cloudlens.core.cache import CacheManager

            cache = CacheManager()
            for resource_type in ("ecs", "rds", "oss", "slb", "redis", "eip"):
                try:
                    cached = cache.get(resource_type, account)
                except Exception as exc:
                    logger.info("读取 %s 缓存失败: %s", resource_type, exc)
                    notes.append(f"{resource_type} 缓存不可用")
                    continue
                if isinstance(cached, list):
                    resources.extend(_normalize_resource(item, resource_type) for item in cached[:200])
        except Exception as exc:
            logger.info("资源缓存不可用: %s", exc)
            notes.append("资源缓存不可用，资源章节仅包含已成功读取的条目")
    else:
        notes.append("未指定账号，未读取资源缓存")

    try:
        from cloudlens.core.bill_storage import BillStorageManager

        rows = BillStorageManager().query_bill_items(limit=300)
        for row in rows:
            if not isinstance(row, dict):
                continue
            bills.append(
                {
                    "product_code": _text(row.get("product_code") or row.get("product_name")),
                    "instance_id": _text(row.get("instance_id")),
                    "billing_cycle": _text(row.get("billing_cycle")),
                    "pretax_amount": _money(row.get("pretax_amount")),
                }
            )
    except Exception as exc:
        logger.info("账单库不可用: %s", exc)
        notes.append("账单库不可用，成本章节为空")

    if not resources and not bills and not notes:
        notes.append("当前没有可汇总的本地数据")
    return {"account": account_name, "resources": resources, "bills": bills, "notes": notes}


def _cost_rows(bills: List[Dict[str, Any]]) -> Tuple[List[List[str]], float]:
    totals: Dict[str, float] = {}
    for row in bills:
        code = row.get("product_code") or "未知产品"
        totals[code] = totals.get(code, 0.0) + _money(row.get("pretax_amount"))
    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    table = [[code, f"{amount:.2f}"] for code, amount in ordered]
    return table, sum(totals.values())


def build_document(account: Optional[str], report_type: str, snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """把素材整理成与格式无关的报告文档。"""
    if report_type not in REPORT_TYPES:
        raise ValueError(f"不支持的报告类型: {report_type}")
    data = snapshot if snapshot is not None else collect_snapshot(account)
    resources = list(data.get("resources") or [])
    bills = list(data.get("bills") or [])
    notes = list(data.get("notes") or [])
    account_name = _text(data.get("account") or account or "未指定账号")
    cost_table, cost_total = _cost_rows(bills)
    exposed = [item for item in resources if item.get("public_ip")]

    summary = [
        ["账号", account_name],
        ["报告类型", TYPE_TITLES[report_type]],
        ["资源条数", str(len(resources))],
        ["账单条数", str(len(bills))],
        ["税前金额合计", f"{cost_total:.2f}"],
        ["公网地址资源", str(len(exposed))],
    ]
    tables: List[Dict[str, Any]] = []
    if report_type in ("comprehensive", "cost"):
        tables.append(
            {
                "title": "产品成本",
                "headers": ["产品", "税前金额"],
                "rows": cost_table or [["—", "0.00"]],
            }
        )
    if report_type in ("comprehensive", "resources"):
        tables.append(
            {
                "title": "资源清单",
                "headers": ["类型", "实例 ID", "名称", "状态", "地域"],
                "rows": [
                    [item["type"], item["id"], item["name"], item["status"], item["region"]]
                    for item in resources[:100]
                ]
                or [["—", "—", "暂无缓存资源", "—", "—"]],
            }
        )
    if report_type in ("comprehensive", "security"):
        tables.append(
            {
                "title": "公网暴露",
                "headers": ["类型", "实例 ID", "名称", "公网地址"],
                "rows": [
                    [item["type"], item["id"], item["name"], item["public_ip"]]
                    for item in exposed[:100]
                ]
                or [["—", "—", "未发现带公网地址的缓存资源", "—"]],
            }
        )
        notes.append("安全章节来自本地资源缓存中的公网地址字段，不替代完整 CIS 扫描")

    return {
        "title": f"CloudLens {TYPE_TITLES[report_type]}",
        "account": account_name,
        "type": report_type,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "tables": tables,
        "notes": notes,
    }


def _html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_html(document: Dict[str, Any]) -> bytes:
    """渲染 HTML 报告。"""
    summary = "".join(
        f"<tr><th>{_html_escape(k)}</th><td>{_html_escape(v)}</td></tr>" for k, v in document["summary"]
    )
    sections = []
    for table in document["tables"]:
        head = "".join(f"<th>{_html_escape(cell)}</th>" for cell in table["headers"])
        body = "".join(
            "<tr>" + "".join(f"<td>{_html_escape(cell)}</td>" for cell in row) + "</tr>" for row in table["rows"]
        )
        sections.append(f"<h2>{_html_escape(table['title'])}</h2><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
    notes = "".join(f"<li>{_html_escape(note)}</li>" for note in document["notes"])
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{_html_escape(document["title"])}</title>
  <style>
    body {{ font-family: "Segoe UI", "PingFang SC", sans-serif; margin: 24px; color: #1f2937; }}
    h1 {{ border-bottom: 3px solid #2563eb; padding-bottom: 8px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 28px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 8px 10px; text-align: left; }}
    th {{ background: #eff6ff; }}
  </style>
</head>
<body>
  <h1>{_html_escape(document["title"])}</h1>
  <p>生成时间：{_html_escape(document["generated_at"])}</p>
  <h2>摘要</h2>
  <table>{summary}</table>
  {''.join(sections)}
  <h2>说明</h2>
  <ul>{notes}</ul>
</body>
</html>
"""
    return html.encode("utf-8")


def render_excel(document: Dict[str, Any]) -> bytes:
    """渲染 Excel 报告。"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "摘要"
    sheet["A1"] = document["title"]
    sheet["A1"].font = Font(size=16, bold=True)
    sheet["A2"] = f"生成时间：{document['generated_at']}"
    for index, (label, value) in enumerate(document["summary"], start=4):
        sheet.cell(index, 1, label)
        sheet.cell(index, 2, value)

    header_fill = PatternFill(start_color="1D4ED8", end_color="1D4ED8", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for table in document["tables"]:
        title = str(table["title"])[:31] or "明细"
        detail = workbook.create_sheet(title)
        for col, header in enumerate(table["headers"], start=1):
            cell = detail.cell(1, col, header)
            cell.fill = header_fill
            cell.font = header_font
        for row_index, row in enumerate(table["rows"], start=2):
            for col, value in enumerate(row, start=1):
                detail.cell(row_index, col, value)

    if document["notes"]:
        note_sheet = workbook.create_sheet("说明")
        for index, note in enumerate(document["notes"], start=1):
            note_sheet.cell(index, 1, note)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _pdf_font() -> str:
    """注册可显示中文的字体；没有系统字体时退回 Helvetica。"""
    global _FONT_NAME
    if _FONT_NAME:
        return _FONT_NAME
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        _FONT_NAME = "Helvetica"
        return _FONT_NAME

    for path in _FONT_CANDIDATES:
        if not Path(path).exists():
            continue
        try:
            kwargs = {"subfontIndex": 0} if path.endswith(".ttc") else {}
            pdfmetrics.registerFont(TTFont("CloudLensCJK", path, **kwargs))
            _FONT_NAME = "CloudLensCJK"
            return _FONT_NAME
        except Exception as exc:
            logger.info("注册字体失败 %s: %s", path, exc)
    _FONT_NAME = "Helvetica"
    return _FONT_NAME


def _pdf_text(value: str, font_name: str) -> str:
    if font_name != "Helvetica":
        return value
    return value.encode("latin-1", errors="replace").decode("latin-1")


def render_pdf(document: Dict[str, Any]) -> bytes:
    """渲染 PDF 报告。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    font_name = _pdf_font()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    _, height = A4
    y = height - 20 * mm

    def line(text: str, size: int = 11, gap: float = 6 * mm) -> None:
        nonlocal y
        if y < 20 * mm:
            pdf.showPage()
            y = height - 20 * mm
        pdf.setFont(font_name, size)
        pdf.drawString(18 * mm, y, _pdf_text(text, font_name)[:110])
        y -= gap

    line(document["title"], 16, 10 * mm)
    line(f"生成时间：{document['generated_at']}")
    line("摘要", 13)
    for label, value in document["summary"]:
        line(f"{label}：{value}", 11, 5.5 * mm)
    for table in document["tables"]:
        line(table["title"], 13, 8 * mm)
        line(" | ".join(table["headers"]), 10, 5 * mm)
        for row in table["rows"][:40]:
            line(" | ".join(row), 10, 5 * mm)
    if document["notes"]:
        line("说明", 13, 8 * mm)
        for note in document["notes"]:
            line(note, 10, 5 * mm)
    pdf.save()
    return buffer.getvalue()


_RENDERERS = {
    "html": render_html,
    "excel": render_excel,
    "pdf": render_pdf,
}
_EXTENSIONS = {"html": "html", "excel": "xlsx", "pdf": "pdf"}
_MEDIA_TYPES = {
    "html": "text/html; charset=utf-8",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def list_reports(account: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """按生成时间倒序列出报告，可按账号过滤。"""
    with _LOCK:
        rows = _load_index()
    if account:
        rows = [row for row in rows if row.get("account") == account]
    rows.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    visible = []
    for row in rows[:limit]:
        visible.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "account": row.get("account"),
                "type": row.get("type"),
                "format": row.get("format"),
                "created_at": row.get("created_at"),
                "filename": row.get("filename"),
            }
        )
    return visible


def read_report(report_id: str) -> Optional[Tuple[Dict[str, Any], bytes]]:
    """读取报告元数据和文件内容。"""
    with _LOCK:
        rows = _load_index()
    meta = next((row for row in rows if row.get("id") == report_id), None)
    if not meta:
        return None
    path = report_root() / "files" / str(meta.get("filename") or "")
    if not path.is_file():
        return None
    return meta, path.read_bytes()


def media_type_for(fmt: str) -> str:
    return _MEDIA_TYPES.get(fmt, "application/octet-stream")


def generate_report_file(
    account: Optional[str],
    report_type: str,
    fmt: str,
    snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """生成报告文件并写入历史索引。

    Args:
        account: 账号名，可为空
        report_type: comprehensive / resources / cost / security
        fmt: excel / html / pdf
        snapshot: 测试或调用方直接传入的素材，跳过外部数据源

    Returns:
        报告元数据。HTML 额外包含 content 文本。

    Raises:
        ValueError: 类型或格式不支持
    """
    if fmt not in REPORT_FORMATS:
        raise ValueError(f"不支持的报告格式: {fmt}")
    document = build_document(account, report_type, snapshot=snapshot)
    content = _RENDERERS[fmt](document)
    report_id = uuid.uuid4().hex
    created_at = document["generated_at"]
    filename = f"{report_id}.{_EXTENSIONS[fmt]}"
    account_name = account or document["account"]
    record = {
        "id": report_id,
        "name": f"{document['title']} {created_at}",
        "account": account_name,
        "type": report_type,
        "format": fmt,
        "created_at": created_at,
        "filename": filename,
    }
    with _LOCK:
        path = report_root() / "files" / filename
        path.write_bytes(content)
        rows = _load_index()
        rows.append(record)
        if len(rows) > 200:
            for old in rows[:-200]:
                old_path = report_root() / "files" / str(old.get("filename") or "")
                if old_path.is_file():
                    old_path.unlink()
            rows = rows[-200:]
        _save_index(rows)
    if fmt == "html":
        record = {**record, "content": content.decode("utf-8")}
    return record
