"""
ActionTrail Helper
用于查询实例操作历史
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

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

    @staticmethod
    def get_resource_operation_history(
        provider,
        resource_id: str,
        resource_type: str = "ECS",
        lookback_days: int = 30,
        event_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        查询资源的操作历史记录
        
        Args:
            provider: AliyunProvider 实例
            resource_id: 资源 ID
            resource_type: 资源类型（如 "ECS", "RDS", "SLB"）
            lookback_days: 回溯天数，默认 30 天
            event_names: 事件名称列表（如 ["StopInstances", "StartInstances"]），如果为 None 则查询所有事件
            
        Returns:
            操作历史记录列表，每个记录包含 eventTime, eventName, userIdentity 等信息
        """
        try:
            from aliyunsdkactiontrail.request.v20200706 import LookupEventsRequest

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=lookback_days)

            request = LookupEventsRequest.LookupEventsRequest()
            request.set_StartTime(start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            request.set_EndTime(end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            request.set_MaxResults("100")  # 增加返回数量

            # 按资源名称查询
            request.add_query_param("LookupAttribute.1.Key", "ResourceName")
            request.add_query_param("LookupAttribute.1.Value", resource_id)

            # 如果指定了事件名称，添加过滤条件
            if event_names:
                for idx, event_name in enumerate(event_names[:5], start=2):  # 最多支持 5 个事件名称
                    request.add_query_param(f"LookupAttribute.{idx}.Key", "EventName")
                    request.add_query_param(f"LookupAttribute.{idx}.Value", event_name)

            client = provider._get_client()
            response = client.do_action_with_exception(request)
            result = json.loads(response)

            events = result.get("Events", [])
            operation_history = []
            
            for event in events:
                event_time = event.get("eventTime", "")
                event_name = event.get("eventName", "")
                user_identity = event.get("userIdentity", {})
                source_ip = event.get("sourceIPAddress", "")
                user_agent = event.get("userAgent", "")
                
                operation_history.append({
                    "event_time": event_time,
                    "event_name": event_name,
                    "user_identity": user_identity,
                    "source_ip": source_ip,
                    "user_agent": user_agent,
                    "raw_event": event  # 保留原始事件数据
                })
            
            return operation_history

        except ImportError:
            logger.warning("ActionTrail SDK not installed")
            return []
        except Exception as e:
            logger.error(f"查询资源 {resource_id} 的操作历史失败: {e}")
            return []

    @staticmethod
    def get_recent_config_changes(
        provider,
        resource_type: str = "ECS",
        lookback_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        查询最近的配置变更操作（如修改安全组、修改实例规格等）
        
        Args:
            provider: AliyunProvider 实例
            resource_type: 资源类型
            lookback_days: 回溯天数，默认 7 天
            
        Returns:
            配置变更记录列表
        """
        # 常见的配置变更事件
        config_change_events = [
            "ModifyInstanceAttribute",
            "ModifySecurityGroupAttribute",
            "ModifyDBInstanceAttribute",
            "ModifyLoadBalancerInstanceSpec",
            "ModifyVpcAttribute",
            "ModifyInstanceSpec",
        ]
        
        try:
            from aliyunsdkactiontrail.request.v20200706 import LookupEventsRequest

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=lookback_days)

            request = LookupEventsRequest.LookupEventsRequest()
            request.set_StartTime(start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            request.set_EndTime(end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            request.set_MaxResults("100")

            # 按事件名称查询配置变更事件
            for idx, event_name in enumerate(config_change_events[:5], start=1):
                request.add_query_param(f"LookupAttribute.{idx}.Key", "EventName")
                request.add_query_param(f"LookupAttribute.{idx}.Value", event_name)

            client = provider._get_client()
            response = client.do_action_with_exception(request)
            result = json.loads(response)

            events = result.get("Events", [])
            changes = []
            
            for event in events:
                changes.append({
                    "event_time": event.get("eventTime", ""),
                    "event_name": event.get("eventName", ""),
                    "resource_name": event.get("resourceName", ""),
                    "user_identity": event.get("userIdentity", {}),
                    "source_ip": event.get("sourceIPAddress", ""),
                })
            
            return changes

        except ImportError:
            logger.warning("ActionTrail SDK not installed")
            return []
        except Exception as e:
            logger.error(f"查询配置变更历史失败: {e}")
            return []
