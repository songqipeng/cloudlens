#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云盘资源分析模块
分析闲置（未挂载）的云盘
"""

import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from dateutil import parser

from core.analyzer_registry import AnalyzerRegistry
from core.base_analyzer import BaseResourceAnalyzer
from core.report_generator import ReportGenerator
from core.threshold_manager import ThresholdManager
from utils.error_handler import ErrorHandler
from utils.logger import get_logger


@AnalyzerRegistry.register("disk", "云盘", "💾")
class DiskAnalyzer(BaseResourceAnalyzer):
    """云盘资源分析器"""

    def __init__(self, access_key_id: str, access_key_secret: str, tenant_name: str = "default"):
        """初始化"""
        threshold_manager = ThresholdManager()
        super().__init__(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            tenant_name=tenant_name,
            threshold_manager=threshold_manager,
        )
        self.logger = get_logger("aliyunidle.disk")
        self.client = AcsClient(access_key_id, access_key_secret, "cn-hangzhou")

    def get_resource_type(self) -> str:
        """获取资源类型"""
        return "disk"

    def get_all_regions(self) -> List[str]:
        """获取所有可用区域"""
        try:
            request = CommonRequest()
            request.set_domain("ecs.cn-hangzhou.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2014-05-26")
            request.set_action_name("DescribeRegions")

            response = self.client.do_action_with_exception(request)
            data = json.loads(response)

            regions = []
            for region in data["Regions"]["Region"]:
                regions.append(region["RegionId"])

            return regions
        except Exception as e:
            self.logger.error(f"获取区域列表失败: {e}")
            return []

    def get_instances(self, region: str) -> List[Dict]:
        """获取指定区域的云盘列表"""
        disks = []
        page_number = 1
        page_size = 100

        try:
            client = AcsClient(self.access_key_id, self.access_key_secret, region)

            while True:
                request = CommonRequest()
                request.set_domain(f"ecs.{region}.aliyuncs.com")
                request.set_method("POST")
                request.set_version("2014-05-26")
                request.set_action_name("DescribeDisks")
                request.add_query_param("PageSize", page_size)
                request.add_query_param("PageNumber", page_number)
                # 只查询未挂载的云盘 (Status=Available)
                request.add_query_param("Status", "Available")

                response = client.do_action_with_exception(request)
                data = json.loads(response)

                if "Disks" in data and "Disk" in data["Disks"]:
                    page_disks = data["Disks"]["Disk"]
                    if not isinstance(page_disks, list):
                        page_disks = [page_disks]

                    if len(page_disks) == 0:
                        break

                    disks.extend(page_disks)
                    page_number += 1

                    if len(page_disks) < page_size:
                        break
                else:
                    break

            return disks
        except Exception as e:
            self.logger.error(f"获取区域 {region} 云盘失败: {e}")
            return []

    def get_metrics(self, region: str, instance_id: str, days: int = 14) -> Dict[str, float]:
        """获取监控指标（云盘通常不需要监控指标来判断是否未挂载，这里返回空）"""
        return {}

    def is_idle(
        self, instance: Dict, metrics: Dict, thresholds: Dict = None
    ) -> Tuple[bool, List[str]]:
        """判断是否闲置（对于云盘，未挂载即视为闲置）"""
        # 这里的instance实际上是一个disk对象
        status = instance.get("Status", "")
        
        # 只要是Available状态，就是未挂载，即闲置
        if status == "Available":
            # 计算闲置时间
            creation_time_str = instance.get("CreationTime", "")
            detached_time_str = instance.get("DetachedTime", "")
            
            idle_reason = "云盘未挂载"
            
            # 尝试计算闲置时长
            try:
                now = datetime.now(timezone.utc)
                if detached_time_str:
                    detached_time = parser.parse(detached_time_str)
                    days = (now - detached_time).days
                    idle_reason += f" (已卸载 {days} 天)"
                elif creation_time_str:
                    creation_time = parser.parse(creation_time_str)
                    days = (now - creation_time).days
                    idle_reason += f" (已创建 {days} 天)"
            except Exception:
                pass
                
            return True, [idle_reason]
            
        return False, []

    def get_optimization_suggestions(self, instance: Dict, metrics: Dict) -> str:
        """获取优化建议"""
        return "建议释放未挂载的云盘以节省成本，或创建快照后释放"

    def get_cost(self, region: str, instance_id: str) -> float:
        """获取成本（估算）"""
        # 简单估算：普通云盘 0.3元/GB/月，SSD 1元/GB/月，ESSD 1.5元/GB/月
        # 实际应调用BSS API
        return 0.0

    def analyze(self, regions: List[str] = None) -> List[Dict]:
        """执行分析"""
        self.logger.info("开始云盘资源分析...")
        
        if not regions:
            regions = self.get_all_regions()
            
        results = []
        
        for region in regions:
            try:
                disks = self.get_instances(region)
                if disks:
                    print(f"  - 区域 {region}: 发现 {len(disks)} 个未挂载云盘")
                    self.logger.info(f"区域 {region}: 找到 {len(disks)} 个未挂载云盘")
                
                for disk in disks:
                    is_idle, conditions = self.is_idle(disk, {})
                    if is_idle:
                        # 估算成本
                        size = disk.get("Size", 0)
                        category = disk.get("Category", "")
                        
                        # 简易价格表 (元/GB/月)
                        price_map = {
                            "cloud": 0.3,
                            "cloud_efficiency": 0.35,
                            "cloud_ssd": 1.0,
                            "cloud_essd": 1.5,
                        }
                        unit_price = price_map.get(category, 0.5)
                        cost = size * unit_price
                        
                        results.append({
                            "region": region,
                            "instance": disk,
                            "metrics": {},
                            "idle_conditions": conditions,
                            "optimization": self.get_optimization_suggestions(disk, {}),
                            "cost": cost
                        })
                        
            except Exception as e:
                self.logger.error(f"分析区域 {region} 失败: {e}")
                
        return results

    def generate_report(self, idle_instances: List[Dict]):
        """生成报告"""
        if not idle_instances:
            self.logger.info("没有发现未挂载的云盘")
            return

        # 转换为报告格式
        report_data = []
        for item in idle_instances:
            disk = item["instance"]
            report_data.append({
                "磁盘ID": disk.get("DiskId", ""),
                "磁盘名称": disk.get("DiskName", ""),
                "区域": item["region"],
                "可用区": disk.get("ZoneId", ""),
                "容量(GB)": disk.get("Size", 0),
                "类型": disk.get("Category", ""),
                "付费类型": disk.get("DiskChargeType", ""),
                "创建时间": disk.get("CreationTime", ""),
                "卸载时间": disk.get("DetachedTime", ""),
                "闲置详情": ", ".join(item["idle_conditions"]),
                "估算月成本(¥)": f"{item['cost']:.2f}",
                "优化建议": item["optimization"]
            })

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成Excel和HTML
        reports = ReportGenerator.generate_combined_report(
            resource_type="Disk",
            idle_instances=report_data,
            output_dir=".",
            tenant_name=self.tenant_name,
            timestamp=timestamp
        )
        
        self.logger.info(f"Excel报告已生成: {reports['excel']}")
        self.logger.info(f"HTML报告已生成: {reports['html']}")
