#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/15 1:23
@Author  : thezehui@gmail.com
@File    : 1.基础LangGraph示例.py

开始节点
中间节点
结束节点

# 执行流程：

# 用户调用 graph.invoke()
#     ↓
# 输入状态: {messages: [human消息], use_name: "graph"}
#     ↓
# START 节点（内置入口）
#     ↓
# 通过 add_edge(START, "llm") 流转
#     ↓
# 执行 "llm" 节点（chatbot函数）
#     ├─ 读取 state["messages"]（历史消息）
#     ├─ 调用 llm.invoke() 生成回复
#     └─ 返回 {"messages": [ai_message], "use_name": "chatbot"} 更新到图数据
#     ↓
# 状态自动合并（add_messages）
#     ├─ messages: 旧列表 + 新消息
#     └─ use_name: "graph" → "chatbot"（覆盖）
#     ↓
# 通过 add_edge("llm", END) 流转
#     ↓
# END 节点（内置出口）
#     ↓
# 返回最终状态给调用者
"""
from typing import TypedDict, Annotated, Any

import dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

dotenv.load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini")


# 1.创建状态图，并使用GraphState作为状态数据
# 不加 Annotated = 直接赋值
# state["messages"] = new_list  # 替换

# # 加 Annotated[list, add_messages] = 扩展列表
# state["messages"].extend(new_list)  # 追加
class State(TypedDict):
    """图结构的状态数据"""
    messages: Annotated[list, add_messages] #意思：messages 是一个列表，当多个节点返回这个字段时，使用 add_messages 函数来决定如何合并。
    use_name: str


def chatbot(state: State, config: dict) -> Any:
    """聊天机器人节点，使用大语言模型根据传递的消息列表生成内容"""
    ai_message = llm.invoke(state["messages"])
    # 这里就是把返回的 messages 更新到 图数据 State
    return {"messages": [ai_message], "use_name": "chatbot"} 


graph_builder = StateGraph(State)

# 2.添加节点
graph_builder.add_node("llm", chatbot) #注册一个叫 “llm” 的节点

# 定义连接关系
graph_builder.add_edge(START, "llm")    # 开始 → 先执行llm
graph_builder.add_edge("llm", END)      # llm执行完 → 结束

# 4.compile 编译图为 Runnable 可运行组件
graph = graph_builder.compile()

# 5.调用图架构应用  就是 调用 Runnable 可运行函数
print(graph.invoke({"messages": [("human", "你好，你是谁，我叫慕小课，我喜欢打篮球游泳")], "use_name": "graph"}))

