#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/12 10:17
@Author  : thezehui@gmail.com
@File    : 2.回退处理策略.py
"""
import dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()


@tool
def complex_tool(int_arg: int, float_arg: float, dict_arg: dict) -> int:
    """使用复杂工具进行复杂计算操作"""
    return int_arg * float_arg


# 1.创建大语言模型并绑定工具
llm = ChatOpenAI(model="gpt-4o-mini").bind_tools([complex_tool])
better_llm = ChatOpenAI(model="gpt-4o").bind_tools([complex_tool])

# 2.创建链并执行工具
better_chain = (better_llm | (lambda msg: msg.tool_calls[0]["args"]) | complex_tool)
def safe_get_args(msg):
    if not msg.tool_calls:
        # 可以抛出特定异常让 fallback 生效
        raise ValueError("没有工具调用")
    return msg.tool_calls[0]["args"]

chain = (llm | safe_get_args | complex_tool).with_fallbacks([better_chain])
result = llm.invoke("使用复杂工具，对应参数为5和2.1，dict_arg参数使用{'key': 'value'}")
# print(result.tool_calls)  # 看看是否为空
