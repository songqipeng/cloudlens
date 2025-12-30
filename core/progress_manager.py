# -*- coding: utf-8 -*-
"""
进度管理器 - 用于存储和获取任务进度
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


class ProgressManager:
    """进度管理器（线程安全）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ProgressManager, cls).__new__(cls)
                    cls._instance._progress_store: Dict[str, Dict] = {}
                    cls._instance._store_lock = threading.Lock()
        return cls._instance
    
    def set_progress(
        self, 
        task_id: str, 
        current: int, 
        total: int, 
        message: str = "",
        stage: str = ""
    ):
        """
        设置任务进度
        
        Args:
            task_id: 任务ID（通常是 account_name）
            current: 当前进度
            total: 总进度
            message: 进度消息
            stage: 当前阶段（如 "checking_regions", "querying_instances", "analyzing"）
        """
        with self._store_lock:
            self._progress_store[task_id] = {
                "current": current,
                "total": total,
                "percent": (current / total * 100) if total > 0 else 0,
                "message": message,
                "stage": stage,
                "updated_at": datetime.now().isoformat(),
                "status": "running"
            }
            logger.debug(f"进度更新 [{task_id}]: {current}/{total} ({self._progress_store[task_id]['percent']:.1f}%) - {message}")
    
    def get_progress(self, task_id: str) -> Optional[Dict]:
        """
        获取任务进度
        
        Args:
            task_id: 任务ID
            
        Returns:
            进度信息字典，如果任务不存在则返回 None
        """
        with self._store_lock:
            return self._progress_store.get(task_id)
    
    def set_completed(self, task_id: str, result: Optional[Dict] = None):
        """
        标记任务完成
        
        Args:
            task_id: 任务ID
            result: 任务结果（可选）
        """
        with self._store_lock:
            if task_id in self._progress_store:
                self._progress_store[task_id].update({
                    "status": "completed",
                    "current": self._progress_store[task_id].get("total", 0),
                    "percent": 100,
                    "result": result,
                    "updated_at": datetime.now().isoformat()
                })
                logger.info(f"任务完成 [{task_id}]")
    
    def set_failed(self, task_id: str, error: str):
        """
        标记任务失败
        
        Args:
            task_id: 任务ID
            error: 错误信息
        """
        with self._store_lock:
            if task_id in self._progress_store:
                self._progress_store[task_id].update({
                    "status": "failed",
                    "error": error,
                    "updated_at": datetime.now().isoformat()
                })
                logger.error(f"任务失败 [{task_id}]: {error}")
    
    def clear_progress(self, task_id: str):
        """
        清除任务进度（任务完成后可以清除）
        
        Args:
            task_id: 任务ID
        """
        with self._store_lock:
            if task_id in self._progress_store:
                del self._progress_store[task_id]
                logger.debug(f"清除进度 [{task_id}]")
    
    def cleanup_old_progress(self, max_age_minutes: int = 60):
        """
        清理过期的进度记录
        
        Args:
            max_age_minutes: 最大保留时间（分钟）
        """
        with self._store_lock:
            now = datetime.now()
            expired_tasks = []
            
            for task_id, progress in self._progress_store.items():
                updated_at = datetime.fromisoformat(progress.get("updated_at", now.isoformat()))
                age = now - updated_at
                
                # 清理已完成或失败的任务，且超过最大保留时间
                if progress.get("status") in ("completed", "failed") and age > timedelta(minutes=max_age_minutes):
                    expired_tasks.append(task_id)
            
            for task_id in expired_tasks:
                del self._progress_store[task_id]
                logger.debug(f"清理过期进度 [{task_id}]")


