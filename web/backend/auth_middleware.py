# -*- coding: utf-8 -*-
"""
认证中间件
用于 FastAPI 的 JWT 认证和权限验证
"""

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging

from core.auth import get_jwt_auth, JWTAuth

logger = logging.getLogger(__name__)

# HTTP Bearer Token 安全方案
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    获取当前用户（从 JWT Token）
    
    Args:
        credentials: HTTP Bearer Token 凭证
        
    Returns:
        用户信息（Token 载荷）
        
    Raises:
        HTTPException: 如果 Token 无效或过期
    """
    token = credentials.credentials
    jwt_auth = get_jwt_auth()
    
    payload = jwt_auth.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


def get_current_username(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> str:
    """获取当前用户名"""
    return current_user.get("username")


def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    要求管理员权限
    
    Args:
        current_user: 当前用户信息
        
    Returns:
        用户信息
        
    Raises:
        HTTPException: 如果不是管理员
    """
    role = current_user.get("role", "user")
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """
    可选认证（用于公开接口，但如果有 Token 则验证）
    
    Args:
        credentials: HTTP Bearer Token 凭证（可选）
        
    Returns:
        用户信息（如果有 Token 且有效），否则返回 None
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    jwt_auth = get_jwt_auth()
    
    payload = jwt_auth.verify_token(token)
    return payload

