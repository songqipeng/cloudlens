#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟标签系统
允许用户通过规则引擎创建虚拟标签，用于成本分配和分组，无需修改云资源实际标签
"""

import logging
import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from cloudlens.core.database import DatabaseFactory

logger = logging.getLogger(__name__)


class RuleOperator(str, Enum):
    """规则操作符"""
    AND = "AND"
    OR = "OR"


class MatchOperator(str, Enum):
    """匹配操作符"""
    CONTAINS = "contains"      # 包含
    EQUALS = "equals"          # 等于
    STARTS_WITH = "starts_with"  # 开头
    ENDS_WITH = "ends_with"    # 结尾
    REGEX = "regex"            # 正则表达式
    IN = "in"                  # 在列表中
    NOT_IN = "not_in"          # 不在列表中


@dataclass
class TagRule:
    """标签规则"""
    id: str
    tag_id: str
    field: str              # 资源字段（name, region, type, instance_id等）
    operator: str           # 匹配操作符
    pattern: str            # 匹配模式
    priority: int = 0       # 优先级（数字越大优先级越高）
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TagRule':
        return cls(**data)


@dataclass
class VirtualTag:
    """虚拟标签"""
    id: str
    name: str               # 标签名称（显示用）
    tag_key: str            # 标签key（如：environment）
    tag_value: str          # 标签value（如：production）
    rules: List[TagRule]    # 规则列表
    priority: int = 0       # 优先级（数字越大优先级越高）
    created_at: datetime = None
    updated_at: datetime = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['rules'] = [rule.to_dict() for rule in self.rules]
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VirtualTag':
        rules = [TagRule.from_dict(r) for r in data.get('rules', [])]
        created_at = None
        updated_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])
        return cls(
            id=data['id'],
            name=data['name'],
            tag_key=data['tag_key'],
            tag_value=data['tag_value'],
            rules=rules,
            priority=data.get('priority', 0),
            created_at=created_at,
            updated_at=updated_at
        )


class TagEngine:
    """标签规则引擎"""
    
    @staticmethod
    def match_rule(resource: Dict[str, Any], rule: TagRule) -> bool:
        """
        检查资源是否匹配规则
        
        Args:
            resource: 资源字典（包含name, region, type等字段）
            rule: 标签规则
            
        Returns:
            bool: 是否匹配
        """
        field_value = resource.get(rule.field, "")
        if field_value is None:
            field_value = ""
        
        # 转换为字符串进行比较
        field_value = str(field_value).lower()
        pattern = rule.pattern.lower()
        
        try:
            if rule.operator == MatchOperator.CONTAINS:
                return pattern in field_value
            elif rule.operator == MatchOperator.EQUALS:
                return field_value == pattern
            elif rule.operator == MatchOperator.STARTS_WITH:
                return field_value.startswith(pattern)
            elif rule.operator == MatchOperator.ENDS_WITH:
                return field_value.endswith(pattern)
            elif rule.operator == MatchOperator.REGEX:
                return bool(re.search(pattern, field_value, re.IGNORECASE))
            elif rule.operator == MatchOperator.IN:
                # pattern是逗号分隔的列表
                values = [v.strip() for v in pattern.split(',')]
                return field_value in [v.lower() for v in values]
            elif rule.operator == MatchOperator.NOT_IN:
                values = [v.strip() for v in pattern.split(',')]
                return field_value not in [v.lower() for v in values]
            else:
                logger.warning(f"Unknown operator: {rule.operator}")
                return False
        except Exception as e:
            logger.error(f"Error matching rule {rule.id}: {e}")
            return False
    
    @staticmethod
    def match_tag(resource: Dict[str, Any], tag: VirtualTag) -> bool:
        """
        检查资源是否匹配标签的所有规则
        
        Args:
            resource: 资源字典
            tag: 虚拟标签
            
        Returns:
            bool: 是否匹配
        """
        if not tag.rules:
            return False
        
        # 按优先级排序规则
        sorted_rules = sorted(tag.rules, key=lambda r: r.priority, reverse=True)
        
        # 目前只支持AND逻辑（所有规则都必须匹配）
        # TODO: 未来可以支持OR逻辑
        for rule in sorted_rules:
            if not TagEngine.match_rule(resource, rule):
                return False
        
        return True


class VirtualTagStorage:
    """虚拟标签存储管理器（支持SQLite和MySQL）"""
    
    def __init__(self, db_path: Optional[str] = None, db_type: Optional[str] = None):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径（仅SQLite使用），默认使用~/.cloudlens/virtual_tags.db
            db_type: 数据库类型（'sqlite' 或 'mysql'），None则从环境变量读取
        """
        self.db_type = db_type or os.getenv("DB_TYPE", "mysql").lower()
        
        if self.db_type == "mysql":
            self.db = None  # 延迟初始化，避免导入时连接MySQL
            self.db_path = None
        else:
            if db_path is None:
                db_dir = Path.home() / ".cloudlens"
                db_dir.mkdir(parents=True, exist_ok=True)
                db_path = str(db_dir / "virtual_tags.db")
            self.db_path = db_path
            self.db = DatabaseFactory.create_adapter("sqlite", db_path=db_path)
        
        self._init_database()
    
    def _get_db(self):
        """延迟获取数据库适配器"""
        if self.db is None:
            self.db = DatabaseFactory.create_adapter("mysql")
        return self.db
    
    def _get_placeholder(self) -> str:
        """获取SQL占位符"""
        return "%s" if self.db_type == "mysql" else "?"
    
    def _init_database(self):
        """初始化数据库表结构（延迟执行，避免导入时连接MySQL）"""
        if self.db_type == "mysql":
            # MySQL表结构已在init_mysql_schema.sql中创建
            # 延迟检查，避免导入时连接
            pass
        else:
            # SQLite表结构（立即创建，因为SQLite是本地文件）
            try:
                # 创建虚拟标签表
                self._get_db().execute("""
                CREATE TABLE IF NOT EXISTS virtual_tags (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    tag_key VARCHAR(100) NOT NULL,
                    tag_value VARCHAR(255) NOT NULL,
                    priority INT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """ if self.db_type == "mysql" else """
                CREATE TABLE IF NOT EXISTS virtual_tags (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    tag_key TEXT NOT NULL,
                    tag_value TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建标签规则表
            self._get_db().execute("""
                CREATE TABLE IF NOT EXISTS tag_rules (
                    id VARCHAR(255) PRIMARY KEY,
                    tag_id VARCHAR(255) NOT NULL,
                    field VARCHAR(100) NOT NULL,
                    operator VARCHAR(50) NOT NULL,
                    pattern TEXT NOT NULL,
                    priority INT DEFAULT 0,
                    FOREIGN KEY (tag_id) REFERENCES virtual_tags(id) ON DELETE CASCADE
                )
            """ if self.db_type == "mysql" else """
                CREATE TABLE IF NOT EXISTS tag_rules (
                    id TEXT PRIMARY KEY,
                    tag_id TEXT NOT NULL,
                    field TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    FOREIGN KEY (tag_id) REFERENCES virtual_tags(id) ON DELETE CASCADE
                )
            """)
            
            # 创建标签匹配缓存表（性能优化）
            self._get_db().execute("""
                CREATE TABLE IF NOT EXISTS tag_matches (
                    resource_id VARCHAR(255) NOT NULL,
                    resource_type VARCHAR(50) NOT NULL,
                    account_name VARCHAR(255) NOT NULL,
                    tag_id VARCHAR(255) NOT NULL,
                    matched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (resource_id, resource_type, account_name, tag_id),
                    FOREIGN KEY (tag_id) REFERENCES virtual_tags(id) ON DELETE CASCADE
                )
            """ if self.db_type == "mysql" else """
                CREATE TABLE IF NOT EXISTS tag_matches (
                    resource_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    account_name TEXT NOT NULL,
                    tag_id TEXT NOT NULL,
                    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (resource_id, resource_type, account_name, tag_id),
                    FOREIGN KEY (tag_id) REFERENCES virtual_tags(id) ON DELETE CASCADE
                )
            """)
            
            # 创建索引（MySQL不支持IF NOT EXISTS，需要先检查）
            if self.db_type == "mysql":
                # MySQL: 先检查索引是否存在，不存在则创建
                indexes_to_create = [
                    ("idx_tag_key_value", "virtual_tags", "tag_key, tag_value"),
                    ("idx_tag_rules_tag_id", "tag_rules", "tag_id"),
                    ("idx_tag_matches_resource", "tag_matches", "resource_id, resource_type"),
                    ("idx_tag_matches_tag", "tag_matches", "tag_id"),
                ]
                for idx_name, table_name, columns in indexes_to_create:
                    try:
                        # 检查索引是否存在
                        result = self._get_db().query(f"""
                            SELECT COUNT(*) as cnt 
                            FROM information_schema.statistics 
                            WHERE table_schema = DATABASE() 
                            AND table_name = '{table_name}' 
                            AND index_name = '{idx_name}'
                        """)
                        if result and result[0].get('cnt', 0) == 0:
                            self._get_db().execute(f"CREATE INDEX {idx_name} ON {table_name}({columns})")
                    except Exception as e:
                        logger.debug(f"Index {idx_name} creation skipped: {e}")
            else:
                # SQLite支持IF NOT EXISTS
                try:
                    self._get_db().execute("CREATE INDEX IF NOT EXISTS idx_tag_key_value ON virtual_tags(tag_key, tag_value)")
                    self._get_db().execute("CREATE INDEX IF NOT EXISTS idx_tag_rules_tag_id ON tag_rules(tag_id)")
                    self._get_db().execute("CREATE INDEX IF NOT EXISTS idx_tag_matches_resource ON tag_matches(resource_id, resource_type, account_name)")
                    self._get_db().execute("CREATE INDEX IF NOT EXISTS idx_tag_matches_tag ON tag_matches(tag_id)")
                except Exception as e:
                    logger.debug(f"Index creation skipped (may already exist): {e}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def create_tag(self, tag: VirtualTag) -> str:
        """创建虚拟标签"""
        if not tag.id:
            tag.id = str(uuid.uuid4())
        
        now = datetime.now()
        tag.created_at = now
        tag.updated_at = now
        
        placeholder = self._get_placeholder()
        try:
            # 插入标签
            self._get_db().execute(f"""
                INSERT INTO virtual_tags (id, name, tag_key, tag_value, priority, created_at, updated_at)
                VALUES ({', '.join([placeholder] * 7)})
            """, (
                tag.id,
                tag.name,
                tag.tag_key,
                tag.tag_value,
                tag.priority,
                tag.created_at.isoformat() if tag.created_at else None,
                tag.updated_at.isoformat() if tag.updated_at else None
            ))
            
            # 插入规则
            for rule in tag.rules:
                if not rule.id:
                    rule.id = str(uuid.uuid4())
                rule.tag_id = tag.id
                self._get_db().execute(f"""
                    INSERT INTO tag_rules (id, tag_id, field, operator, pattern, priority)
                    VALUES ({', '.join([placeholder] * 6)})
                """, (
                    rule.id,
                    rule.tag_id,
                    rule.field,
                    rule.operator,
                    rule.pattern,
                    rule.priority
                ))
            
            logger.info(f"Created virtual tag: {tag.name} ({tag.id})")
            return tag.id
        except Exception as e:
            logger.error(f"Error creating tag: {e}")
            raise
    
    def get_tag(self, tag_id: str) -> Optional[VirtualTag]:
        """获取虚拟标签"""
        placeholder = self._get_placeholder()
        # 获取标签
        rows = self._get_db().query(f"SELECT * FROM virtual_tags WHERE id = {placeholder}", (tag_id,))
        if not rows:
                return None
        
        row = rows[0]
            
            # 获取规则
        rule_rows = self._get_db().query(f"SELECT * FROM tag_rules WHERE tag_id = {placeholder} ORDER BY priority DESC", (tag_id,))
        
        rules = []
        for r in rule_rows:
            if isinstance(r, dict):
                rules.append(TagRule(
                    id=r.get('id', ''),
                    tag_id=r.get('tag_id', ''),
                    field=r.get('field', ''),
                    operator=r.get('operator', ''),
                    pattern=r.get('pattern', ''),
                    priority=int(r.get('priority', 0))
                ))
            else:
                rules.append(TagRule(
                    id=r[0],
                    tag_id=r[1],
                    field=r[2],
                    operator=r[3],
                    pattern=r[4],
                    priority=int(r[5] or 0)
                ))
        
        if isinstance(row, dict):
            return VirtualTag(
                id=row.get('id', ''),
                name=row.get('name', ''),
                tag_key=row.get('tag_key', ''),
                tag_value=row.get('tag_value', ''),
                rules=rules,
                priority=int(row.get('priority', 0)),
                created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else None
            )
        else:
            return VirtualTag(
                id=row[0],
                name=row[1],
                tag_key=row[2],
                tag_value=row[3],
                rules=rules,
                priority=int(row[4] or 0),
                created_at=datetime.fromisoformat(row[5]) if row[5] else None,
                updated_at=datetime.fromisoformat(row[6]) if len(row) > 6 and row[6] else None
            )
    
    def list_tags(self) -> List[VirtualTag]:
        """列出所有虚拟标签"""
        rows = self._get_db().query("SELECT id FROM virtual_tags ORDER BY priority DESC, created_at DESC")
        
        # 处理查询结果可能为None的情况
        if rows is None:
            logger.warning("查询虚拟标签列表返回None，返回空列表")
            return []
        
        tag_ids = [row.get('id') if isinstance(row, dict) else row[0] for row in rows]
        
        tags = []
        for tag_id in tag_ids:
            tag = self.get_tag(tag_id)
            if tag:
                tags.append(tag)
        
        return tags
    
    def update_tag(self, tag: VirtualTag) -> bool:
        """更新虚拟标签"""
        tag.updated_at = datetime.now()
        
        placeholder = self._get_placeholder()
        try:
            # 更新标签
            self._get_db().execute(f"""
                UPDATE virtual_tags
                SET name = {placeholder}, tag_key = {placeholder}, tag_value = {placeholder}, priority = {placeholder}, updated_at = {placeholder}
                WHERE id = {placeholder}
            """, (
                tag.name,
                tag.tag_key,
                tag.tag_value,
                tag.priority,
                tag.updated_at.isoformat() if tag.updated_at else None,
                tag.id
            ))
            
            # 删除旧规则
            self._get_db().execute(f"DELETE FROM tag_rules WHERE tag_id = {placeholder}", (tag.id,))
            
            # 插入新规则
            for rule in tag.rules:
                if not rule.id:
                    rule.id = str(uuid.uuid4())
                rule.tag_id = tag.id
                self._get_db().execute(f"""
                    INSERT INTO tag_rules (id, tag_id, field, operator, pattern, priority)
                    VALUES ({', '.join([placeholder] * 6)})
                """, (
                    rule.id,
                    rule.tag_id,
                    rule.field,
                    rule.operator,
                    rule.pattern,
                    rule.priority
                ))
            
            # 清除匹配缓存（规则已改变）
            self._get_db().execute(f"DELETE FROM tag_matches WHERE tag_id = {placeholder}", (tag.id,))
            
            logger.info(f"Updated virtual tag: {tag.name} ({tag.id})")
            return True
        except Exception as e:
            logger.error(f"Error updating tag: {e}")
            return False
    
    def delete_tag(self, tag_id: str) -> bool:
        """删除虚拟标签"""
        placeholder = self._get_placeholder()
        try:
            cursor = self._get_db().execute(f"DELETE FROM virtual_tags WHERE id = {placeholder}", (tag_id,))
            logger.info(f"Deleted virtual tag: {tag_id}")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting tag: {e}")
            return False
    
    def get_resource_tags(self, resource_id: str, resource_type: str, account_name: str) -> List[VirtualTag]:
        """获取资源的所有匹配标签"""
        # TODO: 实现资源标签查询
        # 可以从缓存表查询，或者实时计算
        pass
    
    def clear_cache(self, tag_id: Optional[str] = None):
        """清除匹配缓存"""
        placeholder = self._get_placeholder()
        try:
            if tag_id:
                self._get_db().execute(f"DELETE FROM tag_matches WHERE tag_id = {placeholder}", (tag_id,))
            else:
                self._get_db().execute("DELETE FROM tag_matches")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")



