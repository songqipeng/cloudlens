import json
import sys
import os

sys.path.append(os.getcwd())
from core.config import ConfigManager
from cli.utils import get_provider

ACCOUNT_NAME = "ydzn"

def inspect_resources_all_regions():
    cm = ConfigManager()
    account_config = cm.get_account(ACCOUNT_NAME)
    
    # 获取区域列表
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.request import CommonRequest
    
    client = AcsClient(account_config.access_key_id, account_config.access_key_secret, "cn-hangzhou")
    request = CommonRequest()
    request.set_domain("ecs.aliyuncs.com")
    request.set_version("2014-05-26")
    request.set_action_name("DescribeRegions")
    response = client.do_action_with_exception(request)
    regions_data = json.loads(response)
    all_regions = [r["RegionId"] for r in regions_data.get("Regions", {}).get("Region", [])]
    
    for region in all_regions:
        account_config.region = region
        provider = get_provider(account_config)
        
        # print(f"Checking region {region}...")
        
        try:
            instances = provider.list_instances()
            for inst in instances:
                if inst.public_ips:
                    print(f"[REGION: {region}] ECS ID: {inst.id}, Name: {inst.name}, Public IPs: {inst.public_ips}")
            
            slbs = provider.list_slb()
            for slb in slbs:
                if slb.public_ips:
                    print(f"[REGION: {region}] SLB ID: {slb.id}, Name: {slb.name}, Public IPs: {slb.public_ips}")

            nats = provider.list_nat_gateways()
            for nat in nats:
                if nat.public_ips:
                    print(f"[REGION: {region}] NAT ID: {nat.id}, Name: {nat.name}, Public IPs: {nat.public_ips}")
        except Exception as e:
            # print(f"Error in region {region}: {e}")
            pass

if __name__ == "__main__":
    inspect_resources_all_regions()
