# -*- coding: utf-8 -*-
"""阿里云框架服务协议 PDF 解析（预填规则，需人工确认）"""

from __future__ import annotations

import logging
import re
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PARSER_VERSION = "1.0"

# 常见地域名 → 账单中可能出现的写法
REGION_ALIASES = {
    "中国香港": ["中国香港", "cn-hongkong", "香港"],
    "华东2（上海）": ["华东2（上海）", "cn-shanghai", "上海"],
    "新加坡": ["新加坡", "ap-southeast-1"],
    "马来西亚（吉隆坡）": ["马来西亚（吉隆坡）", "ap-southeast-3", "吉隆坡"],
    "美国（硅谷）": ["美国（硅谷）", "us-west-1", "硅谷"],
    "英国（伦敦）": ["英国（伦敦）", "eu-west-1", "伦敦"],
}


def parse_framework_contract_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """解析框架合同 PDF，返回可编辑的预填结构。

    Returns:
        title/contract_no/cloud_uid/effective_from/effective_to/rules/warnings/...
    """
    text = _extract_text(pdf_bytes)
    warnings: List[str] = []
    if len(text) < 200:
        warnings.append("PDF 文本提取过短，请核对是否为扫描件，并手工补全规则")

    title = "框架服务协议" if "框架服务协议" in text else "云厂商框架合同"
    contract_no = _first_group(
        text,
        [
            r"(ALY\d{10,}_\w+)",
            r"合同编号[:：\s]*([A-Za-z0-9_\-]+)",
        ],
    )
    cloud_uid = _first_group(
        text,
        [
            r"UID[：:\s]*(\d{10,})",
            r"账号.*?UID[：:\s\(]*(\d{10,})",
        ],
    )

    effective_from, effective_to = _parse_validity(text)
    if not effective_from:
        warnings.append("未解析到协议有效期起始日，请手工填写")
    if not effective_to:
        warnings.append("未解析到协议有效期结束日，请手工填写")

    discount = _parse_discount(text)
    if discount is None:
        discount = 0.50
        warnings.append("未明确解析到折扣比例，默认按 5 折（0.5）预填，请确认")

    months = _parse_allowed_months(text)
    if not months:
        months = [3, 6, 12]
        warnings.append("未解析到订购时长白名单，默认预填 3/6/12 月，请确认")

    families = _parse_ecs_families(text)
    if not families:
        warnings.append("未解析到 ECS 规格族名单，请手工补充")

    regions = _parse_regions(text)
    if not regions:
        warnings.append("未解析到优惠地域，请手工补充")

    products: List[Dict[str, Any]] = []
    if "ECS" in text or "云服务器" in text:
        products.append(
            {
                "product_keys": ["云服务器 ECS", "ECS", "云服务器"],
                "subscription_required": True,
                "allowed_months": months,
                "regions": regions or ["*"],
                "instance_families": families or [],
                "exclude_gpu": True,
                "label": "ECS 包年包月",
            }
        )
    if "RDS" in text or "关系型数据库" in text:
        products.append(
            {
                "product_keys": ["云数据库 RDS", "RDS", "关系型数据库"],
                "subscription_required": True,
                "allowed_months": months,
                "regions": ["*"],
                "instance_families": [],
                "exclude_gpu": False,
                "label": "RDS 包月",
            }
        )
    if not products:
        warnings.append("未识别到 ECS/RDS 覆盖产品，请手工添加 products 规则")

    notes_bits = []
    if "择优" in text:
        notes_bits.append("合同约定与官网活动择优、不叠加")
    if "未在下表" in text or "未列入下表" in text:
        notes_bits.append("未列入附件一的产品按官网目录价")

    return {
        "title": title,
        "contract_no": contract_no,
        "cloud_uid": cloud_uid,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "priority": 10,
        "rules": {
            "framework_discount": discount,
            "products": products,
        },
        "notes": "；".join(notes_bits) if notes_bits else "PDF 解析预填，请确认后发布",
        "warnings": warnings,
        "text_chars": len(text),
        "parser_version": PARSER_VERSION,
        "preview_excerpt": text[:1200],
    }


