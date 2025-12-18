"""
成本分配模块

支持将共享成本按规则分摊到各个部门/项目/标签
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


class AllocationMethod(Enum):
    """成本分配方法"""
    EQUAL = "equal"  # 平均分配
    PROPORTIONAL = "proportional"  # 按比例分配
    USAGE_BASED = "usage_based"  # 按使用量分配
    TAG_BASED = "tag_based"  # 按标签分配
    CUSTOM = "custom"  # 自定义规则


@dataclass
class AllocationRule:
    """成本分配规则"""
    id: str
    name: str
    description: Optional[str] = None
    method: str = AllocationMethod.EQUAL.value
    
    # 源成本过滤
    account_id: Optional[str] = None
    service_filter: Optional[str] = None  # JSON格式，如 ["ecs", "rds"]
    tag_filter: Optional[str] = None  # JSON格式，如 {"Environment": "production"}
    date_range: Optional[str] = None  # 日期范围，如 "2024-01-01,2024-01-31"
    
    # 分配目标
    allocation_targets: Optional[str] = None  # JSON格式，如 [{"type": "tag", "key": "Department", "value": "Engineering"}, ...]
    
    # 分配比例（用于proportional方法）
    allocation_weights: Optional[str] = None  # JSON格式，如 {"Engineering": 0.6, "Marketing": 0.4}
    
    # 其他配置
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class AllocationResult:
    """成本分配结果"""
    id: str
    rule_id: str
    rule_name: str
    period: str  # 如 "2024-01"
    total_cost: float
    allocated_cost: float
    unallocated_cost: float
    allocations: Optional[str] = None  # JSON格式，存储分配明细
    created_at: Optional[datetime] = None


class CostAllocationStorage:
    """成本分配存储管理（支持SQLite和MySQL）"""
    
    def __init__(self, db_path: Optional[str] = None, db_type: Optional[str] = None):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径（仅SQLite使用），默认使用data/cost_allocation.db
            db_type: 数据库类型（'sqlite' 或 'mysql'），None则从环境变量读取
        """
        self.db_type = db_type or os.getenv("DB_TYPE", "mysql").lower()
        
        if self.db_type == "mysql":
            self.db = DatabaseFactory.create_adapter("mysql")
            self.db_path = None
        else:
            if db_path is None:
                db_path = "data/cost_allocation.db"
                Path("data").mkdir(parents=True, exist_ok=True)
            self.db_path = db_path
            self.db = DatabaseFactory.create_adapter("sqlite", db_path=db_path)
        
        self._init_database()
    
    def _get_placeholder(self) -> str:
        """获取SQL占位符"""
        return "%s" if self.db_type == "mysql" else "?"
    
    def _init_database(self):
        """初始化数据库"""
        
        # 分配规则表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS allocation_rules (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                method VARCHAR(50) NOT NULL,
                account_id VARCHAR(255),
                service_filter TEXT,
                tag_filter TEXT,
                date_range VARCHAR(100),
                allocation_targets TEXT,
                allocation_weights TEXT,
                enabled TINYINT NOT NULL DEFAULT 1,
                created_at DATETIME,
                updated_at DATETIME
            )
        """ if self.db_type == "mysql" else """
            CREATE TABLE IF NOT EXISTS allocation_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                method TEXT NOT NULL,
                account_id TEXT,
                service_filter TEXT,
                tag_filter TEXT,
                date_range TEXT,
                allocation_targets TEXT,
                allocation_weights TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # 分配结果表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS allocation_results (
                id VARCHAR(255) PRIMARY KEY,
                rule_id VARCHAR(255) NOT NULL,
                rule_name VARCHAR(255) NOT NULL,
                period VARCHAR(20) NOT NULL,
                total_cost DECIMAL(20, 2) NOT NULL,
                allocated_cost DECIMAL(20, 2) NOT NULL,
                unallocated_cost DECIMAL(20, 2) NOT NULL,
                allocations TEXT,
                created_at DATETIME,
                FOREIGN KEY (rule_id) REFERENCES allocation_rules(id)
            )
        """ if self.db_type == "mysql" else """
            CREATE TABLE IF NOT EXISTS allocation_results (
                id TEXT PRIMARY KEY,
                rule_id TEXT NOT NULL,
                rule_name TEXT NOT NULL,
                period TEXT NOT NULL,
                total_cost REAL NOT NULL,
                allocated_cost REAL NOT NULL,
                unallocated_cost REAL NOT NULL,
                allocations TEXT,
                created_at TEXT,
                FOREIGN KEY (rule_id) REFERENCES allocation_rules(id)
            )
        """)
    
    def create_rule(self, rule: AllocationRule) -> str:
        """创建分配规则"""
        if not rule.id:
            rule.id = f"rule-{datetime.now().timestamp()}"
        
        if not rule.created_at:
            rule.created_at = datetime.now()
        rule.updated_at = datetime.now()
        
        placeholder = self._get_placeholder()
        self.db.execute(f"""
            INSERT INTO allocation_rules (
                id, name, description, method, account_id,
                service_filter, tag_filter, date_range,
                allocation_targets, allocation_weights,
                enabled, created_at, updated_at
            ) VALUES ({', '.join([placeholder] * 13)})
        """, (
            rule.id, rule.name, rule.description, rule.method, rule.account_id,
            rule.service_filter, rule.tag_filter, rule.date_range,
            rule.allocation_targets, rule.allocation_weights,
            int(rule.enabled),
            rule.created_at.isoformat() if rule.created_at else None,
            rule.updated_at.isoformat() if rule.updated_at else None
        ))
        
        return rule.id
    
    def get_rule(self, rule_id: str) -> Optional[AllocationRule]:
        """获取分配规则"""
        placeholder = self._get_placeholder()
        rows = self.db.query(f"SELECT * FROM allocation_rules WHERE id = {placeholder}", (rule_id,))
        
        if not rows:
            return None
        
        return self._row_to_rule(rows[0])
    
    def list_rules(self, account_id: Optional[str] = None, enabled_only: bool = False) -> List[AllocationRule]:
        """列出分配规则"""
        placeholder = self._get_placeholder()
        query = "SELECT * FROM allocation_rules WHERE 1=1"
        params = []
        
        if account_id:
            query += f" AND account_id = {placeholder}"
            params.append(account_id)
        
        if enabled_only:
            query += " AND enabled = 1"
        
        query += " ORDER BY created_at DESC"
        
        rows = self.db.query(query, tuple(params) if params else None)
        
        return [self._row_to_rule(row) for row in rows]
    
    def update_rule(self, rule: AllocationRule) -> bool:
        """更新分配规则"""
        rule.updated_at = datetime.now()
        
        placeholder = self._get_placeholder()
        cursor = self.db.execute(f"""
            UPDATE allocation_rules SET
                name = {placeholder}, description = {placeholder}, method = {placeholder}, account_id = {placeholder},
                service_filter = {placeholder}, tag_filter = {placeholder}, date_range = {placeholder},
                allocation_targets = {placeholder}, allocation_weights = {placeholder},
                enabled = {placeholder}, updated_at = {placeholder}
            WHERE id = {placeholder}
        """, (
            rule.name, rule.description, rule.method, rule.account_id,
            rule.service_filter, rule.tag_filter, rule.date_range,
            rule.allocation_targets, rule.allocation_weights,
            int(rule.enabled),
            rule.updated_at.isoformat() if rule.updated_at else None,
            rule.id
        ))
        
        return cursor.rowcount > 0
    
    def delete_rule(self, rule_id: str) -> bool:
        """删除分配规则"""
        placeholder = self._get_placeholder()
        cursor = self.db.execute(f"DELETE FROM allocation_rules WHERE id = {placeholder}", (rule_id,))
        return cursor.rowcount > 0
    
    def save_result(self, result: AllocationResult) -> str:
        """保存分配结果"""
        if not result.id:
            result.id = f"result-{datetime.now().timestamp()}"
        
        if not result.created_at:
            result.created_at = datetime.now()
        
        placeholder = self._get_placeholder()
        self.db.execute(f"""
            INSERT INTO allocation_results (
                id, rule_id, rule_name, period, total_cost,
                allocated_cost, unallocated_cost, allocations, created_at
            ) VALUES ({', '.join([placeholder] * 9)})
        """, (
            result.id, result.rule_id, result.rule_name, result.period,
            result.total_cost, result.allocated_cost, result.unallocated_cost,
            result.allocations,
            result.created_at.isoformat() if result.created_at else None
        ))
        
        return result.id
    
    def list_results(
        self,
        rule_id: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 100
    ) -> List[AllocationResult]:
        """列出分配结果"""
        placeholder = self._get_placeholder()
        query = "SELECT * FROM allocation_results WHERE 1=1"
        params = []
        
        if rule_id:
            query += f" AND rule_id = {placeholder}"
            params.append(rule_id)
        
        if period:
            query += f" AND period = {placeholder}"
            params.append(period)
        
        query += f" ORDER BY created_at DESC LIMIT {placeholder}"
        params.append(limit)
        
        rows = self.db.query(query, tuple(params))
        
        return [self._row_to_result(row) for row in rows]
    
    def _row_to_rule(self, row) -> AllocationRule:
        """将数据库行转换为AllocationRule对象"""
        if isinstance(row, dict):
            return AllocationRule(
                id=row.get('id', ''),
                name=row.get('name', ''),
                description=row.get('description'),
                method=row.get('method', ''),
                account_id=row.get('account_id'),
                service_filter=row.get('service_filter'),
                tag_filter=row.get('tag_filter'),
                date_range=row.get('date_range'),
                allocation_targets=row.get('allocation_targets'),
                allocation_weights=row.get('allocation_weights'),
                enabled=bool(row.get('enabled', 0)),
                created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else None
            )
        else:
            return AllocationRule(
                id=row[0],
                name=row[1],
                description=row[2],
                method=row[3],
                account_id=row[4],
                service_filter=row[5],
                tag_filter=row[6],
                date_range=row[7],
                allocation_targets=row[8],
                allocation_weights=row[9],
                enabled=bool(row[10]),
                created_at=datetime.fromisoformat(row[11]) if row[11] else None,
                updated_at=datetime.fromisoformat(row[12]) if row[12] else None
            )
    
    def _row_to_result(self, row) -> AllocationResult:
        """将数据库行转换为AllocationResult对象"""
        if isinstance(row, dict):
            return AllocationResult(
                id=row.get('id', ''),
                rule_id=row.get('rule_id', ''),
                rule_name=row.get('rule_name', ''),
                period=row.get('period', ''),
                total_cost=float(row.get('total_cost', 0)),
                allocated_cost=float(row.get('allocated_cost', 0)),
                unallocated_cost=float(row.get('unallocated_cost', 0)),
                allocations=row.get('allocations'),
                created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None
            )
        else:
            return AllocationResult(
                id=row[0],
                rule_id=row[1],
                rule_name=row[2],
                period=row[3],
                total_cost=float(row[4] or 0),
                allocated_cost=float(row[5] or 0),
                unallocated_cost=float(row[6] or 0),
                allocations=row[7],
                created_at=datetime.fromisoformat(row[8]) if row[8] else None
            )


class CostAllocator:
    """成本分配器"""
    
    def __init__(self, storage: CostAllocationStorage, bill_storage_path: str = "data/bills.db"):
        self.storage = storage
        self.bill_storage_path = bill_storage_path
    
    def allocate(self, rule: AllocationRule) -> AllocationResult:
        """执行成本分配"""
        # 获取源成本数据
        source_costs = self._get_source_costs(rule)
        total_cost = sum(cost["amount"] for cost in source_costs)
        
        # 根据分配方法进行分配
        allocations = self._perform_allocation(rule, source_costs)
        
        # 计算分配结果
        allocated_cost = sum(alloc["amount"] for alloc in allocations)
        unallocated_cost = total_cost - allocated_cost
        
        # 生成周期标识（如 "2024-01"）
        period = datetime.now().strftime("%Y-%m")
        if rule.date_range:
            # 从日期范围提取周期
            dates = rule.date_range.split(",")
            if len(dates) == 2:
                period = dates[0][:7]  # 取开始日期的年月
        
        # 创建分配结果
        result = AllocationResult(
            id="",  # 将在存储时生成
            rule_id=rule.id,
            rule_name=rule.name,
            period=period,
            total_cost=total_cost,
            allocated_cost=allocated_cost,
            unallocated_cost=unallocated_cost,
            allocations=json.dumps(allocations, ensure_ascii=False)
        )
        
        return result
    
    def _get_source_costs(self, rule: AllocationRule) -> List[Dict[str, Any]]:
        """获取源成本数据"""
        # 使用BillStorageManager的数据库抽象层
        from core.bill_storage import BillStorageManager
        storage = BillStorageManager(self.bill_storage_path)
        db = storage.db
        placeholder = "%s" if storage.db_type == "mysql" else "?"
        
        query = f"SELECT product_code, SUM(pretax_amount) as total FROM bill_items WHERE 1=1"
        params = []
        
        if rule.account_id:
            query += f" AND account_id = {placeholder}"
            params.append(rule.account_id)
        
        # 服务过滤
        if rule.service_filter:
            services = json.loads(rule.service_filter)
            if services:
                placeholders = ','.join([placeholder for _ in services])
                query += f" AND product_code IN ({placeholders})"
                params.extend(services)
        
        # 日期范围过滤
        if rule.date_range:
            dates = rule.date_range.split(',')
            if len(dates) == 2:
                query += f" AND billing_date >= {placeholder} AND billing_date <= {placeholder}"
                params.extend([dates[0], dates[1]])
        
        query += " GROUP BY product_code"
        
        rows = db.query(query, tuple(params) if params else None)
        
        return [
            {
                "service": row.get('product_code') if isinstance(row, dict) else row[0],
                "amount": float(row.get('total') or 0) if isinstance(row, dict) else float(row[1] or 0)
            }
            for row in rows
        ]
    
    def _perform_allocation(
        self,
        rule: AllocationRule,
        source_costs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """执行分配逻辑"""
        if rule.method == AllocationMethod.EQUAL.value:
            return self._allocate_equal(rule, source_costs)
        elif rule.method == AllocationMethod.PROPORTIONAL.value:
            return self._allocate_proportional(rule, source_costs)
        elif rule.method == AllocationMethod.USAGE_BASED.value:
            return self._allocate_usage_based(rule, source_costs)
        elif rule.method == AllocationMethod.TAG_BASED.value:
            return self._allocate_tag_based(rule, source_costs)
        else:
            logger.warning(f"Unknown allocation method: {rule.method}")
            return []
    
    def _allocate_equal(
        self,
        rule: AllocationRule,
        source_costs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """平均分配"""
        if not rule.allocation_targets:
            return []
        
        targets = json.loads(rule.allocation_targets)
        if not targets:
            return []
        
        total_cost = sum(cost["amount"] for cost in source_costs)
        cost_per_target = total_cost / len(targets)
        
        return [
            {
                "target": target,
                "amount": cost_per_target,
                "percentage": 100.0 / len(targets)
            }
            for target in targets
        ]
    
    def _allocate_proportional(
        self,
        rule: AllocationRule,
        source_costs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """按比例分配"""
        if not rule.allocation_weights:
            return []
        
        weights = json.loads(rule.allocation_weights)
        if not weights:
            return []
        
        total_weight = sum(weights.values())
        if total_weight == 0:
            return []
        
        total_cost = sum(cost["amount"] for cost in source_costs)
        
        return [
            {
                "target": target,
                "amount": total_cost * (weight / total_weight),
                "percentage": (weight / total_weight) * 100.0
            }
            for target, weight in weights.items()
        ]
    
    def _allocate_usage_based(
        self,
        rule: AllocationRule,
        source_costs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """按使用量分配"""
        # TODO: 需要获取实际使用量数据
        # 这里简化处理，使用平均分配
        return self._allocate_equal(rule, source_costs)
    
    def _allocate_tag_based(
        self,
        rule: AllocationRule,
        source_costs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """按标签分配"""
        # TODO: 需要集成虚拟标签系统
        # 这里简化处理，使用平均分配
        return self._allocate_equal(rule, source_costs)

