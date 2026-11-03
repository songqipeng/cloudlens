# -*- coding: utf-8 -*-
"""框架合同持久化"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cloudlens.core.database import DatabaseFactory

logger = logging.getLogger(__name__)

DEFAULT_RULES: Dict[str, Any] = {
    "framework_discount": 0.50,
    "products": [],
}


class FrameworkContractStore:
    """框架合同 CRUD（MySQL）"""

    def __init__(self) -> None:
        self.db = DatabaseFactory.create_adapter("mysql")
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS framework_contracts (
                id VARCHAR(64) PRIMARY KEY,
                account_name VARCHAR(100) NOT NULL,
                title VARCHAR(255) DEFAULT NULL,
                contract_no VARCHAR(128) DEFAULT NULL,
                cloud_uid VARCHAR(64) DEFAULT NULL,
                effective_from DATE DEFAULT NULL,
                effective_to DATE DEFAULT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'draft',
                priority INT NOT NULL DEFAULT 0,
                rules_json JSON NOT NULL,
                source_pdf_path VARCHAR(512) DEFAULT NULL,
                source_pdf_name VARCHAR(255) DEFAULT NULL,
                parse_meta_json JSON DEFAULT NULL,
                notes TEXT DEFAULT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_fc_account_status (account_name, status),
                INDEX idx_fc_dates (effective_from, effective_to)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

    @staticmethod
    def pdf_dir(account_name: str) -> Path:
        base = Path.home() / ".cloudlens" / "contracts" / account_name
        base.mkdir(parents=True, exist_ok=True)
        return base

    def list_contracts(self, account_name: str) -> List[Dict[str, Any]]:
        rows = self.db.query(
            """
            SELECT id, account_name, title, contract_no, cloud_uid,
                   effective_from, effective_to, status, priority,
                   rules_json, source_pdf_name, parse_meta_json, notes,
                   created_at, updated_at
            FROM framework_contracts
            WHERE account_name = %s
            ORDER BY priority DESC, effective_from DESC, updated_at DESC
            """,
            (account_name,),
        )
        return [self._row_to_dict(r) for r in rows]

    def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        row = self.db.query_one(
            """
            SELECT id, account_name, title, contract_no, cloud_uid,
                   effective_from, effective_to, status, priority,
                   rules_json, source_pdf_path, source_pdf_name,
                   parse_meta_json, notes, created_at, updated_at
            FROM framework_contracts WHERE id = %s
            """,
            (contract_id,),
        )
        return self._row_to_dict(row) if row else None

    def get_active_for_period(
        self, account_name: str, billing_cycle: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """按账期选取生效合同；重叠时取 priority 高、更新近的。"""
        contracts = [
            c
            for c in self.list_contracts(account_name)
            if c.get("status") == "active"
        ]
        if not contracts:
            return None
        if not billing_cycle:
            return contracts[0]

        try:
            y, m = billing_cycle.split("-")[:2]
            ref = date(int(y), int(m), 15)
        except Exception:
            return contracts[0]

        matched = []
        for c in contracts:
            start = self._as_date(c.get("effective_from"))
            end = self._as_date(c.get("effective_to"))
            if start and ref < start:
                continue
            if end and ref > end:
                continue
            matched.append(c)
        return matched[0] if matched else None

    def create_draft_from_parse(
        self,
        account_name: str,
        parsed: Dict[str, Any],
        pdf_bytes: bytes,
        pdf_name: str,
    ) -> Dict[str, Any]:
        contract_id = uuid.uuid4().hex[:16]
        pdf_path = self.pdf_dir(account_name) / f"{contract_id}.pdf"
        pdf_path.write_bytes(pdf_bytes)

        rules = parsed.get("rules") or dict(DEFAULT_RULES)
        meta = {
            "warnings": parsed.get("warnings") or [],
            "extracted_text_chars": parsed.get("text_chars") or 0,
            "parser_version": parsed.get("parser_version") or "1.0",
        }
        self.db.execute(
            """
            INSERT INTO framework_contracts (
                id, account_name, title, contract_no, cloud_uid,
                effective_from, effective_to, status, priority,
                rules_json, source_pdf_path, source_pdf_name, parse_meta_json, notes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,'draft',%s,%s,%s,%s,%s,%s)
            """,
            (
                contract_id,
                account_name,
                parsed.get("title") or "框架服务协议",
                parsed.get("contract_no"),
                parsed.get("cloud_uid"),
                parsed.get("effective_from"),
                parsed.get("effective_to"),
                int(parsed.get("priority") or 0),
                json.dumps(rules, ensure_ascii=False),
                str(pdf_path),
                pdf_name,
                json.dumps(meta, ensure_ascii=False),
                parsed.get("notes") or "PDF 解析预填，请确认后发布",
            ),
        )
        result = self.get_contract(contract_id)
        assert result is not None
        return result

    def create_manual(
        self, account_name: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        contract_id = uuid.uuid4().hex[:16]
        rules = payload.get("rules") or dict(DEFAULT_RULES)
        self.db.execute(
            """
            INSERT INTO framework_contracts (
                id, account_name, title, contract_no, cloud_uid,
                effective_from, effective_to, status, priority,
                rules_json, notes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                contract_id,
                account_name,
                payload.get("title") or "手工框架规则",
                payload.get("contract_no"),
                payload.get("cloud_uid"),
                payload.get("effective_from"),
                payload.get("effective_to"),
                payload.get("status") or "draft",
                int(payload.get("priority") or 0),
                json.dumps(rules, ensure_ascii=False),
                payload.get("notes"),
            ),
        )
        result = self.get_contract(contract_id)
        assert result is not None
        return result

    def update_contract(self, contract_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_contract(contract_id)
        if not existing:
            raise ValueError("合同不存在")

        fields = []
        params: List[Any] = []
        for key in (
            "title",
            "contract_no",
            "cloud_uid",
            "effective_from",
            "effective_to",
            "status",
            "priority",
            "notes",
        ):
            if key in payload:
                fields.append(f"{key} = %s")
                params.append(payload[key])
        if "rules" in payload:
            fields.append("rules_json = %s")
            params.append(json.dumps(payload["rules"], ensure_ascii=False))

        if not fields:
            return existing

        params.append(contract_id)
        self.db.execute(
            f"UPDATE framework_contracts SET {', '.join(fields)} WHERE id = %s",
            tuple(params),
        )
        result = self.get_contract(contract_id)
        assert result is not None
        return result

    def publish(self, contract_id: str) -> Dict[str, Any]:
        """确认发布：draft → active；同账号其它 active 自动归档（互斥生效）。"""
        existing = self.get_contract(contract_id)
        if not existing:
            raise ValueError("合同不存在")
        account_name = existing.get("account_name") or ""
        others = self.db.query(
            """
            SELECT id FROM framework_contracts
            WHERE account_name = %s AND status = 'active' AND id != %s
            """,
            (account_name, contract_id),
        )
        for row in others or []:
            oid = row.get("id") if isinstance(row, dict) else None
            if oid:
                self.update_contract(oid, {"status": "archived"})
                logger.info("发布合同 %s：已归档同账号旧生效合同 %s", contract_id, oid)
        return self.update_contract(contract_id, {"status": "active"})

    def archive(self, contract_id: str) -> Dict[str, Any]:
        return self.update_contract(contract_id, {"status": "archived"})

    def delete_contract(self, contract_id: str) -> None:
        row = self.get_contract(contract_id)
        if not row:
            return
        pdf = row.get("source_pdf_path")
        self.db.execute("DELETE FROM framework_contracts WHERE id = %s", (contract_id,))
        if pdf:
            try:
                Path(pdf).unlink(missing_ok=True)
            except Exception as e:
                logger.warning("删除合同 PDF 失败: %s", e)

    @staticmethod
    def _as_date(v: Any) -> Optional[date]:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(str(v)[:10])
        except Exception:
            return None

    @staticmethod
    def _row_to_dict(row: Dict[str, Any]) -> Dict[str, Any]:
        rules = row.get("rules_json")
        if isinstance(rules, str):
            try:
                rules = json.loads(rules)
            except Exception:
                rules = dict(DEFAULT_RULES)
        elif rules is None:
            rules = dict(DEFAULT_RULES)

        meta = row.get("parse_meta_json")
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}

        def fmt(v: Any) -> Any:
            if isinstance(v, (datetime, date)):
                return v.isoformat()
            return v

        return {
            "id": row.get("id"),
            "account_name": row.get("account_name"),
            "title": row.get("title"),
            "contract_no": row.get("contract_no"),
            "cloud_uid": row.get("cloud_uid"),
            "effective_from": fmt(row.get("effective_from")),
            "effective_to": fmt(row.get("effective_to")),
            "status": row.get("status"),
            "priority": int(row.get("priority") or 0),
            "rules": rules,
            "source_pdf_path": row.get("source_pdf_path"),
            "source_pdf_name": row.get("source_pdf_name"),
            "parse_meta": meta or {},
            "notes": row.get("notes"),
            "created_at": fmt(row.get("created_at")),
            "updated_at": fmt(row.get("updated_at")),
        }
