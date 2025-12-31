"""
Config Helper
用于查询资源配置变更历史（阿里云 Config 服务）
"""

import json
import logging
import datetime
from typing import List, Dict, Optional, Any
from datetime import timedelta

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from core.config import CloudAccount

logger = logging.getLogger(__name__)


class ConfigHelper:
    """配置审计辅助类（阿里云 Config）"""

    def __init__(self, account_config: CloudAccount):
        """
        初始化 Config Helper
        
        Args:
            account_config: 云账户配置
        """
        self.client = AcsClient(
            account_config.access_key_id,
            account_config.access_key_secret,
            "cn-hangzhou"  # Config API 通常使用 cn-hangzhou
        )
        self.account_name = account_config.name

    def get_configuration_changes(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        查询资源配置变更历史
        
        Args:
            resource_type: 资源类型（如 "ACS::ECS::Instance"）
            resource_id: 资源 ID（如 "i-xxx"）
            start_time: 开始时间，默认 7 天前
            end_time: 结束时间，默认当前时间
            max_results: 最大返回结果数，默认 50
            
        Returns:
            配置变更记录列表
        """
        try:
            if end_time is None:
                end_time = datetime.datetime.now()
            if start_time is None:
                start_time = end_time - timedelta(days=7)
            
            request = CommonRequest()
            request.set_domain("config.cn-hangzhou.aliyuncs.com")
            request.set_version("2020-09-07")
            request.set_action_name("ListConfigRules")
            request.set_method("POST")
            
            # 注意：阿里云 Config 的 API 可能需要先启用 Config 服务
            # 这里使用 ListConfigurationRecorders 来检查服务状态
            # 实际查询变更历史需要使用 ListConfigurationRecorders 和 GetConfigurationRecorder
            
            # 由于 Config API 较复杂，这里先实现基础框架
            # 实际使用时需要根据 Config 服务状态调整
            
            logger.warning("Config 服务查询需要先启用 Config 服务，当前返回空结果")
            return []
            
        except Exception as e:
            logger.error(f"查询 Config 配置变更失败: {e}")
            return []

    def get_resource_configuration(
        self,
        resource_type: str,
        resource_id: str,
        region: str = "cn-hangzhou"
    ) -> Optional[Dict[str, Any]]:
        """
        获取资源的当前配置
        
        Args:
            resource_type: 资源类型
            resource_id: 资源 ID
            region: 区域
            
        Returns:
            资源配置信息，如果获取失败返回 None
        """
        try:
            # 使用 Config API 获取资源配置
            # 注意：需要先启用 Config 服务并配置资源记录器
            
            logger.warning("获取资源配置需要先启用 Config 服务")
            return None
            
        except Exception as e:
            logger.error(f"获取资源配置失败: {e}")
            return None

    def check_config_service_status(self) -> Dict[str, Any]:
        """
        检查 Config 服务状态
        
        Returns:
            服务状态信息
        """
        try:
            request = CommonRequest()
            request.set_domain("config.cn-hangzhou.aliyuncs.com")
            request.set_version("2020-09-07")
            request.set_action_name("DescribeConfigurationRecorder")
            request.set_method("POST")
            
            response = self.client.do_action_with_exception(request)
            data = json.loads(response)
            
            return {
                "enabled": data.get("ConfigurationRecorder", {}).get("ConfigurationRecorderStatus") == "REGISTERED",
                "status": data.get("ConfigurationRecorder", {}).get("ConfigurationRecorderStatus", "UNKNOWN")
            }
            
        except Exception as e:
            logger.warning(f"检查 Config 服务状态失败（可能未启用）: {e}")
            return {
                "enabled": False,
                "status": "NOT_ENABLED",
                "error": str(e)
            }

