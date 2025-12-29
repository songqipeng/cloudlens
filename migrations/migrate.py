#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移工具
支持版本管理、升级、降级等操作
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseFactory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationManager:
    """数据库迁移管理器"""

    def __init__(self, migrations_dir: str = None):
        """
        初始化迁移管理器

        Args:
            migrations_dir: 迁移脚本目录
        """
        if migrations_dir is None:
            migrations_dir = Path(__file__).parent

        self.migrations_dir = Path(migrations_dir)
        self.db = DatabaseFactory.create()

    def get_current_version(self) -> int:
        """获取当前数据库版本"""
        try:
            result = self.db.query_one(
                "SELECT MAX(version) as version FROM schema_migrations"
            )
            return result['version'] if result and result['version'] is not None else 0
        except Exception as e:
            logger.warning(f"schema_migrations table not found, assuming version 0: {e}")
            return 0

    def get_available_migrations(self) -> List[Dict]:
        """获取可用的迁移脚本"""
        migrations = []

        for file in sorted(self.migrations_dir.glob("*.sql")):
            if file.name.startswith('.'):
                continue

            # 解析文件名：001_description.sql
            parts = file.stem.split('_', 1)
            if len(parts) < 2:
                logger.warning(f"Invalid migration filename format: {file.name}")
                continue

            try:
                version = int(parts[0])
            except ValueError:
                logger.warning(f"Invalid version number in filename: {file.name}")
                continue

            migrations.append({
                'version': version,
                'name': file.stem,
                'description': parts[1].replace('_', ' '),
                'file': file
            })

        return sorted(migrations, key=lambda x: x['version'])

    def get_pending_migrations(self) -> List[Dict]:
        """获取待执行的迁移"""
        current_version = self.get_current_version()
        all_migrations = self.get_available_migrations()

        return [m for m in all_migrations if m['version'] > current_version]

    def execute_migration(self, migration: Dict, direction: str = 'up'):
        """
        执行迁移

        Args:
            migration: 迁移信息
            direction: 方向（up/down）
        """
        logger.info(f"Executing migration {migration['version']}: {migration['description']}")

        # 读取SQL文件
        with open(migration['file'], 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # 执行SQL（分割多个语句）
        statements = self._split_sql_statements(sql_content)

        try:
            for stmt in statements:
                stmt = stmt.strip()
                if not stmt or stmt.startswith('--'):
                    continue

                # 跳过回滚部分（DOWN migration）
                if direction == 'up' and '-- DOWN Migration' in stmt:
                    break

                # 执行语句
                try:
                    self.db.execute(stmt)
                except Exception as e:
                    # 某些查询语句（如SELECT）可能会报错，忽略
                    if 'SELECT' not in stmt.upper():
                        logger.error(f"Error executing statement: {e}")
                        raise

            logger.info(f"Migration {migration['version']} completed successfully")
            return True

        except Exception as e:
            logger.error(f"Migration {migration['version']} failed: {e}")
            return False

    def _split_sql_statements(self, sql: str) -> List[str]:
        """分割SQL语句"""
        # 简单实现：按分号分割（不处理存储过程等复杂情况）
        statements = []
        current = []

        for line in sql.split('\n'):
            line = line.strip()

            # 跳过注释
            if line.startswith('--'):
                continue

            current.append(line)

            # 如果行以分号结束，认为是一个完整语句
            if line.endswith(';'):
                statements.append('\n'.join(current))
                current = []

        # 添加最后一个语句（如果没有分号）
        if current:
            statements.append('\n'.join(current))

        return statements

    def upgrade(self, target_version: Optional[int] = None):
        """
        升级数据库到指定版本

        Args:
            target_version: 目标版本（None表示升级到最新）
        """
        current_version = self.get_current_version()
        logger.info(f"Current database version: {current_version}")

        pending = self.get_pending_migrations()

        if not pending:
            logger.info("No pending migrations. Database is up to date.")
            return

        # 筛选要执行的迁移
        if target_version is not None:
            pending = [m for m in pending if m['version'] <= target_version]

        if not pending:
            logger.info(f"No migrations to execute up to version {target_version}")
            return

        logger.info(f"Found {len(pending)} pending migration(s)")

        # 执行迁移
        for migration in pending:
            success = self.execute_migration(migration, direction='up')
            if not success:
                logger.error(f"Migration {migration['version']} failed. Stopping.")
                break

        # 显示最终版本
        final_version = self.get_current_version()
        logger.info(f"Database upgraded to version {final_version}")

    def status(self):
        """显示迁移状态"""
        current_version = self.get_current_version()
        all_migrations = self.get_available_migrations()

        print("\n" + "="*60)
        print("Database Migration Status")
        print("="*60)
        print(f"Current version: {current_version}")
        print(f"\nAvailable migrations:")
        print("-"*60)

        for migration in all_migrations:
            status = "✓ Applied" if migration['version'] <= current_version else "  Pending"
            print(f"{status} | Version {migration['version']:03d} | {migration['description']}")

        pending = self.get_pending_migrations()
        print(f"\nPending migrations: {len(pending)}")
        print("="*60 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='CloudLens Database Migration Tool')
    subparsers = parser.add_parsers(dest='command', help='Available commands')

    # status命令
    subparsers.add_parser('status', help='Show migration status')

    # upgrade命令
    upgrade_parser = subparsers.add_parser('upgrade', help='Upgrade database')
    upgrade_parser.add_argument(
        '--target',
        type=int,
        help='Target version (default: latest)'
    )

    # downgrade命令
    downgrade_parser = subparsers.add_parser('downgrade', help='Downgrade database')
    downgrade_parser.add_argument(
        '--target',
        type=int,
        required=True,
        help='Target version'
    )

    args = parser.parse_args()

    # 创建迁移管理器
    manager = MigrationManager()

    # 执行命令
    if args.command == 'status':
        manager.status()
    elif args.command == 'upgrade':
        manager.upgrade(target_version=args.target)
    elif args.command == 'downgrade':
        logger.error("Downgrade not implemented yet. Please run DOWN migration SQL manually.")
        sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
