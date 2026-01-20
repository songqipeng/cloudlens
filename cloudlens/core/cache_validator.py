#!/usr/bin/env python3
"""
Smart Cache Validator - 智能缓存验证器

实现多层缓存验证机制，确保缓存数据的正确性和及时性。

验证策略:
- L1: 基础格式检查 (每次, <1ms)
- L2: 时间戳检查 (每次, <5ms)
- L3: 深度检查 (概率性, <100ms)
"""

import logging
import random
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class SmartCacheValidator:
    """智能缓存验证器"""

    def __init__(self, db_adapter=None, verification_probability: float = 0.1):
        """
        初始化验证器

        Args:
            db_adapter: 数据库适配器（用于深度检查）
            verification_probability: 深度检查概率 (0.0-1.0)
        """
        self.db = db_adapter
        self.verification_probability = verification_probability
        self.check_counter = 0

    def validate(
        self,
        cached_data: Any,
        billing_cycle: Optional[str] = None,
        account_id: Optional[str] = None,
        force_deep_check: bool = False
    ) -> Tuple[bool, str, bool]:
        """
        验证缓存有效性

        Args:
            cached_data: 缓存数据
            billing_cycle: 账期 (格式: YYYY-MM)
            account_id: 账号ID
            force_deep_check: 强制深度检查

        Returns:
            (is_valid, reason, should_refresh)
            - is_valid: 缓存是否有效
            - reason: 验证结果原因
            - should_refresh: 是否需要刷新缓存
        """
        # L1: 基础检查 (<1ms)
        if not self._basic_check(cached_data):
            return False, "缓存格式错误", True

        # L2: 时间戳检查 (<5ms)
        valid, reason = self._timestamp_check(cached_data, billing_cycle)
        if not valid:
            return False, reason, True

        # L3: 深度检查 (概率性或强制)
        self.check_counter += 1
        should_deep_check = force_deep_check or (
            random.random() < self.verification_probability
        )

        if should_deep_check and self.db and billing_cycle and account_id:
            valid, reason = self._deep_check(cached_data, billing_cycle, account_id)
            if not valid:
                logger.warning(f"深度检查失败: {reason}")
                return False, reason, True

        return True, "缓存有效", False

    def _basic_check(self, cached_data: Any) -> bool:
        """
        基础格式检查

        检查缓存数据是否符合预期格式
        """
        if not isinstance(cached_data, dict):
            logger.debug("缓存不是字典类型")
            return False

        # 检查必需字段
        required = ['data', 'metadata']
        if not all(k in cached_data for k in required):
            logger.debug(f"缓存缺少必需字段: {required}")
            return False

        # 检查metadata结构
        metadata = cached_data.get('metadata', {})
        if not isinstance(metadata, dict):
            logger.debug("metadata不是字典类型")
            return False

        return True

    def _timestamp_check(
        self,
        cached_data: Dict[str, Any],
        billing_cycle: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        时间戳检查

        验证缓存年龄是否在允许范围内
        - 当月数据: 6小时 TTL
        - 上月数据: 24小时 TTL
        - 历史数据: 7天 TTL
        """
        metadata = cached_data.get('metadata', {})

        if 'cached_at' not in metadata:
            return False, "缺少缓存时间戳"

        try:
            now = datetime.now()
            cached_at = datetime.fromisoformat(metadata['cached_at'])
            age_hours = (now - cached_at).total_seconds() / 3600

            # 区分当月、上月、历史月份
            current_cycle = now.strftime("%Y-%m")
            is_current = (billing_cycle == current_cycle) if billing_cycle else False

            # 计算上月
            first_day_this_month = now.replace(day=1)
            from datetime import timedelta
            last_day_last_month = first_day_this_month - timedelta(days=1)
            last_cycle = last_day_last_month.strftime("%Y-%m")
            is_last_month = (billing_cycle == last_cycle) if billing_cycle else False

            # 差异化TTL策略
            if is_current:
                max_age = 6  # 当月: 6小时
            elif is_last_month:
                max_age = 24  # 上月: 24小时
            else:
                max_age = 24 * 7  # 历史: 7天

            if age_hours > max_age:
                return False, f"缓存过期（{age_hours:.1f}h > {max_age}h）"

            return True, "时间戳有效"

        except (ValueError, TypeError) as e:
            logger.warning(f"时间戳解析错误: {e}")
            return False, f"时间戳格式错误: {e}"

    def _deep_check(
        self,
        cached_data: Dict[str, Any],
        billing_cycle: str,
        account_id: str
    ) -> Tuple[bool, str]:
        """
        深度检查

        快速查询数据库验证缓存数据准确性
        - 验证记录数
        - 验证总金额
        - 允许1%误差（考虑数据延迟）
        """
        if not self.db:
            logger.debug("数据库适配器未配置，跳过深度检查")
            return True, "深度检查跳过"

        metadata = cached_data.get('metadata', {})
        data = cached_data.get('data', {})

        try:
            # 快速查询数据库
            query = f"""
                SELECT
                    COUNT(*) as count,
                    COALESCE(SUM(payment_amount), 0) as total,
                    MAX(billing_date) as latest_date
                FROM bill_items
                WHERE billing_cycle = '{billing_cycle}'
                AND account_id = '{account_id}'
            """

            result = self.db.query(query)

            if not result or len(result) == 0:
                # 数据库无数据，但缓存有数据，可能有问题
                if metadata.get('record_count', 0) > 0:
                    return False, "数据库无数据但缓存有记录"
                return True, "数据库无数据，缓存也为空"

            db_data = result[0]
            db_count = db_data.get('count', 0)
            db_total = float(db_data.get('total') or 0)

            # 验证记录数
            cached_count = metadata.get('record_count', 0)
            if cached_count > 0:
                count_deviation = abs(db_count - cached_count) / max(cached_count, 1)
                if count_deviation > 0.01:  # 1%误差
                    return False, f"记录数不匹配（缓存:{cached_count}, DB:{db_count}, 误差:{count_deviation*100:.2f}%）"

            # 验证金额
            cached_total = data.get('total_pretax', 0)
            if cached_total > 0:
                amount_deviation = abs(db_total - cached_total) / max(cached_total, 1)
                if amount_deviation > 0.01:  # 1%误差
                    return False, f"金额不匹配（缓存:{cached_total:.2f}, DB:{db_total:.2f}, 误差:{amount_deviation*100:.2f}%）"

            logger.debug(f"深度检查通过: 记录数={db_count}, 金额={db_total:.2f}")
            return True, "深度检查通过"

        except Exception as e:
            logger.warning(f"深度检查异常: {e}")
            # 深度检查失败不影响缓存使用（保守策略）
            return True, f"深度检查异常: {e}"


class CacheHealthMonitor:
    """缓存健康度监控"""

    def __init__(self):
        self.metrics = {
            "total_checks": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "validation_failures": 0,
            "deep_checks": 0,
            "deep_check_failures": 0
        }

    def record_check(self, hit: bool, valid: bool, deep_check: bool):
        """记录检查结果"""
        self.metrics["total_checks"] += 1

        if hit:
            self.metrics["cache_hits"] += 1
            if not valid:
                self.metrics["validation_failures"] += 1
        else:
            self.metrics["cache_misses"] += 1

        if deep_check:
            self.metrics["deep_checks"] += 1
            if not valid:
                self.metrics["deep_check_failures"] += 1

    def get_health_score(self) -> float:
        """
        计算健康度评分（0-100）

        评分公式:
        - 缓存命中率权重: 60%
        - 验证成功率权重: 40%
        """
        if self.metrics["total_checks"] == 0:
            return 100.0

        hit_rate = self.metrics["cache_hits"] / self.metrics["total_checks"]

        if self.metrics["cache_hits"] > 0:
            validation_success_rate = 1 - (
                self.metrics["validation_failures"] / self.metrics["cache_hits"]
            )
        else:
            validation_success_rate = 1.0

        # 综合评分
        score = (hit_rate * 0.6 + validation_success_rate * 0.4) * 100
        return round(score, 2)

    def get_report(self) -> str:
        """生成健康报告"""
        total = self.metrics["total_checks"]
        if total == 0:
            return "无缓存检查数据"

        hit_rate = self.metrics['cache_hits'] / total * 100
        validation_fail_rate = self.metrics['validation_failures'] / total * 100
        deep_check_rate = self.metrics['deep_checks'] / total * 100

        return f"""
缓存健康报告:
- 总请求数: {total}
- 缓存命中率: {hit_rate:.1f}%
- 验证失败率: {validation_fail_rate:.1f}%
- 深度检查率: {deep_check_rate:.1f}%
- 健康度评分: {self.get_health_score()}/100
"""

    def reset(self):
        """重置统计数据"""
        for key in self.metrics:
            self.metrics[key] = 0


# 全局监控实例
_global_monitor = CacheHealthMonitor()


def get_cache_health_monitor() -> CacheHealthMonitor:
    """获取全局缓存健康监控实例"""
    return _global_monitor
