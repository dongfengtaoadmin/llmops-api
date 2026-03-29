#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
无问芯穹（Infini-AI）OpenAI 兼容接口 + LangChain 基础对话示例。

在 .env 中配置：
  KEYI_API_KEY=你的密钥

运行前请确保项目根目录的 .env 能被 load_dotenv 找到（本脚本从 study 子目录运行时
会向上查找，也可在 IDE 里将工作目录设为项目根）。
"""

import os
from pathlib import Path

import dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# 从项目根目录加载 .env（与 study 脚本常见写法一致）
_root = Path(__file__).resolve().parents[2]
dotenv.load_dotenv(_root / ".env")

KEYI_API_KEY = os.getenv("KEYI_API_KEY")
if not KEYI_API_KEY:
    raise RuntimeError("请在 .env 中设置 KEYI_API_KEY（无问芯穹密钥）")

llm = ChatOpenAI(
    model="deepseek-r1",
    api_key=KEYI_API_KEY,
    base_url="https://cloud.infini-ai.com/maas/v1",
)

if __name__ == "__main__":
    messages = [
        SystemMessage(content="你是一个简洁、有帮助的中文助手。"),
        HumanMessage(content="用一句话介绍你自己。"),
    ]
    reply: AIMessage = llm.invoke(messages)
    print(reply.content)
