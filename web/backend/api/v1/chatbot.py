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
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

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


def _is_ecs_count_question(text: str) -> bool:
    """判断是否为「有几台ECS」类问题，这类问题直接查资源列表返回，不交给 LLM"""
    if not text or not text.strip():
        return False
    t = text.strip().lower()
    if "几台" not in t and "多少台" not in t and "几台服务器" not in t:
        return False
    return "ecs" in t or "服务器" in t or "实例" in t


def _get_ecs_count_answer(account_name: str) -> Optional[str]:
    """根据资源列表返回「有几台 ECS」的一句标准答案；无数据时返回 0 台提示。"""
    if not account_name:
        return None
    cache_manager = CacheManager(ttl_seconds=3600)
    cache_key = f"resource_list_{account_name}"
    instances_list = None
    raw = cache_manager.get(resource_type=cache_key, account_name=account_name)
    if raw and isinstance(raw, dict):
        instances_list = raw.get("instances") or []
    if not instances_list or len(instances_list) == 0:
        instances_list = cache_manager.get(resource_type="ecs_instances", account_name=account_name) or []
    total = len(instances_list) if instances_list else 0
    if total == 0:
        return "系统当前显示 0 台 ECS；若您实际有实例，请到仪表盘点击刷新后再问。"
    running = sum(
        1 for i in instances_list
        if isinstance(i, dict) and "RUNNING" in str(i.get("status", "")).upper()
    )
    stopped = sum(
        1 for i in instances_list
        if isinstance(i, dict) and "STOPPED" in str(i.get("status", "")).upper()
    )
    if running + stopped < total:
        stopped = total - running
    return f"您共有 {total} 台 ECS，其中 {running} 台运行中、{stopped} 台已停止。"


async def _get_user_context(account_id: Optional[str], account_name: Optional[str] = None) -> str:
    """获取丰富的用户数据上下文（用于构建系统提示词）"""
    if not account_name:
        return "用户没有配置云账号，无法获取成本数据。"

    context_parts = []
    cache_manager = CacheManager(ttl_seconds=3600)  # 1小时缓存

    # 【优先】ECS 服务器统计（来自资源列表）：放在最前，回答「有几台ECS」时只认这个
    try:
        cache_key = f"resource_list_{account_name}"
        instances_list = None
        raw = cache_manager.get(resource_type=cache_key, account_name=account_name)
        if raw and isinstance(raw, dict):
            instances_list = raw.get("instances") or []
        if not instances_list or len(instances_list) == 0:
            instances_list = cache_manager.get(resource_type="ecs_instances", account_name=account_name) or []
        if instances_list and len(instances_list) > 0:
            total_instances = len(instances_list)
            running = sum(1 for i in instances_list if isinstance(i, dict) and "RUNNING" in str(i.get("status", "")).upper())
            stopped = sum(1 for i in instances_list if isinstance(i, dict) and "STOPPED" in str(i.get("status", "")).upper())
            if running + stopped < total_instances:
                stopped = total_instances - running
            region_count = {}
            spec_count = {}
            for inst in instances_list:
                if isinstance(inst, dict):
                    region = inst.get("region", "未知")
                    spec = inst.get("spec", "未知")
                    region_count[region] = region_count.get(region, 0) + 1
                    spec_count[spec] = spec_count.get(spec, 0) + 1
            context_parts.append("""【用户问「有几台ECS」时请直接使用下面数字回答，不要用账单或成本推断】

=== ECS 服务器统计（按资源列表） ===
""")
            context_parts.append(f"共 {total_instances} 台：运行中 {running} 台，已停止 {stopped} 台\n")
            context_parts.append("区域分布 (Top 5):")
            for region, count in sorted(region_count.items(), key=lambda x: x[1], reverse=True)[:5]:
                context_parts.append(f"- {region}: {count}台")
            context_parts.append("\n规格分布 (Top 5):")
            for spec, count in sorted(spec_count.items(), key=lambda x: x[1], reverse=True)[:5]:
                context_parts.append(f"- {spec}: {count}台")
        else:
            # 无资源列表时也写明，避免模型用「成本为0」推断成「0台实例」
            context_parts.append("""【用户问「有几台ECS」时请只按本段回答，不要用账单推断】

=== ECS 服务器统计（按资源列表） ===
当前无资源列表数据，显示 0 台。若用户实际有实例，请建议其到仪表盘点击刷新后再问。
""")
    except Exception as e:
        logger.warning(f"获取 ECS 资源列表失败: {str(e)}")

    try:
        # 1. 从 dashboard_summary 缓存获取核心数据
        summary = cache_manager.get(resource_type="dashboard_summary", account_name=account_name)
        # 无缓存或资源数全为 0 时尝试刷新一次，确保 AI 能基于系统数据回答（如「有几台 ECS」）
        need_refresh = not summary or not isinstance(summary, dict)
        if not need_refresh and summary.get("resource_breakdown"):
            rb = summary.get("resource_breakdown", {})
            if (rb.get("ecs", 0) == 0 and rb.get("rds", 0) == 0 and rb.get("redis", 0) == 0):
                need_refresh = True
        if need_refresh and account_name:
            account_config = ConfigManager().get_account(account_name)
            if account_config:
                try:
                    from web.backend.api_service import _update_dashboard_summary_cache
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            _update_dashboard_summary_cache, account_name, account_config, True
                        )
                        future.result(timeout=25)
                    summary = cache_manager.get(resource_type="dashboard_summary", account_name=account_name)
                except (FuturesTimeoutError, Exception) as e:
                    logger.warning(f"刷新仪表盘摘要失败或超时: {e}")
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
                if res_type == "ecs" and (summary.get("ecs_running") is not None or summary.get("ecs_stopped") is not None):
                    run = summary.get("ecs_running", 0)
                    stop = summary.get("ecs_stopped", 0)
                    context_parts.append(f"- ECS: {count}台（运行中 {run} 台，已停止 {stop} 台）")
                else:
                    context_parts.append(f"- {res_type.upper()}: {count}台")
            if resource_breakdown.get("ecs") == 0:
                context_parts.append("(若用户表示实际有 ECS 但此处为 0，可能是包年包月未在当月体现或资源扫描未覆盖，请建议用户在仪表盘点击刷新或以控制台为准。)")
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
    
    # ECS 服务器统计已放在上下文最前，此处不再重复
    
    if not context_parts:
        return f"账号 {account_name} 暂无可用数据。"
    
    return "\n".join(context_parts)


