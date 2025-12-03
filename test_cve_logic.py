
import sys
import logging
sys.path.insert(0, '/Users/mac/aliyunidle')

# Configure logging
logging.basicConfig(level=logging.INFO)

from core.cve_matcher import CVEMatcher
from core.security_scanner import PublicIPScanner

def test_cve_detection():
    print("=== Testing CVE Detection Logic ===")
    
    # 1. Test Matcher Directly
    print("\n1. Testing CVEMatcher...")
    
    test_cases = [
        ("OpenSSH", "7.2p2", True),  # Should match CVE-2016-10009 (< 7.4)
        ("OpenSSH", "7.9", False),   # Should be safe
        ("Nginx", "1.14.0", True),   # Should match CVE-2019-9511 (1.9.5 - 1.16.0)
        ("Nginx", "1.22.0", False),  # Should be safe
    ]
    
    for product, version, expected in test_cases:
        matches = CVEMatcher.match(product, version)
        found = len(matches) > 0
        status = "✅ PASS" if found == expected else "❌ FAIL"
        print(f"  {product} {version}: Found {len(matches)} CVEs -> {status}")
        if matches:
            print(f"    - {matches[0]['id']}: {matches[0]['description']}")

    # 2. Test Banner Parsing
    print("\n2. Testing Banner Parsing...")
    banners = [
        ("SSH-2.0-OpenSSH_7.4", "OpenSSH", "7.4"),
        ("Server: nginx/1.14.0", "nginx", "1.14.0"),
        ("Server: Apache/2.4.49 (Unix)", "Apache", "2.4.49"),
    ]
    
    for banner, exp_prod, exp_ver in banners:
        info = PublicIPScanner.identify_service_version(banner, 80)
        print(f"  Banner: '{banner}' -> Product: {info['product']}, Version: {info['version']}")
        if info['product'] == exp_prod and info['version'] == exp_ver:
            print("    ✅ Parsed correctly")
        else:
            print(f"    ❌ Parse failed (Expected {exp_prod} {exp_ver})")

if __name__ == "__main__":
    test_cve_detection()
