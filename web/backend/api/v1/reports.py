#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告生成与历史查询。"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from cloudlens.core import report_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


class ReportGenerateBody(BaseModel):
    """与前端报告页一致的生成请求。type / report_type 二选一。"""

    type: Optional[str] = None
    report_type: Optional[str] = None
    format: str = "excel"
    account: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.get("/reports")
def list_reports(
    account: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
):
    """获取报告历史。"""
    try:
        data = report_service.list_reports(account=account, limit=limit)
        return {"success": True, "data": data}
    except Exception as exc:
        logger.exception("获取报告列表失败")
        raise HTTPException(status_code=500, detail="获取报告列表失败") from exc


@router.post("/reports/generate")
def generate_report(
    body: ReportGenerateBody,
    account: Optional[str] = None,
):
    """按类型和格式生成报告，并写入历史。"""
    report_type = body.type or body.report_type or "comprehensive"
    target_account = body.account or account
    try:
        record = report_service.generate_report_file(target_account, report_type, body.format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("生成报告失败")
        raise HTTPException(status_code=500, detail="生成报告失败") from exc

    payload = {
        "id": record["id"],
        "name": record["name"],
        "format": record["format"],
        "filename": record["filename"],
        "created_at": record["created_at"],
        "download_url": f"/reports/{record['id']}/download",
    }
    if record.get("content"):
        payload["content"] = record["content"]
    return {"success": True, "data": payload}


@router.get("/reports/{report_id}/download")
def download_report(report_id: str):
    """下载已生成的报告文件。"""
    found = report_service.read_report(report_id)
    if not found:
        raise HTTPException(status_code=404, detail="报告不存在")
    meta, content = found
    filename = meta.get("filename") or f"{report_id}.bin"
    return Response(
        content=content,
        media_type=report_service.media_type_for(str(meta.get("format") or "")),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
