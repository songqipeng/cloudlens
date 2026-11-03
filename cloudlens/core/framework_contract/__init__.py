"""框架合同：存储、PDF 解析、省钱机会扫描"""

from .store import FrameworkContractStore
from .parser import parse_framework_contract_pdf
from .scanner import SavingsOpportunityScanner
from .report import render_savings_report_html

__all__ = [
    "FrameworkContractStore",
    "parse_framework_contract_pdf",
    "SavingsOpportunityScanner",
    "render_savings_report_html",
]
