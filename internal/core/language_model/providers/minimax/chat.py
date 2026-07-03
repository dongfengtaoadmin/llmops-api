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
    """MiniMax OpenAI兼容聊天模型"""

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("api_key", os.getenv("MINIMAX_API_KEY"))
        kwargs.setdefault("base_url", os.getenv("MINIMAX_API_BASE") or "https://api.minimax.io/v1")

        super().__init__(**kwargs)
