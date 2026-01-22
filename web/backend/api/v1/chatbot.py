#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Chatbot API模块
提供自然语言问答能力
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging
from pydantic import BaseModel
from datetime import datetime
import uuid
import os

from web.backend.api_base import handle_api_error
from cloudlens.core.llm_client import create_llm_client, LLMClient, ClaudeClient, OpenAIClient, DeepSeekClient
from cloudlens.core.database import DatabaseFactory
from cloudlens.core.config import ConfigManager
from cloudlens.core.context import ContextManager
from cloudlens.core.bill_storage import BillStorageManager
from cloudlens.core.encryption import get_encryption

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chatbot", tags=["chatbot"])

# 初始化LLM客户端
_llm_clients: Dict[str, LLMClient] = {}  # 缓存每个provider的客户端
_db: Optional[Any] = None  # 延迟初始化，避免导入时连接MySQL
_bill_storage: Optional[BillStorageManager] = None  # 延迟初始化


def get_llm_client(provider: str = "claude", api_key: Optional[str] = None) -> LLMClient:
    """获取LLM客户端（懒加载）"""
    global _llm_clients

    # 如果提供了api_key，直接创建新客户端
    if api_key:
        try:
            if provider == "claude":
                return ClaudeClient(api_key=api_key)
            elif provider == "openai":
                return OpenAIClient(api_key=api_key)
            elif provider == "deepseek":
                return DeepSeekClient(api_key=api_key)
            else:
                raise ValueError(f"不支持的LLM提供商: {provider}")
        except Exception as e:
            logger.error(f"LLM客户端初始化失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"AI服务不可用: {str(e)}"
            )

    # 否则尝试从数据库获取API key
    try:
        db = _get_db()
        config = db.query(
            "SELECT api_key_encrypted FROM llm_configs WHERE provider = %s AND is_active = TRUE LIMIT 1",
            (provider,)
        )

        if config and config[0].get("api_key_encrypted"):
            # 解密API key
            encryption = get_encryption()
            decrypted_key = encryption.decrypt(config[0]["api_key_encrypted"])

            # 创建并缓存客户端
            if provider not in _llm_clients:
                if provider == "claude":
                    _llm_clients[provider] = ClaudeClient(api_key=decrypted_key)
                elif provider == "openai":
                    _llm_clients[provider] = OpenAIClient(api_key=decrypted_key)
                elif provider == "deepseek":
                    _llm_clients[provider] = DeepSeekClient(api_key=decrypted_key)
                logger.info(f"LLM客户端初始化成功: {provider}")

            return _llm_clients[provider]
        else:
            raise HTTPException(
                status_code=400,
                detail=f"未配置 {provider} 的API密钥，请在设置中配置"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM客户端初始化失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"AI服务不可用: {str(e)}"
        )


def _get_db():
    """获取数据库适配器（懒加载）"""
    global _db
    if _db is None:
        _db = DatabaseFactory.create_adapter("mysql")
    return _db


def _get_bill_storage() -> BillStorageManager:
    """获取账单存储管理器（懒加载）"""
    global _bill_storage
    if _bill_storage is None:
        _bill_storage = BillStorageManager()
    return _bill_storage


# ==================== 请求模型 ====================

class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str  # user/assistant/system
    content: str


class ChatRequest(BaseModel):
    """聊天请求模型"""
    messages: List[ChatMessage]
    session_id: Optional[str] = None
    account: Optional[str] = None
    provider: Optional[str] = "claude"  # LLM提供商
    temperature: float = 0.7
    max_tokens: int = 2000


class ChatResponse(BaseModel):
    """聊天响应模型"""
    message: str
    session_id: str
    usage: Dict[str, int]
    model: str


# ==================== 辅助函数 ====================

def _get_account_id(account: Optional[str] = None) -> Optional[str]:
    """获取格式化的账号ID"""
    cm = ConfigManager()
    if not account:
        ctx = ContextManager()
        account = ctx.get_last_account()
    
    if not account:
        return None
        
    account_config = cm.get_account(account)
    if account_config:
        return f"{account_config.access_key_id[:10]}-{account}"
    return None


