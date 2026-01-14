import requests
import json
import sys
import os
from datetime import datetime

# 确保能导入本地模块
sys.path.append(os.getcwd())

from cloudlens.core.config import ConfigManager
from cloudlens.providers.aliyun.provider import AliyunProvider
from web.backend.api_cost import _get_billing_overview_totals

BASE_URL = "http://localhost:8000/api"
ACCOUNT_NAME = "ydzn"

def log(msg):
    print(f"[*] {msg}")

def verify_cost():
    log("=== 开始验证 Cost 摘要一致性 ===")
    
    # 1. 从 API 获取摘要
    try:
        api_res = requests.get(f"{BASE_URL}/dashboard/summary", params={"account": ACCOUNT_NAME, "force_refresh": "false"})
        api_data = api_res.json()
        api_total_cost = api_data["data"]["total_cost"]
        log(f"API 报告总成本: {api_total_cost}")
    except Exception as e:
        log(f"获取 API 摘要失败: {e}")
        return False

    # 2. 直接调用后端计费函数获取数据
    try:
        cm = ConfigManager()
        account_config = cm.get_account(ACCOUNT_NAME)
        
        now = datetime.now()
        current_cycle = now.strftime("%Y-%m")
        
        log(f"调用 _get_billing_overview_totals 获取 {current_cycle} 数据...")
        # force_refresh=True 以确保获取最新数据
        totals = _get_billing_overview_totals(account_config, billing_cycle=current_cycle, force_refresh=True)
        
        sdk_total_cost = float(totals.get("total_pretax") or 0.0)
        log(f"SDK 计算出的 pretax 成本: {sdk_total_cost}")
        
        if abs(api_total_cost - sdk_total_cost) > 1.0: # 允许 1 元以内的误差
             log(f"❌ 成本不一致！API={api_total_cost}, SDK={sdk_total_cost}")
             return False
        else:
            log("✅ 成本验证通过。")
            return True
    except Exception as e:
        log(f"成本验证过程中出错: {e}")
        return False

if __name__ == "__main__":
    verify_cost()
