#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM客户端封装
支持Claude和OpenAI API
"""

import os
import logging
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """LLM客户端抽象基类"""
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示词
            temperature: 温度参数（0-1）
            max_tokens: 最大token数
            
        Returns:
            包含message和usage信息的字典
        """
        pass


class ClaudeClient(LLMClient):
    """Claude API客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化Claude客户端
        
        Args:
            api_key: Anthropic API密钥，如果为None则从环境变量读取
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY环境变量未设置")
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.model = "claude-3-5-sonnet-20241022"  # 使用最新版本
        except ImportError:
            raise ImportError("请安装anthropic包: pip install anthropic")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """发送聊天请求到Claude API"""
        try:
            # 转换消息格式（Claude使用不同的格式）
            claude_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    # Claude不支持system角色，需要合并到system_prompt
                    if system_prompt:
                        system_prompt = f"{system_prompt}\n\n{msg['content']}"
                    else:
                        system_prompt = msg["content"]
                else:
                    claude_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # 调用API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=claude_messages
            )
            
            # 提取响应内容
            message_content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        message_content += block.text
            
            return {
                "message": message_content,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                "model": self.model
            }
        except Exception as e:
            logger.error(f"Claude API调用失败: {str(e)}")
            raise


class OpenAIClient(LLMClient):
    """OpenAI API客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化OpenAI客户端
        
        Args:
            api_key: OpenAI API密钥，如果为None则从环境变量读取
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY环境变量未设置")
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            self.model = "gpt-4"  # 使用GPT-4
        except ImportError:
            raise ImportError("请安装openai包: pip install openai")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """发送聊天请求到OpenAI API"""
        try:
            # 构建消息列表
            openai_messages = []
            if system_prompt:
                openai_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            for msg in messages:
                if msg["role"] != "system":  # OpenAI支持system角色
                    openai_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # 调用API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return {
                "message": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "model": self.model
            }
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {str(e)}")
            raise


def create_llm_client(provider: str = "claude") -> LLMClient:
    """
    创建LLM客户端
    
    Args:
        provider: 提供商名称（"claude" 或 "openai"）
        
    Returns:
        LLMClient实例
    """
    provider = provider.lower()
    if provider == "claude":
        return ClaudeClient()
    elif provider == "openai":
        return OpenAIClient()
    else:
        raise ValueError(f"不支持的LLM提供商: {provider}")
