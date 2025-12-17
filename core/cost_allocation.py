"""
成本分配模块

支持将共享成本按规则分摊到各个部门/项目/标签
"""

import json
import sqlite3
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

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
    """成本分配存储管理"""
    
    def __init__(self, db_path: str = "data/cost_allocation.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 分配规则表
        cursor.execute("""
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
        cursor.execute("""
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
        
        conn.commit()
        conn.close()
    
    def create_rule(self, rule: AllocationRule) -> str:
        """创建分配规则"""
        if not rule.id:
            rule.id = f"rule-{datetime.now().timestamp()}"
        
        if not rule.created_at:
            rule.created_at = datetime.now()
        rule.updated_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO allocation_rules (
                id, name, description, method, account_id,
                service_filter, tag_filter, date_range,
                allocation_targets, allocation_weights,
                enabled, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule.id, rule.name, rule.description, rule.method, rule.account_id,
            rule.service_filter, rule.tag_filter, rule.date_range,
            rule.allocation_targets, rule.allocation_weights,
            int(rule.enabled), rule.created_at.isoformat(), rule.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return rule.id
    
    def get_rule(self, rule_id: str) -> Optional[AllocationRule]:
        """获取分配规则"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM allocation_rules WHERE id = ?", (rule_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_rule(row)
    
    def list_rules(self, account_id: Optional[str] = None, enabled_only: bool = False) -> List[AllocationRule]:
        """列出分配规则"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM allocation_rules WHERE 1=1"
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
    
    def update_rule(self, rule: AllocationRule) -> bool:
        """更新分配规则"""
        rule.updated_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE allocation_rules SET
                name = ?, description = ?, method = ?, account_id = ?,
                service_filter = ?, tag_filter = ?, date_range = ?,
                allocation_targets = ?, allocation_weights = ?,
                enabled = ?, updated_at = ?
            WHERE id = ?
        """, (
            rule.name, rule.description, rule.method, rule.account_id,
            rule.service_filter, rule.tag_filter, rule.date_range,
            rule.allocation_targets, rule.allocation_weights,
            int(rule.enabled), rule.updated_at.isoformat(), rule.id
        ))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def delete_rule(self, rule_id: str) -> bool:
        """删除分配规则"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM allocation_rules WHERE id = ?", (rule_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def save_result(self, result: AllocationResult) -> str:
        """保存分配结果"""
        if not result.id:
            result.id = f"result-{datetime.now().timestamp()}"
        
        if not result.created_at:
            result.created_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO allocation_results (
                id, rule_id, rule_name, period, total_cost,
                allocated_cost, unallocated_cost, allocations, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.id, result.rule_id, result.rule_name, result.period,
            result.total_cost, result.allocated_cost, result.unallocated_cost,
            result.allocations, result.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return result.id
    
    def list_results(
        self,
        rule_id: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 100
    ) -> List[AllocationResult]:
        """列出分配结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM allocation_results WHERE 1=1"
        params = []
        
        if rule_id:
            query += " AND rule_id = ?"
            params.append(rule_id)
        
        if period:
            query += " AND period = ?"
            params.append(period)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_result(row) for row in rows]
    
    def _row_to_rule(self, row) -> AllocationRule:
        """将数据库行转换为AllocationRule对象"""
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
        return AllocationResult(
            id=row[0],
            rule_id=row[1],
            rule_name=row[2],
            period=row[3],
            total_cost=row[4],
            allocated_cost=row[5],
            unallocated_cost=row[6],
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
        import sqlite3
        conn = sqlite3.connect(self.bill_storage_path)
        cursor = conn.cursor()
        
        query = "SELECT product_code, SUM(pretax_amount) as total FROM bill_items WHERE 1=1"
        params = []
        
        if rule.account_id:
            query += " AND account_id = ?"
            params.append(rule.account_id)
        
        # 服务过滤
        if rule.service_filter:
            services = json.loads(rule.service_filter)
            if services:
                placeholders = ",".join(["?"] * len(services))
                query += f" AND product_code IN ({placeholders})"
                params.extend(services)
        
        # 日期范围过滤
        if rule.date_range:
            dates = rule.date_range.split(",")
            if len(dates) == 2:
                query += " AND billing_date >= ? AND billing_date <= ?"
                params.extend(dates)
        
        query += " GROUP BY product_code"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {"service": row[0], "amount": float(row[1])}
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

