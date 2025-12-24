# -*- coding: utf-8 -*-
"""
数据备份管理器
实现自动备份、备份文件加密、异地存储等功能
"""

import os
import shutil
import json
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
import subprocess

from core.encryption import get_encryption

logger = logging.getLogger(__name__)

# 备份配置
BACKUP_DIR = Path.home() / ".cloudlens" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# 需要备份的数据
BACKUP_DATA_DIRS = [
    Path.home() / ".cloudlens" / "users.json",
    Path.home() / ".cloudlens" / "notifications.json",
    Path.home() / ".cloudlens" / "config.json",
    Path.home() / ".cloudlens" / "audit_logs",
]


class BackupManager:
    """数据备份管理器"""
    
    def __init__(self, backup_dir: Path = BACKUP_DIR, encrypt: bool = True):
        """
        初始化备份管理器
        
        Args:
            backup_dir: 备份目录
            encrypt: 是否加密备份文件
        """
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.encrypt = encrypt
        self.encryption = get_encryption() if encrypt else None
    
    def create_backup(
        self,
        backup_name: Optional[str] = None,
        include_database: bool = True,
        include_files: bool = True
    ) -> Path:
        """
        创建备份
        
        Args:
            backup_name: 备份名称（如果为 None，则自动生成）
            include_database: 是否包含数据库
            include_files: 是否包含配置文件
            
        Returns:
            备份文件路径
        """
        if backup_name is None:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        try:
            # 创建临时目录
            temp_dir = self.backup_dir / f"temp_{backup_name}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 备份配置文件
            if include_files:
                self._backup_files(temp_dir)
            
            # 备份数据库
            if include_database:
                self._backup_database(temp_dir)
            
            # 创建备份清单
            manifest = {
                "backup_name": backup_name,
                "created_at": datetime.now().isoformat(),
                "include_database": include_database,
                "include_files": include_files,
                "files": []
            }
            
            # 列出所有文件
            for file_path in temp_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(temp_dir)
                    manifest["files"].append({
                        "path": str(relative_path),
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
            
            # 保存清单
            manifest_path = temp_dir / "manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            # 创建压缩包
            self._create_archive(temp_dir, backup_path)
            
            # 加密备份文件（如果需要）
            if self.encrypt and self.encryption:
                backup_path = self._encrypt_backup(backup_path)
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
            
            logger.info(f"备份创建成功: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            raise
    
    def _backup_files(self, target_dir: Path):
        """备份配置文件"""
        files_dir = target_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in BACKUP_DATA_DIRS:
            if file_path.exists():
                if file_path.is_file():
                    # 复制文件
                    dest_path = files_dir / file_path.name
                    shutil.copy2(file_path, dest_path)
                elif file_path.is_dir():
                    # 复制目录
                    dest_dir = files_dir / file_path.name
                    shutil.copytree(file_path, dest_dir, dirs_exist_ok=True)
    
    def _backup_database(self, target_dir: Path):
        """备份数据库"""
        db_dir = target_dir / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # MySQL 备份
        db_type = os.getenv("DB_TYPE", "mysql").lower()
        
        if db_type == "mysql":
            try:
                db_host = os.getenv("MYSQL_HOST", "localhost")
                db_user = os.getenv("MYSQL_USER", "cloudlens")
                db_password = os.getenv("MYSQL_PASSWORD", "")
                db_name = os.getenv("MYSQL_DATABASE", "cloudlens")
                
                backup_file = db_dir / f"{db_name}.sql"
                
                # 使用 mysqldump 备份
                cmd = [
                    "mysqldump",
                    f"--host={db_host}",
                    f"--user={db_user}",
                    f"--password={db_password}",
                    "--single-transaction",
                    "--routines",
                    "--triggers",
                    db_name
                ]
                
                with open(backup_file, "w", encoding="utf-8") as f:
                    result = subprocess.run(
                        cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        logger.warning(f"MySQL 备份失败: {result.stderr}")
                    else:
                        logger.info(f"MySQL 备份成功: {backup_file}")
                        
            except Exception as e:
                logger.warning(f"数据库备份失败: {e}")
        else:
            # SQLite 备份
            db_path = os.getenv("SQLITE_DB_PATH")
            if not db_path:
                db_path = str(Path.home() / ".cloudlens" / "cloudlens.db")
            
            if os.path.exists(db_path):
                backup_file = db_dir / "cloudlens.db"
                shutil.copy2(db_path, backup_file)
                logger.info(f"SQLite 备份成功: {backup_file}")
    
    def _create_archive(self, source_dir: Path, target_file: Path):
        """创建压缩包"""
        import tarfile
        
        with tarfile.open(target_file, "w:gz") as tar:
            tar.add(source_dir, arcname=source_dir.name)
    
    def _encrypt_backup(self, backup_path: Path) -> Path:
        """加密备份文件"""
        encrypted_path = backup_path.with_suffix(".encrypted.tar.gz")
        
        # 读取备份文件
        with open(backup_path, "rb") as f:
            backup_data = f.read()
        
        # 加密
        encrypted_data = self.encryption.cipher.encrypt(backup_data)
        
        # 写入加密文件
        with open(encrypted_path, "wb") as f:
            f.write(encrypted_data)
        
        # 删除原文件
        backup_path.unlink()
        
        logger.info(f"备份文件已加密: {encrypted_path}")
        return encrypted_path
    
    def restore_backup(self, backup_path: Path, restore_database: bool = True, restore_files: bool = True):
        """
        恢复备份
        
        Args:
            backup_path: 备份文件路径
            restore_database: 是否恢复数据库
            restore_files: 是否恢复配置文件
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        try:
            # 解密备份文件（如果需要）
            if backup_path.suffixes == [".encrypted", ".tar", ".gz"]:
                backup_path = self._decrypt_backup(backup_path)
            
            # 解压备份
            temp_dir = self.backup_dir / f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            import tarfile
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(temp_dir)
            
            # 读取清单
            manifest_path = temp_dir / backup_path.stem.replace(".tar.gz", "").replace(".encrypted", "") / "manifest.json"
            if not manifest_path.exists():
                # 尝试查找清单文件
                for manifest_file in temp_dir.rglob("manifest.json"):
                    manifest_path = manifest_file
                    break
            
            if manifest_path.exists():
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            else:
                manifest = {}
            
            # 恢复文件
            if restore_files:
                files_dir = temp_dir / manifest.get("backup_name", "") / "files"
                if files_dir.exists():
                    self._restore_files(files_dir)
            
            # 恢复数据库
            if restore_database:
                db_dir = temp_dir / manifest.get("backup_name", "") / "database"
                if db_dir.exists():
                    self._restore_database(db_dir)
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
            
            logger.info(f"备份恢复成功: {backup_path}")
            
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            raise
    
    def _decrypt_backup(self, encrypted_path: Path) -> Path:
        """解密备份文件"""
        decrypted_path = encrypted_path.with_suffix("").with_suffix(".tar.gz")
        
        # 读取加密文件
        with open(encrypted_path, "rb") as f:
            encrypted_data = f.read()
        
        # 解密
        decrypted_data = self.encryption.cipher.decrypt(encrypted_data)
        
        # 写入解密文件
        with open(decrypted_path, "wb") as f:
            f.write(decrypted_data)
        
        logger.info(f"备份文件已解密: {decrypted_path}")
        return decrypted_path
    
    def _restore_files(self, files_dir: Path):
        """恢复配置文件"""
        cloudlens_dir = Path.home() / ".cloudlens"
        cloudlens_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in files_dir.iterdir():
            dest_path = cloudlens_dir / file_path.name
            if file_path.is_file():
                shutil.copy2(file_path, dest_path)
            elif file_path.is_dir():
                shutil.copytree(file_path, dest_path, dirs_exist_ok=True)
    
    def _restore_database(self, db_dir: Path):
        """恢复数据库"""
        db_type = os.getenv("DB_TYPE", "mysql").lower()
        
        if db_type == "mysql":
            # 查找 SQL 文件
            sql_files = list(db_dir.glob("*.sql"))
            if sql_files:
                sql_file = sql_files[0]
                
                try:
                    db_host = os.getenv("MYSQL_HOST", "localhost")
                    db_user = os.getenv("MYSQL_USER", "cloudlens")
                    db_password = os.getenv("MYSQL_PASSWORD", "")
                    db_name = os.getenv("MYSQL_DATABASE", "cloudlens")
                    
                    # 使用 mysql 恢复
                    cmd = [
                        "mysql",
                        f"--host={db_host}",
                        f"--user={db_user}",
                        f"--password={db_password}",
                        db_name
                    ]
                    
                    with open(sql_file, "r", encoding="utf-8") as f:
                        result = subprocess.run(
                            cmd,
                            stdin=f,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        
                        if result.returncode != 0:
                            logger.warning(f"MySQL 恢复失败: {result.stderr}")
                        else:
                            logger.info(f"MySQL 恢复成功")
                            
                except Exception as e:
                    logger.warning(f"数据库恢复失败: {e}")
        else:
            # SQLite 恢复
            db_files = list(db_dir.glob("*.db"))
            if db_files:
                db_file = db_files[0]
                db_path = os.getenv("SQLITE_DB_PATH")
                if not db_path:
                    db_path = str(Path.home() / ".cloudlens" / "cloudlens.db")
                
                shutil.copy2(db_file, db_path)
                logger.info(f"SQLite 恢复成功")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        
        for backup_file in self.backup_dir.glob("*.tar.gz"):
            try:
                stat = backup_file.stat()
                backups.append({
                    "name": backup_file.name,
                    "path": str(backup_file),
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "encrypted": ".encrypted" in backup_file.name
                })
            except Exception as e:
                logger.warning(f"读取备份文件信息失败 {backup_file}: {e}")
        
        # 按创建时间倒序排序
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        
        return backups
    
    def cleanup_old_backups(self, days: int = 30, keep_count: int = 10):
        """
        清理旧备份
        
        Args:
            days: 保留天数
            keep_count: 至少保留的备份数量
        """
        backups = self.list_backups()
        
        # 按时间排序
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for backup in backups[keep_count:]:  # 保留最新的 keep_count 个
            backup_date = datetime.fromisoformat(backup["created_at"])
            
            if backup_date < cutoff_date:
                try:
                    backup_path = Path(backup["path"])
                    backup_path.unlink()
                    deleted_count += 1
                    logger.info(f"已删除旧备份: {backup_path}")
                except Exception as e:
                    logger.warning(f"删除备份失败 {backup_path}: {e}")
        
        logger.info(f"清理完成，删除了 {deleted_count} 个旧备份")


# 全局实例
_backup_manager = None


def get_backup_manager() -> BackupManager:
    """获取备份管理器实例（单例）"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager

