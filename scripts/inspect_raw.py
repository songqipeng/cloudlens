import json
import sys
import os

sys.path.append(os.getcwd())
from cloudlens.core.config import ConfigManager
from cloudlens.cli.utils import get_provider

ACCOUNT_NAME = "ydzn"

def inspect_resources():
    cm = ConfigManager()
    account_config = cm.get_account(ACCOUNT_NAME)
    provider = get_provider(account_config)
    
    print(f"--- ECS Instances in region {account_config.region} ---")
    instances = provider.list_instances()
    for inst in instances:
        raw = inst.raw_data
        print(f"ID: {inst.id}, Name: {inst.name}")
        print(f"  Public IPs (Unified): {inst.public_ips}")
        # print(f"  Raw Network info: {raw.get('VpcAttributes')}")
        # print(f"  Raw PublicIpAddress: {raw.get('PublicIpAddress')}")
        # print(f"  Raw EipAddress: {raw.get('EipAddress')}")
        
    print(f"\n--- SLB Instances ---")
    slbs = provider.list_slb()
    for slb in slbs:
        print(f"ID: {slb.id}, Name: {slb.name}, Public IPs: {slb.public_ips}")

    print(f"\n--- NAT Gateways ---")
    nats = provider.list_nat_gateways()
    for nat in nats:
        print(f"ID: {nat.id}, Name: {nat.name}, Public IPs: {nat.public_ips}")

if __name__ == "__main__":
    inspect_resources()
