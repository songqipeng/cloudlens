"""
告警管理模块

提供告警规则管理、告警触发、通知发送等功能
"""

import json
import sqlite3
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    TRIGGERED = "triggered"  # 已触发
    ACKNOWLEDGED = "acknowledged"  # 已确认
    RESOLVED = "resolved"  # 已解决
    CLOSED = "closed"  # 已关闭


class AlertCondition(Enum):
    """告警条件类型"""
    GT = "gt"  # 大于
    GTE = "gte"  # 大于等于
    LT = "lt"  # 小于
    LTE = "lte"  # 小于等于
    EQ = "eq"  # 等于
    NE = "ne"  # 不等于
    PERCENTAGE_CHANGE = "percentage_change"  # 百分比变化
    TREND_UP = "trend_up"  # 趋势上升
    TREND_DOWN = "trend_down"  # 趋势下降


class AlertType(Enum):
    """告警类型"""
    COST_THRESHOLD = "cost_threshold"  # 成本阈值
    BUDGET_OVERSPEND = "budget_overspend"  # 预算超支
    RESOURCE_ANOMALY = "resource_anomaly"  # 资源异常
    SECURITY_COMPLIANCE = "security_compliance"  # 安全合规
    CUSTOM = "custom"  # 自定义


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    description: Optional[str] = None
    type: str = AlertType.COST_THRESHOLD.value
    severity: str = AlertSeverity.WARNING.value
    enabled: bool = True
    
    # 条件配置
    condition: str = AlertCondition.GT.value
    threshold: Optional[float] = None
    metric: Optional[str] = None  # 指标名称（如：total_cost, daily_cost）
    
    # 过滤条件
    account_id: Optional[str] = None
    tag_filter: Optional[str] = None  # JSON格式
    service_filter: Optional[str] = None  # JSON格式
    
    # 通知配置
    notify_email: Optional[str] = None
    notify_webhook: Optional[str] = None
    notify_sms: Optional[str] = None
    
    # 其他配置
    check_interval: int = 60  # 检查间隔（秒）
    cooldown_period: int = 300  # 冷却期（秒），避免重复告警
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Alert:
    """告警记录"""
    id: str
    rule_id: str
    rule_name: str
    severity: str
    status: str = AlertStatus.TRIGGERED.value
    
    # 告警内容
    title: str = ""
    message: str = ""
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    
    # 上下文信息
    account_id: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    
    # 时间信息
    triggered_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # 额外数据
    metadata: Optional[str] = None  # JSON格式