async def _get_user_context(account_id: Optional[str]) -> str:
    """获取用户成本上下文（用于构建系统提示词）"""
    if not account_id:
        return "用户没有配置云账号。"
    
    try:
        # 获取最近一个月的成本数据
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # 获取账单数据
        billing_cycle = end_date.strftime("%Y-%m")
        items = _get_bill_storage().get_bill_items(
            account_id=account_id,
            billing_cycle=billing_cycle
        )
        
        if not items:
            return f"账号 {account_id} 最近一个月没有账单数据。"
        
        # 计算总成本
        total_cost = sum(float(item.get("payment_amount", 0) or 0) for item in items)
        
        # 按产品分类统计
        product_costs = {}
        for item in items:
            product = item.get("product_name", "未知产品")
            cost = float(item.get("payment_amount", 0) or 0)
            product_costs[product] = product_costs.get(product, 0) + cost
        
        # 构建上下文
        context = f"""
账号ID: {account_id}
最近一个月（{billing_cycle}）总成本: ¥{total_cost:.2f}

主要产品成本分布:
"""
        for product, cost in sorted(product_costs.items(), key=lambda x: x[1], reverse=True)[:10]:
            context += f"- {product}: ¥{cost:.2f}\n"
        
        return context
    except Exception as e:
        logger.warning(f"获取用户上下文失败: {str(e)}")
        return f"无法获取账号 {account_id} 的成本数据。"


def _build_system_prompt(context: str) -> str:
    """构建系统提示词"""
    return f"""你是一个专业的云成本管理助手，名为CloudLens AI。你的职责是帮助用户分析和优化云资源成本。

用户当前的云成本情况：
{context}

请遵循以下原则：
1. 用中文回答所有问题
2. 提供准确、专业的成本分析建议
3. 如果数据不足，明确告知用户
4. 建议要具体、可操作
5. 使用友好的语气，但保持专业性

你可以帮助用户：
- 分析成本变化原因
- 识别闲置资源
- 提供优化建议
- 解释账单明细
- 预测未来成本
"""


