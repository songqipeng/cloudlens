"""
ActionTrail Helper
用于查询实例操作历史
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("ActionTrailHelper")

class ActionTrailHelper:
    """操作审计辅助类"""
    
    @staticmethod
    def get_instance_stop_time(provider, instance_id: str, lookback_days: int = 90) -> Optional[str]:
        """
        查询实例的最后停机时间
        
        Args:
            provider: AliyunProvider 实例
            instance_id: 实例 ID
            lookback_days: 回溯天数
            
        Returns:
            停机时间字符串，格式 YYYY-MM-DD HH:MM:SS，如果找不到返回 None
        """
        try:
            from aliyunsdkactiontrail.request.v20200706 import LookupEventsRequest
            import json
            
            end_time = datetime.now()
            start_time = end_time - timedelta(days=lookback_days)
            
            request = LookupEventsRequest.LookupEventsRequest()
            request.set_StartTime(start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            request.set_EndTime(end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            request.set_MaxResults(50)
            
            # 构造查询条件：StopInstance 事件且资源是目标实例
            lookup_attribute = f"""{{
                "Key": "ResourceName",
                "Value": "{instance_id}"
            }}"""
            request.set_LookupAttribute(lookup_attribute)
            
            # 调用 API
            client = provider.client
            response = client.do_action_with_exception(request)
            result = json.loads(response)
            
            # 查找 StopInstance 事件
            events = result.get("Events", [])
            for event in events:
                if event.get("eventName") == "StopInstance":
                    event_time = event.get("eventTime")
                    if event_time:
                        # 转换时间格式
                        dt = datetime.strptime(event_time, "%Y-%m-%dT%H:%M:%SZ")
                        return dt.strftime("%Y-%m-%d %H:%M:%S")
            
            return None
            
        except ImportError:
            logger.warning("ActionTrail SDK not installed. Install with: pip install aliyun-python-sdk-actiontrail")
            return None
        except Exception as e:
            logger.debug(f"Failed to query ActionTrail for {instance_id}: {e}")
            return None
