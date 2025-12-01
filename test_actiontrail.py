#!/usr/bin/env python3
"""
测试 ActionTrail API 调用
"""
import sys
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, '/Users/mac/aliyunidle')

from core.config import ConfigManager

def test_actiontrail():
    """测试 ActionTrail 查询"""
    cm = ConfigManager()
    acc = cm.get_account('ydzn')
    
    if not acc:
        print("❌ Account 'ydzn' not found")
        return
    
    # 使用 main_cli 中的 get_provider helper
    from main_cli import get_provider
    provider = get_provider(acc)
    
    # 测试实例ID
    test_instance_id = "i-2zeduotnz952362oeg8f"
    
    print(f"🔍 Testing ActionTrail API for instance: {test_instance_id}\n")
    
    try:
        from aliyunsdkactiontrail.request.v20200706 import LookupEventsRequest
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=90)
        
        print(f"📅 Query period: {start_time} to {end_time}\n")
        
        # 方法1：使用 LookupAttribute
        print("=" * 80)
        print("方法1: 使用 add_query_param 设置 LookupAttribute")
        print("=" * 80)
        
        request = LookupEventsRequest.LookupEventsRequest()
        request.set_StartTime(start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
        request.set_EndTime(end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
        request.set_MaxResults("50")
        
        # 使用 add_query_param
        request.add_query_param("LookupAttribute.1.Key", "ResourceName")
        request.add_query_param("LookupAttribute.1.Value", test_instance_id)
        request.add_query_param("LookupAttribute.2.Key", "EventName")
        request.add_query_param("LookupAttribute.2.Value", "StopInstance")
        
        client = provider._get_client()
        response = client.do_action_with_exception(request)
        result = json.loads(response)
        
        print(f"✅ Response received")
        print(f"📊 Total events: {len(result.get('Events', []))}")
        
        if result.get('Events'):
            print(f"\n📋 First 3 events:")
            for idx, event in enumerate(result.get('Events', [])[:3], 1):
                print(f"\n  Event {idx}:")
                print(f"    - Event Name: {event.get('eventName', 'N/A')}")
                print(f"    - Event Time: {event.get('eventTime', 'N/A')}")
                print(f"    - Resource Name: {event.get('resourceName', 'N/A')}")
                print(f"    - User: {event.get('userIdentity', {}).get('userName', 'N/A')}")
        else:
            print("⚠️  No events found")
            print(f"\n🔍 Full response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 方法2：只查询 StopInstance 事件，不限制资源
        print("\n" + "=" * 80)
        print("方法2: 只查询 StopInstance 事件（不限制资源）")
        print("=" * 80)
        
        request2 = LookupEventsRequest.LookupEventsRequest()
        request2.set_StartTime((end_time - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"))
        request2.set_EndTime(end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
        request2.set_MaxResults("10")
        request2.add_query_param("LookupAttribute.1.Key", "EventName")
        request2.add_query_param("LookupAttribute.1.Value", "StopInstance")
        
        response2 = client.do_action_with_exception(request2)
        result2 = json.loads(response2)
        
        print(f"✅ Response received")
        print(f"📊 Total StopInstance events (last 7 days): {len(result2.get('Events', []))}")
        
        if result2.get('Events'):
            print(f"\n📋 Sample events:")
            for idx, event in enumerate(result2.get('Events', [])[:5], 1):
                print(f"\n  Event {idx}:")
                print(f"    - Resource: {event.get('resourceName', 'N/A')}")
                print(f"    - Time: {event.get('eventTime', 'N/A')}")
        
        # 方法3：不使用过滤，查看原始数据结构
        print("\n" + "=" * 80)
        print("方法3: 查询任意事件（了解数据结构）")
        print("=" * 80)
        
        request3 = LookupEventsRequest.LookupEventsRequest()
        request3.set_StartTime((end_time - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"))
        request3.set_EndTime(end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
        request3.set_MaxResults("5")
        
        response3 = client.do_action_with_exception(request3)
        result3 = json.loads(response3)
        
        print(f"✅ Response received")
        print(f"📊 Total events (last 24h): {len(result3.get('Events', []))}")
        
        if result3.get('Events'):
            print(f"\n📋 Sample event structure:")
            print(json.dumps(result3.get('Events', [])[0], indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_actiontrail()