# ==================== API端点 ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """发送聊天消息"""
    try:
        # 获取账号ID
        account_id = _get_account_id(req.account)
        
        # 获取或创建会话ID
        session_id = req.session_id
        if not session_id:
            session_id = str(uuid.uuid4())
            # 创建新会话
            _get_db().execute(
                "INSERT INTO chat_sessions (id, account_id, title, created_at) VALUES (%s, %s, %s, NOW())",
                (session_id, account_id, "新对话")
            )
        
        # 获取用户上下文
        context = await _get_user_context(account_id)
        system_prompt = _build_system_prompt(context)
        
        # 获取历史消息（如果有session_id）
        history_messages = []
        if session_id:
            history = _get_db().query(
                "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC LIMIT 20",
                (session_id,)
            )
            for msg in history:
                history_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # 添加当前用户消息
        messages = history_messages + [
            {"role": msg.role, "content": msg.content}
            for msg in req.messages
        ]
        
        # 调用LLM（使用请求指定的provider）
        llm = get_llm_client(provider=req.provider or "claude")
        result = await llm.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=req.temperature,
            max_tokens=req.max_tokens
        )
        
        # 保存用户消息
        for msg in req.messages:
            _get_db().execute(
                "INSERT INTO chat_messages (id, session_id, role, content, created_at) VALUES (%s, %s, %s, %s, NOW())",
                (str(uuid.uuid4()), session_id, msg.role, msg.content)
            )
        
        # 保存AI回复
        message_id = str(uuid.uuid4())
        metadata = {
            "usage": result["usage"],
            "model": result["model"]
        }
        _get_db().execute(
            "INSERT INTO chat_messages (id, session_id, role, content, metadata, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
            (message_id, session_id, "assistant", result["message"], str(metadata))
        )
        
        # 更新会话标题（如果是第一条消息）
        if len(history_messages) == 0 and req.messages:
            first_message = req.messages[0].content[:50]
            _get_db().execute(
                "UPDATE chat_sessions SET title = %s WHERE id = %s",
                (first_message, session_id)
            )
        
        return ChatResponse(
            message=result["message"],
            session_id=session_id,
            usage=result["usage"],
            model=result["model"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天请求失败: {str(e)}")
        raise handle_api_error(e, "chat")


@router.get("/sessions")
def list_sessions(
    account: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """获取会话列表"""
    try:
        account_id = _get_account_id(account)
        
        query = "SELECT id, title, account_id, created_at, updated_at FROM chat_sessions"
        params = []
        
        if account_id:
            query += " WHERE account_id = %s"
            params.append(account_id)
        
        query += " ORDER BY updated_at DESC LIMIT %s"
        params.append(limit)
        
        sessions = _get_db().query(query, tuple(params))
        
        return {
            "success": True,
            "data": [
                {
                    "id": s["id"],
                    "title": s["title"],
                    "account_id": s["account_id"],
                    "created_at": s["created_at"].isoformat() if isinstance(s["created_at"], datetime) else s["created_at"],
                    "updated_at": s["updated_at"].isoformat() if isinstance(s["updated_at"], datetime) else s["updated_at"]
                }
                for s in sessions
            ],
            "count": len(sessions)
        }
    except Exception as e:
        raise handle_api_error(e, "list_sessions")


@router.get("/sessions/{session_id}/messages")
def get_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """获取会话消息"""
    try:
        messages = _get_db().query(
            "SELECT id, role, content, metadata, created_at FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC LIMIT %s",
            (session_id, limit)
        )
        
        return {
            "success": True,
            "data": [
                {
                    "id": m["id"],
                    "role": m["role"],
                    "content": m["content"],
                    "metadata": m.get("metadata"),
                    "created_at": m["created_at"].isoformat() if isinstance(m["created_at"], datetime) else m["created_at"]
                }
                for m in messages
            ],
            "count": len(messages)
        }
    except Exception as e:
        raise handle_api_error(e, "get_messages")


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> Dict[str, Any]:
    """删除会话（级联删除消息）"""
    try:
        _get_db().execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
        return {
            "success": True,
            "message": "会话删除成功"
        }
    except Exception as e:
        raise handle_api_error(e, "delete_session")


# ==================== LLM配置管理 ====================

class LLMConfigRequest(BaseModel):
    """LLM配置请求模型"""
    provider: str  # claude, openai, deepseek
    api_key: str
    is_active: bool = True


class LLMConfigResponse(BaseModel):
    """LLM配置响应模型"""
    provider: str
    has_api_key: bool  # 是否已配置API key（不返回实际key）
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("/configs", response_model=List[LLMConfigResponse])
def get_llm_configs() -> List[LLMConfigResponse]:
    """获取所有LLM配置（不返回实际API key）"""
    try:
        db = _get_db()
        configs = db.query(
            "SELECT provider, api_key_encrypted, is_active, created_at, updated_at FROM llm_configs ORDER BY provider"
        )

        result = []
        for config in configs:
            result.append(LLMConfigResponse(
                provider=config["provider"],
                has_api_key=bool(config["api_key_encrypted"]),
                is_active=config["is_active"],
                created_at=config["created_at"].isoformat() if isinstance(config["created_at"], datetime) else config["created_at"],
                updated_at=config["updated_at"].isoformat() if isinstance(config["updated_at"], datetime) else config["updated_at"]
            ))

        return result
    except Exception as e:
        raise handle_api_error(e, "get_llm_configs")


@router.post("/configs")
def save_llm_config(req: LLMConfigRequest) -> Dict[str, Any]:
    """保存或更新LLM配置"""
    try:
        # 验证provider
        if req.provider not in ["claude", "openai", "deepseek"]:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的LLM提供商: {req.provider}，支持的选项: claude, openai, deepseek"
            )

        # 加密API key
        encryption = get_encryption()
        encrypted_key = encryption.encrypt(req.api_key)

        db = _get_db()

        # 检查配置是否已存在
        existing = db.query(
            "SELECT provider FROM llm_configs WHERE provider = %s LIMIT 1",
            (req.provider,)
        )

        if existing:
            # 更新现有配置
            db.execute(
                "UPDATE llm_configs SET api_key_encrypted = %s, is_active = %s, updated_at = NOW() WHERE provider = %s",
                (encrypted_key, req.is_active, req.provider)
            )
            logger.info(f"更新LLM配置: {req.provider}")
        else:
            # 插入新配置
            db.execute(
                "INSERT INTO llm_configs (provider, api_key_encrypted, is_active, created_at, updated_at) VALUES (%s, %s, %s, NOW(), NOW())",
                (req.provider, encrypted_key, req.is_active)
            )
            logger.info(f"保存LLM配置: {req.provider}")

        # 清除缓存的客户端，强制下次重新加载
        global _llm_clients
        if req.provider in _llm_clients:
            del _llm_clients[req.provider]

        return {
            "success": True,
            "message": f"{req.provider} 配置已保存"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存LLM配置失败: {str(e)}")
        raise handle_api_error(e, "save_llm_config")


@router.delete("/configs/{provider}")
def delete_llm_config(provider: str) -> Dict[str, Any]:
    """删除LLM配置"""
    try:
        db = _get_db()
        db.execute("DELETE FROM llm_configs WHERE provider = %s", (provider,))

        # 清除缓存的客户端
        global _llm_clients
        if provider in _llm_clients:
            del _llm_clients[provider]

        logger.info(f"删除LLM配置: {provider}")
        return {
            "success": True,
            "message": f"{provider} 配置已删除"
        }
    except Exception as e:
        raise handle_api_error(e, "delete_llm_config")
