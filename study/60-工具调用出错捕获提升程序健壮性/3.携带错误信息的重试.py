#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/12 10:24
@Author  : thezehui@gmail.com
@File    : 3.携带错误信息的重试.py
Human: 使用复杂工具，对应参数为5和2.1
AI: [tool_calls]  # 错误的调用
Tool: [错误信息]   # 工具返回的错误
Human: 最后一次工具调用引发了异常，请尝试使用更正的参数再次调用该工具
"""
from typing import Any

import dotenv
from langchain_core.messages import ToolCall, AIMessage, ToolMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()


class CustomToolException(Exception):
    def __init__(self, tool_call: ToolCall, exception: Exception) -> None:
        super().__init__()
        self.tool_call = tool_call
        self.exception = exception


# 工具函数 装饰过之后，返回的是一个工具对象，工具对象的 invoke 方法可以调用工具函数，并且可以传递参数。才能被 链 调用。
@tool
def complex_tool(int_arg: int, float_arg: float, dict_arg: dict) -> int:
    """使用复杂工具进行复杂计算操作"""
    return int_arg * float_arg


# 当 with_fallbacks 的时候会再次调用 tool_custom_exception 函数，所以需要再次调用工具函数。
def tool_custom_exception(msg: AIMessage, config: RunnableConfig) -> Any:
    try:
        return complex_tool.invoke(msg.tool_calls[0]["args"], config=config)
    except Exception as e:
        raise CustomToolException(msg.tool_calls[0], e)


def exception_to_messages(inputs: dict) -> dict:
    # 1.从inputs中分离出异常信息
    exception = inputs.pop("exception")
    print("exception111111: ", exception)
    # 2.根据异常信息组装占位消息列表
    messages = [
        AIMessage(content="", tool_calls=[exception.tool_call]),
        ToolMessage(tool_call_id=exception.tool_call["id"], content=str(exception.exception)),
        HumanMessage(content="最后一次工具调用引发了异常，请尝试使用更正的参数再次调用该工具，请不要重复犯错"),
    ]
    inputs["last_output"] = messages
    return inputs


# 1.创建prompt
prompt = ChatPromptTemplate.from_messages([
    ("human", "{query}"),
    ("placeholder", "{last_output}") ##当发生异常并触发重试逻辑时，last_output 占位符才会被实际使用。
])

# 2.创建大语言模型并绑定工具
llm = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
    tools=[complex_tool], tool_choice="complex_tool",
)

# 3.创建链并执行工具
chain = prompt | llm | tool_custom_exception
# 默认 with_fallbacks 不会携带上一次的错误，但是如果需要携带上一次的错误，可以设置 exception_key="exception" ，在异常处理时，会将异常信息存储到 inputs 中，然后通过 exception_to_messages 函数将异常信息转换为消息列表，然后传递给下一个链。
self_correcting_chain = chain.with_fallbacks(
    [exception_to_messages | chain], exception_key="exception"
)

# 4.调用自我纠正链完成任务
print(self_correcting_chain.invoke({"query": "使用复杂工具，对应参数为5 和 2.1"}))
