"""
通知服务

负责发送告警通知（邮件、Webhook、短信等）
"""

import logging
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List
from datetime import datetime
import requests
from core.alert_manager import Alert, AlertRule

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.smtp_host = self.config.get("smtp_host", "smtp.gmail.com")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.smtp_user = self.config.get("smtp_user")
        self.smtp_password = self.config.get("smtp_password")
        self.smtp_from = self.config.get("smtp_from", self.smtp_user)
    
    def send_alert_notification(self, alert: Alert, rule: AlertRule) -> bool:
        """发送告警通知"""
        success = True
        
        # 邮件通知
        if rule.notify_email:
            try:
                self.send_email(alert, rule, rule.notify_email)
            except Exception as e:
                logger.error(f"Failed to send email notification: {e}")
                success = False
        
        # Webhook通知
        if rule.notify_webhook:
            try:
                self.send_webhook(alert, rule, rule.notify_webhook)
            except Exception as e:
                logger.error(f"Failed to send webhook notification: {e}")
                success = False
        
        # 短信通知（可选）
        if rule.notify_sms:
            try:
                self.send_sms(alert, rule, rule.notify_sms)
            except Exception as e:
                logger.error(f"Failed to send SMS notification: {e}")
                success = False
        
        return success
    
    def send_email(self, alert: Alert, rule: AlertRule, to_email: str) -> bool:
        """发送邮件通知"""
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured, skipping email notification")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            # 修复编码问题：使用 Header 处理中文主题
            from email.header import Header
            msg['Subject'] = Header(f"[{alert.severity.upper()}] {alert.title}", 'utf-8')
            msg['From'] = self.smtp_from
            msg['To'] = to_email
            
            # 邮件正文
            html_body = self._generate_email_html(alert, rule)
            text_body = self._generate_email_text(alert, rule)
            
            # 修复编码问题：明确指定字符编码
            msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            # 发送邮件
            # 根据端口判断使用SSL还是TLS
            if self.smtp_port == 465:
                # 使用SSL
                import ssl
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                # 使用TLS（默认）
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            
            logger.info(f"Email notification sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_webhook(self, alert: Alert, rule: AlertRule, webhook_url: str) -> bool:
        """发送Webhook通知"""
        try:
            payload = {
                "alert_id": alert.id,
                "rule_id": rule.id,
                "rule_name": rule.name,
                "severity": alert.severity,
                "status": alert.status,
                "title": alert.title,
                "message": alert.message,
                "metric_value": alert.metric_value,
                "threshold": alert.threshold,
                "account_id": alert.account_id,
                "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
                "resource_id": alert.resource_id,
                "resource_type": alert.resource_type
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            response.raise_for_status()
            logger.info(f"Webhook notification sent to {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            return False
    
    def send_sms(self, alert: Alert, rule: AlertRule, phone_number: str) -> bool:
        """发送短信通知（需要第三方服务）"""
        # TODO: 集成短信服务（如阿里云短信、腾讯云短信等）
        logger.warning("SMS notification not implemented yet")
        return False
    
    def _generate_email_text(self, alert: Alert, rule: AlertRule) -> str:
        """生成邮件文本内容"""
        return f"""
告警通知

规则名称: {rule.name}
告警标题: {alert.title}
严重程度: {alert.severity.upper()}
状态: {alert.status}

{alert.message}

详细信息:
- 指标值: {alert.metric_value}
- 阈值: {alert.threshold}
- 账号ID: {alert.account_id}
- 触发时间: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S') if alert.triggered_at else 'N/A'}

请及时处理此告警。
"""
    
    def _generate_email_html(self, alert: Alert, rule: AlertRule) -> str:
        """生成邮件HTML内容"""
        severity_color = {
            "info": "#3b82f6",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "critical": "#dc2626"
        }.get(alert.severity, "#6b7280")
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {severity_color}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
        .info-row {{ margin: 10px 0; }}
        .label {{ font-weight: bold; color: #6b7280; }}
        .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>{alert.title}</h2>
        </div>
        <div class="content">
            <div class="info-row">
                <span class="label">规则名称:</span> {rule.name}
            </div>
            <div class="info-row">
                <span class="label">严重程度:</span> <span style="color: {severity_color}; font-weight: bold;">{alert.severity.upper()}</span>
            </div>
            <div class="info-row">
                <span class="label">状态:</span> {alert.status}
            </div>
            <div class="info-row">
                <span class="label">告警信息:</span>
                <p>{alert.message}</p>
            </div>
            <div class="info-row">
                <span class="label">指标值:</span> {alert.metric_value}
            </div>
            <div class="info-row">
                <span class="label">阈值:</span> {alert.threshold}
            </div>
            <div class="info-row">
                <span class="label">账号ID:</span> {alert.account_id or 'N/A'}
            </div>
            <div class="info-row">
                <span class="label">触发时间:</span> {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S') if alert.triggered_at else 'N/A'}
            </div>
        </div>
        <div class="footer">
            <p>此邮件由 CloudLens 告警系统自动发送，请勿回复。</p>
        </div>
    </div>
</body>
</html>
"""







