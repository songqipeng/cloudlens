"""
告警管理模块

提供告警规则管理、告警触发、通知发送等功能
"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
import logging
from pathlib import Path

from core.database import DatabaseFactory, DatabaseAdapter

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
    """告警存储管理（支持SQLite和MySQL）"""
    
    def __init__(self, db_path: Optional[str] = None, db_type: Optional[str] = None):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径（仅SQLite使用）
            db_type: 数据库类型（'sqlite' 或 'mysql'），None则从环境变量读取
        """
        self.db_type = db_type or os.getenv("DB_TYPE", "mysql").lower()
        
        if self.db_type == "mysql":
            self.db = DatabaseFactory.create_adapter("mysql")
            self.db_path = None
        else:
            if db_path is None:
                db_dir = Path("data")
                db_dir.mkdir(parents=True, exist_ok=True)
                db_path = str(db_dir / "alerts.db")
            self.db_path = db_path
            self.db = DatabaseFactory.create_adapter("sqlite", db_path=db_path)
        
        self._init_database()
    
    def _get_placeholder(self) -> str:
        """获取SQL占位符"""
        return "%s" if self.db_type == "mysql" else "?"
    
    def _init_database(self):
        """初始化数据库"""
        placeholder = self._get_placeholder()
        
        # 告警规则表
        if self.db_type == "mysql":
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    type VARCHAR(50) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    enabled TINYINT NOT NULL DEFAULT 1,
                    `condition` VARCHAR(50) NOT NULL,
                    threshold DECIMAL(20, 2),
                    metric VARCHAR(100),
                    account_id VARCHAR(255),
                    tag_filter TEXT,
                    service_filter TEXT,
                    notify_email VARCHAR(255),
                    notify_webhook TEXT,
                    notify_sms VARCHAR(50),
                    check_interval INT DEFAULT 60,
                    cooldown_period INT DEFAULT 300,
                    created_at DATETIME,
                    updated_at DATETIME
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        else:
            self.db.execute("""
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
        if self.db_type == "mysql":
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id VARCHAR(255) PRIMARY KEY,
                    rule_id VARCHAR(255) NOT NULL,
                    rule_name VARCHAR(255) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'triggered',
                    title VARCHAR(255) NOT NULL,
                    message TEXT,
                    metric_value DECIMAL(20, 2),
                    threshold DECIMAL(20, 2),
                    account_id VARCHAR(255),
                    resource_id VARCHAR(255),
                    resource_type VARCHAR(50),
                    triggered_at DATETIME,
                    acknowledged_at DATETIME,
                    resolved_at DATETIME,
                    closed_at DATETIME,
                    metadata TEXT,
                    FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        else:
            self.db.execute("""
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
        self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS alert_history (
                id VARCHAR(255) PRIMARY KEY,
                alert_id VARCHAR(255) NOT NULL,
                rule_id VARCHAR(255) NOT NULL,
                action VARCHAR(50) NOT NULL,
                status_before VARCHAR(20),
                status_after VARCHAR(20),
                performed_by VARCHAR(255),
                performed_at DATETIME,
                notes TEXT,
                FOREIGN KEY (alert_id) REFERENCES alerts(id)
            )
        """ if self.db_type == "mysql" else """
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
    
    def create_rule(self, rule: AlertRule) -> str:
        """创建告警规则"""
        if not rule.id:
            rule.id = f"rule-{datetime.now().timestamp()}"
        
        if not rule.created_at:
            rule.created_at = datetime.now()
        rule.updated_at = datetime.now()
        
        placeholder = self._get_placeholder()
        self.db.execute(f"""
            INSERT INTO alert_rules (
                id, name, description, type, severity, enabled,
                condition, threshold, metric, account_id,
                tag_filter, service_filter,
                notify_email, notify_webhook, notify_sms,
                check_interval, cooldown_period,
                created_at, updated_at
            ) VALUES ({', '.join([placeholder] * 19)})
        """, (
            rule.id, rule.name, rule.description, rule.type, rule.severity,
            int(rule.enabled), rule.condition, rule.threshold, rule.metric,
            rule.account_id, rule.tag_filter, rule.service_filter,
            rule.notify_email, rule.notify_webhook, rule.notify_sms,
            rule.check_interval, rule.cooldown_period,
            rule.created_at.isoformat() if rule.created_at else None,
            rule.updated_at.isoformat() if rule.updated_at else None
        ))
        
        return rule.id
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """获取告警规则"""
        placeholder = self._get_placeholder()
        rows = self.db.query(f"SELECT * FROM alert_rules WHERE id = {placeholder}", (rule_id,))
        
        if not rows:
            return None
        
        return self._row_to_rule(rows[0])
    
    def list_rules(self, account_id: Optional[str] = None, enabled_only: bool = False) -> List[AlertRule]:
        """列出告警规则"""
        placeholder = self._get_placeholder()
        query = "SELECT * FROM alert_rules WHERE 1=1"
        params = []
        
        if account_id:
            query += f" AND account_id = {placeholder}"
            params.append(account_id)
        
        if enabled_only:
            query += " AND enabled = 1"
        
        query += " ORDER BY created_at DESC"
        
        rows = self.db.query(query, tuple(params) if params else None)
        
        return [self._row_to_rule(row) for row in rows]
    
    def update_rule(self, rule: AlertRule) -> bool:
        """更新告警规则"""
        rule.updated_at = datetime.now()
        
        placeholder = self._get_placeholder()
        cursor = self.db.execute(f"""
            UPDATE alert_rules SET
                name = {placeholder}, description = {placeholder}, type = {placeholder}, severity = {placeholder}, enabled = {placeholder},
                condition = {placeholder}, threshold = {placeholder}, metric = {placeholder}, account_id = {placeholder},
                tag_filter = {placeholder}, service_filter = {placeholder},
                notify_email = {placeholder}, notify_webhook = {placeholder}, notify_sms = {placeholder},
                check_interval = {placeholder}, cooldown_period = {placeholder},
                updated_at = {placeholder}
            WHERE id = {placeholder}
        """, (
            rule.name, rule.description, rule.type, rule.severity, int(rule.enabled),
            rule.condition, rule.threshold, rule.metric, rule.account_id,
            rule.tag_filter, rule.service_filter,
            rule.notify_email, rule.notify_webhook, rule.notify_sms,
            rule.check_interval, rule.cooldown_period,
            rule.updated_at.isoformat() if rule.updated_at else None, rule.id
        ))
        
        return cursor.rowcount > 0
    
    def delete_rule(self, rule_id: str) -> bool:
        """删除告警规则"""
        placeholder = self._get_placeholder()
        cursor = self.db.execute(f"DELETE FROM alert_rules WHERE id = {placeholder}", (rule_id,))
        return cursor.rowcount > 0
    
    def create_alert(self, alert: Alert) -> str:
        """创建告警记录"""
        if not alert.id:
            alert.id = f"alert-{datetime.now().timestamp()}"
        
        if not alert.triggered_at:
            alert.triggered_at = datetime.now()
        
        placeholder = self._get_placeholder()
        self.db.execute(f"""
            INSERT INTO alerts (
                id, rule_id, rule_name, severity, status,
                title, message, metric_value, threshold,
                account_id, resource_id, resource_type,
                triggered_at, acknowledged_at, resolved_at, closed_at,
                metadata
            ) VALUES ({', '.join([placeholder] * 17)})
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
        placeholder = self._get_placeholder()
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []
        
        if account_id:
            query += f" AND account_id = {placeholder}"
            params.append(account_id)
        
        if rule_id:
            query += f" AND rule_id = {placeholder}"
            params.append(rule_id)
        
        if status:
            query += f" AND status = {placeholder}"
            params.append(status)
        
        if severity:
            query += f" AND severity = {placeholder}"
            params.append(severity)
        
        query += f" ORDER BY triggered_at DESC LIMIT {placeholder}"
        params.append(limit)
        
        rows = self.db.query(query, tuple(params))
        
        return [self._row_to_alert(row) for row in rows]
    
    def update_alert_status(
        self,
        alert_id: str,
        status: str,
        performed_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """更新告警状态"""
        placeholder = self._get_placeholder()
        
        # 获取当前状态
        rows = self.db.query(f"SELECT status, rule_id FROM alerts WHERE id = {placeholder}", (alert_id,))
        if not rows:
            return False
        
        row = rows[0]
        status_before = row['status'] if isinstance(row, dict) else row[0]
        rule_id = row.get('rule_id', '') if isinstance(row, dict) else (row[1] if len(row) > 1 else '')
        now = datetime.now()
        
        # 更新告警状态
        update_fields = [f"status = {placeholder}"]
        params = [status]
        
        if status == AlertStatus.ACKNOWLEDGED.value:
            update_fields.append(f"acknowledged_at = {placeholder}")
            params.append(now.isoformat())
        elif status == AlertStatus.RESOLVED.value:
            update_fields.append(f"resolved_at = {placeholder}")
            params.append(now.isoformat())
        elif status == AlertStatus.CLOSED.value:
            update_fields.append(f"closed_at = {placeholder}")
            params.append(now.isoformat())
        
        params.append(alert_id)
        
        cursor = self.db.execute(
            f"UPDATE alerts SET {', '.join(update_fields)} WHERE id = {placeholder}",
            tuple(params)
        )
        
        # 记录历史
        history_id = f"history-{datetime.now().timestamp()}"
        self.db.execute(f"""
            INSERT INTO alert_history (
                id, alert_id, rule_id, action, status_before, status_after,
                performed_by, performed_at, notes
            ) VALUES ({', '.join([placeholder] * 9)})
        """, (
            history_id, alert_id, rule_id, "status_change", status_before, status,
            performed_by, now.isoformat(), notes
        ))
        
        return cursor.rowcount > 0
    
    def _row_to_rule(self, row) -> AlertRule:
        """将数据库行转换为AlertRule对象"""
        if isinstance(row, dict):
            return AlertRule(
                id=row.get('id', ''),
                name=row.get('name', ''),
                description=row.get('description'),
                type=row.get('type', ''),
                severity=row.get('severity', ''),
                enabled=bool(row.get('enabled', 0)),
                condition=row.get('condition', ''),
                threshold=row.get('threshold'),
                metric=row.get('metric'),
                account_id=row.get('account_id'),
                tag_filter=row.get('tag_filter'),
                service_filter=row.get('service_filter'),
                notify_email=row.get('notify_email'),
                notify_webhook=row.get('notify_webhook'),
                notify_sms=row.get('notify_sms'),
                check_interval=int(row.get('check_interval', 60)),
                cooldown_period=int(row.get('cooldown_period', 300)),
                created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else None
            )
        else:
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
        if isinstance(row, dict):
            return Alert(
                id=row.get('id', ''),
                rule_id=row.get('rule_id', ''),
                rule_name=row.get('rule_name', ''),
                severity=row.get('severity', ''),
                status=row.get('status', ''),
                title=row.get('title', ''),
                message=row.get('message'),
                metric_value=row.get('metric_value'),
                threshold=row.get('threshold'),
                account_id=row.get('account_id'),
                resource_id=row.get('resource_id'),
                resource_type=row.get('resource_type'),
                triggered_at=datetime.fromisoformat(row['triggered_at']) if row.get('triggered_at') else None,
                acknowledged_at=datetime.fromisoformat(row['acknowledged_at']) if row.get('acknowledged_at') else None,
                resolved_at=datetime.fromisoformat(row['resolved_at']) if row.get('resolved_at') else None,
                closed_at=datetime.fromisoformat(row['closed_at']) if row.get('closed_at') else None,
                metadata=row.get('metadata')
            )
        else:
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



