
import sys
import logging
sys.path.insert(0, '/Users/mac/aliyunidle')

# Configure logging
logging.basicConfig(level=logging.INFO)

from main_cli import get_provider
from core.config import ConfigManager
from core.security_scanner import PublicIPScanner

def test_security_features():
    print("=== Testing Security Features ===")
    
    cm = ConfigManager()
    acc = cm.get_account('ydzn')
    if not acc:
        print("Account not found")
        return

    provider = get_provider(acc)
    
    # 1. Test Resource Listing
    print("\n1. Testing Resource Listing...")
    
    print("  Fetching SLBs...")
    slbs = provider.list_slb()
    print(f"  - Found {len(slbs)} SLBs")
    if slbs:
        print(f"  - Sample: {slbs[0].id} ({slbs[0].public_ips})")

    print("  Fetching NAT Gateways...")
    nats = provider.list_nat_gateways()
    print(f"  - Found {len(nats)} NAT Gateways")
    if nats:
        print(f"  - Sample: {nats[0].id} ({nats[0].public_ips})")

    print("  Fetching MongoDBs...")
    mongos = provider.list_mongodb()
    print(f"  - Found {len(mongos)} MongoDBs")
    
    # 2. Test Security Scanner
    print("\n2. Testing Security Scanner...")
    # Use a known public IP (e.g., one from the previous output or a public DNS)
    # Let's try scanning one of the SLB IPs found earlier: 39.106.82.166
    target_ip = "39.106.82.166" 
    print(f"  Scanning {target_ip}...")
    
    result = PublicIPScanner.scan_ip(target_ip, ports=[80, 443])
    print(f"  - Open ports: {[p['port'] for p in result['open_ports']]}")
    if result.get('ssl_info'):
        print(f"  - SSL: Valid until {result['ssl_info'].get('expiry_date')}")
    else:
        print("  - SSL: No certificate found or check failed")

if __name__ == "__main__":
    test_security_features()