def _build_system_prompt(context: str) -> str:
    """构建系统提示词"""
    return f"""你是一个专业的云成本管理助手，名为CloudLens AI。你的职责是帮助用户分析和优化云资源成本。

【重要】以下数据来自 CloudLens 系统当前账号的实时/缓存数据，请务必优先基于这些数据直接回答用户问题：
{context}

回答原则：
1. 用中文回答，语气友好且专业。
2. 当上下文中已有具体数字时，必须直接引用回答，不要泛泛地说「请去控制台查看」。
3. 仅当上下文明确标注「暂无」「获取失败」或「暂无可用数据」时，才建议用户去控制台或刷新后重试。
4. 建议要具体、可操作；若数据不足，可简短说明并给出下一步建议。

【重要】当用户问「有几台ECS」「几台服务器」时：
- 必须仅根据上下文中的「ECS 服务器统计」或「资源分布」里的 ECS 数量，用一句话直接回答，例如：「您共有 7 台 ECS，其中 X 台运行中、Y 台已停止。」
- 禁止用「本月ECS成本」或账单推断实例数量——成本为 0 可能是包年包月或已关机，不代表 0 台实例。
- 若资源数据为 0 台，只回复一句：「系统当前显示 0 台；若您实际有实例，请到仪表盘点击刷新后再问。」不要展开成本分析，不要问用户是否关机/释放。

你可以帮助用户：
- 直接回答资源数量（有几台 ECS 等）、成本金额、趋势与分布
- 分析成本变化原因、识别闲置资源、提供优化建议
- 解释账单明细、预测未来成本
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
        
        # 「有几台 ECS」类问题：直接查资源列表返回一句答案，不交给 LLM，避免被成本数据带偏
        last_user_content = (req.messages[-1].content if req.messages else "").strip()
        if last_user_content and _is_ecs_count_question(last_user_content) and account_name:
            direct_answer = _get_ecs_count_answer(account_name)
            if direct_answer:
                for msg in req.messages:
                    _get_db().execute(
                        "INSERT INTO chat_messages (id, session_id, role, content, created_at) VALUES (%s, %s, %s, %s, NOW())",
                        (str(uuid.uuid4()), session_id, msg.role, msg.content)
                    )
                _get_db().execute(
                    "INSERT INTO chat_messages (id, session_id, role, content, metadata, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
                    (str(uuid.uuid4()), session_id, "assistant", direct_answer, json.dumps({"usage": {"prompt_tokens": 0, "completion_tokens": 0}, "model": "cloudlens-resource"}))
                )
                return ChatResponse(
                    message=direct_answer,
                    session_id=session_id,
                    usage={"prompt_tokens": 0, "completion_tokens": 0},
                    model="cloudlens-resource",
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
