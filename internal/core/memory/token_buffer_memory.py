#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/10/01 13:51
@Author  : thezehui@gmail.com
@File    : token_buffer_memory.py
"""
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AnyMessage, AIMessage, trim_messages, get_buffer_string
from sqlalchemy import desc

from internal.core.language_model.entities.model_entity import BaseLanguageModel
from internal.entity.conversation_entity import MessageStatus
from internal.model import Conversation, Message
from pkg.sqlalchemy import SQLAlchemy


@dataclass
class TokenBufferMemory:
    """基于token计数的缓冲记忆组件"""
    db: SQLAlchemy  # 数据库实例
    conversation: Conversation  # 会话模型
    model_instance: BaseLanguageModel  # LLM大语言模型

    @classmethod
    def _stringify_message_content(cls, content: Any) -> str:
        """将不同模型消息内容统一转成文本，避免依赖外部tokenizer。"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                cls._stringify_message_content(item.get("text", "") if isinstance(item, dict) else item)
                for item in content
            )
        return "" if content is None else str(content)

    @classmethod
    def _count_messages_tokens(cls, messages: list[AnyMessage]) -> int:
        """轻量估算消息token数，避免LangChain默认加载gpt2 tokenizer。"""
        text = "\n".join(cls._stringify_message_content(message.content) for message in messages)
        return max(1, len(text) // 4)

    def get_history_prompt_messages(
            self,
            max_token_limit: int = 2000,
            message_limit: int = 10,
    ) -> list[AnyMessage]:
        """根据传递的token限制+消息条数限制获取指定会话模型的历史消息列表"""
        # 1.判断会话模型是否存在，如果不存在则直接返回空列表
        if self.conversation is None:
            return []

        # 2.查询该会话的消息列表，并且使用时间进行倒序，同时匹配答案不为空、匹配会话id、没有软删除、状态是正常
        messages = self.db.session.query(Message).filter(
            Message.conversation_id == self.conversation.id,
            Message.answer != "",
            Message.is_deleted == False,
            Message.status.in_([MessageStatus.NORMAL, MessageStatus.STOP, MessageStatus.TIMEOUT]),
        ).order_by(desc("created_at")).limit(message_limit).all()
        messages = list(reversed(messages))

        # 3.将messages转换成LangChain消息列表
        prompt_messages = []
        for message in messages:
            prompt_messages.extend([
                self.model_instance.convert_to_human_message(message.query, message.image_urls),
                AIMessage(content=message.answer),
            ])
        # 4.调用LangChain继承的trim_messages函数剪切消息列表

        # 剪切前（2500 tokens）:
        # ├── 第1轮: "什么是AI" + "AI是..."
        # ├── 第2轮: "什么是机器学习" + "机器学习..."
        # ├── 第3轮: "什么是深度学习" + "深度学习..."  ← 从这里开始保留
        # ├── 第4轮: "什么是神经网络" + "神经网络..."
        # └── 第5轮: "什么是Transformer" + "Transformer..."

        # 剪切后（1500 tokens）:
        # ├── 第3轮: "什么是深度学习" + "深度学习..."
        # ├── 第4轮: "什么是神经网络" + "神经网络..."
        # └── 第5轮: "什么是Transformer" + "Transformer..."
        
        # 4.调用LangChain继承的trim_messages函数剪切消息列表
        return trim_messages(
            messages=prompt_messages,
            max_tokens=max_token_limit,
            token_counter=self._count_messages_tokens,
            strategy="last",
            start_on="human",
            end_on="ai",
        )

    def get_history_prompt_text(
            self,
            human_prefix: str = "Human",
            ai_prefix: str = "AI",
            max_token_limit: int = 2000,
            message_limit: int = 10,
    ) -> str:
        """根据传递的数据获取指定会话历史消息提示文本(短期记忆的文本形式，用于文本生成模型)"""
        # 1.根据传递的信息获取历史消息列表
        messages = self.get_history_prompt_messages(max_token_limit, message_limit)

        # 2.调用LangChain集成的get_buffer_string()函数将消息列表转换成文本
        return get_buffer_string(messages, human_prefix, ai_prefix)
