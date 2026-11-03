# -*- coding: utf-8 -*-
"""框架合同扫描器单测（可 mock DB）"""

from cloudlens.core.framework_contract.scanner import SavingsOpportunityScanner
from cloudlens.core.framework_contract.report import render_savings_report_html


def test_fmt_terms():
    assert SavingsOpportunityScanner._fmt_terms({6, 3, 1}) == "1个月、3个月、6个月"
    assert SavingsOpportunityScanner._fmt_terms(set()) == "无"


def test_product_covered():
    keys = ["云服务器 ECS", "RDS"]
    assert SavingsOpportunityScanner._product_covered("云服务器 ECS", keys)
    assert not SavingsOpportunityScanner._product_covered("负载均衡", keys)


def test_parse_family():
    cfg = "实例规格族:ecs.r8i;实例规格:4核 32G"
    assert SavingsOpportunityScanner._parse_family(cfg) == "ecs.r8i"


def test_render_report_html():
    html = render_savings_report_html(
        "cf",
        {
            "contract": {
                "configured": True,
                "title": "框架",
                "contract_no": "ALY1",
                "effective_from": "2026-05-18",
                "effective_to": "2027-05-17",
            },
            "summary": {
                "annual_savings_total": 1000,
                "by_type_annual_savings": {"framework_out_of_scope": 600, "idle_low_util": 400},
                "note": "测试",
            },
            "opportunities": [
                {
                    "type": "framework_out_of_scope",
                    "priority": "high",
                    "title": "框外：负载均衡",
                    "annual_savings": 600,
                    "description": "未列入附件一",
                    "recommendation": "纳入框架",
                }
            ],
        },
    )
    assert "省钱机会报告" in html
    assert "负载均衡" in html
    assert "¥600" in html


def test_scan_idle_annualizes():
    """闲置项按规格目录价 × 分级比例 ×12 → 年化；无合同也可扫描利用率。"""
    scanner = SavingsOpportunityScanner.__new__(SavingsOpportunityScanner)
    items = [
        {
            "instance_id": "i-idle1",
            "name": "low-cpu",
            "spec": "ecs.g7.xlarge",
            "metrics": {"avg_cpu": 1.2, "avg_memory": 10.0},
            "status": "Running",
            "level": "low_utilization",
            "priority": "P2",
        }
    ]
    ops = scanner._scan_idle(items)
    assert ops
    assert ops[0]["type"] == "idle_low_util"
    assert ops[0]["annual_savings"] > 0
    assert ops[0]["evidence"]["spec"] == "ecs.g7.xlarge"
    assert ops[0]["evidence"]["avg_cpu"] == 1.2


def test_match_product_rule():
    products = [
        {"label": "ECS", "product_keys": ["云服务器 ECS", "ECS"]},
        {"label": "RDS", "product_keys": ["云数据库 RDS", "RDS"]},
    ]
    assert SavingsOpportunityScanner._match_product_rule("云服务器 ECS", products)["label"] == "ECS"
    assert SavingsOpportunityScanner._match_product_rule("负载均衡", products) is None


def test_region_allowed():
    assert SavingsOpportunityScanner._region_allowed({"cn-hongkong"}, ["中国香港", "cn-hongkong"])
    assert SavingsOpportunityScanner._region_allowed({"cn-shanghai"}, ["*"])
    assert not SavingsOpportunityScanner._region_allowed(
        {"us-west-1"}, ["中国香港", "cn-hongkong"]
    )
    # 无地域信息不判违规
    assert SavingsOpportunityScanner._region_allowed(set(), ["cn-hongkong"])


def test_looks_like_gpu():
    assert SavingsOpportunityScanner._looks_like_gpu({"ecs.gn6i"}, set())
    assert SavingsOpportunityScanner._looks_like_gpu(set(), {"实例规格族:ecs.vgn6i"})
    assert not SavingsOpportunityScanner._looks_like_gpu({"ecs.r8i"}, {"4核 32G"})
    # a100 含 a10 子串，词边界后不应误判
    assert not SavingsOpportunityScanner._looks_like_gpu({"ecs.r8i"}, {"accel a100 board"})
    assert SavingsOpportunityScanner._looks_like_gpu(set(), {"nvidia t4"})
