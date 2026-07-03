#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : chat.py
"""
import os
from typing import Any

from langchain_anthropic import ChatAnthropic

from internal.core.language_model.entities.model_entity import BaseLanguageModel


class Chat(ChatAnthropic, BaseLanguageModel):
    """Anthropic协议兼容聊天模型"""

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("api_key", os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY"))
        kwargs.setdefault("base_url", os.getenv("ANTHROPIC_BASE_URL") or os.getenv("ANTHROPIC_API_BASE"))

        # Anthropic协议不支持OpenAI的惩罚参数，前端复用默认参数时需要过滤掉。
        kwargs.pop("presence_penalty", None)
        kwargs.pop("frequency_penalty", None)

        super().__init__(**kwargs)
