#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询指定账号某年的账单按产品汇总（用于分析「资源少但账单高」的原因）

用法（需在已安装 CloudLens 依赖且能连 MySQL 的环境执行，如远端服务器或本地 venv）:
  python3 scripts/yearly_cost_by_product.py ydhl 2025
  python3 scripts/yearly_cost_by_product.py ydhl    # 默认去年

依赖: 项目依赖 + MySQL 中的 bill_items 已同步该账号对应年份的账单。
"""
import os
import sys
from decimal import Decimal

# 确保项目根在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    account_name = (sys.argv[1] if len(sys.argv) > 1 else "ydhl").strip()
    year = sys.argv[2] if len(sys.argv) > 2 else str(__import__("datetime").datetime.now().year - 1)
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    print(f"账号: {account_name}")
    print(f"统计年份: {year} ({start_date} ~ {end_date})")
    print("-" * 60)

    from cloudlens.core.config import ConfigManager
    from cloudlens.core.bill_storage import BillStorageManager

    cm = ConfigManager()
    account_config = cm.get_account(account_name)
    if not account_config:
        print(f"错误: 未找到账号 '{account_name}'，请检查配置。")
        sys.exit(1)

    account_id = f"{account_config.access_key_id[:10]}-{account_name}"
    storage = BillStorageManager()
    db = storage.db
    ph = storage._get_placeholder()

    # 先查是否有该账号的账单（兼容模糊匹配）
    rows_id = db.query(
        "SELECT DISTINCT account_id FROM bill_items WHERE account_id = " + ph + " LIMIT 1",
        (account_id,),
    )
    if not rows_id:
        rows_id = db.query(
            "SELECT DISTINCT account_id FROM bill_items WHERE account_id LIKE " + ph + " LIMIT 1",
            (f"%{account_name}%",),
        )
    if not rows_id:
        print("错误: 该账号在 bill_items 中无账单数据。")
        print("请先在控制台或通过 CLI 同步账单（如 cl bill sync），再运行本脚本。")
        sys.exit(1)

    aid = rows_id[0]["account_id"] if isinstance(rows_id[0], dict) else rows_id[0][0]
    if aid != account_id:
        print(f"提示: 使用模糊匹配的 account_id: {aid}")

    # 按产品汇总该年税前金额
    sql = f"""
        SELECT
            product_code,
            product_name,
            SUM(pretax_amount) AS total_pretax
        FROM bill_items
        WHERE account_id = {ph}
          AND billing_cycle >= {ph}
          AND billing_cycle <= {ph}
          AND pretax_amount IS NOT NULL
        GROUP BY product_code, product_name
        ORDER BY total_pretax DESC
    """
    start_cycle = f"{year}-01"
    end_cycle = f"{year}-12"
    rows = db.query(sql, (aid, start_cycle, end_cycle))

    if not rows:
        print("该账号在本年度无账单记录（或账期不在范围内）。")
        print("若去年账单在阿里云控制台可见，请同步账单到 CloudLens 后再查。")
        sys.exit(0)

    total = sum(
        float(r["total_pretax"] if isinstance(r, dict) else r[2] or 0) for r in rows
    )
    print(f"年度总成本（税前）: ¥{total:,.2f}\n")
    print("按产品汇总（金额从高到低）:")
    print("-" * 60)
    for r in rows:
        code = (r.get("product_code") or r[0]) or "-"
        name = (r.get("product_name") or r[1]) or code
        amt = float(r.get("total_pretax") or r[2] or 0)
        pct = (amt / total * 100) if total else 0
        print(f"  {name[:36]:36} ({code:20})  ¥{amt:>12,.2f}  ({pct:5.1f}%)")
    print("-" * 60)
    print("\n说明: 账单包含所有阿里云产品（ECS/RDS/OSS/流量/SLB/EIP/CDN 等），")
    print('      而「资源」页仅展示部分实例型资源（如 ECS、RDS、Redis），')
    print("      因此资源数量少、账单金额高是常见情况。")


if __name__ == "__main__":
    main()
