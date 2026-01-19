#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预算告警服务
自动检查预算状态并发送告警
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from cloudlens.core.budget_manager import BudgetStorage, Budget, BudgetStatus, BudgetCalculator
from cloudlens.core.bill_storage import BillStorageManager
from cloudlens.core.notification_service import NotificationService

logger = logging.getLogger(__name__)


class BudgetAlertService:
    """预算告警服务"""
    
    def __init__(self):
        self.budget_storage = BudgetStorage()
        self.bill_storage = BillStorageManager()
        self.notification_service = NotificationService()
        self.calculator = BudgetCalculator()
    
    def check_all_budgets(self, account_id: Optional[str] = None) -> List[Dict]:
        """
        检查所有预算并发送告警
        
        Args:
            account_id: 账号ID，如果为None则检查所有账号
            
        Returns:
            触发的告警列表
        """
        try:
            budgets = self.budget_storage.list_budgets(account_id)
            all_alerts = []
            
            for budget in budgets:
                alerts = self.check_budget(budget)
                all_alerts.extend(alerts)
            
            return all_alerts
            
        except Exception as e:
            logger.error(f"检查预算告警失败: {str(e)}")
            return []
    
    def check_budget(self, budget: Budget) -> List[Dict]:
        """
        检查单个预算并发送告警
        
        Returns:
            触发的告警列表
        """
        try:
            # 计算预算状态
            status = self.budget_storage.calculate_budget_status(
                budget,
                budget.account_id,
                self.bill_storage
            )
            
            # 检查告警阈值
            triggered = self.calculator.check_alerts(budget, status)
            
            alerts_sent = []
            for alert in triggered:
                # 检查是否已经发送过告警（避免重复发送）
                if self._should_send_alert(budget.id, alert["threshold"]):
                    # 发送告警
                    result = self._send_budget_alert(budget, status, alert)
                    if result:
                        alerts_sent.append({
                            "budget_id": budget.id,
                            "budget_name": budget.name,
                            "threshold": alert["threshold"],
                            "current_rate": alert["current_rate"],
                            "channels": alert["channels"],
                            "sent_at": datetime.now().isoformat(),
                            "notification_results": result
                        })
                        
                        # 记录已发送的告警
                        self._record_alert_sent(budget.id, alert["threshold"])
            
            return alerts_sent
            
        except Exception as e:
            logger.error(f"检查预算 {budget.id} 告警失败: {str(e)}")
            return []
    
    def _should_send_alert(self, budget_id: str, threshold: float) -> bool:
        """检查是否应该发送告警（避免重复发送）"""
        try:
            # 检查今天是否已经发送过该阈值的告警
            today = datetime.now().strftime("%Y-%m-%d")
            existing = self.budget_storage.db.query(
                """SELECT id FROM budget_alerts 
                   WHERE budget_id = %s AND threshold = %s 
                   AND DATE(triggered_at) = %s 
                   AND status = 'sent'
                   LIMIT 1""",
                (budget_id, threshold, today)
            )
            
            return len(existing) == 0
            
        except Exception as e:
            logger.error(f"检查告警状态失败: {str(e)}")
            return True  # 出错时默认发送
    
    def _send_budget_alert(
        self,
        budget: Budget,
        status: BudgetStatus,
        alert: Dict
    ) -> Dict[str, bool]:
        """发送预算告警"""
        try:
            # 构建消息
            title = f"预算告警 - {budget.name}"
            message = self._build_budget_alert_message(budget, status, alert)
            
            # 获取通知渠道
            channels = alert.get("channels", ["email"])
            if not channels:
                channels = ["email"]  # 默认使用邮件
            
            # 发送通知
            results = {}
            for channel in channels:
                if channel == "email":
                    results["email"] = self.notification_service._send_email(
                        to=self.notification_service.smtp_user,
                        subject=title,
                        content=message
                    )
                elif channel == "dingtalk":
                    results["dingtalk"] = self.notification_service._send_dingtalk(title, message)
                elif channel == "wechat":
                    results["wechat"] = self.notification_service._send_wechat(title, message)
            
            return results
            
        except Exception as e:
            logger.error(f"发送预算告警失败: {str(e)}")
            return {}
    
    def _build_budget_alert_message(
        self,
        budget: Budget,
        status: BudgetStatus,
        alert: Dict
    ) -> str:
        """构建预算告警消息"""
        threshold = alert["threshold"]
        current_rate = alert["current_rate"]
        
        message = f"""
预算告警通知

预算名称: {budget.name}
预算金额: ¥{budget.amount:,.2f}
预算周期: {budget.period}

当前状态:
- 已支出: ¥{status.spent:,.2f}
- 剩余预算: ¥{status.remaining:,.2f}
- 使用率: {current_rate:.1f}%
- 告警阈值: {threshold}%

"""
        
        if status.predicted_spend:
            message += f"预测信息:\n"
            message += f"- 预测总支出: ¥{status.predicted_spend:,.2f}\n"
            if status.predicted_overspend:
                message += f"- 预测超支: ¥{status.predicted_overspend:,.2f}\n"
            message += "\n"
        
        message += "请及时查看并调整预算。"
        
        return message
    
    def _record_alert_sent(self, budget_id: str, threshold: float):
        """记录已发送的告警"""
        try:
            self.budget_storage.db.execute(
                """INSERT INTO budget_alerts 
                   (id, budget_id, threshold, triggered_at, status, message)
                   VALUES (%s, %s, %s, NOW(), 'sent', %s)""",
                (
                    f"{budget_id}-{threshold}-{datetime.now().strftime('%Y%m%d')}",
                    budget_id,
                    threshold,
                    f"预算使用率达到{threshold}%"
                )
            )
        except Exception as e:
            logger.error(f"记录告警失败: {str(e)}")
