#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预算管理模块
支持预算创建、监控、预测和告警
"""

import logging
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class BudgetPeriod(str, Enum):
    """预算周期"""
    MONTHLY = "monthly"      # 月度
    QUARTERLY = "quarterly"  # 季度
    YEARLY = "yearly"        # 年度


class BudgetType(str, Enum):
    """预算类型"""
    TOTAL = "total"          # 总预算
    TAG = "tag"              # 按标签预算
    SERVICE = "service"      # 按服务预算


@dataclass
class AlertThreshold:
    """告警阈值"""
    percentage: float        # 百分比（50, 80, 100）
    enabled: bool = True
    notification_channels: List[str] = None  # 通知渠道（email, webhook等）
    
    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = []
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AlertThreshold':
        return cls(**data)


@dataclass
class Budget:
    """预算"""
    id: str
    name: str
    amount: float            # 预算金额
    period: str              # 周期（monthly/quarterly/yearly）
    type: str                # 类型（total/tag/service）
    start_date: datetime
    end_date: datetime
    tag_filter: Optional[str] = None      # 标签过滤（JSON格式）
    service_filter: Optional[str] = None  # 服务过滤（JSON格式）
    alerts: List[AlertThreshold] = None   # 告警规则
    account_id: Optional[str] = None      # 账号ID
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['alerts'] = [alert.to_dict() for alert in self.alerts]
        if self.start_date:
            data['start_date'] = self.start_date.isoformat()
        if self.end_date:
            data['end_date'] = self.end_date.isoformat()
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Budget':
        alerts = [AlertThreshold.from_dict(a) for a in data.get('alerts', [])]
        start_date = datetime.fromisoformat(data['start_date']) if data.get('start_date') else None
        end_date = datetime.fromisoformat(data['end_date']) if data.get('end_date') else None
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        updated_at = datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        return cls(
            id=data['id'],
            name=data['name'],
            amount=data['amount'],
            period=data['period'],
            type=data['type'],
            start_date=start_date,
            end_date=end_date,
            tag_filter=data.get('tag_filter'),
            service_filter=data.get('service_filter'),
            alerts=alerts,
            account_id=data.get('account_id'),
            created_at=created_at,
            updated_at=updated_at
        )


@dataclass
class BudgetStatus:
    """预算状态"""
    budget_id: str
    spent: float             # 已支出
    remaining: float         # 剩余预算
    usage_rate: float        # 使用率（百分比）
    days_elapsed: int        # 已过天数
    days_total: int          # 总天数
    predicted_spend: Optional[float] = None  # 预测支出
    predicted_overspend: Optional[float] = None  # 预测超支
    alerts_triggered: List[Dict] = None      # 已触发的告警
    
    def __post_init__(self):
        if self.alerts_triggered is None:
            self.alerts_triggered = []
    
    def to_dict(self) -> Dict:
        return asdict(self)


class BudgetCalculator:
    """预算计算器"""
    
    @staticmethod
    def calculate_period_dates(period: str, start_date: datetime) -> Tuple[datetime, datetime]:
        """
        计算预算周期的开始和结束日期
        
        Args:
            period: 周期类型（monthly/quarterly/yearly）
            start_date: 开始日期
            
        Returns:
            (start_date, end_date)
        """
        if period == BudgetPeriod.MONTHLY:
            # 月度：从开始日期的下一个月1号到下下个月1号
            if start_date.month == 12:
                end_date = datetime(start_date.year + 1, 1, 1)
            else:
                end_date = datetime(start_date.year, start_date.month + 1, 1)
        elif period == BudgetPeriod.QUARTERLY:
            # 季度：3个月
            month = start_date.month
            quarter_start_month = ((month - 1) // 3) * 3 + 1
            quarter_end_month = quarter_start_month + 3
            if quarter_end_month > 12:
                end_date = datetime(start_date.year + 1, quarter_end_month - 12, 1)
            else:
                end_date = datetime(start_date.year, quarter_end_month, 1)
        elif period == BudgetPeriod.YEARLY:
            # 年度：1年
            end_date = datetime(start_date.year + 1, start_date.month, start_date.day)
        else:
            end_date = start_date + timedelta(days=30)  # 默认30天
        
        return start_date, end_date
    
    @staticmethod
    def calculate_usage_rate(spent: float, budget: float) -> float:
        """计算使用率"""
        if budget == 0:
            return 0.0
        return min((spent / budget) * 100, 100.0)
    
    @staticmethod
    def predict_spend(
        current_spend: float,
        days_elapsed: int,
        days_total: int,
        historical_data: Optional[List[float]] = None
    ) -> float:
        """
        预测总支出
        
        Args:
            current_spend: 当前已支出
            days_elapsed: 已过天数
            days_total: 总天数
            historical_data: 历史支出数据（可选）
            
        Returns:
            预测的总支出
        """
        if days_elapsed == 0:
            return 0.0
        
        # 简单线性预测：基于当前平均日支出
        daily_average = current_spend / days_elapsed
        predicted = daily_average * days_total
        
        # 如果有历史数据，可以使用更复杂的预测算法
        # TODO: 集成Prophet或其他时间序列预测模型
        
        return predicted
    
    @staticmethod
    def check_alerts(
        budget: Budget,
        status: BudgetStatus
    ) -> List[Dict]:
        """
        检查告警阈值
        
        Returns:
            触发的告警列表
        """
        triggered = []
        
        for alert in budget.alerts:
            if not alert.enabled:
                continue
            
            if status.usage_rate >= alert.percentage:
                triggered.append({
                    "threshold": alert.percentage,
                    "current_rate": status.usage_rate,
                    "channels": alert.notification_channels,
                    "triggered_at": datetime.now().isoformat()
                })
        
        return triggered


class BudgetStorage:
    """预算存储管理器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径，默认使用~/.cloudlens/budgets.db
        """
        if db_path is None:
            db_dir = Path.home() / ".cloudlens"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "budgets.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 创建预算表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    period TEXT NOT NULL,
                    type TEXT NOT NULL,
                    start_date TIMESTAMP NOT NULL,
                    end_date TIMESTAMP NOT NULL,
                    tag_filter TEXT,
                    service_filter TEXT,
                    alerts TEXT,
                    account_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建预算执行记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budget_records (
                    id TEXT PRIMARY KEY,
                    budget_id TEXT NOT NULL,
                    date DATE NOT NULL,
                    spent REAL NOT NULL,
                    predicted REAL,
                    FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE,
                    UNIQUE(budget_id, date)
                )
            """)
            
            # 创建预算告警记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budget_alerts (
                    id TEXT PRIMARY KEY,
                    budget_id TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_budgets_account ON budgets(account_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_budgets_period ON budgets(period)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_budget_records_budget ON budget_records(budget_id, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_budget_alerts_budget ON budget_alerts(budget_id)")
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def create_budget(self, budget: Budget) -> str:
        """创建预算"""
        if not budget.id:
            budget.id = str(uuid.uuid4())
        
        now = datetime.now()
        budget.created_at = now
        budget.updated_at = now
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO budgets (
                    id, name, amount, period, type,
                    start_date, end_date,
                    tag_filter, service_filter, alerts,
                    account_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                budget.id,
                budget.name,
                budget.amount,
                budget.period,
                budget.type,
                budget.start_date.isoformat(),
                budget.end_date.isoformat(),
                budget.tag_filter,
                budget.service_filter,
                json.dumps([alert.to_dict() for alert in budget.alerts]),
                budget.account_id,
                budget.created_at.isoformat(),
                budget.updated_at.isoformat()
            ))
            
            conn.commit()
            logger.info(f"Created budget: {budget.name} ({budget.id})")
            return budget.id
        except Exception as e:
            logger.error(f"Error creating budget: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """获取预算"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM budgets WHERE id = ?", (budget_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            alerts_data = json.loads(row['alerts'] or '[]')
            alerts = [AlertThreshold.from_dict(a) for a in alerts_data]
            
            budget = Budget(
                id=row['id'],
                name=row['name'],
                amount=row['amount'],
                period=row['period'],
                type=row['type'],
                start_date=datetime.fromisoformat(row['start_date']),
                end_date=datetime.fromisoformat(row['end_date']),
                tag_filter=row['tag_filter'],
                service_filter=row['service_filter'],
                alerts=alerts,
                account_id=row['account_id'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
            )
            
            return budget
        finally:
            conn.close()
    
    def list_budgets(self, account_id: Optional[str] = None) -> List[Budget]:
        """列出预算"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if account_id:
                cursor.execute("SELECT id FROM budgets WHERE account_id = ? ORDER BY created_at DESC", (account_id,))
            else:
                cursor.execute("SELECT id FROM budgets ORDER BY created_at DESC")
            
            budget_ids = [row['id'] for row in cursor.fetchall()]
            
            budgets = []
            for budget_id in budget_ids:
                budget = self.get_budget(budget_id)
                if budget:
                    budgets.append(budget)
            
            return budgets
        finally:
            conn.close()
    
    def update_budget(self, budget: Budget) -> bool:
        """更新预算"""
        budget.updated_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE budgets
                SET name = ?, amount = ?, period = ?, type = ?,
                    start_date = ?, end_date = ?,
                    tag_filter = ?, service_filter = ?, alerts = ?,
                    account_id = ?, updated_at = ?
                WHERE id = ?
            """, (
                budget.name,
                budget.amount,
                budget.period,
                budget.type,
                budget.start_date.isoformat(),
                budget.end_date.isoformat(),
                budget.tag_filter,
                budget.service_filter,
                json.dumps([alert.to_dict() for alert in budget.alerts]),
                budget.account_id,
                budget.updated_at.isoformat(),
                budget.id
            ))
            
            conn.commit()
            logger.info(f"Updated budget: {budget.name} ({budget.id})")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating budget: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_budget(self, budget_id: str) -> bool:
        """删除预算"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
            conn.commit()
            logger.info(f"Deleted budget: {budget_id}")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting budget: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def record_spend(self, budget_id: str, date: datetime, spent: float, predicted: Optional[float] = None):
        """记录预算支出"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            record_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT OR REPLACE INTO budget_records (id, budget_id, date, spent, predicted)
                VALUES (?, ?, ?, ?, ?)
            """, (
                record_id,
                budget_id,
                date.date().isoformat(),
                spent,
                predicted
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error recording spend: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_spend_history(self, budget_id: str, days: int = 30) -> List[Dict]:
        """获取支出历史"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT date, spent, predicted
                FROM budget_records
                WHERE budget_id = ?
                ORDER BY date DESC
                LIMIT ?
            """, (budget_id, days))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    "date": row['date'],
                    "spent": row['spent'],
                    "predicted": row['predicted']
                })
            
            return records
        finally:
            conn.close()
    
    def calculate_budget_status(
        self,
        budget: Budget,
        account_id: str,
        bill_storage_manager = None
    ) -> BudgetStatus:
        """
        计算预算状态
        
        Args:
            budget: 预算对象
            account_id: 账号ID
            bill_storage_manager: 账单存储管理器（可选）
            
        Returns:
            预算状态
        """
        now = datetime.now()
        
        # 计算已过天数和总天数
        days_total = (budget.end_date - budget.start_date).days
        days_elapsed = (now - budget.start_date).days
        days_elapsed = max(0, min(days_elapsed, days_total))
        
        # 计算已支出
        spent = 0.0
        
        if bill_storage_manager:
            try:
                # 从账单数据库获取实际支出
                import sqlite3
                conn = sqlite3.connect(bill_storage_manager.db_path)
                cursor = conn.cursor()
                
                # 计算预算周期内的支出
                start_date_str = budget.start_date.strftime('%Y-%m-%d')
                end_date_str = min(now, budget.end_date).strftime('%Y-%m-%d')
                
                if budget.type == BudgetType.TOTAL:
                    # 总预算：查询所有支出
                    cursor.execute("""
                        SELECT SUM(pretax_amount) as total
                        FROM bill_items
                        WHERE account_id = ?
                            AND billing_date >= ?
                            AND billing_date <= ?
                            AND pretax_amount IS NOT NULL
                    """, (account_id, start_date_str, end_date_str))
                elif budget.type == BudgetType.SERVICE:
                    # 按服务预算：需要解析service_filter
                    service_filter = json.loads(budget.service_filter) if budget.service_filter else {}
                    if service_filter.get('services'):
                        placeholders = ','.join(['?' for _ in service_filter['services']])
                        cursor.execute(f"""
                            SELECT SUM(pretax_amount) as total
                            FROM bill_items
                            WHERE account_id = ?
                                AND billing_date >= ?
                                AND billing_date <= ?
                                AND product_name IN ({placeholders})
                                AND pretax_amount IS NOT NULL
                        """, (account_id, start_date_str, end_date_str, *service_filter['services']))
                    else:
                        cursor.execute("""
                            SELECT SUM(pretax_amount) as total
                            FROM bill_items
                            WHERE account_id = ?
                                AND billing_date >= ?
                                AND billing_date <= ?
                                AND pretax_amount IS NOT NULL
                        """, (account_id, start_date_str, end_date_str))
                else:
                    # 按标签预算：需要匹配虚拟标签（TODO: 实现标签匹配）
                    cursor.execute("""
                        SELECT SUM(pretax_amount) as total
                        FROM bill_items
                        WHERE account_id = ?
                            AND billing_date >= ?
                            AND billing_date <= ?
                            AND pretax_amount IS NOT NULL
                    """, (account_id, start_date_str, end_date_str))
                
                row = cursor.fetchone()
                if row and row[0]:
                    spent = float(row[0])
                
                conn.close()
            except Exception as e:
                logger.error(f"Error calculating budget spend from bills: {e}")
        
        # 计算剩余预算和使用率
        remaining = max(0, budget.amount - spent)
        usage_rate = BudgetCalculator.calculate_usage_rate(spent, budget.amount)
        
        # 预测支出
        predicted_spend = None
        predicted_overspend = None
        if days_elapsed > 0:
            predicted_spend = BudgetCalculator.predict_spend(
                spent, days_elapsed, days_total
            )
            predicted_overspend = max(0, predicted_spend - budget.amount)
        
        # 创建临时状态用于告警检查
        temp_status = BudgetStatus(
            budget_id=budget.id,
            spent=spent,
            remaining=remaining,
            usage_rate=usage_rate,
            days_elapsed=days_elapsed,
            days_total=days_total,
            predicted_spend=predicted_spend,
            predicted_overspend=predicted_overspend
        )
        
        # 检查告警
        alerts_triggered = BudgetCalculator.check_alerts(budget, temp_status)
        
        status = BudgetStatus(
            budget_id=budget.id,
            spent=spent,
            remaining=remaining,
            usage_rate=usage_rate,
            days_elapsed=days_elapsed,
            days_total=days_total,
            predicted_spend=predicted_spend,
            predicted_overspend=predicted_overspend,
            alerts_triggered=alerts_triggered
        )
        
        # 记录支出
        self.record_spend(budget.id, now, spent, predicted_spend)
        
        return status

