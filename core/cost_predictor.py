"""
AI成本预测器
使用机器学习模型预测未来成本趋势
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# 可选依赖: 如果未安装会降级到简单预测
try:
    import pandas as pd
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("Prophet not available, using simple prediction")


class CostPredictor:
    """AI成本预测器"""

    def __init__(self, data_dir: str = "./data/cost"):
        self.data_dir = Path(data_dir)
        self.cost_history_file = self.data_dir / "cost_history.json"
        self.model = None
        self.model_trained = False

    def load_historical_data(self, account_name: str, min_days: int = 30) -> Optional[pd.DataFrame]:
        """
        加载历史成本数据
        
        Returns:
            DataFrame with columns: ds (date), y (cost)
        """
        if not self.cost_history_file.exists():
            logger.warning("No cost history file found")
            return None

        with open(self.cost_history_file, "r") as f:
            all_history = json.load(f)

        # 筛选账号
        account_history = [h for h in all_history if h.get("account") == account_name]

        if len(account_history) < min_days:
            logger.warning(f"Insufficient data: {len(account_history)} days (need {min_days})")
            return None

        if not PROPHET_AVAILABLE:
            # 返回字典格式
            return account_history

        # 转换为DataFrame
        df = pd.DataFrame(account_history)
        df["ds"] = pd.to_datetime(df["timestamp"])
        df["y"] = df["total_cost"]
        df = df[["ds", "y"]].sort_values("ds")

        return df

    def train(self, account_name: str) -> bool:
        """
        训练预测模型
        
        Returns:
            是否训练成功
        """
        df = self.load_historical_data(account_name)

        if df is None:
            return False

        if not PROPHET_AVAILABLE:
            # 简单模型: 使用线性增长
            logger.info("Using simple linear prediction model")
            self.model = self._train_simple_model(df)
            self.model_trained = True
            return True

        try:
            # 使用Prophet训练
            model = Prophet(
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=False,  # 数据不够一年
                changepoint_prior_scale=0.05,  # 减少过拟合
            )

            model.fit(df)
            self.model = model
            self.model_trained = True
            logger.info("Prophet model trained successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to train model: {e}")
            return False

    def _train_simple_model(self, history: List[Dict]) -> Dict:
        """简单线性模型"""
        # 计算平均增长率
        if len(history) < 2:
            return {"type": "simple", "avg_cost": history[0]["total_cost"], "growth_rate": 0}

        costs = [h["total_cost"] for h in history]
        dates = [datetime.fromisoformat(h["timestamp"]) for h in history]

        # 简单线性回归
        x = [(d - dates[0]).days for d in dates]
        y = costs

        # 计算斜率
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if n * sum_x2 != sum_x ** 2 else 0
        intercept = (sum_y - slope * sum_x) / n

        return {
            "type": "simple",
            "slope": slope,
            "intercept": intercept,
            "avg_cost": sum_y / n,
        }

    def predict(self, days: int = 90, confidence_interval: float = 0.95) -> Optional[Dict]:
        """
        预测未来成本
        
        Args:
            days: 预测天数
            confidence_interval: 置信区间
            
        Returns:
            预测结果
        """
        if not self.model_trained or self.model is None:
            logger.warning("Model not trained")
            return None

        if not PROPHET_AVAILABLE or self.model.get("type") == "simple":
            # 简单预测
            return self._predict_simple(days)

        try:
            # Prophet预测
            future = self.model.make_future_dataframe(periods=days)
            forecast = self.model.predict(future)

            # 提取预测值
            predictions = forecast.tail(days)

            result = {
                "model": "prophet",
                "forecast_days": days,
                "predictions": predictions[["ds", "yhat", "yhat_lower", "yhat_upper"]].to_dict("records"),
                "total_cost": predictions["yhat"].sum(),
                "avg_daily_cost": predictions["yhat"].mean(),
                "confidence_interval": confidence_interval,
            }

            return result

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return None

    def _predict_simple(self, days: int) -> Dict:
        """简单线性预测"""
        model = self.model
        predictions = []

        for i in range(days):
            if model["type"] == "simple":
                # 线性增长
                future_day = i + 1
                predicted_cost = model["intercept"] + model["slope"] * future_day
                predictions.append({
                    "day": future_day,
                    "predicted_cost": max(0, predicted_cost),  # 成本不能为负
                })
            else:
                # 常量
                predictions.append({
                    "day": i + 1,
                    "predicted_cost": model["avg_cost"],
                })

        total_cost = sum(p["predicted_cost"] for p in predictions)
        avg_cost = total_cost / days

        return {
            "model": "simple",
            "forecast_days": days,
            "total_cost": round(total_cost, 2),
            "avg_daily_cost": round(avg_cost, 2),
            "predictions": predictions,
        }

    def calculate_accuracy(self, account_name: str, test_days: int = 7) -> Optional[Dict]:
        """
        计算模型准确度
        
        使用最后N天数据作为测试集
        """
        df = self.load_historical_data(account_name, min_days=test_days + 30)

        if df is None:
            return None

        if not PROPHET_AVAILABLE:
            # 简单模型不支持准确度计算
            return {"error": "Prophet required for accuracy calculation"}

        # 分割训练集和测试集
        train_df = df[:-test_days]
        test_df = df[-test_days:]

        # 训练模型
        model = Prophet()
        model.fit(train_df)

        # 预测测试集
        forecast = model.predict(test_df[["ds"]])

        # 计算MAPE (Mean Absolute Percentage Error)
        actual = test_df["y"].values
        predicted = forecast["yhat"].values

        mape = sum(abs((a - p) / a) for a, p in zip(actual, predicted) if a != 0) / len(actual) * 100

        return {
            "test_days": test_days,
            "mape": round(mape, 2),
            "accuracy": round(100 - mape, 2),
            "rmse": round(((sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual)) ** 0.5), 2),
        }

    def generate_forecast_report(
        self, account_name: str, days: int = 90
    ) -> Optional[Dict]:
        """
        生成完整的预测报告
        """
        # 训练模型
        if not self.train(account_name):
            return {"error": "Failed to train model - insufficient data"}

        # 预测
        forecast = self.predict(days)

        if forecast is None:
            return {"error": "Prediction failed"}

        # 加载历史数据用于对比
        df = self.load_historical_data(account_name)

        if df is None:
            historical_avg = 0
        elif PROPHET_AVAILABLE:
            historical_avg = df["y"].mean()
        else:
            historical_avg = sum(h["total_cost"] for h in df) / len(df)

        # 计算增长
        if "avg_daily_cost" in forecast:
            growth_rate = (
                (forecast["avg_daily_cost"] - historical_avg) / historical_avg * 100
                if historical_avg > 0
                else 0
            )
        else:
            growth_rate = 0

        report = {
            "account": account_name,
            "forecast_period": f"{days} days",
            "model_type": forecast.get("model", "simple"),
            "predicted_total_cost": forecast.get("total_cost", 0),
            "predicted_avg_daily_cost": forecast.get("avg_daily_cost", 0),
            "historical_avg_cost": round(historical_avg, 2),
            "growth_rate": round(growth_rate, 2),
            "forecast_data": forecast.get("predictions", []),
        }

        return report
