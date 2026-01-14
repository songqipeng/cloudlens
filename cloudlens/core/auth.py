# -*- coding: utf-8 -*-
"""
认证和授权模块
实现 JWT 认证、用户管理等功能
"""

import os
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

# JWT 配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24  # Token 有效期 24 小时

# 用户存储文件
USERS_FILE = Path.home() / ".cloudlens" / "users.json"


class UserManager:
    """用户管理器"""
    
    def __init__(self):
        self.users_file = USERS_FILE
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_users()
    
    def _load_users(self) -> Dict[str, Dict]:
        """加载用户数据"""
        if self.users_file.exists():
            try:
                with open(self.users_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载用户数据失败: {e}")
        return {}
    
    def _save_users(self, users: Dict[str, Dict]):
        """保存用户数据"""
        try:
            with open(self.users_file, "w", encoding="utf-8") as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户数据失败: {e}")
            raise
    
    def create_user(self, username: str, password: str, email: Optional[str] = None, role: str = "user") -> bool:
        """
        创建用户
        
        Args:
            username: 用户名
            password: 密码（明文，会自动加密）
            email: 邮箱（可选）
            role: 角色（user/admin），默认 user
            
        Returns:
            是否创建成功
        """
        users = self._load_users()
        
        if username in users:
            logger.warning(f"用户已存在: {username}")
            return False
        
        # 加密密码（使用 SHA256）
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        users[username] = {
            "username": username,
            "password_hash": password_hash,
            "email": email,
            "role": role,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "enabled": True
        }
        
        self._save_users(users)
        logger.info(f"用户创建成功: {username}")
        return True
    
    def verify_user(self, username: str, password: str) -> bool:
        """
        验证用户密码
        
        Args:
            username: 用户名
            password: 密码（明文）
            
        Returns:
            是否验证成功
        """
        users = self._load_users()
        
        if username not in users:
            logger.warning(f"用户不存在: {username}")
            return False
        
        user = users[username]
        
        if not user.get("enabled", True):
            logger.warning(f"用户已禁用: {username}")
            return False
        
        # 验证密码
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user["password_hash"] != password_hash:
            logger.warning(f"密码错误: {username}")
            return False
        
        # 更新最后登录时间
        user["last_login"] = datetime.now().isoformat()
        self._save_users(users)
        
        logger.info(f"用户验证成功: {username}")
        return True
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """获取用户信息（不包含密码）"""
        users = self._load_users()
        if username in users:
            user = users[username].copy()
            user.pop("password_hash", None)  # 移除密码哈希
            return user
        return None
    
    def update_user(self, username: str, **kwargs) -> bool:
        """更新用户信息"""
        users = self._load_users()
        
        if username not in users:
            return False
        
        user = users[username]
        
        # 允许更新的字段
        allowed_fields = ["email", "role", "enabled"]
        for key, value in kwargs.items():
            if key in allowed_fields:
                user[key] = value
        
        self._save_users(users)
        logger.info(f"用户信息已更新: {username}")
        return True
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        if not self.verify_user(username, old_password):
            return False
        
        users = self._load_users()
        if username not in users:
            return False
        
        # 加密新密码
        new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        users[username]["password_hash"] = new_password_hash
        
        self._save_users(users)
        logger.info(f"密码已修改: {username}")
        return True
    
    def list_users(self) -> list:
        """列出所有用户（不包含密码）"""
        users = self._load_users()
        result = []
        for username, user in users.items():
            user_info = user.copy()
            user_info.pop("password_hash", None)
            result.append(user_info)
        return result


class JWTAuth:
    """JWT 认证管理器"""
    
    def __init__(self, secret_key: str = JWT_SECRET_KEY, algorithm: str = JWT_ALGORITHM):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.user_manager = UserManager()
    
    def create_token(self, username: str, expiration_hours: int = JWT_EXPIRATION_HOURS) -> str:
        """
        创建 JWT Token
        
        Args:
            username: 用户名
            expiration_hours: 过期时间（小时）
            
        Returns:
            JWT Token 字符串
        """
        user = self.user_manager.get_user(username)
        if not user:
            raise ValueError(f"用户不存在: {username}")
        
        # Token 载荷
        payload = {
            "username": username,
            "role": user.get("role", "user"),
            "email": user.get("email"),
            "iat": datetime.utcnow(),  # 签发时间
            "exp": datetime.utcnow() + timedelta(hours=expiration_hours)  # 过期时间
        }
        
        # 生成 Token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证 JWT Token
        
        Args:
            token: JWT Token 字符串
            
        Returns:
            Token 载荷（如果有效），否则返回 None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查用户是否仍然存在且启用
            username = payload.get("username")
            user = self.user_manager.get_user(username)
            
            if not user or not user.get("enabled", True):
                logger.warning(f"用户不存在或已禁用: {username}")
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token 已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token 无效: {e}")
            return None
    
    def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            登录结果（包含 token 和用户信息），如果失败返回 None
        """
        if not self.user_manager.verify_user(username, password):
            return None
        
        token = self.create_token(username)
        user = self.user_manager.get_user(username)
        
        return {
            "token": token,
            "user": user,
            "expires_in": JWT_EXPIRATION_HOURS * 3600  # 秒
        }


# 全局实例
_jwt_auth = JWTAuth()
_user_manager = UserManager()


def get_jwt_auth() -> JWTAuth:
    """获取 JWT 认证实例"""
    return _jwt_auth


def get_user_manager() -> UserManager:
    """获取用户管理器实例"""
    return _user_manager

