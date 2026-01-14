#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预算管理模块
支持预算创建、监控、预测和告警
"""

import logging
import os
import json
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from cloudlens.core.database import DatabaseFactory, DatabaseAdapter

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
        # 安全地转换日期字段
        if self.start_date:
            data['start_date'] = self.start_date.isoformat() if isinstance(self.start_date, datetime) else str(self.start_date)
        else:
            data['start_date'] = None
        if self.end_date:
            data['end_date'] = self.end_date.isoformat() if isinstance(self.end_date, datetime) else str(self.end_date)
        else:
            data['end_date'] = None
        if self.created_at:
            data['created_at'] = self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at)
        else:
            data['created_at'] = None
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at)
        else:
            data['updated_at'] = None
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
        """计算使用率（允许超过100%，表示超支）"""
        if budget == 0:
            return 0.0
        # 允许超过100%，以正确反映超支情况
        return (spent / budget) * 100
    
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
    """预算存储管理器（支持SQLite和MySQL）"""
    
    def __init__(self, db_path: Optional[str] = None, db_type: Optional[str] = None):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径（仅SQLite使用），默认使用~/.cloudlens/budgets.db
            db_type: 数据库类型（'sqlite' 或 'mysql'），None则从环境变量读取
        """
        self.db_type = db_type or os.getenv("DB_TYPE", "mysql").lower()
        
        if self.db_type == "mysql":
            self.db = DatabaseFactory.create_adapter("mysql")
            self.db_path = None
        else:
            if db_path is None:
                db_dir = Path.home() / ".cloudlens"
                db_dir.mkdir(parents=True, exist_ok=True)
                db_path = str(db_dir / "budgets.db")
            self.db_path = db_path
            self.db = DatabaseFactory.create_adapter("sqlite", db_path=db_path)
        
        self._init_database()
    
    def _get_placeholder(self) -> str:
        """获取SQL占位符"""
        return "%s" if self.db_type == "mysql" else "?"
    
    def _init_database(self):
        """初始化数据库表结构"""
        
        try:
            # 创建预算表
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    amount DECIMAL(20, 2) NOT NULL,
                    period VARCHAR(20) NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    start_date DATETIME NOT NULL,
                    end_date DATETIME NOT NULL,
                    tag_filter TEXT,
                    service_filter TEXT,
                    alerts TEXT,
                    account_id VARCHAR(255),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """ if self.db_type == "mysql" else """
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
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS budget_records (
                    id VARCHAR(255) PRIMARY KEY,
                    budget_id VARCHAR(255) NOT NULL,
                    date DATE NOT NULL,
                    spent DECIMAL(20, 2) NOT NULL,
                    predicted DECIMAL(20, 2),
                    FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_budget_date (budget_id, date)
                )
            """ if self.db_type == "mysql" else """
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
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS budget_alerts (
                    id VARCHAR(255) PRIMARY KEY,
                    budget_id VARCHAR(255) NOT NULL,
                    threshold DECIMAL(20, 2) NOT NULL,
                    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'pending',
                    FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE
                )
            """ if self.db_type == "mysql" else """
                CREATE TABLE IF NOT EXISTS budget_alerts (
                    id TEXT PRIMARY KEY,
                    budget_id TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE
                )
            """)
            
            # 创建索引（MySQL不支持IF NOT EXISTS，需要先检查）
            if self.db_type == "mysql":
                # MySQL: 先检查索引是否存在，不存在则创建
                indexes_to_create = [
                    ("idx_budgets_account", "budgets", "account_id"),
                    ("idx_budgets_period", "budgets", "period"),
                    ("idx_budget_records_budget", "budget_records", "budget_id, date"),
                    ("idx_budget_alerts_budget", "budget_alerts", "budget_id"),
                ]
                for idx_name, table_name, columns in indexes_to_create:
                    try:
                        # 检查索引是否存在
                        result = self.db.query(f"""
                            SELECT COUNT(*) as cnt 
                            FROM information_schema.statistics 
                            WHERE table_schema = DATABASE() 
                            AND table_name = '{table_name}' 
                            AND index_name = '{idx_name}'
                        """)
                        if result and result[0].get('cnt', 0) == 0:
                            self.db.execute(f"CREATE INDEX {idx_name} ON {table_name}({columns})")
                    except Exception as e:
                        logger.debug(f"Index {idx_name} creation skipped: {e}")
            else:
                # SQLite支持IF NOT EXISTS
                try:
                    self.db.execute("CREATE INDEX IF NOT EXISTS idx_budgets_account ON budgets(account_id)")
                    self.db.execute("CREATE INDEX IF NOT EXISTS idx_budgets_period ON budgets(period)")
                    self.db.execute("CREATE INDEX IF NOT EXISTS idx_budget_records_budget ON budget_records(budget_id, date)")
                    self.db.execute("CREATE INDEX IF NOT EXISTS idx_budget_alerts_budget ON budget_alerts(budget_id)")
                except Exception as e:
                    # 索引可能已存在，忽略错误
                    logger.debug(f"Index creation skipped (may already exist): {e}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def create_budget(self, budget: Budget) -> str:
        """创建预算"""
        if not budget.id:
            budget.id = str(uuid.uuid4())
        
        now = datetime.now()
        budget.created_at = now
        budget.updated_at = now
        
        placeholder = self._get_placeholder()
        try:
            self.db.execute(f"""
                INSERT INTO budgets (
                    id, name, amount, period, type,
                    start_date, end_date,
                    tag_filter, service_filter, alerts,
                    account_id, created_at, updated_at
                ) VALUES ({', '.join([placeholder] * 13)})
            """, (
                budget.id,
                budget.name,
                budget.amount,
                budget.period,
                budget.type,
                budget.start_date.isoformat() if budget.start_date else None,
                budget.end_date.isoformat() if budget.end_date else None,
                budget.tag_filter,
                budget.service_filter,
                json.dumps([alert.to_dict() for alert in budget.alerts], ensure_ascii=False),
                budget.account_id,
                budget.created_at.isoformat() if budget.created_at else None,
                budget.updated_at.isoformat() if budget.updated_at else None
            ))
            logger.info(f"Created budget: {budget.name} ({budget.id})")
            return budget.id
        except Exception as e:
            logger.error(f"Error creating budget: {e}")
            raise
    
    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """获取预算"""
        placeholder = self._get_placeholder()
        rows = self.db.query(f"SELECT * FROM budgets WHERE id = {placeholder}", (budget_id,))
        if not rows:
            return None
        
        row = rows[0]
        alerts_str = row.get('alerts') if isinstance(row, dict) else (row[10] if len(row) > 10 else '[]')
        alerts_data = json.loads(alerts_str or '[]')
        alerts = [AlertThreshold.from_dict(a) for a in alerts_data]
        
        if isinstance(row, dict):
            # 辅助函数：安全地解析日期
            def parse_date(date_value, field_name: str = "date"):
                if date_value is None:
                    logger.warning(f"预算 {budget_id} 的 {field_name} 字段为 None")
                    return None
                # 处理 datetime 对象
                if isinstance(date_value, datetime):
                    return date_value
                # 处理 date 对象（MySQL DATE 类型）
                if isinstance(date_value, date) and not isinstance(date_value, datetime):
                    # 将 date 转换为 datetime（时间设为 00:00:00）
                    return datetime.combine(date_value, datetime.min.time())
                # 处理字符串
                if isinstance(date_value, str):
                    # 移除时区信息
                    date_str = date_value.replace('Z', '').replace('+00:00', '').strip()
                    try:
                        # 尝试 ISO 格式 (YYYY-MM-DDTHH:MM:SS)
                        if 'T' in date_str:
                            return datetime.fromisoformat(date_str)
                        # 尝试 MySQL 标准格式 (YYYY-MM-DD HH:MM:SS)
                        elif ' ' in date_str:
                            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        # 尝试日期格式 (YYYY-MM-DD)
                        else:
                            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                            return parsed_date
                    except (ValueError, AttributeError) as e:
                        logger.error(f"预算 {budget_id} 的 {field_name} 字段解析失败: 值={date_value}, 类型={type(date_value)}, 错误={e}")
                        return None
                logger.warning(f"预算 {budget_id} 的 {field_name} 字段类型不支持: {type(date_value)}, 值: {date_value}")
                return None
            
            start_date = parse_date(row.get('start_date'), 'start_date')
            end_date = parse_date(row.get('end_date'), 'end_date')
            
            # 如果日期解析失败，记录详细错误并抛出异常
            if not start_date or not end_date:
                error_msg = f"预算 {budget_id} 日期解析失败: start_date={row.get('start_date')} ({type(row.get('start_date'))}), end_date={row.get('end_date')} ({type(row.get('end_date'))})"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            return Budget(
                id=row.get('id', ''),
                name=row.get('name', ''),
                amount=float(row.get('amount', 0)),
                period=row.get('period', ''),
                type=row.get('type', ''),
                start_date=start_date,
                end_date=end_date,
                tag_filter=row.get('tag_filter'),
                service_filter=row.get('service_filter'),
                alerts=alerts,
                account_id=row.get('account_id'),
                created_at=parse_date(row.get('created_at'), 'created_at'),
                updated_at=parse_date(row.get('updated_at'), 'updated_at')
            )
        else:
            # 辅助函数：安全地解析日期（元组格式）
            def parse_date_tuple(date_value, field_name: str = "date"):
                if date_value is None:
                    return None
                if isinstance(date_value, datetime):
                    return date_value
                if isinstance(date_value, date) and not isinstance(date_value, datetime):
                    return datetime.combine(date_value, datetime.min.time())
                if isinstance(date_value, str):
                    try:
                        if 'T' in date_value:
                            return datetime.fromisoformat(date_value.replace('Z', ''))
                        elif ' ' in date_value:
                            return datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S')
                        else:
                            return datetime.strptime(date_value, '%Y-%m-%d')
                    except (ValueError, AttributeError):
                        return None
                return None
            
            return Budget(
                id=row[0],
                name=row[1],
                amount=float(row[2]),
                period=row[3],
                type=row[4],
                start_date=parse_date_tuple(row[5], 'start_date'),
                end_date=parse_date_tuple(row[6], 'end_date'),
                tag_filter=row[7],
                service_filter=row[8],
                alerts=alerts,
                account_id=row[9],
                created_at=parse_date_tuple(row[11] if len(row) > 11 else None, 'created_at'),
                updated_at=parse_date_tuple(row[12] if len(row) > 12 else None, 'updated_at')
            )
    
    def list_budgets(self, account_id: Optional[str] = None) -> List[Budget]:
        """列出预算"""
        placeholder = self._get_placeholder()
        if account_id:
            rows = self.db.query(f"SELECT id FROM budgets WHERE account_id = {placeholder} ORDER BY created_at DESC", (account_id,))
        else:
            rows = self.db.query("SELECT id FROM budgets ORDER BY created_at DESC")
        
        # 处理查询结果可能为None的情况
        if rows is None:
            logger.warning("查询预算列表返回None，返回空列表")
            return []
        
        budget_ids = [row.get('id') if isinstance(row, dict) else row[0] for row in rows]
        
        budgets = []
        for budget_id in budget_ids:
            try:
                budget = self.get_budget(budget_id)
                if budget:
                    budgets.append(budget)
            except (ValueError, TypeError, AttributeError) as e:
                # 如果预算数据有问题（如日期解析失败），记录警告但继续处理其他预算
                logger.warning(f"跳过有问题的预算 {budget_id}: {str(e)}")
                continue
            except Exception as e:
                # 其他错误也记录但继续
                logger.error(f"获取预算 {budget_id} 时出错: {str(e)}")
                continue
        
        return budgets
    
    def update_budget(self, budget: Budget) -> bool:
        """更新预算"""
        budget.updated_at = datetime.now()
        
        placeholder = self._get_placeholder()
        try:
            cursor = self.db.execute(f"""
                UPDATE budgets
                SET name = {placeholder}, amount = {placeholder}, period = {placeholder}, type = {placeholder},
                    start_date = {placeholder}, end_date = {placeholder},
                    tag_filter = {placeholder}, service_filter = {placeholder}, alerts = {placeholder},
                    account_id = {placeholder}, updated_at = {placeholder}
                WHERE id = {placeholder}
            """, (
                budget.name,
                budget.amount,
                budget.period,
                budget.type,
                budget.start_date.isoformat() if budget.start_date else None,
                budget.end_date.isoformat() if budget.end_date else None,
                budget.tag_filter,
                budget.service_filter,
                json.dumps([alert.to_dict() for alert in budget.alerts], ensure_ascii=False),
                budget.account_id,
                budget.updated_at.isoformat() if budget.updated_at else None,
                budget.id
            ))
            logger.info(f"Updated budget: {budget.name} ({budget.id})")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating budget: {e}")
            return False
    
    def delete_budget(self, budget_id: str) -> bool:
        """删除预算"""
        placeholder = self._get_placeholder()
        try:
            cursor = self.db.execute(f"DELETE FROM budgets WHERE id = {placeholder}", (budget_id,))
            logger.info(f"Deleted budget: {budget_id}")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting budget: {e}")
            return False
    
    def record_spend(self, budget_id: str, date: datetime, spent: float, predicted: Optional[float] = None):
        """记录预算支出"""
        placeholder = self._get_placeholder()
        try:
            record_id = str(uuid.uuid4())
            # MySQL使用REPLACE，SQLite使用INSERT OR REPLACE
            if self.db_type == "mysql":
                self.db.execute(f"""
                    REPLACE INTO budget_records (id, budget_id, date, spent, predicted)
                    VALUES ({', '.join([placeholder] * 5)})
                """, (record_id, budget_id, date.date().isoformat(), spent, predicted))
            else:
                self.db.execute(f"""
                INSERT OR REPLACE INTO budget_records (id, budget_id, date, spent, predicted)
                    VALUES ({', '.join([placeholder] * 5)})
                """, (record_id, budget_id, date.date().isoformat(), spent, predicted))
        except Exception as e:
            logger.error(f"Error recording spend: {e}")
    
    def get_spend_history(self, budget_id: str, days: int = 30) -> List[Dict]:
        """获取支出历史"""
        placeholder = self._get_placeholder()
        rows = self.db.query(f"""
                SELECT date, spent, predicted
                FROM budget_records
            WHERE budget_id = {placeholder}
                ORDER BY date DESC
            LIMIT {placeholder}
            """, (budget_id, days))
            
        return [
            {
                'date': row.get('date') if isinstance(row, dict) else row[0],
                'spent': float(row.get('spent') or 0) if isinstance(row, dict) else float(row[1] or 0),
                'predicted': float(row.get('predicted') or 0) if isinstance(row, dict) else (float(row[2] or 0) if len(row) > 2 else None)
            }
            for row in rows
        ]
    
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
                # 使用BillStorageManager的数据库抽象层
                db = bill_storage_manager.db
                placeholder = "%s" if bill_storage_manager.db_type == "mysql" else "?"
                
                # 计算预算周期内的支出
                start_date_str = budget.start_date.strftime('%Y-%m-%d')
                end_date_str = min(now, budget.end_date).strftime('%Y-%m-%d')
                
                if budget.type == BudgetType.TOTAL:
                    # 总预算：查询所有支出
                    rows = db.query(f"""
                        SELECT SUM(pretax_amount) as total
                        FROM bill_items
                        WHERE account_id = {placeholder}
                            AND billing_date >= {placeholder}
                            AND billing_date <= {placeholder}
                            AND pretax_amount IS NOT NULL
                    """, (account_id, start_date_str, end_date_str))
                elif budget.type == BudgetType.SERVICE:
                    # 按服务预算：需要解析service_filter
                    service_filter = json.loads(budget.service_filter) if budget.service_filter else {}
                    if service_filter.get('services'):
                        placeholders = ','.join([placeholder for _ in service_filter['services']])
                        rows = db.query(f"""
                            SELECT SUM(pretax_amount) as total
                            FROM bill_items
                            WHERE account_id = {placeholder}
                                AND billing_date >= {placeholder}
                                AND billing_date <= {placeholder}
                                AND product_name IN ({placeholders})
                                AND pretax_amount IS NOT NULL
                        """, (account_id, start_date_str, end_date_str, *service_filter['services']))
                    else:
                        rows = db.query(f"""
                            SELECT SUM(pretax_amount) as total
                            FROM bill_items
                            WHERE account_id = {placeholder}
                                AND billing_date >= {placeholder}
                                AND billing_date <= {placeholder}
                                AND pretax_amount IS NOT NULL
                        """, (account_id, start_date_str, end_date_str))
                else:
                    # 按标签预算：需要匹配虚拟标签（TODO: 实现标签匹配）
                    rows = db.query(f"""
                        SELECT SUM(pretax_amount) as total
                        FROM bill_items
                        WHERE account_id = {placeholder}
                            AND billing_date >= {placeholder}
                            AND billing_date <= {placeholder}
                            AND pretax_amount IS NOT NULL
                    """, (account_id, start_date_str, end_date_str))
                
                if rows and len(rows) > 0:
                    row = rows[0]
                    total = row.get('total') if isinstance(row, dict) else row[0]
                    if total:
                        spent = float(total)
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