class AlertStorage:
    """告警存储管理"""
    
    def __init__(self, db_path: str = "data/alerts.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 告警规则表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                type TEXT NOT NULL,
                severity TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                condition TEXT NOT NULL,
                threshold REAL,
                metric TEXT,
                account_id TEXT,
                tag_filter TEXT,
                service_filter TEXT,
                notify_email TEXT,
                notify_webhook TEXT,
                notify_sms TEXT,
                check_interval INTEGER DEFAULT 60,
                cooldown_period INTEGER DEFAULT 300,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # 告警记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                rule_id TEXT NOT NULL,
                rule_name TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'triggered',
                title TEXT NOT NULL,
                message TEXT,
                metric_value REAL,
                threshold REAL,
                account_id TEXT,
                resource_id TEXT,
                resource_type TEXT,
                triggered_at TEXT,
                acknowledged_at TEXT,
                resolved_at TEXT,
                closed_at TEXT,
                metadata TEXT,
                FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
            )
        """)
        
        # 告警历史表（用于统计）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id TEXT PRIMARY KEY,
                alert_id TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                action TEXT NOT NULL,
                status_before TEXT,
                status_after TEXT,
                performed_by TEXT,
                performed_at TEXT,
                notes TEXT,
                FOREIGN KEY (alert_id) REFERENCES alerts(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_rule(self, rule: AlertRule) -> str:
        """创建告警规则"""
        if not rule.id:
            rule.id = f"rule-{datetime.now().timestamp()}"
        
        if not rule.created_at:
            rule.created_at = datetime.now()
        rule.updated_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO alert_rules (
                id, name, description, type, severity, enabled,
                condition, threshold, metric, account_id,
                tag_filter, service_filter,
                notify_email, notify_webhook, notify_sms,
                check_interval, cooldown_period,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule.id, rule.name, rule.description, rule.type, rule.severity,
            int(rule.enabled), rule.condition, rule.threshold, rule.metric,
            rule.account_id, rule.tag_filter, rule.service_filter,
            rule.notify_email, rule.notify_webhook, rule.notify_sms,
            rule.check_interval, rule.cooldown_period,
            rule.created_at.isoformat(), rule.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return rule.id
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """获取告警规则"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM alert_rules WHERE id = ?", (rule_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_rule(row)
    
    def list_rules(self, account_id: Optional[str] = None, enabled_only: bool = False) -> List[AlertRule]:
        """列出告警规则"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM alert_rules WHERE 1=1"
        params = []
        
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        
        if enabled_only:
            query += " AND enabled = 1"
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_rule(row) for row in rows]
    
    def update_rule(self, rule: AlertRule) -> bool:
        """更新告警规则"""
        rule.updated_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE alert_rules SET
                name = ?, description = ?, type = ?, severity = ?, enabled = ?,
                condition = ?, threshold = ?, metric = ?, account_id = ?,
                tag_filter = ?, service_filter = ?,
                notify_email = ?, notify_webhook = ?, notify_sms = ?,
                check_interval = ?, cooldown_period = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            rule.name, rule.description, rule.type, rule.severity, int(rule.enabled),
            rule.condition, rule.threshold, rule.metric, rule.account_id,
            rule.tag_filter, rule.service_filter,
            rule.notify_email, rule.notify_webhook, rule.notify_sms,
            rule.check_interval, rule.cooldown_period,
            rule.updated_at.isoformat(), rule.id
        ))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def delete_rule(self, rule_id: str) -> bool:
        """删除告警规则"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def create_alert(self, alert: Alert) -> str:
        """创建告警记录"""
        if not alert.id:
            alert.id = f"alert-{datetime.now().timestamp()}"
        
        if not alert.triggered_at:
            alert.triggered_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO alerts (
                id, rule_id, rule_name, severity, status,
                title, message, metric_value, threshold,
                account_id, resource_id, resource_type,
                triggered_at, acknowledged_at, resolved_at, closed_at,
                metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.id, alert.rule_id, alert.rule_name, alert.severity, alert.status,
            alert.title, alert.message, alert.metric_value, alert.threshold,
            alert.account_id, alert.resource_id, alert.resource_type,
            alert.triggered_at.isoformat() if alert.triggered_at else None,
            alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            alert.resolved_at.isoformat() if alert.resolved_at else None,
            alert.closed_at.isoformat() if alert.closed_at else None,
            alert.metadata
        ))
        
        conn.commit()
        conn.close()
        
        return alert.id
    
    def list_alerts(
        self,
        account_id: Optional[str] = None,
        rule_id: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[Alert]:
        """列出告警记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []
        
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        
        if rule_id:
            query += " AND rule_id = ?"
            params.append(rule_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        query += " ORDER BY triggered_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_alert(row) for row in rows]
    
    def update_alert_status(
        self,
        alert_id: str,
        status: str,
        performed_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """更新告警状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取当前状态
        cursor.execute("SELECT status FROM alerts WHERE id = ?", (alert_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        
        status_before = row[0]
        now = datetime.now()
        
        # 更新告警状态
        update_fields = ["status = ?"]
        params = [status]
        
        if status == AlertStatus.ACKNOWLEDGED.value:
            update_fields.append("acknowledged_at = ?")
            params.append(now.isoformat())
        elif status == AlertStatus.RESOLVED.value:
            update_fields.append("resolved_at = ?")
            params.append(now.isoformat())
        elif status == AlertStatus.CLOSED.value:
            update_fields.append("closed_at = ?")
            params.append(now.isoformat())
        
        params.append(alert_id)
        
        cursor.execute(
            f"UPDATE alerts SET {', '.join(update_fields)} WHERE id = ?",
            params
        )
        
        # 记录历史
        history_id = f"history-{datetime.now().timestamp()}"
        cursor.execute("""
            INSERT INTO alert_history (
                id, alert_id, rule_id, action, status_before, status_after,
                performed_by, performed_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            history_id, alert_id, "", "status_change", status_before, status,
            performed_by, now.isoformat(), notes
        ))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def _row_to_rule(self, row) -> AlertRule:
        """将数据库行转换为AlertRule对象"""
        return AlertRule(
            id=row[0],
            name=row[1],
            description=row[2],
            type=row[3],
            severity=row[4],
            enabled=bool(row[5]),
            condition=row[6],
            threshold=row[7],
            metric=row[8],
            account_id=row[9],
            tag_filter=row[10],
            service_filter=row[11],
            notify_email=row[12],
            notify_webhook=row[13],
            notify_sms=row[14],
            check_interval=row[15],
            cooldown_period=row[16],
            created_at=datetime.fromisoformat(row[17]) if row[17] else None,
            updated_at=datetime.fromisoformat(row[18]) if row[18] else None
        )
    
    def _row_to_alert(self, row) -> Alert:
        """将数据库行转换为Alert对象"""
        return Alert(
            id=row[0],
            rule_id=row[1],
            rule_name=row[2],
            severity=row[3],
            status=row[4],
            title=row[5],
            message=row[6],
            metric_value=row[7],
            threshold=row[8],
            account_id=row[9],
            resource_id=row[10],
            resource_type=row[11],
            triggered_at=datetime.fromisoformat(row[12]) if row[12] else None,
            acknowledged_at=datetime.fromisoformat(row[13]) if row[13] else None,
            resolved_at=datetime.fromisoformat(row[14]) if row[14] else None,
            closed_at=datetime.fromisoformat(row[15]) if row[15] else None,
            metadata=row[16]
        )

