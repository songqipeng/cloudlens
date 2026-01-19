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
from cloudlens.core.llm_client import create_llm_client, LLMClient
from cloudlens.core.database import DatabaseFactory
from cloudlens.core.config import ConfigManager
from cloudlens.core.context import ContextManager
from cloudlens.core.bill_storage import BillStorageManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chatbot", tags=["chatbot"])

# 初始化LLM客户端
_llm_client: Optional[LLMClient] = None
_db = DatabaseFactory.create_adapter("mysql")
_bill_storage = BillStorageManager()


def get_llm_client() -> LLMClient:
    """获取LLM客户端（懒加载）"""
    global _llm_client
    if _llm_client is None:
        provider = os.getenv("LLM_PROVIDER", "claude").lower()
        try:
            _llm_client = create_llm_client(provider)
            logger.info(f"LLM客户端初始化成功: {provider}")
        except Exception as e:
            logger.error(f"LLM客户端初始化失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"AI服务不可用: {str(e)}"
            )
    return _llm_client


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
        items = _bill_storage.get_bill_items(
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
            _db.execute(
                "INSERT INTO chat_sessions (id, account_id, title, created_at) VALUES (%s, %s, %s, NOW())",
                (session_id, account_id, "新对话")
            )
        
        # 获取用户上下文
        context = await _get_user_context(account_id)
        system_prompt = _build_system_prompt(context)
        
        # 获取历史消息（如果有session_id）
        history_messages = []
        if session_id:
            history = _db.query(
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
        
        # 调用LLM
        llm = get_llm_client()
        result = await llm.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=req.temperature,
            max_tokens=req.max_tokens
        )
        
        # 保存用户消息
        for msg in req.messages:
            _db.execute(
                "INSERT INTO chat_messages (id, session_id, role, content, created_at) VALUES (%s, %s, %s, %s, NOW())",
                (str(uuid.uuid4()), session_id, msg.role, msg.content)
            )
        
        # 保存AI回复
        message_id = str(uuid.uuid4())
        metadata = {
            "usage": result["usage"],
            "model": result["model"]
        }
        _db.execute(
            "INSERT INTO chat_messages (id, session_id, role, content, metadata, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
            (message_id, session_id, "assistant", result["message"], str(metadata))
        )
        
        # 更新会话标题（如果是第一条消息）
        if len(history_messages) == 0 and req.messages:
            first_message = req.messages[0].content[:50]
            _db.execute(
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
        
        sessions = _db.query(query, tuple(params))
        
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
        messages = _db.query(
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
        _db.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
        return {
            "success": True,
            "message": "会话删除成功"
        }
    except Exception as e:
        raise handle_api_error(e, "delete_session")
