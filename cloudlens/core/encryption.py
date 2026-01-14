# -*- coding: utf-8 -*-
"""
数据加密模块
用于加密敏感数据（如 Access Key Secret）
"""

import os
import base64
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

# 加密密钥文件路径
KEY_FILE = Path.home() / ".cloudlens" / ".encryption_key"


class DataEncryption:
    """数据加密管理器"""
    
    def __init__(self, key: Optional[bytes] = None):
        """
        初始化加密管理器
        
        Args:
            key: 加密密钥（如果为 None，则从文件加载或生成新密钥）
        """
        if key is None:
            key = self._load_or_generate_key()
        
        self.cipher = Fernet(key)
        self._key = key
    
    def _load_or_generate_key(self) -> bytes:
        """
        加载或生成加密密钥
        
        Returns:
            加密密钥（bytes）
        """
        if KEY_FILE.exists():
            try:
                with open(KEY_FILE, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"加载加密密钥失败: {e}，将生成新密钥")
        
        # 生成新密钥
        key = Fernet.generate_key()
        
        # 保存密钥
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(KEY_FILE, "wb") as f:
                f.write(key)
            # 设置文件权限（仅所有者可读）
            os.chmod(KEY_FILE, 0o600)
            logger.info("已生成新的加密密钥")
        except Exception as e:
            logger.error(f"保存加密密钥失败: {e}")
        
        return key
    
    def encrypt(self, data: str) -> str:
        """
        加密数据
        
        Args:
            data: 要加密的字符串
            
        Returns:
            加密后的字符串（Base64 编码）
        """
        if not data:
            return ""
        
        try:
            encrypted = self.cipher.encrypt(data.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"加密数据失败: {e}")
            raise
    
    def decrypt(self, encrypted: str) -> str:
        """
        解密数据
        
        Args:
            encrypted: 加密后的字符串（Base64 编码）
            
        Returns:
            解密后的字符串
        """
        if not encrypted:
            return ""
        
        try:
            encrypted_bytes = base64.b64decode(encrypted.encode('utf-8'))
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"解密数据失败: {e}")
            raise
    
    def encrypt_dict(self, data: dict, fields: list) -> dict:
        """
        加密字典中的指定字段
        
        Args:
            data: 要加密的字典
            fields: 需要加密的字段名列表
            
        Returns:
            加密后的字典
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                result[field] = self.encrypt(result[field])
        return result
    
    def decrypt_dict(self, data: dict, fields: list) -> dict:
        """
        解密字典中的指定字段
        
        Args:
            data: 要解密的字典
            fields: 需要解密的字段名列表
            
        Returns:
            解密后的字典
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                try:
                    result[field] = self.decrypt(result[field])
                except Exception:
                    # 如果解密失败，可能是未加密的数据，保持原样
                    pass
        return result


# 全局实例
_encryption = None


def get_encryption() -> DataEncryption:
    """获取加密管理器实例（单例）"""
    global _encryption
    if _encryption is None:
        _encryption = DataEncryption()
    return _encryption

