#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟标签系统
允许用户通过规则引擎创建虚拟标签，用于成本分配和分组，无需修改云资源实际标签
"""

import logging
import sqlite3
import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

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
    """虚拟标签存储管理器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径，默认使用~/.cloudlens/virtual_tags.db
        """
        if db_path is None:
            db_dir = Path.home() / ".cloudlens"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "virtual_tags.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 创建虚拟标签表
            cursor.execute("""
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
            cursor.execute("""
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
            cursor.execute("""
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
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag_key_value ON virtual_tags(tag_key, tag_value)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag_rules_tag_id ON tag_rules(tag_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag_matches_resource ON tag_matches(resource_id, resource_type, account_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag_matches_tag ON tag_matches(tag_id)")
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def create_tag(self, tag: VirtualTag) -> str:
        """创建虚拟标签"""
        if not tag.id:
            tag.id = str(uuid.uuid4())
        
        now = datetime.now()
        tag.created_at = now
        tag.updated_at = now
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 插入标签
            cursor.execute("""
                INSERT INTO virtual_tags (id, name, tag_key, tag_value, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                tag.id,
                tag.name,
                tag.tag_key,
                tag.tag_value,
                tag.priority,
                tag.created_at.isoformat(),
                tag.updated_at.isoformat()
            ))
            
            # 插入规则
            for rule in tag.rules:
                if not rule.id:
                    rule.id = str(uuid.uuid4())
                rule.tag_id = tag.id
                cursor.execute("""
                    INSERT INTO tag_rules (id, tag_id, field, operator, pattern, priority)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    rule.id,
                    rule.tag_id,
                    rule.field,
                    rule.operator,
                    rule.pattern,
                    rule.priority
                ))
            
            conn.commit()
            logger.info(f"Created virtual tag: {tag.name} ({tag.id})")
            return tag.id
        except Exception as e:
            logger.error(f"Error creating tag: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_tag(self, tag_id: str) -> Optional[VirtualTag]:
        """获取虚拟标签"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 获取标签
            cursor.execute("SELECT * FROM virtual_tags WHERE id = ?", (tag_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            # 获取规则
            cursor.execute("SELECT * FROM tag_rules WHERE tag_id = ? ORDER BY priority DESC", (tag_id,))
            rule_rows = cursor.fetchall()
            
            rules = [
                TagRule(
                    id=r['id'],
                    tag_id=r['tag_id'],
                    field=r['field'],
                    operator=r['operator'],
                    pattern=r['pattern'],
                    priority=r['priority']
                )
                for r in rule_rows
            ]
            
            tag = VirtualTag(
                id=row['id'],
                name=row['name'],
                tag_key=row['tag_key'],
                tag_value=row['tag_value'],
                rules=rules,
                priority=row['priority'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
            )
            
            return tag
        finally:
            conn.close()
    
    def list_tags(self) -> List[VirtualTag]:
        """列出所有虚拟标签"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM virtual_tags ORDER BY priority DESC, created_at DESC")
            tag_ids = [row['id'] for row in cursor.fetchall()]
            
            tags = []
            for tag_id in tag_ids:
                tag = self.get_tag(tag_id)
                if tag:
                    tags.append(tag)
            
            return tags
        finally:
            conn.close()
    
    def update_tag(self, tag: VirtualTag) -> bool:
        """更新虚拟标签"""
        tag.updated_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 更新标签
            cursor.execute("""
                UPDATE virtual_tags
                SET name = ?, tag_key = ?, tag_value = ?, priority = ?, updated_at = ?
                WHERE id = ?
            """, (
                tag.name,
                tag.tag_key,
                tag.tag_value,
                tag.priority,
                tag.updated_at.isoformat(),
                tag.id
            ))
            
            # 删除旧规则
            cursor.execute("DELETE FROM tag_rules WHERE tag_id = ?", (tag.id,))
            
            # 插入新规则
            for rule in tag.rules:
                if not rule.id:
                    rule.id = str(uuid.uuid4())
                rule.tag_id = tag.id
                cursor.execute("""
                    INSERT INTO tag_rules (id, tag_id, field, operator, pattern, priority)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    rule.id,
                    rule.tag_id,
                    rule.field,
                    rule.operator,
                    rule.pattern,
                    rule.priority
                ))
            
            # 清除匹配缓存（规则已改变）
            cursor.execute("DELETE FROM tag_matches WHERE tag_id = ?", (tag.id,))
            
            conn.commit()
            logger.info(f"Updated virtual tag: {tag.name} ({tag.id})")
            return True
        except Exception as e:
            logger.error(f"Error updating tag: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_tag(self, tag_id: str) -> bool:
        """删除虚拟标签"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM virtual_tags WHERE id = ?", (tag_id,))
            conn.commit()
            logger.info(f"Deleted virtual tag: {tag_id}")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting tag: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_resource_tags(self, resource_id: str, resource_type: str, account_name: str) -> List[VirtualTag]:
        """获取资源的所有匹配标签"""
        # TODO: 实现资源标签查询
        # 可以从缓存表查询，或者实时计算
        pass
    
    def clear_cache(self, tag_id: Optional[str] = None):
        """清除匹配缓存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if tag_id:
                cursor.execute("DELETE FROM tag_matches WHERE tag_id = ?", (tag_id,))
            else:
                cursor.execute("DELETE FROM tag_matches")
            conn.commit()
        finally:
            conn.close()

