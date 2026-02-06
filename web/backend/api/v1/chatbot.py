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
from datetime import datetime, timedelta
import uuid
import json
import os

from web.backend.api_base import handle_api_error
from cloudlens.core.llm_client import create_llm_client, LLMClient, ClaudeClient, OpenAIClient, DeepSeekClient
from cloudlens.core.database import DatabaseFactory
from cloudlens.core.config import ConfigManager
from cloudlens.core.context import ContextManager
from cloudlens.core.bill_storage import BillStorageManager
from cloudlens.core.encryption import get_encryption
from cloudlens.core.cache import CacheManager

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


async def _get_user_context(account_id: Optional[str], account_name: Optional[str] = None) -> str:
    """获取丰富的用户数据上下文（用于构建系统提示词）"""
    if not account_name:
        return "用户没有配置云账号，无法获取成本数据。"
    
    context_parts = []
    cache_manager = CacheManager(ttl_seconds=3600)  # 1小时缓存
    
    try:
        # 1. 从 dashboard_summary 缓存获取核心数据
        summary = cache_manager.get(resource_type="dashboard_summary", account_name=account_name)
        if summary and isinstance(summary, dict):
            total_cost = summary.get("total_cost", 0)
            trend_pct = summary.get("trend_pct", 0)
            cost_trend = summary.get("cost_trend", "")
            idle_count = summary.get("idle_count", 0)
            total_resources = summary.get("total_resources", 0)
            savings_potential = summary.get("savings_potential", 0)
            resource_breakdown = summary.get("resource_breakdown", {})
            
            context_parts.append(f"""
=== 账号概览 ===
账号: {account_name}
本月总成本: ¥{total_cost:,.2f}
成本趋势: {cost_trend} {trend_pct:.1f}%
总资源数: {total_resources}
闲置资源数: {idle_count}
潜在节省: ¥{savings_potential:,.2f}/月

资源分布:""")
            for res_type, count in resource_breakdown.items():
                context_parts.append(f"- {res_type.upper()}: {count}台")
        else:
            context_parts.append(f"账号 {account_name} 暂无仪表盘摘要数据。")
            
    except Exception as e:
        logger.warning(f"获取仪表盘摘要失败: {str(e)}")
        context_parts.append(f"仪表盘数据获取失败: {str(e)}")
    
    try:
        # 2. 从 optimization_suggestions 缓存获取闲置资源详情
        opt_data = cache_manager.get(resource_type="optimization_suggestions", account_name=account_name)
        if opt_data and isinstance(opt_data, dict):
            suggestions = opt_data.get("suggestions", [])
            summary_info = opt_data.get("summary", {})
            
            # 找到闲置资源类型的建议
            idle_suggestion = None
            for s in suggestions:
                if isinstance(s, dict) and s.get("type") == "idle_resources":
                    idle_suggestion = s
                    break
            
            if idle_suggestion:
                resources = idle_suggestion.get("resources", [])
                context_parts.append(f"""
=== 闲置资源详情 ===
共检测到 {len(resources)} 个闲置资源
优化建议优先级: {idle_suggestion.get('priority', 'N/A')}

闲置资源列表 (Top 15):""")
                for res in resources[:15]:
                    if isinstance(res, dict):
                        name = res.get('name', 'N/A')
                        spec = res.get('spec', 'N/A')
                        region = res.get('region', 'N/A')
                        reasons = res.get('reasons', [])
                        reason_str = "; ".join(reasons) if reasons else "低利用率"
                        context_parts.append(f"- {name} ({spec}) @ {region}: {reason_str}")
            else:
                context_parts.append("\n=== 闲置资源 ===\n暂无闲置资源检测数据")
                
    except Exception as e:
        logger.warning(f"获取优化建议失败: {str(e)}")
    
    try:
        # 3. 获取详细成本分解数据（用于根因分析）
        cost_breakdown = cache_manager.get(resource_type="cost_breakdown", account_name=account_name)
        if cost_breakdown and isinstance(cost_breakdown, dict):
            categories = cost_breakdown.get("categories", [])
            billing_cycle = cost_breakdown.get("billing_cycle", "")
            
            context_parts.append(f"""
=== 本月成本明细 ({billing_cycle}) ===
按产品分类的成本 (Top 15):""")
            for cat in categories[:15]:
                if isinstance(cat, dict):
                    code = cat.get("code", "")
                    name = cat.get("name", code)
                    amount = cat.get("amount", 0)
                    sub = cat.get("subscription", {})
                    pay_type = "包年包月" if sub.get("Subscription", 0) > sub.get("PayAsYouGo", 0) else "按量付费"
                    context_parts.append(f"- {name}: ¥{amount:,.2f} ({pay_type})")
    except Exception as e:
        logger.warning(f"获取成本分解失败: {str(e)}")
    
    try:
        # 4. 获取上月账单数据进行对比分析
        now = datetime.now()
        current_month = now.strftime("%Y-%m")
        last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        
        current_billing = cache_manager.get(resource_type=f"billing_overview_totals_{current_month}", account_name=account_name)
        last_billing = cache_manager.get(resource_type=f"billing_overview_totals_{last_month}", account_name=account_name)
        
        if current_billing and last_billing:
            # 处理可能是列表的情况
            curr_data = current_billing[0] if isinstance(current_billing, list) else current_billing
            last_data = last_billing[0] if isinstance(last_billing, list) else last_billing
            
            curr_by_product = curr_data.get("by_product", {})
            last_by_product = last_data.get("by_product", {})
            curr_total = curr_data.get("total_pretax", 0)
            last_total = last_data.get("total_pretax", 0)
            
            # 计算每个产品的变化
            changes = []
            all_products = set(curr_by_product.keys()) | set(last_by_product.keys())
            for product in all_products:
                curr_cost = curr_by_product.get(product, 0)
                last_cost = last_by_product.get(product, 0)
                diff = curr_cost - last_cost
                if abs(diff) > 100:  # 只关注变化超过100元的
                    pct = (diff / last_cost * 100) if last_cost > 0 else 100
                    changes.append({
                        "product": product,
                        "curr": curr_cost,
                        "last": last_cost,
                        "diff": diff,
                        "pct": pct
                    })
            
            # 按变化金额排序
            changes.sort(key=lambda x: abs(x["diff"]), reverse=True)
            
            context_parts.append(f"""
=== 成本环比分析 ===
本月 ({current_month}): ¥{curr_total:,.2f}
上月 ({last_month}): ¥{last_total:,.2f}
变化: ¥{curr_total - last_total:,.2f} ({((curr_total - last_total) / last_total * 100) if last_total > 0 else 0:.1f}%)

成本变化最大的产品 (Top 10):""")
            for c in changes[:10]:
                direction = "↑" if c["diff"] > 0 else "↓"
                context_parts.append(f"- {c['product']}: ¥{c['last']:,.2f} → ¥{c['curr']:,.2f} ({direction}¥{abs(c['diff']):,.2f}, {c['pct']:+.1f}%)")
            
            # 新增的产品
            new_products = [p for p in curr_by_product if p not in last_by_product and curr_by_product[p] > 100]
            if new_products:
                context_parts.append("\n本月新增产品:")
                for p in new_products[:5]:
                    context_parts.append(f"- {p}: ¥{curr_by_product[p]:,.2f}")
    except Exception as e:
        logger.warning(f"获取账单对比数据失败: {str(e)}")
    
    try:
        # 5. 获取实例统计（从 ecs_instances 缓存）
        instances_cache = cache_manager.get(resource_type="ecs_instances", account_name=account_name)
        if instances_cache and isinstance(instances_cache, list) and len(instances_cache) > 0:
            total_instances = len(instances_cache)
            running = sum(1 for i in instances_cache if isinstance(i, dict) and str(i.get('status', '')).upper() == 'RUNNING')
            stopped = total_instances - running
            
            # 区域分布
            region_count = {}
            spec_count = {}
            for inst in instances_cache:
                if isinstance(inst, dict):
                    region = inst.get('region', '未知')
                    spec = inst.get('spec', '未知')
                    region_count[region] = region_count.get(region, 0) + 1
                    spec_count[spec] = spec_count.get(spec, 0) + 1
            
            context_parts.append(f"""
=== ECS实例统计 ===
总实例数: {total_instances}
运行中: {running}, 已停止: {stopped}

区域分布 (Top 5):""")
            for region, count in sorted(region_count.items(), key=lambda x: x[1], reverse=True)[:5]:
                context_parts.append(f"- {region}: {count}台")
            
            context_parts.append("\n规格分布 (Top 5):")
            for spec, count in sorted(spec_count.items(), key=lambda x: x[1], reverse=True)[:5]:
                context_parts.append(f"- {spec}: {count}台")
    except Exception as e:
        logger.warning(f"获取实例数据失败: {str(e)}")
    
    if not context_parts:
        return f"账号 {account_name} 暂无可用数据。"
    
    return "\n".join(context_parts)


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
async def chat(
    req: ChatRequest,
    account: Optional[str] = Query(None, description="账号名称（URL参数）")
) -> ChatResponse:
    """发送聊天消息"""
    try:
        # 优先使用 URL query param，其次使用 request body
        account_name = account or req.account
        
        # 获取账号ID
        account_id = _get_account_id(account_name)
        
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
        context = await _get_user_context(account_id, account_name)
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
        import json
        _get_db().execute(
            "INSERT INTO chat_messages (id, session_id, role, content, metadata, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
            (message_id, session_id, "assistant", result["message"], json.dumps(metadata))
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
        import traceback
        logger.error(f"聊天请求失败: {str(e)}\n{traceback.format_exc()}")
        # 返回更详细的错误信息
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            detail = "AI服务响应超时，请稍后重试"
        elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
            detail = "请求频率过高，请稍后重试"
        elif "api" in error_msg.lower() or "key" in error_msg.lower():
            detail = f"API调用失败: {error_msg}"
        elif "connect" in error_msg.lower() or "network" in error_msg.lower():
            detail = "网络连接错误，请检查网络状态"
        else:
            detail = f"服务异常: {error_msg}"
        raise HTTPException(status_code=500, detail=detail)


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
