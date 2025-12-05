import sys
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import ConfigManager
from providers.aliyun.provider import AliyunProvider

# List of IPs to analyze
TARGET_IPS = [
    "101.200.123.129", "101.200.60.82", "101.201.115.121", "101.201.209.246", "101.201.210.110",
    "101.201.50.55", "123.57.130.19", "123.57.182.123", "123.57.184.149", "123.57.252.162",
    "123.57.35.2", "182.92.85.51", "39.103.66.119", "39.106.13.204", "39.106.152.192",
    "39.106.27.157", "39.106.82.166", "39.106.89.153", "39.106.90.178", "39.107.126.110",
    "39.107.73.100", "39.107.73.91", "39.107.81.69", "39.107.84.229", "39.96.169.54",
    "39.96.199.69", "47.93.124.215", "47.93.183.56", "47.93.184.81", "47.93.223.175",
    "47.94.108.227", "47.94.164.5", "47.94.224.201", "47.94.244.173", "47.94.246.26",
    "47.95.157.147", "47.95.176.7", "47.95.197.149", "47.95.217.81", "60.205.168.32",
    "60.205.5.225", "8.147.105.208", 
    "101.200.181.239", "101.200.91.106", "101.201.154.91", "101.201.56.116", "123.56.201.196",
    "123.56.31.215", "123.56.31.54", "123.56.77.218", "123.56.8.28", "123.57.181.198",
    "123.57.223.44", "123.57.83.173", "182.92.142.136", "182.92.186.250", "182.92.71.41",
    "39.105.117.79", "39.105.208.3", "39.106.49.145", "39.107.113.242", "39.107.152.98",
    "39.107.211.202", "39.96.175.33", "39.97.241.9", "39.97.39.54", "47.93.140.115",
    "47.93.157.13", "47.93.45.29", "47.93.58.105", "47.93.61.134", "47.93.80.196",
    "47.94.156.108", "47.94.162.116", "47.95.212.28", "47.95.9.58", "59.110.229.25",
    "59.110.38.205", "60.205.158.12", "60.205.183.167", "8.140.249.100", "8.141.26.142",
    "8.152.154.148"
]

def get_provider(account_config):
    if account_config.provider == "aliyun":
        return AliyunProvider(
            account_config.name,
            account_config.access_key_id,
            account_config.access_key_secret,
            account_config.region
        )
    return None