def _extract_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError("缺少 pypdf，请安装：pip install pypdf") from e

    reader = PdfReader(BytesIO(pdf_bytes))
    parts: List[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception as e:
            logger.warning("PDF 页提取失败: %s", e)
    # 压缩空白，保留换行便于正则
    text = "\n".join(parts)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _first_group(text: str, patterns: List[str]) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _parse_validity(text: str) -> Tuple[Optional[str], Optional[str]]:
    m = re.search(
        r"有效期为\s*(\d{4}-\d{2}-\d{2})\s*\d{0,2}:?\d{0,2}:?\d{0,2}\s*至\s*(\d{4}-\d{2}-\d{2})",
        text,
    )
    if m:
        return m.group(1), m.group(2)
    m = re.search(
        r"(\d{4}-\d{2}-\d{2})\s*.{0,8}至\s*(\d{4}-\d{2}-\d{2})",
        text,
    )
    if m and "有效期" in text[max(0, m.start() - 40) : m.start() + 10]:
        return m.group(1), m.group(2)
    return None, None


def _parse_discount(text: str) -> Optional[float]:
    """5折 → 0.5（相对目录价的应付比例？）

    业务上「5折」= 半价 = 账单折扣约 50%。本系统 framework_discount 表示
    **优惠幅度**（0.5 = 省一半），与账单 invoice_discount/(pay+discount) 对齐。
    """
    # 必须先匹配小数折（如 4.5折），否则会被「5折」子串误命中
    if re.search(r"4\.5\s*折|4\.\s*5\s*折", text):
        return 0.55
    if re.search(r"(?<![.\d])5\s*折", text):
        return 0.50
    if re.search(r"(?<![.\d])6\s*折", text):
        return 0.40
    m = re.search(r"折扣比例[^\d]{0,12}(\d+(?:\.\d+)?)\s*%", text)
    if m:
        return min(0.95, float(m.group(1)) / 100.0)
    m = re.search(r"(\d+(?:\.\d+)?)\s*折", text)
    if m:
        # N折 → 优惠幅度 = 1 - N/10
        n = float(m.group(1))
        if 1 <= n <= 9.9:
            return round(1.0 - n / 10.0, 2)
    return None


def _parse_allowed_months(text: str) -> List[int]:
    found = set()
    # 附件常见写法：3个月,6个月,1年
    if re.search(r"3\s*个?月", text):
        found.add(3)
    if re.search(r"6\s*个?月", text):
        found.add(6)
    if re.search(r"1\s*年|12\s*个?月", text):
        found.add(12)
    if re.search(r"9\s*个?月", text):
        found.add(9)
    # 仅当附件一附近出现时更可信；这里用整体命中即可，人工可改
    return sorted(found)


def _parse_ecs_families(text: str) -> List[str]:
    """优先抽取「等于」白名单段，避免把「排除部分规格」里的族名收进来。"""
    families: set = set()

    # 1) 优先：等于)实例规格族 后的短名单（跨行，直到排除/不等于）
    for m in re.finditer(
        r"\(?\s*等\s*于\s*\)?\s*实\s*例\s*规\s*格\s*族\s*[:：]?",
        text,
        re.IGNORECASE,
    ):
        chunk = text[m.end() : m.end() + 500]
        cut = re.search(r"排除部分规格|以上条件下排除|\(不等于\)|不等于\s*GPU", chunk)
        if cut:
            chunk = chunk[: cut.start()]
        for fm in re.finditer(r"ecs\.([a-z0-9]+)", chunk, re.IGNORECASE):
            fam = f"ecs.{fm.group(1).lower()}"
            if _is_plausible_family(fam):
                families.add(fam)


    # 2) 常见商务短名单兜底（若正文能命中）
    for fam in (
        "ecs.r8i",
        "ecs.u1",
        "ecs.e",
        "ecs.g7",
        "ecs.g6e",
        "ecs.t5",
        "ecs.hfr9i",
        "ecs.g6",
        "ecs.c7",
        "ecs.r7",
    ):
        if fam in text.lower().replace(" ", "") or fam in text.lower():
            # 仅当出现在非「排除」邻近时更可信；这里作补充
            if fam not in families:
                # 检查附近 80 字是否在讲排除
                idx = text.lower().find(fam)
                if idx >= 0:
                    window = text[max(0, idx - 40) : idx + 40]
                    if "排除" not in window and "不等于" not in window:
                        families.add(fam)

    # 3) 仍为空则保守扫描全文短规格族，但强过滤内部码
    if not families:
        for m in re.finditer(r"ecs\.([a-z0-9]+)", text, re.IGNORECASE):
            fam = f"ecs.{m.group(1).lower()}"
            if _is_plausible_family(fam):
                families.add(fam)

    return sorted(families)[:20]


def _is_plausible_family(fam: str) -> bool:
    if re.search(r"\d+xlarge|large$|medium$|small$", fam):
        return False
    short = fam.split(".")[-1]
    if len(fam) > 24 or len(short) > 10:
        return False
    if short.startswith(("ebm", "sgn", "gn", "ga")):
        return False
    if short.endswith("-") or not re.match(r"^[a-z]+[0-9]*[a-z]*$", short):
        return False
    return True



def _parse_regions(text: str) -> List[str]:
    regions: List[str] = []
    for name, aliases in REGION_ALIASES.items():
        if name in text or any(a in text for a in aliases if len(a) > 2):
            # 存规范名 + 别名，扫描时宽松匹配
            regions.append(name)
            for a in aliases:
                if a not in regions:
                    regions.append(a)
    return regions
