#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试预算告警邮件发送功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import json
import logging
from datetime import datetime
from core.notification_service import NotificationService
from core.alert_manager import Alert, AlertRule, AlertSeverity

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_budget_alert_email():
    """测试预算告警邮件发送"""
    
    # 加载通知配置
    config_file = Path.home() / ".cloudlens" / "notifications.json"
    
    if not config_file.exists():
        print("❌ 通知配置文件不存在: ~/.cloudlens/notifications.json")
        return False
    
    with open(config_file, "r", encoding="utf-8") as f:
        notification_config = json.load(f)
    
    print("📧 测试预算告警邮件发送")
    print(f"配置邮箱: {notification_config.get('email')}")
    print(f"接收邮箱: {notification_config.get('default_receiver_email') or notification_config.get('email')}")
    print(f"SMTP服务器: {notification_config.get('smtp_host')}")
    print(f"SMTP端口: {notification_config.get('smtp_port')}")
    
    # 检查密码配置
    smtp_password = notification_config.get("smtp_password") or notification_config.get("auth_code")
    if not smtp_password:
        print("❌ 错误：未配置 SMTP 密码")
        return False
    
    if "Console Error" in str(smtp_password) or "API Error" in str(smtp_password):
        print("❌ 错误：SMTP 密码配置错误，包含错误信息字符串")
        print("   请重新配置正确的 SMTP 密码（QQ邮箱需要使用授权码）")
        return False
    
    # 初始化通知服务
    smtp_config = {
        "smtp_host": notification_config.get("smtp_host", "smtp.qq.com"),
        "smtp_port": notification_config.get("smtp_port", 587),
        "smtp_user": notification_config.get("smtp_user") or notification_config.get("email"),
        "smtp_password": smtp_password,
        "smtp_from": notification_config.get("smtp_from") or notification_config.get("email")
    }
    
    if not smtp_config.get("smtp_user") or not smtp_config.get("smtp_password"):
        print("❌ 错误：SMTP 配置不完整")
        return False
    
    try:
        notification_service = NotificationService(smtp_config)
        
        # 获取接收邮箱
        receiver_email = notification_config.get("default_receiver_email") or notification_config.get("email")
        if not receiver_email:
            print("❌ 错误：未配置接收邮箱")
            return False
        
        # 创建测试告警
        alert = Alert(
            id="test-budget-alert",
            rule_id="test-budget-rule",
            rule_name="预算告警测试",
            severity=AlertSeverity.ERROR.value,
            status="triggered",
            title="预算告警测试: 12月预算 使用率已达 100.00%",
            message="预算 '12月预算' 的使用率已达到 100.00%，超过告警阈值 90%。\n\n"
                   "预算金额: ¥50,000.00\n"
                   "已支出: ¥111,745.51\n"
                   "剩余预算: ¥0.00\n"
                   "使用率: 100.00%\n"
                   "预测支出: ¥150,613.51\n"
                   "预测超支: ¥100,613.51",
            metric_value=100.0,
            threshold=90.0,
            account_id="test-account",
            triggered_at=datetime.now()
        )
        
        # 创建测试规则
        rule = AlertRule(
            id="test-budget-rule",
            name="预算告警测试",
            description="预算告警测试规则",
            type="budget_overspend",
            severity=AlertSeverity.ERROR.value,
            enabled=True,
            notify_email=receiver_email
        )
        
        print(f"\n📤 正在发送测试邮件到: {receiver_email}")
        
        # 发送邮件
        success = notification_service.send_email(alert, rule, receiver_email)
        
        if success:
            print("✅ 邮件发送成功！")
            print(f"   请检查邮箱 {receiver_email} 的收件箱（包括垃圾邮件文件夹）")
            return True
        else:
            print("❌ 邮件发送失败")
            return False
            
    except Exception as e:
        print(f"❌ 发送邮件时出错: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_budget_alert_email()
    sys.exit(0 if success else 1)

