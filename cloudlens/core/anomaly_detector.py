#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成本异常检测模块
基于历史数据建立基线，检测成本异常波动
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from statistics import mean, stdev
import json

from cloudlens.core.bill_storage import BillStorageManager
from cloudlens.core.database import DatabaseFactory

logger = logging.getLogger(__name__)


@dataclass
class Anomaly:
    """成本异常"""
    id: str
    account_id: str
    date: str  # YYYY-MM-DD
    current_cost: float
    baseline_cost: float
    deviation_pct: float  # 偏差百分比
    severity: str  # low/medium/high/critical
    root_cause: Optional[str] = None
    created_at: Optional[datetime] = None


class AnomalyDetector:
    """成本异常检测器"""
    
    def __init__(self):
        self.bill_storage = BillStorageManager()
        self.db = DatabaseFactory.create_adapter("mysql")
    
    def detect(
        self,
        account_id: str,
        date: Optional[str] = None,
        baseline_days: int = 30,
        threshold_std: float = 2.0
    ) -> List[Anomaly]:
        """
        检测成本异常
        
        Args:
            account_id: 账号ID
            date: 检测日期（YYYY-MM-DD），如果为None则使用今天
            baseline_days: 基线天数（默认30天）
            threshold_std: 阈值（标准差的倍数，默认2.0）
            
        Returns:
            异常列表
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # 1. 获取当天成本
            current_cost = self._get_daily_cost(account_id, date)
            if current_cost is None:
                logger.warning(f"无法获取账号 {account_id} 在 {date} 的成本数据")
                return []
            
            # 2. 获取历史基线（过去N天）
            baseline = self._calculate_baseline(account_id, baseline_days, date)
            if not baseline:
                logger.warning(f"无法计算账号 {account_id} 的基线数据")
                return []
            
            # 3. 判断是否异常
            mean_cost = baseline["mean"]
            std_cost = baseline["std"]
            threshold = mean_cost + threshold_std * std_cost
            
            anomalies = []
            
            if current_cost > threshold:
                # 计算偏差百分比
                deviation_pct = ((current_cost - mean_cost) / mean_cost) * 100
                
                # 确定严重程度
                if deviation_pct >= 100:
                    severity = "critical"
                elif deviation_pct >= 50:
                    severity = "high"
                elif deviation_pct >= 30:
                    severity = "medium"
                else:
                    severity = "low"
                
                # 分析根因（简化版，后续可以用AI增强）
                root_cause = self._analyze_root_cause(account_id, date, current_cost, baseline)
                
                anomaly = Anomaly(
                    id=f"{account_id}-{date}",
                    account_id=account_id,
                    date=date,
                    current_cost=current_cost,
                    baseline_cost=mean_cost,
                    deviation_pct=deviation_pct,
                    severity=severity,
                    root_cause=root_cause,
                    created_at=datetime.now()
                )
                
                anomalies.append(anomaly)
                
                # 保存异常记录
                self._save_anomaly(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"检测成本异常失败: {str(e)}")
            return []
    
    def _get_daily_cost(self, account_id: str, date: str) -> Optional[float]:
        """获取指定日期的成本"""
        try:
            # 从账单数据中获取
            billing_cycle = date[:7]  # YYYY-MM
            items = self.bill_storage.get_bill_items(
                account_id=account_id,
                billing_cycle=billing_cycle
            )
            
            if not items:
                return None
            
            # 过滤指定日期的数据
            daily_cost = 0.0
            for item in items:
                item_date = item.get("billing_date", "")
                if item_date == date:
                    cost = float(item.get("payment_amount", 0) or 0)
                    daily_cost += cost
            
            return daily_cost if daily_cost > 0 else None
            
        except Exception as e:
            logger.error(f"获取日成本失败: {str(e)}")
            return None
    
    def _calculate_baseline(
        self,
        account_id: str,
        days: int,
        end_date: str
    ) -> Optional[Dict[str, float]]:
        """计算基线（平均值和标准差）"""
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            start = end - timedelta(days=days)
            
            # 获取历史成本数据
            daily_costs = []
            current = start
            
            while current < end:
                date_str = current.strftime("%Y-%m-%d")
                cost = self._get_daily_cost(account_id, date_str)
                if cost is not None and cost > 0:
                    daily_costs.append(cost)
                current += timedelta(days=1)
            
            if len(daily_costs) < 7:  # 至少需要7天数据
                return None
            
            mean_cost = mean(daily_costs)
            std_cost = stdev(daily_costs) if len(daily_costs) > 1 else 0.0
            
            return {
                "mean": mean_cost,
                "std": std_cost,
                "samples": len(daily_costs)
            }
            
        except Exception as e:
            logger.error(f"计算基线失败: {str(e)}")
            return None
    
    def _analyze_root_cause(
        self,
        account_id: str,
        date: str,
        current_cost: float,
        baseline: Dict[str, float]
    ) -> str:
        """分析根因（简化版）"""
        try:
            # 获取当天的账单明细
            billing_cycle = date[:7]
            items = self.bill_storage.get_bill_items(
                account_id=account_id,
                billing_cycle=billing_cycle
            )
            
            # 按产品分类统计
            product_costs = {}
            for item in items:
                item_date = item.get("billing_date", "")
                if item_date == date:
                    product = item.get("product_name", "未知产品")
                    cost = float(item.get("payment_amount", 0) or 0)
                    product_costs[product] = product_costs.get(product, 0) + cost
            
            # 找出成本最高的产品
            if product_costs:
                top_product = max(product_costs.items(), key=lambda x: x[1])
                top_cost = top_product[1]
                top_pct = (top_cost / current_cost) * 100
                
                return f"主要成本来源：{top_product[0]}（¥{top_cost:.2f}，占比{top_pct:.1f}%）"
            
            return "成本异常，但无法确定具体原因"
            
        except Exception as e:
            logger.error(f"分析根因失败: {str(e)}")
            return "无法分析根因"
    
    def _save_anomaly(self, anomaly: Anomaly):
        """保存异常记录到数据库"""
        try:
            # 检查是否已存在
            existing = self.db.query(
                "SELECT id FROM cost_anomalies WHERE id = %s",
                (anomaly.id,)
            )
            
            if existing:
                # 更新
                self.db.execute(
                """UPDATE cost_anomalies 
                   SET current_cost = %s, baseline_cost = %s, deviation_pct = %s, 
                       severity = %s, root_cause = %s, updated_at = NOW()
                   WHERE id = %s""",
                (
                    anomaly.current_cost,
                    anomaly.baseline_cost,
                    anomaly.deviation_pct,
                    anomaly.severity,
                    anomaly.root_cause,
                    anomaly.id
                )
            )
            else:
                # 插入
                self.db.execute(
                """INSERT INTO cost_anomalies 
                   (id, account_id, date, current_cost, baseline_cost, deviation_pct, 
                    severity, root_cause, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                (
                    anomaly.id,
                    anomaly.account_id,
                    anomaly.date,
                    anomaly.current_cost,
                    anomaly.baseline_cost,
                    anomaly.deviation_pct,
                    anomaly.severity,
                    anomaly.root_cause
                )
            )
        except Exception as e:
            logger.error(f"保存异常记录失败: {str(e)}")
    
    def get_anomalies(
        self,
        account_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取异常记录"""
        try:
            query = "SELECT * FROM cost_anomalies WHERE 1=1"
            params = []
            
            if account_id:
                query += " AND account_id = %s"
                params.append(account_id)
            
            if start_date:
                query += " AND date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND date <= %s"
                params.append(end_date)
            
            if severity:
                query += " AND severity = %s"
                params.append(severity)
            
            query += " ORDER BY date DESC, deviation_pct DESC LIMIT %s"
            params.append(limit)
            
            results = self.db.query(query, tuple(params))
            
            return [
                {
                    "id": r["id"],
                    "account_id": r["account_id"],
                    "date": r["date"],
                    "current_cost": float(r["current_cost"]),
                    "baseline_cost": float(r["baseline_cost"]),
                    "deviation_pct": float(r["deviation_pct"]),
                    "severity": r["severity"],
                    "root_cause": r.get("root_cause"),
                    "created_at": r["created_at"].isoformat() if isinstance(r["created_at"], datetime) else r["created_at"]
                }
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"获取异常记录失败: {str(e)}")
            return []
