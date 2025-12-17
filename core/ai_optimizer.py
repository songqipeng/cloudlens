"""
AI成本优化建议模块

提供基于机器学习的成本优化建议
"""

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
import json

logger = logging.getLogger(__name__)


class SuggestionType(Enum):
    """优化建议类型"""
    RESOURCE_DOWNSIZE = "resource_downsize"  # 资源降配
    RESOURCE_CLEANUP = "resource_cleanup"  # 资源清理
    STORAGE_OPTIMIZATION = "storage_optimization"  # 存储优化
    DISCOUNT_OPTIMIZATION = "discount_optimization"  # 折扣优化
    BUDGET_ADJUSTMENT = "budget_adjustment"  # 预算调整
    COST_ANOMALY = "cost_anomaly"  # 成本异常


class SuggestionPriority(Enum):
    """建议优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    id: str
    type: str
    priority: str
    title: str
    description: str
    
    # 建议详情
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    current_cost: Optional[float] = None
    potential_savings: Optional[float] = None
    confidence: Optional[float] = None  # 置信度（0-1）
    
    # 执行建议
    action: Optional[str] = None  # 建议的操作
    estimated_savings: Optional[float] = None  # 预计节省金额
    
    # 上下文信息
    account_id: Optional[str] = None
    metadata: Optional[str] = None  # JSON格式
    
    # 时间信息
    created_at: Optional[datetime] = None
    status: str = "pending"  # pending, applied, dismissed


class AIOptimizer:
    """AI优化器"""
    
    def __init__(self, bill_storage_path: str = "data/bills.db"):
        self.bill_storage_path = bill_storage_path
    
    def generate_suggestions(
        self,
        account_id: Optional[str] = None,
        limit: int = 20
    ) -> List[OptimizationSuggestion]:
        """生成优化建议"""
        suggestions = []
        
        # 1. 资源降配建议
        suggestions.extend(self._suggest_resource_downsize(account_id))
        
        # 2. 闲置资源清理建议
        suggestions.extend(self._suggest_resource_cleanup(account_id))
        
        # 3. 存储优化建议
        suggestions.extend(self._suggest_storage_optimization(account_id))
        
        # 4. 折扣优化建议
        suggestions.extend(self._suggest_discount_optimization(account_id))
        
        # 5. 成本异常检测
        suggestions.extend(self._detect_cost_anomalies(account_id))
        
        # 按优先级和潜在节省金额排序
        suggestions.sort(
            key=lambda s: (
                {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(s.priority, 0),
                s.potential_savings or 0
            ),
            reverse=True
        )
        
        return suggestions[:limit]
    
    def _suggest_resource_downsize(self, account_id: Optional[str]) -> List[OptimizationSuggestion]:
        """生成资源降配建议"""
        suggestions = []
        
        # TODO: 分析资源使用率，识别可以降配的资源
        # 这里简化处理，返回示例建议
        
        return suggestions
    
    def _suggest_resource_cleanup(self, account_id: Optional[str]) -> List[OptimizationSuggestion]:
        """生成资源清理建议"""
        suggestions = []
        
        try:
            # 获取闲置资源（从闲置检测模块）
            # 这里简化处理，假设有闲置资源数据
            import sqlite3
            conn = sqlite3.connect(self.bill_storage_path)
            cursor = conn.cursor()
            
            # 查找长期未使用的资源（简化版）
            # 实际应该从idle_detector获取数据
            
            conn.close()
        except Exception as e:
            logger.error(f"Failed to generate cleanup suggestions: {e}")
        
        return suggestions
    
    def _suggest_storage_optimization(self, account_id: Optional[str]) -> List[OptimizationSuggestion]:
        """生成存储优化建议"""
        suggestions = []
        
        # TODO: 分析存储使用情况，识别可以优化的存储
        # 例如：未使用的快照、过期的备份等
        
        return suggestions
    
    def _suggest_discount_optimization(self, account_id: Optional[str]) -> List[OptimizationSuggestion]:
        """生成折扣优化建议"""
        suggestions = []
        
        try:
            # 分析折扣使用情况
            # 建议续费策略、合同谈判等
            import sqlite3
            conn = sqlite3.connect(self.bill_storage_path)
            cursor = conn.cursor()
            
            # 查找可以优化的折扣场景
            # 例如：按量付费转包年包月、续费折扣等
            
            conn.close()
        except Exception as e:
            logger.error(f"Failed to generate discount optimization suggestions: {e}")
        
        return suggestions
    
    def _detect_cost_anomalies(self, account_id: Optional[str]) -> List[OptimizationSuggestion]:
        """检测成本异常"""
        suggestions = []
        
        try:
            import sqlite3
            from datetime import datetime, timedelta
            
            conn = sqlite3.connect(self.bill_storage_path)
            cursor = conn.cursor()
            
            # 计算最近7天的平均成本
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            cursor.execute("""
                SELECT AVG(pretax_amount) as avg_cost
                FROM bill_items
                WHERE billing_date >= ? AND billing_date <= ?
                AND account_id = ?
            """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), account_id or ""))
            
            row = cursor.fetchone()
            avg_cost = row[0] if row and row[0] else 0
            
            # 计算今天的成本
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT SUM(pretax_amount) as today_cost
                FROM bill_items
                WHERE billing_date = ? AND account_id = ?
            """, (today, account_id or ""))
            
            row = cursor.fetchone()
            today_cost = row[0] if row and row[0] else 0
            
            # 如果今天的成本超过平均成本的150%，则标记为异常
            if avg_cost > 0 and today_cost > avg_cost * 1.5:
                suggestion = OptimizationSuggestion(
                    id=f"suggestion-{datetime.now().timestamp()}",
                    type=SuggestionType.COST_ANOMALY.value,
                    priority=SuggestionPriority.HIGH.value,
                    title="成本异常检测",
                    description=f"今日成本（¥{today_cost:.2f}）超过7天平均成本（¥{avg_cost:.2f}）的150%",
                    current_cost=today_cost,
                    potential_savings=(today_cost - avg_cost * 1.5),
                    confidence=0.8,
                    account_id=account_id,
                    created_at=datetime.now()
                )
                suggestions.append(suggestion)
            
            conn.close()
        except Exception as e:
            logger.error(f"Failed to detect cost anomalies: {e}")
        
        return suggestions
    
    def analyze_resource_usage(
        self,
        resource_id: str,
        resource_type: str,
        account_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """分析资源使用情况"""
        # TODO: 实现资源使用率分析
        # 返回CPU、内存、网络等使用率数据
        return None
    
    def predict_cost(
        self,
        account_id: Optional[str] = None,
        days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """预测未来成本"""
        try:
            # 使用Prophet模型进行成本预测
            # 这里简化处理，返回基于历史趋势的预测
            import sqlite3
            from datetime import datetime, timedelta
            
            conn = sqlite3.connect(self.bill_storage_path)
            cursor = conn.cursor()
            
            # 获取最近30天的成本数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            cursor.execute("""
                SELECT billing_date, SUM(pretax_amount) as daily_cost
                FROM bill_items
                WHERE billing_date >= ? AND billing_date <= ?
                AND account_id = ?
                GROUP BY billing_date
                ORDER BY billing_date
            """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), account_id or ""))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return None
            
            # 计算平均日成本
            daily_costs = [float(row[1]) for row in rows]
            avg_daily_cost = sum(daily_costs) / len(daily_costs) if daily_costs else 0
            
            # 简单预测：基于平均日成本
            predicted_cost = avg_daily_cost * days
            
            return {
                "predicted_cost": predicted_cost,
                "avg_daily_cost": avg_daily_cost,
                "confidence": 0.7,
                "method": "average"
            }
        except Exception as e:
            logger.error(f"Failed to predict cost: {e}")
            return None

