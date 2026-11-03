# -*- coding: utf-8 -*-
"""框架合同 PDF 解析单测（有样例 PDF 时跑完整断言）"""

from pathlib import Path

import pytest

from cloudlens.core.framework_contract.parser import (
    _parse_discount,
    parse_framework_contract_pdf,
)

SAMPLE = Path("/Users/songqipeng/Downloads/103a4e3246ae2132fb96000o.pdf")
SAMPLE_ALT = Path(__file__).resolve().parents[2] / "artifacts" / "samples" / "framework-contract.pdf"


def test_parse_discount_prefers_decimal_over_substring():
    """4.5折 不得被「5折」子串误解析为 0.50。"""
    assert _parse_discount("优惠幅度为4.5折") == 0.55
    assert _parse_discount("优惠幅度为5折") == 0.50
    assert _parse_discount("优惠幅度为6折") == 0.40


@pytest.mark.skipif(
    not SAMPLE.exists() and not SAMPLE_ALT.exists(),
    reason="无样例框架合同 PDF",
)
def test_parse_aliyun_framework_pdf():
    path = SAMPLE if SAMPLE.exists() else SAMPLE_ALT
    result = parse_framework_contract_pdf(path.read_bytes())
    assert result["contract_no"]
    assert result["cloud_uid"]
    assert result["effective_from"]
    assert result["effective_to"]
    assert result["rules"]["framework_discount"] == 0.5
    products = result["rules"]["products"]
    assert any("ECS" in (p.get("label") or "") for p in products)
    ecs = next(p for p in products if "ECS" in (p.get("label") or ""))
    fams = set(ecs.get("instance_families") or [])
    assert "ecs.r8i" in fams
    assert "ecs.hfr9i" in fams or "ecs.g7" in fams
    assert 3 in ecs["allowed_months"] and 6 in ecs["allowed_months"]
