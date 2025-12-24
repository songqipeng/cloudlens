#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成本预测模块
基于历史成本数据预测未来成本趋势
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np

from core.database import DatabaseFactory
from utils.logger import get_logger


class CostPredictor:
    """成本预测器"""

    def __init__(self, db_name="cost_data.db", db_type: str = None):
        self.db_name = db_name
        self.db_type = db_type or os.getenv("DB_TYPE", "mysql").lower()
        self.logger = get_logger("cost_predictor")
        
        if self.db_type == "mysql":
            self.db = DatabaseFactory.create_adapter("mysql")
        else:
            self.db = DatabaseFactory.create_adapter("sqlite", db_path=db_name)
        
        self.init_database()

    def _get_placeholder(self):
        """获取SQL占位符"""
        return "%s" if self.db_type == "mysql" else "?"

    def init_database(self):
        """初始化数据库"""
        placeholder = self._get_placeholder()
        
        if self.db_type == "mysql":
            # MySQL表结构
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tenant_name VARCHAR(100) NOT NULL,
                    date VARCHAR(20) NOT NULL,
                    total_cost DECIMAL(10,2) DEFAULT 0,
                    compute_cost DECIMAL(10,2) DEFAULT 0,
                    storage_cost DECIMAL(10,2) DEFAULT 0,
                    network_cost DECIMAL(10,2) DEFAULT 0,
                    database_cost DECIMAL(10,2) DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_tenant_date (tenant_name, date)
                )
                """
            )

            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_predictions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tenant_name VARCHAR(100) NOT NULL,
                    prediction_date VARCHAR(20) NOT NULL,
                    predicted_cost DECIMAL(10,2) DEFAULT 0,
                    confidence_level DECIMAL(5,2) DEFAULT 0,
                    prediction_method VARCHAR(50),
                    prediction_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_tenant_date_method (tenant_name, prediction_date, prediction_method)
                )
                """
            )

            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS budgets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tenant_name VARCHAR(100) NOT NULL,
                    budget_type VARCHAR(50) NOT NULL,
                    budget_amount DECIMAL(10,2) NOT NULL,
                    start_date VARCHAR(20) NOT NULL,
                    end_date VARCHAR(20) NOT NULL,
                    alert_threshold DECIMAL(5,2) DEFAULT 0.8,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_tenant_type_start (tenant_name, budget_type, start_date)
                )
                """
            )

            # 创建索引
            try:
                self.db.execute(
                    "CREATE INDEX idx_cost_history_tenant_date ON cost_history(tenant_name, date)"
                )
            except Exception as e:
                # 索引可能已存在，这是正常的
                logger.debug(f"Index idx_cost_history_tenant_date may already exist: {e}")

            try:
                self.db.execute(
                    "CREATE INDEX idx_predictions_tenant_date ON cost_predictions(tenant_name, prediction_date)"
                )
            except Exception as e:
                logger.debug(f"Index idx_predictions_tenant_date may already exist: {e}")
        else:
            # SQLite表结构
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    total_cost REAL DEFAULT 0,
                    compute_cost REAL DEFAULT 0,
                    storage_cost REAL DEFAULT 0,
                    network_cost REAL DEFAULT 0,
                    database_cost REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_name, date)
                )
                """
            )

            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_name TEXT NOT NULL,
                    prediction_date TEXT NOT NULL,
                    predicted_cost REAL DEFAULT 0,
                    confidence_level REAL DEFAULT 0,
                    prediction_method TEXT,
                    prediction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_name, prediction_date, prediction_method)
                )
                """
            )

            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_name TEXT NOT NULL,
                    budget_type TEXT NOT NULL,
                    budget_amount REAL NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    alert_threshold REAL DEFAULT 0.8,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_name, budget_type, start_date)
                )
                """
            )

            # 创建索引
            self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_cost_history_tenant_date ON cost_history(tenant_name, date)"
            )
            self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_predictions_tenant_date ON cost_predictions(tenant_name, prediction_date)"
            )

        self.logger.info("成本预测数据库初始化完成")

    def collect_historical_cost(
        self, tenant_name: str, access_key_id: str, access_key_secret: str, days: int = 90
    ):
        """收集历史成本数据"""
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkcore.request import CommonRequest

            self.logger.info(f"开始收集 {tenant_name} 的成本数据 (最近{days}天)")

            client = AcsClient(access_key_id, access_key_secret, "cn-hangzhou")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 按月收集数据
            current_date = start_date
            cost_records = []

            while current_date <= end_date:
                billing_cycle = current_date.strftime("%Y-%m")
                
                try:
                    request = CommonRequest()
                    request.set_domain("business.aliyuncs.com")
                    request.set_method("POST")
                    request.set_version("2017-12-14")
                    request.set_action_name("QueryBill")
                    request.add_query_param("BillingCycle", billing_cycle)
                    request.add_query_param("Type", "SubscriptionOrder")

                    response = client.do_action_with_exception(request)
                    data = json.loads(response)

                    if data.get("Success"):
                        items = data.get("Data", {}).get("Items", {}).get("Item", [])
                        
                        # 按天聚合成本
                        daily_costs = {}
                        for item in items:
                            usage_date = item.get("UsageStartTime", "")[:10]
                            cost = float(item.get("PretaxAmount", 0))
                            product_code = item.get("ProductCode", "")
                            
                            if usage_date not in daily_costs:
                                daily_costs[usage_date] = {
                                    "total": 0,
                                    "compute": 0,
                                    "storage": 0,
                                    "network": 0,
                                    "database": 0,
                                }
                            
                            daily_costs[usage_date]["total"] += cost
                            
                            # 按产品分类
                            if product_code in ["ecs", "eci"]:
                                daily_costs[usage_date]["compute"] += cost
                            elif product_code in ["oss", "nas", "disk"]:
                                daily_costs[usage_date]["storage"] += cost
                            elif product_code in ["slb", "eip", "nat", "vpn"]:
                                daily_costs[usage_date]["network"] += cost
                            elif product_code in ["rds", "redis", "mongodb", "polardb"]:
                                daily_costs[usage_date]["database"] += cost

                        cost_records.extend([
                            {
                                "date": date,
                                "total_cost": costs["total"],
                                "compute_cost": costs["compute"],
                                "storage_cost": costs["storage"],
                                "network_cost": costs["network"],
                                "database_cost": costs["database"],
                            }
                            for date, costs in daily_costs.items()
                        ])

                except Exception as e:
                    self.logger.warning(f"获取 {billing_cycle} 账单失败: {e}")

                # 移动到下个月
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

            # 保存到数据库
            if cost_records:
                self.save_cost_history(tenant_name, cost_records)
                self.logger.info(f"成功收集 {len(cost_records)} 条成本记录")
            else:
                self.logger.warning("未获取到成本数据")

            return cost_records

        except Exception as e:
            self.logger.error(f"收集成本数据失败: {e}")
            return []

    def save_cost_history(self, tenant_name: str, cost_records: List[Dict]):
        """保存成本历史数据"""
        placeholder = self._get_placeholder()
        
        if self.db_type == "mysql":
            sql = f"""
                REPLACE INTO cost_history 
                (tenant_name, date, total_cost, compute_cost, storage_cost, network_cost, database_cost)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """
        else:
            sql = f"""
                INSERT OR REPLACE INTO cost_history 
                (tenant_name, date, total_cost, compute_cost, storage_cost, network_cost, database_cost)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """
        
        for record in cost_records:
            self.db.execute(
                sql,
                (
                    tenant_name,
                    record["date"],
                    record["total_cost"],
                    record["compute_cost"],
                    record["storage_cost"],
                    record["network_cost"],
                    record["database_cost"],
                ),
            )

    def get_historical_cost(self, tenant_name: str, days: int = 90) -> List[Dict]:
        """获取历史成本数据"""
        placeholder = self._get_placeholder()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        rows = self.db.query(
            f"""
            SELECT date, total_cost, compute_cost, storage_cost, network_cost, database_cost
            FROM cost_history
            WHERE tenant_name = {placeholder} AND date >= {placeholder} AND date <= {placeholder}
            ORDER BY date
        """,
            (tenant_name, start_date, end_date),
        )

        return [
            {
                "date": row.get("date") if isinstance(row, dict) else row[0],
                "total_cost": row.get("total_cost") if isinstance(row, dict) else row[1],
                "compute_cost": row.get("compute_cost") if isinstance(row, dict) else row[2],
                "storage_cost": row.get("storage_cost") if isinstance(row, dict) else row[3],
                "network_cost": row.get("network_cost") if isinstance(row, dict) else row[4],
                "database_cost": row.get("database_cost") if isinstance(row, dict) else row[5],
            }
            for row in rows
        ]

    def predict_cost_linear(self, tenant_name: str, future_days: int = 30) -> List[Dict]:
        """使用线性回归预测成本"""
        try:
            historical_data = self.get_historical_cost(tenant_name, days=90)

            if len(historical_data) < 7:
                self.logger.warning("历史数据不足,无法预测")
                return []

            # 提取时间序列
            dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in historical_data]
            costs = np.array([d["total_cost"] for d in historical_data])

            # 转换为数值(天数)
            base_date = dates[0]
            x = np.array([(d - base_date).days for d in dates])

            # 线性回归
            coefficients = np.polyfit(x, costs, 1)
            slope, intercept = coefficients

            # 预测未来
            predictions = []
            last_date = dates[-1]

            for i in range(1, future_days + 1):
                future_date = last_date + timedelta(days=i)
                x_future = (future_date - base_date).days
                predicted_cost = slope * x_future + intercept

                # 确保预测值非负
                predicted_cost = max(0, predicted_cost)

                predictions.append(
                    {
                        "date": future_date.strftime("%Y-%m-%d"),
                        "predicted_cost": round(predicted_cost, 2),
                        "confidence_level": 0.7,  # 简单模型,置信度中等
                        "method": "linear_regression",
                    }
                )

            # 保存预测结果
            self.save_predictions(tenant_name, predictions)

            return predictions

        except Exception as e:
            self.logger.error(f"预测失败: {e}")
            return []

    def predict_cost_moving_average(
        self, tenant_name: str, future_days: int = 30, window: int = 7
    ) -> List[Dict]:
        """使用移动平均法预测成本"""
        try:
            historical_data = self.get_historical_cost(tenant_name, days=90)

            if len(historical_data) < window:
                self.logger.warning("历史数据不足")
                return []

            # 计算移动平均
            costs = [d["total_cost"] for d in historical_data]
            recent_avg = np.mean(costs[-window:])

            # 预测(假设未来保持平均水平)
            predictions = []
            last_date = datetime.strptime(historical_data[-1]["date"], "%Y-%m-%d")

            for i in range(1, future_days + 1):
                future_date = last_date + timedelta(days=i)
                predictions.append(
                    {
                        "date": future_date.strftime("%Y-%m-%d"),
                        "predicted_cost": round(recent_avg, 2),
                        "confidence_level": 0.6,
                        "method": "moving_average",
                    }
                )

            self.save_predictions(tenant_name, predictions)
            return predictions

        except Exception as e:
            self.logger.error(f"移动平均预测失败: {e}")
            return []

    def save_predictions(self, tenant_name: str, predictions: List[Dict]):
        """保存预测结果"""
        placeholder = self._get_placeholder()
        
        if self.db_type == "mysql":
            sql = f"""
                REPLACE INTO cost_predictions
                (tenant_name, prediction_date, predicted_cost, confidence_level, prediction_method)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """
        else:
            sql = f"""
                INSERT OR REPLACE INTO cost_predictions
                (tenant_name, prediction_date, predicted_cost, confidence_level, prediction_method)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """
        
        for pred in predictions:
            self.db.execute(
                sql,
                (
                    tenant_name,
                    pred["date"],
                    pred["predicted_cost"],
                    pred["confidence_level"],
                    pred["method"],
                ),
            )

    def set_budget(
        self,
        tenant_name: str,
        budget_type: str,
        amount: float,
        start_date: str,
        end_date: str,
        alert_threshold: float = 0.8,
    ):
        """设置预算"""
        placeholder = self._get_placeholder()
        
        if self.db_type == "mysql":
            sql = f"""
                REPLACE INTO budgets
                (tenant_name, budget_type, budget_amount, start_date, end_date, alert_threshold)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """
        else:
            sql = f"""
                INSERT OR REPLACE INTO budgets
                (tenant_name, budget_type, budget_amount, start_date, end_date, alert_threshold)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """
        
        self.db.execute(
            sql,
            (tenant_name, budget_type, amount, start_date, end_date, alert_threshold),
        )
        self.logger.info(f"预算设置成功: {tenant_name} {budget_type} ¥{amount}")

    def check_budget_usage(self, tenant_name: str) -> List[Dict]:
        """检查预算使用情况"""
        placeholder = self._get_placeholder()
        current_date = datetime.now().strftime("%Y-%m-%d")

        budgets = self.db.query(
            f"""
            SELECT budget_type, budget_amount, start_date, end_date, alert_threshold
            FROM budgets
            WHERE tenant_name = {placeholder} AND start_date <= {placeholder} AND end_date >= {placeholder}
        """,
            (tenant_name, current_date, current_date),
        )

        results = []

        for budget in budgets:
            budget_type = budget.get("budget_type") if isinstance(budget, dict) else budget[0]
            amount = budget.get("budget_amount") if isinstance(budget, dict) else budget[1]
            start_date = budget.get("start_date") if isinstance(budget, dict) else budget[2]
            end_date = budget.get("end_date") if isinstance(budget, dict) else budget[3]
            threshold = budget.get("alert_threshold") if isinstance(budget, dict) else budget[4]

            # 计算实际花费
            cost_result = self.db.query_one(
                f"""
                SELECT SUM(total_cost) as total FROM cost_history
                WHERE tenant_name = {placeholder} AND date >= {placeholder} AND date <= {placeholder}
            """,
                (tenant_name, start_date, end_date),
            )

            actual_cost = cost_result.get("total", 0) if cost_result else 0
            usage_rate = (actual_cost / amount) * 100 if amount > 0 else 0

            results.append(
                {
                    "budget_type": budget_type,
                    "budget_amount": amount,
                    "actual_cost": actual_cost,
                    "usage_rate": usage_rate,
                    "alert_threshold": threshold * 100,
                    "exceeds_threshold": usage_rate >= (threshold * 100),
                }
            )

        return results

    def generate_prediction_report(self, tenant_name: str, output_file: str):
        """生成预测报告"""
        try:
            import pandas as pd

            # 获取历史数据
            historical = self.get_historical_cost(tenant_name, days=90)

            # 获取预测数据
            placeholder = self._get_placeholder()
            predictions_data = self.db.query(
                f"""
                SELECT prediction_date, predicted_cost, confidence_level, prediction_method
                FROM cost_predictions
                WHERE tenant_name = {placeholder}
                ORDER BY prediction_date
            """,
                (tenant_name,),
            )
            predictions = pd.DataFrame(predictions_data)

            # 生成Excel报告
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                # 历史数据
                if historical:
                    hist_df = pd.DataFrame(historical)
                    hist_df.to_excel(writer, sheet_name="历史成本", index=False)

                # 预测数据
                if not predictions.empty:
                    predictions.to_excel(writer, sheet_name="成本预测", index=False)

                # 预算使用情况
                budget_usage = self.check_budget_usage(tenant_name)
                if budget_usage:
                    budget_df = pd.DataFrame(budget_usage)
                    budget_df.to_excel(writer, sheet_name="预算使用", index=False)

            self.logger.info(f"预测报告已生成: {output_file}")

        except ImportError:
            self.logger.warning("pandas未安装,跳过Excel报告")
        except Exception as e:
            self.logger.error(f"生成报告失败: {e}")


if __name__ == "__main__":
    # 测试代码
    predictor = CostPredictor()
    print("成本预测模块初始化完成")
