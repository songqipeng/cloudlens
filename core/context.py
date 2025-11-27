#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Manager - 管理CLI上下文（如上次使用的账号）
"""

import os
import json
from pathlib import Path
from typing import Optional

CONTEXT_DIR = Path.home() / ".cloudlens"
CONTEXT_FILE = CONTEXT_DIR / "context.json"


class ContextManager:
    """管理CLI上下文"""
    
    def __init__(self):
        self.context = self._load_context()
    
    def _load_context(self) -> dict:
        """加载上下文"""
        if not CONTEXT_FILE.exists():
            return {}
        
        try:
            with open(CONTEXT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_context(self):
        """保存上下文"""
        CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.context, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # 静默失败，不影响主流程
            pass
    
    def get_last_account(self) -> Optional[str]:
        """获取上次使用的账号"""
        return self.context.get('last_account')
    
    def set_last_account(self, account: str):
        """设置上次使用的账号"""
        self.context['last_account'] = account
        self._save_context()
    
    def get_default_provider(self) -> str:
        """获取默认云厂商"""
        return self.context.get('default_provider', 'aliyun')
    
    def set_default_provider(self, provider: str):
        """设置默认云厂商"""
        self.context['default_provider'] = provider
        self._save_context()
