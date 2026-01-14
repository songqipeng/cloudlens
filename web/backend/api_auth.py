# -*- coding: utf-8 -*-
"""
认证相关 API 端点
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import logging

from cloudlens.core.auth import get_jwt_auth, get_user_manager
from web.backend.auth_middleware import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# 请求模型
class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str
    email: Optional[EmailStr] = None


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str


class UpdateUserRequest(BaseModel):
    """更新用户请求"""
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    enabled: Optional[bool] = None


# 响应模型
class LoginResponse(BaseModel):
    """登录响应"""
    token: str
    user: Dict[str, Any]
    expires_in: int


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    """
    用户登录
    
    Returns:
        登录结果（包含 token 和用户信息）
    """
    jwt_auth = get_jwt_auth()
    
    result = jwt_auth.login(request.username, request.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    return LoginResponse(**result)


@router.post("/register")
def register(request: RegisterRequest, admin_user: Dict = Depends(require_admin)) -> Dict[str, Any]:
    """
    注册新用户（需要管理员权限）
    
    Returns:
        注册结果
    """
    user_manager = get_user_manager()
    
    success = user_manager.create_user(
        username=request.username,
        password=request.password,
        email=request.email,
        role="user"  # 新用户默认为普通用户
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    return {
        "status": "success",
        "message": "用户注册成功",
        "username": request.username
    }


@router.get("/me")
def get_current_user_info(current_user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    获取当前用户信息
    
    Returns:
        当前用户信息
    """
    return current_user


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    修改密码
    
    Returns:
        修改结果
    """
    username = current_user.get("username")
    user_manager = get_user_manager()
    
    success = user_manager.change_password(
        username=username,
        old_password=request.old_password,
        new_password=request.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )
    
    return {
        "status": "success",
        "message": "密码修改成功"
    }


@router.get("/users")
def list_users(admin_user: Dict = Depends(require_admin)) -> Dict[str, Any]:
    """
    列出所有用户（需要管理员权限）
    
    Returns:
        用户列表
    """
    user_manager = get_user_manager()
    users = user_manager.list_users()
    
    return {
        "status": "success",
        "users": users,
        "count": len(users)
    }


@router.put("/users/{username}")
def update_user(
    username: str,
    request: UpdateUserRequest,
    admin_user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    更新用户信息（需要管理员权限）
    
    Returns:
        更新结果
    """
    user_manager = get_user_manager()
    
    update_data = {}
    if request.email is not None:
        update_data["email"] = request.email
    if request.role is not None:
        update_data["role"] = request.role
    if request.enabled is not None:
        update_data["enabled"] = request.enabled
    
    success = user_manager.update_user(username, **update_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return {
        "status": "success",
        "message": "用户信息已更新",
        "username": username
    }


@router.get("/users/{username}")
def get_user(username: str, admin_user: Dict = Depends(require_admin)) -> Dict[str, Any]:
    """
    获取用户信息（需要管理员权限）
    
    Returns:
        用户信息
    """
    user_manager = get_user_manager()
    user = user_manager.get_user(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return {
        "status": "success",
        "user": user
    }

