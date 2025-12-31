
import sys
import os
import json
import logging
sys.path.append(os.getcwd())

from core.config import ConfigManager
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

def check_permissions():
    account_name = "ydzn"
    cm = ConfigManager()
    account_config = cm.get_account(account_name)
    
    if not account_config:
        print(f"Error: Account {account_name} not found.")
        return

    print(f"Checking permissions for account: {account_name}")
    
    # 1. Get Caller Identity (STS)
    client = AcsClient(account_config.access_key_id, account_config.access_key_secret, "cn-hangzhou")
    
    try:
        request = CommonRequest()
        request.set_domain("sts.aliyuncs.com")
        request.set_version("2015-04-01")
        request.set_action_name("GetCallerIdentity")
        request.set_protocol_type('https') # Fix SSL error
        response = client.do_action_with_exception(request)
        identity = json.loads(response)
        user_id = identity.get("UserId")
        arn = identity.get("Arn")
        print(f"\n[Identity]")
        print(f"User ID: {user_id}")
        print(f"ARN: {arn}")
        
        # Extract user name from ARN if possible
        # ARN format: acs:ram::account-id:user/user-name
        if ":user/" in arn:
            user_name = arn.split(":user/")[1]
        else:
            user_name = None
            
    except Exception as e:
        print(f"\n[Identity Check Failed]: {e}")
        user_name = None

    # 2. Try to list policies attached to this user (RAM)
    # This requires 'ram:ListPoliciesForUser' or similar permissions on itself.
    if user_name:
        print(f"\n[Attached Policies Verification]")
        try:
            request = CommonRequest()
            request.set_domain("ram.aliyuncs.com")
            request.set_version("2015-05-01")
            request.set_action_name("ListPoliciesForUser")
            request.set_protocol_type('https') # Fix SSL error
            request.add_query_param("UserName", user_name)
            response = client.do_action_with_exception(request)
            policies = json.loads(response).get("Policies", {}).get("Policy", [])
            
            if not policies:
                print("No policies found attached directly to user (or empty list).")
            else:
                for p in policies:
                    print(f"- {p['PolicyName']} ({p['PolicyType']})")
        except Exception as e:
            print(f"Unable to list RAM policies (Expected if no RAM read permission): {e}")
            print(">> 如果您看到此错误，说明该账号没有由于列出自身权限的 RAM 读权限。")
            
    # 3. Functional Tests (Verify Read Access)
    print(f"\n[Functional Checks]")
    
    # ECS
    try:
        req = CommonRequest()
        req.set_domain("ecs.aliyuncs.com")
        req.set_version("2014-05-26")
        req.set_action_name("DescribeInstances")
        req.add_query_param("PageSize", "1")
        client.do_action_with_exception(req)
        print("✅ ECS Read (DescribeInstances): Success")
    except Exception as e:
        print(f"❌ ECS Read Failed: {e}")

    # BSS (Billing)
    try:
        req = CommonRequest()
        req.set_domain("business.aliyuncs.com")
        req.set_version("2017-12-14")
        req.set_action_name("QueryBillOverview")
        req.add_query_param("BillingCycle", "2024-01") # Just checking permissions, date doesn't strictly matter
        client.do_action_with_exception(req)
        print("✅ BSS Read (QueryBillOverview): Success")
    except Exception as e:
        if "EntityNotExist.Role" in str(e): # Often BSS involves roles, but simpler check
             print(f"❌ BSS Read Failed (Role Error): {e}")
        elif "Forbidden" in str(e) or "AccessDenied" in str(e):
             print(f"❌ BSS Read Denied: {e}")
        else:
             # Some other error (like timeout) implies permission passed?
             # But safer to say Mixed
             print(f"⚠️  BSS Read Check (Other Error): {e}")

    # CMS (CloudMonitor)
    try:
        req = CommonRequest()
        req.set_domain("metrics.aliyuncs.com")
        req.set_version("2019-01-01")
        req.set_action_name("DescribeMetricMetaList")
        req.add_query_param("PageSize", "1")
        client.do_action_with_exception(req)
        print("✅ CMS Read (DescribeMetricMetaList): Success")
    except Exception as e:
        print(f"❌ CMS Read Failed: {e}")

if __name__ == "__main__":
    check_permissions()
