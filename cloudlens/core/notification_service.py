#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知服务模块
支持邮件、钉钉、企业微信告警
"""

import os
import logging
import json
from typing import List, Dict, Optional, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务"""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_from = os.getenv("SMTP_FROM", self.smtp_user)
        
        self.dingtalk_webhook = os.getenv("DINGTALK_WEBHOOK_URL")
        self.wechat_webhook = os.getenv("WECHAT_WEBHOOK_URL")
    
    def send_anomaly_alert(
        self,
        anomaly: Dict[str, Any],
        channels: List[str] = None
    ) -> Dict[str, bool]:
        """
        发送异常告警
        
        Args:
            anomaly: 异常数据
            channels: 通知渠道列表（email/dingtalk/wechat），如果为None则使用所有可用渠道
            
        Returns:
            发送结果字典
        """
        if channels is None:
            channels = ["email", "dingtalk", "wechat"]
        
        results = {}
        
        # 构建消息内容
        title = f"成本异常告警 - {anomaly.get('severity', 'unknown').upper()}"
        message = self._build_anomaly_message(anomaly)
        
        # 发送到各个渠道
        if "email" in channels and self.smtp_host:
            results["email"] = self._send_email(
                to=self.smtp_user,  # 默认发送给自己，可以配置
                subject=title,
                content=message
            )
        else:
            results["email"] = False
        
        if "dingtalk" in channels and self.dingtalk_webhook:
            results["dingtalk"] = self._send_dingtalk(title, message)
        else:
            results["dingtalk"] = False
        
        if "wechat" in channels and self.wechat_webhook:
            results["wechat"] = self._send_wechat(title, message)
        else:
            results["wechat"] = False
        
        return results
    
    def _build_anomaly_message(self, anomaly: Dict[str, Any]) -> str:
        """构建异常消息内容"""
        account_id = anomaly.get("account_id", "未知账号")
        date = anomaly.get("date", "未知日期")
        current_cost = anomaly.get("current_cost", 0)
        baseline_cost = anomaly.get("baseline_cost", 0)
        deviation_pct = anomaly.get("deviation_pct", 0)
        severity = anomaly.get("severity", "unknown")
        root_cause = anomaly.get("root_cause", "未分析")
        
        message = f"""
成本异常检测告警

账号: {account_id}
日期: {date}
严重程度: {severity.upper()}

成本情况:
- 当前成本: ¥{current_cost:.2f}
- 基线成本: ¥{baseline_cost:.2f}
- 偏差: {deviation_pct:.1f}%

根因分析:
{root_cause}

请及时查看并处理。
"""
        return message
    
    def _send_email(
        self,
        to: str,
        subject: str,
        content: str
    ) -> bool:
        """发送邮件"""
        try:
            if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
                logger.warning("邮件配置不完整，跳过发送")
                return False
            
            msg = MIMEMultipart()
            msg["From"] = self.smtp_from
            msg["To"] = to
            msg["Subject"] = subject
            
            msg.attach(MIMEText(content, "plain", "utf-8"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"邮件发送成功: {to}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")
            return False
    
    def _send_dingtalk(self, title: str, content: str) -> bool:
        """发送钉钉消息"""
        try:
            if not self.dingtalk_webhook:
                logger.warning("钉钉webhook未配置，跳过发送")
                return False
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"## {title}\n\n{content}"
                }
            }
            
            response = requests.post(
                self.dingtalk_webhook,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info("钉钉消息发送成功")
            return True
            
        except Exception as e:
            logger.error(f"钉钉消息发送失败: {str(e)}")
            return False
    
    def _send_wechat(self, title: str, content: str) -> bool:
        """发送企业微信消息"""
        try:
            if not self.wechat_webhook:
                logger.warning("企业微信webhook未配置，跳过发送")
                return False
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"## {title}\n\n{content}"
                }
            }
            
            response = requests.post(
                self.wechat_webhook,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info("企业微信消息发送成功")
            return True
            
        except Exception as e:
            logger.error(f"企业微信消息发送失败: {str(e)}")
            return False
