"""
ActionTrail Helper
用于查询实例操作历史
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("ActionTrailHelper")


class ActionTrailHelper:
    """操作审计辅助类"""

    @staticmethod
    def get_instance_stop_time(
        provider, instance_id: str, raw_data: dict = None, lookback_days: int = 90
    ) -> Optional[str]:
        """
        查询实例的停机时间（从 ActionTrail）

        Args:
            provider: AliyunProvider 实例
            instance_id: 实例 ID
            raw_data: 实例原始数据（未使用）
            lookback_days: ActionTrail 回溯天数

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
            request.add_query_param("LookupAttribute.2.Value", "StopInstances")  # 注意是复数！

            # 调用 API - 使用 provider 的 _get_client() 方法
            client = provider._get_client()
            response = client.do_action_with_exception(request)
            result = json.loads(response)

            # 查找最近的 StopInstance 事件
            events = result.get("Events", [])
            if events and len(events) > 0:
                event_time = events[0].get("eventTime")
                if event_time:
                    dt = datetime.strptime(event_time, "%Y-%m-%dT%H:%M:%SZ")
                    logger.info(f"Found stop time from ActionTrail for {instance_id}: {event_time}")
                    return dt.strftime("%Y-%m-%d %H:%M:%S")

        except ImportError:
            logger.warning("ActionTrail SDK not installed")
        except Exception as e:
            logger.debug(f"ActionTrail query failed for {instance_id}: {e}")

        # 如果 ActionTrail 没有数据，返回 None
        logger.warning(f"No stop time found in ActionTrail for {instance_id} (may be >90 days ago)")
        return None
