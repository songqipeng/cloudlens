# -*- coding: utf-8 -*-
"""
数据备份 API 端点
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

from cloudlens.core.backup_manager import get_backup_manager
from web.backend.auth_middleware import require_admin
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backup", tags=["backup"])
limiter = Limiter(key_func=get_remote_address)


class BackupRequest(BaseModel):
    """备份请求"""
    backup_name: Optional[str] = None
    include_database: bool = True
    include_files: bool = True


class RestoreRequest(BaseModel):
    """恢复请求"""
    backup_path: str
    restore_database: bool = True
    restore_files: bool = True


@router.post("/create")
@limiter.limit("10/hour")
def create_backup(
    request: Request,
    backup_req: BackupRequest,
    admin_user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    创建备份（需要管理员权限，限流: 10次/小时）
    
    Returns:
        备份结果
    """
    backup_manager = get_backup_manager()
    
    try:
        backup_path = backup_manager.create_backup(
            backup_name=backup_req.backup_name,
            include_database=backup_req.include_database,
            include_files=backup_req.include_files
        )
        
        return {
            "status": "success",
            "message": "备份创建成功",
            "backup_path": str(backup_path),
            "backup_name": backup_path.name
        }
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建备份失败: {str(e)}"
        )


@router.post("/restore")
@limiter.limit("5/hour")
def restore_backup(
    request: Request,
    restore_req: RestoreRequest,
    admin_user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    恢复备份（需要管理员权限，限流: 5次/小时）
    
    Returns:
        恢复结果
    """
    backup_manager = get_backup_manager()
    
    backup_path = Path(restore_req.backup_path)
    if not backup_path.is_absolute():
        # 相对路径，从备份目录查找
        backup_path = backup_manager.backup_dir / restore_req.backup_path
    
    try:
        backup_manager.restore_backup(
            backup_path=backup_path,
            restore_database=restore_req.restore_database,
            restore_files=restore_req.restore_files
        )
        
        return {
            "status": "success",
            "message": "备份恢复成功"
        }
    except Exception as e:
        logger.error(f"恢复备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复备份失败: {str(e)}"
        )


@router.get("/list")
def list_backups(admin_user: Dict = Depends(require_admin)) -> Dict[str, Any]:
    """
    列出所有备份（需要管理员权限）
    
    Returns:
        备份列表
    """
    backup_manager = get_backup_manager()
    backups = backup_manager.list_backups()
    
    return {
        "status": "success",
        "backups": backups,
        "count": len(backups)
    }


@router.post("/cleanup")
@limiter.limit("1/hour")
def cleanup_backups(
    request: Request,
    days: int = 30,
    keep_count: int = 10,
    admin_user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    清理旧备份（需要管理员权限，限流: 1次/小时）
    
    Args:
        days: 保留天数
        keep_count: 至少保留的备份数量
        
    Returns:
        清理结果
    """
    backup_manager = get_backup_manager()
    
    try:
        backup_manager.cleanup_old_backups(days=days, keep_count=keep_count)
        
        return {
            "status": "success",
            "message": "清理完成"
        }
    except Exception as e:
        logger.error(f"清理备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理备份失败: {str(e)}"
        )