def main():
    print(f"🔍 Starting traffic analysis for {len(TARGET_IPS)} IPs...")
    
    cm = ConfigManager()
    accounts = cm.list_accounts()
    
    # 1. Map IPs to Resources
    print("📦 Mapping IPs to resources...")
    ip_map = {}  # IP -> {account, type, id, region}
    
    for acc in accounts:
        provider = get_provider(acc)
        if not provider: continue
        
        print(f"   Scanning account: {acc.name}...")
        try:
            # Check ECS
            instances = provider.list_instances()
            for inst in instances:
                for ip in inst.public_ips:
                    if ip in TARGET_IPS:
                        ip_map[ip] = {
                            "account": acc.name,
                            "type": "ECS",
                            "id": inst.id,
                            "name": inst.name,
                            "region": inst.region,
                            "provider": provider
                        }
            
            # Check EIP
            eips = provider.list_eip()
            for eip in eips:
                ip = eip['ip_address']
                if ip in TARGET_IPS:
                    # If already found as ECS, it means this ECS uses this EIP.
                    # We MUST switch to EIP type to get correct metrics (ECS metrics are 0 for EIP).
                    if ip in ip_map and ip_map[ip]['type'] == 'ECS':
                        ip_map[ip]['type'] = 'EIP'
                        ip_map[ip]['id'] = eip['id']
                        ip_map[ip]['name'] = f"{ip_map[ip]['name']} (EIP)"
                        continue
                        
                    ip_map[ip] = {
                        "account": acc.name,
                        "type": "EIP",
                        "id": eip['id'],
                        "name": f"EIP-{eip['id']}",
                        "region": eip['region'],
                        "provider": provider
                    }
            
            # Check SLB
            slbs = provider.list_slb()
            for slb in slbs:
                for ip in slb.public_ips:
                    if ip in TARGET_IPS:
                        ip_map[ip] = {
                            "account": acc.name,
                            "type": "SLB",
                            "id": slb.id,
                            "name": slb.name,
                            "region": slb.region,
                            "provider": provider
                        }
                        
        except Exception as e:
            print(f"❌ Error scanning {acc.name}: {e}")

    found_ips = list(ip_map.keys())
    missing_ips = [ip for ip in TARGET_IPS if ip not in found_ips]
    
    print(f"✅ Found {len(found_ips)} IPs. Missing {len(missing_ips)} IPs.")
    if missing_ips:
        print(f"⚠️  Missing IPs: {', '.join(missing_ips[:5])}...")

    # 2. Fetch Metrics
    print("\n📊 Fetching traffic metrics (last 14 days)...")
    
    results = []
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=14)).timestamp() * 1000)
    
    for i, ip in enumerate(found_ips, 1):
        info = ip_map[ip]
        print(f"   [{i}/{len(found_ips)}] Analyzing {ip} ({info['type']}/{info['id']})...")
        
        provider = info['provider']
        metrics_in = []
        metrics_out = []
        
        try:
            if info['type'] == 'ECS':
                # ECS: InternetInRate, InternetOutRate (bps)
                metrics_in = provider.get_metric(info['id'], "InternetInRate", start_time, end_time)
                metrics_out = provider.get_metric(info['id'], "InternetOutRate", start_time, end_time)
                unit_factor = 1/8/1024  # bps -> KB/s
                
            elif info['type'] == 'EIP':
                # EIP: net_rx.rate, net_tx.rate (bps)
                # Namespace: acs_vpc_eip
                # NOTE: Must use "instanceId" not "allocationId" for proper per-EIP metrics
                metrics_in = provider.get_metric(info['id'], "net_rx.rate", start_time, end_time, 
                                               namespace="acs_vpc_eip", 
                                               dimensions=f'[{{"instanceId":"{info["id"]}"}}]')
                metrics_out = provider.get_metric(info['id'], "net_tx.rate", start_time, end_time, 
                                                namespace="acs_vpc_eip", 
                                                dimensions=f'[{{"instanceId":"{info["id"]}"}}]')
                unit_factor = 1/8/1024 # bps -> KB/s
                
            elif info['type'] == 'SLB':
                # SLB: TrafficRXNew, TrafficTXNew (bps)
                # Namespace: acs_slb_dashboard
                metrics_in = provider.get_metric(info['id'], "TrafficRXNew", start_time, end_time, 
                                               namespace="acs_slb_dashboard", 
                                               dimensions=f'[{{"instanceId":"{info["id"]}"}}]')
                metrics_out = provider.get_metric(info['id'], "TrafficTXNew", start_time, end_time, 
                                                namespace="acs_slb_dashboard", 
                                                dimensions=f'[{{"instanceId":"{info["id"]}"}}]')
                unit_factor = 1/8/1024 # bps -> KB/s
            
            # Process metrics
            max_in = 0
            avg_in = 0
            max_out = 0
            avg_out = 0
            
            # Log raw data for debugging
            with open("traffic_debug.log", "a") as f:
                f.write(f"IP: {ip}, Resource: {info['id']}\n")
                f.write(f"Metrics In Count: {len(metrics_in)}\n")
                if metrics_in: f.write(f"Sample In: {metrics_in[0]}\n")
                f.write(f"Metrics Out Count: {len(metrics_out)}\n")
                if metrics_out: f.write(f"Sample Out: {metrics_out[0]}\n")
                f.write("-" * 50 + "\n")

            if metrics_in:
                # EIP metrics might use 'Value' instead of 'Average' for some metrics, or just be different
                # Let's inspect the first point to see keys
                first_point = metrics_in[0]
                val_key = 'Average' if 'Average' in first_point else 'Value'
                if val_key in first_point:
                    vals = [p[val_key] for p in metrics_in]
                    max_in = max(vals) * unit_factor
                    avg_in = (sum(vals) / len(vals)) * unit_factor
            
            if metrics_out:
                first_point = metrics_out[0]
                val_key = 'Average' if 'Average' in first_point else 'Value'
                if val_key in first_point:
                    vals = [p[val_key] for p in metrics_out]
                    max_out = max(vals) * unit_factor
                    avg_out = (sum(vals) / len(vals)) * unit_factor
            
            results.append({
                "IP": ip,
                "Account": info['account'],
                "Type": info['type'],
                "ResourceID": info['id'],
                "Name": info['name'],
                "Region": info['region'],
                "Max In (KB/s)": round(max_in, 2),
                "Avg In (KB/s)": round(avg_in, 2),
                "Max Out (KB/s)": round(max_out, 2),
                "Avg Out (KB/s)": round(avg_out, 2),
                "Total Traffic (GB)": round((avg_in + avg_out) * 14 * 24 * 3600 / 1024 / 1024, 2) # Approx
            })
            
        except Exception as e:
            print(f"❌ Error fetching metrics for {ip}: {e}")
            results.append({
                "IP": ip,
                "Account": info['account'],
                "Type": info['type'],
                "ResourceID": info['id'],
                "Name": info['name'],
                "Region": info['region'],
                "Error": str(e)
            })

    # Add missing IPs
    for ip in missing_ips:
        results.append({
            "IP": ip,
            "Account": "Not Found",
            "Type": "N/A",
            "ResourceID": "N/A",
            "Name": "N/A",
            "Region": "N/A"
        })

    # 3. Generate Report
    df = pd.DataFrame(results)
    import datetime as dt
    timestamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"ip_traffic_report_{timestamp}.xlsx"
    df.to_excel(output_file, index=False)
    print(f"\n✅ Report generated: {output_file}")

if __name__ == "__main__":
    main()
