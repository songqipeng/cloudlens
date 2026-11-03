# -*- coding: utf-8 -*-
"""报告生成与历史存储测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cloudlens.core import report_service


SNAPSHOT = {
    "account": "demo",
    "resources": [
        {
            "type": "ecs",
            "id": "i-1",
            "name": "web",
            "spec": "ecs.g6.large",
            "status": "Running",
            "region": "cn-hangzhou",
            "public_ip": "1.2.3.4",
        }
    ],
    "bills": [
        {"product_code": "ecs", "instance_id": "i-1", "billing_cycle": "2026-10", "pretax_amount": 12.5},
        {"product_code": "rds", "instance_id": "rm-1", "billing_cycle": "2026-10", "pretax_amount": 7.5},
    ],
    "notes": [],
}


def test_generate_html_excel_pdf_and_list(monkeypatch, tmp_path):
    """三种格式都能落盘，并按账号出现在历史里。"""
    monkeypatch.setenv("CLOUDLENS_REPORT_DIR", str(tmp_path))
    report_service._FONT_NAME = None

    html_report = report_service.generate_report_file("demo", "cost", "html", snapshot=SNAPSHOT)
    excel_report = report_service.generate_report_file("demo", "resources", "excel", snapshot=SNAPSHOT)
    pdf_report = report_service.generate_report_file("demo", "security", "pdf", snapshot=SNAPSHOT)

    assert "税前金额" in html_report["content"]
    assert html_report["content"].count("ecs") >= 1

    excel_meta, excel_bytes = report_service.read_report(excel_report["id"])
    assert excel_meta["filename"].endswith(".xlsx")
    assert excel_bytes[:2] == b"PK"

    pdf_meta, pdf_bytes = report_service.read_report(pdf_report["id"])
    assert pdf_meta["format"] == "pdf"
    assert pdf_bytes.startswith(b"%PDF")

    listed = report_service.list_reports(account="demo")
    assert len(listed) == 3
    assert report_service.list_reports(account="other") == []


def test_reject_unknown_format(monkeypatch, tmp_path):
    """未知格式返回明确错误，不写文件。"""
    monkeypatch.setenv("CLOUDLENS_REPORT_DIR", str(tmp_path))
    try:
        report_service.generate_report_file("demo", "cost", "json", snapshot=SNAPSHOT)
        raised = False
    except ValueError as exc:
        raised = True
        assert "不支持的报告格式" in str(exc)
    assert raised
    assert report_service.list_reports() == []


def test_reports_api_roundtrip(monkeypatch, tmp_path):
    """列表、生成、下载接口返回真实文件而不是占位 ID。"""
    import importlib.util
    from pathlib import Path

    monkeypatch.setenv("CLOUDLENS_REPORT_DIR", str(tmp_path))
    monkeypatch.setattr(report_service, "collect_snapshot", lambda account: {**SNAPSHOT, "account": account or "demo"})

    module_path = Path("web/backend/api/v1/reports.py").resolve()
    spec = importlib.util.spec_from_file_location("reports_api_under_test", module_path)
    assert spec and spec.loader
    reports_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reports_api)

    app = FastAPI()
    app.include_router(reports_api.router)
    client = TestClient(app)

    empty = client.get("/api/reports", params={"account": "demo"})
    assert empty.status_code == 200
    assert empty.json()["data"] == []

    created = client.post("/api/reports/generate", params={"account": "demo"}, json={"type": "comprehensive", "format": "html"})
    assert created.status_code == 200
    body = created.json()
    assert body["success"] is True
    assert body["data"]["id"] != "new_report_id"
    assert "资源清单" in body["data"]["content"]

    listed = client.get("/api/reports", params={"account": "demo"})
    assert len(listed.json()["data"]) == 1

    downloaded = client.get(f"/api/reports/{body['data']['id']}/download")
    assert downloaded.status_code == 200
    assert b"CloudLens" in downloaded.content

    missing = client.get("/api/reports/missing/download")
    assert missing.status_code == 404

    bad = client.post("/api/reports/generate", json={"type": "cost", "format": "docx"})
    assert bad.status_code == 400
