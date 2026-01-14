# -*- coding: utf-8 -*-
"""
审计日志模块
记录用户操作、API 调用等关键操作
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# 审计日志目录
AUDIT_LOG_DIR = Path.home() / ".cloudlens" / "audit_logs"
AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)


class AuditAction(str, Enum):
    """审计操作类型"""
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    CREATE_ACCOUNT = "create_account"
    UPDATE_ACCOUNT = "update_account"
    DELETE_ACCOUNT = "delete_account"
    CREATE_BUDGET = "create_budget"
    UPDATE_BUDGET = "update_budget"
    DELETE_BUDGET = "delete_budget"
    CREATE_ALERT = "create_alert"
    UPDATE_ALERT = "update_alert"
    DELETE_ALERT = "delete_alert"
    EXPORT_DATA = "export_data"
    IMPORT_DATA = "import_data"
    API_CALL = "api_call"
    CONFIG_CHANGE = "config_change"
    OTHER = "other"


class AuditResult(str, Enum):
    """操作结果"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, log_dir: Path = AUDIT_LOG_DIR):
        """
        初始化审计日志记录器
        
        Args:
            log_dir: 日志目录
        """
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_log_file(self) -> Path:
        """获取当前日志文件（按日期）"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"audit_{today}.jsonl"
    
    def log_operation(
        self,
        user: str,
        action: AuditAction,
        resource: Optional[str] = None,
        resource_type: Optional[str] = None,
        result: AuditResult = AuditResult.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        记录操作日志
        
        Args:
            user: 用户名
            action: 操作类型
            resource: 资源标识（如资源ID）
            resource_type: 资源类型（如 "account", "budget"）
            result: 操作结果
            details: 详细信息（字典）
            ip_address: IP 地址
            user_agent: User Agent
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user,
            "action": action.value,
            "resource": resource,
            "resource_type": resource_type,
            "result": result.value,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        log_file = self._get_log_file()
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"写入审计日志失败: {e}")
    
    def query_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user: Optional[str] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        result: Optional[AuditResult] = None,
        limit: int = 1000
    ) -> list:
        """
        查询审计日志
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            user: 用户名（过滤）
            action: 操作类型（过滤）
            resource_type: 资源类型（过滤）
            result: 操作结果（过滤）
            limit: 返回数量限制
            
        Returns:
            日志条目列表
        """
        logs = []
        
        # 确定要查询的日期范围
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if end_date is None:
            end_date = datetime.now()
        
        # 遍历日期范围内的所有日志文件
        current_date = start_date
        while current_date <= end_date:
            log_file = self.log_dir / f"audit_{current_date.strftime('%Y-%m-%d')}.jsonl"
            
            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if not line.strip():
                                continue
                            
                            entry = json.loads(line)
                            entry_date = datetime.fromisoformat(entry["timestamp"])
                            
                            # 日期过滤
                            if entry_date < start_date or entry_date > end_date:
                                continue
                            
                            # 其他过滤条件
                            if user and entry.get("user") != user:
                                continue
                            if action and entry.get("action") != action.value:
                                continue
                            if resource_type and entry.get("resource_type") != resource_type:
                                continue
                            if result and entry.get("result") != result.value:
                                continue
                            
                            logs.append(entry)
                            
                            if len(logs) >= limit:
                                break
                except Exception as e:
                    logger.warning(f"读取日志文件失败 {log_file}: {e}")
            
            # 移动到下一天
            from datetime import timedelta
            current_date += timedelta(days=1)
            
            if len(logs) >= limit:
                break
        
        # 按时间倒序排序
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return logs[:limit]
    
    def cleanup_old_logs(self, days: int = 90):
        """
        清理旧日志（保留指定天数）
        
        Args:
            days: 保留天数
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for log_file in self.log_dir.glob("audit_*.jsonl"):
            try:
                # 从文件名提取日期
                date_str = log_file.stem.replace("audit_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    logger.info(f"已删除旧日志文件: {log_file}")
            except Exception as e:
                logger.warning(f"处理日志文件失败 {log_file}: {e}")


# 全局实例
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """获取审计日志记录器实例（单例）"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger

