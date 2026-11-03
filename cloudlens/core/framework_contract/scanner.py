# -*- coding: utf-8 -*-
"""省钱机会扫描：框架合规 + 弱建议 + 利用率"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from cloudlens.core.database import DatabaseFactory
from cloudlens.core.framework_contract.store import FrameworkContractStore

logger = logging.getLogger(__name__)


def _estimate_monthly_from_spec(spec: str) -> float:
    if not spec or not isinstance(spec, str):
        return 300.0
    if not spec.startswith("ecs."):
        return 300.0
    parts = spec.split(".")
    size = parts[-1].lower() if parts else ""
    mul = 1.0
    if size == "small":
        mul = 0.25
    elif size == "medium":
        mul = 0.5
    elif size == "large":
        mul = 1.0
    elif size == "xlarge":
        mul = 2.0
    else:
        m = re.match(r"^(\d+)xlarge$", size)
        if m:
            mul = max(1.0, float(m.group(1)) * 2.0)
    return round(320.0 * mul, 2)


class SavingsOpportunityScanner:
    """统一扫描引擎，输出年化可省机会列表。"""

    def __init__(self) -> None:
        self.db = DatabaseFactory.create_adapter("mysql")
        self.store = FrameworkContractStore()

    def scan(
        self,
        account_name: str,
        bill_account_id: str,
        idle_items: Optional[List[Dict[str, Any]]] = None,
        billing_cycle: Optional[str] = None,
    ) -> Dict[str, Any]:
        all_active = [
            c
            for c in self.store.list_contracts(account_name)
            if c.get("status") == "active"
        ]
        contract = self.store.get_active_for_period(account_name, billing_cycle)
        period_miss = bool(billing_cycle and all_active and not contract)
        opportunities: List[Dict[str, Any]] = []

        if contract:
            opportunities.extend(
                self._scan_framework(bill_account_id, contract)
            )
        else:
            opportunities.extend(self._scan_weak_subscription(bill_account_id))

        if idle_items:
            opportunities.extend(self._scan_idle(idle_items))

        opportunities.sort(
            key=lambda x: (
                {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "low"), 9),
                -float(x.get("annual_savings") or 0),
            )
        )

        by_type: Dict[str, float] = defaultdict(float)
        for o in opportunities:
            by_type[o["type"]] += float(o.get("annual_savings") or 0)

        note = "金额为年化可省估算；框外与未按约、利用率之间可能有重叠，勿简单承诺相加"
        if period_miss:
            note = (
                f"账期 {billing_cycle} 无匹配生效合同（已有 {len(all_active)} 份 active，"
                f"但有效期未覆盖该月），当前仅展示弱建议与利用率。"
            )
        elif not contract:
            note = "尚未发布生效的框架合同；当前为弱建议与利用率扫描。"

        return {
            "contract": {
                "id": contract.get("id") if contract else None,
                "title": contract.get("title") if contract else None,
                "contract_no": contract.get("contract_no") if contract else None,
                "effective_from": contract.get("effective_from") if contract else None,
                "effective_to": contract.get("effective_to") if contract else None,
                "status": contract.get("status") if contract else None,
                "configured": bool(contract),
                "period_miss": period_miss,
                "billing_cycle": billing_cycle,
            },
            "opportunities": opportunities,
            "summary": {
                "total_opportunities": len(opportunities),
                "annual_savings_total": round(
                    sum(float(o.get("annual_savings") or 0) for o in opportunities), 2
                ),
                "by_type_annual_savings": {k: round(v, 2) for k, v in by_type.items()},
                "high_priority_count": sum(
                    1 for o in opportunities if o.get("priority") == "high"
                ),
                "medium_priority_count": sum(
                    1 for o in opportunities if o.get("priority") == "medium"
                ),
                "low_priority_count": sum(
                    1 for o in opportunities if o.get("priority") == "low"
                ),
                "note": note,
            },
        }

    # ---------- 框架合规 ----------
    def _scan_framework(
        self, bill_account_id: str, contract: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        rules = contract.get("rules") or {}
        fw_discount = float(rules.get("framework_discount") or 0.50)
        products = rules.get("products") or []
        covered_keys = self._all_product_keys(products)

        out: List[Dict[str, Any]] = []
        out.extend(
            self._scan_out_of_scope(bill_account_id, covered_keys, fw_discount, contract)
        )
        out.extend(self._scan_wrong_purchase(bill_account_id, products, fw_discount, contract))
        return out

    def _scan_out_of_scope(
        self,
        bill_account_id: str,
        covered_keys: List[str],
        fw_discount: float,
        contract: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        rows = self.db.query(
            """
            SELECT product_name,
                   ROUND(SUM(pretax_amount), 2) spend,
                   COUNT(DISTINCT billing_cycle) months
            FROM bill_items
            WHERE account_id = %s
            GROUP BY product_name
            HAVING spend >= 1000
            ORDER BY spend DESC
            """,
            (bill_account_id,),
        )
        results = []
        for r in rows:
            name = r.get("product_name") or ""
            if self._product_covered(name, covered_keys):
                continue
            spend = float(r.get("spend") or 0)
            months = max(int(r.get("months") or 1), 1)
            monthly = spend / months
            # 框外：假设谈入框架后可拿到 framework_discount 优惠幅度
            annual = round(monthly * 12 * fw_discount * 0.5, 2)  # 保守：按框架折扣的一半估算谈价空间
            if annual < 200:
                continue
            results.append(
                {
                    "id": f"oos:{name}",
                    "type": "framework_out_of_scope",
                    "category": "框架合规",
                    "priority": "high" if annual >= 3000 else "medium",
                    "title": f"框外产品：{name}",
                    "description": (
                        f"未列入生效合同附件一，无框架价保障。窗口实付约 ¥{spend:,.0f}，"
                        f"月均约 ¥{monthly:,.0f}。"
                    ),
                    "annual_savings": annual,
                    "resource_count": 1,
                    "action": "negotiate_into_framework",
                    "recommendation": "评估纳入下期框架，或压用量/换有折扣方案",
                    "evidence": {
                        "product_name": name,
                        "window_spend": spend,
                        "months": months,
                        "monthly_spend": round(monthly, 2),
                        "contract_id": contract.get("id"),
                        "estimate_note": "年化可省按「月均×12×框架折扣×50%」保守估算谈价空间",
                    },
                }
            )
        return results

    def _scan_wrong_purchase(
        self,
        bill_account_id: str,
        products: List[Dict[str, Any]],
        fw_discount: float,
        contract: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        if not products:
            return []

        rows = self.db.query(
            """
            SELECT instance_id, product_name, subscription_type, service_period,
                   service_period_unit, region, instance_config,
                   SUM(pretax_amount) pretax, SUM(invoice_discount) disc,
                   MIN(billing_cycle) first_m, MAX(billing_cycle) last_m,
                   COUNT(DISTINCT billing_cycle) months
            FROM bill_items
            WHERE account_id = %s
            GROUP BY instance_id, product_name, subscription_type, service_period,
                     service_period_unit, region, instance_config
            HAVING pretax >= 100
            """,
            (bill_account_id,),
        )

        # 按实例聚合主购买模式
        by_inst: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for r in rows:
            name = r.get("product_name") or ""
            rule = self._match_product_rule(name, products)
            if not rule:
                continue
            iid = r.get("instance_id") or "(none)"
            key = (iid, name)
            slot = by_inst.setdefault(
                key,
                {
                    "instance_id": iid,
                    "product_name": name,
                    "rule": rule,
                    "pay_month": 0.0,
                    "pay_payg": 0.0,
                    "pay_day": 0.0,
                    "disc_month": 0.0,
                    "month_terms": set(),
                    "families": set(),
                    "regions": set(),
                    "configs": set(),
                    "first_m": r.get("first_m"),
                    "last_m": r.get("last_m"),
                    "months": int(r.get("months") or 1),
                },
            )
            pretax = float(r.get("pretax") or 0)
            disc = float(r.get("disc") or 0)
            unit = r.get("service_period_unit") or ""
            sub = r.get("subscription_type") or ""
            cfg = r.get("instance_config") or ""
            if cfg:
                slot["configs"].add(str(cfg)[:500])
            fam = self._parse_family(cfg)
            if fam:
                slot["families"].add(fam)
            if r.get("region"):
                slot["regions"].add(r["region"])
            # 多订阅类型行聚合时取最大账期跨度，避免只保留首行 months 导致年化失真
            slot["months"] = max(slot["months"], int(r.get("months") or 1))

            if sub == "PayAsYouGo":
                slot["pay_payg"] += pretax
            elif unit == "月":
                slot["pay_month"] += pretax
                slot["disc_month"] += disc
                try:
                    slot["month_terms"].add(int(float(r.get("service_period"))))
                except Exception:
                    pass
            elif unit == "天":
                slot["pay_day"] += pretax
            elif unit == "年":
                slot["pay_month"] += pretax
                slot["disc_month"] += disc
                try:
                    slot["month_terms"].add(int(float(r.get("service_period"))) * 12)
                except Exception:
                    pass

            if r.get("first_m") and (
                not slot["first_m"] or str(r["first_m"]) < str(slot["first_m"])
            ):
                slot["first_m"] = r["first_m"]
            if r.get("last_m") and (
                not slot["last_m"] or str(r["last_m"]) > str(slot["last_m"])
            ):
                slot["last_m"] = r["last_m"]

        results: List[Dict[str, Any]] = []
        for slot in by_inst.values():
            rule = slot["rule"]
            allowed: Set[int] = set(int(x) for x in (rule.get("allowed_months") or [3, 6, 12]))
            families_rule = [f.lower() for f in (rule.get("instance_families") or [])]
            require_sub = bool(rule.get("subscription_required", True))

            pay_m = slot["pay_month"]
            pay_g = slot["pay_payg"]
            terms: Set[int] = slot["month_terms"]
            fams: Set[str] = {f.lower() for f in slot["families"] if f}

            issues = []
            if require_sub and pay_g > pay_m and pay_g >= 200:
                issues.append("payg")
            if families_rule and fams and not (fams & set(families_rule)):
                issues.append("family")
            if terms and not (terms & allowed):
                issues.append("duration")
            elif terms and (terms - allowed) and not (terms & allowed):
                issues.append("duration")
            # 只有 1 个月、或夹杂 1 个月且无合规时长
            if 1 in terms and not (terms & allowed):
                if "duration" not in issues:
                    issues.append("duration")

            # 地域白名单（规则含 * 则不限）
            regions_rule = [str(x) for x in (rule.get("regions") or []) if x]
            slot_regions: Set[str] = {str(r) for r in slot["regions"] if r}
            if regions_rule and not self._region_allowed(slot_regions, regions_rule):
                issues.append("region")

            # 排除 GPU：规格族或配置含 GPU 特征则不合规
            if rule.get("exclude_gpu") and self._looks_like_gpu(fams, slot.get("configs") or set()):
                issues.append("gpu")

            if not issues:
                # 部分合规：有合规时长但也有 1 个月
                if 1 in terms and (terms & allowed):
                    issues.append("mixed_duration")
                else:
                    continue

            # 年化：相关实付月均 ×12 × (框架折扣 - 当前整月折扣)
            relevant = pay_m + pay_g
            months = max(slot["months"], 1)
            monthly = relevant / months
            cur_disc = 0.0
            if pay_m + slot["disc_month"] > 0:
                cur_disc = slot["disc_month"] / (pay_m + slot["disc_month"])
            if "payg" in issues and pay_g >= pay_m:
                cur_disc = min(cur_disc, 0.05)
            lift = max(0.0, fw_discount - cur_disc)
            annual = round(monthly * 12 * lift, 2)
            if annual < 100 and "mixed_duration" not in issues:
                continue

            reason_map = {
                "payg": "按量采购，框架要求包年包月",
                "family": f"规格族 {', '.join(sorted(fams)) or '?'} 不在合同名单",
                "duration": f"整月时长 {self._fmt_terms(terms)} 不在白名单 {sorted(allowed)}",
                "mixed_duration": f"混用时长 {self._fmt_terms(terms)}，含不合规的 1 个月档",
                "region": f"地域 {', '.join(sorted(slot_regions)) or '?'} 不在合同优惠地域",
                "gpu": "合同排除 GPU 规格，当前实例疑似 GPU",
            }
            reason = "；".join(reason_map[i] for i in issues if i in reason_map)
            priority = "high" if annual >= 2000 or "payg" in issues else "medium"

            results.append(
                {
                    "id": f"wrong:{slot['instance_id']}:{slot['product_name']}",
                    "type": "framework_wrong_purchase",
                    "category": "框架合规",
                    "priority": priority,
                    "title": f"未按约采购：{slot['product_name']} {slot['instance_id'][:22]}",
                    "description": reason,
                    "annual_savings": annual,
                    "resource_count": 1,
                    "action": "align_to_framework",
                    "recommendation": "改为合同允许的包年包月时长与规格族，避免 1 个月/按量",
                    "evidence": {
                        "instance_id": slot["instance_id"],
                        "product_name": slot["product_name"],
                        "families": sorted(fams),
                        "regions": sorted(slot_regions),
                        "month_terms": sorted(terms),
                        "pay_month": round(pay_m, 2),
                        "pay_payg": round(pay_g, 2),
                        "pay_day_fragment": round(slot["pay_day"], 2),
                        "current_month_discount": round(cur_disc * 100, 1),
                        "framework_discount": round(fw_discount * 100, 1),
                        "contract_id": contract.get("id"),
                        "period": f"{slot['first_m']}~{slot['last_m']}",
                        "issues": issues,
                    },
                }
            )
        return results

    def _scan_weak_subscription(self, bill_account_id: str) -> List[Dict[str, Any]]:
        """无合同时：长期按量弱建议（保守）"""
        rows = self.db.query(
            """
            SELECT instance_id, product_name,
                   SUM(pretax_amount) spend,
                   COUNT(DISTINCT billing_cycle) months,
                   AVG(CASE
                     WHEN (pretax_amount + invoice_discount) > 0
                     THEN invoice_discount / (pretax_amount + invoice_discount)
                     ELSE 0 END) avg_disc
            FROM bill_items
            WHERE account_id = %s AND subscription_type = 'PayAsYouGo'
              AND instance_id IS NOT NULL AND instance_id != ''
            GROUP BY instance_id, product_name
            HAVING months >= 3 AND spend >= 500
            ORDER BY spend DESC
            LIMIT 40
            """,
            (bill_account_id,),
        )
        results = []
        for r in rows:
            spend = float(r.get("spend") or 0)
            months = max(int(r.get("months") or 1), 1)
            monthly = spend / months
            # 弱建议：假设转包年多 13% 优惠
            annual = round(monthly * 12 * 0.13, 2)
            if annual < 150:
                continue
            results.append(
                {
                    "id": f"weak:{r.get('instance_id')}",
                    "type": "weak_subscription",
                    "category": "采购优化",
                    "priority": "low" if annual < 800 else "medium",
                    "title": f"长期按量：{r.get('product_name')} {str(r.get('instance_id'))[:20]}",
                    "description": (
                        f"已按量运行约 {months} 个月，窗口实付 ¥{spend:,.0f}。"
                        f"未配置框架合同时仅作保守转包年建议。"
                    ),
                    "annual_savings": annual,
                    "resource_count": 1,
                    "action": "consider_subscription",
                    "recommendation": "导入框架合同后可精确判断；或评估转 3/6/12 月包年",
                    "evidence": {
                        "instance_id": r.get("instance_id"),
                        "product_name": r.get("product_name"),
                        "months": months,
                        "window_spend": spend,
                        "estimate_note": "无合同时按 +13% 优惠幅度粗估",
                    },
                }
            )
        return results

    def _scan_idle(self, idle_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for item in idle_items:
            metrics = item.get("metrics") or {}
            cpu = metrics.get("avg_cpu")
            if cpu is None:
                cpu = item.get("avg_cpu", item.get("cpu_avg"))
            mem = metrics.get("avg_memory")
            if mem is None:
                mem = item.get("avg_memory", item.get("memory_avg"))
            spec = item.get("spec") or item.get("instance_type") or ""
            monthly = _estimate_monthly_from_spec(spec)
            priority = item.get("priority") or "P2"
            level = str(item.get("level") or item.get("tier") or "")
            # 按闲置分级定可省比例，再用 CPU/内存微调
            if level in ("critical_idle", "stopped_prepaid") or priority == "P1":
                ratio = 0.55
            elif level in ("low_utilization", "low_util") or priority == "P2":
                ratio = 0.30
            elif cpu is not None and cpu < 1 and (mem is None or mem < 50):
                ratio = 0.45
            elif cpu is not None and cpu < 5:
                ratio = 0.30
            else:
                ratio = 0.20
            if mem is not None and mem >= 70 and level != "stopped_prepaid":
                ratio = min(ratio, 0.15)
            annual = round(monthly * ratio * 12, 2)
            if annual < 100:
                continue
            iid = item.get("instance_id") or item.get("id") or ""
            name = item.get("name") or item.get("instance_name") or iid
            results.append(
                {
                    "id": f"idle:{iid}",
                    "type": "idle_low_util",
                    "category": "利用率",
                    "priority": "high" if priority == "P1" else "medium",
                    "title": f"低利用率：{name}",
                    "description": (
                        f"{spec} · CPU {cpu if cpu is not None else '—'}%"
                        f" / 内存 {mem if mem is not None else '—'}%"
                        f"（{item.get('level_label') or item.get('level') or priority}）"
                    ),
                    "annual_savings": annual,
                    "resource_count": 1,
                    "action": "downsize_or_release",
                    "recommendation": item.get("suggestion") or "评估降配或合并释放",
                    "evidence": {
                        "instance_id": iid,
                        "spec": spec,
                        "level": level,
                        "priority": priority,
                        "avg_cpu": cpu,
                        "avg_memory": mem,
                        "savings_ratio": ratio,
                        "estimated_monthly_list": monthly,
                        "estimate_note": "按规格目录价×分级降配比例年化，偏上限",
                    },
                }
            )
        return results

    # ---------- helpers ----------
    @staticmethod
    def _all_product_keys(products: List[Dict[str, Any]]) -> List[str]:
        keys: List[str] = []
        for p in products:
            keys.extend(p.get("product_keys") or [])
        return keys

    @staticmethod
    def _product_covered(name: str, keys: List[str]) -> bool:
        n = name or ""
        for k in keys:
            if k and k in n:
                return True
        return False

    @staticmethod
    def _match_product_rule(
        name: str, products: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        for p in products:
            for k in p.get("product_keys") or []:
                if k and k in name:
                    return p
        return None

    @staticmethod
    def _parse_family(cfg: str) -> Optional[str]:
        if not cfg:
            return None
        m = re.search(r"实例规格族[:：]\s*([a-zA-Z0-9.\-]+)", cfg)
        if m:
            return m.group(1).lower()
        m = re.search(r"(ecs\.[a-z0-9]+)", cfg, re.I)
        return m.group(1).lower() if m else None

    @staticmethod
    def _fmt_terms(terms: Set[int]) -> str:
        if not terms:
            return "无"
        return "、".join(f"{t}个月" for t in sorted(terms))

    @staticmethod
    def _normalize_region_token(token: str) -> str:
        return re.sub(r"[\s（）()]", "", (token or "").lower())

    @classmethod
    def _region_allowed(cls, actual: Set[str], allowed: List[str]) -> bool:
        """账单地域是否落在合同 regions（支持 * / 别名子串匹配）。"""
        if not allowed or any(str(a).strip() == "*" for a in allowed):
            return True
        if not actual:
            # 无地域信息时不贸然判违规
            return True
        norms = [cls._normalize_region_token(a) for a in allowed if a]
        for region in actual:
            rn = cls._normalize_region_token(region)
            if not rn:
                continue
            for an in norms:
                if not an:
                    continue
                if an in rn or rn in an:
                    return True
        return False

    @staticmethod
    def _looks_like_gpu(families: Set[str], configs: Set[str]) -> bool:
        blob = " ".join(sorted(families) + sorted(configs)).lower()
        # 用词边界/规格族前缀，避免 t4/a10 子串误伤（如 a100 含 a10）
        patterns = (
            r"\bgpu\b",
            r"ecs\.gn",
            r"ecs\.vgn",
            r"ecs\.ebmgn",
            r"ecs\.sccgn",
            r"nvidia",
            r"(?<![a-z0-9])t4(?![a-z0-9])",
            r"(?<![a-z0-9])a10(?![a-z0-9])",
            r"(?<![a-z0-9])v100(?![a-z0-9])",
            r"(?<![a-z0-9])p100(?![a-z0-9])",
        )
        return any(re.search(p, blob) for p in patterns)
