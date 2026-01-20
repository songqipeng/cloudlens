#!/usr/bin/env python3
"""
修复仪表盘数据显示 - 直接从数据库查询
"""

from cloudlens.core.database import get_database_adapter
from cloudlens.core.config import ConfigManager
from datetime import datetime, timedelta

def get_dashboard_summary_from_db(account_name=None):
    """直接从数据库获取仪表盘摘要数据"""

    db = get_database_adapter()

    # 如果没有指定账号，从配置中获取第一个
    if not account_name:
        cm = ConfigManager()
        accounts = cm.list_accounts()
        if accounts:
            account_name = accounts[0].name
        else:
            return {"error": "No account configured"}

    # 获取当前月份和上月
    now = datetime.now()
    current_cycle = now.strftime("%Y-%m")
    first_day_this_month = now.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    last_cycle = last_day_last_month.strftime("%Y-%m")

    # 查询本月成本
    current_month_query = f"""
        SELECT SUM(payment_amount) as total_cost
        FROM bill_items
        WHERE account_id = '{account_name}'
        AND billing_cycle = '{current_cycle}'
    """
    current_result = db.query(current_month_query)
    current_cost = float(current_result[0]['total_cost'] or 0) if current_result else 0.0

    # 查询上月成本
    last_month_query = f"""
        SELECT SUM(payment_amount) as total_cost
        FROM bill_items
        WHERE account_id = '{account_name}'
        AND billing_cycle = '{last_cycle}'
    """
    last_result = db.query(last_month_query)
    last_cost = float(last_result[0]['total_cost'] or 0) if last_result else 0.0

    # 计算趋势
    if last_cost > 0:
        trend_pct = ((current_cost - last_cost) / last_cost) * 100
        if trend_pct > 5:
            cost_trend = f"上升 {trend_pct:.1f}%"
        elif trend_pct < -5:
            cost_trend = f"下降 {abs(trend_pct):.1f}%"
        else:
            cost_trend = "基本持平"
    else:
        trend_pct = 0.0
        cost_trend = "数据不足"

    # 查询总记录数和金额
    total_query = f"""
        SELECT
            COUNT(DISTINCT billing_cycle) as total_months,
            COUNT(*) as total_records,
            SUM(payment_amount) as total_amount
        FROM bill_items
        WHERE account_id = '{account_name}'
    """
    total_result = db.query(total_query)
    total_info = total_result[0] if total_result else {}

    summary = {
        "account": account_name,
        "total_cost": current_cost,
        "idle_count": 0,  # 需要单独查询
        "cost_trend": cost_trend,
        "trend_pct": round(trend_pct, 2),
        "total_resources": 0,  # 需要从资源表查询
        "resource_breakdown": {
            "ecs": 0,
            "rds": 0,
            "redis": 0
        },
        "alert_count": 0,
        "tag_coverage": 0.0,
        "savings_potential": 0.0,
        "loading": False,
        "data_info": {
            "total_months": total_info.get('total_months', 0),
            "total_records": total_info.get('total_records', 0),
            "total_amount": float(total_info.get('total_amount') or 0),
            "current_cycle": current_cycle,
            "last_cycle": last_cycle
        }
    }

    return summary

if __name__ == "__main__":
    import sys

    account = sys.argv[1] if len(sys.argv) > 1 else None

    summary = get_dashboard_summary_from_db(account)

    import json
    print(json.dumps(summary, indent=2, ensure_ascii=False))
