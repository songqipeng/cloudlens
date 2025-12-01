"""
ActionTrail Helper
用于查询实例操作历史
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
import json

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
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=lookback_days)
            
            request = LookupEventsRequest.LookupEventsRequest()
            request.set_StartTime(start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            request.set_EndTime(end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            request.set_MaxResults("50")
            
            # 使用正确的 API 参数格式
            request.add_query_param("LookupAttribute.1.Key", "ResourceName")
            request.add_query_param("LookupAttribute.1.Value", instance_id)
            request.add_query_param("LookupAttribute.2.Key", "EventName")  
            request.add_query_param("LookupAttribute.2.Value", "StopInstance")
            
            # 调用 API
            client = provider.client
            response = client.do_action_with_exception(request)
            result = json.loads(response)
            
            logger.info(f"ActionTrail query for {instance_id}: found {len(result.get('Events', []))} events")
            
            # 查找最近的 StopInstance 事件
            events = result.get("Events", [])
            if events and len(events) > 0:
                # 事件已按时间倒序排列，取第一个
                event_time = events[0].get("eventTime")
                event_name = events[0].get("eventName")
                logger.info(f"Latest event for {instance_id}: {event_name} at {event_time}")
                
                if event_time:
                    # 转换时间格式
                    dt = datetime.strptime(event_time, "%Y-%m-%dT%H:%M:%SZ")
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                logger.warning(f"No events found in ActionTrail for {instance_id}")
            
            return None
            
        except ImportError:
            logger.warning("ActionTrail SDK not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to query ActionTrail for {instance_id}: {e}", exc_info=True)
            return None
