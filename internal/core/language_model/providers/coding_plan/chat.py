#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : chat.py
"""
import os
from typing import Any

from langchain_openai import ChatOpenAI

from internal.core.language_model.entities.model_entity import BaseLanguageModel


class Chat(ChatOpenAI, BaseLanguageModel):
    """腾讯云Coding Plan OpenAI兼容聊天模型"""

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("api_key", os.getenv("CODING_PLAN_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))
        kwargs.setdefault("base_url", os.getenv("CODING_PLAN_API_BASE") or "https://api.lkeap.cloud.tencent.com/coding/v3")

        super().__init__(**kwargs)
