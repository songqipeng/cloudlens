import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import numpy as np
import json
from pathlib import Path

# Try to import sklearn, handle if missing
try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

class CostPredictor:
    """
    AI成本预测器
    
    使用线性回归算法基于历史数据预测未来成本。
    """
    
    def __init__(self, data_dir: str = "./data/cost"):
        self.data_dir = Path(data_dir)
        self.model = None
        
    def load_history(self) -> List[Dict]:
        """加载历史成本数据"""
        history_file = self.data_dir / "cost_history.json"
        if not history_file.exists():
            return []
            
        try:
            with open(history_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return []

    def train_and_predict(self, days_to_predict: int = 90) -> Dict:
        """
        训练模型并预测
        
        Returns:
            Dict containing forecast data
        """
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn not installed. Run: pip install scikit-learn"}
            
        history = self.load_history()
        if len(history) < 2:
            return {"error": "Insufficient data. Need at least 2 data points (days) for prediction."}
            
        # 准备训练数据
        # X: Days since start (timestamps converted to integers)
        # y: Total Cost
        
        # Sort by date
        history.sort(key=lambda x: x["timestamp"])
        
        start_date = datetime.fromisoformat(history[0]["timestamp"])
        
        dates = []
        costs = []
        
        for record in history:
            dt = datetime.fromisoformat(record["timestamp"])
            days_diff = (dt - start_date).days
            
            # 简单的去重逻辑：如果同一天有多个点，取最后一个(最新的)
            if dates and dates[-1] == days_diff:
                costs[-1] = record["total_cost"]
            else:
                dates.append(days_diff)
                costs.append(record["total_cost"])
                
        if len(dates) < 2:
             return {"error": "Need data from at least 2 different days."}

        X = np.array(dates).reshape(-1, 1)
        y = np.array(costs)
        
        # 训练线性回归模型
        self.model = LinearRegression()
        self.model.fit(X, y)
        
        # 预测未来
        last_day = dates[-1]
        future_days = np.array([last_day + i for i in range(1, days_to_predict + 1)]).reshape(-1, 1)
        future_costs = self.model.predict(future_days)
        
        # 构建返回结果
        forecast_dates = []
        for d in future_days.flatten():
            date_str = (start_date + timedelta(days=int(d))).strftime("%Y-%m-%d")
            forecast_dates.append(date_str)
            
        # 历史数据(用于绘图)
        history_dates_str = [(start_date + timedelta(days=int(d))).strftime("%Y-%m-%d") for d in dates]
        
        # 计算趋势斜率 (每天增加多少钱)
        daily_increase = self.model.coef_[0]
        
        return {
            "model_type": "Linear Regression",
            "daily_increase": round(daily_increase, 2),
            "predicted_total_increase": round(daily_increase * days_to_predict, 2),
            "history": {
                "dates": history_dates_str,
                "costs": [round(c, 2) for c in costs]
            },
            "forecast": {
                "dates": forecast_dates,
                "costs": [round(c, 2) for c in future_costs]
            },
            "confidence_score": self.model.score(X, y) # R^2 score
        }
