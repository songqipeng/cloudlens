import logging
import json
from typing import List, Dict, Any, Tuple, Optional, Callable
from cloudlens.core.idle_detector import IdleDetector
from cloudlens.providers.aliyun.provider import AliyunProvider
from cloudlens.core.rules_manager import RulesManager
from cloudlens.core.cache import CacheManager
from cloudlens.core.config import ConfigManager
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

logger = logging.getLogger(__name__)

class AnalysisService:
    @staticmethod
    def _get_all_regions(access_key: str, secret_key: str) -> List[str]:
        """
        获取所有可用的阿里云region列表
        
        Returns:
            所有region的列表
        """
        # 检查是否为Mock模式
        import os
        if os.getenv("CLOUDLENS_MOCK_MODE", "false").lower() == "true" or access_key.startswith("MOCK_"):
            # Mock模式返回模拟区域列表
            mock_regions = [
                "cn-hangzhou", "cn-shanghai", "cn-beijing", "cn-shenzhen",
                "cn-hongkong", "ap-southeast-1", "us-west-1"
            ]
            logger.info(f"Mock模式：返回 {len(mock_regions)} 个模拟区域")
            return mock_regions
        
        try:
            # 使用任意一个region来调用DescribeRegions API
            client = AcsClient(access_key, secret_key, "cn-hangzhou")
            request = CommonRequest()
            request.set_domain("ecs.cn-hangzhou.aliyuncs.com")
            request.set_method("POST")
            request.set_version("2014-05-26")
            request.set_action_name("DescribeRegions")
            
            response = client.do_action_with_exception(request)
            data = json.loads(response)
            
            regions = []
            if "Regions" in data and "Region" in data["Regions"]:
                for region in data["Regions"]["Region"]:
                    regions.append(region["RegionId"])
            
            logger.info(f"获取到 {len(regions)} 个可用区域")
            return regions
        except Exception as e:
            logger.warning(f"获取region列表失败，使用默认region列表: {e}")
            # 如果API调用失败，返回常用的region列表
            return [
                "cn-beijing", "cn-hangzhou", "cn-shanghai", "cn-shenzhen",
                "cn-qingdao", "cn-zhangjiakou", "cn-huhehaote", "cn-chengdu",
                "cn-hongkong", "ap-southeast-1", "ap-southeast-2", "ap-southeast-3",
                "ap-southeast-5", "ap-northeast-1", "ap-south-1", "us-east-1",
                "us-west-1", "eu-west-1", "eu-central-1", "me-east-1"
            ]
    
    @staticmethod
    def analyze_idle_resources(
        account_name: str, 
        days: int = 7, 
        force_refresh: bool = False,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None
    ) -> Tuple[List[Dict], bool]:
        """
        Analyze idle resources for the given account.
        
        Args:
            account_name: Cloud account name
            days: Number of days to analyze
            force_refresh: Whether to force refresh cache
            
        Returns:
            (idle_instances, is_from_cache)
        """
        cm = ConfigManager()
        account_config = cm.get_account(account_name)
        if not account_config:
            raise ValueError(f"Account '{account_name}' not found")

        # 1. Check Cache (复用同一个CacheManager实例，避免创建多个数据库连接)
        cache = CacheManager(ttl_seconds=86400)
        
        if not force_refresh:
            # 尝试从新缓存键获取
            cached_data = cache.get(resource_type="idle_result", account_name=account_name)
            # 兼容旧缓存键
            if not cached_data:
                cached_data = cache.get(resource_type="dashboard_idle", account_name=account_name)
            if cached_data:
                return cached_data, True

        # 2. Load Rules
        rm = RulesManager()
        rules = rm.get_rules()

        # 3. Get all regions
        all_regions = AnalysisService._get_all_regions(
            account_config.access_key_id,
            account_config.access_key_secret
        )
        logger.info(f"将查询 {len(all_regions)} 个区域: {', '.join(all_regions[:5])}...")
        
        # 总进度计算：检查区域 + 查询实例 + 分析实例
        # 阶段1：检查区域 (0-10%)
        # 阶段2：查询实例 (10-30%)
        # 阶段3：分析实例 (30-100%)
        total_steps = len(all_regions) + 100 + 100  # 估算总步数
        current_step = 0

        # 4. 快速检查哪些区域有资源（优化：先检查，再详细查询）
        logger.info(f"第一步：快速检查 {len(all_regions)} 个区域是否有ECS实例...")
        if progress_callback:
            progress_callback(0, total_steps, "正在获取区域列表...", "initializing")
        
        regions_with_resources = []  # 有资源的区域列表
        
        for idx, region in enumerate(all_regions):
            try:
                provider = AliyunProvider(
                    account_name=account_config.name,
                    access_key=account_config.access_key_id,
                    secret_key=account_config.access_key_secret,
                    region=region,
                )
                # 快速检查：只查询第一页获取总数
                count = provider.check_instances_count()
                if count > 0:
                    regions_with_resources.append((region, provider, count))
                    logger.info(f"区域 {region}: 有 {count} 个ECS实例")
                
                # 更新进度（检查区域阶段：0-10%）
                current_step += 1
                if progress_callback:
                    progress_callback(
                        current_step, 
                        total_steps, 
                        f"正在检查区域 {region} ({idx + 1}/{len(all_regions)})...",
                        "checking_regions"
                    )
            except Exception as e:
                logger.warning(f"检查区域 {region} 失败: {str(e)}")
                # 继续检查其他区域
                current_step += 1
                continue
        
        logger.info(f"第二步：在 {len(regions_with_resources)} 个有资源的区域中详细查询...")
        
        if progress_callback:
            progress_callback(
                current_step, 
                total_steps, 
                f"开始查询 {len(regions_with_resources)} 个有资源的区域...",
                "querying_instances"
            )
        
        # 5. 只对有资源的区域进行详细查询
        all_instances = []
        region_providers = {}  # 保存每个region的provider，用于后续获取监控数据
        
        for idx, (region, provider, expected_count) in enumerate(regions_with_resources):
            try:
                logger.info(f"正在详细查询区域 {region} 的 {expected_count} 个ECS实例...")
                if progress_callback:
                    progress_callback(
                        current_step, 
                        total_steps, 
                        f"正在查询区域 {region} 的实例 ({idx + 1}/{len(regions_with_resources)})...",
                        "querying_instances"
                    )
                
                instances = provider.list_instances()
                logger.info(f"区域 {region}: 实际获取到 {len(instances)} 个ECS实例")
                
                # 保存该region的provider，用于后续获取监控数据
                for inst in instances:
                    region_providers[inst.id] = provider
                
                all_instances.extend(instances)
                
                # 更新进度（查询实例阶段：10-30%）
                current_step += 10
                if progress_callback:
                    progress_callback(
                        current_step, 
                        total_steps, 
                        f"区域 {region} 查询完成，已获取 {len(all_instances)} 个实例",
                        "querying_instances"
                    )
            except Exception as e:
                logger.warning(f"详细查询区域 {region} 的实例失败: {str(e)}")
                # 继续查询其他区域，不中断整个流程
                current_step += 10
                continue
        
        logger.info(f"总共找到 {len(all_instances)} 个ECS实例（从 {len(regions_with_resources)} 个有资源的区域）")
        instances = all_instances
        
        if not instances:
            # 即使没有实例，也保存空结果到缓存，避免重复查询
            if progress_callback:
                progress_callback(total_steps, total_steps, "未找到ECS实例", "completed")
            cache.set(resource_type="dashboard_idle", account_name=account_name, data=[])
            cache.set(resource_type="idle_result", account_name=account_name, data=[])
            return [], False

        # 5. Analyze (优化：批量处理，显示进度)
        idle_instances = []
        total_instances = len(instances)
        logger.info(f"开始分析 {total_instances} 个ECS实例的闲置情况...")
        
        # 重新计算总步数（基于实际实例数）
        analyze_steps = max(total_instances, 100)  # 至少100步
        total_steps = current_step + analyze_steps
        
        if progress_callback:
            progress_callback(
                current_step, 
                total_steps, 
                f"开始分析 {total_instances} 个ECS实例的闲置情况...",
                "analyzing"
            )
        
        for idx, inst in enumerate(instances):
            try:
                # 每处理10个实例或每10%更新一次进度
                if (idx + 1) % 10 == 0 or idx == 0 or (idx + 1) % max(1, total_instances // 10) == 0:
                    if progress_callback:
                        progress_callback(
                            current_step + idx + 1, 
                            total_steps, 
                            f"正在分析实例 {idx + 1}/{total_instances}...",
                            "analyzing"
                        )
                    logger.info(f"分析进度: {idx + 1}/{total_instances} ({100 * (idx + 1) // total_instances}%)")
                
                # 使用对应region的provider获取监控数据
                instance_provider = region_providers.get(inst.id)
                if not instance_provider:
                    logger.warning(f"实例 {inst.id} 没有对应的provider，跳过分析")
                    continue
                
                # Metrics
                metrics = IdleDetector.fetch_ecs_metrics(instance_provider, inst.id, days)
                
                # Detection
                detector = IdleDetector(rules)
                # 转换 tags 格式：UnifiedResource.tags 是 Dict[str, str]，需要转换为列表格式
                tags_list = None
                if inst.tags and isinstance(inst.tags, dict):
                    tags_list = [{"Key": k, "Value": v} for k, v in inst.tags.items()]
                is_idle, reasons = detector.is_ecs_idle(metrics, tags_list)
                
                if is_idle:
                    idle_instances.append({
                        "instance_id": inst.id,
                        "name": inst.name or "-",
                        "region": inst.region,
                        "spec": inst.spec,
                        "reasons": reasons,
                    })
            except Exception as e:
                logger.warning(f"分析实例 {inst.id if hasattr(inst, 'id') else 'unknown'} 失败: {str(e)}")
                # 继续处理下一个实例，不中断整个分析过程
                continue
        
        logger.info(f"分析完成: 共 {len(idle_instances)} 个闲置资源（从 {total_instances} 个实例中）")
        
        if progress_callback:
            progress_callback(
                total_steps, 
                total_steps, 
                f"分析完成！找到 {len(idle_instances)} 个闲置资源",
                "saving"
            )

        # 6. Save to Cache (即使为空也保存，避免重复分析)
        try:
            cache.set(resource_type="idle_result", account_name=account_name, data=idle_instances)
            # 同时保存到 dashboard_idle 缓存（兼容旧代码）
            cache.set(resource_type="dashboard_idle", account_name=account_name, data=idle_instances)
        except Exception as e:
            logger.warning(f"保存缓存失败: {str(e)}")
            # 缓存失败不影响返回结果
        
        if progress_callback:
            progress_callback(
                total_steps, 
                total_steps, 
                "扫描完成！",
                "completed"
            )
            
        return idle_instances, False
