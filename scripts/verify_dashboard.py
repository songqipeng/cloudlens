import requests
import json
import sys
import os

# 确保能导入本地模块
sys.path.append(os.getcwd())

from cloudlens.core.config import ConfigManager
from cloudlens.cli.utils import get_provider
from cloudlens.core.services.analysis_service import AnalysisService

BASE_URL = "http://localhost:8000/api"
ACCOUNT_NAME = "ydzn"

def log(msg):
    print(f"[*] {msg}")

def verify_dashboard():
    log("=== 开始验证 Dashboard 摘要一致性 (全区域) ===")
    
    # 1. 从 API 获取摘要 (不强制刷新，使用之前的缓存)
    try:
        log("获取 API Dashboard Summary (force_refresh=false)...")
        api_res = requests.get(f"{BASE_URL}/dashboard/summary", params={"account": ACCOUNT_NAME, "force_refresh": "false"})
        api_data = api_res.json()
        
        summary = api_data["data"]
        if summary.get("loading"):
            log("⚠️ API 仍在加载中，结果可能不完整。")
            
        api_total_resources = summary["total_resources"]
        api_breakdown = summary["resource_breakdown"]
        
        log(f"API 报告总资源数: {api_total_resources}")
        log(f"API Breakdown: {api_breakdown}")
    except Exception as e:
        log(f"获取 API 摘要失败: {e}")
        return False

    # 2. 从 SDK 获取真实数据
    cm = ConfigManager()
    account_config = cm.get_account(ACCOUNT_NAME)
    all_regions = AnalysisService._get_all_regions(account_config.access_key_id, account_config.access_key_secret)
    
    log(f"通过 SDK 快速扫描所有区域 ({len(all_regions)} 个)...")
    
    sdk_counts = {"ecs": 0, "rds": 0, "redis": 0}
    
    for region in all_regions:
        try:
            from cloudlens.core.config import CloudAccount
            temp_config = CloudAccount(
                name=account_config.name,
                provider=account_config.provider,
                access_key_id=account_config.access_key_id,
                access_key_secret=account_config.access_key_secret,
                region=region
            )
            provider = get_provider(temp_config)
            
            # ECS
            sdk_counts["ecs"] += provider.check_instances_count()
            
            # RDS/Redis (快速检查暂时不支持，这里如果不查全量可能比不出来)
            # 但 Backend 也是这么写的。
        except:
            pass
            
    log(f"SDK 累计 ECS 总数: {sdk_counts['ecs']}")
    
    if api_breakdown.get("ecs") != sdk_counts["ecs"]:
        log(f"❌ ECS 数量不一致！API={api_breakdown.get('ecs')}, SDK={sdk_counts['ecs']}")
        return False
    else:
        log("✅ ECS 数量验证通过。")
        return True

if __name__ == "__main__":
    verify_dashboard()
