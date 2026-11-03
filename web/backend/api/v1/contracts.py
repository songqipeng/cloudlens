# -*- coding: utf-8 -*-
"""框架合同 API：上传 PDF、确认发布、多版本管理"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from web.backend.api_base import handle_api_error
from cloudlens.core.config import ConfigManager
from cloudlens.core.framework_contract import (
    FrameworkContractStore,
    parse_framework_contract_pdf,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class ContractUpdateBody(BaseModel):
    title: Optional[str] = None
    contract_no: Optional[str] = None
    cloud_uid: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    notes: Optional[str] = None
    rules: Optional[Dict[str, Any]] = None


class ContractCreateBody(BaseModel):
    title: Optional[str] = "手工框架规则"
    contract_no: Optional[str] = None
    cloud_uid: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    status: str = "draft"
    priority: int = 0
    notes: Optional[str] = None
    rules: Dict[str, Any] = Field(default_factory=dict)


def _require_account(account: Optional[str]) -> str:
    cm = ConfigManager()
    if not account:
        accounts = cm.list_accounts()
        if not accounts:
            raise HTTPException(status_code=404, detail="未配置账号")
        account = accounts[0].name
    if not cm.get_account(account):
        raise HTTPException(status_code=404, detail=f"账号不存在: {account}")
    return account


@router.get("/contracts")
def list_contracts(
    account: Optional[str] = Query(None),
    billing_cycle: Optional[str] = Query(None, description="账期 YYYY-MM，用于标注当前生效合同"),
):
    try:
        account_name = _require_account(account)
        store = FrameworkContractStore()
        items = store.list_contracts(account_name)
        active = store.get_active_for_period(account_name, billing_cycle)
        return {
            "success": True,
            "data": {
                "contracts": items,
                "active_contract_id": active.get("id") if active else None,
                "billing_cycle": billing_cycle,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "list_contracts")


@router.get("/contracts/{contract_id}")
def get_contract(contract_id: str):
    try:
        store = FrameworkContractStore()
        row = store.get_contract(contract_id)
        if not row:
            raise HTTPException(status_code=404, detail="合同不存在")
        return {"success": True, "data": row}
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "get_contract")


@router.post("/contracts/parse-pdf")
async def parse_contract_pdf(
    account: str = Form(...),
    file: UploadFile = File(...),
):
    """上传 PDF → 解析预填 → 保存为 draft（需再调用 publish 确认）"""
    try:
        account_name = _require_account(account)
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="请上传 PDF 文件")
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="空文件")
        if len(raw) > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="PDF 超过 25MB")

        parsed = parse_framework_contract_pdf(raw)
        store = FrameworkContractStore()
        draft = store.create_draft_from_parse(
            account_name=account_name,
            parsed=parsed,
            pdf_bytes=raw,
            pdf_name=file.filename,
        )
        return {
            "success": True,
            "data": {
                "contract": draft,
                "warnings": parsed.get("warnings") or [],
                "preview_excerpt": parsed.get("preview_excerpt") or "",
                "message": "已解析为草稿，请核对规则后点击「确认发布」",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "parse_contract_pdf")


@router.post("/contracts")
def create_contract(body: ContractCreateBody, account: Optional[str] = Query(None)):
    try:
        account_name = _require_account(account)
        store = FrameworkContractStore()
        payload = body.model_dump()
        # 直接创建 active 必须走 publish，保证同账号互斥
        want_active = payload.get("status") == "active"
        if want_active:
            payload["status"] = "draft"
        row = store.create_manual(account_name, payload)
        if want_active:
            rules = row.get("rules") or {}
            if not (rules.get("products") or []):
                raise HTTPException(
                    status_code=400, detail="规则中无覆盖产品，无法直接设为生效"
                )
            row = store.publish(row["id"])
        return {"success": True, "data": row}
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "create_contract")


@router.put("/contracts/{contract_id}")
def update_contract(contract_id: str, body: ContractUpdateBody):
    try:
        store = FrameworkContractStore()
        payload = {k: v for k, v in body.model_dump().items() if v is not None}
        if "rules" in body.model_dump(exclude_unset=True):
            payload["rules"] = body.rules
        # 设为 active 统一走 publish，避免绕过互斥产生多份生效合同
        want_active = payload.pop("status", None) == "active"
        if payload:
            row = store.update_contract(contract_id, payload)
        else:
            row = store.get_contract(contract_id)
            if not row:
                raise HTTPException(status_code=404, detail="合同不存在")
        if want_active:
            rules = (row or {}).get("rules") or {}
            if not (rules.get("products") or []):
                raise HTTPException(
                    status_code=400, detail="规则中无覆盖产品，请先编辑补充后再发布"
                )
            row = store.publish(contract_id)
        return {"success": True, "data": row}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "update_contract")


@router.post("/contracts/{contract_id}/publish")
def publish_contract(contract_id: str):
    """人工确认后发布为 active"""
    try:
        store = FrameworkContractStore()
        row = store.get_contract(contract_id)
        if not row:
            raise HTTPException(status_code=404, detail="合同不存在")
        rules = row.get("rules") or {}
        if not (rules.get("products") or []):
            raise HTTPException(status_code=400, detail="规则中无覆盖产品，请先编辑补充后再发布")
        published = store.publish(contract_id)
        return {
            "success": True,
            "data": published,
            "message": "已发布；同账号其它生效合同已自动归档，扫描将使用此合同",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "publish_contract")


@router.post("/contracts/{contract_id}/archive")
def archive_contract(contract_id: str):
    try:
        store = FrameworkContractStore()
        if not store.get_contract(contract_id):
            raise HTTPException(status_code=404, detail="合同不存在")
        return {"success": True, "data": store.archive(contract_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "archive_contract")


@router.get("/contracts/{contract_id}/pdf")
def download_contract_pdf(contract_id: str):
    """下载合同来源 PDF（若已上传）。"""
    try:
        store = FrameworkContractStore()
        row = store.get_contract(contract_id)
        if not row:
            raise HTTPException(status_code=404, detail="合同不存在")
        pdf_path = row.get("source_pdf_path")
        if not pdf_path:
            raise HTTPException(status_code=404, detail="该合同无关联 PDF")
        path = Path(pdf_path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="PDF 文件不存在或已被删除")
        filename = row.get("source_pdf_name") or path.name
        return FileResponse(
            path=str(path),
            media_type="application/pdf",
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "download_contract_pdf")


@router.delete("/contracts/{contract_id}")
def delete_contract(contract_id: str):
    try:
        store = FrameworkContractStore()
        store.delete_contract(contract_id)
        return {"success": True}
    except Exception as e:
        raise handle_api_error(e, "delete_contract")
