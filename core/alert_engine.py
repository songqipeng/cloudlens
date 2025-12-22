"""
告警引擎

负责告警规则的评估和触发
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from core.alert_manager import (
    AlertStorage, AlertRule, Alert, AlertCondition, AlertType, AlertSeverity, AlertStatus
)
from core.bill_storage import BillStorageManager

logger = logging.getLogger(__name__)


class AlertEvaluator:
    """告警评估器"""
    
    def __init__(self, alert_storage: AlertStorage, bill_storage: BillStorageManager):
        self.alert_storage = alert_storage
        self.bill_storage = bill_storage
    
    def evaluate_rule(self, rule: AlertRule, account_id: Optional[str] = None) -> Optional[Alert]:
        """评估告警规则，如果触发则返回Alert对象"""
        if not rule.enabled:
            return None
        
        # 检查冷却期
        if self._is_in_cooldown(rule, account_id):
            return None
        
        # 根据告警类型评估
        if rule.type == AlertType.COST_THRESHOLD.value:
            return self._evaluate_cost_threshold(rule, account_id)
        elif rule.type == AlertType.BUDGET_OVERSPEND.value:
            return self._evaluate_budget_overspend(rule, account_id)
        elif rule.type == AlertType.RESOURCE_ANOMALY.value:
            return self._evaluate_resource_anomaly(rule, account_id)
        elif rule.type == AlertType.SECURITY_COMPLIANCE.value:
            return self._evaluate_security_compliance(rule, account_id)
        else:
            logger.warning(f"Unknown alert type: {rule.type}")
            return None
    
    def _evaluate_cost_threshold(self, rule: AlertRule, account_id: Optional[str]) -> Optional[Alert]:
        """评估成本阈值告警"""
        if not rule.threshold or not rule.metric:
            return None
        
        # 获取当前指标值
        metric_value = self._get_metric_value(rule.metric, account_id, rule.tag_filter, rule.service_filter)
        if metric_value is None:
            return None
        
        # 评估条件
        triggered = self._check_condition(metric_value, rule.condition, rule.threshold)
        
        if triggered:
            return self._create_alert(
                rule=rule,
                title=f"成本阈值告警: {rule.name}",
                message=f"{rule.metric} = {metric_value:.2f}，超过阈值 {rule.threshold}",
                metric_value=metric_value,
                threshold=rule.threshold,
                account_id=account_id
            )
        
        return None
    
    def _evaluate_budget_overspend(self, rule: AlertRule, account_id: Optional[str]) -> Optional[Alert]:
        """评估预算超支告警"""
        # TODO: 集成预算管理模块
        # 这里需要从预算管理模块获取预算状态
        return None
    
    def _evaluate_resource_anomaly(self, rule: AlertRule, account_id: Optional[str]) -> Optional[Alert]:
        """评估资源异常告警"""
        # TODO: 实现资源异常检测逻辑
        return None
    
    def _evaluate_security_compliance(self, rule: AlertRule, account_id: Optional[str]) -> Optional[Alert]:
        """评估安全合规告警"""
        # TODO: 实现安全合规检查逻辑
        return None
    
    def _get_metric_value(
        self,
        metric: str,
        account_id: Optional[str],
        tag_filter: Optional[str],
        service_filter: Optional[str]
    ) -> Optional[float]:
        """获取指标值"""
        try:
            if metric == "total_cost":
                return self._get_total_cost(account_id, tag_filter, service_filter)
            elif metric == "daily_cost":
                return self._get_daily_cost(account_id, tag_filter, service_filter)
            elif metric == "monthly_cost":
                return self._get_monthly_cost(account_id, tag_filter, service_filter)
            elif metric.startswith("cost_"):
                # 支持 cost_ecs, cost_rds 等
                service = metric.replace("cost_", "")
                return self._get_service_cost(account_id, service, tag_filter)
            else:
                logger.warning(f"Unknown metric: {metric}")
                return None
        except Exception as e:
            logger.error(f"Failed to get metric value: {e}")
            return None
    
    def _get_total_cost(
        self,
        account_id: Optional[str],
        tag_filter: Optional[str],
        service_filter: Optional[str]
    ) -> float:
        """获取总成本"""
        # 使用BillStorageManager的数据库抽象层
        query = "SELECT SUM(pretax_amount) FROM bill_items WHERE 1=1"
        params = []
        
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        
        # TODO: 应用tag_filter和service_filter
        
        rows = self.bill_storage.db.query(query, tuple(params) if params else None)
        if rows and len(rows) > 0:
            row = rows[0]
            value = row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]
            return float(value) if value else 0.0
        return 0.0
    
    def _get_daily_cost(
        self,
        account_id: Optional[str],
        tag_filter: Optional[str],
        service_filter: Optional[str]
    ) -> float:
        """获取今日成本"""
        # 使用BillStorageManager的数据库抽象层
        today = datetime.now().strftime('%Y-%m-%d')
        query = "SELECT SUM(pretax_amount) FROM bill_items WHERE billing_date = ?"
        params = [today]
        
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        
        rows = self.bill_storage.db.query(query, tuple(params))
        if rows and len(rows) > 0:
            row = rows[0]
            value = row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]
            return float(value) if value else 0.0
        return 0.0
    
    def _get_monthly_cost(
        self,
        account_id: Optional[str],
        tag_filter: Optional[str],
        service_filter: Optional[str]
    ) -> float:
        """获取本月成本"""
        # 使用BillStorageManager的数据库抽象层
        now = datetime.now()
        month_start = now.replace(day=1).strftime('%Y-%m-%d')
        month_end = now.strftime('%Y-%m-%d')
        
        query = """
            SELECT SUM(pretax_amount) FROM bill_items
            WHERE billing_date >= ? AND billing_date <= ?
        """
        params = [month_start, month_end]
        
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        
        rows = self.bill_storage.db.query(query, tuple(params))
        if rows and len(rows) > 0:
            row = rows[0]
            value = row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]
            return float(value) if value else 0.0
        return 0.0
    
    def _get_service_cost(
        self,
        account_id: Optional[str],
        service: str,
        tag_filter: Optional[str]
    ) -> float:
        """获取服务成本"""
        # 使用BillStorageManager的数据库抽象层
        query = "SELECT SUM(pretax_amount) FROM bill_items WHERE product_code = ?"
        params = [service]
        
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        
        rows = self.bill_storage.db.query(query, tuple(params))
        if rows and len(rows) > 0:
            row = rows[0]
            value = row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]
            return float(value) if value else 0.0
        return 0.0
    
    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """检查条件是否满足"""
        if condition == AlertCondition.GT.value:
            return value > threshold
        elif condition == AlertCondition.GTE.value:
            return value >= threshold
        elif condition == AlertCondition.LT.value:
            return value < threshold
        elif condition == AlertCondition.LTE.value:
            return value <= threshold
        elif condition == AlertCondition.EQ.value:
            return abs(value - threshold) < 0.01  # 浮点数比较
        elif condition == AlertCondition.NE.value:
            return abs(value - threshold) >= 0.01
        else:
            logger.warning(f"Unknown condition: {condition}")
            return False
    
    def _is_in_cooldown(self, rule: AlertRule, account_id: Optional[str]) -> bool:
        """检查是否在冷却期内"""
        if rule.cooldown_period <= 0:
            return False
        
        # 查找最近的告警记录
        recent_alerts = self.alert_storage.list_alerts(
            account_id=account_id,
            rule_id=rule.id,
            limit=1
        )
        
        if not recent_alerts:
            return False
        
        last_alert = recent_alerts[0]
        if not last_alert.triggered_at:
            return False
        
        cooldown_end = last_alert.triggered_at + timedelta(seconds=rule.cooldown_period)
        return datetime.now() < cooldown_end
    
    def _create_alert(
        self,
        rule: AlertRule,
        title: str,
        message: str,
        metric_value: Optional[float] = None,
        threshold: Optional[float] = None,
        account_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """创建告警对象"""
        import json
        
        return Alert(
            id="",  # 将在存储时生成
            rule_id=rule.id,
            rule_name=rule.name,
            severity=rule.severity,
            status=AlertStatus.TRIGGERED.value,
            title=title,
            message=message,
            metric_value=metric_value,
            threshold=threshold,
            account_id=account_id or rule.account_id,
            resource_id=resource_id,
            resource_type=resource_type,
            triggered_at=datetime.now(),
            metadata=json.dumps(metadata) if metadata else None
        )


class AlertEngine:
    """告警引擎"""
    
    def __init__(self, alert_storage: AlertStorage, bill_storage: BillStorageManager):
        self.alert_storage = alert_storage
        self.evaluator = AlertEvaluator(alert_storage, bill_storage)
    
    def check_all_rules(self, account_id: Optional[str] = None) -> List[Alert]:
        """检查所有启用的告警规则"""
        rules = self.alert_storage.list_rules(account_id=account_id, enabled_only=True)
        triggered_alerts = []
        
        for rule in rules:
            try:
                alert = self.evaluator.evaluate_rule(rule, account_id)
                if alert:
                    # 保存告警
                    alert_id = self.alert_storage.create_alert(alert)
                    alert.id = alert_id
                    triggered_alerts.append(alert)
                    logger.info(f"Alert triggered: {alert.title} (Rule: {rule.name})")
            except Exception as e:
                logger.error(f"Failed to evaluate rule {rule.id}: {e}")
        
        return triggered_alerts
    
    def check_rule(self, rule_id: str, account_id: Optional[str] = None) -> Optional[Alert]:
        """检查单个告警规则"""
        rule = self.alert_storage.get_rule(rule_id)
        if not rule:
            return None
        
        alert = self.evaluator.evaluate_rule(rule, account_id)
        if alert:
            alert_id = self.alert_storage.create_alert(alert)
            alert.id = alert_id
            return alert
        
        return None



