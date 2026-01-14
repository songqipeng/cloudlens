import requests
import json
import sys
import os

# 确保能导入本地模块
sys.path.append(os.getcwd())

from core.config import ConfigManager
from cli.utils import get_provider
from core.security_compliance import SecurityComplianceAnalyzer

BASE_URL = "http://localhost:8000/api"
ACCOUNT_NAME = "ydzn"

def log(msg):
    print(f"[*] {msg}")

def validate_security_data():
    log("=== 开始验证安全模块公网暴露数据一致性 (全区域) ===")
    
    # 1. 从 API 获取数据
    try:
        log("触发 API 强制刷新...")
        api_res = requests.get(f"{BASE_URL}/security/checks", params={"account": ACCOUNT_NAME, "force_refresh": "true", "locale": "zh"})
        api_data = api_res.json()
        if not api_data.get("success"):
            log(f"API 获取失败: {api_data.get('error')}")
            return False
        
        checks = api_data["data"]
        api_exposed = next((c for c in checks if c["type"] == "public_exposure"), None)
        api_exposed_count = api_exposed["count"] if api_exposed else 0
        api_exposed_ids = [r["id"] for r in api_exposed["resources"]] if api_exposed else []
        
        log(f"API 报告的暴露资源总数: {api_exposed_count}")
    except Exception as e:
        log(f"执行 API 请求时出错: {e}")
        return False

    # 2. 从 SDK 实时获取数据 (全区域)
    cm = ConfigManager()
    account_config = cm.get_account(ACCOUNT_NAME)
    
    from core.services.analysis_service import AnalysisService
    all_regions = AnalysisService._get_all_regions(
        account_config.access_key_id,
        account_config.access_key_secret
    )
    
    log(f"正在全区域 ({len(all_regions)} 个) 资源扫描...")
    
    all_resources = []
    for region in all_regions:
        try:
            # Create a localized config copy
            from core.config import CloudAccount
            temp_config = CloudAccount(
                name=account_config.name,
                provider=account_config.provider,
                access_key_id=account_config.access_key_id,
                access_key_secret=account_config.access_key_secret,
                region=region
            )
            provider = get_provider(temp_config)
            
            instances = provider.list_instances()
            rds_list = provider.list_rds()
            redis_list = provider.list_redis()
            slb_list = provider.list_slb() if hasattr(provider, 'list_slb') else []
            nat_list = provider.list_nat_gateways() if hasattr(provider, 'list_nat_gateways') else []
            
            all_resources.extend(instances + rds_list + redis_list + slb_list + nat_list)
        except Exception as e:
            # log(f"Error in region {region}: {e}")
            pass
    
    analyzer = SecurityComplianceAnalyzer()
    real_exposed = analyzer.detect_public_exposure(all_resources)
    real_exposed_count = len(real_exposed)
    real_exposed_ids = [r["id"] for r in real_exposed]
    
    log(f"SDK 检测到的暴露资源总数: {real_exposed_count}")
    
    # 3. 对比
    if api_exposed_count != real_exposed_count:
        log(f"❌ 数据不一致！API={api_exposed_count}, SDK={real_exposed_count}")
        
        missing_in_api = set(real_exposed_ids) - set(api_exposed_ids)
        extra_in_api = set(api_exposed_ids) - set(real_exposed_ids)
        
        if missing_in_api:
            log(f"  API 缺失的资源: {list(missing_in_api)}")
            for r in real_exposed:
                if r["id"] in missing_in_api:
                    log(f"    - Type: {r['type']}, Region: {r['region']}, Name: {r['name']}, IPs: {r['public_ips']}")
        
        if extra_in_api:
            log(f"  API 多出的资源 (可能含有未扫描区域的旧缓存): {list(extra_in_api)}")
        
        return False
    else:
        log("✅ 验证通过：API 数据与 SDK 实时检测结果一致。")
        return True

if __name__ == "__main__":
    validate_security_data()
